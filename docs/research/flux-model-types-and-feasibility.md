# Flux Model Types & 24GB Feasibility — What to Build Next

*Cited research report. Generated 2026-06-30 via the `deep-research` harness
(5 angles → 21 sources → 92 claims → 25 verified, 16 confirmed / 9 refuted →
6 findings). Resolves the Q2/Q3 left unanswered by `flux-lora-edge-and-licensing.md`.*

> **Confidence:** 🟢 high (3-0) · 🟡 medium (2-1) · 🔴 refuted · ⬜ unverified.
> **Read the refutations** — many specific numbers did NOT survive; the
> *categorical* conclusions did.

---

## BOTTOM LINE

1. **Utility / quality-enhancer LoRAs are the highest-demand Flux category** —
   above any single art style. (But see licensing: build them **free** for
   CivitAI Buzz/reputation, not as a paid file.)
2. **The LoRA is the only solo-feasible unit.** Training a Flux **ControlNet**
   (datacenter scale) or **full checkpoint** (~120 GB) on your 24 GB card is **not
   feasible** — cross those off the "what else to build" list.
3. **Your 24 GB 3090 Ti comfortably trains Flux LoRAs** — you're well above the floor.
4. **The quality edge (multi-res, eval-grid) is real but unquantified** — it's
   process consistency, not a proven quality multiplier. Be honest in marketing.

---

## 1. Supply gap + most-downloaded Flux LoRA categories

### 1a. Utility/quality-enhancer LoRAs dominate the top 🟢
Among Flux-supporting LoRAs sorted by downloads on CivitAI, the very top entries
are **hand/anatomy, realism, and detail enhancers — not art styles**:

| LoRA | Downloads | Type |
|------|-----------|------|
| UltraRealistic Lora Project (Flux.1 D) | **383.1k** (3,114 reviews) | realism + "Enhanced Hands & Anatomy" |
| Hands XL + SD1.5 + F1D + Pony + Illustrious | ~292.6k *(cross-base aggregate; ~80.5k Flux-only)* | hand/anatomy fixer |
| Flux.1 Turbo Detailer | (count unverified) | detail amplification (eyes/hands/lighting) |
| Hand Detail FLUX & XL | 5★, 2,466 reviews | "add more details to hands" |
| Detailifier | (count unverified) | faces/skin/clothing/fur/materials |

