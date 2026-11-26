// Assets/Character/ 의 FBX마다 Humanoid로 설정하고(뼈 대응은 같은 이름의 .humanoid.txt), 텍스처를 꺼내고, 클립마다 전체 뼈 마스크를 지정한다.
// 교복 사무라이 GamaujiTest/Assets/Editor/GamaujiCheck.cs 의 Setup을 캐릭터 설정 파일로 뼈 이름을 받게 고친 것.
// 실행: Unity.exe -batchmode -projectPath <프로젝트> -executeMethod OnsenSetup.Run [-onsenOnly 이름,이름(FBX 파일 이름, 확장자 없이)] -logFile <로그>   (-onsenOnly가 없으면 모든 FBX)
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class OnsenSetup
{
    public static void Run()
    {
        bool ok = true;
        try
        {
            var argv = System.Environment.GetCommandLineArgs(); int oi = System.Array.IndexOf(argv, "-onsenOnly");
            var only = oi >= 0 && oi + 1 < argv.Length ? new HashSet<string>(argv[oi + 1].Split(',')) : null;   // 고른 FBX만 다시 설정
            foreach (var fbx in Directory.GetFiles("Assets/Character", "*.fbx").Select(p => p.Replace('\\', '/')).Where(p => only == null || only.Contains(Path.GetFileNameWithoutExtension(p))))
            {
                var map = File.ReadAllLines(Path.ChangeExtension(fbx, null) + ".humanoid.txt").Where(l => l.Contains("=")).ToDictionary(l => l.Split('=')[0], l => l.Split('=')[1]);
                var imp = (ModelImporter)AssetImporter.GetAtPath(fbx);
                string texDir = "Assets/Character/Textures_" + Path.GetFileNameWithoutExtension(fbx);
                Directory.CreateDirectory(texDir); bool tex = imp.ExtractTextures(texDir); AssetDatabase.Refresh();
                imp = (ModelImporter)AssetImporter.GetAtPath(fbx);
                var model = AssetDatabase.LoadAssetAtPath<GameObject>(fbx);
                var names = new HashSet<string>(model.GetComponentsInChildren<Transform>(true).Select(t => t.name));
                var human = new List<HumanBone>(); var missing = new List<string>();
                foreach (var h in HumanTrait.BoneName)
                {
                    if (map.TryGetValue(h, out var n) && names.Contains(n)) { var hb = new HumanBone { boneName = n, humanName = h }; hb.limit.useDefaultValues = true; human.Add(hb); }
                    else missing.Add(h);
                }
                imp.animationType = ModelImporterAnimationType.Human; imp.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
                var hd = imp.humanDescription; hd.human = human.ToArray(); imp.humanDescription = hd;
                imp.optimizeGameObjects = false; imp.animationCompression = ModelImporterAnimationCompression.Off; imp.importAnimation = true;
                var mask = new AvatarMask(); mask.AddTransformPath(model.transform, true);
                for (int i = 0; i < mask.transformCount; i++) mask.SetTransformActive(i, true);
                for (int i = 0; i < (int)AvatarMaskBodyPart.LastBodyPart; i++) mask.SetHumanoidBodyPartActive((AvatarMaskBodyPart)i, true);
                var clips = imp.defaultClipAnimations;
                foreach (var c in clips)
                {
                    c.loopTime = c.name.Contains("Loop");
                    c.lockRootRotation = true; c.keepOriginalOrientation = true; c.lockRootHeightY = true; c.keepOriginalPositionY = true; c.lockRootPositionXZ = true; c.keepOriginalPositionXZ = true;
                    c.maskType = ClipAnimationMaskType.CreateFromThisModel; c.ConfigureClipFromMask(mask);
                }
                imp.clipAnimations = clips; imp.SaveAndReimport();
                var avatar = AssetDatabase.LoadAllAssetsAtPath(fbx).OfType<Avatar>().FirstOrDefault();
                var cl = AssetDatabase.LoadAllAssetsAtPath(fbx).OfType<AnimationClip>().Where(c => !c.name.StartsWith("__preview__")).ToList();
                bool good = avatar != null && avatar.isValid && avatar.isHuman; ok &= good;
                Debug.Log("ONSEN_SETUP " + fbx + " textures=" + tex + " mapped=" + human.Count + " avatar=" + (avatar ? avatar.isValid + "/" + avatar.isHuman : "null") + " transforms=" + names.Count
                          + " skirtBones=" + names.Count(n => n.StartsWith("Skirt_")) + " skirtCurves=" + string.Join("/", cl.Select(c => AnimationUtility.GetCurveBindings(c).Count(b => b.path.Contains("Skirt_")).ToString()))
                          + " clips=" + string.Join(";", cl.Select(c => c.name + ":" + c.length.ToString("F3") + "s")) + " missingRequired=[" + string.Join(",", missing.Where(m => HumanTrait.RequiredBone(System.Array.IndexOf(HumanTrait.BoneName, m)))) + "]");
            }
            AssetDatabase.SaveAssets();
        }
        catch (System.Exception e) { Debug.LogError("ONSEN_FAIL " + e); ok = false; }
        EditorApplication.Exit(ok ? 0 : 1);
    }
}
