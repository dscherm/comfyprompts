# ComfyUI Toolchain — Monetization Business Plan

*Drafted 2026-06-26. Pairs with the market research in this session.*

> **Status of the numbers in this plan.** **Updated 2026-06-29/30 from three
> deep-research passes** (`docs/research/selling-ai-assets-best-practices.md` +
> `selling-ai-assets-followup.md`). Platform policies, revenue splits, the CivitAI
> Buzz economy, and the live style-demand data (CivitAI API + itch.io top-sellers)
> are now **verified** and folded into §6/§8 and the Stream D playbook. Remaining
> `~est` figures are the per-stream monthly projections (§6) and a few open items
> (static-vs-rigged multiplier, Booth fee split, time-to-40k score) — treat those
> as planning assumptions, not promises.

---

## 1. Strategy in one paragraph

Run a **portfolio**, not a single bet. Lead with the three PROVEN pipelines
(image gen, image→3D, LoRA training) producing **low-controversy assets**
(textures, tilesets, static props) onto the **only marketplaces confirmed to
welcome AI content** (Fab, Unity Asset Store, itch.io) — these are quick wins
with near-zero build cost. In parallel, **harden the rig→animate chain**, which
is the single highest-leverage engineering investment because it unlocks the
premium price tier (animated characters sell for ~6–15× a static prop). Use a
**public build-log** as the funnel that converts the whole effort into the
higher-ceiling play: **productizing the pipeline itself** (workflow packs,
custom-LoRA-as-a-service). Passive asset sales fund the runway; productization
+ audience is the ceiling.

---

## 2. Revenue portfolio at a glance

| # | Stream | Type | Lead pipeline | Maturity | Effort | Time-to-1st-$ | Ceiling |
|---|--------|------|---------------|----------|--------|---------------|---------|
| A | Pixel-art tilesets / UI packs | Passive | Image gen + tileset-ralph | PROVEN | Low | 1–2 wks | Low-Med |
| B | Seamless PBR texture packs | Passive | Texture tiles | PROVEN | Low | 1–2 wks | Med |
| C | Static 3D game-ready props | Passive | Hunyuan3D/TripoSG | PROVEN | Low-Med | 2–4 wks | Med |
| D | Flux/SDXL LoRAs + custom-LoRA service | Passive + Active | LoRA harness | PROVEN | Low-Med | 2–3 wks | Med (active: High) |
| E | Rigged characters (VRM/humanoid) | Passive | UniRig (autorig-ralph) | WORKING | Med-High | 6–10 wks | Med-High |
| F | Animated characters / anim packs | Passive | Mocap retarget (animate-ralph) | FRAGILE | High | 10–14 wks | High |
| G | Workflow packs / pipeline-as-product | Active/Productize | Whole chain | Varies | Med | 8–12 wks | High |
| H | Content / audience funnel | Multiplier | Any | n/a | Med, ongoing | n/a | Force-mult. |

Confirmed channel policy (verified 2026-06-29): **all target game-dev
marketplaces permit AI assets** — Fab (mandatory "Created with AI" flag at
publish + optional "NoAI" opt-out), Unity (mandatory AI-description field),
itch.io (`[AI Generated]` tag, deindexed if skipped), CGTrader & Booth (allowed,
**no** disclosure required; Booth soft-suppresses AI-heavy shops in search).
**Disclosure is tied to search discoverability** on Fab/Unity/itch — disclose
proactively everywhere. Stock-photo sites (Shutterstock etc.) still ban AI — sell
on game-dev channels, not stock sites. **Avoid low-effort/mass-produced AI pages**
(itch & Unity treat them as spam) — curate and hand-finish.

---

## 3. Stream playbooks

Each playbook = **what you sell · who buys & where · pricing · the product gate
(§4) it must clear · map to production**.

### A — Pixel-art tilesets & UI packs  *(quick win)*
- **Sell:** RPG tilesets (16×16 / 32×32), animated character sprite packs, UI
  kits. itch.io's verified top sellers are exactly these categories.
- **Who/where:** indie/hobby game devs on **itch.io** (primary), **Unity Asset
  Store**, **Fab**. Cross-list.
- **Pricing `~est`:** $4–20 per pack; "name your price" free packs as funnel;
  $30–70 mega-bundles.
