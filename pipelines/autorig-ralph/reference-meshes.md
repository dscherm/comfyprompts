# AutoRig Ralph -- Reference Mesh Library

Reference rigged meshes improve the pipeline in two ways:
1. **Skeleton template matching** -- compare predicted skeleton against known-good reference for the body type
2. **Weight transfer** -- copy skin weights from well-rigged reference to new mesh via Blender's Transfer Weights

## How to Use Reference Meshes

Store downloaded references in `pipelines/autorig-ralph/references/` organized by body type:

```
references/
├── humanoid/
│   ├── quaternius_superhero_male.glb      (CC0, low-poly, Rigify-compatible)
│   ├── quaternius_regular_female.glb      (CC0, low-poly, Rigify-compatible)
│   ├── mixamo_ybot.fbx                    (Adobe free, standard Mixamo skeleton)
│   ├── mixamo_xbot.fbx                    (Adobe free, standard Mixamo skeleton)
│   └── sketchfab_human_basemesh.glb       (CC-BY, male+female pair)
├── quadruped/
│   ├── quaternius_wolf.glb                (CC0, animated, low-poly)
│   ├── quaternius_horse.glb               (CC0, animated, low-poly)
│   ├── quaternius_dog.glb                 (CC0, animated, low-poly)
│   └── sketchfab_camel.glb               (CC-BY, rigged)
├── creature/
│   ├── quaternius_dragon.glb              (CC0, animated)
│   ├── quaternius_skeleton_enemy.glb      (CC0, animated humanoid-ish)
│   └── turbosquid_dragon_free.fbx         (Royalty-free)
├── mech/
│   └── quaternius_mech.glb                (CC0, animated)
└── serpentine/
    └── quaternius_snake.glb               (CC0, animated)
```

---

## Source 1: Quaternius (CC0 -- Best for Pipeline)

**License**: CC0 (public domain) -- no attribution required, commercial use allowed
**Formats**: FBX, GLB/GLTF, OBJ, Blend
**Quality**: Low-poly game-ready, properly rigged with standard bone hierarchies

### Must-Download Packs

| Pack | Body Types Covered | Download |
|------|-------------------|----------|
| **Universal Base Characters** | 6 humanoids (Superhero/Regular/Teen x Male/Female), humanoid rig, ~13k tris each | https://quaternius.itch.io/universal-base-characters |
| **Universal Animation Library** | Humanoid rig template + 120 retargetable animations | https://quaternius.itch.io/universal-animation-library |
| **Ultimate Animated Animal Pack** | 12 quadrupeds (bull, fox, horse, donkey, wolf, cow, deer, stag, llama, alpaca, husky, shiba inu) with 12+ animations each | https://quaternius.com/packs/ultimateanimatedanimals.html |
| **Farm Animal Pack** | 7 farm animals (cow, pig, sheep, chicken, horse, goat, donkey) rigged + animated | https://quaternius.com/packs/farmanimal.html |
| **Animated Monster Pack** | Dragon, skeleton, bat, slime -- creature reference | https://quaternius.com/packs/animatedmonster.html |
| **Easy Enemy Pack** | Bee, wasp, snake, rat, spider, frog -- small creature/insect reference | https://quaternius.com/packs/easyenemy.html |
| **Animated Mech Pack** | Mechanical biped -- mech body type reference | https://quaternius.com/packs/animatedmech.html |
| **RPG Character Pack** | Wizard, knight, monk, ranger, assassin -- humanoid with armor/accessories | https://quaternius.com/packs/rpgcharacter.html |
| **Animated Dinosaur Pack** | Dinosaurs -- large creature reference | https://quaternius.com/packs/animateddinosaur.html |

**Why Quaternius is ideal**: CC0 license means zero legal risk embedding these as pipeline templates. Models have clean, game-ready topology with standard bone naming that maps well to Unity/Unreal conventions.

---

## Source 2: Mixamo (Adobe Free -- Industry Standard Humanoid Rig)

**License**: Free with Adobe account, royalty-free for any project
**Formats**: FBX (with skin), Collada (DAE)
**Quality**: Production-quality humanoid skeleton, ~65 bones, Mecanim-compatible

### Must-Download Characters

| Character | Why | How to Get |
|-----------|-----|------------|
| **Y Bot** (male base) | Industry-standard Mixamo skeleton, perfect humanoid template | mixamo.com -> Characters -> Y Bot -> Download FBX |
| **X Bot** (female base) | Same skeleton as Y Bot, female proportions | mixamo.com -> Characters -> X Bot -> Download FBX |
| **Mutant** | Larger/bulkier humanoid, tests edge cases | mixamo.com -> Characters -> Mutant -> Download FBX |
| **Paladin** | Humanoid with armor (hard-surface reference) | mixamo.com -> Characters -> Paladin -> Download FBX |

**Download steps**:
1. Go to https://www.mixamo.com/
2. Sign in with Adobe account (free)
3. Click "Characters" tab
4. Select character, click "Download"
5. Format: FBX Binary, Pose: T-Pose, check "With Skin"

**Why Mixamo matters**: The Mixamo skeleton is the de facto standard for humanoid animation retargeting. Having Y Bot / X Bot as references lets the pipeline validate bone mapping against the most widely-used skeleton convention.

