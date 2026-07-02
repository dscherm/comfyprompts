# soapbox_world — eval

*2026-07-01. Base: Flux.1-dev fp8. LoRA: `soapbox_world` (rank 16, **step 1000**,
cut early per user). Dataset: 45 images — 38 *Soapbox Sabotage* cutscenes (1280×720)
+ 7 kart designs. Captions: Florence + trigger, "post-apocalyptic wasteland racing,
bold outlines, dramatic". Companion to `soapbox_racers` (the two-LoRA split — same
aesthetic, different framing: WORLD = wide scenes/vehicles, RACERS = character portraits).*

## Verdict: **PASS at step 1000 — shipped.** Winner: **step 1000 @ strength 1.0.**

Reproduces the **bold comic-book post-apocalyptic wasteland-racing SCENE** aesthetic —
orange desert sunsets, ruined-city raceways, junkyards, canyons, karts kicking up dust,
heavy ink, speed lines. Matches the game's cutscene art.

Unlike `soapbox_racers`, there was **no false-alarm risk**: scenes/vehicles ARE the
subject, so the training previews (scene prompts) showed the style directly from step
250 onward. Cut at step 1000 (checkpoints 1000/1250/1500 all saved) — 1000 already
strong; more steps available if a stronger imprint is ever wanted.

### Scene tests (step 1000 @ 1.0, fixed seed) — all on-style
| Scene | Read | File |
|-------|------|------|
| Desert sunset | kart on a desert road toward a huge orange sun, canyon walls | `soapbox_world_assets/desert_sunset.png` |
| Ruined city | karts through a crumbling city, orange smoky sky | `ruined_city.png` |
| Junkyard | wrecked cars + scrap, dusty orange wasteland | `junkyard.png` |
| Canyon | kart in a canyon, dust and speed lines | `canyon.png` |
| Pit stop | ramshackle desert pit stop, tires + fuel drums | `pitstop.png` |
| Finish | checkered banner over a dusty desert track | `finish.png` |

Full sheet: `soapbox_world_assets/_scenes.png`. (Banner text garbles — normal Flux
text artifact, irrelevant for a scene style.)

## Recommendation
- **Deploy:** `soapbox_world_000001000.safetensors` → `ComfyUI/models/loras/style/soapbox_world.safetensors` (done) + sidecar (done).
- **Strength:** **1.0** default; 0.8 lighter, 1.2 max-bold.
- **Use with `soapbox_racers`:** world for backgrounds/scenes/vehicles, racers for
  the character portraits — same aesthetic, they compose.

## Licensing
FLUX.1-dev derivative → distribute the LoRA **FREE**; outputs are commercial. List free.