- **Gate:** `TILESET-PRODUCT` (§4.1).
- **Production map:** pick a theme → generate base + transition tiles via
  tileset-ralph → pass seamless gate (5-RGB edge tolerance) → pack atlas +
  metadata JSON → 5 preview mockups in a real engine grid → list on itch.io →
  cross-post to Unity/Fab with AI disclosure.

### B — Seamless PBR texture packs  *(stealth quick win — lowest risk of all)*
- **Sell:** tiling PBR material sets (albedo/normal/roughness/AO), 10–30
  materials per pack (stone, metal, wood, sci-fi, fabric).
- **Who/where:** game devs & 3D artists on **Fab**, **Unity Asset Store**,
  **Gumroad**. No human likeness, no rig, no character-IP risk → smallest legal
  surface in the whole portfolio.
- **Pricing `~est`:** $8–25 per pack; $40+ bundles.
- **Gate:** `TEXTURE-PRODUCT` (§4.2).
- **Production map:** generate tile → verify seamless tiling at 2×2 → derive
  normal/roughness/AO maps → validate in a PBR viewer (Blender) → pack +
  thumbnail render → list.

### C — Static 3D game-ready props  *(quick win, slightly more QA)*
- **Sell:** kitbash/prop packs (crates, barrels, weapons, furniture, junk),
  single hero props. Game-ready = clean topology, sane poly count, UVs, real-world scale.
- **Who/where:** **Fab** (Unreal/game buyers), **Unity Asset Store**,
  **CGTrader**, **Sketchfab store**. Game devs buy props in volume.
- **Pricing `~est`:** $3–15 single prop; $20–60 themed packs.
- **Gate:** `MESH-PRODUCT` (§4.3).
- **Production map:** concept image (LoRA-styled) → Hunyuan3D/TripoSG mesh →
  Blender cleanup (decimate to budget, manifold check, UV, scale to meters) →
  PBR texture/bake → export GLB+FBX → turntable render → list with AI disclosure.

### D — Flux/SDXL LoRAs + custom-LoRA-as-a-service  *(quick win + active upside)*
- **Sell (passive):** original **style** and **original-character** LoRAs on
  **CivitAI** (Buzz/tips/early-access), mirrored on **Gumroad/Ko-fi**.
- **Sell (active):** "I'll train a Flux LoRA on your brand/characters/product"
  — this is where your reusable QLoRA harness is a real moat; most uploaders
  can't offer a repeatable, eval-gated service.
- **Who/where:** AI-art hobbyists (CivitAI), indie studios & small brands
  (direct, via content funnel) for custom work.
- **Pricing `~est`:** passive — tips + early-access $3–10/mo patrons; custom —
  $50–300 per trained LoRA depending on dataset prep.
- **Gate:** `LORA-PRODUCT` (§4.4).
- **Legal:** **original IP only.** No celebrities, named characters, or living
  artists' styles — that's the fastest takedown/exposure path in the plan.
- **⚠️ LICENSE (verified 2026-06-30, `flux-lora-edge-and-licensing.md`):**
  **Selling a FLUX.1-dev-trained LoRA *file* is PROHIBITED** — a LoRA is a
  "Derivative" under the FLUX.1 [dev] Non-Commercial License, restricted to
  non-commercial use. **BUT the OUTPUT images (and assets derived from them) ARE
  commercially sellable** — BFL claims no ownership of outputs. So:
  **(a)** sell the *images/assets* freely (Streams A/B/C/K are clean);
  **(b)** give Flux-dev LoRAs away FREE on CivitAI (reputation/lead-magnet);
  **(c)** for a sellable LoRA *file* or paid custom-LoRA deliverable, train on
  **FLUX.1-schnell (Apache-2.0)** or another permissive base, not dev. Even a
  paid BFL commercial license appears to bar reselling the weights to third
  parties (unresolved). **Monetize Outputs + audience, not the weights.**
- **Production map:** curate dataset (prep_dataset.py) → caption → train (1500
  steps) → eval-grid + AI judge → pick winner ckpt/strength → deploy + trigger
  sidecar → publish card with sample grid + recommended settings.
