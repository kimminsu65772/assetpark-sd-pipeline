// OnsenPlay.cs — Play 모드에서 동작을 실제로 재생하며(Animator + Playables, 게임 시간 24fps) 세 방향을 PNG로 찍는다.
// 교복 사무라이 GamaujiTest/Assets/Scripts/PlayCapture.cs 를 간단히 줄여 고친 것. 씬 준비는 Assets/Editor/OnsenPlayRun.cs.
// 동작마다 한 바퀴를 먼저 재생하고(흔들림이 자리 잡도록, 저장 안 함) 두 번째 바퀴를 찍는다.
// view = "upper"면 카메라가 가슴 뼈(Spine02)의 이동을 따라간다(앉는 동작에서도 상체가 화면 안에).
// 결과: <프로젝트>/_captures/<이름>/<작업>/q_0000.png(쿼터뷰 위 35°), f_0000.png(정면 위 10°), u_0000.png(앞 아래 25°에서 올려다봄), zs_(아랫도리 확대, 옆 비스듬히), zu_(아랫도리 확대, 아래 30°)
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEngine;
using UnityEngine.Animations;
using UnityEngine.Playables;

public class OnsenPlay : MonoBehaviour
{
    public GameObject characterPrefab; public AnimationClip[] clips; public string runName = "run"; public bool spring; public string vrm = ""; public string sleeve = ""; public string view = ""; public string[] hide = new string[0];   // hide: 숨길 메시 이름(머리가 가릴 때)   // view = "upper": 상체(겨드랑이) 확대 묶음
    public string[] jobClips = { "UAL_Walk_Loop", "UAL_Sprint_Loop", "UAL_Crouch_Idle_Loop", "UAL_Sword_Attack" };
    public int res = 400;
    GameObject ch; Animator anim; PlayableGraph graph; AnimationPlayableOutput output; AnimationClipPlayable cp;
    Camera[] cams; RenderTexture rt; Texture2D tex; string outRoot; StringBuilder log = new StringBuilder();
    int job = -1, frame, count, pass; bool pending; string pendingDir; int pendingIdx;
    static string[] Tag = { "q", "f", "u", "zs", "zu" };

