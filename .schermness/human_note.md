# Human Note

Tasks 1-3 are DONE. Mark them passes: true if not already.

Task 4 (Map ComfyUI) — here's the info you need. DO NOT try to access C:\Users\Teacher\ComfyUI directly; use this data:

## ComfyUI Installation: C:\Users\Teacher\ComfyUI

- **Version:** 0.16.4
- **Checkpoints:** 512-inpainting-ema.safetensors, dreamshaper_8.safetensors, v1-5-pruned-emaonly-fp16.safetensors, v1-5-pruned-emaonly.safetensors
- **LoRAs:** blindbox_V1Mix.safetensors
- **ControlNets:** NONE installed (empty)
- **VAE:** ae.safetensors
- **Custom nodes:** NONE installed (only example_node.py.example and websocket_image_save.py)
- **Output directory:** default (ComfyUI/output/)
- **COMFYUI_OUTPUT_ROOT env var:** NOT SET

## What workflows reference
Check workflows/mcp/*.json for PARAM_CHECKPOINT defaults — they may reference models not installed.
ControlNet workflows will NOT work until controlnet models are downloaded.

## After completing Task 4
Proceed to Task 5+ — you can write code and tests even if ComfyUI isn't running.
Use mocked tests for anything requiring a live ComfyUI connection.
