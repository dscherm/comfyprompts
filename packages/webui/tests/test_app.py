"""Offline tests for the comfyui-webui Flask backend.

All tests run without a live ComfyUI. The module-level ``client`` attribute
on the app module is monkeypatched per-test so that no real HTTP calls reach
ComfyUI.  ``manager`` and ``validator`` are real objects loaded from the repo
at import time (same as production).
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Import the app module.  ComfyUIClient.__init__ calls _refresh_models() which
# does an HTTP GET; it catches all exceptions internally so import succeeds even
# if ComfyUI is unreachable.
# ---------------------------------------------------------------------------
import comfyui_webui.app as app_module
from comfyui_webui.app import app, manager, PARAM_RE


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """Flask test client with testing mode enabled."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _make_stub_client(**method_returns: Any):
    """Build a SimpleNamespace that mimics the subset of ComfyUIClient used by app.py."""
    stub = SimpleNamespace(
        base_url="http://localhost:8188",
        queue_prompt=lambda workflow: method_returns.get("queue_prompt", {"prompt_id": "stub-id"}),
        get_job_status=lambda prompt_id: method_returns.get("get_job_status", {"status": "pending"}),
        get_history=lambda prompt_id: method_returns.get("get_history", {}),
        check_connection=lambda: method_returns.get("check_connection", {"connected": True}),
        upload_image=lambda data, filename: method_returns.get("upload_image", {}),
    )
    return stub


# ---------------------------------------------------------------------------
# 1. GET /api/workflows
# ---------------------------------------------------------------------------

class TestWorkflowCatalog:
    def test_returns_200_and_list(self, client):
        resp = client.get("/api/workflows")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)

    def test_more_than_40_entries(self, client):
        data = client.get("/api/workflows").get_json()
        assert len(data) > 40, f"expected >40 workflows, got {len(data)}"

    def test_each_entry_has_required_keys(self, client):
        data = client.get("/api/workflows").get_json()
        for item in data:
            assert "id" in item, f"missing 'id' in {item}"
            assert "name" in item, f"missing 'name' in {item}"
            assert "category" in item, f"missing 'category' in {item}"
            assert "parameters" in item, f"missing 'parameters' in {item}"

    def test_generate_image_present_with_required_params(self, client):
        data = client.get("/api/workflows").get_json()
        gi = next((w for w in data if w["id"] == "generate_image"), None)
        assert gi is not None, "generate_image not in workflow list"

        param_names = {p["name"] for p in gi["parameters"]}
        assert "prompt" in param_names, f"'prompt' not in generate_image parameters: {param_names}"
        assert "steps" in param_names, f"'steps' not in generate_image parameters: {param_names}"

        # prompt must be marked required
        prompt_param = next(p for p in gi["parameters"] if p["name"] == "prompt")
        assert prompt_param["required"] is True, "generate_image 'prompt' should be required"


# ---------------------------------------------------------------------------
# 2. POST /api/generate — unknown workflow → 404
# ---------------------------------------------------------------------------

class TestGenerateUnknownWorkflow:
    def test_unknown_workflow_returns_404(self, client, monkeypatch):
        stub = _make_stub_client()
        monkeypatch.setattr(app_module, "client", stub)

        resp = client.post(
            "/api/generate",
            data=json.dumps({"workflow_id": "workflow_that_does_not_exist_xyz", "params": {}}),
            content_type="application/json",
        )
        assert resp.status_code == 404
        body = resp.get_json()
        assert "error" in body


# ---------------------------------------------------------------------------
# 3. POST /api/generate — generate_image with only prompt
# ---------------------------------------------------------------------------

