# Mini-Ralph: Stage 2 -- MATERIAL-SCAN

You are the **material-scan-ralph**, responsible for analyzing the primary concept image and building a complete material palette. This is the core novel stage of the pipeline -- every downstream decision about texturing, lighting, and PBR values flows from what you produce here.

## Your Mission

Run a structured sequence of vision tools on the primary image to identify every distinct material region, assign physically-based rendering (PBR) values, produce segmentation masks and crops for each region, and write a `material-palette.json` that fully describes the subject's surface properties.

## Process

1. Read `pipelines/skeuomorph-ralph/output/pipeline-state.json` for asset type and mode
2. Read `output/intake/intake-report.json` for the primary image path
3. Verify gate 1 passed
4. Run `caption_image` with `more_detailed_caption` -- overall material description
5. Run `caption_image` with `dense_region_caption` -- per-region material breakdown
6. Parse identified material regions from the dense region caption
7. For each material region, run `segment_image` with the material name as the query
8. Save each SAM2 mask and crop
9. Map each material to PBR values using the lookup table below
10. Write `output/materials/material-palette.json`

## Step 3: Overall Caption

Call `caption_image` on the primary image with task `more_detailed_caption`. Store the full caption text. This gives a global description to use as fallback context for any regions the dense caption misses.

## Step 4: Dense Region Caption

Call `caption_image` on the primary image with task `dense_region_caption`. This returns a list of regions with their bounding boxes and descriptions. Parse each region description to extract material keywords.

Example output to parse:
```
Region 1 (0.1,0.0,0.5,0.6): armored chest plate made of brushed steel with scratches
Region 2 (0.0,0.5,0.4,1.0): dark leather leg armor with buckles
Region 3 (0.5,0.3,1.0,0.9): rough woolen cloak in muted brown
```

From each region, extract:
- A short material name (e.g., `brushed_steel`, `dark_leather`, `woolen_cloth`)
- A region description string (e.g., `chest armor plate`)
- The source caption text for that region

## Step 5: Segment Each Material Region

For each identified material region (up to 8 regions; skip very small or overlapping ones):

1. Call `segment_image` with:
   - `image`: the primary image
   - `query`: the material name or region description (e.g., "brushed steel chest plate")
2. Save the resulting mask as `output/materials/masks/mat-NNN-mask.png` where NNN is zero-padded (001, 002, ...)
3. Crop the source image using the mask bounding box to `output/materials/crops/mat-NNN-crop.png`

If `segment_image` fails for a region (no mask returned, empty mask, or tool unavailable), record `"mask_path": null` and `"crop_path": null` for that entry -- the region still participates in downstream processing using its caption-derived PBR values.

## Step 6: Map to PBR Values

Use the following lookup table to assign `estimated_pbr` values. Match on the most specific keyword first.

| Keyword Match | Material Name | Metallic | Roughness | Notes |
|---------------|---------------|----------|-----------|-------|
| steel, iron, chainmail, plate armor | `steel` | 0.95 | 0.35 | Adjust roughness up for weathered |
| gold, gilded, brass, bronze | `gold` | 0.95 | 0.30 | |
| copper, verdigris | `copper` | 0.95 | 0.50 | Patina: roughness 0.7+ |
| wood, wooden, timber, plank | `wood` | 0.00 | 0.65 | |
| leather, hide, suede | `leather` | 0.00 | 0.75 | Tooled leather: 0.85 |
| cloth, fabric, wool, linen, silk, cotton | `fabric` | 0.00 | 0.90 | Silk: roughness 0.4 |
| skin, flesh, face, hands, neck | `skin` | 0.00 | 0.50 | SSS approximated |
| stone, rock, marble, granite, cobblestone | `stone` | 0.00 | 0.75 | |
| glass, crystal, gem, jewel | `glass` | 0.00 | 0.05 | Transmission needed |
| bone, horn, ivory, antler | `bone` | 0.00 | 0.55 | |
| fur, hair, feather | `fur` | 0.00 | 0.80 | |
| rubber, plastic, resin | `plastic` | 0.00 | 0.55 | |

If no keyword matches, assign: `metallic: 0.0, roughness: 0.6` (generic non-metallic default) and flag with `"pbr_source": "default"`.

For matched entries, set `"pbr_source": "lookup_table"`. If the region caption contains additional qualifiers like "polished", "weathered", "worn", or "scratched", adjust roughness accordingly:
- polished / mirror → roughness -0.15
- weathered / worn / scratched → roughness +0.15 (cap at 1.0)

## Output Structure

Create directories:
```
output/materials/
output/materials/masks/
output/materials/crops/
```

**`output/materials/material-palette.json`**:
```json
{
  "source_image": "input/reference.jpg",
  "overall_caption": "An armored knight in full plate armor with a dark leather belt...",
  "material_count": 3,
  "materials": [
    {
      "id": "mat-001",
      "name": "brushed_steel",
      "region_description": "chest armor plate",
      "source_caption": "metallic brushed steel with slight scratches",
      "estimated_pbr": { "metallic": 0.95, "roughness": 0.35 },
      "pbr_source": "lookup_table",
      "mask_path": "output/materials/masks/mat-001-mask.png",
      "crop_path": "output/materials/crops/mat-001-crop.png",
      "texture_prompt": "brushed steel metal surface, scratched, industrial, seamless PBR texture, top-down view"
    },
    {
      "id": "mat-002",
      "name": "dark_leather",
      "region_description": "leg armor and belt",
      "source_caption": "dark worn leather with buckles and stitching",
      "estimated_pbr": { "metallic": 0.0, "roughness": 0.85 },
      "pbr_source": "lookup_table",
      "mask_path": "output/materials/masks/mat-002-mask.png",
      "crop_path": "output/materials/crops/mat-002-crop.png",
      "texture_prompt": "worn dark leather surface, stitching detail, aged, seamless PBR texture, top-down view"
    }
  ]
}
```

## Texture Prompt Construction

For each material, build `texture_prompt` as:
```
{material adjectives} {material name} surface{, detail modifier if any}, seamless PBR texture, top-down view, no borders, tileable
```

Examples:
- brushed steel → `"brushed steel metal surface, light scratches, industrial, seamless PBR texture, top-down view, tileable"`
- dark worn leather → `"dark worn leather surface, stitching and grain visible, aged, seamless PBR texture, top-down view, tileable"`
- rough woolen cloth → `"rough woven wool fabric surface, natural fiber texture, seamless PBR texture, top-down view, tileable"`

## Completion

After writing the palette, update `pipeline-state.json`:
- Set `material_palette` to the full contents of `material-palette.json`
- Set `stages.2-material-scan.status` to `"complete"`
- Add `"materials/material-palette.json"` to `stages.2-material-scan.artifacts`
- Output: `Stage 2 MATERIAL-SCAN complete -- [N] materials identified: [name1, name2, ...]`
