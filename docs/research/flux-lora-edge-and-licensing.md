# Flux LoRA — Commercial Licensing, Quality Edge & Model Ideas

*Cited research report. Generated 2026-06-30 via the `deep-research` harness
(5 angles → 19 sources → 87 claims → 25 verified, 24 confirmed / 1 refuted →
5 findings). Companion to the two `selling-ai-assets-*` reports.*

> **Confidence:** 🟢 high (3-0) · 🟡 medium · 🔴 refuted · ⬜ unanswered this pass.

> ⚠️ **This is not legal advice.** It summarizes primary license text; consult a
> lawyer before relying on it for a commercial decision.

---

## 🚨 BOTTOM LINE (Q1 — the one that matters)

**Selling a LoRA trained on / targeting FLUX.1-dev is PROHIBITED** under the
default **FLUX.1 [dev] Non-Commercial License**. But there's a clean, decisive
split that *rescues most of the business plan*:

| Thing | Sell it commercially? |
|-------|----------------------|
| **The LoRA `.safetensors` weights** (e.g. `grimforge_style`) | ❌ **NO** — a LoRA is a "Derivative"; Derivatives are non-commercial-only |
| **The OUTPUT images** the LoRA generates | ✅ **YES** — BFL claims no ownership of outputs; explicitly commercial-OK |
| **3D models / textures / tilesets** *derived from* those output images | ✅ **YES** — they're downstream of Outputs, not the weights |

**So:** your **asset products** (texture packs, tilesets, 3D village kits, image
products — all of which are *Outputs* or downstream of them) are **fine to sell.**
What's **not** clear-to-sell is the **LoRA file itself** (the GrimForge listing,
task D0.6) and the **custom-LoRA-as-a-service** deliverable — because both
distribute a Flux-dev *Derivative* commercially.

---

## 1. FLUX.1-dev commercial licensing 🟢

### 1a. The base license is non-commercial, and it binds Derivatives
FLUX.1-dev weights ship under the **FLUX.1 [dev] Non-Commercial License**
(v2.0, last revised 2025-11-25; HF mirrors v1.1.x). Verbatim:

> *"You may only access, use, Distribute, or create Derivatives of the FLUX.1
> [dev] Model or Derivatives for Non-Commercial Purposes."*

