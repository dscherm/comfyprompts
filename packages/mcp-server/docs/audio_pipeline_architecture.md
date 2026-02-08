# Audio Pipeline Architecture & TTS Integration Plan

**Date:** 2026-02-06
**Task:** #29 - Plan TTS-Audio-Suite integration and create speech generation workflows

---

## 1. TTS-Audio-Suite: Installation & Configuration

### Installation

```bash
# Via ComfyUI Manager (recommended - zero manual setup):
# Open ComfyUI -> Manager -> Install Custom Nodes -> Search "TTS-Audio-Suite" -> Install

# Via git (manual):
cd D:\Projects\ComfyUI\custom_nodes
git clone https://github.com/diodiogod/TTS-Audio-Suite.git
cd TTS-Audio-Suite
pip install -r requirements.txt
```

### Model Storage

All models auto-download to `ComfyUI/models/TTS/[engine_name]/` on first use.

| Engine | Model Size | VRAM (inference) | Auto-Download |
|--------|-----------|------------------|---------------|
| F5-TTS | ~1.2GB/language | ~4GB | Yes |
| ChatterBox | ~4.3GB | ~4-6GB | Yes |
| ChatterBox 23-Lang | ~4.3GB | ~4-6GB | Yes |
| Higgs Audio 2 | ~9GB | ~6-8GB | Yes |
| VibeVoice (1.5B) | ~5.4GB | ~4-6GB | Yes |
| VibeVoice (7B) | ~18GB | ~12GB+ | Yes |
| IndexTTS-2 | ~3GB | ~4GB | Yes |
| CosyVoice 3 | ~5.4GB | ~4-6GB | Yes |
| Qwen3-TTS | ~3-6GB | ~4-6GB | Yes |
| Step Audio EditX | ~4GB | ~4-6GB | Yes |
| RVC models | 100-300MB each | ~2GB | Manual |

### RTX 3070 8GB Compatibility

| Engine | Fits in 8GB? | Notes |
|--------|-------------|-------|
| F5-TTS | YES | Runs on 6GB VRAM. Best starting choice. |
| ChatterBox | YES | ~4-6GB with bf16 precision |
| IndexTTS-2 | YES | Lightweight |
| CosyVoice 3 | YES | With bf16 |
| Qwen3-TTS | TIGHT | Enable `unload_model_after_generate` |
| Higgs Audio 2 | TIGHT | Enable `unload_model_after_generate`, use bf16 |
| VibeVoice 1.5B | YES | With bf16 |
| VibeVoice 7B | NO | Needs 12GB+ |
| RVC | YES | Very lightweight |

**Key setting for 8GB cards:** Always set `unload_model_after_generate: true` and `precision: bf16` in engine nodes. This frees VRAM between generations so other models (image, video, 3D) can run.

### Node Reference

| Node Name | Purpose | Key Inputs | Output |
|-----------|---------|------------|--------|
| `TTS Text` | Main TTS generation | engine, text, character_voice | AUDIO |
| `TTS SRT` | Subtitle-timed TTS | engine, srt_text, voices | AUDIO |
| `F5 TTS Engine` | Configure F5-TTS | model, device, precision | ENGINE |
| `ChatterBox TTS Engine` | Configure ChatterBox | device, precision | ENGINE |
| `ChatterBox Official 23-Lang Engine` | 23-language ChatterBox | device, precision, language | ENGINE |
| `Higgs Audio 2 Engine` | Configure Higgs | device, precision | ENGINE |
| `VibeVoice Engine` | Configure VibeVoice | model_variant, device | ENGINE |
| `IndexTTS-2 Engine` | Configure IndexTTS-2 | device, precision | ENGINE |
| `RVC Engine` | Configure RVC | device | ENGINE |
| `Character Voices` | Voice reference loader | voice_name, voices_dir | VOICE |
| `Load RVC Character Model` | RVC model loader | model_name | RVC_MODEL |
| `Voice Changer` | RVC voice conversion | rvc_model, audio, pitch_shift | AUDIO |
| `Audio Wave Analyzer` | Waveform analysis | audio | ANALYSIS |
| `Silent Speech Analyzer` | Mouth movement detection | video | ANALYSIS |
| `ASR Transcribe` | Speech-to-text | audio | STRING |
| `Phoneme Text Normalizer` | Normalize text for TTS | text | STRING |
| `IndexTTS-2 Emotion Vectors` | Emotion control | emotion_type | VECTORS |

