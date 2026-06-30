#!/usr/bin/env python3
"""package_for_unity.py — deploy the 9 barbarian clips into the Unity project as a
Humanoid/Mecanim avatar + a hand-authored Animator controller.

Unity was NOT running when this was authored, so coplay-mcp could not drive a live
editor. Instead this writes the import as DETERMINISTIC ON-DISK ASSETS (exactly how
the kart deploy works: FBX + .meta to disk, Unity imports on next open). The pieces
that look like they'd need a live editor are all deterministic in Unity's serialized
format, so no live step is required to PRODUCE the package:

  * Humanoid import + avatar — mirror the project's existing humanoid meta
    (Assets/.../Hitogatas.fbx.meta): animationType: 3, avatarSetup: 1 (Create From
    This Model) on EVERY clip. Each FBX self-creates its own valid Humanoid avatar
    from its own model (exactly how stock Mixamo FBX import). The bone map (UniRig
    role names -> Mecanim human bones) is written explicitly into
    humanDescription.human so the avatar does not depend on Unity's name-guessing.
    skeleton: [] -> Unity builds the T-pose + skeleton from the model.

    Why not Copy From Other? The earlier package made idle CreateFromThisModel and
    the other 8 CopyFromOther idle's avatar. That failed in the live editor with
    "Copied Avatar Rig Configuration mis-match: Transform Armature not found in
    HumanDescription" — every retarget FBX has an extra 'Armature' transform above
    'hips', and a copied HumanDescription (empty skeleton) can't account for it, so
    the copy is rejected. CreateFromThisModel sidesteps the copy entirely: idle
    already imported clean this way, and Unity Humanoid clips are normalized to
    muscle space, so any clip plays on the character's avatar regardless of which
    avatar instance it was imported with. idle's avatar stays the canonical
    character avatar; the other clips just don't depend on it at import time.
  * Avatar reference — an FBX's generated Avatar sub-asset has the deterministic
    fileID 9000000 (classID 90), so the 8 Copy-From-Other clips can reference idle's
    avatar as {fileID: 9000000, guid: <idle guid>, type: 3} with no live import.
  * Animator motions — an FBX's primary AnimationClip has the deterministic fileID
    7400000 (classID 74), confirmed against the project's boost.controller, so each
    Animator state can bind its clip as {fileID: 7400000, guid: <clip guid>, type: 3}
    by name-independent reference.

Loop Time is the one property that genuinely needs the imported clip's internal
name; it is declared per-clip in ANIMATION-MANIFEST.json and is applied on import by
the GS4 editor validator. Live avatar/clip/transition VALIDATION is GS4's job.

Usage:
    python package_for_unity.py [--unity ../soapbox-unity] [--dry-run]
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PIPE = os.path.dirname(HERE)                                   # pipelines/animate-ralph
SRC_DIR = os.path.join(PIPE, "output", "export", "barbarian", "textured")
MANIFEST_TRACKED = os.path.join(PIPE, "output", "export", "barbarian", "ANIMATION-MANIFEST.json")

# UniRig role name -> Mecanim required/optional human bone. All 15 REQUIRED human
# bones are present; chest/neck/shoulders are the optional ones we also map.
BONE_MAP = {
    "hips": "Hips", "spine": "Spine", "chest": "Chest", "neck": "Neck", "head": "Head",
    "shoulder.l": "LeftShoulder", "upperarm.l": "LeftUpperArm",
    "lowerarm.l": "LeftLowerArm", "hand.l": "LeftHand",
    "shoulder.r": "RightShoulder", "upperarm.r": "RightUpperArm",
    "lowerarm.r": "RightLowerArm", "hand.r": "RightHand",
    "upperleg.l": "LeftUpperLeg", "lowerleg.l": "LeftLowerLeg", "foot.l": "LeftFoot",
    "upperleg.r": "RightUpperLeg", "lowerleg.r": "RightLowerLeg", "foot.r": "RightFoot",
}
# Filler/connector bones with no Mecanim slot — left unmapped by design (recorded in
# the manifest). bone_3/bone_4 are extra spine segments; bone_9/11/13/16/18 are arm
# twist/filler; hip_connector.* are pelvis connectors.
UNMAPPED_BONES = ["bone_3", "bone_4", "bone_9", "bone_11", "bone_13",
                  "bone_16", "bone_18", "hip_connector.l", "hip_connector.r"]

# Clip spec: name, loop, root_motion, animator_state, category.
# Durations are measured from each FBX's action frame_range at fps 100 (the retarget
# export fps) — see scripts probe; GS4 re-reads clip length and diffs the manifest.
CLIPS = [
    # name        loop  root   state        category      frames
    ("idle",      True,  False, "Idle",      "locomotion", 140),
    ("walk",      True,  True,  "Walk",      "locomotion", 120),
    ("run",       True,  True,  "Run",       "locomotion", 120),
    ("attack",    False, False, "Attack",    "action",     130),
    ("hit",       False, False, "Hit",       "action",     130),
    ("dodge",     False, True,  "Dodge",     "action",     102),
    ("block",     False, False, "Block",     "action",     150),
    ("wave",      False, False, "Wave",      "emote",      150),
    ("celebrate", False, False, "Celebrate", "emote",      150),
]
FPS = 100.0
AVATAR_SOURCE = "idle"   # canonical rig: Create From This Model; others Copy From Other

# Trigger params (one per non-locomotion clip) + the Speed float for idle/walk/run.
TRIGGER_CLIPS = [c for c in CLIPS if c[4] in ("action", "emote")]

UNITY_AVATAR_FILEID = 9000000   # classID 90 — generated Avatar sub-asset of an FBX
UNITY_CLIP_FILEID = 7400000     # classID 74 — primary AnimationClip of an FBX


def guid(s: str) -> str:
    """Deterministic 32-hex Unity guid from a stable string."""
    return hashlib.md5(s.encode()).hexdigest()


# --------------------------------------------------------------------------- meta

def fbx_meta(clip: str, gd: str) -> str:
    human = "\n".join(
        f"    - boneName: {bone}\n"
        f"      humanName: {human_name}\n"
        f"      limit:\n"
        f"        min: {{x: 0, y: 0, z: 0}}\n"
        f"        max: {{x: 0, y: 0, z: 0}}\n"
        f"        value: {{x: 0, y: 0, z: 0}}\n"
        f"        length: 0\n"
        f"        modified: 0"
        for bone, human_name in BONE_MAP.items()
    )
    # Every clip is CreateFromThisModel (avatarSetup: 1) and builds its own avatar.
    # No CopyFromOther reference — a copied HumanDescription can't account for the
    # extra 'Armature' root above 'hips' (Unity: "Transform Armature not found").
    avatar_setup = 1
    avatar_src = "{instanceID: 0}"
    return f"""fileFormatVersion: 2
