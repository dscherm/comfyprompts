---
name: vn-generation-craft
description: Measured craft for generating consistent VN/game character art with ComfyUI — building a character LoRA that is actually of the right person, keeping wardrobe and setting under control, cutting sprites, and animating an approved still into a looping webm. Covers the silent failure modes where a job returns a clean file of the wrong thing. Use when generating character references, staging shot sets, assembling LoRA training data, training or verifying a character adapter, producing sprites or backgrounds, or animating a still.
triggers:
  - generating a character reference or a staged shot set
  - assembling a LoRA training set, or training / verifying a character adapter
  - a render "works" but the person, outfit, setting or anatomy is wrong
  - cutting sprites, generating backgrounds, or animating a still into video
  - choosing a checkpoint, adapter or workflow variant
---

# VN generation craft

Everything here was measured. No claim is included that was not observed
directly, because the failure mode this whole document exists to prevent is
plausible-looking output that nobody checked.

For explicit/adult generation, see the separate explicit-generation skill in
`comfyui-renpy` — it is kept apart on purpose.

## The one rule

**Every failure in this domain returns a clean file.** Nothing errors. A wrong
model variant, a missing trigger token, a colliding asset id, a dead dispatch
layer — each produces a well-formed image or video of the wrong thing, at the
right resolution, with a successful exit code.

So the gate is never "did it succeed". It is **"is this the thing I asked
for"**, answered by looking.

## Identity: making the adapter be the right person

**Fingerprint a `.safetensors`; never trust its name.** Read the tensor keys.
`transformer.single_transformer_blocks.*` is FLUX in diffusers naming. Count
blocks and hidden dim to tell 14B from 5B — a file named `wan2-2nsfw_cowgirl`
was 30 blocks / dim 3072, a **5B** adapter that could never load in a 14B rig,
and the name was accurate the whole time.

**FLUX character LoRAs carry no CLIP tensors.** Trained with
`train_text_encoder: false`, so `strength_clip` must be `0`. A non-zero value
on absent tensors is noise.

**The trigger token is mandatory.** An adapter whose token is missing from the
prompt loads cleanly and contributes almost nothing — which renders as a
competent picture of the wrong person, not as an error.

**Captions attribute.** Whatever a caption NAMES is learned as belonging to
those words; only what it omits is forced into the trigger. Spelling out
"a Black woman in her late thirties, long dark locs" on every training image
teaches the model that those attributes belong to the description — and at
render time the description competes with the base model's prior, which wins.
Measured: an adapter trained that way on 18 correct images rendered a
light-skinned woman in her twenties, at every strength, in dim and bright
prompts alike. Caption pose, framing and setting; never identity.

**Strip boilerplate wherever it sits, not just at the start.** Prefix-anchored
stripping silently stops working the day a project edits its `style_prefix`,
because existing art still records the old one.

**Filter training sets on OWNERSHIP.** An asset that names a different
character must never enter a set, whatever list points at it. Prompt-derived
ids collide between characters staged through one shared shot list, and three
adapters once trained on 17 pictures of a fourth character plus one correct
reference. Nothing detected it: a training set is the first thing that looks at
all of a character's art at once, and it was looking at the wrong art.

**Namespace generated asset ids by character**, and let a caller name an asset
explicitly. A derived id slugs the first few words of a prompt, so two shots
differing only in a clause at the END slug identically — indistinguishable from
a re-import, so the second silently replaces the first.

**A DIM training set cannot teach a skin tone the base model's prior fights.**
If the character is never lit, the adapter learns a silhouette and a hairstyle
and leaves the tone to the prompt — which loses to the prior. Measured on one
character across a retrain: median figure luminance **32.4 → 71.3** (19 frames,
4 under 60, against 21 of 28 before). The cell that proves it is the adapter
ALONE with **no skin, race or hair word anywhere in the prompt**: the dim
adapter scored **0/3** there, the bright retrain **2/3**, and the same cell at
strength **0.0** drew three white women — so it is the weights and not the text.
Brightness has a ceiling: blown-out frames (luminance 115–156) read several
steps LIGHTER than the reference, so "under even white ceiling light" beat
"brightly lit", and "brightly lit engine room" renders a DIM engine room
because the noun beats the adjective.

**But a better character adapter does NOT out-vote a position adapter on
skin.** Same character, same seeds, one variable: **0/33** with the dim adapter
across every strength of two position adapters, and **0/6** after the retrain
that had just fixed the adapter alone. Character strength is not the lever (1.0
and 1.1 are pixel-identical at the same seed); position-adapter strength is not
the lever either (the tone never returns above strength 0, and the position
starts collapsing two steps before the tone moves). **The identity channel a
position adapter takes first is SKIN** — face shape and hair partly survive,
tone does not. So when a position adapter suppresses a character adapter,
adapter quality is the wrong axis to spend GPU on. The remedies, in the order
they cost:

* a **different position adapter** — the same character held 6/6 under one and
  0/12 under another, and which adapter respects which character differs per
  character, so measure the (character × position adapter) pairing before
  spending a batch;
* **two passes** (structure first, identity second with the position adapter
  retained at ~0.4 — the strong-adapter-suppression remedy in `comfy-inference`);
* a **masked edit** (a real `SetLatentNoiseMask`, not a pixel composite).

Which one wins is a per-project measurement, not a rule. On the run that
produced these numbers the two-pass route held the join **12/12** across denoise
0.45–0.75 and still drew the wrong woman **12/12**, while the masked edit
reached her tone 3/3 and left a two-tone limb on the mask edge. Note what the
two-pass route DID fix: the pale man in the same frame, whose adapter had also
been suppressed — his stubble and face came back as the position adapter went
down to 0.4. Two passes recover the identity the prior does not fight, and do
nothing for the one it does.

## Verification

**A control cell is necessary and not sufficient.** Render the same seed and
prompt with the adapter at 0.0. If the pair is identical the adapter is inert.
But a control cell only proves the adapter does *something* — it cannot prove it
does the right thing. Three adapters passed control cells while trained on the
wrong person.

**Verify on a subject the base model gets WRONG.** A blonde white woman looks
fine even when the adapter was trained on somebody else, because that is what
the prior produces anyway. Pick the character whose attributes the prior fights;
that render fails loudly in one image.

**Contact-sheet the training set before spending GPU on it.** Every automated
signal stayed green through three bad runs: assembly reported "18 images ready",
captions were well-formed, training converged, adapters loaded. Four seconds of
looking would have caught it.

**Judge identity with the REFERENCE crop tiled beside the frame's crop, at one
scale.** Not "the skin looks dark", not the frame on its own, and never a luma
number: two separate readings of "her skin held N/N" (12 frames and 20 frames)
were later RETRACTED because the judge never put the reference next to the
frame, and both times the picture was the same lighter medium-tan woman. A
skin-luma statistic does not rescue this either — the reference is usually lit
differently from the render, so luma compares lighting, not tone; it is a
direction measure between frames of one arm and nothing more. Distrust
"identity holds" from any pass that cannot show the side-by-side.

**Judge anatomy at full size, cropped to the region that fails.** A 2x2 sheet at
640x360 confirms identity and hides everything else. Frames passed at thumbnail
scale and failed at full size with three hands, a melted face, and wrong
proportions. Check: hand count, limb count, proportion, and continuity with
other scenes.

**Mid-training samples are only meaningful in-distribution.** A sample prompt
asking for something the set never contained ("plain grey background" when every
portrait is lit by a work lamp) leaves the adapter idle and the prior visible,
so a healthy run looks dead. Read the TREND across steps, not one snapshot.

## Wardrobe and setting

**A costume is an ACTION ON THE GARMENT IN FRAME.** "Dress her in a coverall
unzipped to show cleavage" changes nothing — she is already wearing a coverall,
so the sentence is satisfied and every modifier is dropped. "Unzip her coverall
to the navel and pull it open wide" works first try.

**The action must match the real fastening.** "Unzip" opened one character's zip
and did nothing to another's buttons.

**Large wardrobe edits erode identity.** Name the specific features that drift —
"keep her close-cropped short black hair and her warm brown skin" — or expect a
different woman in half the seals.

**A character adapter will not undress its subject.** Prompted "nude, bare
breasts", a trained character rendered fully dressed in her trained outfit. The
learned wardrobe overrides the prompt.

**Mixed, captioned outfits make wardrobe a prompt-time choice.** A single-outfit
set welds the outfit to the trigger. Several outfits, each named in its own
caption, separate face from clothes — partially; expect influence, not a clean
swap, and balance the counts.

**No industrial jargon in prompts.** Every one of these is read literally:
`moonpool` → swimming pool. `racked diving suits` → clothing shop with
mannequins. `deck` → wooden porch. `frost-furred corridor` → snowy birch forest.
`mess table` → domestic kitchen. `cabin` → apartment. Say "steel", "industrial",
"windowless", "floor plating".

**Setting words carry LIGHT, and light binds to the trigger.** A set half-shot in
daylight teaches the adapter daylight even when the caption names the setting.

## Settings: what makes a room read at game size

Measured 2026-09-05 on four Flux backgrounds (1280x720, style adapter 0.5),
same seed per room, ONE clause changed per arm, judged on a 640-wide contact
sheet beside the control — i.e. at roughly the size a background has under
two sprites and a textbox. Counts are rooms in which the arm read without
explanation.

**Light is the lever, and coloured light always reads (14/16).** A red wash
4/4, a green console glow 4/4, one warm amber lamp 3/4, a single lamp against
shadow 3/4. Naming the light SOURCE ("one warm amber lamp over the table")
also draws the lamp and gives the room a key; naming a colour alone gives a
wash. The only light arm that failed was amber in a white room: a small
practical cannot warm a room the prompt has already painted white.

