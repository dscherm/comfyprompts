# Berserkr Character Generation Architecture

## 1. Overview

This document defines the architecture for generating consistent character art for the Berserkr Norse fantasy game. The system produces portraits, dialogue busts, and sprite concepts for 10 player classes and 17 NPCs using ComfyUI workflows integrated into the existing comfyui-toolchain monorepo.

**Hardware constraint**: RTX 3070 (8GB VRAM). All pipeline choices are driven by this limit.

**Art style**: 1970s dark fantasy ink illustration — Frank Miller Sin City meets Frank Frazetta. Heavy black ink, extreme noir contrast, selective bold color accents (crimson, amber). This style is already defined in the existing `berserkr.json` workflow.

## 2. Character Inventory

### 2.1 Player Classes (10)

Each class needs a representative portrait and isometric sprite concept. Character appearance varies by player choice, so class art represents the archetype:

| Class | Visual Archetype | Key Visual Elements |
|-------|-----------------|---------------------|
| Berserkr | Massive rage warrior | Bear/wolf pelt, great axe, wild eyes, battle scars |
| Valkyrie | Winged shield-maiden | Swan-feather cloak, spear, round shield, chainmail |
| Vanir Warden | Nature protector | Staff, leather, mistletoe, wild hair, animal motifs |
| Skald | Poet-warrior | Lyre, fine clothes, ink-stained fingers, sword |
| Runecaster | Rune mage | Rune stones, robes, staff, glowing inscriptions |
| Shield Thane | Sworn protector | Large shield, chainmail, oath ring, stoic stance |
| Raider | Sea wolf | Dual weapons, grappling hook, rope, leather, seax |
| Hunter | Bow master | Longbow, camouflage cloak, hunting knife, traps |
| Seer | Prophet/oracle | Crystal ball, robes, distant eyes, ritual knife |
| Thrall Risen | Freed slave | Broken chains, improvised weapons, tattered clothes |

### 2.2 Named NPCs (17)

Each NPC has a `visual_description` field in `npcs.json` that drives prompt generation:

| NPC | Visual Description |
|-----|-------------------|
| Helga One-Eye | Female, middle-aged, muscular build, missing left eye, gray-streaked red hair in braids |
| Grimr (Odin) | Male, elderly, hooded dark blue cloak, one eye visible, long gray beard, ash-wood staff, two ravens |
| Bjorn Ironsides | Male, middle-aged, scarred face, unkempt beard, bloodshot eyes, dented chainmail |
| Leif Steady-Hand | Male, young, earnest face, spear and shield, warm furs over leather armor |
| Frey Silvertongue | Male, middle-aged, well-dressed, calculating eyes, merchant's pack |
| Jarl Erik | Male, elderly, silver hair, fur-trimmed cloak, gold arm-rings, weary but dignified |
| Thorvald Rune-Hammer | Male, elderly, massive arms, burn scars, leather apron, rune-tattooed hands |
| Sigrid the Volva | Female, ancient, white-blind eyes, staff with raven skull, dark robes, bone jewelry |
| Knut Word-Weaver | Male, young, bright eyes, lyre on back, ink-stained fingers, eager expression |
| Ulf the Silent | Male, middle-aged, tall and imposing, scarred throat, fine armor, great axe |
| Astrid Helgasdottir | Female, young, red hair, torn dress, defiant despite fear |
| Sigrun Thorvaldsdottir | Female, young, strong arms, soot-smudged face, dark braided hair, leather apron |
| Dalla Frost-Born | Female, young, pale complexion, dark circles under grey eyes, white robe, trembling hands |
| Ragna Ketilsdottir | Female, middle-aged, gaunt face, wild eyes, torn farm clothes, worn amulet |
| (+ 3 additional NPCs from locations not fully detailed) | |

## 3. Model Selection

### 3.1 Base Model: Flux 1 Dev FP8

**Decision**: Use `flux1-dev-fp8.safetensors` (already installed, confirmed 8GB VRAM compatible)

**Rationale**:
- Already in use by the existing `berserkr.json` workflow — proven to work on this hardware
- FP8 quantization fits in 8GB VRAM with room for additional model components
- Superior prompt following compared to SD1.5/SDXL for complex character descriptions
- The existing Berserkr style prompt already produces excellent results with Flux
- No negative prompt needed (Flux ignores it in practice; the workflow includes one for compatibility but CFG is set to 1.0)

