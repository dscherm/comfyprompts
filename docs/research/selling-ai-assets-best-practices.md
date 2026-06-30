# Selling AI-Generated Models & Game Assets — Best-Practices Research

*Cited research report. Generated 2026-06-29 via the `deep-research` harness
(5 search angles → 22 sources fetched → 100 claims extracted → 25
adversarially verified, 23 confirmed / 2 refuted → synthesized).*

**Scope:** best practices for a solo, IP-clean, AI-disclosed creator selling
across **CivitAI, Gumroad/Ko-fi, itch.io, Unity Asset Store / Fab, CGTrader,
and Booth**, for five product lines:

1. **Style LoRAs** (Flux — e.g. the `grimforge_style` dark-fantasy LoRA) — CivitAI + Gumroad/Ko-fi mirror
2. **Seamless 2K PBR texture/material packs** — Fab, Unity, Gumroad
3. **Pixel-art / top-down RPG tilesets (16×16)** — itch.io (primary), Unity, Fab
4. **Static 3D game-ready props (GLB/FBX)** — Fab, Unity, CGTrader
5. **(Later) rigged + animated characters (VRM / Unity-Humanoid)** — Fab, Unity, Booth

> **Confidence legend:** 🟢 high (3-0 unanimous verify) · 🟡 medium (single-source
> or content-blog) · 🔴 refuted (do **not** cite — listed at the end).

---

## TL;DR — the actionable thesis

For a solo IP-clean creator in 2025-2026, **distribution is the product-market-fit
lever, not the asset.** Five moves:

1. **Disclose AI proactively everywhere** — it is now mandatory and enforced on
   every target marketplace, and on most it is *tied directly to search
   discoverability*. Non-disclosure gets you deindexed or removed.
2. **Treat CivitAI as a top-of-funnel lead magnet + reputation engine**, not a
   paycheck — its earnings are extremely top-heavy (top 1,000 creators take ~90%
   of all Buzz). Capture actual dollars on the **Gumroad/Ko-fi mirror** (~90%
   to you) and via CivitAI **Early Access** (100% of Buzz to you).
3. **Charge premium and bundle on Unity/Fab.** Cohesive *themed packs* reliably
   outsell single assets; never sell one-off files where a bundle is possible.
4. **Lead-magnet on CivitAI/itch.io** (free or pay-what-you-want) to build
   audience, then convert on the paid mirrors.
5. **Build a content funnel** (devlog / short-form / Reddit) and consider **paid
   micro-influencer outreach** — the one documented LoRA post-mortem that cleared
   >$1,000 did it through ~$5-$20/creator TikTok outreach driving ~40k views, not
   through listing more models.

---

## 1. The cross-cutting constraint: mandatory AI disclosure 🟢

*Confidence: high (3-0 unanimous on each platform component).*

AI disclosure is **mandatory and enforced across all target marketplaces**, and
on most it **directly governs discoverability** via search filters/tags. This is
the single most important operational fact in this report.

| Platform | Requirement | Enforcement / discoverability impact |
|----------|-------------|--------------------------------------|
| **Unity Asset Store** | Declare the **specific AI tools used** and **all value-adding modifications** in a dedicated "AI description" field, in plain non-marketing language. | Undisclosed AI content **and purely-AI descriptions are rejected.** |
| **itch.io** | "Generative AI" disclosure field **required for all asset creators**; selecting "yes" auto-applies the **`[AI Generated]` tag**. (Still optional for *game* devs.) | Non-compliant asset pages are **deindexed / removed from browse pages** after a grace period. |
| **Sketchfab / Fab** | Mandatory **`CreatedWithAI`** label on **all** AI-generated models from **11 Dec 2025** (expanded beyond the prior purchasable-only rule). | New **search filters rely on the label** — disclosure changes whether your model appears in filtered searches. |

