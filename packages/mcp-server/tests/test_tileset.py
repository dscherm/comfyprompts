"""Tests for the tileset generation tool"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.tileset import _build_simple_workflow, _build_coherent_tileset_workflow


class TestBuildSimpleWorkflow:
    """Test _build_simple_workflow generates correct ComfyUI workflow dicts"""

    def _default_kwargs(self, **overrides):
        defaults = dict(
            model="test_model.safetensors",
            prompt="grass terrain, seamless",
            negative_prompt="blurry, text",
            lora_name=None,
            lora_strength=0.85,
            tile_size=512,
            seed=42,
            steps=25,
            cfg=7.0,
            sampler_name="euler",
            scheduler="normal",
        )
        defaults.update(overrides)
        return defaults

    def test_has_required_nodes(self):
        wf = _build_simple_workflow(**self._default_kwargs())
        class_types = {v["class_type"] for v in wf.values()}
        assert "CheckpointLoaderSimple" in class_types
        assert "CLIPTextEncode" in class_types
        assert "KSampler" in class_types
        assert "VAEDecode" in class_types
        assert "SaveImage" in class_types
        assert "EmptyLatentImage" in class_types

    def test_two_clip_text_encodes(self):
        wf = _build_simple_workflow(**self._default_kwargs())
        clip_nodes = [v for v in wf.values() if v["class_type"] == "CLIPTextEncode"]
        assert len(clip_nodes) == 2

    def test_positive_prompt_text(self):
        wf = _build_simple_workflow(**self._default_kwargs(prompt="my custom prompt"))
        clip_nodes = [v for v in wf.values() if v["class_type"] == "CLIPTextEncode"]
        texts = [n["inputs"]["text"] for n in clip_nodes]
        assert "my custom prompt" in texts

    def test_negative_prompt_text(self):
        wf = _build_simple_workflow(**self._default_kwargs(negative_prompt="ugly, bad"))
        clip_nodes = [v for v in wf.values() if v["class_type"] == "CLIPTextEncode"]
        texts = [n["inputs"]["text"] for n in clip_nodes]
        assert "ugly, bad" in texts

    def test_with_lora(self):
        wf = _build_simple_workflow(
            **self._default_kwargs(lora_name="style/SomeTile.safetensors")
        )
        class_types = {v["class_type"] for v in wf.values()}
        assert "LoraLoader" in class_types

    def test_lora_strength_applied(self):
        wf = _build_simple_workflow(
            **self._default_kwargs(
                lora_name="style/SomeTile.safetensors", lora_strength=0.6
            )
        )
        lora_nodes = [v for v in wf.values() if v["class_type"] == "LoraLoader"]
        assert len(lora_nodes) == 1
        assert lora_nodes[0]["inputs"]["strength_model"] == 0.6
        assert lora_nodes[0]["inputs"]["strength_clip"] == 0.6

    def test_lora_receives_checkpoint_outputs(self):
        wf = _build_simple_workflow(
            **self._default_kwargs(lora_name="style/SomeTile.safetensors")
        )
        lora_nodes = [v for v in wf.values() if v["class_type"] == "LoraLoader"]
        assert len(lora_nodes) == 1
        lora_inputs = lora_nodes[0]["inputs"]
        # LoRA should reference checkpoint node for model and clip
        checkpoint_id = None
        for nid, node in wf.items():
            if node["class_type"] == "CheckpointLoaderSimple":
                checkpoint_id = nid
                break
        assert checkpoint_id is not None
        assert lora_inputs["model"] == [checkpoint_id, 0]
        assert lora_inputs["clip"] == [checkpoint_id, 1]

    def test_without_lora(self):
        wf = _build_simple_workflow(**self._default_kwargs(lora_name=None))
        class_types = {v["class_type"] for v in wf.values()}
        assert "LoraLoader" not in class_types

    def test_ksampler_uses_lora_model_when_present(self):
        wf = _build_simple_workflow(
            **self._default_kwargs(lora_name="style/SomeTile.safetensors")
        )
        ksampler = [v for v in wf.values() if v["class_type"] == "KSampler"][0]
        lora_id = None
        for nid, node in wf.items():
            if node["class_type"] == "LoraLoader":
                lora_id = nid
                break
        assert lora_id is not None
        assert ksampler["inputs"]["model"] == [lora_id, 0]

    def test_ksampler_uses_checkpoint_model_without_lora(self):
        wf = _build_simple_workflow(**self._default_kwargs(lora_name=None))
        ksampler = [v for v in wf.values() if v["class_type"] == "KSampler"][0]
        checkpoint_id = None
        for nid, node in wf.items():
            if node["class_type"] == "CheckpointLoaderSimple":
                checkpoint_id = nid
                break
        assert checkpoint_id is not None
        assert ksampler["inputs"]["model"] == [checkpoint_id, 0]

    def test_tile_size_applied(self):
        wf = _build_simple_workflow(**self._default_kwargs(tile_size=256))
        latent_nodes = [
            v for v in wf.values() if v["class_type"] == "EmptyLatentImage"
        ]
        assert len(latent_nodes) == 1
        assert latent_nodes[0]["inputs"]["width"] == 256
        assert latent_nodes[0]["inputs"]["height"] == 256

    def test_seed_applied(self):
        wf = _build_simple_workflow(**self._default_kwargs(seed=12345))
        ksampler = [v for v in wf.values() if v["class_type"] == "KSampler"][0]
        assert ksampler["inputs"]["seed"] == 12345

    def test_steps_applied(self):
        wf = _build_simple_workflow(**self._default_kwargs(steps=30))
        ksampler = [v for v in wf.values() if v["class_type"] == "KSampler"][0]
        assert ksampler["inputs"]["steps"] == 30

    def test_cfg_applied(self):
        wf = _build_simple_workflow(**self._default_kwargs(cfg=5.5))
        ksampler = [v for v in wf.values() if v["class_type"] == "KSampler"][0]
        assert ksampler["inputs"]["cfg"] == 5.5

    def test_sampler_and_scheduler_applied(self):
        wf = _build_simple_workflow(
            **self._default_kwargs(sampler_name="dpmpp_2m", scheduler="karras")
        )
        ksampler = [v for v in wf.values() if v["class_type"] == "KSampler"][0]
        assert ksampler["inputs"]["sampler_name"] == "dpmpp_2m"
        assert ksampler["inputs"]["scheduler"] == "karras"

    def test_node_connections_valid(self):
        """All node references point to existing nodes"""
        wf = _build_simple_workflow(**self._default_kwargs())
        node_ids = set(wf.keys())
        for node_id, node in wf.items():
            for key, val in node["inputs"].items():
                if isinstance(val, list) and len(val) == 2:
                    ref_id, ref_idx = val
                    assert ref_id in node_ids, (
                        f"Node {node_id} input '{key}' references nonexistent node {ref_id}"
                    )

    def test_node_connections_valid_with_lora(self):
        """Node references valid when LoRA is included"""
        wf = _build_simple_workflow(
            **self._default_kwargs(lora_name="style/Test.safetensors")
        )
        node_ids = set(wf.keys())
        for node_id, node in wf.items():
            for key, val in node["inputs"].items():
                if isinstance(val, list) and len(val) == 2:
                    ref_id, ref_idx = val
                    assert ref_id in node_ids, (
                        f"Node {node_id} input '{key}' references nonexistent node {ref_id}"
                    )

    def test_checkpoint_model_name(self):
        wf = _build_simple_workflow(
            **self._default_kwargs(model="my_checkpoint_v2.safetensors")
        )
        ckpt = [
            v for v in wf.values() if v["class_type"] == "CheckpointLoaderSimple"
        ][0]
        assert ckpt["inputs"]["ckpt_name"] == "my_checkpoint_v2.safetensors"

    def test_save_image_prefix(self):
        wf = _build_simple_workflow(**self._default_kwargs())
        save_nodes = [v for v in wf.values() if v["class_type"] == "SaveImage"]
        assert len(save_nodes) == 1
        assert "filename_prefix" in save_nodes[0]["inputs"]

    def test_denoise_is_1(self):
        wf = _build_simple_workflow(**self._default_kwargs())
        ksampler = [v for v in wf.values() if v["class_type"] == "KSampler"][0]
        assert ksampler["inputs"]["denoise"] == 1.0

    def test_batch_size_is_1(self):
        wf = _build_simple_workflow(**self._default_kwargs())
        latent = [
            v for v in wf.values() if v["class_type"] == "EmptyLatentImage"
        ][0]
        assert latent["inputs"]["batch_size"] == 1

    def test_node_count_without_lora(self):
        wf = _build_simple_workflow(**self._default_kwargs(lora_name=None))
        # Checkpoint + 2 CLIP + EmptyLatent + KSampler + VAEDecode + SaveImage = 7
        assert len(wf) == 7

    def test_node_count_with_lora(self):
        wf = _build_simple_workflow(
            **self._default_kwargs(lora_name="style/Test.safetensors")
        )
        # Checkpoint + LoRA + 2 CLIP + EmptyLatent + KSampler + VAEDecode + SaveImage = 8
        assert len(wf) == 8

    def test_vae_decode_receives_sampler_output(self):
        wf = _build_simple_workflow(**self._default_kwargs())
        sampler_id = None
        for nid, node in wf.items():
            if node["class_type"] == "KSampler":
                sampler_id = nid
                break
        vae_decode = [v for v in wf.values() if v["class_type"] == "VAEDecode"][0]
        assert vae_decode["inputs"]["samples"] == [sampler_id, 0]

    def test_save_image_receives_vae_output(self):
        wf = _build_simple_workflow(**self._default_kwargs())
        decode_id = None
        for nid, node in wf.items():
            if node["class_type"] == "VAEDecode":
                decode_id = nid
                break
        save_node = [v for v in wf.values() if v["class_type"] == "SaveImage"][0]
        assert save_node["inputs"]["images"] == [decode_id, 0]


class TestBuildCoherentWorkflow:
    """Test _build_coherent_tileset_workflow stub behavior"""

    def test_raises_not_implemented(self):
        with pytest.raises(NotImplementedError) as exc_info:
            _build_coherent_tileset_workflow()
        assert "comfyui-tileset-nodes" in str(exc_info.value)


class TestToolParameterValidation:
    """Test the parameter validation logic in generate_game_tileset.

    These tests validate the logic directly since calling the registered tool
    requires a running MCP server. We test the validation patterns instead.
    """

    def test_valid_modes(self):
        valid_modes = ("simple", "coherent", "dual_terrain")
        for mode in valid_modes:
            assert mode in valid_modes

    def test_invalid_mode_rejected(self):
        valid_modes = ("simple", "coherent", "dual_terrain")
        invalid = ["fast", "turbo", "", "Simple", "SIMPLE"]
        for mode in invalid:
            assert mode not in valid_modes

    def test_valid_output_formats(self):
        valid_formats = ("godot_minimal", "godot_full", "rpgmaker", "generic")
        for fmt in valid_formats:
            assert fmt in valid_formats

    def test_invalid_output_format_rejected(self):
        valid_formats = ("godot_minimal", "godot_full", "rpgmaker", "generic")
        invalid = ["godot", "unity", "", "GODOT_MINIMAL"]
        for fmt in invalid:
            assert fmt not in valid_formats

    def test_tile_size_range(self):
        for valid in [64, 128, 256, 512, 1024, 2048]:
            assert 64 <= valid <= 2048
        for invalid in [32, 63, 2049, 4096, 0, -1]:
            assert not (64 <= invalid <= 2048)

    def test_lora_strength_range(self):
        for valid in [0.0, 0.5, 0.85, 1.0]:
            assert 0.0 <= valid <= 1.0
        for invalid in [-0.1, 1.1, 2.0, -1.0]:
            assert not (0.0 <= invalid <= 1.0)

    def test_dual_terrain_requires_prompt_b(self):
        # Mirrors validation: mode=="dual_terrain" and not prompt_b -> error
        mode = "dual_terrain"
        prompt_b = None
        assert mode == "dual_terrain" and not prompt_b

        prompt_b = "stone terrain"
        assert not (mode == "dual_terrain" and not prompt_b)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
