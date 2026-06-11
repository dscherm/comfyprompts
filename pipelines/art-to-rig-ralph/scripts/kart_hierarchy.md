# Kart Modular Hierarchy Design

## Reference: Mario Kart Standard Kart
- 3 flat meshes (body, detail, emblem area), 977 verts total
- No armature, no bones, no vertex groups
- Hierarchy built entirely in Unity via prefab + C# scripts
- Wheels are separate GameObjects with programmatic rotation
- Steering = Y-axis rotation on front tire parent transforms

## Our Approach: Hybrid (Blender split + Unity prefab)

Generate a single kart mesh via ComfyUI (Hunyuan3D), then split it in Blender
into separate objects by bounding-box region analysis. Assemble into a parent-child
hierarchy with empties for dynamic attachment points (wheels, particles, seat).

## Target Hierarchy

```
KartRoot (Empty @ origin)
├── Chassis (Mesh — center ~60% of geometry)
│   ├── Hood (Mesh — front 20% of length)
│   ├── Bumper_Front (Mesh — front 5% of length, lower half)
│   ├── Bumper_Rear (Mesh — rear 5% of length, lower half)
│   ├── Panel_L (Mesh — left 15% of width)
│   ├── Panel_R (Mesh — right 15% of width)
│   ├── Spoiler (Mesh — rear 15%, upper half)
│   ├── Seat (Empty — center, driver attachment point)
│   └── EngineBay (Empty — rear center, particle anchor)
├── Axle_Front (Empty @ front axle position)
│   ├── WheelMount_FL (Empty — front-left wheel attach)
│   ├── WheelMount_FR (Empty — front-right wheel attach)
│   └── SteeringColumn (Empty — steering pivot)
├── Axle_Rear (Empty @ rear axle position)
│   ├── WheelMount_RL (Empty — rear-left wheel attach)
│   ├── WheelMount_RR (Empty — rear-right wheel attach)
│   ├── Exhaust_L (Empty — left exhaust particle anchor)
│   └── Exhaust_R (Empty — right exhaust particle anchor)
├── FX_Boost_L (Empty — left boost particle spawn)
├── FX_Boost_R (Empty — right boost particle spawn)
├── FX_Drift_L (Empty — left drift spark spawn)
└── FX_Drift_R (Empty — right drift spark spawn)
```

## Region Split Rules (Bounding Box Fractions)

Kart is oriented: +Y = forward, +X = right, +Z = up (Blender convention).
After import, auto-detect longest axis as "length" (forward).

| Region | Length Range | Width Range | Height Range | Detachable |
|--------|-------------|-------------|--------------|------------|
| Hood | 0.75–1.0 | 0.15–0.85 | 0.3–1.0 | Yes |
| Bumper_Front | 0.90–1.0 | 0.1–0.9 | 0.0–0.4 | Yes |
| Bumper_Rear | 0.0–0.10 | 0.1–0.9 | 0.0–0.4 | Yes |
| Panel_L | 0.15–0.85 | 0.0–0.15 | 0.2–0.8 | Yes |
| Panel_R | 0.15–0.85 | 0.85–1.0 | 0.2–0.8 | Yes |
| Spoiler | 0.0–0.15 | 0.15–0.85 | 0.6–1.0 | Yes |
| Chassis | everything else | — | — | No (parent) |

## Empty Placement (Normalized Positions)

| Empty | Length | Width | Height | Purpose |
|-------|--------|-------|--------|---------|
| KartRoot | 0.5 | 0.5 | 0.0 | Root origin at bottom center |
| Seat | 0.45 | 0.5 | 0.55 | Driver attachment |
| EngineBay | 0.15 | 0.5 | 0.35 | Engine particle anchor |
| Axle_Front | 0.85 | 0.5 | 0.12 | Front axle pivot |
| Axle_Rear | 0.15 | 0.5 | 0.12 | Rear axle pivot |
| WheelMount_FL | 0.85 | 0.0 | 0.12 | Front-left wheel |
| WheelMount_FR | 0.85 | 1.0 | 0.12 | Front-right wheel |
| WheelMount_RL | 0.15 | 0.0 | 0.12 | Rear-left wheel |
| WheelMount_RR | 0.15 | 1.0 | 0.12 | Rear-right wheel |
| SteeringColumn | 0.75 | 0.5 | 0.55 | Steering visual pivot |
| Exhaust_L | 0.05 | 0.2 | 0.25 | Left exhaust |
| Exhaust_R | 0.05 | 0.8 | 0.25 | Right exhaust |
| FX_Boost_L | 0.0 | 0.25 | 0.2 | Left boost particles |
| FX_Boost_R | 0.0 | 0.75 | 0.2 | Right boost particles |
| FX_Drift_L | 0.15 | 0.0 | 0.1 | Left drift sparks |
| FX_Drift_R | 0.15 | 1.0 | 0.1 | Right drift sparks |

## Export Formats

| Format | Target | Notes |
|--------|--------|-------|
| FBX (Binary) | Unity (primary) | Mecanim Generic, -Z forward, Y up |
| GLB | Blender / web | Blender conventions |
| FBX (Binary) | Unreal | Z up, X forward |

## Key Differences from Old 17-Bone Approach

| Aspect | Old (Armature) | New (Modular) |
|--------|---------------|---------------|
| Rigging | 17-bone skeleton + vertex weights | No bones, separate mesh objects |
| Detachment | Weight group isolation | Separate objects, parent/unparent |
| Wheel mounts | Bones with no geometry | Empty GameObjects |
| Unity import | Generic rig, bone mapping | Prefab hierarchy, no rig needed |
| Complexity | Weight painting issues | Clean separation, simpler |
| MK-compatible | No | Yes — same pattern |

## Back-Pressure Considerations

1. **Mesh split failure**: If bounding-box split produces empty regions, fall back to keeping
   the entire mesh as Chassis (graceful degradation)
2. **ComfyUI timeout**: Retry with lower resolution, then fall back to TripoSG
3. **VRAM OOM**: Queue karts sequentially instead of parallel, reduce octree resolution
4. **Blender crash**: Checkpoint after each major step (import, split, assemble, export)
5. **Throughput**: Max 2 concurrent ComfyUI generations, max 3 concurrent Blender headless
