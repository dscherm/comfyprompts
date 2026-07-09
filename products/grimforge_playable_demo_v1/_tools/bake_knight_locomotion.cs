using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.Formats.Fbx.Exporter;
using UnityEngine;

/// <summary>
/// Bakes idle + walk locomotion clips onto the AccuRIG revenant_knight rig and
/// exports each as a BINARY FBX for Godot's native ufbx importer.
/// Recipe per project_ccbase_retarget_scramble: Humanoid retarget via
/// AnimationMode.SampleAnimationClip, record per-bone localRotation + hips
/// localPosition only, clip .name MUST be set, ModelExporter binary export.
/// Walk source: ActorCore walk_relaxed_loop.fbx (CC_Base-native).
/// Idle source: shared Mixamo set (Humanoid retarget).
/// </summary>
public class BakeKnightLocomotion
{
    const string CharPath = "Assets/Animations/revenant_knight/Source/revenant_knight_accurig.fbx";
    const string IdleSrc = "Assets/Animations/Barbarian/Mixamo/idle.fbx";
    const string WalkSrc = "Assets/Animations/revenant_knight/ActorCore/walk_relaxed_loop.fbx";
    const string ExportDir = "Assets/Animations/revenant_knight/export";
    const float FPS = 30f;

    public static string Execute()
    {
        var sb = new StringBuilder();
        try
        {
            EnsureHumanoid(WalkSrc, sb);
            EnsureHumanoid(IdleSrc, sb);

            var idleClip = FirstClip(IdleSrc);
            var walkClip = FirstClip(WalkSrc);
            if (idleClip == null) return sb + "\nFAIL: no idle clip";
            if (walkClip == null) return sb + "\nFAIL: no walk clip";
            sb.AppendLine($"idle src clip: {idleClip.name} len={idleClip.length:F2}s humanMotion={idleClip.humanMotion}");
            sb.AppendLine($"walk src clip: {walkClip.name} len={walkClip.length:F2}s humanMotion={walkClip.humanMotion}");

            Directory.CreateDirectory(ExportDir);
            sb.AppendLine(BakeAndExport(idleClip, "idle"));
            sb.AppendLine(BakeAndExport(walkClip, "walk"));
            AssetDatabase.Refresh();
            return sb + "\nOK";
        }
        catch (System.Exception e)
        {
            return sb + "\nEXCEPTION: " + e;
        }
    }

    static void EnsureHumanoid(string path, StringBuilder sb)
    {
        var imp = AssetImporter.GetAtPath(path) as ModelImporter;
        if (imp == null) { sb.AppendLine($"WARN: no importer for {path}"); return; }
        if (imp.animationType != ModelImporterAnimationType.Human)
        {
            imp.animationType = ModelImporterAnimationType.Human;
            imp.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
            imp.SaveAndReimport();
            sb.AppendLine($"reimported {path} as Humanoid");
        }
        else sb.AppendLine($"{path} already Humanoid");
    }

    static AnimationClip FirstClip(string path)
    {
        // ActorCore FBXs ship a 0_T-Pose take ahead of the real animation —
        // take the longest non-preview clip.
        return AssetDatabase.LoadAllAssetsAtPath(path)
            .OfType<AnimationClip>()
            .Where(c => !c.name.StartsWith("__preview__"))
            .OrderByDescending(c => c.length)
            .FirstOrDefault();
    }

