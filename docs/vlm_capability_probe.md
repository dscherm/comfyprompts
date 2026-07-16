# VL7 — VLM capability probe: can a local VLM even see the melt?

**Date:** 2026-07-16 · **Script:** `scripts/vlm_eval/probe.py` · **Corpus:** `eval/exemplars/manifest.json` (VL4, commit a5c9436)

## Question

The cheap falsifier before any judge-harness investment (VL5/VL6/VL8): show each
model a known-differing good/bad rig-deformation pair **side by side**, TELL it the
two differ in exactly one production variable, and ask it to (1) articulate what
differs, (2) pick the defective image, (3) propose a QA criterion. If a model can't
name the melt under these maximally favourable conditions, no harness will make it
a useful judge.

The defective-image pick is a seeded-random 2-alternative forced choice
(bad twin's left/right placement randomized per pair, ground truth never in the
prompt), so **chance = 50%**.

## Setup

| | qwen3-vl:8b | qwen3-vl:32b |
|---|---|---|
| num_ctx | 8192, then 20480 (re-run) | 8192 |
| VRAM (`ollama ps`) | 6.5 GB, 100% GPU | **23 GB, 100% GPU — no CPU split** |
| Latency per pair | 33–186 s | 60–127 s |
| Thinking | enabled (VL2 ran think-off and under-elicited; not repeated here) | enabled |

The `num_ctx` fix worked: ollama 0.32 defaults qwen3-vl:32b to a 32768 context
(~29 GB → spills onto the 3070 + CPU, >600 s/image). Capped at 8192 it sits
entirely on the 3090 Ti at 23 GB and answers in 1–2 min. ComfyUI was down for the
whole run (no VRAM contention).

## Results — defective-image picks (chance = 3/6)

| pair (project_type) | bad twin | 8b pick | 32b pick |
|---|---|---|---|
| knee_bend (humanoid) | image 1 | 2 ✗ | **1 ✓** |
| elbow_bend (humanoid) | image 1 | 2 ✗ | 2 ✗ |
| hip_flex (humanoid) | image 2 | no answer | **2 ✓** |
| front_knee_bend (quadruped) | image 1 | 2 ✗ | **1 ✓** |
| hind_knee_bend (quadruped) | image 1 | no answer | 2 ✗ |
| neck_bend (quadruped) | image 1 | no answer | no commitment |
| **total** | | **0/6** | **3/6 (= chance)** |

## Per-model: did it articulate the real difference?

### qwen3-vl:8b — no. Confabulation plus a positional bias.

Every answered pair picked **image 2**, regardless of truth (bad twin was image 1
in all three it answered). The three unanswered pairs ran away in thinking
(81k–89k chars at num_ctx 20480; at 8192 they truncated to empty) without ever
converging — the thinking is guesswork, not perception, e.g. hip_flex (verbatim,
from thinking): *"Let's consider a common rigging defect: 'stretching of the mesh
along the arm' … Another possibility: 'pinching at the elbow joint' … Let me try"*.

Where it did answer, the description is fabricated. On elbow_bend (a humanoid
forearm pair) it reported, verbatim: *"the character's **tail (or neck)** exhibits
visible **self-intersection** where the mesh passes through itself"* — there is no
tail in frame, and it picked the clean image.

### qwen3-vl:32b — partially. Real signal on the two clearest pairs, chance overall.

Genuine articulation where the melt is most legible:

- **knee_bend ✓** (right image, right region, right mechanism): *"The left knee
  region shows a visible, unnatural **puckering** or **folding** of the mesh in
  image 1 … where the surface appears to collapse inward at the joint. In
  contrast, image 2 exhibits smooth, continuous deformation."*
- **front_knee_bend ✓**: *"The ankle region … shows an unnatural 'kink' or
  'stretched' mesh in one image … a visible gap or sharp angle between the lower
  leg and foot."*
- **hip_flex ✓ pick, wrong region label**: *"an unnatural 'cable' effect—a thin,
  stretched line of mesh where it should maintain natural volume"* — plausibly the
  real drooping shred in the bad twin, but attributed to the forearm bandage.
- **neck_bend, no commitment**: *"a semi-transparent 'ghost' duplicate of the mesh
  … slightly offset from the primary mesh and overlaps with it"* — arguably the
  overlapping melted jaw membrane, but it never named image 1 or 2.

But on elbow_bend and hind_knee_bend it produced equally confident, equally
detailed descriptions of the **clean** image (e.g. hind_knee_bend, verbatim:
*"Image 2 (the one showing the crawling/stretched effect) is defective"* — the
bad twin was image 1). The failure mode is not "can't see anything"; it is
**can't reliably tell which image the artifact is in**, which is fatal for a
judge whose whole job is that attribution.