guid: {gd}
ModelImporter:
  serializedVersion: 24200
  internalIDToNameTable: []
  externalObjects: {{}}
  materials:
    materialImportMode: 2
    materialName: 0
    materialSearch: 1
    materialLocation: 1
  animations:
    legacyGenerateAnimations: 4
    bakeSimulation: 0
    resampleCurves: 1
    optimizeGameObjects: 0
    motionNodeName:
    animationImportErrors:
    animationImportWarnings:
    animationRetargetingWarnings:
    animationDoRetargetingWarnings: 0
    importAnimatedCustomProperties: 0
    importConstraints: 0
    animationCompression: 1
    animationRotationError: 0.5
    animationPositionError: 0.5
    animationScaleError: 0.5
    animationWrapMode: 0
    extraExposedTransformPaths: []
    extraUserProperties: []
    clipAnimations: []
    isReadable: 0
  meshes:
    lODScreenPercentages: []
    globalScale: 1
    meshCompression: 0
    addColliders: 0
    useSRGBMaterialColor: 1
    sortHierarchyByName: 1
    importVisibility: 1
    importBlendShapes: 1
    importCameras: 1
    importLights: 1
    nodeNameCollisionStrategy: 1
    fileIdsGeneration: 2
    swapUVChannels: 0
    generateSecondaryUV: 0
    useFileUnits: 1
    keepQuads: 0
    weldVertices: 1
    bakeAxisConversion: 0
    preserveHierarchy: 0
    skinWeightsMode: 0
    maxBonesPerVertex: 4
    minBoneWeight: 0.001
    optimizeBones: 1
    indexFormat: 0
    useFileScale: 1
  tangentSpace:
    normalSmoothAngle: 60
    normalImportMode: 0
    tangentImportMode: 3
    normalCalculationMode: 4
    normalSmoothingSource: 0
  referencedClips: []
  importAnimation: 1
  humanDescription:
    serializedVersion: 3
    human:
{human}
    skeleton: []
    armTwist: 0.5
    foreArmTwist: 0.5
    upperLegTwist: 0.5
    legTwist: 0.5
    armStretch: 0.05
    legStretch: 0.05
    feetSpacing: 0
    globalScale: 1
    rootMotionBoneName: hips
    hasTranslationDoF: 0
    hasExtraRoot: 0
    skeletonHasParents: 1
  lastHumanDescriptionAvatarSource: {avatar_src}
  autoGenerateAvatarMappingIfUnspecified: 1
  animationType: 3
  humanoidOversampling: 1
  avatarSetup: {avatar_setup}
  addHumanoidExtraRootOnlyWhenUsingAvatar: 1
  importBlendShapeDeformPercent: 1
  remapMaterialsIfMaterialImportModeIsNone: 0
  additionalBone: 0
  userData:
  assetBundleName:
  assetBundleVariant:
