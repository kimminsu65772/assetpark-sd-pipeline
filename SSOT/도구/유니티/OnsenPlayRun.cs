// 캡처용 씬을 만들고 Play 모드로 들어간다. 찍기와 종료는 Assets/Scripts/OnsenPlay.cs.
// 실행(-quit 없이): Unity.exe -batchmode -projectPath <프로젝트> -executeMethod OnsenPlayRun.Run -onsenFbx <Assets/Character/이름.fbx> -onsenName <이름> [-onsenSpring 1] [-onsenVrm "stiff,gravity,drag,hitRadius,thighR,calfR,pelvisR,n"] [-onsenSleeve "stiff,gravity,drag,hitRadius,bodyR,offX,thighR,n"] [-onsenJobs 동작,동작(Action 끝 이름)] [-onsenView upper] [-onsenHide 메시,메시] -logFile <로그>
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class OnsenPlayRun
{
    static string Arg(string k, string d) { var a = System.Environment.GetCommandLineArgs(); int i = System.Array.IndexOf(a, k); return i >= 0 && i + 1 < a.Length ? a[i + 1] : d; }
    public static void Run()
    {
        try
        {
            string fbx = Arg("-onsenFbx", ""); var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var p = new GameObject("OnsenPlay").AddComponent<OnsenPlay>();
            p.characterPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(fbx);
            p.clips = AssetDatabase.LoadAllAssetsAtPath(fbx).OfType<AnimationClip>().Where(c => !c.name.StartsWith("__preview__")).ToArray();
            p.runName = Arg("-onsenName", "run"); p.spring = Arg("-onsenSpring", "0") == "1"; p.vrm = Arg("-onsenVrm", ""); p.sleeve = Arg("-onsenSleeve", ""); var hide = Arg("-onsenHide", ""); if (hide != "") p.hide = hide.Split(',');
            p.view = Arg("-onsenView", ""); var jobs = Arg("-onsenJobs", ""); if (jobs != "") p.jobClips = jobs.Split(',');
            EditorSceneManager.SaveScene(scene, "Assets/Scenes/OnsenPlay.unity");
            EditorApplication.EnterPlaymode();
        }
        catch (System.Exception e) { Debug.LogError("ONSEN_FAIL " + e); EditorApplication.Exit(1); }
    }
}
