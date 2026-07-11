using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.Formats.Fbx.Exporter;
using UnityEngine;

// Bake the Creature Pack swipe (attack) + dying (death) onto each humanoid
// bestiary biped (Humanoid retarget). Exports <biped>_swipe.fbx / _die.fbx.
public class BakeCreatures
{
    const string SrcDir = "Assets/Animations/revenant_knight/Compare";
    const float FPS = 30f;

    static readonly string[] Bipeds = {
        "bone_golem", "cultist", "ghoul", "imp", "necromancer",
        "plague_zombie", "skeleton_warrior",
    };
    // (source clip file in SrcDir, exported clip name)
    static readonly (string src, string name)[] Clips = {
        ("cr_swipe", "swipe"), ("cr_die", "die"),
    };

    public static string Execute()
    {
        var sb = new StringBuilder();
        try
        {
            var srcClips = new Dictionary<string, AnimationClip>();
            foreach (var c in Clips)
            {
                string p = $"{SrcDir}/{c.src}.fbx";
                EnsureHumanoid(p, sb);
                var clip = LongestClip(p);
                if (clip == null) { sb.AppendLine($"{c.src}: NO CLIP"); continue; }
                srcClips[c.name] = clip;
            }
            foreach (var biped in Bipeds)
            {
                string charPath = $"Assets/Animations/{biped}/Source/{biped}_accurig.fbx";
                string exportDir = $"Assets/Animations/{biped}/export";
                Directory.CreateDirectory(exportDir);
                foreach (var c in Clips)
                {
                    if (!srcClips.ContainsKey(c.name)) continue;
                    try { sb.AppendLine(BakeAndExport(charPath, exportDir, biped, srcClips[c.name], c.name)); }
                    catch (System.Exception ex) { sb.AppendLine($"{biped}_{c.name}: FAIL {ex.GetType().Name}: {ex.Message.Split('\n')[0]}"); }
                }
            }
            AssetDatabase.Refresh();
            return sb + "\nOK";
        }
        catch (System.Exception e) { return sb + "\nEXCEPTION: " + e; }
    }

    static void EnsureHumanoid(string path, StringBuilder sb)
    {
        var imp = AssetImporter.GetAtPath(path) as ModelImporter;
        if (imp == null) { sb.AppendLine($"WARN no importer {path}"); return; }
        if (imp.animationType != ModelImporterAnimationType.Human)
        {
            imp.animationType = ModelImporterAnimationType.Human;
            imp.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
            imp.SaveAndReimport();
        }
    }

    static AnimationClip LongestClip(string path)
    {
        return AssetDatabase.LoadAllAssetsAtPath(path).OfType<AnimationClip>()
            .Where(c => !c.name.StartsWith("__preview__"))
            .OrderByDescending(c => c.length).FirstOrDefault();
    }

    static string BakeAndExport(string charPath, string exportDir, string charName, AnimationClip src, string clipName)
    {
        var charAsset = AssetDatabase.LoadAssetAtPath<GameObject>(charPath);
        if (charAsset == null) return $"FAIL {charName}: char missing {charPath}";
        var go = Object.Instantiate(charAsset);
        go.name = charName;
        try
        {
            var animator = go.GetComponent<Animator>();
            if (animator == null) animator = go.AddComponent<Animator>();
            if (animator.avatar == null || !animator.avatar.isHuman) return $"FAIL {charName}: not humanoid";
            var hips = animator.GetBoneTransform(HumanBodyBones.Hips);
            var bones = go.GetComponentsInChildren<Transform>().Where(t => t != go.transform).ToArray();

            int frames = Mathf.Max(2, Mathf.CeilToInt(src.length * FPS) + 1);
            var rot = new Dictionary<Transform, List<Quaternion>>();
            foreach (var b in bones) rot[b] = new List<Quaternion>();
            var hp = new List<Vector3>();
            AnimationMode.StartAnimationMode();
            try
            {
                AnimationMode.BeginSampling();
                for (int f = 0; f < frames; f++)
                {
                    AnimationMode.SampleAnimationClip(go, src, Mathf.Min(f / FPS, src.length));
                    foreach (var b in bones) rot[b].Add(b.localRotation);
                    hp.Add(hips.localPosition);
                }
                AnimationMode.EndSampling();
            }
            finally { AnimationMode.StopAnimationMode(); }

            Vector3 drift = hp[hp.Count - 1] - hp[0];
            for (int f = 0; f < hp.Count; f++)
            {
                float k = f / (float)(hp.Count - 1);
                hp[f] = new Vector3(hp[f].x - drift.x * k, hp[f].y, hp[f].z - drift.z * k);
            }

            var baked = new AnimationClip { name = clipName, legacy = true, frameRate = FPS };
            foreach (var b in bones)
            {
                string p = AnimationUtility.CalculateTransformPath(b, go.transform);
                var keys = rot[b];
                var kx = new Keyframe[keys.Count]; var ky = new Keyframe[keys.Count];
                var kz = new Keyframe[keys.Count]; var kw = new Keyframe[keys.Count];
                for (int f = 0; f < keys.Count; f++)
                {
                    float t = f / FPS; var q = keys[f];
                    kx[f] = new Keyframe(t, q.x); ky[f] = new Keyframe(t, q.y);
                    kz[f] = new Keyframe(t, q.z); kw[f] = new Keyframe(t, q.w);
                }
                baked.SetCurve(p, typeof(Transform), "localRotation.x", new AnimationCurve(kx));
                baked.SetCurve(p, typeof(Transform), "localRotation.y", new AnimationCurve(ky));
                baked.SetCurve(p, typeof(Transform), "localRotation.z", new AnimationCurve(kz));
                baked.SetCurve(p, typeof(Transform), "localRotation.w", new AnimationCurve(kw));
            }
            {
                string p = AnimationUtility.CalculateTransformPath(hips, go.transform);
                var px = new Keyframe[hp.Count]; var py = new Keyframe[hp.Count]; var pz = new Keyframe[hp.Count];
                for (int f = 0; f < hp.Count; f++)
                {
                    float t = f / FPS;
                    px[f] = new Keyframe(t, hp[f].x); py[f] = new Keyframe(t, hp[f].y); pz[f] = new Keyframe(t, hp[f].z);
                }
                baked.SetCurve(p, typeof(Transform), "localPosition.x", new AnimationCurve(px));
                baked.SetCurve(p, typeof(Transform), "localPosition.y", new AnimationCurve(py));
                baked.SetCurve(p, typeof(Transform), "localPosition.z", new AnimationCurve(pz));
            }

            var animComp = go.GetComponent<Animation>();
            if (animComp == null) animComp = go.AddComponent<Animation>();
            animComp.AddClip(baked, clipName);
            animComp.clip = baked;

            string outPath = $"{exportDir}/{charName}_{clipName}.fbx";
            var opts = new ExportModelOptions { ExportFormat = ExportFormat.Binary, ModelAnimIncludeOption = Include.ModelAndAnim, AnimateSkinnedMesh = true };
            ModelExporter.ExportObjects(Path.GetFullPath(outPath), new Object[] { go }, opts);
            return $"{charName}_{clipName}: {src.length:F2}s -> {outPath}";
        }
        finally { Object.DestroyImmediate(go); }
    }
}