---

## Source 3: Sketchfab (CC-BY -- High Quality, Varied Styles)

**License**: CC-BY (attribution required) or CC0 depending on model
**Formats**: GLB/GLTF (native download), also FBX/OBJ via conversion
**Quality**: Varies -- hand-pick quality models

### Must-Download Models

| Model | Body Type | Link |
|-------|-----------|------|
| **Human Models Set - Male/Female (Rigged)** | Humanoid pair | https://sketchfab.com/3d-models/human-models-set-malefemale-rigged-7311fcfdc03e4234900eeced42a1e669 |
| **Humanoid Avatar with Rig** | Generic humanoid | https://sketchfab.com/3d-models/humanoid-avatar-with-rig-995558e2514644909c9037b0e7762855 |
| **DREX Human Character** | Humanoid, 75 outfits (hard-surface reference) | https://sketchfab.com/3d-models/drex-human-3d-character-9e20ab49ceb147b2a1e867187258c370 |
| **Camel (GLB)** | Quadruped | https://sketchfab.com/3d-models/camel-download-the-original-glb-05a0854fb54d4e34a100016545cc69e5 |
| **DL - Basemesh Animals collection** | Multiple quadrupeds | https://sketchfab.com/apatel/collections/dl-basemesh-animals-209b4e514f2b42cfae18d7bf03bf47d4 |

**Note**: blender-mcp has built-in Sketchfab search/download! You can use:
```
blender-mcp: search_sketchfab(query="rigged humanoid", downloadable=true)
blender-mcp: download_sketchfab(model_id="...")
```

---

## Source 4: Unity Asset Store (Free Mecanim Packs)

**License**: Unity Asset Store EULA (free for Unity projects)
**Formats**: FBX (Mecanim-compatible)

| Pack | Contents |
|------|----------|
| **RPG Character Mecanim Animation Pack FREE** | Rigged humanoid + animations, Mecanim avatar | Unity Asset Store |
| **Human Basic Motions FREE** | Humanoid reference animations | Unity Asset Store |

---

## Source 5: Rigify Built-in Templates (Already Installed)

Blender's Rigify addon includes metarig templates for free -- no download needed:

```python
# Via blender-mcp execute_blender_code:
import bpy
bpy.ops.preferences.addon_enable(module='rigify')

# Human metarig (standard humanoid skeleton)
bpy.ops.object.armature_human_metarig_add()

# Other built-in types:
# bpy.ops.object.armature_basic_human_metarig_add()  # simplified
# Cat, horse, shark, bird metarigs available via Rigify samples
```

These are skeleton-only (no mesh) but define the **gold standard bone hierarchy** for each body type.

---

## Priority Download Order

For maximum pipeline coverage with minimum effort:

### Phase 1: Core Templates (download first)
1. **Quaternius Universal Base Characters** -- 6 humanoid body types, CC0
2. **Mixamo Y Bot + X Bot** -- industry-standard skeleton
3. **Quaternius Ultimate Animated Animal Pack** -- 12 quadrupeds, CC0

### Phase 2: Creature Coverage
4. **Quaternius Animated Monster Pack** -- dragon + skeleton + bat
5. **Quaternius Easy Enemy Pack** -- insects, snakes, small creatures
6. **Quaternius Animated Mech Pack** -- mechanical biped

### Phase 3: Hard-Surface Reference
7. **Quaternius RPG Character Pack** -- humanoids with armor/weapons
8. **Mixamo Paladin** -- armor attachment reference
9. **Sketchfab DREX** -- 75 outfit variations

### Phase 4: Edge Cases
10. **Quaternius Animated Dinosaur Pack** -- large creatures
11. **Sketchfab animal basemesh collection** -- varied quadrupeds
12. **Quaternius Farm Animal Pack** -- additional quadruped variety

---

## Integration with Pipeline

Once downloaded, reference meshes are used in two pipeline stages:

### Stage 3 (SKELETON-PREDICT): Template Matching
```python
# Compare predicted skeleton against reference
ref_armature = load_reference("humanoid/quaternius_superhero_male.glb")
pred_armature = predicted_skeleton

# Check bone count similarity
# Check hierarchy structure match
# Check bone position ratios (head height %, hip height %, etc.)
# If deviation > threshold, WARN and attempt alignment
```

### Stage 4 (SKIN-WEIGHTS): Weight Transfer
```python
# Transfer weights from reference to new mesh
import bpy

ref_mesh = bpy.data.objects["reference_mesh"]
new_mesh = bpy.data.objects["target_mesh"]

# Select target, then reference
new_mesh.select_set(True)
ref_mesh.select_set(True)
bpy.context.view_layer.objects.active = new_mesh

# Transfer vertex data (nearest face interpolated)
bpy.ops.object.data_transfer(
    use_reverse_transfer=True,
    data_type='VGROUP_WEIGHTS',
    vert_mapping='POLYINTERP_NEAREST',
    layers_select_src='NAME',
    layers_select_dst='ALL'
)
```

This is how Mixamo works internally -- it deforms a template rig to fit the target mesh, then transfers weights. Having multiple reference body types gives the pipeline a "closest match" to transfer from.