class TestGenerateImageMinimal:
    def test_minimal_payload_fills_defaults(self, client, monkeypatch):
        """Only prompt supplied → defaults+fallbacks fill everything; no PARAM_ leftovers."""
        captured: list[dict] = []

        def fake_queue_prompt(workflow: dict) -> dict:
            captured.append(workflow)
            return {"prompt_id": "test-123"}

        stub = _make_stub_client()
        stub.queue_prompt = fake_queue_prompt
        monkeypatch.setattr(app_module, "client", stub)

        resp = client.post(
            "/api/generate",
            data=json.dumps({"workflow_id": "generate_image", "params": {"prompt": "a cat"}}),
            content_type="application/json",
        )
        assert resp.status_code == 200, resp.get_json()
        body = resp.get_json()
        assert body["prompt_id"] == "test-123"

        # Verify the captured workflow has no leftover PARAM_ placeholders
        assert captured, "queue_prompt was never called"
        rendered_str = json.dumps(captured[0])
        leftover = PARAM_RE.findall(rendered_str)
        assert not leftover, f"Leftover PARAM_ placeholders in rendered workflow: {leftover}"

    def test_returns_prompt_id_in_response(self, client, monkeypatch):
        stub = _make_stub_client(queue_prompt={"prompt_id": "abc-456"})
        monkeypatch.setattr(app_module, "client", stub)

        resp = client.post(
            "/api/generate",
            data=json.dumps({"workflow_id": "generate_image", "params": {"prompt": "a dog"}}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["prompt_id"] == "abc-456"


# ---------------------------------------------------------------------------
# 4. GET /api/job/<id>
# ---------------------------------------------------------------------------

class TestJobStatus:
    def test_unknown_status_maps_to_pending(self, client, monkeypatch):
        """get_job_status returning 'unknown' → response status 'pending', error null."""
        stub = _make_stub_client(get_job_status={"status": "unknown"})
        monkeypatch.setattr(app_module, "client", stub)

        resp = client.get("/api/job/some-prompt-id")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["status"] == "pending"
        assert body["error"] is None

    def test_completed_status_builds_output_urls(self, client, monkeypatch):
        """Completed job: history outputs → response outputs with filename and /api/view? url."""
        history_payload = {
            "test-prompt-99": {
                "outputs": {
                    "9": {
                        "images": [
                            {"filename": "a.png", "subfolder": "", "type": "output"}
                        ]
                    }
                }
            }
        }

        stub = _make_stub_client(
            get_job_status={"status": "completed"},
            get_history=history_payload,
        )
        # get_history is called with the prompt_id; make it return the dict regardless
        stub.get_job_status = lambda prompt_id: {"status": "completed"}
        stub.get_history = lambda prompt_id: history_payload

        monkeypatch.setattr(app_module, "client", stub)

        resp = client.get("/api/job/test-prompt-99")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["status"] == "completed"
        assert len(body["outputs"]) >= 1

        first = body["outputs"][0]
        assert first["filename"] == "a.png"
        assert first["url"].startswith("/api/view?")
        assert "filename=a.png" in first["url"]

    def test_error_status_includes_error_field(self, client, monkeypatch):
        stub = _make_stub_client(get_job_status={"status": "error", "error": "OOM"})
        monkeypatch.setattr(app_module, "client", stub)

        resp = client.get("/api/job/err-id")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["status"] == "error"
        assert body["error"] == "OOM"


# ---------------------------------------------------------------------------
# 5. POST /api/author/validate
# ---------------------------------------------------------------------------

class TestAuthorValidate:
    # Use a structurally broken workflow guaranteed to fail without object_info:
    # a node whose input links to a non-existent source node.
    STRUCTURAL_BREAK = {
        "1": {
            "class_type": "CLIPTextEncode",
            "inputs": {"x": ["99", 0]},  # node 99 doesn't exist → structural error
        }
    }

    # A workflow with a bogus class_type — caught only when object_info is present
    BOGUS_CLASS = {
        "1": {"class_type": "DefinitelyNotARealNode", "inputs": {}}
    }

    def test_missing_workflow_body_returns_400(self, client):
        resp = client.post(
            "/api/author/validate",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_structurally_broken_workflow_fails(self, client):
        """A workflow with a dangling link always fails validation (no object_info needed)."""
        resp = client.post(
            "/api/author/validate",
            data=json.dumps({"workflow": self.STRUCTURAL_BREAK}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["ok"] is False
        assert len(body["errors"]) > 0

    def test_bogus_class_detected(self, client):
        """Bogus class_type is detected when object_info cache is present; otherwise test
        the structural-break path to stay deterministic."""
        resp = client.post(
            "/api/author/validate",
            data=json.dumps({"workflow": self.BOGUS_CLASS}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        body = resp.get_json()

        if body.get("checked_against_live_nodes"):
            # object_info present: bogus class must be caught
            assert body["ok"] is False
            assert any("DefinitelyNotARealNode" in e for e in body["errors"])
        else:
            # structural-only mode: fall back to the structural-break assertion
            resp2 = client.post(
                "/api/author/validate",
                data=json.dumps({"workflow": self.STRUCTURAL_BREAK}),
                content_type="application/json",
            )
            body2 = resp2.get_json()
            assert body2["ok"] is False
            assert len(body2["errors"]) > 0


# ---------------------------------------------------------------------------
# 6. POST /api/author/save
# ---------------------------------------------------------------------------

class TestAuthorSave:
    VALID_WORKFLOW = {
        "1": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "test", "images": ["2", 0]},
        },
        "2": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 0]},
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 42, "steps": 20, "cfg": 7.0,
                "sampler_name": "euler", "scheduler": "normal",
                "denoise": 1.0,
                "model": ["5", 0], "positive": ["6", 0],
                "negative": ["6", 0], "latent_image": ["7", 0],
            },
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"},
        },
        "5": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "test prompt", "clip": ["5", 1]},
        },
        "7": {
            "class_type": "EmptySD3LatentImage",
            "inputs": {"width": 512, "height": 512, "batch_size": 1},
        },
    }

    def test_invalid_id_returns_400(self, client):
        resp = client.post(
            "/api/author/save",
            data=json.dumps({
                "id": "Bad Name!",
                "workflow": self.VALID_WORKFLOW,
            }),
            content_type="application/json",
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert "error" in body

    def test_existing_id_without_overwrite_returns_409(self, client):
        """generate_image already exists in repo → 409 Conflict without overwrite:true."""
        resp = client.post(
            "/api/author/save",
            data=json.dumps({
                "id": "generate_image",
                "workflow": self.VALID_WORKFLOW,
                # no "overwrite": true
            }),
            content_type="application/json",
        )
        assert resp.status_code == 409
        body = resp.get_json()
        assert "error" in body


# ---------------------------------------------------------------------------
# 7. POST /api/author/request + GET /api/author/requests
# ---------------------------------------------------------------------------

class TestAuthorRequest:
    def test_missing_fields_returns_400(self, client):
        resp = client.post(
            "/api/author/request",
            data=json.dumps({"title": "Only title, no spec"}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_request_queued_and_listed(self, client, monkeypatch, tmp_path):
        """A valid request writes a file to BRIDGE_DIR; GET /api/author/requests lists it."""
        bridge_dir = tmp_path / "webui-requests"
        monkeypatch.setattr(app_module, "BRIDGE_DIR", bridge_dir)

        title = "My test workflow"
        spec = "Generate a test image using a simple KSampler."

        resp = client.post(
            "/api/author/request",
            data=json.dumps({"title": title, "spec": spec}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert "queued" in body
        fname = body["queued"]
        assert fname.endswith(".md")

        # The file must exist in the temp bridge dir
        assert (bridge_dir / fname).exists()

        # GET /api/author/requests should list it
        resp2 = client.get("/api/author/requests")
        assert resp2.status_code == 200
        items = resp2.get_json()
        assert isinstance(items, list)
        filenames = [item["file"] for item in items]
        assert fname in filenames

    def test_request_file_content(self, client, monkeypatch, tmp_path):
        """The written .md file contains the title and spec text."""
        bridge_dir = tmp_path / "bridge"
        monkeypatch.setattr(app_module, "BRIDGE_DIR", bridge_dir)

        title = "Portrait workflow"
        spec = "High-quality portrait with bokeh background."

        resp = client.post(
            "/api/author/request",
            data=json.dumps({"title": title, "spec": spec}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        fname = resp.get_json()["queued"]
        content = (bridge_dir / fname).read_text(encoding="utf-8")
        assert title in content
        assert spec in content

    def test_requests_empty_when_no_dir(self, client, monkeypatch, tmp_path):
        """If BRIDGE_DIR does not exist, GET /api/author/requests returns []."""
        monkeypatch.setattr(app_module, "BRIDGE_DIR", tmp_path / "nonexistent")
        resp = client.get("/api/author/requests")
        assert resp.status_code == 200
        assert resp.get_json() == []


class TestEnumOptions:
    def test_catalog_exposes_meta_options_as_dropdown(self, client):
        """Params whose .meta.json declares options[] surface them in the catalog."""
        resp = client.get("/api/workflows")
        assert resp.status_code == 200
        wf = next(
            (w for w in resp.get_json() if w["id"] == "multiview_full_body_profile"), None
        )
        assert wf is not None, "multiview_full_body_profile missing from catalog"
        style = next(p for p in wf["parameters"] if p["name"] == "style")
        assert isinstance(style.get("options"), list) and len(style["options"]) >= 4
        assert style["default"] in style["options"]
        prompt = next(p for p in wf["parameters"] if p["name"] == "prompt")
        assert "options" not in prompt