**Rejected alternatives**:
- **SD1.5**: Good VRAM fit but significantly worse quality and prompt adherence. IP-Adapter ecosystem is mature but output quality is a generation behind.
- **SDXL**: The existing `face_id_portrait.json` uses SDXL + IP-Adapter FaceID, but SDXL has worse prompt following than Flux and the FaceID approach requires a reference face photo we don't have for fictional characters.

### 3.2 IP-Adapter: Not Used for Initial Generation

**Decision**: Skip IP-Adapter for the initial character generation pipeline.

**Rationale**:
- IP-Adapter FaceID requires a **reference face photo** — we're generating characters from text descriptions, not cloning real faces
- IP-Adapter (non-FaceID) requires a **reference style image** — we already achieve style consistency through the Berserkr prompt template
- The consistency problem is solved differently here: all characters share the same style prompt prefix, same checkpoint, and fixed sampler settings
- IP-Adapter can be added later for **variant generation** (e.g., generating the same character in different poses/expressions) once we have a base portrait to use as reference

### 3.3 ControlNet: Pose Control via Flux Union ControlNet

**Decision**: Use `flux-dev-controlnet-union.safetensors` (already installed) for pose-controlled variants

**When to use**: After initial portraits are generated, ControlNet enables:
- Generating isometric sprite concepts from a character portrait + pose skeleton
- Creating expression variants (same character, different emotional state)
- Producing action poses for combat sprites

**VRAM note**: The existing `generate_image_controlnet.json` workflow lists `minimum_vram_gb: 10`, which exceeds the 8GB RTX 3070. This workflow will need testing — Flux FP8 + ControlNet may require:
- Reducing resolution from 1024x1024 to 768x768 or 528x528
- Using `--lowvram` or `--medvram` ComfyUI flags
- Generating at lower resolution and upscaling afterward

**Fallback**: If ControlNet + Flux doesn't fit in 8GB, skip ControlNet entirely and rely on prompt-based pose direction (e.g., "three-quarter view", "facing left", "isometric overhead angle").

### 3.4 PromptOptimizer from comfyui-ai-gamedev

**Decision**: Do NOT integrate the PromptOptimizer node.

**Rationale**:
- The PromptOptimizer runs on Ollama (llama3.2) which is available, but it adds complexity for marginal benefit
- Our prompts are already well-structured: a fixed Berserkr style prefix + character-specific descriptions extracted from game data
- Adding an LLM optimization step adds latency (~5-15s per prompt) and non-determinism
- The existing prompt template in `berserkr.meta.json` already produces consistent, high-quality results
- If prompt refinement is needed, it's better done once by a human and baked into the templates

## 4. Art Style Pipeline

### 4.1 Style Prompt Template

The Berserkr style is already defined in `berserkr.meta.json`. The `prompt_template` field contains the full style prefix:

```
Frank Miller Sin City meets Frank Frazetta 1970s fantasy art, {subject},
HEAVY BLACK INK illustration style, extreme high contrast black and white
with selective bold color accents of {color_accent}, stark dramatic noir
shadows and silhouettes, thick aggressive ink brushstrokes and splatter,
Frank Miller comic panel composition, pulp magazine cover art, exaggerated
heroic muscular anatomy like Frazetta, deep chiaroscuro with pools of pure
black shadow, gritty noir atmosphere, psychedelic lurid color bleeding
through the black ink darkness, raw expressive linework, graphic novel
aesthetic, visible ink texture and cross-hatching, romanticism meets noir,
epic swords-and-sorcery mood, NOT photorealistic NOT smooth NOT digital
NOT 3d render
```

### 4.2 Character Prompt Structure

Each character prompt is built by inserting character-specific details into the `{subject}` placeholder:

```
{style_prefix}, {character_description}, {pose_direction}, {framing}
```

Where:
- `style_prefix` = the Berserkr prompt template (fixed for all characters)
- `character_description` = from NPC `visual_description` or class archetype description
- `pose_direction` = "portrait facing viewer" / "three-quarter view" / "isometric angle"
- `framing` = "bust portrait" / "full body" / "waist-up"

### 4.3 Color Accent Strategy

The default color accent is `"deep crimson red and burning amber orange"`. For character variety:

| Character Type | Color Accent |
|---------------|-------------|
| Warriors (Berserkr, Shield Thane, Raider) | Deep crimson red and burning amber orange (default) |
| Magic users (Runecaster, Seer, Volva) | Cold blue and pale silver |
| Nature/divine (Vanir Warden, Valkyrie, Dalla) | Forest green and gold |
| Stealth/guile (Hunter, Thrall Risen, Merchant) | Deep violet and rust orange |
| Neutral/warm (Skald, Helga, Leif) | Warm amber and honey gold |
| Odin/Grimr | Single icy blue-white (his one eye) |

This provides visual variety while maintaining the core ink-noir aesthetic.

## 5. Output Formats for Godot

### 5.1 Asset Types and Sizes

| Asset Type | Resolution | Aspect Ratio | Use in Godot | Count |
|-----------|-----------|-------------|-------------|-------|
| **Dialogue Portrait** | 512x512 | 1:1 | Dialogue UI panel, character info | 27 (10 classes + 17 NPCs) |
| **Dialogue Bust** | 384x512 | 3:4 | Dialogue scene side panel | 17 (NPCs only) |
| **Class Selection Card** | 528x528 | 1:1 | Class picker during character creation | 10 |
| **Sprite Concept** | 528x528 | 1:1 | Reference for manual sprite creation | 27 |

**Why these sizes**:
- 512x512 and 528x528 are native Flux generation sizes that work well on 8GB VRAM (528x528 is already the default in `berserkr.json`)
- Dialogue portraits at 512x512 are large enough for sharp display in the Godot UI but small enough for fast generation
- These are **concept art and portraits**, not final sprite sheets — actual isometric sprites will need manual pixel art or a separate sprite workflow

### 5.2 File Organization in Godot Project

```
D:/Projects/berserkr-godot/assets/sprites/characters/
├── portraits/           # 512x512 dialogue portraits
│   ├── classes/         # berserkr.png, valkyrie.png, ...
│   └── npcs/            # helga_one_eye.png, grimr.png, ...
├── busts/               # 384x512 dialogue busts (NPCs)
│   └── helga_one_eye.png, grimr.png, ...
├── cards/               # 528x528 class selection cards
│   └── berserkr.png, valkyrie.png, ...
└── concepts/            # 528x528 sprite concept reference
    ├── classes/
    └── npcs/
```

### 5.3 File Format

- PNG with transparency where possible (use background removal post-processing)
- Filenames: lowercase snake_case matching the JSON keys (e.g., `innkeeper_helga.png`, `drunk_warrior.png`)
- No alpha channel on initial generation — Flux doesn't generate transparent backgrounds. Background removal is a separate post-processing step if needed.

## 6. Workflow Architecture

### 6.1 New Workflows to Create

Three new parametric workflows, following the existing `workflow.json` + `workflow.meta.json` pattern:

#### Workflow 1: `berserkr_chargen_portrait.json`
- **Purpose**: Generate character portraits (512x512, bust framing)
- **Base**: Fork of existing `berserkr.json` with portrait-specific defaults
- **Parameters**: `character_name`, `character_description`, `color_accent`, `framing`, `seed`
- **Fixed**: Berserkr style prefix auto-prepended, 512x512 resolution, 25 steps, euler sampler

#### Workflow 2: `berserkr_chargen_fullbody.json`
- **Purpose**: Generate full-body character concepts (528x528)
- **Base**: Fork of `berserkr.json` with full-body framing and pose direction
- **Parameters**: `character_name`, `character_description`, `color_accent`, `pose`, `seed`
- **Fixed**: Berserkr style prefix, 528x528, "full body standing pose" default

#### Workflow 3: `berserkr_chargen_card.json`
- **Purpose**: Generate class selection cards with decorative framing
- **Base**: Fork of `berserkr.json` with card-specific framing prompt additions
- **Parameters**: `class_name`, `class_description`, `equipment_list`, `color_accent`, `seed`
- **Additional prompt elements**: "character card illustration, ornate Norse knotwork border, rune inscriptions frame"

### 6.2 Workflow JSON Structure

All three workflows share the same node graph as `berserkr.json` (CheckpointLoaderSimple -> CLIPTextEncode -> EmptySD3LatentImage -> KSampler -> VAEDecode -> SaveImage). The differentiation is in the meta.json sidecar which defines:

- Different `prompt_template` strings with character-specific placeholders
- Different default dimensions
- Different filename prefixes for organized output

### 6.3 Integration with Existing Toolchain

The new workflows integrate with the existing MCP server infrastructure:

1. **Discovery**: The MCP server's `WorkflowManager` auto-discovers all `.json` + `.meta.json` pairs in `workflows/mcp/`
2. **Execution**: Use existing `batch_generate` MCP tool to run multiple characters in sequence
3. **Asset tracking**: Generated images are tracked by `AssetRegistry` with TTL-based cleanup
4. **Style presets**: Register "berserkr" as a style preset in the `StylePresetsManager` (may already exist)

## 7. Batch Generation Strategy

### 7.1 Generation Script

A Python script at `packages/mcp-server/scripts/generate_berserkr_characters.py` that:

1. Reads `classes.json` and `npcs.json` from the Berserkr Godot project
2. Builds prompts from character data using the template system
3. Calls the ComfyUI API via the SDK's `ComfyUIClient`
4. Saves outputs to the Berserkr Godot project's asset directories
5. Generates a manifest of all produced assets

### 7.2 Prompt Construction from Game Data

For NPCs, the prompt is built from the `visual_description` field:

```python
def build_npc_prompt(npc_data: dict, framing: str = "bust portrait") -> str:
    visual = npc_data["visual_description"]
    name = npc_data["name"]
    # Extract personality cues for expression
    personality = npc_data.get("personality", {})
    mood = "stern" if personality.get("aggression", 0) > 0 else "calm"

    return f"{name}, {visual}, {framing}, {mood} expression, Norse fantasy setting"
```

For player classes, the prompt is built from class description + equipment:

```python
def build_class_prompt(class_data: dict, framing: str = "full body") -> str:
    name = class_data["name"]
    desc = class_data["description"]
    equipment = ", ".join(class_data["starting_equipment"][:3])  # Top 3 items

    return f"{name} warrior, {desc}, carrying {equipment}, {framing}, Norse fantasy setting"
```

### 7.3 Execution Order

1. **Phase 1 — NPC Portraits** (17 images): Dialogue portraits at 512x512. These are the highest priority since NPCs appear in dialogue.
2. **Phase 2 — Class Cards** (10 images): Class selection cards at 528x528 for the character creation screen.
3. **Phase 3 — Full-body Concepts** (27 images): Full-body reference art for eventual sprite creation.
4. **Phase 4 — Expression Variants** (optional, ~34 images): 2 expression variants per major NPC for dialogue variety.

Total: ~54-88 images. At ~30-45 seconds per image on RTX 3070 with Flux FP8, expect 30-60 minutes for the full batch.

### 7.4 Seed Strategy

- Use a fixed base seed per character for reproducibility (e.g., hash of character name)
- Generate 3 candidates per character, pick the best manually
- Record chosen seeds in a manifest file for regeneration

## 8. Post-Processing Pipeline

### 8.1 Background Removal (Optional)

If transparent portraits are needed for Godot UI overlays:
- Use `rembg` (runs on CPU, no VRAM cost) as a post-processing step
- Or use ComfyUI's `RemoveBackground` node in a separate workflow
- Only needed for dialogue busts that overlay on scene backgrounds

### 8.2 Downscaling for Sprites

The generated 512x512 / 528x528 concept art is reference material. Actual isometric sprites for the game (likely 64x64 or 128x128 per frame) will need:
- Manual pixel art creation using the generated concepts as reference
- OR a separate pixel art workflow (the `generate_image_pixelart.json` workflow exists but requires 12GB VRAM — exceeds our constraint)

### 8.3 Consistency Verification

After batch generation, a manual review step:
1. Check all characters share the same ink-noir visual style
2. Verify color accents match the assigned palette
3. Confirm no anachronistic elements (modern clothing, etc.)
4. Re-generate any outliers with adjusted prompts or different seeds

## 9. Future Extensions

### 9.1 IP-Adapter for Character Variants

Once base portraits exist, IP-Adapter can be used to generate variants:
- Feed the chosen portrait as a reference image
- Generate expression variants (happy, angry, sad, neutral)
- Generate action poses for combat sprites
- This requires the SDXL-based `face_id_portrait.json` workflow since Flux IP-Adapter support is still maturing

### 9.2 LoRA Fine-tuning

If the batch results are good but not consistent enough:
- Train a LoRA on the best 20-30 generated images to lock the style
- Use the LoRA for all subsequent character generation
- 8GB VRAM is sufficient for LoRA inference (training requires cloud GPU)

### 9.3 3D Upgrade Path via 3D AI Studio (Optional)

