# Selling AI Assets — Focused Follow-up Research (2025–2026)

> Second-pass research for a solo, IP-clean AI-asset creator selling Flux style LoRAs,
> seamless PBR texture packs, 16x16 pixel-art tilesets, static game-ready props, and
> (later) rigged/animated VRM + Unity-Humanoid characters. All AI-generated from original
> training data, with AI-disclosure enabled.
>
> Companion to `selling-ai-assets-best-practices.md` (first pass). This file is additive.
> Findings below survived a 3-vote adversarial verification pass (25 confirmed claims).
>
> **Compiled:** 2026-06-29

---

## 1. Fab.com AI Policy (distinct from legacy Sketchfab)

**Bottom line: AI-generated content is explicitly permitted for sale on Fab. The policy is
disclosure-based, not prohibition-based. Two separate, independent mechanisms exist — do not
conflate them.**

### 1a. "Created with AI" — mandatory AI-origin disclosure (seller-facing)

Fab requires any publisher who uses generative AI to create a product to enable the
**"Created with AI"** self-declaration flag on that product. This is **mandatory, not
optional**, and is enforced at publish time.

- Fab support: *"Fab requires publishers who use AI to generate content for distribution to
  enable the Created with AI flag on those products."*
  ([support.fab.com — Generative AI](https://support.fab.com/s/article/Generative-Artificial-Intelligence-AI?language=en_US),
  [support.fab.com — NoAI + Created with AI](https://support.fab.com/s/article/Introducing-NoAI-meta-tags-and-Created-with-AI-self-declaration?language=en_US))
- Epic's official announcement (May 22, 2025) confirms the flag became mandatory during the
  publishing flow: *"We'll be making it mandatory during the publishing process for creators
  to select whether their asset was created with a Generative AI Program or not,"* and
  *"Content that's not identified properly with the 'Created with AI' setting violates Fab
  terms."* ([forums.unrealengine.com](https://forums.unrealengine.com/t/update-on-products-generated-with-ai/2523501))
- AI-generated 3D models, textures, and 2D assets are all permitted, provided the flag is set.
  ([fab.com/distribution-agreement](https://www.fab.com/distribution-agreement))

**Evolution:** The flag started as voluntary self-declaration and became mandatory-at-publish
during 2025. Epic acknowledged enforcement gaps (some AI assets mislabeled "not created with
AI"), but the requirement itself is real and enforceable.

> **Action for the creator:** This is already your stated practice ("AI-disclosure on"). Keep
> the "Created with AI" flag enabled on every Flux-derived texture, prop, and (later) character
> listing. Non-disclosure is a ToS violation that risks takedown.

### 1b. "NoAI" meta tag — buyer-side training opt-out (a different control)

Distinct from disclosure, Fab offers an HTML **"NoAI"** meta tag, enabled via the
**"Disallow use by generative AI"** checkbox on a product's page in the Fab Publisher Portal.
It signals that your product **must not be used as training data** for generative AI programs.

- *"Fab offers an HTML 'NoAI' meta tag that indicates to generative AI programs that a product
  is not to be used for generative AI data collection, which you can add by ticking the
  'Disallow use by generative AI' checkbox on a product's page in the Fab Publisher Portal."*
  ([support.fab.com](https://support.fab.com/s/article/Introducing-NoAI-meta-tags-and-Created-with-AI-self-declaration?language=en_US))

> Do not confuse the two: **"Created with AI"** = *"I made this with AI"* (mandatory).
> **"NoAI"** = *"don't train on my asset"* (optional, your choice as seller).

### 1c. Fab revenue split and payout terms

- **88% revenue share to sellers; Fab/Epic retains 12%** (88/12 split, set at Fab's Oct 2024
  launch and unchanged into 2025–2026).
  ([fab.com/distribution-agreement](https://www.fab.com/distribution-agreement),
  [support.fab.com — Payout](https://support.fab.com/s/article/Payout?language=en_US),
  corroborated by Epic's UE launch blog and Game Developer)
- **$100 USD minimum payout threshold.** Payouts issue ~30 days after the end of each month
  with ≥$100 earned; amounts below $100 roll over month-to-month until the threshold is met
  (rollover also terminates at calendar year-end; earnings unpaid >1 year are paid regardless).
  ([support.fab.com — Payout](https://support.fab.com/s/article/Payout?language=en_US),
  [dev.epicgames.com publisher docs](https://dev.epicgames.com/documentation/en-us/fab/publisher-get-started-in-fab))
- Note: a temporary 100%-revenue promo ran from launch through end of 2024 — it has ended;
  88% is the standing rate.

### 1d. How Fab differs from legacy Sketchfab

Sketchfab (also Epic-owned) historically used the **"CreatedWithAI"** tag, originally scoped
to models under a redistribution-permitting license (Creative Commons / standard Sketchfab
License). ([sketchfab.com/blogs/community](https://www.sketchfab.com/blogs/community/introducing-the-noai-createdwithai-tags/))

**As of December 11, 2025, Sketchfab broadened this:** the "CreatedWithAI" label is now
required on **every** AI-generated model, regardless of whether it is downloadable or saleable
— so new search filters can find/exclude AI content.
([gamedeveloper.com](https://www.gamedeveloper.com/business/sketchfab-to-require-mandatory-ai-disclosure-epic-games-accounts-for-users),
[sketchfab.com blog](https://www.sketchfab.com/blogs/community/introducing-the-noai-createdwithai-tags/))

**Practical read:** Fab and Sketchfab are converging toward the same Epic policy — mandatory
AI-origin disclosure on all AI content + an optional NoAI training opt-out. If you cross-list
on both, expect to tag identically.

---

## 2. CGTrader & Booth

### 2a. CGTrader — payout system (26-level tiered royalty)

Effective **June 2, 2025**, CGTrader runs a **26-level payout system, 60%–85%**, +1% per level
as cumulative **rolling 365-day** net sales cross each threshold.

- **Level 1 (new sellers): $0 threshold → 60% payout** (the lowest rate; this was a reduction
  from the prior ~70% standard, which drew seller backlash).
- **Level 26: $300,000+ rolling sales → 85% payout.** Level 2 = $50 → 61%.
- Levels upgrade/downgrade prospectively as rolling sales move; rate changes are not
  retroactive.
- ([help.cgtrader.com — Payout Rate System](https://help.cgtrader.com/hc/en-us/articles/35293756906257-Payout-Rate-System-Explained),
  [cgtrader.com/pages/earnings-and-payout-schedule](https://www.cgtrader.com/pages/earnings-and-payout-schedule))

> **Reality for a solo new seller:** you keep **60%** of each sale until volume grows — the
> least generous starting split of the major marketplaces studied (vs Fab's flat 88%). CGTrader
> only becomes competitive at high cumulative volume.

### 2b. CGTrader — AI policy

- **AI-generated assets are allowed; no explicit AI-disclosure requirement on sellers.**
  CGTrader's terms do not forbid selling AI-made content, and contain no labeling/transparency
  obligation for AI-generated uploads. Sellers must, however, warrant assets are their own
  original work.
  ([cgtrader.com/pages/terms-and-conditions](https://www.cgtrader.com/pages/terms-and-conditions),
  [cgtrader.com/pages/cgtrader-content-policy](https://www.cgtrader.com/pages/cgtrader-content-policy))
- The **"Royalty Free License, No AI"** is a **buyer-side** restriction: it forbids the *buyer*
  from using the purchased product for ML / neural-network / generative-AI training. It does
  **not** restrict sellers from listing AI-generated assets. (Same terms as standard Royalty
  Free, *"except that product use for machine learning or training of neural network models,
  including generative AI models, is not permitted."*)
  ([cgtrader.com/pages/terms-and-conditions](https://www.cgtrader.com/pages/terms-and-conditions))

> Even though CGTrader does not *require* disclosure, the creator's stated "AI-disclosure on"
> posture is still safe here — disclosing voluntarily does not violate any CGTrader term.

### 2c. Booth.pm (pixiv) — AI policy now verified (2nd pass)

Booth's **AI policy** is now confirmed from primary platform announcements (its fee/payout
specifics remain an open question — see end).

- **AI-generated works are allowed; no blanket ban.** On **July 18, 2025** BOOTH issued an
  official policy, *"BOOTHにおけるAI生成作品への対応強化について"* ("Strengthening Responses to
  AI-Generated Works on BOOTH"), framed as **enforcement against abuse**, not prohibition. It
  targets specific abuse patterns — high-fidelity imitation of a named artist via trained
  models, repeat copyright infringement, and spam-posting that degrades search — with penalties
  (product removal, shop closure, account suspension) aimed at violators and recidivists.
  ([booth.pm/announcements/828](https://booth.pm/announcements/828))
- **No general AI-disclosure label/tag is required** of sellers. The policy mandates no
  AI-labeling obligation; it polices infringing imitation and undifferentiated mass-produced
  output, not failure-to-disclose. (An earlier notice, [booth.pm/announcements/646](https://booth.pm/announcements/646),
  similarly imposes no flag/tag requirement.)
- **Practical penalty caveat:** pixiv offers an *optional* "AI-generated" flag, and since May
  2023 BOOTH has made AI-heavy shops **non-discoverable in search**. So selling original
  AI-generated assets is permitted and needs no disclosure tag, but heavy AI catalogs lose
  organic search visibility — a real soft penalty for a solo seller relying on discovery.

> For the creator's "AI-disclosure on" posture: BOOTH neither requires nor rewards a disclosure
> tag, and a visibly all-AI shop can be search-suppressed. If selling VRM avatars here, lead
> with original characters (not artist-imitation), keep catalogs varied, and expect to drive
> traffic externally (Twitter/X, Gumroad cross-link) rather than relying on BOOTH search.

---

## 3. Rigged/Animated vs. Static — Price Premium & VRM Avatar Pricing

The verified data here is **VTuber/VRM-specific** (the creator's "later" character lane). A
clean static-vs-rigged *multiplier* on TurboSquid/CGTrader did **not** survive verification —
treat that as an open question. What is well-supported:

### 3a. Custom commissioned 3D VRM models (2026)

- **Basic: $300–$800 · Mid-tier: $800–$2,500 · Pro-tier: $3,000–$10,000+**
  ([news.viverse.com](https://news.viverse.com/post/vtuber-model-pricing-2026); corroborated by
  vtubermodels.com and general industry figures of $1,000–$10,000+).
  *Caveat: all sources are commission-studio marketing blogs; some place the custom-3D floor
  nearer $1,000–$2,000 rather than $300–$800. This is commission cost, not resale price.*

### 3b. Pre-made (non-custom) VTuber/VRM models — the relevant resale lane

- **$30–$200** on marketplaces like **Booth and Gumroad** (some listings start ~$8; Booth
  listings commonly ~¥4,000–¥7,000 ≈ $30–$50).
  ([vtubermodels.com](https://vtubermodels.com/how-much-do-vtuber-models-cost/),
  [arwall.co](https://arwall.co/blogs/arwall-blogs/how-much-do-vtuber-models-cost), booth.pm
  listings) — **high confidence**, reproduced across multiple 2025–2026 sources.
- **Booth VRChat/VRM avatar band (now primary-verified):** **200 JPY → 9,000 JPY**, with most
  individual character avatars clustering **3,000–6,000 JPY (≈ $20–$40)** and premium models
  6,000–9,000 JPY. Independent Japanese buying guides put the typical Humanoid body at
  3,000–7,000 JPY (avg ~5,000). Named best-sellers confirm the mid-premium band: **Kipfel
  5,500 JPY, Mafuyu (真冬) 6,000 JPY, Nemesis (ネメシス) 3,500 JPY** (the last with face-tracking
  + Quest/VRM support; Nov 2025 outfit ecosystem confirms popularity).
  ([booth.pm VRChat avatar listings](https://booth.pm/en/browse/3D%20Models?q=vrchat+avatar),
  boothplorer.com/avatar/5007531, komainu-street.booth.pm/items/5986971) — **high confidence.**

### 3c. The rigging premium, expressed as a standalone service

- **Rigging-only (no base model): $100–$1,000.** Riggers price "rig only" roughly 30–40% below
  full art+rig packages; premium/cinematic rigging exceeds $1,000.
  ([vtubermodels.com](https://vtubermodels.com/how-much-do-vtuber-models-cost/),
  [arwall.co](https://arwall.co/blogs/arwall-blogs/how-much-do-vtuber-models-cost)) —
  *2-1 vote; blog-quality but cross-corroborated.*

> **Inference (not a hard multiplier):** the rig itself is independently valued at roughly the
> same magnitude as an entire pre-made model ($30–$200), and commissioned rigging ($100–$1,000)
> often exceeds the price of a static pre-made. This indicates rigging adds substantial,
> separately-priced value — but a precise "rigged sells for N× static" figure on the general 3D
> marketplaces (Fab/CGTrader/TurboSquid) was **not** verifiable here.

---

## 4. CivitAI Creator Score — The Cash-Out Reality

### 4a. Eligibility gate

To cash out you need **both**:
1. **Creator Score ≥ 40,000**, and
2. **An active paid CivitAI membership** (Bronze, Silver, or Gold). A lapsed membership halts
   Buzz banking.
- ([education.civitai.com — Earning guide](https://education.civitai.com/civitais-guide-to-earning-with-the-creator-program/))

### 4b. How the score is calculated — no published formula

CivitAI does **not** publish a concrete formula, weights, or metrics. It is described only as a
composite of *"your participation in the Civitai community, including your activity and how
others engage with the content and models you create."*
([education.civitai.com](https://education.civitai.com/civitais-guide-to-earning-with-the-creator-program/))

### 4c. The earning mechanism (what actually feeds the score / payout)

- Creators earn **Buzz** when resources they uploaded (e.g. LoRAs) are used by others in the
  **on-site Image Generator** — receiving a cut of the generation cost. Specifically, **25% of
  all Buzz spent in the Generator is distributed to the creators of resources used** (25% of
  that to the checkpoint, 75% split among other resources like LoRAs).
  ([education.civitai.com — Buzz guide](https://education.civitai.com/civitais-guide-to-on-site-currency-buzz-%E2%9A%A1/),
  [civitai.com/articles/6456](https://civitai.com/articles/6456))
- Payment comes from a **monthly Creator Compensation Pool** funded by a portion of the
  *previous month's platform revenue*, distributed **proportionally to each creator's share of
  banked Buzz**. (Example: $35,000 pool, your banked Buzz = 2% of total → you receive $700.)
  ([civitai.com/articles/11163](https://civitai.com/articles/11163/evolving-our-creators-program-the-next-chapter))

### 4d. The dollar reality (March 2025 first cycle — primary data)

- Conversion rate: **$0.81 per 1,000 Buzz Banked** — *variable*, tied to platform performance
  (vs the prior fixed Beta $0.70/1,000).
- **Average payout: $226 · Median payout: $81.00 · Highest earner: $8,505.72** (from 10.5M
  Banked Buzz). Total ~$43K paid across **254 creators**.
  ([civitai.com/articles/13199](https://civitai.com/articles/13199/civitai-creator-program-update-a-successful-first-cycle))

> **Time-to-threshold for a new style-LoRA creator:** Working backward from primary data —
> the 40,000 Creator Score cash-out gate is a *score* (not Buzz), and CivitAI publishes **no
> formula**, so no defensible "X downloads in Y months" estimate can be made from the verified
> evidence. The median payout of **$81** and the requirement to *pay* for a membership to even
> bank Buzz tell the real story: **for a typical new creator, CivitAI is a marketing/discovery
> channel and a small supplementary income stream, not a primary revenue source.** Treat the
> concrete time-to-40,000 as an **open question** — no creator post-mortem with a verified
> timeline survived this pass.

---

## 5. Style Recommendations (high-demand × thin-supply)

**This section did NOT survive adversarial verification.** None of the 25 confirmed claims
contain marketplace-backed evidence ranking specific art styles by demand vs. saturation for
Flux LoRAs or game-asset packs. Rather than present unverified style picks as findings, this
is flagged honestly as the **largest gap** in this pass and the top priority for a third pass.

What *can* be said from adjacent verified evidence:
- The **VRM/VTuber character lane has documented, reproducible buyer pricing** ($30–$200
  pre-made; §3), making it a concretely monetizable niche the creator already plans to enter.
- CivitAI's earning model rewards **LoRAs that get used in the on-site Generator** (§4c) — so
  styles that are *generically useful for image generation* (broad utility, repeated reuse)
  monetize better on CivitAI than narrow one-off styles, independent of which aesthetic.

### 5b. THIRD PASS — live marketplace data (2026-06-29, direct fetch)

The refuted pass-2 style claims were a **false negative** from weak search-snippet
evidence. Pulling the **live data directly** — CivitAI's public JSON API (bypasses
the JS-SPA that WebFetch couldn't read) and itch.io's server-rendered top-sellers
page — resolves the question. *(Method note: direct API/HTML fetch, not the verified
claim corpus; treat as a current snapshot, not adversarially triple-verified.)*

**CivitAI — most-downloaded Flux.1 D LoRAs (live API):**
- **Saturated / dominant:** photorealism & hyperrealism (the #1 lane by far —
  "Hands" utility LoRA ~292k DLs; UltraRealistic, XLabs Realism), **broad "style"**,
  **anime/Pony**, **character/woman/girl**, **fantasy**, **NSFW**, and utility/detail
  enhancers (hands, skin).
- **Thin / largely absent from the top tiers:** **pixel art, watercolor, oil
  painting / traditional media, flat-minimalist design, pure cyberpunk,
  clothing-specific.**
- **Winning pattern:** the top fantasy entry ("Velvet's Mythic Fantasy Styles",
  ~214k DLs) **bundles multiple substyles under one model** — direct live
  confirmation of the "breadth = downloads/Buzz" thesis from §4.

**itch.io — top-selling game-asset packs (live):** dominated by **16×16 pixel-art
RPG tilesets** (Modern Interiors/Exteriors/Office/Farm), **low-poly 3D kits**
(KayKit, $99), pixel-art character packs, pixel UI/HUD, and cute pixel farming sets
(Sprout Lands, Tiny Farm). **This live data CONFIRMS exactly what pass-2 refuted:**
16×16 tilesets and low-poly 3D *are* the proven itch.io best-seller categories.

**Demand × gap synthesis (now evidence-backed):**

| Lane | CivitAI (LoRA) read | itch.io (asset) read | Verdict for this creator |
|------|--------------------|----------------------|--------------------------|
| Photoreal / anime / NSFW | saturated, not your edge / IP-risky | n/a | **avoid** |
| Stylized & dark fantasy (painterly) | high demand, less saturated than photoreal; bundle substyles | fantasy themes sell | **GrimForge + `stylized_game` — strongest LoRA play** |
| 16×16 top-down RPG tiles | thin on Flux | **#1 itch.io seller** | **`tile_topdown` (L5) feeds the top itch category** |
| Low-poly 3D / flat | thin on Flux | **#2 itch.io seller (KayKit-style kits)** | **`lowpoly_flat` (L7) + Stream K kits — proven demand** |
| Pixel / watercolor / traditional-media LoRA | genuinely thin supply | pixel sells as *assets* | opportunistic LoRA niche (thin supply = unproven LoRA demand; safer as asset packs) |
| Multi-view turnaround (`ortho_turnaround`) | rare (3D-data moat) | — | **defensible moat; sells to image→3D crowd** |

**Build order, now evidence-backed:** `stylized_game` (L4, bundle substyles) →
`tile_topdown` (L5, feeds #1 itch seller) → `lowpoly_flat` (L7, feeds #2 itch
seller + Stream K) → `ortho_turnaround` (L3, moat) → `mat_tile` (L1, thin Flux
material supply).

**Sources (live, 2026-06-29):** [itch.io top-sellers](https://itch.io/game-assets/top-sellers) ·
CivitAI API: `civitai.com/api/v1/models?types=LORA&sort=Most Downloaded&baseModels=Flux.1 D`
(and `&tag=style`).

---

## Cross-Platform Summary Table

| Platform | AI assets allowed? | Disclosure required? | Seller split | Payout threshold |
|---|---|---|---|---|
| **Fab** | Yes | **Yes — "Created with AI" mandatory at publish** | **88%** | **$100** |
| **Sketchfab** | Yes | **Yes — "CreatedWithAI" on ALL AI models (since Dec 11 2025)** | (Epic-owned; migrating to Fab) | — |
| **CGTrader** | Yes | **No explicit requirement** (warrant original work) | **60% → 85%** (26-level, rolling 365-day) | — |
| **CivitAI** | Yes (its whole model) | (platform-native) | Pool-proportional; ~$0.81/1k Buzz | Creator Score **≥40,000** + paid membership |
| **Booth** | **Yes** (no blanket ban; abuse-enforcement only, since Jul 18 2025) | **No** label required (but AI-heavy shops are search-suppressed) | *Fee/payout unverified* | *Unverified* |

---

## Sources

Primary platform docs and official announcements (highest weight):
- Fab: support.fab.com (Generative AI; NoAI + Created with AI; Payout), fab.com/distribution-agreement, dev.epicgames.com publisher docs
- Epic: forums.unrealengine.com/t/update-on-products-generated-with-ai/2523501
- Sketchfab: sketchfab.com/blogs/community/introducing-the-noai-createdwithai-tags
- CGTrader: help.cgtrader.com Payout Rate System, cgtrader.com earnings-and-payout-schedule, terms-and-conditions, content-policy
- CivitAI: education.civitai.com (earning guide; Buzz guide; Creator Score 40k gate), civitai.com articles 6456 / 11163 / 13199
- BOOTH (pixiv): booth.pm/announcements/828 (Jul 18 2025 AI-enforcement policy), booth.pm/announcements/646, booth.pm/en/browse/3D Models?q=vrchat+avatar (VRM pricing)

Secondary / corroborating: gamedeveloper.com, 80.lv, CG Channel

Blog-quality (pricing, lower confidence): news.viverse.com, vtubermodels.com, arwall.co
