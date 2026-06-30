# Business Plan — Execution Task Tracker

*Companion to `docs/BUSINESS-PLAN.md`. This is the actionable task list;
the business plan is the strategy/rationale. Keep statuses current.*

**Status legend:** `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked
**Gate refs** point at the product-readiness gates in BUSINESS-PLAN.md §4.

> Note: this is a deliberately separate file from the repo's `plan.md`
> (which is the Ralph-loop queue for the mv_ortho LoRA). Do not merge them.

> **CURRENT FOCUS (2026-06-30): list the finished products.** The texture pack
> (B0.8), tileset (A0.4), and village kits (K0.5) are DONE + engine-validated —
> they just need account upload. Selling these **Outputs/assets** is the licensed,
> proven money. Secondary: build **distinctive own-art style LoRAs** (Phase DS in
> `plan.md` — DissonantDreams), free on CivitAI for reputation/Buzz. **`stylized_game`
> was SCRAPPED** (generic AI output, no edge — see `plan.md` Phase SL header).
> GrimForge is LIVE on CivitAI (+ratings, 11 downloads / first 12h) — validates the
> distinctive-free-LoRA play.

---

## Phase 0 — Cash the proven wins + clear blockers

### Infrastructure / blockers
- [x] **B0.1** Fix LoRA path-separator bug (ComfyUI Windows backslash vs forward slash). *Done: `normalize_model_path_separators()` in workflow_manager.py + unit tests.*
- [ ] **B0.2** Restart the `comfyui-mcp` server (or session) and live-verify B0.1 — re-run `generate_image_pixelart` and `generate_image_lora` with forward-slash LoRA paths; both should succeed. *(Verified at code level; needs MCP restart.)*
- [x] **B0.3** Repoint `generate_texture_tile` defaults off the uninstalled juggernautXL checkpoint + placeholder LoRA. *Done.*
- [~] **B0.4** Re-run the focused market research; fold verified numbers into BUSINESS-PLAN.md §6. *(2026-06-29: TWO deep-research passes done → `docs/research/selling-ai-assets-best-practices.md` (pass 1: CivitAI economy + Unity/Fab/itch/Gumroad/TurboSquid splits) + `selling-ai-assets-followup.md` (pass 2: Fab "Created with AI" policy, CGTrader 60→85% ladder, Booth AI policy + VRM resale $30–200, CivitAI 40k-score gate). §6/§8 updated. **Pass 3 (live data):** style demand×gap RESOLVED via CivitAI API + itch.io top-sellers → `selling-ai-assets-followup.md` §5b (itch top sellers = 16×16 pixel tiles + low-poly kits; CivitAI fantasy/stylized beats saturated photoreal; build order `stylized_game→tile_topdown→lowpoly_flat→ortho_turnaround→mat_tile`). **Still open:** static-vs-rigged multiplier, Booth fee split, time-to-40k score, SVG policies.)*
- [ ] **B0.9** Fix `scripts/lora_eval_grid.py` auto-caption step — fails `HTTP 400 /prompt: invalid_prompt` and retries 4×/image, slowing evals. Cosmetic (captions are notes only), but wasteful. *(Found during the grimforge eval.)*

### Stream D — Sellable style LoRA (FIRST quick win, in flight)
- [x] **D0.1** Rebrand `berserkr_style` → `grimforge` (trigger `grimforge_style`), IP-clean. Dataset cloned + captions retriggered (148 imgs, 0 leftover brand tokens).
- [x] **D0.2** Train `grimforge` LoRA — rank 16, multi-res 512/768/1024, 1500 steps, 3090 Ti. *(Done; final ckpt 1500 + 500/750/1000/1250.)*
- [x] **D0.3** Eval grid (base vs ckpt 1000/1250/1500 × strengths 0.7/1.0) + AI-judge. **Winner: ckpt 1500 @ 0.8** (`scripts/train_lora/eval/grimforge_grid.md`).
- [x] **D0.4** 8-sample 1024px product card rendered (character/creature/env/weapon/portrait/prop/interior/beast); style cohesive 7/8. → `LORA-PRODUCT` met (`eval/grimforge_assets/`).
- [x] **D0.5** Deployed `grimforge_style.safetensors` + sidecar + provenance (original IP) to ComfyUI loras/style.
- [~] **D0.6** List `grimforge` style LoRA on **CivitAI** (+ mirror Gumroad/Ko-fi). Toggle AI disclosure. Add 8 samples + recommended settings. *(Listing copy ready: `scripts/train_lora/eval/grimforge_listing.md`; needs account upload.)* **⚠️ LICENSE BLOCKER (2026-06-30, `flux-lora-edge-and-licensing.md`): GrimForge is FLUX.1-dev-trained, so SELLING the `.safetensors` is prohibited (non-commercial Derivative). REVISED: list it FREE on CivitAI (reputation/lead-magnet) + monetize the OUTPUT images/assets; do NOT charge for the weights or paywall on Gumroad. For a SELLABLE LoRA file, retrain on FLUX.1-schnell (Apache-2.0).**
- [ ] **D0.7** Stand up the **custom-LoRA-as-a-service** intake (offer, dataset-rights checklist, fixed deliverable, turnaround SLA). **⚠️ LICENSE: a paid Flux-dev LoRA deliverable distributes a non-commercial Derivative — train client LoRAs on FLUX.1-schnell/SDXL (permissive), or sell the OUTPUT images/a hosted-generation service rather than the LoRA file.** **Market refinement (2026-06-30, from a "Flux LoRA Foundry" arbitrage write-up — affiliate/SEO source, treat as a lead not gospel): B2B shape validated — price ~$500-$1,500/engagement, pitch DIRECT to e-commerce brands / Shopify owners / agencies (NOT cheap marketplaces). KEY: the client wants product photos, not a model file → the compliant AND better deliverable is the OUTPUT images (or a hosted "generate more like this" service), sidestepping both the Flux-dev license and the client-photo-rights problem. The article's own method (ship the .safetensors; syndicate AI video to Getty/Shutterstock) is exactly what our pass-1/pass-4 research says fails — do NOT copy it.**

### Stream B — Seamless texture/material pack (quick win, needs workflow surgery)
- [x] **B0.5** Added a true **seamless mechanism** to `generate_texture_tile` — `SeamlessTile` (circular conv padding on the model) + `CircularVAEDecode`; verified tiles edge-to-edge (wrap-seam ≈ interior baseline). Also fixed two latent bugs found while testing: **512px→1024px** default (SDXL produces noise at 512) and sampler **euler/normal→dpmpp_2m/karras**; meta synced. Demos: `scripts/train_lora/eval/texture_seamless/`.
- [x] **B0.6** PBR map derivation (normal/roughness/AO via wrap-padded height-from-luminance, stays seamless) + edge-wrap tiling validation per map (`_seam_report.json`). *Caveats: maps are procedural (not photometric); no metallic map.*
- [x] **B0.7** Produced **Fantasy Environment Materials Vol.1** — 12 coherent materials × 4 maps (48 PBR files) at **2048×2048 (2K, ESRGAN-upscaled, seam-preserved)**, labeled contact sheet + README + license in `products/texture_pack_fantasy_v1/`. → `TEXTURE-PRODUCT` **fully met** (resolution + PBR set + seamless + thumbnails + Blender PBR-viewer validation). Normal orientation confirmed correct (raised relief under raking light) via headless render + interactive `_preview_scene.blend` (12 materials on a lit grid).
- [~] **B0.8** List texture pack on **Fab + Unity + Gumroad** (AI disclosure on). *(Listing copy ready: `products/texture_pack_fantasy_v1/LISTING.md`; needs account upload + zip.)*

### Stream A — Pixel-art tileset / UI pack (quick win)
- [x] **A0.1** Evaluated AI-gen+pixelate for tiles → **mediocre mush** (and Flux can't tile); `tileset-ralph` is docs-only. **Pivoted to procedural/code-drawn** pixel art (user-approved) — higher quality, full seam/transition control.
- [x] **A0.2** Built a cohesive 16×16 fantasy RPG tileset procedurally: **11 seamless terrain tiles** (grass +variants, dirt, water, deep water, stone, sand, cobble) + **48 Wang corner-autotile transitions** (grass↔dirt/water/sand) + **6 object sprites**. Seamless (toroidal patterns) verified visually. `products/tileset_fantasy_16_v1/`.
- [x] **A0.3** Packed **128×256 power-of-2 atlas** + `metadata.json` (regions + autotile corner masks) + 65 individual tiles + engine import notes (Godot/Unity/RPG Maker) + **sample-map mockup** (hero) + showcase sheet + README/license. → `TILESET-PRODUCT` met. **Engine-validated: imported into Godot 4.6, renders pixel-identical to the reference mockup** (atlas slicing, regions, transparency, Wang autotile masks all correct; bundled `examples/godot_import/` + `godot_validation.png`). *Note: transitions cover primary pairs (not all); more pairs = Vol.2.*
- [~] **A0.4** List tileset on **itch.io** (primary) + Unity/Fab. *(Listing copy ready: `products/tileset_fantasy_16_v1/LISTING.md`; needs account upload.)*

### Stream K — Low-poly 3D modular kits (NEW — user pivot from 2D)
- [x] **K0.1** Validated approach: AI/Hunyuan3D is wrong for clean modular kits; **procedural Blender** is right (same lesson as the tileset). PoC city block → approved.
- [x] **K0.2** Locked the look on a hero cottage after feedback: **dropped gradient-atlas → solid colors** (atlas mip-blurred to "multicolor" in Godot), added real detail (Tudor framing, jetty, gable roof, chimney, framed openings).
- [x] **K0.3** Built **GrimForge Village — Vol.1**: 28 procedural pieces (8 buildings, 3 walls/gate, 4 ground/path, 13 props), GrimForge palette, exported **GLB + OBJ + FBX**. Hero village render + catalog + README + LISTING in `products/village_kit_grimforge_v1/`. → modular-kit product.
- [x] **K0.4** Engine-validated: 28 GLBs imported into **Godot 4.6**, village scene reconstructed (`godot_village_kit/`), materials intact, grid-modular.
- [ ] **K0.5** List on **itch.io + Fab + Unity** (free base or $4.99 PWYW). *(Listing copy ready; needs account upload + in-engine gallery screenshot.)*
- [x] **K0.6** Built **Vol.2 expansion** — 23 pieces (windmill, ruined house, stable, guard tower, stone bridge, portcullis, palisade, fountain, torch, banner, stocks, anvil, trough, weapon rack, gibbet, bone pile, crypt, pine, stump, rocks, bush, wood pile, ruined wall). GLB+OBJ+FBX + combined Vol1+Vol2 hero + catalog + README + LISTING in `products/village_kit_grimforge_v2/`. **Kit now ~51 pieces.**
- [x] **K0.9** 3rd/4th feedback rounds: **gate** rebuilt solid+connected (block towers + bridging lintel + filled overlapping arch + full portcullis, no gaps/floaters); **walls** rebuilt as ashlar stone blocks (offset courses + shade variation = stone texture) + merlons; **windmill** window fixed flush on tapered tower; **tower** heavily detailed (battered base, stone courses, arrow slits, lit torch, wooden hoarding gallery, machicolation+battlements, banner). Rolled into kit + hero + Godot.
- [x] **K0.8** 2nd feedback round: authentic **half-timbered Tudor framing** on all house variants (studs/rails/corner braces/plaster panels); **detailed watchtower** (battered shaft, stone courses, arrow slits, arched door, machicolation+battlements, banner, glow window); **stained-glass** church windows + rose window (emissive blue/red/gold leaded panes). Rolled into kit + hero + Godot scene.
- [x] **K0.7** Acted on user feedback: reworked windmill (lattice × sails), stone bridge (wide cobbled deck + arch), gate (arched + full portcullis), graveyard (cohesive fenced plot), church (belfry/buttresses/rose window); fixed dead-tree branches connecting. Added **vertex-color gradient shading** kit-wide ("more texture", no atlas bleed) — validated rendering correctly in Godot 4.6. Re-rendered hero; product GLBs updated (v1 28, v2 25). *GLB = primary (carries shading); FBX carries vertex colors; OBJ flat.*

### Stream H — Content funnel (start now, ongoing)
- [~] **H0.1** Start a public build-log (the grimforge LoRA + path-bug fix make a natural first post/devlog). *(Draft ready: `scripts/train_lora/eval/grimforge_devlog.md` — long-form + short-form thread + titles; needs posting.)*
- [ ] **H0.2** Establish cadence: short-form (Shorts/TikTok/Reels) + long-form YouTube; lead with craft/process.

### LoRAs to train this phase (pipeline-feeders + fast sellable demand) — see catalog for rationale
- [ ] **L1 `mat_tile`** — seamless PBR/tileable material LoRA. Pairs with B0.5–B0.7 (texture pack). *(Tier 1)*
- [ ] **L2 `asset_neutral`** — single game asset on neutral bg (icons/equipment/props). Feeds Stream A icon packs **and** image→3D silhouette quality. *(Tier 1)*
- [ ] **L5 `tile_topdown`** — top-down RPG tile LoRA (16×16/32×32). Feeds Stream A tilesets (A0.2). *(Tier 2)*

---

## Phase 1 — Harden static 3D + open the LoRA service

### Stream C — Static 3D game-ready props
- [ ] **C1.1** Build a **mesh-cleanup auto-validator**: manifold/watertight check, decimate-to-poly-budget, UV sanity, meter-scale normalize, origin fix. → core of `MESH-PRODUCT` (§4.3).
- [ ] **C1.2** PBR texture/bake; export GLB **and** FBX, both open clean in Blender + one engine.
- [ ] **C1.3** Turntable render per asset; produce first themed prop/kitbash pack.
- [ ] **C1.4** List static prop pack on **Fab + Unity + CGTrader** (AI disclosure on).

### LoRAs to train this phase — see catalog for rationale
- [ ] **L4 `stylized_game`** — stylized hand-painted "fantasy game render" style (sibling to grimforge). Sellable + sets the house asset look. *(Tier 2)*
- [ ] **L6 `iso_build`** — isometric building/diorama LoRA (consistent scale/angle). Feeds iso asset packs. *(Tier 2)*
- [ ] **L7 `lowpoly_flat`** — low-poly flat-shaded LoRA; also improves image→3D input for Stream C. *(Tier 3)*
- [ ] **L8 `emblem`** — centered crest/badge LoRA; vectorize via `image_to_svg` for a vector/SVG product line. *(Tier 3)*

---

## Phase 2 — Unlock the premium tier (the real engineering bet)

### Stream E — Rigged characters (gated on rig hardening)
- [ ] **E2.1** Automate skin-weight refinement to **>95% coverage**, no floating verts. → `RIG-PRODUCT` (§4.5).
- [ ] **E2.2** Enforce the **5-pose deformation test** (no collapse, <2cm joint penetration, no candy-wrap).
- [ ] **E2.3** Standard bone naming + **VRM / Unity-Mecanim-Humanoid conformance**; hard-surface accessory attachment.
- [ ] **E2.4** Export valid GLB (Blender names) + FBX (Unity Humanoid), no import warnings. → clears `RIG-PRODUCT`.
- [ ] **E2.5** Ship first rigged character (Fab/Unity) + first VRM avatar (Booth/Gumroad).

### Stream F — Animated characters / animation packs (gated on animate hardening)
- [ ] **F2.1** Add **foot-IK lock** to the mocap retarget (kill foot-sliding).
- [ ] **F2.2** Loop-cleanup (first=last pose) + a **multi-clip set** (idle/walk/run + ≥2 actions).
- [ ] **F2.3** Bake + export multi-clip FBX/GLB; **validate playing in Unity Animator** (not just Blender). → clears `ANIM-PRODUCT` (§4.6).
- [ ] **F2.4** Ship first animated character + first animation pack (Fab/Unity).

### LoRA to train this phase (the 3D-pipeline moat) — see catalog for rationale
- [ ] **L3 `ortho_turnaround`** — multi-view character turnaround LoRA (extends `mv_ortho`); training set rendered from our own rigged meshes via `render_multiview`. Improves the rig/animate input **and** sells to 3D creators (2D-only creators can't replicate it). *(Tier 1)*

---

## Phase 3 — Productize the pipeline

### Stream G — Workflow packs / pipeline-as-product
- [ ] **G3.1** Strip project-specific paths/assets; make a pipeline run from a clean checkout. → `PRODUCT-KIT` (§4.7).
- [ ] **G3.2** Write setup guide + demo video; define license + support scope + known limitations.
- [ ] **G3.3** Package + launch: ComfyUI workflow pack(s) on Gumroad; Patreon/Ko-fi tiers.
- [ ] **G3.4** Scope a hosted "image→rigged→animated 3D" or auto-LoRA API.

---

## Suggested LoRA catalog (demand × gap)

Strategy: **avoid the oversupplied lanes** (anime/waifu, photoreal portraits,
celebrity/character likenesses, NSFW — saturated and/or IP-risky). Target the
intersection of *real demand* and *thin Flux supply*, biased to where THIS
toolchain has an unfair advantage: game-asset production + LoRAs whose training
data is rendered from our own 3D meshes (`render_multiview` / blender-mcp /
Poly Haven). All originals — no copyrighted styles/characters.

> Demand signals below are reasoned, not yet numerically verified (the CivitAI
> earnings research was rate-limited — see B0.4). Treat priority as a hypothesis
> to confirm, not a guarantee.

### Tier 1 — Pipeline-feeders (build first: each is BOTH a sellable LoRA AND a quality lever for our own products)
- **L1 `mat_tile` — seamless PBR / tileable material LoRA.** *Demand:* game devs buy textures constantly (Stream B). *Gap:* Flux has very few even-lit, tileable-material LoRAs (texture gen still lives mostly on SD1.5/SDXL). *Dataset:* even-lit crops of CC0 materials (Poly Haven via blender-mcp) + our own swatches. *Feeds:* Stream B. Pairs with B0.5 (seamless workflow).
- **L2 `asset_neutral` — single game asset on neutral background (icon / equipment / prop).** *Demand:* inventory icons, items, props on clean bg are an evergreen dev need. *Gap:* most LoRAs make scenes/characters, not clean isolated catalog assets; also clean silhouettes mesh far better in Hunyuan3D. *Dataset:* the Berserkr Equipment/Prop render style (regenerable) + isolated 3D-prop renders. *Feeds:* Streams A/C/D **and** the image→3D pipeline.
- **L3 `ortho_turnaround` — orthographic multi-view character turnaround (front/side/back), extends `mv_ortho`.** *Demand:* character artists + the booming image→3D crowd need consistent turnarounds. *Gap:* genuinely rare on the public market — hard to make without 3D data. *Moat:* we render the training set from our own rigged meshes; 2D-only creators can't. *Dataset:* `render_multiview` over owned/CC0 meshes. *Feeds:* the 3D pipeline + sells to other 3D creators.

### Tier 2 — Broad-demand sellable style LoRAs (IP-safe originals)
- **L4 `stylized_game` — stylized hand-painted "fantasy game render" look.** *Demand:* stylized (WoW/Hearthstone/Fortnite-adjacent) is the dominant indie aesthetic — very high. *Gap:* most Flux style LoRAs are photoreal or anime; a cohesive *original* stylized-game look is undersupplied. *Dataset:* curated original stylized renders. *Feeds:* Streams C/D + our own asset look. (Sibling to the dark-fantasy `grimforge`.)
- **L5 `tile_topdown` — top-down RPG tile LoRA (16×16/32×32, consistent palette).** *Demand:* itch.io's verified top sellers are 16×16 RPG tiles. *Gap:* Flux tile/pixel LoRAs are thin vs SDXL. *Dataset:* curated tileset-ralph outputs + CC0 tilesets. *Feeds:* Stream A.
- **L6 `iso_build` — isometric building / diorama LoRA (consistent scale & angle).** *Demand:* perennial for strategy/sim/mobile. *Gap:* scale-consistent iso Flux LoRAs are rare. *Dataset:* iso renders of 3D buildings (blender-mcp). *Feeds:* Streams A/C.

### Tier 3 — Niche gaps / opportunistic
- **L7 `lowpoly_flat` — low-poly flat-shaded stylized LoRA.** *Demand:* huge indie low-poly aesthetic. *Gap:* underserved on Flux; also low-poly concepts mesh cleanly in image→3D. *Dataset:* flat-shaded low-poly mesh renders. *Feeds:* the 3D pipeline.
- **L8 `emblem` — centered crest / badge / heraldry LoRA (vectorization-friendly).** *Demand:* logos/crests/badges are evergreen on Etsy/Creative Market and in games. *Gap:* clean centered emblem LoRA that traces well to SVG is a tidy niche. *Dataset:* curated original emblems. *Feeds:* the vector/SVG angle (pairs with `image_to_svg`).

**Scheduled across phases** (these entries are the rationale reference; the
trackable checkboxes live in the phase sections above):
**Phase 0** → L1, L2, L5 · **Phase 1** → L4, L6, L7, L8 · **Phase 2** → L3.
Build order within that: L1 → L2 → L5 → L4 → L3 → L6 → L7/L8. Reuse the proven
`scripts/train_lora/` harness for every one (the grimforge run is the template).

---

## Always-on compliance (every listing)
- [ ] Toggle platform AI-disclosure flag (Fab + Unity require it).
- [ ] Original IP only — no named characters/celebrities/living-artist styles.
- [ ] Don't market assets as "fully copyright-protected."
- [ ] Keep dataset-provenance notes per LoRA.
- [ ] Re-read the platform's AI terms immediately before listing.
