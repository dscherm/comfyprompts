using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.Formats.Fbx.Exporter;
using UnityEngine;

/// <summary>
/// Batch locomotion bake: walk clips for every AccuRIG bestiary biped, plus a
/// run clip for revenant_knight. Same recipe as bake_knight_locomotion.cs
/// (Humanoid retarget sample, rotation-only + hips position, XZ drift strip,
/// legacy named clip, binary FBX export for Godot ufbx).
/// </summary>
public class BakeBatchLocomotion
{
    const string WalkSrc = "Assets/Animations/revenant_knight/ActorCore/walk_relaxed_loop.fbx";
    const string RunSrc = "Assets/Animations/revenant_knight/ActorCore/run_forward.fbx";
    const float FPS = 30f;

    static readonly string[] WalkChars =
    {
        "bone_golem", "cultist", "ghoul", "imp", "lich_king",
        "necromancer", "plague_zombie", "skeleton_mage", "skeleton_warrior",
    };

    public static string Execute()
    {
        var sb = new StringBuilder();
        try
        {
            EnsureHumanoid(WalkSrc, sb);
            EnsureHumanoid(RunSrc, sb);
            var walkClip = LongestClip(WalkSrc);
            var runClip = LongestClip(RunSrc);
            if (walkClip == null) return sb + "\nFAIL: no walk clip";
            if (runClip == null) return sb + "\nFAIL: no run clip";
            sb.AppendLine($"walk src: {walkClip.name} {walkClip.length:F2}s human={walkClip.humanMotion}");
            sb.AppendLine($"run src: {runClip.name} {runClip.length:F2}s human={runClip.humanMotion}");

            foreach (var c in WalkChars)
            {
                string charPath = $"Assets/Animations/{c}/Source/{c}_accurig.fbx";
                string exportDir = $"Assets/Animations/{c}/export";
                sb.AppendLine(BakeAndExport(charPath, exportDir, c, walkClip, "walk"));
            }
            sb.AppendLine(BakeAndExport(
                "Assets/Animations/revenant_knight/Source/revenant_knight_accurig.fbx",
                "Assets/Animations/revenant_knight/export", "revenant_knight", runClip, "run"));
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
    }

    static AnimationClip LongestClip(string path)
    {
        return AssetDatabase.LoadAllAssetsAtPath(path)
            .OfType<AnimationClip>()
            .Where(c => !c.name.StartsWith("__preview__"))
            .OrderByDescending(c => c.length)
            .FirstOrDefault();
    }

    static string BakeAndExport(string charPath, string exportDir, string charName, AnimationClip src, string clipName)
    {
        var charAsset = AssetDatabase.LoadAssetAtPath<GameObject>(charPath);
        if (charAsset == null) return $"FAIL {charName}: char asset missing at {charPath}";
        var go = Object.Instantiate(charAsset);
        go.name = charName;
        try
        {
            var animator = go.GetComponent<Animator>();
            if (animator == null) animator = go.AddComponent<Animator>();
            if (animator.avatar == null || !animator.avatar.isHuman)
                return $"FAIL {charName}: avatar not humanoid";

            var hips = animator.GetBoneTransform(HumanBodyBones.Hips);
            var bones = go.GetComponentsInChildren<Transform>().Where(t => t != go.transform).ToArray();

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
                    AnimationMode.SampleAnimationClip(go, src, Mathf.Min(f / FPS, src.length));
                    foreach (var b in bones) rotKeys[b].Add(b.localRotation);
                    hipsPos.Add(hips.localPosition);
                }
                AnimationMode.EndSampling();
            }
            finally { AnimationMode.StopAnimationMode(); }

            Vector3 drift = hipsPos[hipsPos.Count - 1] - hipsPos[0];
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
                    float t = f / FPS; var q = keys[f];
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

            Directory.CreateDirectory(exportDir);
            string outPath = $"{exportDir}/{charName}_{clipName}.fbx";
            var options = new ExportModelOptions
            {
                ExportFormat = ExportFormat.Binary,
                ModelAnimIncludeOption = Include.ModelAndAnim,
                AnimateSkinnedMesh = true,
            };
            ModelExporter.ExportObjects(Path.GetFullPath(outPath), new Object[] { go }, options);
            return $"{charName}_{clipName}: exported {outPath}";
        }
        finally { Object.DestroyImmediate(go); }
    }
}
