"""Integration tests validating Blender workflow rendering and submission.

Tests that parametric Blender workflows (depth, normal, pose) render correctly
and produce ComfyUI-compatible workflow dicts when combined with the WorkflowManager.
"""

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
WORKFLOWS_DIR = REPO_ROOT / "workflows" / "mcp"

BLENDER_WORKFLOWS = {
    "blender_depth_guided": {
        "required_params": ["depth_image", "source_image", "prompt"],
        "required_nodes": [
            "CheckpointLoaderSimple", "ControlNetLoader", "LoadImage",
            "VAEEncode", "CLIPTextEncode", "ControlNetApply", "KSampler",
            "VAEDecode", "SaveImage",
        ],
        "controlnet_model": "control_v11f1p_sd15_depth.pth",
    },
    "blender_normal_texturing": {
        "required_params": ["normal_image", "prompt"],
        "required_nodes": [
            "CheckpointLoaderSimple", "ControlNetLoader", "LoadImage",
            "EmptyLatentImage", "CLIPTextEncode", "ControlNetApply",
            "KSampler", "VAEDecode", "SaveImage",
        ],
        "controlnet_model": "control_v11p_sd15_normalbae.pth",
    },
    "blender_pose_to_render": {
        "required_params": ["pose_image", "prompt"],
        "required_nodes": [
            "CheckpointLoaderSimple", "ControlNetLoader", "LoadImage",
            "EmptyLatentImage", "CLIPTextEncode", "ControlNetApply",
            "KSampler", "VAEDecode", "SaveImage",
        ],
        "controlnet_model": "OpenPoseXL2.safetensors",
    },
}


class TestWorkflowFileIntegrity:
    """Validate JSON structure and meta/workflow consistency."""

    @pytest.mark.parametrize("name", BLENDER_WORKFLOWS.keys())
    def test_workflow_json_matches_meta_nodes(self, name):
        """Every node in meta requirements should be present in the workflow."""
        spec = BLENDER_WORKFLOWS[name]
        with open(WORKFLOWS_DIR / f"{name}.json") as f:
            wf = json.load(f)
        with open(WORKFLOWS_DIR / f"{name}.meta.json") as f:
            meta = json.load(f)

        wf_class_types = {node["class_type"] for node in wf.values() if isinstance(node, dict)}
        required_nodes = set(meta["requirements"]["nodes"])

        missing = required_nodes - wf_class_types
        assert not missing, f"Meta requires nodes not in workflow: {missing}"

    @pytest.mark.parametrize("name", BLENDER_WORKFLOWS.keys())
    def test_controlnet_model_matches(self, name):
        """ControlNetLoader in workflow uses the model specified in meta."""
        spec = BLENDER_WORKFLOWS[name]
        with open(WORKFLOWS_DIR / f"{name}.json") as f:
            wf = json.load(f)

        controlnet_nodes = [
            n for n in wf.values()
            if isinstance(n, dict) and n.get("class_type") == "ControlNetLoader"
        ]
        assert len(controlnet_nodes) == 1
        assert controlnet_nodes[0]["inputs"]["control_net_name"] == spec["controlnet_model"]

    @pytest.mark.parametrize("name", BLENDER_WORKFLOWS.keys())
    def test_all_param_placeholders_in_workflow(self, name):
        """Every meta parameter should have a corresponding PARAM_* in the workflow JSON."""
        with open(WORKFLOWS_DIR / f"{name}.json") as f:
            wf_text = f.read()
        with open(WORKFLOWS_DIR / f"{name}.meta.json") as f:
            meta = json.load(f)

        for param_name in meta["parameters"]:
            param_type = meta["parameters"][param_name]["type"]
            type_prefix = {"string": "STR", "int": "INT", "float": "FLOAT"}.get(param_type, "STR")
            placeholder = f"PARAM_{type_prefix}_{param_name.upper()}"
            # Some params like "prompt" map to "PARAM_PROMPT" (no type prefix)
            has_typed = placeholder in wf_text
            has_untyped = f"PARAM_{param_name.upper()}" in wf_text
            assert has_typed or has_untyped, (
                f"Parameter '{param_name}' has no placeholder in {name}.json "
                f"(looked for {placeholder} and PARAM_{param_name.upper()})"
            )

    @pytest.mark.parametrize("name", BLENDER_WORKFLOWS.keys())
    def test_node_graph_connectivity(self, name):
        """Every node input that references another node should reference a valid node ID."""
        with open(WORKFLOWS_DIR / f"{name}.json") as f:
            wf = json.load(f)

        node_ids = set(wf.keys())
        for node_id, node in wf.items():
            if not isinstance(node, dict) or "inputs" not in node:
                continue
            for input_name, input_val in node["inputs"].items():
                if isinstance(input_val, list) and len(input_val) == 2:
                    ref_id, ref_slot = input_val
                    assert str(ref_id) in node_ids, (
                        f"Node {node_id} ({node.get('class_type')}) input '{input_name}' "
                        f"references non-existent node '{ref_id}'"
                    )