    void Start()
    {
        try
        {
            Time.captureFramerate = 24; QualitySettings.skinWeights = SkinWeights.FourBones;
            outRoot = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "_captures", runName)); Directory.CreateDirectory(outRoot);
            var lightGo = new GameObject("Sun"); var light = lightGo.AddComponent<Light>(); light.type = LightType.Directional; light.intensity = 1.1f; light.shadows = LightShadows.Soft; light.shadowStrength = 0.5f;
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat; RenderSettings.ambientLight = new Color(0.6f, 0.6f, 0.6f);
            ch = Instantiate(characterPrefab); ch.transform.position = Vector3.zero;
            var rends = ch.GetComponentsInChildren<Renderer>(true);
            foreach (var r in ch.GetComponentsInChildren<SkinnedMeshRenderer>(true)) r.updateWhenOffscreen = true;
            float minY = rends.Min(r => r.bounds.min.y), height = rends.Max(r => r.bounds.max.y) - minY;
            ch.transform.position = new Vector3(0, -minY, 0);   // 발바닥을 바닥(y = 0)에
            foreach (var r in rends) if (System.Array.IndexOf(hide, r.gameObject.name) >= 0) r.enabled = false;   // 숨기기(높이는 숨기기 전에 잼)
            var tr = ch.GetComponentsInChildren<Transform>(true).GroupBy(t => t.name).ToDictionary(g => g.Key, g => g.First());
            Vector3 face = BoneFind.Need(ch, tr, "L_ToeBase").position - BoneFind.Need(ch, tr, "L_Foot").position;   // 뼈는 이름 먼저, 없으면 Humanoid 대응(BoneFind.cs) face.y = 0; face.Normalize();
            lightGo.transform.rotation = Quaternion.LookRotation(Quaternion.AngleAxis(-30f, Vector3.up) * -face + Vector3.down * 1.2f, Vector3.up);
            if (spring) ch.AddComponent<SkirtSpring>();
            if (vrm != "") { var vs = ch.AddComponent<VrmSkirt>(); vs.prm = vrm; }
            if (sleeve != "") { var vsl = ch.AddComponent<VrmSleeve>(); vsl.prm = sleeve; }   // 소매 사슬 흔들림(겨드랑이 후보 C)
            anim = ch.GetComponent<Animator>(); if (!anim) anim = ch.AddComponent<Animator>(); anim.applyRootMotion = false; anim.cullingMode = AnimatorCullingMode.AlwaysAnimate;
                        height = 0.9f; light.shadows = LightShadows.None;   // 모든 실행에서 같은 화면(바닥 없음)
            Vector3 target = new Vector3(0, height * 0.40f, 0); float fov = 30f, dist = height * 0.78f / Mathf.Tan(fov * 0.5f * Mathf.Deg2Rad);
            float[][] views = { new[] { -40f, 35f, 1f }, new[] { 0f, 10f, 1f }, new[] { 0f, -25f, 1f }, new[] { -50f, 5f, 0.42f }, new[] { 30f, -30f, 0.42f } };   // 넷째·다섯째: 아랫도리 확대(옆 비스듬히, 아래에서)
            if (view == "upper")   // 상체 확대: 왼옆·오른옆·앞 비스듬히 아래·뒤 비스듬히 아래·쿼터뷰 위 (가슴 높이, 화면 폭 = 키의 0.36배)
            {
                views = new[] { new[] { -90f, 0f, 0.36f, 0.52f }, new[] { 90f, 0f, 0.36f, 0.52f }, new[] { -30f, -20f, 0.36f, 0.50f }, new[] { 150f, -20f, 0.36f, 0.50f }, new[] { -45f, 25f, 0.36f, 0.55f } };
                Tag = new[] { "al", "ar", "afu", "abu", "aq" };
            }
            cams = views.Select(v =>
            {
                var c = new GameObject("Cam").AddComponent<Camera>(); c.enabled = false; c.clearFlags = CameraClearFlags.SolidColor; c.backgroundColor = new Color(0.5f, 0.5f, 0.55f); c.fieldOfView = fov; c.nearClipPlane = 0.05f;
                Vector3 d = Quaternion.AngleAxis(v[0], Vector3.up) * face; Vector3 dir = d * Mathf.Cos(v[1] * Mathf.Deg2Rad) + Vector3.up * Mathf.Sin(v[1] * Mathf.Deg2Rad);
                Vector3 tg = v.Length > 3 ? new Vector3(0, height * v[3], 0) : v[2] < 1f ? new Vector3(0, height * 0.2f, 0) : target; c.transform.position = tg + dir * dist * v[2]; c.transform.rotation = Quaternion.LookRotation(-dir, Vector3.up); return c;
            }).ToArray();
            rt = new RenderTexture(res, res, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { antiAliasing = 4 }; rt.Create(); tex = new Texture2D(res, res, TextureFormat.RGB24, false);
            foreach (var c in cams) c.targetTexture = rt;
            graph = PlayableGraph.Create("OnsenPlay"); graph.SetTimeUpdateMode(DirectorUpdateMode.GameTime); output = AnimationPlayableOutput.Create(graph, "Anim", anim);
            Log("start run=" + runName + " spring=" + spring + " vrm=" + vrm + " sleeve=" + sleeve + " view=" + view + " hide=" + string.Join("/", hide) + " height=" + height.ToString("F3") + " avatar=" + (anim.avatar ? anim.avatar.isHuman.ToString() : "null") + " clips=" + string.Join(";", clips.Select(c => c.name)));
            Next(); graph.Play();
        }
        catch (System.Exception e) { Fail(e); }
    }
    AnimationClip Find(string k) { return clips.FirstOrDefault(c => c.name.EndsWith("|" + k)) ?? clips.First(c => c.name.Contains(k)); }
    void Next()
    {
        job++; if (job >= jobClips.Length) { Finish(); return; }
        var clip = Find(jobClips[job]); var old = cp; cp = AnimationClipPlayable.Create(graph, clip); cp.SetApplyFootIK(false); cp.SetTime(0); output.SetSourcePlayable(cp); if (old.IsValid()) old.Destroy();
        count = Mathf.RoundToInt(clip.length * 24f); frame = 0; pass = 0;
        pendingDir = Path.Combine(outRoot, jobClips[job]); if (Directory.Exists(pendingDir)) Directory.Delete(pendingDir, true); Directory.CreateDirectory(pendingDir);
        Log("job " + jobClips[job] + " frames=" + count + " loop=" + clip.isLooping);
    }
    void Update()
    {
        try
        {
            if (pending) { pending = false; if (chest != null) { Vector3 dv = chest.position - chest0; for (int i = 0; i < cams.Length; i++) cams[i].transform.position = camPos0[i] + dv; }   // 상체 확대: 카메라가 가슴 뼈를 따라감
                for (int i = 0; i < cams.Length; i++) { cams[i].Render(); RenderTexture.active = rt; tex.ReadPixels(new Rect(0, 0, res, res), 0, 0); tex.Apply(); RenderTexture.active = null; File.WriteAllBytes(Path.Combine(pendingDir, Tag[i] + "_" + pendingIdx.ToString("D4") + ".png"), tex.EncodeToPNG()); } }
            if (job >= jobClips.Length) return;
            frame++;
            if (frame >= count) { frame = 0; pass++; cp.SetTime(0); if (pass >= 2) { Next(); } }
        }
        catch (System.Exception e) { Fail(e); }
    }
    bool grounded; Transform fl, fr2, chest; Vector3 chest0; Vector3[] camPos0;
    void LateUpdate()
    {
        if (!grounded)   // 첫 재생 프레임에서 발 뼈 높이를 재어 캐릭터를 내린다(발목 뼈 높이 0.035를 바닥 위로)
        {
            if (fl == null) { var tr = BoneFind.All(ch); fl = BoneFind.Need(ch, tr, "L_Foot"); fr2 = BoneFind.Need(ch, tr, "R_Foot"); }
            float y = Mathf.Min(fl.position.y, fr2.position.y) - 0.035f; ch.transform.position -= new Vector3(0, y, 0); grounded = true; Log("grounded shift=" + y.ToString("F3"));
            if (view == "upper") { chest = BoneFind.Need(ch, BoneFind.All(ch), "Spine02"); chest0 = chest.position; camPos0 = cams.Select(c => c.transform.position).ToArray(); Log("upper cams follow Spine02 from " + chest0.ToString("F3")); }
        }
        if (job < jobClips.Length && job >= 0 && pass == 1) { pending = true; pendingIdx = frame; }
    }
    void Finish() { Log("ONSEN_PLAY_DONE"); File.WriteAllText(Path.Combine(outRoot, "play_log.txt"), log.ToString()); if (graph.IsValid()) graph.Destroy();
#if UNITY_EDITOR
        UnityEditor.EditorApplication.Exit(0);
#endif
    }
    void Fail(System.Exception e) { Debug.LogError("ONSEN_FAIL " + e); try { File.WriteAllText(Path.Combine(outRoot ?? ".", "play_log.txt"), log + "\nFAIL " + e); } catch { }
#if UNITY_EDITOR
        UnityEditor.EditorApplication.Exit(1);
#endif
    }
    void Log(string s) { log.AppendLine(s); Debug.Log("ONSEN_PLAY " + s); }
}
