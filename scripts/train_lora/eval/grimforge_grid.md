# grimforge_style — Flux LoRA eval + product card

**Verdict:** ship. **Winner:** checkpoint **1500** @ strength **0.8**
(0.6 portraits / 1.0 environments). Trigger: `grimforge_style`. Base: `flux1-dev-fp8`.

A painterly dark-fantasy concept-art / game-render style: saturated color,
dramatic skies, high contrast, illustrative surfaces. Rebrand + higher-res
(multi-res 512/768/1024) retrain of an earlier in-house style LoRA.

## How it was selected

Eval grid (`scripts/lora_eval_grid.py --only grimforge_eval --strengths 0.7 1.0`)
compared **base vs checkpoints 1000/1250/1500 × strengths 0.7/1.0** on a neutral
portrait + scene prompt (14 cells, `eval/grimforge-grid/`). Findings:

- No degradation/artifacts at any checkpoint or strength.
- Style shift is moderate on **trigger-less** neutral prompts (dramatic only on
  scenes) — consistent with the prior berserkr eval — and strong once the
  `grimforge_style` trigger is used (see product card below).
- Checkpoint **1500** (final) gave the strongest *coherent* style; 1250 close
  second. → 1500 is the keeper.
- **0.8** is the balanced default (preserves subject, strong style).

## Product card — 8 samples @ 1024px (trigger + deployed default)

Stable copies in `eval/grimforge_assets/`. Style identity is cohesive across the
full subject range (7/8 tight; the neutral-bg prop skews cleaner — a known Flux
tendency for isolated objects).

| Sample | Subject | Strength | File |
|--------|---------|----------|------|
| 1 | Warrior character sheet (neutral bg) | 0.8 | `card_character_0.8.png` |
| 2 | Mountain troll creature | 0.8 | `card_creature_0.8.png` |
| 3 | Ruined castle on a stormy cliff | 1.0 | `card_environment_1.0.png` |
| 4 | Rune-etched greatsword (neutral bg) | 0.8 | `card_weapon_0.8.png` |
| 5 | Barbarian king portrait | 0.6 | `card_portrait_0.6.png` |
| 6 | Treasure chest prop (neutral bg) | 0.8 | `card_prop_0.8.png` |
| 7 | Torchlit dwarven forge hall | 1.0 | `card_interior_1.0.png` |
| 8 | Armored dire wolf | 0.8 | `card_beast_0.8.png` |

## Usage

```
grimforge_style, <your subject>, dark fantasy concept art
```
Strength 0.8 default · 0.6 for portrait/character fidelity · 1.0 for
environments/scenes. Strongest on character + scene/environment prompts.

## Provenance / IP

Trained on 148 curated **original** in-house renders (no third-party IP, no
named characters/artists). Safe for commercial listing with AI disclosure.

## Deployed

`D:/Projects/ComfyUI/models/loras/style/grimforge_style.safetensors` (+ `.txt`
sidecar). Source checkpoint: `E:/ai-training/flux-output/grimforge_style/grimforge_style.safetensors` (1500 steps).

_Judge: Claude (Opus 4.8), visual comparison of the rendered grid + product card._