---

## 2. Stable Audio Open: Sound Effects

### Installation

No custom nodes needed - uses native ComfyUI nodes.

### Model Download

```
# Download from HuggingFace:
# https://huggingface.co/stabilityai/stable-audio-open-1.0

# Place files:
# stable_audio_open_1.0.safetensors -> D:\Projects\ComfyUI\models\checkpoints\
# t5_base.safetensors -> D:\Projects\ComfyUI\models\text_encoders\
```

**Total download:** ~2.5GB
**VRAM:** ~4GB (fits RTX 3070 easily)

### Workflow Pipeline

```
CheckpointLoaderSimple (stable_audio_open_1.0)
    |
    v
CLIPTextEncode (positive prompt) --+
CLIPTextEncode (negative prompt) --+--> ConditioningStableAudio
                                          |
EmptyLatentAudio (seconds) --------+--> KSampler
                                          |
                                          v
                                    VAEDecodeAudio --> SaveAudioMP3
```

### Prompt Engineering for SFX

**Good prompts:**
- "Footsteps on wooden floor, slow pace, indoor, quiet room"
- "Thunder rumbling in the distance, heavy rain, storm ambience"
- "Sword clash, metal on metal, medieval battle sounds"
- "Car engine starting, idle, then accelerating away"

**Negative prompts to include:**
- "low quality, distorted, noise, glitch, hiss, hum, music" (for pure SFX)
- "vocals, speech, voice" (if you want only sound effects)

---

## 3. Wav2Lip: Local Lip Sync

### Installation

```bash
cd D:\Projects\ComfyUI\custom_nodes
git clone https://github.com/ShmuelRonen/ComfyUI_wav2lip.git
cd ComfyUI_wav2lip
pip install -r requirements.txt
```

### Model Download

Download `wav2lip_gan.pth` from HuggingFace and place in:
`custom_nodes/ComfyUI_wav2lip/Wav2Lip/checkpoints/wav2lip_gan.pth`

The face detection model (`s3fd.pth`) auto-downloads on first use.

**VRAM:** ~2-4GB (very lightweight)

### Node Interface

| Input | Type | Description |
|-------|------|-------------|
| images | IMAGE | Video frames (from VHS_LoadVideo or image generation) |
| audio | AUDIO | Speech audio (from TTS or loaded file) |
| mode | STRING | "sequential" or "repetitive" |
| face_detect_batch | INT | Batch size for face detection (default: 8) |

| Output | Type | Description |
|--------|------|-------------|
| images | IMAGE | Lip-synced video frames |
| audio | AUDIO | Pass-through audio |

**Also requires:** ComfyUI-VideoHelperSuite for `VHS_LoadVideo` and `VHS_VideoCombine` nodes.

---

## 4. MMAudio: Video to Audio

### Installation

```bash
cd D:\Projects\ComfyUI\custom_nodes
git clone https://github.com/kijai/ComfyUI-MMAudio.git
pip install -r ComfyUI-MMAudio/requirements.txt
```

### Model Download

