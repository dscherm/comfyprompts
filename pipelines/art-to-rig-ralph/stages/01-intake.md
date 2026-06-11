# Mini-Ralph: Stage 1 -- INTAKE

You are the **intake-ralph**, responsible for parsing the project requirements and establishing the production plan for the entire batch.

## Your Mission

Read the PRD at `pipelines/art-to-rig-ralph/prd.md`, extract all asset definitions, determine the visual style profile, resolve user preferences, and write a structured intake report that drives all downstream stages.

## Process

1. Read `pipelines/art-to-rig-ralph/prd.md` for project requirements
2. Read `pipelines/art-to-rig-ralph/output/pipeline-state.json` for current state
3. Parse the asset list, style guide, and preferences
4. For each asset, determine the body type and skeleton type mapping
5. Resolve the background approach (auto-detect if user chose `auto`)
6. Calculate total generations needed (assets x variations)
7. Write the intake report
8. Update pipeline-state.json

## Asset Extraction

From the PRD asset table, extract for each asset:
- **id**: Generate as `asset-{NNN}` (zero-padded, e.g., `asset-001`)
- **name**: Asset name from table
- **description**: Full description text
- **body_type**: From the Body Type column
- **skeleton_type**: Map from body_type using the skeleton selection matrix
- **variations_requested**: Number from Variations column (default 1)

### Body Type to Skeleton Mapping
| Body Type | Skeleton Type | Expected Bone Count |
|-----------|--------------|-------------------|
| humanoid | biped_rigify | 50-80 |
| quadruped | quadruped_spine | 40-60 |
| quadruped_winged | dragon | 60-90 |
| biped_winged | biped_winged | 50-70 |
| serpentine | spine_chain | 30-50 |
| insect | multi_leg | 50-70 |
| mech | rigid_hierarchy | 20-40 |
| custom | custom | varies |

## Style Profile Construction

From the PRD Style Guide section, build a structured profile:

```json
{
  "primary_style": "dark_fantasy",
  "influences": ["Frank Frazetta", "70s book covers"],
  "color_palette": "muted earth tones, warm highlights",
  "line_work": "heavy ink outlines",
  "rendering": "painterly with texture",
  "mood": "menacing",
  "prompt_suffix": "dark fantasy illustration, oil painting, dramatic chiaroscuro lighting",
  "negative_prompt": "bright, cheerful, modern, clean"
}
```

Map the user's style choice to prompt engineering parameters using the style-to-prompt table in PROMPT.md.

## Background Approach Resolution

If the user chose `auto`, select based on style:
- **generate_transparent** (recommended for): cartoon, chibi, comic, pixel_art, digital_painting
  - Rationale: These styles have clean edges and benefit from generating directly on transparent/white background. The silhouette stays crisp.
- **remove_after** (recommended for): dark_fantasy, high_fantasy, realistic, oil_painting, watercolor, pencil
  - Rationale: These styles produce better composition and lighting when generated with full scene context. Background removal after generation preserves artistic quality.

If the user specified a preference, respect it regardless of style.

## Output: intake-report.json

Write to `pipelines/art-to-rig-ralph/output/intake/intake-report.json`:

```json
{
  "project_name": "PRD title or first line of overview",
  "created": "2026-03-25T00:00:00Z",
  "assets": [
    {
      "id": "asset-001",
      "name": "Fire Dragon",
      "description": "A massive red dragon with torn wings and battle scars, breathing fire",
      "body_type": "quadruped_winged",
      "skeleton_type": "dragon",
      "expected_bone_count": [60, 90],
      "variations_requested": 3,
      "status": "pending",
      "notes": ""
    }
  ],
  "style_profile": {
    "primary_style": "dark_fantasy",
    "influences": ["Frank Frazetta", "70s book covers"],
    "color_palette": "muted earth tones, warm highlights",
    "line_work": "heavy ink outlines",
    "rendering": "painterly with texture",
    "mood": "menacing",
    "prompt_suffix": "dark fantasy illustration, oil painting, dramatic chiaroscuro lighting",
    "negative_prompt": "bright, cheerful, modern, clean"
  },
  "background_approach": "remove_after",
  "background_rationale": "Dark fantasy style produces better composition with full background; removing after preserves lighting quality",
  "target_platforms": ["blender", "unity", "unreal"],
  "total_assets": 4,
  "total_variations": 12,
  "total_generations": 12,
  "batch_size": 4,
  "reference_images": []
}
```

## User Interaction

If the PRD is incomplete or ambiguous, ask the user to clarify:
- Missing body type: Suggest based on the description (e.g., "dragon" -> quadruped_winged)
- Missing style: Ask for style preference or suggest based on description keywords
- Missing variations count: Default to 1 per asset
- Conflicting preferences: Explain the tradeoff and ask for a decision

## Completion

After writing the intake report, update `pipeline-state.json`:
- Set `stages.1-intake.status` to `"complete"`
- Add `intake/intake-report.json` to `stages.1-intake.artifacts`
- Set `batch_progress.total_assets` to the count of assets
- Set `batch_progress.current_asset_id` to the first asset ID
- Set `style_profile` to the constructed style profile
- Set `background_approach` to the resolved approach
- Output: `Stage 1 INTAKE complete -- {N} assets defined, style: {primary_style}, background: {approach}`