"""


def folder_meta(gd: str) -> str:
    return (f"fileFormatVersion: 2\nguid: {gd}\nfolderAsset: yes\n"
            "DefaultImporter:\n  externalObjects: {}\n  userData:\n"
            "  assetBundleName:\n  assetBundleVariant:\n")


# ---------------------------------------------------------------- animator controller

class FileIds:
    """Deterministic, collision-free int64 fileIDs per Unity class."""
    def __init__(self):
        self._n = {}

    def new(self, classid: int) -> int:
        self._n[classid] = self._n.get(classid, 0) + 1
        return classid * 10_000_000_000_000 + self._n[classid]


def build_controller(clip_guids: dict[str, str]) -> str:
    ids = FileIds()
    CTRL = 9100000
    sm_id = ids.new(1107)

    states = {}      # clip name -> state fileID
    state_blocks = []
    transitions = []   # yaml blocks
    child_states_yaml = []
    anystate_trans_refs = []

    # grid positions
    def pos(col, row):
        return f"{{x: {260 + col * 250}, y: {40 + row * 70}, z: 0}}"

    # --- locomotion states (idle/walk/run) on a row, with their out-transitions ---
    loco = [c for c in CLIPS if c[4] == "locomotion"]
    for i, (name, *_rest) in enumerate(loco):
        states[name] = ids.new(1102)
    actions = [c for c in CLIPS if c[4] != "locomotion"]
    for i, (name, *_rest) in enumerate(actions):
        states[name] = ids.new(1102)

    idle_id, walk_id, run_id = states["idle"], states["walk"], states["run"]

    def transition(dst_id, conditions, has_exit, exit_time=0.85, dur=0.15):
        tid = ids.new(1101)
        cond_yaml = "\n".join(
            f"  - m_ConditionMode: {m}\n    m_ConditionEvent: {p}\n    m_EventTreshold: {t}"
            for (m, p, t) in conditions
        ) if conditions else ""
        cond_field = f"m_Conditions:\n{cond_yaml}" if conditions else "m_Conditions: []"
        transitions.append(f"""--- !u!1101 &{tid}
