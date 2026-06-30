# dissonant_style — eval (DS3)

*2026-06-30. Base: Flux.1-dev fp8. LoRA: `dissonant_style` (rank 16, 1500 steps,
50 curated DissonantDreams illustrations). Eval = base+LoRA via `generate_image_lora`,
direct ComfyUI HTTP. Tested on **on-domain** retro-futurist subjects NOT in the
training set, across strengths 0.8/1.0/1.2, + a ckpt-1000 vs final control.*

## Verdict: **PASS — strong, distinctive, transferable.** Winner: **ckpt 1500 @ 0.8-1.0.**

The LoRA cleanly reproduces the **DissonantDreams retro-futurist pulp aesthetic**
(pink/cyan/black/cream, halftone screen-print + chrome airbrush, 70s-80s
sci-fi-paperback) on **new subjects it never saw** — i.e. it learned a transferable
*style*, not memorized images. This is exactly the distinctive, ownable look the
generic `stylized_game` lacked.

### Important process note (why the training previews looked weak)
ai-toolkit's in-training sample images used `launch_train.py`'s **default sample
prompts**, which are baked-in **dark-fantasy berserkr/GrimForge prompts** (warrior
on a cliff / horned beast / battle axe / ruined longhouse) — totally off-domain
from this sci-fi style, so they showed the style weakly and triggered a false alarm.
On **appropriate** subjects (below) the style is strong. *(Fix for next time: pass
style-appropriate `sample.prompts` for non-fantasy LoRAs.)*

### Strength sweep (subject = "woman in a black suit in a futuristic space station")
| Strength | Read | File |
|----------|------|------|
| 0.8 | Style fully present; face a touch more naturalistic | `dseval_00001` |
| **1.0** | **Bold sweet spot — the signature look** | `dseval_00002` |
| 1.2 | Flatter / more graphic-poster (great vintage-print feel) | `dseval_00003` |

### Cross-subject (strength 1.0) — all on-style
| Subject | Read | File |
|---------|------|------|
| Sci-fi figure | catsuit woman, retro space station, ships, teal/red/cream | `dseval_00002` |
| Chrome car | car on a pink desert road at sunset, bold flat color-blocking | `dseval_00005` |
| Comic portrait | suited man, starry sky, **pink/cyan/yellow color-split face** (the class-portrait signature) | `dseval_00008` |
| Cityscape | pink/cyan/black towers + halftone (the scenario look) | `dseval_00011` |

### Checkpoint control
ckpt-1000 (`dseval_00013`) vs final-1500 (`dseval_00002`): both strong, comparable;
**no overcooking at 1500**, so the final checkpoint ships.

## Recommendation
- **Deploy:** final `dissonant_style.safetensors` → `ComfyUI/models/loras/style/` (done) + sidecar (done).
- **Strength:** **1.0** default; **0.8** for more naturalistic subjects; **1.2** for max graphic-poster.
- **Hero samples** for the listing gallery: `eval/dissonant_style_assets/` (figure 1.0, car, portrait, cityscape, figure 1.2).
- **Confidence note:** trained on only 50 images but the style is consistent and
  transfers well — no sign of memorization or undertraining. If broader subject
  coverage is wanted later, add more curated own-art or img2img augment.