**A foreground occluder gives depth (11/16), but only if it is big.** A
doorframe edge 4/4, a thick pipe 3/4, a railing 2/4, hanging cables 2/4. The
arms that failed drew a thin dark blur at one edge that vanishes at game
size. Say "close to the camera", "thick", "heavy", and where in the frame it
sits ("along the top edge") — an occluder that crosses the middle of the
frame will be drawn OVER by a sprite standing in front of it.

**Camera words are weak (7/16).** "Seen from the doorway, framed through the
open hatch" 4/4 — because it is really an occluder. High angle 2/4, corner
perspective 1/4, low angle 0/4: a room described as symmetric (two bunks
either side, a corridor of doors) snaps back to the one-point eye-level view
whatever the camera clause says. Change the room description, not the camera.

**Dressing reads (8/12) and carries text.** Signs of habitation (mugs, a
jacket, notes taped up, a chart) 4/4 and it is the cheapest "lived-in";
"steam and haze, dust in a beam" 4/4 and it changes the LIGHT too (a beam
needs a source, so the model adds one). Condensation / wet floor 0/4 —
invisible at game size. Anything "taped to the wall" comes with gibberish
lettering the negative does not remove; keep notes small or name them as
"blank".

**Palette words repaint the room (7/8) — too well.** "Dominant warm amber
palette" rebuilt the mess as a different, orange, riveted room; "dominant
teal" is a monochrome wash. Carry a palette through the LIGHT clause (an
amber lamp, a green screen) and the props, not through a colour word.

**"Suit racks" draws standing figures.** Gear on the wall rendered as
people in suits in 4 of 18 moonpool arms despite "no people" in the negative;
"pressure vessels and coiled hoses" does not. "Dead strip lighting" renders
the strips ON — say "the ceiling lights dead and dark".

## Kontext

Preserves what it is not told to change — that is the whole tool.

- Identity holds through `ReferenceLatent` at denoise 1.0, not through a partial
  denoise. Plain img2img wearing Kontext weights repaints freely.
- It will **replace and rearrange clothing but not remove it**.
- It does **not isolate a global attribute**. Told to change one figure's skin
  tone and explicitly to preserve the other's, it lightened both.
- Props travel with the subject; say what to remove.

## Sprites

Staged shots are opaque frames with a room in them. They are `full_frame_shot`,
not cutouts — mislabelling them as `character_cutout` makes an exporter refuse to
scale them (correctly: a sprite stretched to the stage becomes a giant) and they
render at native size with the screen edges empty.

Real sprites: segment with InSPyReNet, **crop to the alpha bounding box**, and
compute scale from the cropped height. Choose STANDING sources — a cut-out
seated figure dropped onto a floor appears to sit on air.

## Animation

**Match the node to the checkpoint variant, not the family.** VACE is Wan's
control/editing model and conditions through `WanVaceToVideo`'s
`reference_image`. Feeding a VACE checkpoint through `WanImageToVideo`'s
`start_image` renders a clean five-second clip of a **different person in a
different room**. The graph was right, the upload was right, the submitted
prompt named the correct file.

**Animate an approved still.** The video model has no character adapter;
generating from text re-rolls a likeness that cost hours.

**Feed `trim_latent` into `TrimVideoLatent`** or the clip opens on a frozen
reference frame.

**Wan does not close its own loop.** Seam ~19/255. Ping-pong (forward then
reversed) takes it to ~1 and doubles the duration free. **Check brightness at
both ends before trusting a seam number** — a clip that fades to black scores a
perfect seam by being dark twice.

**Pick stills for animatability**: separated figures, simple silhouettes.
Overlapping limbs animate into incoherence — identities morph and extra people
appear.

**Cost**: ~20 min per 81-frame 832x480 clip at 20 steps on a 3090 Ti with a Q4
GGUF, against ~1 min for a still. Cull at the still stage.

`SaveWEBM` emits VP9 directly — the format Ren'Py plays natively, no ffmpeg step.

## Operational

**Check the dispatch layer before debugging your own code.** If jobs are
accepted and never run, query ComfyUI's `/history` and count them. A wedged MCP
layer accepted every job, returned 200, and reported `{"online": true}` because
that check probes ComfyUI directly rather than the layer actually in the path.
Three "fixes" were built for downloads before anyone counted the jobs.

**Duplicate processes on one port** — one on system Python, one on a venv — have
now caused this twice, on two different services. Check `Get-NetTCPConnection`
before assuming stale code.

**Batch and select.** Multi-figure interaction is where diffusion is least
reliable; expect roughly 1 keeper in 10 once you inspect properly.

**Unique filename prefixes per batch**, or deleting an output resets ComfyUI's
counter and the next clip silently overwrites.