AnimatorStateTransition:
  m_ObjectHideFlags: 1
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_Name:
  {cond_field}
  m_DstStateMachine: {{fileID: 0}}
  m_DstState: {{fileID: {dst_id}}}
  m_Solo: 0
  m_Mute: 0
  m_IsExit: 0
  serializedVersion: 3
  m_TransitionDuration: {dur}
  m_TransitionOffset: 0
  m_ExitTime: {exit_time}
  m_HasExitTime: {1 if has_exit else 0}
  m_HasFixedDuration: 1
  m_InterruptionSource: 0
  m_OrderedInterruption: 1
  m_CanTransitionToSelf: 1""")
        return tid

    # condition modes: 1=If, 3=Greater, 4=Less
    state_out = {name: [] for name in states}
    # idle -> walk when Speed > 0.1
    state_out["idle"].append(transition(walk_id, [(3, "Speed", 0.1)], False))
    # walk -> idle (<0.1), walk -> run (>0.6)
    state_out["walk"].append(transition(idle_id, [(4, "Speed", 0.1)], False))
    state_out["walk"].append(transition(run_id, [(3, "Speed", 0.6)], False))
    # run -> walk (<0.6)
    state_out["run"].append(transition(walk_id, [(4, "Speed", 0.6)], False))
    # each action/emote -> idle when finished (exit time, no condition)
    for name, _l, _r, _s, _cat, _f in actions:
        state_out[name].append(transition(idle_id, [], True, exit_time=0.85))

    # AnyState -> each action/emote on its trigger
    for name, _l, _r, _s, _cat, _f in actions:
        trig = name.capitalize()
        anystate_trans_refs.append(transition(states[name], [(1, trig, 0)], False, dur=0.1))

    # --- emit state objects ---
    col_row = {}
    for i, (name, *_r) in enumerate(loco):
        col_row[name] = (i, 0)
    for i, (name, *_r) in enumerate(actions):
        col_row[name] = (i, 2)
    for name, _loop, _root, _state, _cat, _f in CLIPS:
        sid = states[name]
        trans_refs = "\n".join(f"  - {{fileID: {t}}}" for t in state_out[name]) or ""
        trans_field = f"m_Transitions:\n{trans_refs}" if state_out[name] else "m_Transitions: []"
        c, r = col_row[name]
        state_blocks.append(f"""--- !u!1102 &{sid}
AnimatorState:
  serializedVersion: 6
  m_ObjectHideFlags: 1
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_Name: {name.capitalize()}
  m_Speed: 1
  m_CycleOffset: 0
  {trans_field}
  m_StateMachineBehaviours: []
  m_Position: {pos(c, r)}
  m_IKOnFeet: 0
  m_WriteDefaultValues: 1
  m_Mirror: 0
  m_SpeedParameterActive: 0
  m_MirrorParameterActive: 0
  m_CycleOffsetParameterActive: 0
  m_TimeParameterActive: 0
  m_Motion: {{fileID: {UNITY_CLIP_FILEID}, guid: {clip_guids[name]}, type: 3}}
  m_Tag:
  m_SpeedParameter:
  m_MirrorParameter:
  m_CycleOffsetParameter:
  m_TimeParameter:""")
        child_states_yaml.append(
            f"  - serializedVersion: 1\n    m_State: {{fileID: {sid}}}\n"
            f"    m_Position: {pos(c, r)}")

    anystate_yaml = ("\n".join(f"  - {{fileID: {t}}}" for t in anystate_trans_refs)
                     if anystate_trans_refs else "")
    anystate_field = (f"m_AnyStateTransitions:\n{anystate_yaml}"
                      if anystate_trans_refs else "m_AnyStateTransitions: []")

    sm_block = f"""--- !u!1107 &{sm_id}
AnimatorStateMachine:
  serializedVersion: 6
  m_ObjectHideFlags: 1
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_Name: Base Layer
  m_ChildStates:
{chr(10).join(child_states_yaml)}
  m_ChildStateMachines: []
  {anystate_field}
  m_EntryTransitions: []
  m_StateMachineTransitions: {{}}
  m_StateMachineBehaviours: []
  m_AnyStatePosition: {{x: 50, y: 20, z: 0}}
  m_EntryPosition: {{x: 50, y: 120, z: 0}}
  m_ExitPosition: {{x: 1200, y: 120, z: 0}}
  m_ParentStateMachinePosition: {{x: 800, y: 20, z: 0}}
  m_DefaultState: {{fileID: {idle_id}}}"""

    # --- parameters: Speed (float) + a Trigger per action/emote ---
    params = [("Speed", 1, "m_DefaultFloat: 0")]   # type 1 = Float
    for name, *_r in actions:
        params.append((name.capitalize(), 9, "m_DefaultFloat: 0"))   # type 9 = Trigger
    param_yaml = "\n".join(
        f"  - m_Name: {pn}\n    m_Type: {pt}\n    {df}\n    m_DefaultInt: 0\n"
        f"    m_DefaultBool: 0\n    m_Controller: {{fileID: {CTRL}}}"
        for pn, pt, df in params
    )

    ctrl_block = f"""%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!91 &{CTRL}
