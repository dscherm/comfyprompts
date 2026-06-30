# GrimForge LoRA — marketplace listing copy (ready to paste)

*Draft for D0.6. Fill the CivitAI fields / Gumroad page from the blocks below.
Attach the 8 images in `eval/grimforge_assets/` as the gallery, in the order
listed under "Gallery". Toggle AI-disclosure ON wherever the platform asks.*

---

## CivitAI

**Model name:** `GrimForge — Dark Fantasy Concept Art`
**Type:** LORA  ·  **Base model:** Flux.1 D
**Version name:** `v1.0 (1500 / 0.8)`
**Trigger word:** `grimforge_style`
**Recommended weight:** `0.8`  (0.6 portraits · 1.0 environments)

**Tags:** `flux`, `concept art`, `dark fantasy`, `game art`, `character design`,
`creature`, `environment`, `fantasy`, `painterly`, `game asset`, `style`

### Description (paste as-is, markdown)

> **GrimForge** is a painterly **dark-fantasy concept-art** style for Flux.1 D —
> tuned for **game art**: characters, creatures, environments, weapons/equipment,
> and props. Expect saturated color, dramatic skies, high contrast, and
> illustrative rendered surfaces — the look of a polished game-pitch concept sheet.
>
> **How to use**
> - Add the trigger **`grimforge_style`** to your prompt.
> - **Weight 0.8** is the sweet spot. Drop to **0.6** for tighter portrait/face
>   fidelity; push to **1.0** for environments and dramatic scenes.
> - Strongest on **character** and **scene/environment** prompts. For clean
>   item/prop catalog shots, add `neutral background, concept art`.
> - Trained multi-resolution — renders crisp at **1024px**.
>
> **Example**
> ```
> grimforge_style, full body dark fantasy warrior in ornate plate armor,
> character concept art, neutral background
> ```
>
> Built on Flux.1 D (`flux1-dev`). Rank-16, 1500 steps.
>
> **AI / provenance:** This LoRA was trained on **148 curated original renders**
> — no third-party IP, no named characters, no living-artist styles. Outputs are
> AI-generated; please disclose AI use where your platform requires it. Free to
> use for personal and commercial work — a credit link back is appreciated but
> not required.
>
> If you make something cool with it, drop it in the gallery. ⚔️

### Per-image settings (enter on each uploaded sample)

All: Flux.1 D base, `flux1-dev-fp8`, LoRA `grimforge_style`, 1024×1024.

| Gallery # | Prompt (prepend `grimforge_style, `) | Weight |
|-----------|--------------------------------------|--------|
| 1 (cover) | full body dark fantasy warrior in ornate plate armor holding a battle standard, character concept art, neutral background | 0.8 |
| 2 | a ruined castle on a stormy cliff above a raging sea, dramatic sky, environment concept art | 1.0 |
| 3 | a torchlit dwarven forge hall with molten metal and great stone pillars, dark fantasy interior | 1.0 |
| 4 | a monstrous mountain troll with mossy stone skin, dark fantasy creature concept art | 0.8 |
| 5 | an armored dire wolf with glowing eyes snarling in a misty forest, dark fantasy creature concept art | 0.8 |
| 6 | an ornate rune-etched greatsword with a jeweled hilt, equipment concept art, neutral background | 0.8 |
| 7 | portrait of a grizzled barbarian king with a braided beard and battle scars, dark fantasy | 0.6 |
| 8 | an ancient treasure chest overflowing with gold coins and gems, game prop, neutral background | 0.8 |

**Gallery order** (set #1 as cover): `card_character_0.8` → `card_environment_1.0`
→ `card_interior_1.0` → `card_creature_0.8` → `card_beast_0.8` → `card_weapon_0.8`
→ `card_portrait_0.6` → `card_prop_0.8`.
*(Lead with the two strongest — character sheet + environment — for the thumbnail.)*

### License toggles (recommended)
- Allow commercial use: **Yes** (sell merch / use generated images / sell models).
- Credit required: **No** (appreciated).
- Allow others to share merges: your call (Yes is friendlier for reach).

---

## Gumroad / Ko-fi mirror

**Title:** `GrimForge — Dark Fantasy Concept Art LoRA (Flux)`
**Price:** free or pay-what-you-want (lead magnet) — or $3–5 "early access" tier.

**Short description:**
> A painterly dark-fantasy concept-art style for Flux.1 D — game-ready characters,
> creatures, environments, weapons & props. Trigger `grimforge_style`, weight 0.8.
> Trained on original art (no third-party IP). Includes the `.safetensors` + a
> usage card with example prompts. AI-generated outputs.

**What's included:** `grimforge_style.safetensors` (Flux.1 D, rank-16) · usage/
trigger sidecar · 8 example prompts. **Requires:** ComfyUI or any Flux LoRA loader.

---

## Pre-publish checklist
- [ ] Upload `grimforge_style.safetensors`.
- [ ] Set trigger `grimforge_style`, weight 0.8.
- [ ] Upload the 8 images from `eval/grimforge_assets/`, cover = character sheet.
- [ ] Paste description; confirm provenance line.
- [ ] **Toggle AI-disclosure ON.**
- [ ] Set license toggles.
- [ ] (Optional) link from the build-log post (task H0.1).