**Verified takeaway:** the *category* (utility/quality enhancers) is what gets
downloaded, broadly and repeatedly — exactly the "breadth = Generator-Buzz"
pattern. **Sources:** [Hands XL](https://civitai.com/models/200255/hands-xl-sd-15-flux1-dev-pony-illustrious) ·
[API 200255](https://civitai.com/api/v1/models/200255) ·
[UltraRealistic](https://civitai.com/models/796382/ultrarealistic-lora-project) ·
[Turbo Detailer](https://civitai.com/models/930386/flux1-turbo-detailer) ·
[Hand Detail](https://civitai.com/models/260852/hand-detail-flux-and-xl) ·
[Detailifier](https://civitai.com/models/430687/detailifier-fluxsdxlponysd15)

> 🔴 **Refuted — do NOT cite as fact:** specific download counts for Hand Detail
> (~405.6k), Detailifier (~178.9k), "Extreme Detailer" (~98.4k) all failed
> verification (1-2). Only the categorical positioning survived. Also note CivitAI
> download-sorted Flux lists **conflate cross-base multi-architecture models**,
> inflating apparent Flux-specific ranking.

### 1b. The supply gap is directional, not numeric 🔴→directional
Flux LoRAs **are** scarcer than SDXL/SD1.5 (recency since Aug 2024, the 12B-param
training barrier, tooling immaturity, and the non-commercial license chilling
commercial creators). **But every specific ratio was refuted** — "SD1.5 100k+ /
SDXL 30k+ / Flux 5k+" (1-2) and "10k/5k/500" (0-3) both failed. **Treat the gap as
real but unquantified** until a direct CivitAI API count is run (open question).

---

## 2. Training feasibility on a single 24 GB GPU

### 2a. Flux LoRA — first-class, well above the floor 🟢
| Trainer | VRAM | Note |
|---------|------|------|
| FluxGym | **12 / 16 / 20 GB** tiers | low-VRAM Flux LoRA UI |
| ai-toolkit | **24 GB** | ships `train_lora_flux_24gb.yaml` (+ schnell variant) — your harness's basis |
| SimpleTuner | **~18 GB** (int8) | names "a single 3090" as the realistic minimum; >30 GB unquantized |
| QLoRA | **~9 GB** peak | (RTX 4090, bs1, 512×768) |

Your 24 GB 3090 Ti clears all of these comfortably. **Sources:** [FluxGym](https://github.com/cocktailpeanut/fluxgym) ·
[ai-toolkit](https://github.com/ostris/ai-toolkit) ·
[SimpleTuner FLUX.md](https://github.com/bghira/SimpleTuner/blob/main/documentation/quickstart/FLUX.md) ·
[HF flux-qlora](https://huggingface.co/blog/flux-qlora)

### 2b. Flux ControlNet — NOT solo-feasible 🟢
A production Flux ControlNet (Shakker-Labs Union-Pro-2.0) was **trained from
scratch for 300k steps on 20M images at 512×512, batch size 128, LR 2e-5**. A
global batch of 128 over a 12B transformer + ControlNet branch **cannot fit on
24 GB**; 300k steps over 20M images is unambiguously a multi-GPU/datacenter run.
→ **Don't attempt ControlNet training. Use existing ones for inference.**
**Source:** [Shakker-Labs Union-Pro-2.0](https://huggingface.co/Shakker-Labs/FLUX.1-dev-ControlNet-Union-Pro-2.0)

### 2c. Full fine-tune / checkpoint — NOT solo-feasible 🟢
Full FLUX.1-dev fine-tuning is **~120 GB VRAM unoptimized** (≈5× a 24 GB card).
DeepSpeed/8-bit/CPU-offload can lower it but is impractically slow.
→ **LoRA/QLoRA is the only realistically solo-feasible path.**
**Source:** [HF flux-qlora](https://huggingface.co/blog/flux-qlora)

### 2d. IP-Adapter training ⬜ unverified
No surviving claim established whether a Flux IP-Adapter is trainable on 24 GB.
**Open question** — don't assume either way.

---

## 3. The LoRA quality edge

**Multi-resolution bucketing is real and built-in** 🟢 — ai-toolkit's loader
"downscales images and places them in buckets… handles varying aspect ratios"
(also in Kohya sd-scripts). Your harness already uses 512/768/1024.
**Source:** [ai-toolkit](https://github.com/ostris/ai-toolkit)

> ⬜ **But the quality DELTA is unquantified.** No surviving evidence measures
> multi-res vs single-res, or eval-grid checkpoint/strength selection, as a
> before/after improvement. **So the edge is process *consistency/repeatability*,
> not a proven quality multiplier — don't oversell it as "higher quality."**

---

## 4. Caveats (read before acting)

- **Numbers refuted:** all cross-architecture VRAM deltas (Flux 24 / SDXL 16 /
  SD1.5 10) failed 0-3; the "26 GB FP16 LoRA on 4090" specific figure failed 0-3;
  all supply-gap ratios failed. Use only the **trainer-specific** VRAM anchors in §2a.
- **Download counts drift** (live API) and **cross-base models inflate** Flux-sorted lists.
- The utility-LoRA finding is **categorical** (high confidence), the magnitudes are not.

---

## 5. What this means for the build order

**Add a "utility/quality-enhancer LoRA" track — as a FREE CivitAI Buzz/reputation
play** (licensing bars selling the file anyway). Utility LoRAs are used in *every*
generation → they top the 25%-of-Generator-Buzz mechanic, making them the best
reputation/funnel engine even though you can't sell the file. Candidates that fit
your stylized/3D edge rather than competing in saturated photoreal:
- a **game-art / stylized detail enhancer** (sharpen materials/edges on stylized renders),
- a **clean-silhouette / neutral-background** helper (also improves image→3D input).

**Cross OFF the "what else to build" list (not solo-feasible):** Flux ControlNets,
Flux IP-Adapters (unverified — don't assume), full checkpoints/fine-tunes. **The
LoRA is the unit.**

**Marketing honesty:** lead with *repeatability + curation + 3D-rendered datasets*
(verifiable edges), not "higher quality" (unproven).