All models go in `D:\Projects\ComfyUI\models\mmaudio\`:

| File | Size | Source |
|------|------|--------|
| `mmaudio_44k.safetensors` | ~800MB | HuggingFace |
| `vae_44k.safetensors` | ~200MB | HuggingFace |
| `synchformer.safetensors` | ~400MB | HuggingFace |
| `apple_DFN5B-CLIP-ViT-H-14-384_fp16.safetensors` | ~600MB | HuggingFace |
| BigVGAN vocoder | ~100MB | Auto-downloads |

**Total:** ~2GB
**VRAM:** ~4-6GB for 44kHz mode (video under 1 minute on RTX 3070)

### Node Pipeline

```
MMAudioModelLoader (mmaudio_44k) ----+
MMAudioVoCoderLoader -----------------+--> MMAudioSampler --> SaveAudioMP3
MMAudioFeatureUtilsLoader (44k mode) -+         ^
VHS_LoadVideo (input video) ----------+         |
                                       prompt --+
```

---

## 5. New MCP Tools Required

### Tool Registration Changes

File: `D:\Projects\comfyui-mcp-server\tools\generation.py`

The namespace detection (line ~74) needs updating to recognize new audio workflows:

```python
# Current:
if definition.workflow_id == "generate_song":
    namespace = "audio"

# Needs to become:
if definition.workflow_id in ("generate_song", "generate_speech", "generate_sfx", "voice_clone", "video_to_audio"):
    namespace = "audio"
elif definition.workflow_id == "lip_sync":
    namespace = "video"  # lip_sync outputs video
```

### New MCP Tool Definitions (Auto-Registered from Workflow JSONs)

| Tool Name | Workflow File | Namespace | Description |
|-----------|-------------|-----------|-------------|
| `generate_speech` | `generate_speech.json` | audio | Text-to-speech via F5-TTS |
| `generate_sfx` | `generate_sfx.json` | audio | Sound effects via Stable Audio Open |
| `voice_clone` | `voice_clone.json` | audio | TTS + RVC voice cloning |
| `lip_sync` | `lip_sync.json` | video | Wav2Lip video lip sync |
| `video_to_audio` | `video_to_audio.json` | audio | MMAudio video-to-audio |

### Existing Tool (Already Working)

| Tool Name | Workflow File | Namespace | Description |
|-----------|-------------|-----------|-------------|
| `generate_song` | `generate_song.json` | audio | AceStep music generation |

### Output Key Updates

File: `D:\Projects\comfyui-mcp-server\managers\workflow_manager.py`

The `AUDIO_OUTPUT_KEYS` already includes `("audio", "audios", "sound", "files")` which should cover all new workflows.

### Placeholder Description Updates

Add to `PLACEHOLDER_DESCRIPTIONS` in `workflow_manager.py`:

```python
# TTS parameters
"text": "Text to convert to speech. Supports [CharacterName] syntax for multi-speaker.",
"voice_reference": "Voice reference name. Place .wav + .txt pair in voices directory. Use 'default' for engine default.",
"rvc_model": "RVC voice model filename (.pth). Must be pre-trained on target voice.",
"pitch_shift": "Pitch adjustment in semitones. 0 = no change. Default: 0.",
# SFX parameters
"negative_prompt": "What to avoid in generation. Default: 'low quality, distorted'.",
# Video-to-audio parameters
"video_path": "Path to input video file.",
"audio_path": "Path to input audio file.",
"face_detect_batch": "Face detection batch size. Higher = faster. Default: 8.",
"duration": "Audio duration in seconds.",
```

---

## 6. End-to-End Pipeline Architecture

### Pipeline A: Talking Head (Image + Speech -> Animated Video)

```
[User provides: text, character description]
        |
        v
generate_image (portrait) ---------> generate_speech (text)
        |                                    |
        v                                    v
   Static image                        Speech audio
        |                                    |
        +------------------------------------+
        |                                    |
        v                                    v
              lip_sync (image + audio)
                       |
                       v
               Talking head video
                       |
               + generate_sfx (ambient)
                       |
                       v
              Final video with audio
```

### Pipeline B: Video Post-Production (Video -> Audio)

```
[User provides: generated video]
        |
        v
video_to_audio (MMAudio)
        |
        v
Matching SFX/ambient audio
        +
Original video
        |
        v
  AudioMerge / AudioConcat (native nodes)
        |
        v
  Final video with matched audio
