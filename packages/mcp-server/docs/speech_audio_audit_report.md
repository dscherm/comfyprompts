# Speech & Audio Workflow Audit Report

**Date:** 2026-02-06
**Researcher:** Speech & Audio Workflow Agent

---

## 1. Current State: Existing Audio Capabilities

### 1.1 Built-in ComfyUI Audio Nodes (Native)

ComfyUI ships with comprehensive audio utility nodes in `comfy_extras/nodes_audio.py`:

| Node | Function |
|------|----------|
| `LoadAudio` | Load audio files (supports audio & video containers) |
| `RecordAudio` | Microphone input capture |
| `SaveAudio` (FLAC) | Export audio as FLAC |
| `SaveAudioMP3` | Export audio as MP3 (V0, 128k, 320k) |
| `SaveAudioOpus` | Export audio as Opus (64k-320k) |
| `PreviewAudio` | In-browser audio playback |
| `VAEEncodeAudio` | Encode audio to latent space |
| `VAEDecodeAudio` | Decode latents to audio |
| `EmptyLatentAudio` | Create blank audio latent (for Stable Audio) |
| `TrimAudioDuration` | Cut audio to time range |
| `SplitAudioChannels` | Stereo to mono L/R split |
| `JoinAudioChannels` | Mono L/R to stereo |
| `AudioConcat` | Concatenate two audio clips |
| `AudioMerge` | Overlay/mix two audio tracks (add, mean, subtract, multiply) |
| `AudioAdjustVolume` | Volume adjustment in dB |
| `EmptyAudio` | Generate silence of specified duration |
| `ConditioningStableAudio` | Conditioning for Stable Audio models |

### 1.2 AceStep Song Generation (Native)

Located in `comfy_extras/nodes_ace.py`:

| Node | Function |
|------|----------|
| `TextEncodeAceStepAudio` | Encode tags + lyrics for music generation |
| `EmptyAceStepLatentAudio` | Create empty latent for AceStep (up to 1000s) |

**Existing Workflow:** `workflows/generate_song.json`
- Model: `ace_step_v1_3.5b.safetensors`
- Parameters: `PARAM_TAGS`, `PARAM_LYRICS`, `PARAM_FLOAT_LYRICS_STRENGTH`, `PARAM_INT_SEED`, `PARAM_INT_STEPS`, `PARAM_FLOAT_CFG`, `PARAM_INT_SECONDS`
- Output: MP3 via SaveAudioMP3
- MCP integration: Registered as `generate_song` tool with `audio` namespace

### 1.3 LTXV Audio (Native - Video Audio Track)

Located in `comfy_extras/nodes_lt_audio.py`:

| Node | Function |
|------|----------|
| `LTXVAudioVAELoader` | Load audio VAE checkpoint |
| `LTXVAudioVAEEncode` | Encode audio for LTXV pipeline |
| `LTXVAudioVAEDecode` | Decode audio latents |
| `LTXVEmptyLatentAudio` | Create empty audio latent synced to video frames |
| `LTXAVTextEncoderLoader` | Load text encoder (Gemma 3 12B) for audio-visual |

This supports audio generation synced to LTXV video generation.

### 1.4 Audio Encoder (Native)

Located in `comfy_extras/nodes_audio_encoder.py`:
- `AudioEncoderLoader` - Load audio encoder models
- `AudioEncoderEncode` - Encode audio for conditioning
- **Note:** `audio_encoders` model directory exists but is empty (no models installed)

### 1.5 Fill-Nodes Audio (Custom Node - Installed)

Package: `comfyui_fill-nodes` (already installed)

**Audio Processing:**
- `FL_Audio_Separation` - Stem separation (bass, drums, other, vocals) using Hybrid Demucs
- `FL_Audio_BPM_Analyzer` - BPM detection
- `FL_Audio_Beat_Visualizer` - Beat visualization
- `FL_Audio_Crop` - Audio cropping
- `FL_Audio_Drum_Detector` - Drum detection
- `FL_Audio_Envelope_Visualizer` - Envelope visualization
- `FL_Audio_Segment_Extractor` - Segment extraction
- `FL_Audio_Shot_Iterator` - Shot-based iteration
- `FL_Audio_Music_Video_Sequencer` - Music video sequencing

**Audio-Reactive Nodes:**
- `FL_Audio_Reactive_Scale` / `Speed` / `Envelope` / `Saturation` / `Brightness` / `Edge_Glow`

