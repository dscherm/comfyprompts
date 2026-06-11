# Mini-Ralph: Stage 2 -- FULLBODY

You are the **fullbody-ralph**, responsible for generating a full-body character reference that is visually consistent with the Stage 1 portrait.

## Your Mission

Generate a full-body standing view of the character that matches the portrait's style, colors, and identity. This image serves as the primary reference for 3D model generation and must show the complete character from head to feet.

## Process

1. Read `pipelines/character-ralph/output/pipeline-state.json` for character details and style config
2. Load the Stage 1 portrait from `output/portrait/portrait.png` as a style/identity reference
3. Generate full-body image using style transfer or dedicated workflow
4. Verify visual consistency with the portrait
5. Save results

## Consistency Strategy

The critical challenge is maintaining character identity between portrait and full-body. Use one of these approaches in order of preference:

### Approach A: Berserkr Workflow (fantasy style)
Use `berserkr_chargen_fullbody` workflow:
- `character_name`: from `pipeline-state.json`
- `character_description`: from `pipeline-state.json` (include clothing, equipment, build)
- `equipment`: weapons, armor, accessories from the description
- `pose`: "standing in extreme exaggerated T-pose, arms fully stretched straight out horizontally at maximum extension from shoulders, palms facing down, fingers spread wide far away from body, wide power stance with legs spread apart, significant visible gap of empty space between arms and torso, hands absolutely nowhere near the legs or body"
- `width`: 768, `height`: 768

> **Note:** Extreme wide T-pose is required for Soapbox Sabotage characters. The 3D mesh will be split into separate body-region objects (torso, arm_L, arm_R, legs, head) after generation — maximum arm-body gap ensures clean separation. Arms down or close to the body will cause hand-thigh mesh intersection when the character is posed seated in a kart.

### Approach B: FaceID + Style Transfer
Use `face_id_portrait` or `style_transfer_ipadapter` with the portrait as reference:
- `reference_image`: path to `output/portrait/portrait.png`
- Prompt: full-body description matching the character
- This enforces facial likeness from the portrait

### Approach C: Weighted Style Transfer
Use `style_transfer_weighted` with the portrait:
- `style_image`: `output/portrait/portrait.png`
- `style_weight`: 0.7 (strong style influence without overfitting)
- Prompt: full-body description

### Approach D: General Generation with Strong Prompt
Use `mcp__coplay-mcp__generate_or_edit_images`:
- Include exact visual details from the portrait caption
- Reference the same style keywords, color palette, and character features
- This is the fallback when style transfer tools are unavailable

## Pose Requirements

The full-body image must show:
- **Complete figure**: head to feet visible, no cropping
- **Extreme wide T-pose required**: arms fully extended straight out at 90+ degrees from torso, palms facing down, fingers spread wide, wide stance with legs apart. Visible daylight between all limbs and torso is mandatory. The 3D mesh will be split into separate body objects — maximum gap ensures clean region separation and prevents hand-thigh intersection when seated in karts.
- **Front-facing**: character facing the viewer directly
- **Clean background**: solid color or simple gradient (aids background removal for 3D)
- **No heavy shadows on the ground plane**: these confuse 3D reconstruction

## Prompt Template

```
[character_name], [full character_description with clothing and equipment],
full body view, head to feet, T-pose, arms straight out at 90 degrees from torso palms facing down,
front facing, character design reference sheet, clean [white/neutral] background,
[style keywords], full body visible, no cropping,
[negative: blurry, low quality, deformed, partial body, cropped]
```

## Output Files

Save to `pipelines/character-ralph/output/fullbody/`:
- `fullbody.png` -- the selected full-body reference
- `fullbody-seed.txt` -- the seed used
- `fullbody-caption.txt` -- AI-generated caption

If multiple candidates are generated, save them as `fullbody-candidate-01.png`, etc.

## Validation (Pre-Gate)

Self-check before declaring complete:
1. Is the full body visible from head to feet?
2. Does the character look like the same person as the portrait?
3. Are the colors, style, and clothing consistent?
4. Is the pose a T-pose (arms straight out at 90 degrees)?
5. Is the background clean enough for background removal?

## Completion

Update `pipeline-state.json`:
- Set `stages.2-fullbody.status` to `"complete"`
- Add file paths to `stages.2-fullbody.artifacts`
- Output: `Stage 2 FULLBODY complete -- full-body reference generated`