```

### Pipeline C: Multi-Character Dialogue

```
[User provides: script with character tags]
        |
        v
generate_speech (with [Alice] and [Bob] tags)
        |
        v
Speech audio with character switching
        |
  [Optional: voice_clone per character]
        |
        v
  Character-specific voiced audio
```

### Pipeline D: Music Video

```
generate_song (AceStep) -----------> FL_Audio_BPM_Analyzer
        |                                    |
        v                                    v
  Generated song                     BPM/beat data
                                             |
                              FL_Audio_Reactive_* nodes
                                             |
                                             v
                              Audio-reactive image/video gen
```

---

## 7. Files Created

### Workflow JSONs (in `D:\Projects\comfyui-mcp-server\workflows\`)

| File | Purpose | Custom Nodes Required |
|------|---------|----------------------|
| `generate_speech.json` | Text-to-speech | TTS-Audio-Suite |
| `generate_speech.meta.json` | Metadata/validation | - |
| `generate_sfx.json` | Sound effects generation | None (native) |
| `generate_sfx.meta.json` | Metadata/validation | - |
| `voice_clone.json` | Voice cloning (TTS+RVC) | TTS-Audio-Suite |
| `voice_clone.meta.json` | Metadata/validation | - |
| `lip_sync.json` | Video lip sync | ComfyUI_wav2lip, VideoHelperSuite |
| `lip_sync.meta.json` | Metadata/validation | - |
| `video_to_audio.json` | Video-to-audio | ComfyUI-MMAudio, VideoHelperSuite |
| `video_to_audio.meta.json` | Metadata/validation | - |

### Documentation (in `D:\Projects\comfyui-mcp-server\docs\`)

| File | Content |
|------|---------|
| `speech_audio_audit_report.md` | Original audit (from Task #5) |
| `audio_pipeline_architecture.md` | This document - full integration plan |

---

## 8. Implementation Priority & Dependencies

### Phase 1: Immediate (No new installs needed)
1. Download Stable Audio Open model files
2. `generate_sfx` workflow is ready to use with native nodes

### Phase 2: Core TTS (Install TTS-Audio-Suite)
1. Install TTS-Audio-Suite via ComfyUI Manager
2. `generate_speech` workflow becomes available
3. `voice_clone` workflow becomes available (if RVC models added)
4. Update `generation.py` namespace detection

### Phase 3: Lip Sync (Install Wav2Lip)
1. Install ComfyUI_wav2lip + ComfyUI-VideoHelperSuite
2. Download wav2lip_gan.pth model
3. `lip_sync` workflow becomes available

### Phase 4: Video-to-Audio (Install MMAudio)
1. Install ComfyUI-MMAudio
2. Download MMAudio model files (~2GB)
3. `video_to_audio` workflow becomes available

### Code Changes Needed (MCP Server)
1. **`tools/generation.py`**: Add new workflow IDs to namespace detection
2. **`managers/workflow_manager.py`**: Add new placeholder descriptions
3. **`config.py` (prompter)**: Add `generate_speech`, `generate_sfx`, etc. to WORKFLOWS dict

---

## 9. VRAM Budget (RTX 3070 8GB - Sequential Execution)

| Pipeline Step | VRAM | Can Chain? |
|--------------|------|-----------|
| generate_image (FLUX fp8) | ~6-8GB | Must unload before audio |
| generate_speech (F5-TTS bf16) | ~4GB | Yes, after image unloads |
| generate_sfx (Stable Audio) | ~4GB | Yes, after image unloads |
| lip_sync (Wav2Lip) | ~2-4GB | Yes, after TTS unloads |
| generate_song (AceStep) | ~6GB | Must run alone |
| video_to_audio (MMAudio) | ~4-6GB | Yes, after image unloads |

**Rule:** Run audio workflows AFTER image/video generation completes. The `unload_model_after_generate: true` flag in TTS engines ensures cleanup between steps.