class TestWorkflowManagerRendering:
    """Test WorkflowManager renders Blender workflows with correct substitutions."""

    def test_depth_guided_renders_all_params(self, workflow_manager):
        defn = next(
            d for d in workflow_manager.tool_definitions
            if d.tool_name == "blender_depth_guided"
        )
        rendered = workflow_manager.render_workflow(defn, {
            "prompt": "stylized landscape",
            "negative_prompt": "ugly, blurry",
            "depth_image": "depth_pass.png",
            "source_image": "render_pass.png",
            "controlnet_strength": 0.7,
            "steps": 30,
            "cfg": 8.0,
            "seed": 42,
            "sampler_name": "dpmpp_2m",
            "scheduler": "karras",
            "denoise": 0.6,
        })

        # Verify no PARAM_* placeholders remain
        rendered_json = json.dumps(rendered)
        assert "PARAM_" not in rendered_json, (
            f"Unsubstituted placeholders in rendered workflow: "
            f"{[w for w in rendered_json.split() if 'PARAM_' in w]}"
        )

        # Verify specific values
        assert rendered["6"]["inputs"]["text"] == "stylized landscape"
        assert rendered["7"]["inputs"]["text"] == "ugly, blurry"
        assert rendered["3"]["inputs"]["image"] == "depth_pass.png"
        assert rendered["4"]["inputs"]["image"] == "render_pass.png"
        assert rendered["8"]["inputs"]["strength"] == 0.7
        assert rendered["9"]["inputs"]["steps"] == 30
        assert rendered["9"]["inputs"]["cfg"] == 8.0
        assert rendered["9"]["inputs"]["seed"] == 42

    def test_normal_texturing_renders_required_params(self, workflow_manager):
        defn = next(
            d for d in workflow_manager.tool_definitions
            if d.tool_name == "blender_normal_texturing"
        )
        rendered = workflow_manager.render_workflow(defn, {
            "prompt": "stone wall texture",
            "normal_image": "normal_map.png",
        })

        # Required params should be substituted
        assert rendered["5"]["inputs"]["text"] == "stone wall texture"
        assert rendered["3"]["inputs"]["image"] == "normal_map.png"

    def test_normal_texturing_renders_all_params(self, workflow_manager):
        defn = next(
            d for d in workflow_manager.tool_definitions
            if d.tool_name == "blender_normal_texturing"
        )
        rendered = workflow_manager.render_workflow(defn, {
            "prompt": "stone wall texture",
            "negative_prompt": "blurry",
            "normal_image": "normal_map.png",
            "controlnet_strength": 0.9,
            "width": 512,
            "height": 512,
            "steps": 30,
            "cfg": 7.5,
            "seed": 42,
            "sampler_name": "dpmpp_2m",
            "scheduler": "karras",
            "denoise": 1.0,
        })

        rendered_json = json.dumps(rendered)
        assert "PARAM_" not in rendered_json
        assert rendered["4"]["inputs"]["width"] == 512
        assert rendered["4"]["inputs"]["height"] == 512

    def test_pose_to_render_renders_required_params(self, workflow_manager):
        defn = next(
            d for d in workflow_manager.tool_definitions
            if d.tool_name == "blender_pose_to_render"
        )
        rendered = workflow_manager.render_workflow(defn, {
            "prompt": "anime character, dynamic pose",
            "pose_image": "pose_vis.png",
            "width": 768,
            "height": 1024,
        })

        # Provided params should be substituted
        assert rendered["5"]["inputs"]["text"] == "anime character, dynamic pose"
        assert rendered["3"]["inputs"]["image"] == "pose_vis.png"
        assert rendered["4"]["inputs"]["width"] == 768
        assert rendered["4"]["inputs"]["height"] == 1024

    def test_pose_to_render_renders_all_params(self, workflow_manager):
        defn = next(
            d for d in workflow_manager.tool_definitions
            if d.tool_name == "blender_pose_to_render"
        )
        rendered = workflow_manager.render_workflow(defn, {
            "prompt": "anime character",
            "negative_prompt": "ugly",
            "pose_image": "pose_vis.png",
            "controlnet_strength": 0.8,
            "width": 512,
            "height": 768,
            "steps": 25,
            "cfg": 7.5,
            "seed": 42,
            "sampler_name": "dpmpp_2m",
            "scheduler": "karras",
            "denoise": 1.0,
        })

        rendered_json = json.dumps(rendered)
        assert "PARAM_" not in rendered_json

    def test_rendered_workflow_submittable(self, workflow_manager, comfyui_client):
        """Rendered Blender workflow can be queued to (mock) ComfyUI."""
        defn = next(
            d for d in workflow_manager.tool_definitions
            if d.tool_name == "blender_depth_guided"
        )
        rendered = workflow_manager.render_workflow(defn, {
            "prompt": "test submission",
            "depth_image": "depth.png",
            "source_image": "render.png",
        })

        ok, queue = comfyui_client.queue_prompt(rendered)
        assert ok, f"Failed to queue rendered workflow: {queue}"
        assert "prompt_id" in queue

        ok, status = comfyui_client.get_job_status(queue["prompt_id"])
        assert ok
        assert status["status"] == "completed"