- **Evidence-backed style strategy** (live CivitAI API + itch.io top-sellers,
  2026-06-29; see `selling-ai-assets-followup.md` §5b):
  - **Saturated — avoid:** photoreal/hyperreal (the runaway #1 lane), anime/Pony,
    generic "woman/girl" character, NSFW. Not our edge; IP/saturation-risky.
  - **Win pattern:** the top fantasy LoRA bundles *many substyles* under one model.
    On CivitAI **breadth = downloads = Generator-Buzz** — build broad, versatile
    style LoRAs, not narrow one-offs.
  - **Build order (each is BOTH sellable AND a pipeline lever):**
    `stylized_game` (hand-painted fantasy, bundle substyles — strongest LoRA play;
    sibling to the shipped GrimForge) → `tile_topdown` (feeds itch.io's **#1**
    selling category, 16×16 RPG tiles) → `lowpoly_flat` (feeds itch.io's **#2**,
    low-poly 3D kits + image→3D) → `ortho_turnaround` (the 3D-data moat) →
    `mat_tile` (thin Flux material supply).
  - **Reach vs dollars:** CivitAI is a **lead-magnet + reputation engine**
    (earnings top-heavy: top 1,000 creators ≈ 90% of Buzz; median cycle payout
    ~$81) — capture actual dollars on the **Gumroad/Ko-fi mirror (~90%)**.
  - **Utility/quality-enhancer LoRA track** (verified 2026-06-30, `flux-model-types-
    and-feasibility.md`): the **most-downloaded Flux LoRAs are utility enhancers**
    (hands/anatomy/detail/realism), not art styles — they're used in *every*
    generation, so they top the 25%-of-Generator-Buzz mechanic. Build one or two
    **FREE** (licensing bars selling the file) as the best Buzz/reputation/funnel
    engine — fitting our edge: a stylized/game-art **detail enhancer** or a
    **clean-silhouette/neutral-bg** helper (the latter also improves image→3D input).
  - **Feasibility boundary:** the **LoRA is the only solo-feasible unit** on a
    24GB card. **Do NOT attempt to train Flux ControlNets** (datacenter-scale:
    300k steps / 20M images) **or full checkpoints** (~120GB) — use existing
    ControlNets for inference instead.
  - **Edge, stated honestly:** lead with **repeatability + curation + 3D-rendered
    datasets** (verifiable). Multi-res training is real but its quality *delta* is
    unquantified — don't market "higher quality" as a proven claim.

### E — Rigged characters (VRM / humanoid / Mixamo-compatible)  *(higher ceiling, harden first)*
- **Sell:** game-ready rigged humanoid/creature GLB; **VRM** avatars for the
  VTuber/VRChat market (a distinct, willing-to-pay audience).
- **Who/where:** indie devs (**Fab/Unity**), VTubers & VRChat users
  (**Booth.pm**, **Gumroad**). Rigging commands a real premium over static.
- **Pricing `~est`:** $15–60 rigged character; VRM avatars $20–100+.
- **Gate:** `RIG-PRODUCT` (§4.5) — this is the gate your pipeline does **not**
  reliably clear yet.
- **Production map:** static mesh (Stream C) → UniRig predict skeleton →
  rename bones to standard → weight refinement to >95% coverage → deformation
  test (5 poses) → VRM/humanoid retarget conformance → export → list.

### F — Animated characters & animation packs  *(highest ceiling, most build)*
- **Sell:** characters with a baked locomotion/idle/action set; standalone
  **animation packs** (the Mixamo-alternative niche).
- **Who/where:** **Fab**, **Unity Asset Store**. Animation is the top of the
  3D-asset value pyramid.
- **Pricing `~est`:** $25–80 animated character; $15–50 animation packs.
- **Gate:** `ANIM-PRODUCT` (§4.6) — currently the weakest link (one walk cycle
  works end-to-end).
- **Production map:** rigged char (Stream E) → mocap retarget per clip → clean
  loops (no foot-slide, no head pop) → bake → multi-clip FBX/GLB → in-engine
  validation → list.

### G — Workflow packs / pipeline-as-a-product  *(productization play, audience-gated)*
- **Sell:** ComfyUI workflow packs (the parametric `workflows/mcp/` set,
  cleaned for resale), the "image→rigged→animated 3D" recipe, custom-LoRA
  service productized, eventually a hosted API.
- **Who/where:** **Gumroad/Patreon**, ComfyUI community, your own audience.
  Sells *to people who already follow you* — gated on Stream H.
- **Pricing `~est`:** $5–30 workflow packs; $10–25/mo Patreon; service tiers.
- **Gate:** `PRODUCT-KIT` (§4.7) — docs, reproducibility, support burden.
- **Production map:** harden + document a pipeline → strip project-specific
  paths/assets → write setup guide + demo video → package → launch to audience.

### H — Content / audience funnel  *(multiplier, not direct revenue)*
- **Do:** build-logs ("automating image→rigged→animated 3D"), LoRA-in-an-
  afternoon tutorials, asset-pack devlogs. Short-form (TikTok/YT Shorts/Reels)
  + long-form YouTube.
- **Why:** every video is the funnel for D (custom LoRA), E/F (asset buyers),
  and G (productization). Free packs are lead magnets.
- **Caveat:** disclose AI per each platform's rules; faceless-automation
  channels face tightening monetization policies — lead with *craft/process*,
  which is defensible.

---

## 4. Product-readiness gates (the "threshold to be sellable" per tool)

A pipeline output is **not a product** until it clears its gate. These extend
the existing pipeline acceptance criteria (autorig-ralph PRD, tileset-ralph PRD)
into *commercial* thresholds. Status: ✅ pipeline already enforces · ⚠️ partially
· ❌ not yet.

### 4.1 `TILESET-PRODUCT` (Stream A) — current: mostly ✅
- ✅ Seamless: edge pixels match within **5 RGB units** when tiled (tileset gate 03).
- ✅ Every terrain type + all transition pairs present; no duplicate tiles.
- ✅ Atlas packed to power-of-2 with metadata JSON mapping each tile region.
- ⚠️ **Commercial adds:** ≥3 engine-ready exports (Godot/Unity/RPG Maker); a
  README with license + import steps; ≥5 marketing mockups in a real grid;
  consistent palette across the *whole pack* (not just one set).

### 4.2 `TEXTURE-PRODUCT` (Stream B) — current: ⚠️
- ⚠️ Tiles seamlessly at 2×2 and 4×4 (no visible repetition artifacts).
- ❌ Full PBR set per material: albedo + normal + roughness (+ AO/metallic),
  resolution ≥2K, consistent texel density across the pack.
- ❌ Validated in a PBR viewer under 2 lighting setups; normal map orientation
  correct (no inverted bumps).
- ⚠️ Pack ≥10 materials, thematically coherent, thumbnail sheet rendered.

### 4.3 `MESH-PRODUCT` (Stream C) — current: ⚠️
- ❌ **Manifold/watertight** where expected; no non-manifold edges, no flipped
  normals, no internal floating geometry.
- ❌ **Poly budget** stated and met (e.g. prop ≤5k tris game-ready; LOD0 hero
  ≤20k); decimated cleanly.
- ❌ **UVs** non-overlapping, reasonable texel density; **scale in real meters**;
  origin sane (base-centered).
- ❌ PBR textures baked; GLB **and** FBX export both open clean in Blender +
  one engine. Turntable render produced.
- *Why ❌: Hunyuan3D output is mesh-PROVEN but not yet auto-validated to
  game-ready spec; cleanup is currently manual/ad-hoc.*

### 4.4 `LORA-PRODUCT` (Stream D) — current: ✅ (passive) / ⚠️ (service)
- ✅ Eval-grid run, base-vs-LoRA across checkpoints × strengths, AI-judge winner
  recorded (harness does this).
- ✅ Trigger word + recommended strength documented in sidecar.
- ⚠️ **Commercial adds:** ≥8 sample images on the card with prompts/settings;
  **provenance statement** (dataset is original/licensed — no scraped IP);
  consistent identity across ≥5 unseen prompts (for character LoRAs).
- ⚠️ **Service tier:** turnaround SLA, intake form, dataset-rights checklist,
  fixed deliverable (ckpt + sidecar + sample grid).

### 4.5 `RIG-PRODUCT` (Stream E) — current: ❌ (the blocker for premium tier)
From autorig-ralph PRD, promoted to commercial gate:
- ❌ **Skin-weight coverage >95%**, no floating/unweighted vertices.
- ❌ **5-pose deformation test** passes: no mesh collapse, **<2cm penetration**
  at joints, no candy-wrapper twisting.
- ❌ **Bone hierarchy standard-named** and **humanoid/VRM/Mixamo-conformant**
  (maps cleanly to Unity Mecanim Humanoid / VRM spec).
- ❌ Hard-surface accessories parented/constrained correctly.
- ❌ Exports valid GLB (Blender names) **and** FBX (Unity Humanoid) that import
  without warnings.
- *Why ❌: rigging is WORKING but needs manual bone cleanup + proximity-weight
  fixes; not yet repeatable to spec without intervention.*

### 4.6 `ANIM-PRODUCT` (Stream F) — current: ❌ (weakest link)
- ⚠️ Retarget transfers a clip with correct scale (quaternion fix landed) and
  **no head/neck artifact** (skip-head fix landed) — **one walk proven**.
- ❌ **No foot-sliding** (foot contacts locked); loops seamless (first=last pose).
- ❌ A **set** of clips (idle/walk/run + ≥2 actions) all clean, not just one.
- ❌ Baked, exported, and **validated playing in-engine** (Unity Animator),
  not just in Blender.
- *Why ❌: only a single locomotion clip survives the full chain today.*

### 4.7 `PRODUCT-KIT` (Stream G) — current: ❌
- ❌ Runs from a clean checkout with documented setup (no hardcoded D:\ paths).
- ❌ Reproducible by a stranger following the README; demo video.
- ❌ License terms + support scope defined; known-limitations stated.

---

## 5. Production roadmap (phased)

**Phase 0 — Cash the proven wins (weeks 1–4).** Ship 1 texture pack (B) + 1
tileset/UI pack (A) to itch.io + Fab + Unity. Publish 2 original LoRAs (D) to
CivitAI + Gumroad. Start the build-log (H). *Goal: first dollar, learn each
storefront's listing + AI-disclosure flow.* No new engineering — close the
small commercial gaps in 4.1/4.2.

**Phase 1 — Harden static 3D + open the LoRA service (weeks 3–8, overlaps).**
Build a **mesh-cleanup auto-validator** to clear `MESH-PRODUCT` (4.3): manifold
check, decimate-to-budget, UV sanity, meter-scale normalize, GLB+FBX export.
Ship first static prop pack (C). Stand up the custom-LoRA intake (D-service).

**Phase 2 — Unlock the premium tier (weeks 7–14).** This is the real
engineering bet. Harden in order:
1. **Rig (E):** automate weight-refinement to >95% + the 5-pose deformation
   gate; enforce VRM/Mecanim-conformant bone naming. *Exit: `RIG-PRODUCT` ✅.*
2. **Animate (F):** add foot-IK lock (kill foot-slide), loop-cleanup, and a
   multi-clip batch; validate in Unity. *Exit: `ANIM-PRODUCT` ✅.*
Ship first rigged character (E), then first animated character / anim pack (F).

**Phase 3 — Productize (weeks 12+).** With audience from H and a hardened
chain, package the workflow kit + pipeline recipe (G), launch Patreon/Gumroad
tiers, scope a hosted "image→rigged→animated 3D" or auto-LoRA API.

**Always-on:** AI-disclosure compliance, original-IP-only discipline, re-check
platform policies before each launch (they're changing fast).

---

## 6. Illustrative economics

> **Verified platform economics** (two deep-research runs 2026-06-29; full cited
> reports: `docs/research/selling-ai-assets-best-practices.md` (pass 1) +
> `selling-ai-assets-followup.md` (pass 2)). These replace the earlier guesses.

**Revenue splits (creator share):**

| Platform | Creator share | Notes |
|----------|--------------|-------|
| Gumroad | **~90%** | flat 10% on direct sales + $0.50/sale; 30% on marketplace/discovery sales |
| itch.io | **90–100%** | seller-set slider, default 10% cut; instant publish, no curation |
| Fab (ex-Unreal Mktpl.) | **88%** | 12% cut; **$100 payout floor** (sub-$100 rolls over). Sketchfab Store merged in Oct 2024 |
| CGTrader | **60% → 85%** | 26-level ladder on cumulative **rolling-365-day** sales; **new sellers start at 60%** (worst start of the set) |
| TurboSquid | **40–80%** | tiered by exclusivity |
| Unity Asset Store | **70%** | 30% cut, no listing fee, **$4.99 paid min**; PayPal payout threshold as low as $0, bank/wire quarterly $250 min |
| Booth (pixiv) | *fee unverified* | AI allowed (abuse-enforcement only, Jul 2025); **AI-heavy shops search-suppressed**; VRM resale lane |

**CivitAI LoRA economy (re-verify before relying — changes fast):** Early Access
= **100% of Buzz** to creator; **25%** of on-site generator Buzz redistributed to
resource creators; cash-out needs **Creator Score ≥ 40,000 + paid membership**;
payouts via a **monthly revenue-share pool** (~$43–46K/mo paid early 2025, avg
~$226/creator). **Earnings are top-heavy: top 1,000 creators take ~90% of all
Buzz** → treat CivitAI as lead-magnet/reputation, capture dollars on the Gumroad
mirror. **AI disclosure is now mandatory AND tied to search visibility** on
Unity, itch.io, and Fab (`CreatedWithAI`, mandatory 11 Dec 2025).

**Pricing guidance:** Unity 2D/tilesets $5–30, 3D models $5–50+; **themed bundles
consistently outsell single assets** (sell packs, never one-off files). Avoid the
oversupplied/overpriced character-3D and anime/photoreal lanes; favor props,
environment kits, and long-tail high-intent titles.

**Disclosure mechanics (pass 2):** **Fab** — mandatory "Created with AI" flag at
publish (separate from the *optional* "NoAI" training opt-out — enable both).
**CGTrader & Booth** — AI allowed, **no disclosure required** (but disclosing is
safe; Booth soft-penalizes AI-heavy shops in search). **VRM/avatar lane (Stream
E/F):** pre-made avatars resell **$30–$200** (Booth cluster ~$20–$40);
rigging-only commissions $100–$1,000+ — rigging is independently priced near a
whole static model, confirming the premium even though a hard "N× static"
multiplier on Fab/CGTrader/TurboSquid did **not** verify.

> *Still open → third pass: Booth's exact fee/payout, a marketplace-backed
> static-vs-rigged price multiplier, concrete time-to-40k Creator Score, and the
> full style demand×gap ranking (pass-2 style claims were refuted — needs live
> marketplace browsing).*

---

Per-stream monthly steady-state for a solo operator, **conservative** *(`~est`,
not additive)*:

| Stream | Realistic monthly `~est` | Notes |
|--------|--------------------------|-------|
| A Tilesets/UI | $20–200 | volume + bundles; long-tail |
| B Textures | $30–250 | low effort, steady, low risk |
| C Static props | $50–400 | scales with catalog size |
| D LoRA passive | $10–100 | top-heavy market; median is low |
| D LoRA service | $100–1,000+ | active; gated on audience/leads |
| E Rigged chars | $100–600 | premium; needs Phase 2 |
| F Animated | $150–800 | premium; needs Phase 2 |
| G Productization | $100–2,000+ | audience-gated; highest ceiling |

These are **not** additive promises — early months land at the low end of A–D
only. The thesis is: A–D fund the runway while E/F/G are built; G + D-service +
audience are where the meaningful ceiling lives.

---

## 7. Legal / policy compliance checklist (do for every listing)

- [ ] Toggle the platform's **AI-disclosure** flag (Fab + Unity require it).
- [ ] **Original IP only** — no named characters, celebrities, living artists' styles.
- [ ] **Flux-dev license:** never sell a **FLUX.1-dev-derived LoRA *file*** (it's a
      non-commercial "Derivative"). Selling the **output images/assets** is fine.
      For a sellable LoRA file, use **FLUX.1-schnell (Apache-2.0)** or another
      permissive base. (See `docs/research/flux-lora-edge-and-licensing.md`.)
- [ ] Don't market assets as "fully copyright-protected" (pure prompt→output
      likely isn't registrable; your editing/rigging strengthens but doesn't
      guarantee the claim).
- [ ] Keep dataset-provenance notes for every LoRA (defensible origin).
- [ ] Re-read the target platform's AI terms immediately before listing.

---

## 8. Open items

**Resolved — pass 1** (→ `docs/research/selling-ai-assets-best-practices.md`):
- [x] CivitAI 2026 payout mechanics, thresholds, earnings distribution.
- [x] Fab / Unity / TurboSquid / itch.io / Gumroad royalty cuts.

**Resolved — pass 2** (→ `docs/research/selling-ai-assets-followup.md`):
- [x] Fab's seller-specific AI policy ("Created with AI" mandatory; "NoAI" optional).
- [x] CGTrader royalty (60%→85% ladder) + AI rules (allowed, no disclosure req).
- [x] Booth AI policy (allowed, abuse-enforcement only; AI-heavy shops search-suppressed) + VRM resale pricing ($30–$200).
- [x] CivitAI Creator Score gate (40k + paid membership; no published formula).

**Resolved — pass 3 (live data 2026-06-29)** (→ `selling-ai-assets-followup.md` §5b):
- [x] **Style demand × gap** — live CivitAI API + itch.io top-sellers. CivitAI
  saturated by photoreal/anime/NSFW; **fantasy/stylized less saturated + bundling
  substyles wins downloads**. itch.io top sellers = **16×16 pixel RPG tiles +
  low-poly 3D kits** (confirms Streams A/K + L5/L7). Build order:
  `stylized_game → tile_topdown → lowpoly_flat → ortho_turnaround → mat_tile`.

**Resolved — pass 4 (2026-06-30)** (→ `docs/research/flux-lora-edge-and-licensing.md`):
- [x] **FLUX.1-dev commercial licensing** — selling a Flux-dev LoRA *file* is
  PROHIBITED (non-commercial "Derivative"); but **Outputs/assets are commercially
  sellable**. Sell images/assets, give Flux-dev LoRAs away free, use
  **schnell (Apache-2.0)** for any sellable LoRA file. Folded into §3 (Stream D)
  + §7. **Materially changes D0.6/D0.7.**

**Resolved — pass 5 (2026-06-30)** (→ `docs/research/flux-model-types-and-feasibility.md`):
- [x] **Top Flux LoRA category = utility/quality enhancers** (hands/anatomy/detail/
  realism), above any single art style → build a **free** utility-LoRA track for
  CivitAI Buzz/reputation (folded into §3 Stream D).
- [x] **24GB feasibility:** LoRA/QLoRA = first-class (FluxGym 12-20GB, ai-toolkit
  24GB, SimpleTuner ~18GB int8, QLoRA ~9GB). **ControlNet training (datacenter-
  scale) and full fine-tune (~120GB) are NOT solo-feasible — the LoRA is the unit.**
- [~] **Quality edge:** multi-res bucketing confirmed built-in, but the quality
  *delta* is unquantified → market repeatability/curation, not "higher quality."

**Resolved — pass 5b (2026-06-30, direct API/source)** (→ `flux-model-types-and-feasibility.md`):
- [x] **Supply-gap count is NOT API-obtainable** — CivitAI `/models` is cursor-only
  (no `totalItems`), so the Flux-vs-SDXL ratio stays *directional, not numeric*.
- [x] **Flux IP-Adapter training is NOT solo-feasible** — XLabs trains on 8-GPU
  clusters; a single 24GB can't even reliably run IP-Adapter inference. Joins
  ControlNet/checkpoint as off-limits. **The LoRA is the only feasible unit.**

**Still open** (low priority):
- Whether any **paid BFL tier** authorizes selling a Flux-dev LoRA file to the public.
- A quantified multi-res / eval-grid quality *delta* (feature confirmed, delta unmeasured).
- Confirm **schnell (Apache-2.0)** terms + dev-vs-schnell LoRA quality tradeoff.
- A marketplace-backed **static-vs-rigged price multiplier** (Fab/CGTrader/TurboSquid).
- **Booth's exact fee split + payout threshold** (only AI policy + VRM pricing verified).
- Concrete **time-to-40k CivitAI Creator Score** for a new LoRA creator.
- SVG/vector marketplace AI policies + economics (came back empty pass 1).
- Concrete ComfyUI-workflow productization revenue examples.