**API-Based Lip Sync (Installed):**
- `FL_Fal_Pixverse_LipSync` - Lip sync via Fal.ai Pixverse API (requires API key, cloud-based)
- `FL_Hedra_API` - Talking head generation via Hedra API (requires API key, cloud-based)

---

## 2. Research: Available ComfyUI TTS Custom Nodes

### 2.1 TTS-Audio-Suite (RECOMMENDED - Best All-In-One)

**Repository:** [diodiogod/TTS-Audio-Suite](https://github.com/diodiogod/TTS-Audio-Suite)
**Status:** Actively maintained, v4.6.0+, Python 3.13 support

**Supported Engines:**
| Engine | Type | Voice Cloning | Languages | Notes |
|--------|------|--------------|-----------|-------|
| F5-TTS | Local TTS | Yes (zero-shot) | Multi | High quality, reference audio based |
| Chatterbox | Local TTS | Yes | 23 languages | ResembleAI, multilingual |
| IndexTTS-2 | Local TTS | Yes | Multi | Fast inference |
| CosyVoice 3 | Local TTS | Yes | Multi | Alibaba FunAudioLLM |
| Qwen3-TTS | Local TTS | Yes (voice design) | Multi | Alibaba Qwen family |
| Step Audio EditX | Local TTS | Yes | Multi | Step Audio system |
| Higgs Audio 2 | Local TTS | Yes | Multi | Latest addition |
| VibeVoice | Local TTS | Yes | Multi | Microsoft engine, long-form audio |
| RVC | Voice Conversion | Yes (trained) | Any | Real-Time Voice Conversion |

**Key Features:**
- Unlimited text length with smart chunking
- SRT timing integration for dubbing
- Character switching syntax `[CharacterName]`
- Intelligent caching
- Emotion control
- Auto-installs from ComfyUI Manager (zero manual setup)
- Unified `TTS Text` and `Voice Changer` nodes

### 2.2 ComfyUI-F5-TTS (Standalone)

**Repository:** [niknah/ComfyUI-F5-TTS](https://github.com/niknah/ComfyUI-F5-TTS)
**Type:** Zero-shot voice cloning TTS
**How it works:** Provide a .wav reference audio + .txt transcript, generates speech matching that voice
**Best for:** Simple voice cloning without needing a full suite

### 2.3 ComfyUI-FishSpeech

**Repository:** [AIFSH/ComfyUI-FishSpeech](https://github.com/AIFSH/ComfyUI-FishSpeech)
**Type:** High-quality TTS with voice cloning
**Features:** Reference audio path for voice guidance, auto-downloads from HuggingFace
**Best for:** High naturalness speech, multilingual

### 2.4 CosyVoice-ComfyUI

**Repository:** [AIFSH/CosyVoice-ComfyUI](https://github.com/AIFSH/CosyVoice-ComfyUI)
**Type:** TTS + cross-lingual voice cloning
**Modes:** Zero-shot TTS, cross-lingual cloning, instruction-based TTS
**Best for:** Cross-language dubbing

### 2.5 ComfyUI-XTTS

**Repository:** [AIFSH/ComfyUI-XTTS](https://github.com/AIFSH/ComfyUI-XTTS)
**Type:** Coqui TTS XTTS module
**Languages:** 17 languages
**Best for:** Broad language support voice cloning

### 2.6 ComfyUI-ChatTTS

**Type:** High-quality controllable TTS
**Best for:** Fine-grained control over speech prosody and emotion

### 2.7 MaskGCT-ComfyUI

**Type:** Zero-shot TTS using masked generative codec transformer
**Best for:** Zero-shot scenarios without training

### 2.8 ComfyUI-VoxCPM

**Repository:** [wildminder/ComfyUI-VoxCPM](https://github.com/wildminder/ComfyUI-VoxCPM)
**Type:** Tokenizer-free TTS on MiniCPM-4 backbone
**Best for:** Highly expressive speech, zero-shot voice cloning

### 2.9 ComfyUI-QwenTTS

**Repository:** [1038lab/ComfyUI-QwenTTS](https://github.com/1038lab/ComfyUI-QwenTTS)
**Type:** Qwen3-TTS based speech, voice cloning, and voice design
**Best for:** Voice design (creating new voices from descriptions)

---

## 3. Research: Sound Effects Generation

### 3.1 Stable Audio (Native ComfyUI Support)

ComfyUI has built-in support for Stable Audio models:
- `EmptyLatentAudio` + `ConditioningStableAudio` + standard KSampler pipeline
- Can generate music AND sound effects from text prompts
- **Stable Audio Open 1.0:** Local model, open source
- **Stable Audio 2.5:** API-based via partner node (enterprise quality, up to 3min in <2s)

### 3.2 ComfyUI Sound Lab

**Repository:** [MixLabPro/comfyui-sound-lab](https://github.com/MixLabPro/comfyui-sound-lab)
- MusicGen integration (Meta's music generation)
- Stable Audio integration
- Sound design focused

### 3.3 ComfyUI-StableAudioX (AudioX)

**Repository:** [lum3on/ComfyUI-StableAudioX](https://github.com/lum3on/ComfyUI-StableAudioX)
- AudioX model integration
- Text-to-audio and video-to-audio synthesis
- High quality synthesis

### 3.4 MMAudio (Video-to-Audio)

- Generates matching audio/sound effects for video content
- AI audio synchronization
- Useful for adding SFX to generated videos

### 3.5 DiffRhythm

- Full-length song generation
- Alternative to AceStep for music creation

---

## 4. Research: Voice Cloning

### 4.1 RVC (Real-Time Voice Conversion)

- Available in TTS-Audio-Suite
- Also standalone: Comfy-RVC with training node (`RVCTrainModelNode`)
- Best quality with trained model on target voice
- Works as post-processing on any TTS output

### 4.2 Zero-Shot Cloning Options

| Tool | Quality | Speed | Setup Complexity |
|------|---------|-------|-----------------|
| F5-TTS | High | Medium | Low (reference audio only) |
| XTTS | Good | Fast | Low |
| CosyVoice | High | Medium | Medium |
| Fish Speech | High | Medium | Low |
| VoxCPM | High | Medium | Low |
| Chatterbox | High | Fast | Low |

---

## 5. Research: Lip Sync

### 5.1 Local/Open-Source Options

| Tool | Type | Quality | Speed | ComfyUI Node |
|------|------|---------|-------|-------------|
| Wav2Lip | GAN-based | Good | Fast | [ComfyUI_wav2lip](https://github.com/ShmuelRonen/ComfyUI_wav2lip) |
| SadTalker | Image animation | Good | Medium | Available via custom nodes |
| MuseTalk | Neural | High (30+ FPS) | Fast | Tencent model |
| LatentSync | Latent diffusion | High | Medium | [LatentSync ComfyUI](https://learn.thinkdiffusion.com/seamless-lip-sync-create-stunning-videos-with-latentsync/) |
| LivePortrait | Portrait animation | Premium | Medium | Various custom nodes |

### 5.2 API-Based (Already Installed)

| Tool | Provider | Requires |
|------|----------|----------|
| FL_Fal_Pixverse_LipSync | Fal.ai | API key |
| FL_Hedra_API | Hedra | API key |

---

## 6. Gap Analysis

### What We Have
- Song/music generation (AceStep) -- working workflow with MCP integration
- Audio utilities (load, save, trim, mix, concat, split, volume)
- Audio stem separation (Demucs via fill-nodes)
- Audio-reactive animation tools
- API-based lip sync (Pixverse, Hedra)
- LTXV audio-video sync nodes

### What We're Missing
1. **Text-to-Speech (TTS)** -- No local TTS capability at all
2. **Voice Cloning** -- No local voice cloning
3. **Sound Effects Generation** -- No text-to-SFX workflow (Stable Audio model not downloaded)
4. **Local Lip Sync** -- No local lip sync (only cloud API options)
5. **Voice Conversion (RVC)** -- Not installed
6. **Video-to-Audio** -- No MMAudio or similar
7. **Audio Upscaling/Enhancement** -- No dedicated upscaling

---

## 7. Recommendations: Priority Implementation Order

### Priority 1: TTS-Audio-Suite (HIGH - Install First)

**Why:** Single install gives access to 8+ TTS engines, voice cloning, RVC voice conversion, SRT timing, and character switching. Most comprehensive solution with zero-config setup via ComfyUI Manager.

**Action Items:**
1. Install `TTS-Audio-Suite` via ComfyUI Manager
2. Create `generate_speech.json` workflow with `PARAM_TEXT`, `PARAM_ENGINE`, `PARAM_VOICE_REFERENCE`
3. Create `generate_speech.meta.json` validation file
4. Register as `generate_speech` MCP tool with `audio` namespace
5. Create `voice_clone.json` workflow for dedicated cloning tasks
6. Test with F5-TTS engine first (best quality/ease balance)

**Estimated VRAM:** 4-8GB depending on engine

### Priority 2: Stable Audio Open for Sound Effects (HIGH)

**Why:** Native ComfyUI support already exists, just needs model download and workflow creation.

**Action Items:**
1. Download Stable Audio Open 1.0 model to `models/checkpoints/`
2. Create `generate_sfx.json` workflow using `EmptyLatentAudio` + `ConditioningStableAudio` pipeline
3. Create `generate_sfx.meta.json`
4. Register as `generate_sfx` MCP tool with `audio` namespace
5. Also create `generate_ambient.json` for longer ambient/environmental audio

**Estimated VRAM:** ~4GB

### Priority 3: Wav2Lip Local Lip Sync (MEDIUM)

**Why:** Free, local, no API key needed. Industry standard for lip sync.

**Action Items:**
1. Install `ComfyUI_wav2lip` custom node
2. Download Wav2Lip model weights
3. Create `lip_sync.json` workflow: video input + audio input -> synced output
4. Create `lip_sync.meta.json`
5. Register as `lip_sync` MCP tool

**Estimated VRAM:** ~2-4GB

### Priority 4: MMAudio Video-to-Audio (MEDIUM)

**Why:** Completes the video pipeline by auto-generating matching audio for generated videos.

**Action Items:**
1. Install MMAudio ComfyUI node
2. Create `video_to_audio.json` workflow
3. Integrate with video generation pipeline (chain after `generate_video`)

### Priority 5: ComfyUI-F5-TTS Standalone (LOW - Alternative)

**Why:** Lighter weight alternative if TTS-Audio-Suite is too heavy. Single engine, simple setup.

**Action Items:**
1. Install `ComfyUI-F5-TTS`
2. Add reference voice .wav files to ComfyUI input folder
3. Create simple TTS workflow

### Priority 6: Audio Enhancement / Upscaling (LOW)

**Why:** Post-processing quality improvement for generated audio.

**Action Items:**
1. Research AudioSR or similar audio upscaling models
2. Create enhancement workflow to chain after TTS output

---

## 8. Integration Architecture

### Recommended MCP Tool Registration

```
generate_speech     -> TTS-Audio-Suite workflow (text -> speech audio)
generate_sfx        -> Stable Audio workflow (text -> sound effect)
generate_song       -> AceStep workflow (already exists)
voice_clone         -> TTS-Audio-Suite + RVC workflow
lip_sync            -> Wav2Lip workflow (video + audio -> synced video)
video_to_audio      -> MMAudio workflow (video -> matching audio)
separate_audio      -> Demucs stem separation (already available via fill-nodes)
```

### End-to-End Pipeline Example

```
Text Prompt
    |
    v
generate_image (portrait) --> generate_speech (TTS) --> lip_sync (Wav2Lip)
                                                            |
                                                            v
                                                     Talking Head Video
                                                            |
                                                     + generate_sfx (ambient)
                                                            |
                                                            v
                                                     Final Video with Audio
```

### Config.py Updates Needed

Add to `config.py` WORKFLOWS dict:
- `generate_speech.json` entry with type `"audio_tts"`
- `generate_sfx.json` entry with type `"audio_sfx"`
- `lip_sync.json` entry with type `"lip_sync"`

Add to MODEL_FOLDERS:
- `"audio_encoders"` path already exists at `C:\ComfyUI\models\audio_encoders`
- TTS models will be auto-downloaded by TTS-Audio-Suite

---

## 9. Hardware Considerations

| Workflow | VRAM Required | Can Run on RTX 3070 (8GB)? |
|----------|--------------|---------------------------|
| AceStep song generation | ~6GB | Yes |
| TTS (F5-TTS) | ~4-6GB | Yes |
| TTS (Qwen3-TTS) | ~8GB | Tight, may need offloading |
| Stable Audio Open | ~4GB | Yes |
| Wav2Lip | ~2-4GB | Yes |
| RVC voice conversion | ~2-4GB | Yes |
| MMAudio | ~4-6GB | Yes |

**Note:** Running TTS + image generation simultaneously may exceed 8GB VRAM. Recommend sequential pipeline execution.

---

## 10. Summary

The current setup has strong music generation (AceStep) and audio utility capabilities but completely lacks text-to-speech, sound effects generation, and local lip sync. The **TTS-Audio-Suite** is the single most impactful install, providing 8+ TTS engines, voice cloning, and RVC in one package. Combined with Stable Audio Open for SFX and Wav2Lip for lip sync, this would create a comprehensive audio pipeline integrated with the existing MCP server architecture.