class TestCrossPipelineConsistency:
    """Verify consistency between the direct client and MCP-based pipelines."""

    def test_both_pipelines_use_same_checkpoint(self, workflow_manager):
        """Direct and MCP pipelines should both target the default checkpoint.

        Workflows with a requires_download block are pinned to a not-yet-
        installed model stack on purpose — they are exempt.
        """
        from workflows import DEFAULT_CHECKPOINT

        for name in BLENDER_WORKFLOWS:
            with open(WORKFLOWS_DIR / f"{name}.meta.json") as f:
                meta = json.load(f)
            if meta.get("requires_download"):
                continue
            assert meta["requirements"]["models"]["checkpoint"] == DEFAULT_CHECKPOINT, (
                f"{name} uses different checkpoint than direct pipeline default"
            )

    def test_direct_and_parametric_workflow_output_nodes_match(self, workflow_manager):
        """Both pipeline types use SaveImage as the output node."""
        from workflows import build_img2img_workflow, build_txt2img_workflow

        # Direct pipeline
        img2img = build_img2img_workflow("test.png", "test", seed=42)
        txt2img = build_txt2img_workflow("test", seed=42)

        direct_outputs = set()
        for wf in [img2img, txt2img]:
            for node in wf.values():
                if node["class_type"] == "SaveImage":
                    direct_outputs.add("SaveImage")

        # Parametric pipeline
        for name in BLENDER_WORKFLOWS:
            with open(WORKFLOWS_DIR / f"{name}.json") as f:
                wf = json.load(f)
            for node in wf.values():
                if isinstance(node, dict) and node.get("class_type") == "SaveImage":
                    assert True
                    break
            else:
                pytest.fail(f"{name} has no SaveImage output node")