> **Post-probe human curation review (2026-07-16): the corpus itself failed
> review, so the NO-GO below is PROVISIONAL.** The user rejected knee_bend
> (an unattached left foot appears in BOTH twins — a pre-existing artifact
> violating the one-variable contract) and could not adjudicate elbow_bend or
> the quadruped pairs because the tight joint crops exclude the regions the
> models' claims cite (e.g. the 32b's "neck/shoulder bulge" is unverifiable
> when the neck isn't in frame). The 2AFC-at-chance result is objective, but a
> corpus that fails human review can't support a final verdict. Rule going
> forward: exemplars enter the manifest only after per-pair human approval,
> rendered wide enough (full body + joint detail) that every claim is
> adjudicable. Re-run this probe on the curated corpus before acting on the
> verdict.

> **Scope note (2026-07-16, cross-session evidence):** the no-go below is
> specific to **contrastive-pair attribution on 3D renders** (which of two
> near-identical images holds the defect). A parallel session's pilot
> (`E:\ai-training\flux-output\occult_providence\pipeline\score_pilot.py`)
> found qwen3-vl:8b SUCCESSFUL at **single-image attribute checking on 2D
> art** — enumerable rubric fields (background type, base style, accent
> colours/areas), think off, num_ctx 4096, retry-on-empty, layered under a
> deterministic presence screen and a human montage that may overrule it.
> The model regime that works: "what is present in this image" against a
> spec. The regime that failed here: "which of these two images differs,
> and where." Future VLM checks (VJ1) should be framed as the former.

## Go/no-go: **NO-GO, provisional** (threshold: ≥5/6 correct picks with correct-region articulation)

The 32b scores exactly chance on a coin-flip task under the most favourable
conditions we can construct — both images in-frame, told they differ, told only
one variable changed, thinking enabled, full GPU residency. The 8b is worse than
chance with a position bias and unstable termination. An exemplar-based VL judge
built on these models would be an expensive random-number generator for rig
deformation.

**What survives:**

- **Tier-1 stays code** (VL3P) — unchanged, that work is independent of any model.
- Rig-deformation QA should also be attempted **as code**, not perception: the
  melt has a deterministic signature (per-vertex deform delta between good-weight
  and candidate-weight twins, or posed-joint cross-section/volume change). That is
  a candidate future Tier-1 check.
- The VL4 exemplar corpus keeps its value: as calibration ground truth for any
  future model (bigger local VLM, cloud VLM, or Claude-in-the-loop review), and as
  documentation of the failure mode.
- Human (or Claude-session) visual review remains the Tier-2 decider.

**Consequence for the plan:** VL5, VL6, VL8 were explicitly gated on a VL7 go and
are closed as skipped-by-design. Re-open them only if a materially stronger model
becomes cheaply runnable (or cloud judging becomes acceptable), and re-run this
probe first — the probe is the gate, and it is cheap (~20 min end to end).

## Appendix — model-proposed criteria (UNCURATED)

Collected verbatim as brainstorm input for VL5-style curation, **not
human-approved, never to be used as a rubric a model grades itself against**
(self-marking). Deduplicated to the distinct ideas:

1. *"For all major joints (knees, elbows), in any pose where the joint is flexed
   beyond 45°, the mesh must exhibit smooth, continuous surface deformation
   without visible creasing, stretching, or popping artifacts at the joint
   region."* (32b, knee_bend)
2. *"No visible bulges, gaps, or discontinuities exceeding 0.5% of the local
   mesh's bounding box size may exist at any joint region … verified by rendering
   the asset against a high-contrast background."* (32b, elbow_bend)
3. *"Any mesh area subject to joint movement (e.g., limbs, clothing) must not
   exhibit a 'cable' artifact (a thin, stretched line of mesh) during deformation;
   the mesh must maintain consistent volume."* (32b, hip_flex)
4. *"The ankle/foot region must exhibit no visible stretching, pinching, or
   'crawling' artifacts; the mesh near the ankle must align naturally with the
   foot bone without unnatural pulling toward the shin."* (32b, hind_knee_bend)
5. *"No visible z-fighting artifacts (e.g., semi-transparent duplicates or
   overlapping geometry) from any camera angle in any pose."* (32b, neck_bend)
6. *"All vertices in the lower leg (shin) have a primary weight assignment to the
   shin bone rather than the thigh bone."* (8b, knee_bend — note: this is a
   weight-space check, i.e. Tier-1 code territory, not a visual criterion)
7. *"No part of the mesh intersects with another part when in any pose."*
   (8b, elbow_bend)

## Raw data

- `scripts/vlm_eval/probe_results_qwen3-vl-8b.json` (num_ctx 20480 run)
- `scripts/vlm_eval/probe_results_qwen3-vl-32b.json` (num_ctx 8192 run)

Each record holds the full verbatim `content` and `thinking`, the seeded bad-twin
placement, the parsed pick, per-pair latency, and the `/api/ps` GPU-residency
snapshot taken immediately after the call.
