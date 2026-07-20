---
title: The default HF downloader stalls on large gated models — use HF_HUB_ENABLE_HF_TRANSFER=1
severity: medium
tags: [huggingface, download, hf_transfer, gated, flux, kontext, training]
source: hand-authored
created: 2026-07-20
project: comfyui-toolchain
---

## Symptom

Pulling the gated ~24GB `black-forest-labs/FLUX.1-Kontext-dev` (via ai-toolkit's
implicit `snapshot_download`) got to ~22GB then **stalled**: a single ~9GB
transformer-shard `.incomplete` blob grew 0 KB in 30s, the python process sat at
0% CPU (waiting on the network), and the training could not start. Earlier it had
managed ~360 MB/min, then collapsed to ~17 MB/min and finally froze.

## Root cause

The default `huggingface_hub` HTTP downloader is a single-stream fetch that
degrades/stalls on very large files over a flaky connection, with no automatic
recovery. It silently blocks the whole training start.

## Mitigation

1. **Enable the rust parallel downloader:** set `HF_HUB_ENABLE_HF_TRANSFER=1`
   (the `hf_transfer` package is already in the ai-toolkit venv). It restored
   ~500 MB/min and is stall-resistant.
2. **Pre-download explicitly** rather than relying on the trainer's implicit pull,
   and restrict to what's needed:
   ```python
   snapshot_download("black-forest-labs/FLUX.1-Kontext-dev",
       cache_dir="E:/ai-training/hf-cache",
       allow_patterns=["model_index.json","transformer/*","text_encoder/*",
                       "text_encoder_2/*","tokenizer/*","tokenizer_2/*",
                       "vae/*","scheduler/*"], max_workers=8)
   ```
   (skips the redundant single-file + onnx). Then relaunch training against the
   cache (`HF_HUB_CACHE=E:/ai-training/hf-cache`) — it goes straight to stepping.
3. **Verify gated access before committing to a long run:** a HEAD on a repo file
   with the token from `~/.cache/huggingface/token` — `200` = terms accepted,
   `401/403` = the user must accept them on the model page (their action).
4. Killing a stalled download is safe; `snapshot_download` discards the bad
   `.incomplete` and re-fetches. Big files live on E: (C:/D: near-full).
