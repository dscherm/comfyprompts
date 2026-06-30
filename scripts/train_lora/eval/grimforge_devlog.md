# Build-log: shipping a sellable Flux LoRA in an afternoon (H0.1)

*Draft devlog. Lead with craft/process. Funnels to the GrimForge listing.
Includes a long-form post + a short-form thread + title/thumbnail options.*

---

## Long-form post

### I tried to sell my AI game-art tools' output. First I had to fix what was quietly broken.

I've been building a local pipeline that turns prompts into game assets — images,
3D meshes, rigs. Before selling anything, I did the unglamorous thing: a real
quality check against "is this actually shippable" criteria. Two lessons fell out
of it, and one of them might save you an afternoon.

**1. Nothing generated. The bug was a single backslash.**

Every LoRA-based generation was failing validation. The cause: on Windows,
ComfyUI lists nested LoRAs with **backslashes** (`style\my_lora.safetensors`) and
validates the submitted name by *exact string match*. My tooling passed
**forward slashes** (`style/my_lora.safetensors`). Same file, different string →
"Prompt outputs failed validation," silently, on everything.

Fix: normalize the separator to the OS-native one right before submission — so
both slash styles match the host's enum. One function, one chokepoint, every
LoRA workflow unblocked. If your ComfyUI LoRAs "exist but won't load" on Windows,
check this first.

**2. The boring part — an automated harness — is the actual product.**

I have a four-step loop that turns a folder of images into a deployed LoRA:
`prep → caption → train → eval-grid → deploy`. It's dataset-agnostic — paths and a
trigger word are the only inputs. That repeatability is the moat: it's the
difference between "I trained a LoRA once" and "I can train one on anything,
on demand."

### So I shipped one: GrimForge

A painterly **dark-fantasy concept-art** style for Flux — built for game art:
characters, creatures, environments, weapons, props.

- **Rebrand + retrain.** Took an in-house style LoRA, gave it a clean IP-safe name
  and trigger, and retrained it **multi-resolution (512/768/1024)** instead of
  512-only — so the style stays crisp at 1024.
- **Trained on 148 curated *original* renders.** No third-party IP, no named
  characters, no living-artist styles. That matters if you intend to sell.
- **Picked the winner objectively.** An eval grid compared every checkpoint ×
  strength; the final checkpoint at weight **0.8** won (0.6 for portraits, 1.0
  for environments).
- **Proved range before listing.** 8 samples at 1024px — character sheet, troll,
  storm-cliff castle, rune greatsword, barbarian portrait, forge hall, dire wolf,
  treasure chest. The style held across all of them.

Whole thing, dataset to deployed: an afternoon on a single 24GB GPU.

**Grab it here:** [CivitAI link] · mirror on [Gumroad link]. Free to use,
commercial OK. Outputs are AI-generated — disclose where your platform asks.

### What's next
GrimForge is the first of a small catalog I'm building around where the Flux
library is actually thin: seamless tileable materials, clean game-asset-on-neutral
LoRAs, and the one I'm most excited about — multi-view character turnarounds
rendered from real 3D meshes (something pure-2D creators can't easily fake).
Follow along.

---

## Short-form thread (X / TikTok / Reels caption)

1/ Tried to sell my AI game-art output. Did a real QC first. Found a bug that was
silently breaking *every* LoRA generation. 🧵

2/ On Windows, ComfyUI lists nested LoRAs with backslashes and matches the name
exactly. My tools sent forward slashes. Same file → "failed validation" on
everything. Fix: normalize the separator before submit. One function.

3/ Real lesson though: the moat isn't one LoRA, it's the *harness*. prep → caption
→ train → eval → deploy, dataset-agnostic. Train one on anything, on demand.

4/ So I shipped one: GrimForge — dark-fantasy concept art for Flux. Game-ready
characters, creatures, environments, weapons, props. Trigger `grimforge_style`,
weight 0.8.

5/ Retrained multi-res so it's crisp at 1024. Trained on 148 *original* renders —
no stolen IP. Picked the best checkpoint with an eval grid, not vibes.

6/ Dataset → deployed in an afternoon on one 24GB GPU. Free, commercial OK 👇
[link]

7/ Next: seamless material LoRAs + multi-view character turnarounds rendered from
real 3D meshes. Follow for the catalog.

---

## Titles / thumbnails

**YouTube/blog title options**
- "I shipped a sellable AI art model in an afternoon (and fixed the bug breaking all my LoRAs)"
- "The one-backslash bug that breaks every ComfyUI LoRA on Windows"
- "From prompt to product: training & shipping a Flux LoRA, start to finish"

**Thumbnail:** the GrimForge character sheet (`card_character_0.8.png`) on one
side, a `style/my_lora ❌ → style\my_lora ✅` overlay on the other. Big text:
"ONE BACKSLASH."

**CTA everywhere:** link to the CivitAI listing; pin the Gumroad mirror.
```
```