The newer **FLUX.1-Krea-dev** (2025-07-31) uses the identical license — the
non-commercial regime governs new dev releases too.
**Sources:** [HF model card](https://huggingface.co/black-forest-labs/FLUX.1-dev) ·
[LICENSE.md](https://huggingface.co/black-forest-labs/FLUX.1-dev/blob/main/LICENSE.md) ·
[bfl.ai non-commercial terms](https://bfl.ai/legal/non-commercial-license-terms)

### 1b. A LoRA IS a "Derivative" → selling the weights is prohibited 🟢
> *"'Derivative' means any (i) modified version of the FLUX.1 [dev] Model
> (including but not limited to any customized or fine-tuned version thereof)…"*
> and *"Any restrictions … regarding the FLUX.1 [dev] Model also apply to any
> Derivative you create."*

"Non-Commercial Purpose" **excludes** use *"(a) for revenue-generating activity,
(b) in direct interactions with or that has impact on end users, or (c) to train,
fine-tune or distill other models for commercial use."* BFL/HF even self-list
LoRAs (e.g. *FLUX.1 Depth [dev] LoRA*) as covered Derivatives.
→ **Distributing or selling a Flux-dev LoRA weights file is outside the free grant.**
**Sources:** [LICENSE.md](https://huggingface.co/black-forest-labs/FLUX.1-dev/blob/main/LICENSE.md) ·
[GitHub license](https://github.com/black-forest-labs/flux/blob/main/model_licenses/LICENSE-FLUX1-dev) ·
[bfl.ai/licensing](https://bfl.ai/licensing)

### 1c. OUTPUTS are carved out — commercial use is allowed 🟢
> *"We claim no ownership rights in and to the Outputs… You may use Output for
> any purpose (including for commercial purposes), except as expressly prohibited
> herein."* and *"Outputs are not considered Derivatives under this License."*

The **only** output restriction: you may not use outputs to **train/fine-tune/
distill a competing model**. Outputs include images from a *Derivative* (your
LoRA), so **LoRA-generated images are commercially usable.** This is the single
most robust, multi-source finding — and it's the legal foundation of the
asset-product business.
**Sources:** [LICENSE.md](https://huggingface.co/black-forest-labs/FLUX.1-dev/blob/main/LICENSE.md) ·
[bfl.ai non-commercial terms](https://bfl.ai/legal/non-commercial-license-terms)

### 1d. The paid commercial path — and its unresolved limit 🟢/🔴
BFL offers a **Self-Hosted Commercial License** (effective 2025-06-26) + self-serve
tiers (**Builder / Platform / Professional / Enterprise**) that advertise
**"fine-tuning and LoRA rights."** It permits self-hosted commercial generation
and creating/storing Derivatives **for integration into your own Customer
Application** — but **explicitly prohibits reselling/redistributing the model
weights or Derivatives to third parties** (incl. via API).

> 🔴 **Refuted (1-2):** the claim that the paid tiers *let you sell Flux-dev LoRAs
> to the public* — the no-redistribution clause contradicts a blanket-resale
> reading. **So even a paid license likely lets you USE a LoRA in your own
> product, not SELL the LoRA file on CivitAI/Gumroad.** (Open question.)
**Sources:** [Self-Hosted Commercial terms](https://bfl.ai/legal/self-hosted-commercial-license-terms) ·
[self-serve pricing](https://help.bfl.ai/articles/9272590838-self-serve-dev-license-overview-pricing) ·
[bfl.ai/pricing/licensing](https://bfl.ai/pricing/licensing)

### 1e. FLUX.1-schnell (Apache-2.0) — the clean fallback 🟡
schnell is **Apache-2.0**, so a **schnell-trained LoRA should be sellable without
the dev restriction.** *Flagged medium:* no surviving primary-source claim in this
batch independently confirmed schnell's terms or the dev-vs-schnell training-
quality tradeoff — **verify against the [schnell model card](https://huggingface.co/black-forest-labs/FLUX.1-schnell)
before relying on it.**

---

## 2. Supply gap & top Flux LoRA categories ⬜ UNANSWERED this pass

No claims survived verification for Q2. **Not established here:** the Flux-vs-
SDXL/SD1.5 LoRA supply ratio, and whether utility/quality-enhancer LoRAs (the
"Hands" LoRA ~292k-download signal) dominate CivitAI's most-downloaded Flux list.
*(The ~292k Hands-LoRA figure was observed live via the CivitAI API in-session but
was not re-verified in this batch — treat as a strong lead, not a citation.)*
Needs a dedicated pass.

## 3. ControlNet/IP-Adapter 24GB feasibility + LoRA quality edge ⬜ UNANSWERED

No claims survived for Q3 (24GB Flux ControlNet/IP-Adapter *training* feasibility;
whether multi-res training + eval-grid selection measurably beat a single-res
hobbyist upload). Reasoned priors from in-session analysis stand but are
**unverified**. Needs a dedicated pass (ai-toolkit/Kohya/XLabs docs + post-mortems).

---

## 4. Caveats

- **Not legal advice.** Get counsel before commercial reliance.
- **Versioned & moving:** the dev license changed v1.1 (2025-06-26) → v2.0
  (2025-11-25); the FLUX.2 family arrived 2026. **Re-verify current text.**
- **Gray area:** HF discussions (#136, #181) debate whether a standalone LoRA
  *delta* (containing no BFL weights) is technically a "Derivative." BFL's broad
  written definition resolves this **against** the creator; no official loophole.
- **Q2/Q3 unanswered** — don't treat their in-session reasoned answers as verified.

---

## 5. What this means for the business plan (action)

**Keep selling (legally clean — these are Outputs/downstream):**
- ✅ Texture packs, tilesets, 3D village kits, and any **image/asset products**
  generated via the Flux pipeline. **This is the bulk of Streams A/B/C/K.**

**Do NOT sell as-is (distributes a Flux-dev Derivative):**
- ❌ The **GrimForge `.safetensors` for sale** (task D0.6) and any paid
  **custom-LoRA deliverable** (D0.7) — if trained on FLUX.1-dev.

**Compliant options for the LoRA-product / service lane:**
1. **Retrain sellable LoRAs on FLUX.1-schnell (Apache-2.0)** — clean to sell
   (verify schnell terms first; expect some quality tradeoff vs dev).
2. **Or train on another permissively-licensed base** (e.g. SDXL for the
   asset-feeding LoRAs).
3. **Keep Flux-dev LoRAs FREE / non-commercial on CivitAI** — use them as a
   reputation/lead-magnet + to generate **Outputs you DO sell** (this stays
   within the non-commercial grant for the weights while monetizing the images).
4. **Monetize the OUTPUTS and the audience**, not the weights — which aligns with
   the earlier research finding that CivitAI is a lead-magnet anyway and the real
   dollars are in Gumroad asset sales + the content funnel.

**The safest, highest-confidence business model: sell the images/assets (Outputs),
give the Flux-dev LoRAs away free, and reserve paid LoRA *files* for a
schnell/Apache base.**
