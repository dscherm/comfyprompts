"""Tests for tools/vlm_judge.py — local-VLM visual QA.

These cover the parts that break silently in production: JSON extraction from chatty
model output, and the cold-load empty-response retry. Neither needs ollama running.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import vlm_judge  # noqa: E402


class TestExtractJsonObject:
    def test_bare_object(self):
        assert vlm_judge._extract_json_object('{"verdict": "pass"}') == {"verdict": "pass"}

    def test_ignores_prose_around_it(self):
        raw = 'Sure! Here is my analysis:\n{"verdict": "fail"}\nHope that helps.'
        assert vlm_judge._extract_json_object(raw) == {"verdict": "fail"}

    def test_markdown_fenced(self):
        raw = '```json\n{"verdict": "pass", "confidence": 0.9}\n```'
        assert vlm_judge._extract_json_object(raw)["confidence"] == 0.9

    def test_nested_objects(self):
        raw = '{"verdict": "pass", "observations": {"accent": {"colour": "green"}}}'
        got = vlm_judge._extract_json_object(raw)
        assert got["observations"]["accent"]["colour"] == "green"

    def test_braces_inside_strings_do_not_unbalance(self):
        # A naive brace counter terminates early here and yields invalid JSON.
        raw = '{"reasoning": "the shape looks like a { brace", "verdict": "pass"}'
        got = vlm_judge._extract_json_object(raw)
        assert got["verdict"] == "pass"

    def test_escaped_quote_inside_string(self):
        raw = r'{"reasoning": "it is \"green\"", "verdict": "pass"}'
        assert vlm_judge._extract_json_object(raw)["verdict"] == "pass"

    def test_no_json_returns_none(self):
        assert vlm_judge._extract_json_object("I cannot see an image.") is None

    def test_malformed_json_returns_none(self):
        assert vlm_judge._extract_json_object('{"verdict": pass}') is None

    def test_empty_string_returns_none(self):
        assert vlm_judge._extract_json_object("") is None


class TestColdLoadRetry:
    """A cold model load INTERMITTENTLY returns an EMPTY string on the first call.

    Observed on qwen3-vl:8b (33s, 6GB) and :32b (113s, 20GB): image 1 of 9 came back
    empty, every later call parsed fine — but a later cold 8b run did not reproduce it.
    Intermittent, so a retry is the fix rather than a warmup call.
    """

    def test_retries_once_when_first_response_is_empty(self, monkeypatch):
        calls = []

        def fake_once(model, image_bytes, prompt, num_ctx, timeout):
            calls.append(model)
            if len(calls) == 1:
                return "", 33.0
            return '{"verdict": "pass"}', 5.0

        monkeypatch.setattr(vlm_judge, "_call_vision_model_once", fake_once)
        raw, latency = vlm_judge._call_vision_model("m", b"x", "p", 4096, 300.0)
        assert len(calls) == 2
        assert raw == '{"verdict": "pass"}'
        assert latency == pytest.approx(38.0)  # both attempts counted

    def test_no_retry_when_first_response_is_good(self, monkeypatch):
        calls = []

        def fake_once(model, image_bytes, prompt, num_ctx, timeout):
            calls.append(model)
            return '{"verdict": "pass"}', 5.0

        monkeypatch.setattr(vlm_judge, "_call_vision_model_once", fake_once)
        raw, _ = vlm_judge._call_vision_model("m", b"x", "p", 4096, 300.0)
        assert len(calls) == 1
        assert raw == '{"verdict": "pass"}'

    def test_whitespace_only_counts_as_empty(self, monkeypatch):
        calls = []

        def fake_once(model, image_bytes, prompt, num_ctx, timeout):
            calls.append(model)
            return ("   \n  ", 33.0) if len(calls) == 1 else ('{"verdict": "fail"}', 5.0)

        monkeypatch.setattr(vlm_judge, "_call_vision_model_once", fake_once)
        raw, _ = vlm_judge._call_vision_model("m", b"x", "p", 4096, 300.0)
        assert len(calls) == 2
        assert raw == '{"verdict": "fail"}'

    def test_gives_up_after_one_retry(self, monkeypatch):
        calls = []

        def fake_once(model, image_bytes, prompt, num_ctx, timeout):
            calls.append(model)
            return "", 10.0

        monkeypatch.setattr(vlm_judge, "_call_vision_model_once", fake_once)
        raw, _ = vlm_judge._call_vision_model("m", b"x", "p", 4096, 300.0)
        assert len(calls) == 2  # does not loop forever
        assert raw == ""


class TestResolveImage:
    def test_existing_path(self, tmp_path):
        p = tmp_path / "a.png"
        p.write_bytes(b"x")
        assert vlm_judge._resolve_image(str(p), None) == p

    def test_missing_path_raises(self):
        with pytest.raises(FileNotFoundError):
            vlm_judge._resolve_image("nope/does_not_exist.png", None)

    def test_falls_back_to_asset_registry(self, tmp_path):
        p = tmp_path / "asset.png"
        p.write_bytes(b"x")

        class FakeRecord:
            path = str(p)

        class FakeRegistry:
            def get(self, asset_id):
                return FakeRecord() if asset_id == "asset-123" else None

        assert vlm_judge._resolve_image("asset-123", FakeRegistry()) == p

    def test_registry_miss_raises(self):
        class FakeRegistry:
            def get(self, asset_id):
                return None

        with pytest.raises(FileNotFoundError):
            vlm_judge._resolve_image("unknown-id", FakeRegistry())

    def test_registry_exception_does_not_leak(self):
        """Registry APIs vary; a raising registry must still yield a clear error."""

        class ExplodingRegistry:
            def get(self, asset_id):
                raise RuntimeError("registry backend down")

        with pytest.raises(FileNotFoundError):
            vlm_judge._resolve_image("some-id", ExplodingRegistry())


class TestDefaults:
    def test_num_ctx_capped_well_below_ollama_default(self):
        """ollama's 32768 default spills the 32b off-GPU (>600s/image vs ~20s)."""
        assert vlm_judge.DEFAULT_NUM_CTX <= 8192

    def test_default_model_is_the_fast_one(self):
        """8b scored 90% on the probe at 5-24s/image; 32b is ~10x slower."""
        assert vlm_judge.DEFAULT_MODEL == "qwen3-vl:8b"