AnimatorController:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_Name: Barbarian
  serializedVersion: 5
  m_AnimatorParameters:
{param_yaml}
  m_AnimatorLayers:
  - serializedVersion: 5
    m_Name: Base Layer
    m_StateMachine: {{fileID: {sm_id}}}
    m_Mask: {{fileID: 0}}
    m_Motions: []
    m_Behaviours: []
    m_BlendingMode: 0
    m_SyncedLayerIndex: -1
    m_DefaultWeight: 0
    m_IKPass: 0
    m_SyncedLayerAffectsTiming: 0
    m_Controller: {{fileID: {CTRL}}}
"""
    return ctrl_block + sm_block + "\n" + "\n".join(state_blocks) + "\n" + "\n".join(transitions) + "\n"


def controller_meta(gd: str) -> str:
    return (f"fileFormatVersion: 2\nguid: {gd}\n"
            "NativeFormatImporter:\n  externalObjects: {}\n  mainObjectFileID: 9100000\n"
            "  userData:\n  assetBundleName:\n  assetBundleVariant:\n")


# --------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unity", default=os.path.normpath(os.path.join(PIPE, "..", "..", "..", "soapbox-unity")),
                    help="Unity project root (default: sibling ../soapbox-unity)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    unity_root = os.path.abspath(args.unity)
    dest = os.path.join(unity_root, "Assets", "Animations", "Barbarian")
    if not os.path.isdir(os.path.join(unity_root, "Assets")):
        sys.exit(f"ERROR: Unity project not found at {unity_root} (no Assets/)")
    for name, *_ in CLIPS:
        if not os.path.isfile(os.path.join(SRC_DIR, f"{name}.fbx")):
            sys.exit(f"ERROR: missing textured clip {name}.fbx in {SRC_DIR} (run reapply_texture.py)")

    clip_guids = {name: guid(f"barbarian/Animations/{name}.fbx") for name, *_ in CLIPS}
    idle_guid = clip_guids[AVATAR_SOURCE]
    ctrl_guid = guid("barbarian/Animations/Barbarian.controller")
    folder_guid = guid("barbarian/Animations/folder")

    actions_done = []
    if not args.dry_run:
        os.makedirs(dest, exist_ok=True)
        # folder .meta (so Unity tracks the new folder deterministically)
        with open(dest + ".meta", "w", newline="\n") as f:
            f.write(folder_meta(folder_guid))
        for name, *_ in CLIPS:
            shutil.copy2(os.path.join(SRC_DIR, f"{name}.fbx"), os.path.join(dest, f"{name}.fbx"))
            with open(os.path.join(dest, f"{name}.fbx.meta"), "w", newline="\n") as f:
                f.write(fbx_meta(name, clip_guids[name]))
            actions_done.append(f"{name}.fbx + .meta")
        with open(os.path.join(dest, "Barbarian.controller"), "w", newline="\n") as f:
            f.write(build_controller(clip_guids))
        with open(os.path.join(dest, "Barbarian.controller.meta"), "w", newline="\n") as f:
            f.write(controller_meta(ctrl_guid))
        actions_done.append("Barbarian.controller + .meta")

    # --- manifest (clip -> file -> duration -> loop -> root_motion -> avatar) ---
    manifest = {
        "character": "barbarian",
        "generated_by": "scripts/package_for_unity.py",
        "unity_project": os.path.relpath(unity_root, PIPE).replace("\\", "/"),
        "unity_dest": "Assets/Animations/Barbarian",
        "source_policy": ("Commercial Rokoko/Mixamo library retargets (batch_retarget.py) — "
                          "SHIPPABLE. MDM (generate_motion.py) output is previz only and is "
                          "never shipped."),
        "import": {
            "animation_type": "Humanoid",
            "fps": FPS,
            "scale_note": ("UniRig rigs export at ~0.01 scale; these clips were exported from "
                           "Blender in meters (useFileScale: 1, useFileUnits: 1). If the "
                           "character imports tiny, set the FBX 'Scale Factor' to ~100 per the "
                           "retarget_mocap export note. GS4 confirms in-engine size."),
        },
        "avatar": {
            "name": "BarbarianAvatar",
            "source_clip": f"{AVATAR_SOURCE}.fbx",
            "definition": ("CreateFromThisModel on EVERY clip — each FBX self-creates a valid "
                           "Humanoid avatar (like stock Mixamo FBX). Unity Humanoid clips are "
                           "muscle-space normalized, so any clip plays on the character's avatar "
                           "regardless of which avatar instance it imported with. idle's avatar "
                           "is the canonical character avatar."),
            "fix_note": ("GS6: switched the 8 non-idle clips from CopyFromOther to "
                         "CreateFromThisModel. CopyFromOther failed in the live editor with "
                         "'Copied Avatar Rig Configuration mis-match: Transform Armature not "
                         "found in HumanDescription' — the retarget FBX has an extra 'Armature' "
                         "transform above 'hips' that a copied (empty-skeleton) HumanDescription "
                         "can't account for. CreateFromThisModel avoids the copy entirely."),
            "character_avatar_ref": {"fileID": UNITY_AVATAR_FILEID, "guid": idle_guid, "type": 3},
            "bone_map": BONE_MAP,
            "required_human_bones_mapped": True,
            "unmapped_bones": UNMAPPED_BONES,
            "unmapped_note": ("Filler/connector bones with no Mecanim slot: extra spine "
                              "(bone_3/4), arm twist/filler (bone_9/11/13/16/18), pelvis "
                              "connectors (hip_connector.l/r). All 15 REQUIRED human bones map."),
        },
        "animator_controller": {
            "file": "Barbarian.controller",
            "guid": ctrl_guid,
            "default_state": "Idle",
            "parameters": {"Speed": "float", **{c[0].capitalize(): "trigger" for c in TRIGGER_CLIPS}},
            "transitions": [
                "Idle -> Walk (Speed > 0.1)", "Walk -> Idle (Speed < 0.1)",
                "Walk -> Run (Speed > 0.6)", "Run -> Walk (Speed < 0.6)",
                "AnyState -> {Attack,Hit,Dodge,Block,Wave,Celebrate} (trigger)",
                "each action/emote -> Idle (exit time)",
            ],
            "motion_binding": (f"each state's m_Motion = fileID {UNITY_CLIP_FILEID} (FBX primary "
                               "AnimationClip) + the clip's guid"),
        },
        "loop_note": ("loop flags below are the spec; Loop Time is enabled on the imported "
                      "idle/walk/run clips by the GS4 editor validator (needs the imported "
                      "clip's internal name, only known after Unity imports)."),
        "clips": [
            {
                "clip": name,
                "file": f"{name}.fbx",
                "guid": clip_guids[name],
                "duration_s": round(frames / FPS, 4),
                "frames": frames,
                "fps": FPS,
                "loop": loop,
                "root_motion": root,
                "animator_state": state,
                "category": cat,
                "avatar": ("BarbarianAvatar (CreateFromThisModel, canonical character avatar)"
                           if name == AVATAR_SOURCE else "BarbarianAvatar (CreateFromThisModel)"),
            }
            for name, loop, root, state, cat, frames in CLIPS
        ],
    }
    os.makedirs(os.path.dirname(MANIFEST_TRACKED), exist_ok=True)
    if not args.dry_run:
        with open(MANIFEST_TRACKED, "w", newline="\n") as f:
            json.dump(manifest, f, indent=2)
        # also drop a copy alongside the Unity assets for in-project discoverability
        with open(os.path.join(dest, "ANIMATION-MANIFEST.json"), "w", newline="\n") as f:
            json.dump(manifest, f, indent=2)

    print(f"{'DRY-RUN ' if args.dry_run else ''}PACKAGED {len(CLIPS)} clips -> {dest}")
    for a in actions_done:
        print(f"  + {a}")
    print(f"  manifest -> {MANIFEST_TRACKED}")
    print(f"  avatar: every clip CreateFromThisModel; {AVATAR_SOURCE}.fbx = canonical avatar")
    print(f"  unmapped bones: {', '.join(UNMAPPED_BONES)}")


if __name__ == "__main__":
    main()