For a potential future migration from 2.5D isometric to full 3D, cloud-based text/image-to-3D services bypass the 8GB VRAM constraint entirely. [3D AI Studio](https://3daistudio.com) is one such option evaluated for this project.

**What it provides**:
- Cloud-based text-to-3D and image-to-3D generation (~90 seconds per model)
- Exports GLB, FBX, OBJ — GLB imports natively into Godot 4
- Auto-generated PBR textures, quad-remesh for game-ready topology, AI UV unwrapping
- Multiple AI backends (Meshy, Rodin, Tripo, Hunyuan 3.1 Pro)
- Batch mode: up to 12 image-to-3D conversions at once

**Proposed 2D-to-3D pipeline**:
1. Local ComfyUI generates consistent 2D reference images (the pipeline described in this document)
2. Best references are selected and uploaded to 3D AI Studio
3. Image-to-3D converts the 2D art into textured 3D meshes
4. Export as GLB and import into Godot

**Limitations**:
- No character consistency feature — each 3D generation is independent, so the 2D reference quality matters
- API is early access only (not publicly available yet), so automation requires manual upload or waiting for API access
- Pricing: ~14-29 EUR/month for 1000-3500 credits, or 29 EUR one-time for 2000 credits. Each 3D model costs 25-35 credits. Generating all 27 characters would cost ~675-945 credits (~1 month subscription).

**When to consider this**:
- If the project migrates from 2.5D isometric to full 3D rendering
- If 3D character models are needed for cutscenes or close-up views
- NOT needed for the current 2.5D approach with TileMap + CharacterBody2D sprites

This is purely an optional upgrade path. The primary pipeline remains local ComfyUI for 2D character art.

### 9.4 Creature Art

The same pipeline can generate creature art from `creatures.json` using the same Berserkr style. Creatures (trolls, draugr, frost giants, etc.) would use the same workflow with creature-specific prompts.

### 9.5 Location Art

Scene backgrounds for locations in `locations.json` can use the base `berserkr.json` workflow directly, since it already generates scene-oriented art.

## 10. File Manifest

### New Files to Create

```
comfyui-toolchain/
├── workflows/mcp/
│   ├── berserkr_chargen_portrait.json          # Portrait workflow
│   ├── berserkr_chargen_portrait.meta.json     # Portrait metadata
│   ├── berserkr_chargen_fullbody.json          # Full-body workflow
│   ├── berserkr_chargen_fullbody.meta.json     # Full-body metadata
│   ├── berserkr_chargen_card.json              # Class card workflow
│   └── berserkr_chargen_card.meta.json         # Class card metadata
├── packages/mcp-server/scripts/
│   └── generate_berserkr_characters.py         # Batch generation script
└── docs/
    └── berserkr-chargen-architecture.md        # This document
```

### Directories to Create in Godot Project

```
berserkr-godot/assets/sprites/characters/
├── portraits/classes/
├── portraits/npcs/
├── busts/
├── cards/
└── concepts/classes/
    concepts/npcs/
```

## 11. Dependencies and Prerequisites

### Required (already installed)
- ComfyUI with `flux1-dev-fp8.safetensors` checkpoint
- Python 3.10+ with comfyui-agent-sdk installed
- Ollama with llama3.2 (for Berserkr game, not needed for chargen)

### Required (verify installation)
- `flux-dev-controlnet-union.safetensors` — for future pose-controlled variants
- ComfyUI custom nodes: none beyond base for the portrait/fullbody/card workflows

### Optional
- `rembg` Python package — for background removal post-processing
- `ip-adapter-faceid_sdxl_lora.safetensors` + `sd_xl_base_1.0.safetensors` — for future IP-Adapter variant generation
- InsightFace `antelopev2` detection model — for future FaceID use

## 12. Summary of Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Base model | Flux 1 Dev FP8 | Already working on 8GB VRAM, best prompt following |
| IP-Adapter | Skip for now | No reference photos for fictional characters |
| ControlNet | Future use only | May not fit in 8GB with Flux; needs testing |
| PromptOptimizer | Skip | Adds latency, our templates are already good |
| Art style | Berserkr ink-noir | Already defined and proven in existing workflow |
| Portrait size | 512x512 | Native Flux size, good for Godot dialogue UI |
| Consistency method | Shared style prefix + fixed settings | Simpler and more reliable than IP-Adapter |
| Batch approach | Sequential via SDK ComfyUIClient | Leverages existing infrastructure |
| Sprite creation | Manual from concept art | Automated sprite sheets exceed VRAM budget |
| 3D models | Optional via 3D AI Studio (cloud) | Bypasses VRAM limit; only needed if migrating to full 3D |
