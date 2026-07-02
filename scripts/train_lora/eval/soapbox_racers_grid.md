# soapbox_racers — eval (gritty retrain)

*2026-07-01. Base: Flux.1-dev fp8. LoRA: `soapbox_racers` (rank 16, **step 500**
of a gritty retrain). Dataset: 132 images — 19 real `character_variations` +
img2img-augmented at low denoise (gritty-comic prompt) + bones; the chibi `to3d`
mascots and the soup_box cartoon-robot were EXCLUDED. Captions: clean per-character
templates from the character brief (NO "cartoon/animated/anime"). Eval = base+LoRA
via `generate_image_lora`, direct ComfyUI HTTP, one fixed seed per test.*

## Verdict: **PASS at step 500 — shipped.** Winner: **step 500 @ strength 1.1.**

Reproduces the target **gritty illustrative / comic-book (ink) style** — bold black
outlines, heavy ink, realistic proportions, big expressive faces (Mad Max + Speed
Racer + R. Crumb + Otomo + Mad Magazine) — on **all 9 named characters**, standing,
full body, white background. No cartoon, no anime, no photoreal, no karts.

### Why v1 was scrapped (and the fix)
- **v1 (`soapbox_racers_v1_cartoonish`)** trained on the `to3d/` chibi game-mascots
  + Florence captions that said "cartoon/animated/anime" 87× → came out cartoonish.
- **Fix:** train on the realistic-proportion `character_variations` (gritty ink art),
  drop the chibi/robot images, and caption from the brief with a gritty-comic
  vocabulary. Result = the correct style.

### Critical process note — training previews were a FALSE ALARM
ai-toolkit's in-training samples used vehicle-cueing prompts ("wasteland racer /
desert warrior") at guidance 4, so **base Flux rendered photoreal karts and masked
the LoRA** — the previews looked photoreal/cartoonish at steps 250–500. Testing the
same step-500 checkpoint with PROPER prompts ("flat ink comic, standing, white
background") showed the style is strong and correct. (Same false-alarm documented
for `dissonant_style`. Fix for future: pass style-forward `sample.prompts`.)

### Roster (step 500 @ 1.1, fixed seed) — all on-model
| Character | Read | File |
|-----------|------|------|
| player (rookie) | orange racing jacket, goggles on forehead, brown hair | `soapbox_racers_assets/player.png` |
| bones | skeletal reaper, bone-white face, white mohawk, black leather | `bones.png` |
| crank | stocky mechanic, overalls, flat cap, handlebar mustache, wrench | `crank.png` |
| grit | muscular desert warrior woman, hood, tribal tattoos | `grit.png` |
| pip | thin scavenger kid, green patched vest, red hair, backpack | `pip.png` |
| punk_king | wasteland queen, spiked crown, purple cape, chains | `punk_king.png` |
| rust | ironclad, bolted rusted armor, welding mask | `rust.png` |
| smog | chemist, gas mask, green hazmat overcoat, hood | `smog.png` |
| sparks | livewire woman, blue bodysuit, lightning accents, blue hair | `sparks.png` |

Full sheet: `soapbox_racers_assets/_roster9.png`.

## Recommendation
- **Deploy:** `soapbox_racers_gritty_000000500.safetensors` → `ComfyUI/models/loras/style/soapbox_racers.safetensors` (done) + sidecar `.txt` (done).
- **Strength:** **1.1** default; 0.9 lighter, 1.3 max-bold.
- **Stopped at 500 on purpose:** already nails all 9 chars + the aesthetic; more steps
  risk overfitting/less flexibility. v1 preserved as `_v1_cartoonish` for reference.
- **Companion LoRA:** `soapbox_world` (wasteland scenes/vehicles) trains next.

## Licensing
FLUX.1-dev derivative → distribute the LoRA **FREE**; the **outputs** are commercially
usable. List free on CivitAI; sell only generated assets, not the weights.
