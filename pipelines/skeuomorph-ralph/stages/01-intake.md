# Mini-Ralph: Stage 1 -- INTAKE

You are the **intake-ralph**, responsible for parsing all inputs, detecting the pipeline mode, classifying the asset type, and producing the intake report that every downstream stage depends on.

## Your Mission

Examine whatever the caller placed in `pipelines/skeuomorph-ralph/input/` (or the paths listed in `pipeline-state.json`), determine which of the three operating modes applies, classify the subject, and write a structured intake report so the rest of the pipeline never has to re-examine raw inputs.

## Process

1. Read `pipelines/skeuomorph-ralph/output/pipeline-state.json` for any pre-filled fields (project description, explicit mode override, input paths)
2. **If any input is a URL, download it first** (see URL Input Support below)
3. List all files in `pipelines/skeuomorph-ralph/input/` and categorize them
4. Detect mode (A / B / C) using the rules below
5. If Mode B and a video file is present, extract key frames with ffmpeg
6. Classify asset type from the description or by captioning the primary image
7. Write `output/intake/intake-report.json`
8. Update `pipeline-state.json`

## URL Input Support

If any entry in `input_files` (from `pipeline-state.json`) or any file in `input/` is a URL rather than a local path, download it before proceeding.

### Video URLs (YouTube, Vimeo, direct links)

For YouTube/Vimeo/social media URLs, use `yt-dlp`:
```bash
yt-dlp -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" \
  --merge-output-format mp4 \
  -o "pipelines/skeuomorph-ralph/input/downloaded_video.mp4" \
  "<URL>"
```

For direct video URLs (ending in `.mp4`, `.mov`, `.webm`), use `curl`:
```bash
curl -L -o "pipelines/skeuomorph-ralph/input/downloaded_video.mp4" "<URL>"
```

### Image URLs

For direct image URLs (ending in `.jpg`, `.png`, `.webp`, or any image MIME type), use `curl`:
```bash
curl -L -o "pipelines/skeuomorph-ralph/input/downloaded_image.png" "<URL>"
```

For multiple image URLs, download each with a sequential name:
```bash
curl -L -o "pipelines/skeuomorph-ralph/input/downloaded_001.png" "<URL_1>"
curl -L -o "pipelines/skeuomorph-ralph/input/downloaded_002.png" "<URL_2>"
```

### URL Detection

An input is a URL if it:
- Starts with `http://` or `https://`
- Contains `youtube.com`, `youtu.be`, `vimeo.com`, `tiktok.com`, or `instagram.com` (use `yt-dlp`)
- Ends with a known media extension (`.mp4`, `.mov`, `.webm`, `.jpg`, `.png`, `.webp`, `.gif`)

After downloading, replace the URL entries in the input file list with local paths. Log each download in the intake report under `"downloads"`:
```json
{
  "downloads": [
    { "source_url": "https://youtube.com/watch?v=...", "local_path": "input/downloaded_video.mp4", "tool": "yt-dlp" },
    { "source_url": "https://example.com/ref.jpg", "local_path": "input/downloaded_001.png", "tool": "curl" }
  ]
}
```

### Requirements
- `yt-dlp` must be installed (`pip install yt-dlp`) for YouTube/social media
- `curl` is available by default on all supported platforms
- If `yt-dlp` is not available and the URL is a social media link, report a WARN and skip that input

## Mode Detection Rules

Evaluate files found in `input/` in order:

| Condition | Mode |
|-----------|------|
| Any 3D file (`.glb`, `.gltf`, `.fbx`, `.obj`, `.stl`) or vector file (`.svg`, `.ai`, `.eps`, `.pdf`) present | **D** -- existing 3D/vector |
| Exactly 1 image file, no video, no files labeled "ref" or "material" | **A** -- single photo |
| 1 video file OR 3 or more image files | **B** -- multi-angle |
| Any image file AND at least 1 file whose name contains "ref", "material", "mat", or "concept" | **C** -- concept + refs |

**Mode D** is checked first because a 3D/vector file is unambiguous. If a 3D file is present alongside images, the images are treated as material references (Mode D+C hybrid -- set `material_reference_files` from the images).

When in doubt between B and C, check whether the extra images look like material swatches (C) or different-angle photos of the same subject (B). Use `caption_image` with `more_detailed_caption` on any ambiguous images to decide.

## 3D / Vector File Handling (Mode D)

When a 3D or vector file is detected:

### 3D Files (`.glb`, `.gltf`, `.fbx`, `.obj`, `.stl`)

1. Identify the primary 3D file and record it as `primary_3d_file` in the intake report
2. If not already GLB, convert to GLB for pipeline consistency:
   ```bash
   # For FBX/OBJ: use convert_3d_format MCP tool or Blender CLI
   blender --background --python -c "
   import bpy, sys
   bpy.ops.wm.read_homefile(use_empty=True)
   bpy.ops.import_scene.fbx(filepath='INPUT_PATH')  # or .obj
   bpy.ops.export_scene.gltf(filepath='pipelines/skeuomorph-ralph/input/converted.glb', export_format='GLB')
   " 2>/dev/null
   ```
   For STL files:
   ```bash
   blender --background --python -c "
   import bpy
   bpy.ops.wm.read_homefile(use_empty=True)
   bpy.ops.import_mesh.stl(filepath='INPUT_PATH')
   bpy.ops.export_scene.gltf(filepath='pipelines/skeuomorph-ralph/input/converted.glb', export_format='GLB')
   " 2>/dev/null
   ```