**Sources:** [Unity Support](https://support.unity.com/hc/en-us/articles/16456407029524-Can-I-publish-and-sell-content-generated-with-AI-on-the-Asset-Store) ·
[itch.io disclosure thread](https://itch.io/t/4309690/generative-ai-disclosure-tagging) ·
[Game Developer — Sketchfab mandate](https://www.gamedeveloper.com/business/sketchfab-to-require-mandatory-ai-disclosure-epic-games-accounts-for-users)

> ⚠️ **Disclosure alone is not enough.** itch.io and Unity both *tolerate*
> disclosed AI assets but **actively discourage low-effort / mass-produced AI
> pages** and treat them as spam. AI tilesets/props must be disclosed **AND**
> hand-finished / curated to avoid spam treatment. (This matches your plan's
> already-chosen pivot to procedural/code-drawn pixel art and curated outputs.)

---

## 2. Platform economics — revenue splits & payouts 🟢

*Confidence: high on Unity/itch specifics (3-0); cross-platform table 2-1.*

Revenue shares favor **everything except Unity**:

| Platform | Creator share | Notes |
|----------|--------------|-------|
| **Gumroad** | **~90%** | Flat 10% on direct sales + $0.50/sale. Separate **30%** applies to marketplace/discovery-driven sales. |
| **itch.io** | **90-100%** | Seller-configurable slider, **default 10%** cut. Immediate publication, no curation. |
| **Fab** (ex-Unreal Marketplace) | **88%** | Sketchfab Store (~80%) was merged into Fab Oct 2024. |
| **TurboSquid** | **40-80%** | Tiered by exclusivity. |
| **Unity Asset Store** | **70%** | 30% cut, no listing fee, **$4.99 paid minimum**. |

**Unity payout mechanics:** monthly via PayPal (threshold settable as low as
**$0**) or quarterly via bank/wire (mandatory **$250 minimum**, earnings roll
forward until met).

**Sources:** [Unity selling guide](https://generalistprogrammer.com/tutorials/unity-asset-store-selling-guide-revenue) ·
[ansimuz — 10yr 2D-asset seller](https://medium.com/@ansimuz/where-to-sell-your-2d-game-assets-my-advice-after-10-years-of-experience-d518d6f332ff) ·
[itch.io open revenue sharing](https://itch.io/updates/introducing-open-revenue-sharing)

**Implication:** mirror everything to Gumroad/itch where you keep ~90%; use
Unity/Fab for *reach* and premium bundles where the 30% cut is worth the
millions of monthly visitors.

---

## 3. CivitAI monetization — the LoRA channel 🟢

*Confidence: high (3-0 on mechanics; proportional-split formula 2-1).*

CivitAI is the **strongest native channel for LoRAs**, via a layered Buzz stack:

- **Early Access** — gate downloads and/or on-site generation behind a Buzz
  price *you* set; **you receive 100% of the Buzz spent.** ([guide](https://education.civitai.com/civitais-guide-to-early-access/))
- **Generator compensation** — **25% of all Buzz spent in CivitAI's on-site
  generator** is redistributed to the creators of the resources used. ([update](https://civitai.com/articles/6456/creator-compensation-generator-update))
- **Creator Program (cash-out)** — requires a **minimum Creator Score of 40,000**
  **plus an active paid membership** (Bronze/Silver/Gold). Only **"Yellow Buzz"**
  from Early Access, Tips, and Generator Compensation is bankable; Buzz from
  bounties/contests/cosmetics/membership/purchases is **excluded.** ([guide](https://education.civitai.com/civitais-guide-to-earning-with-the-creator-program/))
- **Likeness prohibition** — monetization is banned on content reproducing real
  people. *Your original-training-data posture keeps you clear of this.* ([policy](https://civitai.com/articles/13632/policy-and-content-adjustments))

**Payout model (changed mid-2025):** the old fixed **1,000 Buzz = $1** (minus 30%
fee → effectively **$0.70 / 1,000 Buzz**) was replaced by a **monthly Creator
Compensation Pool** funded from a share of the prior month's revenue, split
proportionally by each creator's banked-Buzz share — e.g. a 2% share of a
$35,000 pool pays $700. Real cycles: **~$43K paid March 2025** to 254 creators
(avg ~$226), rising to **~$46,472 in April 2025** (top earner ~$8.5K).
**Sources:** [evolving the program](https://civitai.com/articles/11163/evolving-our-creators-program-the-next-chapter) ·
[issues & solutions](https://civitai.com/articles/11274/new-creators-program-issues-and-solutions)

> 🟢 **Earnings are extremely concentrated — do NOT model income on top-creator
> figures.** Top 10 creators ≈ 10% of all Buzz, top 100 ≈ 60%, top 1,000 ≈ 90%;
> the ~1,000th-ranked creator earned roughly **$2** for the cycle.
> ([data](https://civitai.com/articles/11274/new-creators-program-issues-and-solutions))
> **Takeaway:** CivitAI = lead magnet + reputation + Early-Access Buzz, with the
> real dollars captured on Gumroad/Ko-fi mirrors.

---

## 4. Demand, pricing & thin-supply gaps

### Unity Asset Store price bands 🟡
*Confidence: medium (verbatim-verified but single content-blog source).*

| Category | Range | Note |
|----------|-------|------|
| 3D models | $5-$50+ | singles $5-$15 · mid $15-$30 · premium $30-$50+ |
| 2D art / sprites / **tilesets** | $5-$30 | **cohesive style packs outperform single assets** |
| Shaders / VFX | $10-$60+ | |
| Audio packs | $5-$30 | |
| Editor tools | $15-$80+ | |
| Game templates | $20-$100+ | |

**Bundles/cohesive style packs consistently outsell single assets** — sell PBR
materials and props as **themed bundles**, never one-off files.
**Source:** [Unity selling guide](https://generalistprogrammer.com/tutorials/unity-asset-store-selling-guide-revenue)

### itch.io is the right *primary* for 2D 🟢
10%-or-lower configurable commission, **immediate publication, no curation**,
pay-what-you-want support. Trade-off vs Unity: Unity has a higher 30% cut and a
multi-week approval (~10 business days, can run several weeks) but **millions of
monthly visitors** and requires building Unity packages.
**Sources:** [ansimuz](https://medium.com/@ansimuz/where-to-sell-your-2d-game-assets-my-advice-after-10-years-of-experience-d518d6f332ff) ·
[itch.io about](https://itch.io/docs/general/about) · [itch.io quality guidelines](https://itch.io/docs/creators/quality-guidelines)

> 🟡 **Reality check on itch.io revenue** (forum/post-mortem sentiment): itch.io
> is widely described as a **prototyping/validation and audience channel, not a
> reliable revenue channel** — "you will not make money from itch.io, nobody
> does" is a common (hyperbolic) refrain, and traffic is highly skewed (one
> survey: median game **1,582 lifetime views** vs **54,483 average**). Use it for
> reach and lead-magnets; expect dollars elsewhere.
> ([howtomarketagame traffic benchmark](https://howtomarketagame.com/2025/05/12/benchmark-itch-io-traffic/))

### 3D demand signals 🟡
CGTrader data indicates **cars ≈ 22% of revenue** but the **best-*converting***
categories are space, food, and animals, while **character models are often
overpriced/oversupplied**. Long-tail specific queries ("game ready medieval
barrel PBR Unity") signal **high purchase intent** and convert better than broad
keywords. **Source:** [CGTrader best-sellers](https://www.cgtrader.com/blog/infographic-best-selling-3d-models-and-practices)

---

## 5. Listing & SEO best practices 🟡

*Confidence: medium (content-blog sourced, directionally reliable).*

- **Title formula for 3D/props:** `[Style] + [Object] + 3D Model – [Main Use]`
  e.g. *"Medieval Wooden Barrel 3D Model – Game-Ready Prop"*. ([3DSkillUp](https://3dskillup.art/keyword-research-for-3d-assets/))
- **Three search levers:** tags, keywords, and product **name** — items only
  surface if target keywords appear in the search fields/description. ([gamediscover](https://newsletter.gamediscover.co/p/seo-on-game-platforms-why-dont-we))
- **Target long-tail, high-intent queries** over broad heads — lower volume, far
  higher conversion, and you can actually rank.
- **Gallery presentation matters** — lead with your two strongest images (e.g.
  for the GrimForge listing: character sheet + environment as the cover pair, per
  the existing `grimforge_listing.md`).
- **Per-image generation metadata** on CivitAI (prompt + weight) lets buyers
  "copy generation data," which drives downloads/engagement.

---

## 6. Distribution & the marketing funnel — the real lever 🟡

*Confidence: medium (single self-reported post-mortem, but internally consistent).*

**The asset doesn't sell itself — distribution does.** Documented post-mortem:
one LoRA creator made **>$1,000 in 3 months** by:

- Messaging **100+ TikTok creators** (~**10% response rate**),
- Paying **$5-$20 per creator** scaled to channel size,
- Generating **~40,000 combined YouTube/TikTok views** feeding the funnel.

(A parallel reading of the same creator: $3.99/generation × 251 paying customers
≈ $1,000+ via Stripe.) **Source:** [How I made >$1000 in 3 months selling LoRAs](https://civitai.com/articles/2684/how-i-made-over-dollar1000-in-3-months-selling-loras)

Combined with the earnings-concentration finding, the lesson is unambiguous:
**breaking out of the long tail requires deliberate marketing spend + a
devlog/short-form funnel, not listing more assets.** This validates your
plan's **Stream H (content funnel)** as a top-priority lever, not a nice-to-have.

---

## 7. Per-product-line playbook

### Line 1 — Style LoRAs (`grimforge_style`)
- **Primary:** CivitAI. Use **Early Access** (100% Buzz to you) for new
  versions; free download after the gate window to maximize reach + reputation.
- **Capture dollars** on the **Gumroad/Ko-fi mirror** (~90% to you) — bundle the
  `.safetensors` + usage card + example prompts (already drafted).
- **Funnel:** post the build-log/devlog (already drafted) + short-form; consider
  $5-$20 micro-influencer outreach once you have 2-3 LoRAs to cross-sell.
- Don't expect Creator-Program cash early (40k score is far off) — treat Buzz as
  reputation, not income, at first.

### Line 2 — Seamless 2K PBR texture packs
- **Sell as themed bundles** ("Fantasy Environment Materials Vol.1" — already
  built) on **Fab (88%)** and **Gumroad (~90%)**; use **Unity (70%)** for reach.
- Price in the **$5-$30** band for 2D-surface packs; bundles > singles.
- Disclose AI in Unity's AI-description field + Fab's `CreatedWithAI` label.

### Line 3 — Pixel-art / top-down RPG tilesets
- **Primary: itch.io** (90-100% to you, instant publish, PWYW). Mirror to
  Unity/Fab for reach.
- **Must be hand-finished/curated** (your procedural pivot already satisfies the
  anti-spam bar) and AI-disclosed where applicable.
- itch.io is a **reach/validation** channel — pair with a free lead-magnet
  tileset to build a follower base, sell Vol.2+ as paid.

### Line 4 — Static 3D game-ready props
- **Fab (88%) + CGTrader + Unity (70%).** Sell as **themed kitbash/prop packs**,
  not single props.
- **Lean into the high-converting / thin-supply categories** (avoid the
  oversupplied/overpriced character-model lane; favor props, environment kits,
  and specific high-intent niches).
- **Title for long-tail intent:** `[Style] [Object] 3D Model – Game-Ready Prop`.
- **`CreatedWithAI` label is mandatory on Fab from 11 Dec 2025.**

### Line 5 — (Later) rigged + animated characters
- **Fab + Unity + Booth (VRM).** This is the **premium tier** — rigged/animated
  commands a real price premium over static (exact multiplier unverified — see
  open questions).
- Gate behind your plan's rig/anim hardening (RIG-PRODUCT / ANIM-PRODUCT) before
  listing; broken weights/foot-slide will tank reviews.

---

## 8. Caveats — re-verify before relying

- **Time-sensitivity is the biggest risk.** CivitAI's Buzz economy and Creator
  Program changed materially between early- and mid-2025 (fixed rate → revenue
  pool) and will keep shifting. **Re-verify all CivitAI figures** (40k score
  threshold, 30% fee, $0.70/1,000, pool sizes) immediately before relying on them.
- **Sketchfab/Fab's mandatory `CreatedWithAI` label (11 Dec 2025)** and itch.io's
  asset-disclosure enforcement are recent and partly **report-driven**, so
  practical strictness may evolve.
- Several quantitative findings (Unity price bands, cross-platform split table,
  the >$1,000 post-mortem, influencer metrics) rest on **content blogs or a single
  self-reported source** — directionally reliable, not precise.
- The **"Sketchfab Store 80%"** figure is **historical** (merged into Fab Oct 2024).
- **Disclosure ≠ permission to dump.** Both itch.io and Unity penalize
  low-effort/mass-produced AI pages; curate and hand-finish.

---

## 9. 🔴 Refuted claims — do NOT cite

Both were adversarially killed (0-3):

1. **"CivitAI's generator pool gives checkpoints 25% while LoRAs/others split the
   remaining 75% equally."** — False. The verified mechanic is that **25% of
   generator Buzz goes to resource creators**, with no such checkpoint/LoRA split.
   ([source](https://civitai.com/articles/6456/creator-compensation-generator-update))
2. **"The Jan-2025 effective payout rate was ~7,585 Buzz = $1."** — False/unsupported.
   ([source](https://civitai.com/articles/11274/new-creators-program-issues-and-solutions))

---

## 10. Open questions (not resolved by this pass)

1. Do disclosed-AI assets convert/refund **worse** than non-AI equivalents on
   Fab/Unity/CGTrader, or does the label just *filter* the audience?
2. What is **Fab's specific** 2025-2026 AI policy/mechanism (distinct from
   Sketchfab's)? Fab is your named primary for textures/props/characters but
   wasn't directly covered by verified claims.
3. **CGTrader and Booth** current AI policies, revenue splits, and
   **rigged-vs-static price premiums** — named in the plan, no verified evidence yet.
4. Realistic **time-to-40,000 Creator Score** for a new style-LoRA creator, and
   what a non-top-1,000 creator can actually expect from the monthly pool.

---

## 11. Source quality ledger

**Primary sources** (platform docs / first-party): Unity Support, itch.io
disclosure thread + docs, CivitAI policy/education/program articles (13632, 6456,
11163, Early Access & Creator Program guides). **Secondary:** Game Developer
(Sketchfab mandate), CGTrader best-sellers, gamediscover SEO. **Blog/forum
(treat as directional):** ansimuz (Medium), generalistprogrammer (Unity guide),
3DSkillUp, howtomarketagame, the >$1,000 LoRA post-mortem, itch.io seller forums.

*Full URL list in the research run output. 22 sources fetched, 8 findings
survived synthesis.*

---

## 12. Feedback into BUSINESS-PLAN-TASKS.md

This report directly serves several open tasks:

- **B0.4** (re-run market research; fold verified numbers into BUSINESS-PLAN §6) —
  **substantially addressed.** Revenue splits, CivitAI economy, and price bands
  here are the verified numbers to fold in. *Remaining gap:* Fab-specific policy,
  CGTrader/Booth splits, rigged-vs-static premium (open questions 2-4).
- **D0.6 / B0.8 / A0.4** (listings) — apply the per-line playbook (§7): bundle,
  long-tail titles, AI-disclosure fields, Gumroad mirror for dollar capture.
- **LoRA catalog "demand × gap"** (currently *reasoned, not verified*) —
  partially supported: bundles>singles, avoid oversupplied character/anime lanes,
  itch.io 16×16 tile demand. Still hypothesis-level on specific LoRA picks.
- **Stream H (content funnel)** — elevated from nice-to-have to **the primary
  revenue lever** by the distribution findings.