    static string BakeAndExport(AnimationClip src, string clipName)
    {
        var charAsset = AssetDatabase.LoadAssetAtPath<GameObject>(CharPath);
        if (charAsset == null) return "FAIL: char asset missing";
        var go = Object.Instantiate(charAsset);
        go.name = "revenant_knight";
        var log = new StringBuilder();
        try
        {
            var animator = go.GetComponent<Animator>();
            if (animator == null) animator = go.AddComponent<Animator>();
            if (animator.avatar == null || !animator.avatar.isHuman)
                return "FAIL: knight avatar not humanoid";

            var hips = animator.GetBoneTransform(HumanBodyBones.Hips);
            var bones = go.GetComponentsInChildren<Transform>()
                .Where(t => t != go.transform).ToArray();

            int frames = Mathf.Max(2, Mathf.CeilToInt(src.length * FPS) + 1);
            var rotKeys = new Dictionary<Transform, List<Quaternion>>();
            foreach (var b in bones) rotKeys[b] = new List<Quaternion>();
            var hipsPos = new List<Vector3>();

            AnimationMode.StartAnimationMode();
            try
            {
                AnimationMode.BeginSampling();
                for (int f = 0; f < frames; f++)
                {
                    float t = Mathf.Min(f / FPS, src.length);
                    AnimationMode.SampleAnimationClip(go, src, t);
                    foreach (var b in bones) rotKeys[b].Add(b.localRotation);
                    hipsPos.Add(hips.localPosition);
                }
                AnimationMode.EndSampling();
            }
            finally { AnimationMode.StopAnimationMode(); }

            // strip XZ root drift so the loop plays in place (gameplay moves the body)
            Vector3 drift = hipsPos[hipsPos.Count - 1] - hipsPos[0];
            log.AppendLine($"{clipName}: frames={frames} hipsDrift={drift}");
            for (int f = 0; f < hipsPos.Count; f++)
            {
                float k = f / (float)(hipsPos.Count - 1);
                hipsPos[f] = new Vector3(hipsPos[f].x - drift.x * k, hipsPos[f].y, hipsPos[f].z - drift.z * k);
            }

            var baked = new AnimationClip { name = clipName, legacy = true, frameRate = FPS };
            foreach (var b in bones)
            {
                string bonePath = AnimationUtility.CalculateTransformPath(b, go.transform);
                var keys = rotKeys[b];
                var kx = new Keyframe[keys.Count]; var ky = new Keyframe[keys.Count];
                var kz = new Keyframe[keys.Count]; var kw = new Keyframe[keys.Count];
                for (int f = 0; f < keys.Count; f++)
                {
                    float t = f / FPS;
                    var q = keys[f];
                    kx[f] = new Keyframe(t, q.x); ky[f] = new Keyframe(t, q.y);
                    kz[f] = new Keyframe(t, q.z); kw[f] = new Keyframe(t, q.w);
                }
                baked.SetCurve(bonePath, typeof(Transform), "localRotation.x", new AnimationCurve(kx));
                baked.SetCurve(bonePath, typeof(Transform), "localRotation.y", new AnimationCurve(ky));
                baked.SetCurve(bonePath, typeof(Transform), "localRotation.z", new AnimationCurve(kz));
                baked.SetCurve(bonePath, typeof(Transform), "localRotation.w", new AnimationCurve(kw));
            }
            {
                string hipsPath = AnimationUtility.CalculateTransformPath(hips, go.transform);
                var px = new Keyframe[hipsPos.Count]; var py = new Keyframe[hipsPos.Count]; var pz = new Keyframe[hipsPos.Count];
                for (int f = 0; f < hipsPos.Count; f++)
                {
                    float t = f / FPS;
                    px[f] = new Keyframe(t, hipsPos[f].x);
                    py[f] = new Keyframe(t, hipsPos[f].y);
                    pz[f] = new Keyframe(t, hipsPos[f].z);
                }
                baked.SetCurve(hipsPath, typeof(Transform), "localPosition.x", new AnimationCurve(px));
                baked.SetCurve(hipsPath, typeof(Transform), "localPosition.y", new AnimationCurve(py));
                baked.SetCurve(hipsPath, typeof(Transform), "localPosition.z", new AnimationCurve(pz));
            }

            var animComp = go.GetComponent<Animation>();
            if (animComp == null) animComp = go.AddComponent<Animation>();
            animComp.AddClip(baked, clipName);
            animComp.clip = baked;

            string outPath = $"{ExportDir}/revenant_knight_{clipName}.fbx";
            var options = new ExportModelOptions
            {
                ExportFormat = ExportFormat.Binary,
                ModelAnimIncludeOption = Include.ModelAndAnim,
                AnimateSkinnedMesh = true,
            };
            string result = ModelExporter.ExportObjects(Path.GetFullPath(outPath), new Object[] { go }, options);
            log.AppendLine($"{clipName}: exported -> {result}");
            return log.ToString();
        }
        finally
        {
            Object.DestroyImmediate(go);
        }
    }
}