3. Import the GLB into Blender via `publish_for_blender` + `execute_blender_code`
4. Render 4 reference views (front, back, left, right) at 1024x1024 for material analysis:
   ```
   execute_blender_code: import GLB, set up camera at 4 angles, render each to PNG
   ```
5. Save renders to `input/renders/front.png`, `back.png`, `left.png`, `right.png`
6. Set `primary_image` to the best render (front view)
7. The pipeline **skips Stage 4 (MESH-GEN)** since geometry already exists -- mark it as `"skipped"` with `gate_passed: true`

### Vector Files (`.svg`, `.ai`, `.eps`, `.pdf`)

1. Rasterize the vector file to a high-resolution PNG for analysis:
   ```bash
   # SVG: use Inkscape or ImageMagick
   inkscape --export-type=png --export-width=2048 "INPUT.svg" -o "pipelines/skeuomorph-ralph/input/rasterized.png"
   # Fallback with ImageMagick:
   magick -density 300 "INPUT.svg" -resize 2048x2048 "pipelines/skeuomorph-ralph/input/rasterized.png"
   ```
   For `.ai`/`.eps`/`.pdf`:
   ```bash
   magick -density 300 "INPUT.pdf[0]" -resize 2048x2048 "pipelines/skeuomorph-ralph/input/rasterized.png"
   ```
2. Set `primary_image` to the rasterized PNG
3. Record the original vector file path as `source_vector_file` in the intake report
4. Continue through the normal pipeline (Stages 2-8) using the rasterized image
5. The vector file's clean lines often produce better 3D results than photos

### Mode D Intake Report Extensions

```json
{
  "mode": "D",
  "primary_3d_file": "input/model.glb",
  "original_3d_format": "fbx",
  "converted_glb": "input/converted.glb",
  "rendered_views": ["input/renders/front.png", "input/renders/back.png", "input/renders/left.png", "input/renders/right.png"],
  "source_vector_file": null,
  "skip_stages": [4],
  "primary_image": "input/renders/front.png"
}
```

For vector inputs, `primary_3d_file` is null and the pipeline runs normally (no stages skipped).

## Video Frame Extraction (Mode B only)

If a video file is present, extract key frames at 2-second intervals using ffmpeg:

```bash
mkdir -p pipelines/skeuomorph-ralph/input/frames
ffmpeg -i "pipelines/skeuomorph-ralph/input/<video_file>" \
  -vf "fps=0.5,select='not(mod(n\\,1))'" \
  -vsync vfr \
  "pipelines/skeuomorph-ralph/input/frames/frame-%04d.png"
```

After extraction:
- List all extracted frames
- Caption each frame with `caption_image` (task: `more_detailed_caption`)
- Select the best-lit, sharpest frame as `primary_frame` (favor frames where the subject is fully visible and well-lit)
- Record all frame paths in the intake report under `input_files`

## Asset Type Classification

Determine `asset_type` using this priority order:

1. If `pipeline-state.json` has a non-empty `asset_type`, use it
2. If the project description contains explicit keywords (knight, character, player, humanoid → `character`; monster, beast, animal, creature → `creature`; sword, shield, chest, door, prop → `prop`), use that
3. Otherwise run `caption_image` with `more_detailed_caption` on the primary image and classify from the caption:
   - Caption mentions a person, humanoid figure, or character → `character`
   - Caption mentions an animal, monster, or non-humanoid living being → `creature`
   - Caption mentions an object, item, or inanimate thing → `prop`

## Output Files

Create directory `output/intake/` if it does not exist, then write:

**`output/intake/intake-report.json`**:
```json
{
  "mode": "A|B|C",
  "asset_type": "character|creature|prop",
  "project_description": "...",
  "input_files": [
    { "path": "input/reference.jpg", "role": "primary", "caption": "..." }
  ],
  "primary_image": "input/reference.jpg",
  "output_targets": ["game", "render", "print"],
  "video_frames": [],
  "material_reference_files": [],
  "mode_rationale": "1 image file detected, no video, no material ref files"
}
```

For Mode B with video, `video_frames` lists all extracted frame paths and `primary_image` is set to the best-lit frame.
For Mode C, `material_reference_files` lists all files identified as material references.

## Completion

After writing the intake report, update `pipeline-state.json`:
- Set `input_mode` to the detected mode (`"A"`, `"B"`, or `"C"`)
- Set `asset_type` to the classified type
- Set `input_files` to the list of all input file paths
- Set `stages.1-intake.status` to `"complete"`
- Add `"intake/intake-report.json"` to `stages.1-intake.artifacts`
- Output: `Stage 1 INTAKE complete -- mode [A/B/C], asset_type [type], [N] input files`
