// SkirtSpring.cs — 자락(치마) 사슬 뼈를 스프링처럼 흔들고 다리 원기둥(캡슐)을 피하게 하는 무료 직접 구현(후보 D).
// 사슬: 이름이 "Skirt_<단>_<줄>"인 뼈. 단 번호가 클수록 위. 줄마다 위 단에서 아래 단으로 이어진 사슬이다(SSOT/도구/리깅/자락리깅.py 사슬 방식).
// 다리 캡슐: 허벅지 뼈 머리→종아리 뼈 머리, 종아리 뼈 머리→발 뼈 머리. Animator가 자세를 정한 뒤(LateUpdate) 계산한다.
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

[DefaultExecutionOrder(1000)]
public class SkirtSpring : MonoBehaviour
{
    public string thighL = "L_Thigh", calfL = "L_Calf", footL = "L_Foot", thighR = "R_Thigh", calfR = "R_Calf", footR = "R_Foot";
    public float stiffness = 0.6f;     // 원래 방향으로 돌아가려는 힘(초당)
    public float drag = 0.35f;         // 0~1, 클수록 출렁임이 빨리 죽음
    public Vector3 gravity = new Vector3(0, -0.3f, 0);
    public float thighRadius = 0.045f, calfRadius = 0.032f, nodeRadius = 0.008f;
    public int iterations = 2;

    class Node { public Transform t; public Quaternion initLocal; public Vector3 tailLocal; public float len; public Vector3 cur, prev; }
    readonly List<List<Node>> chains = new List<List<Node>>();
    Transform tL, cL, fL, tR, cR, fR; bool started;

    void Start()
    {
        var all = GetComponentsInChildren<Transform>(true);
        var tr = all.GroupBy(t => t.name).ToDictionary(g => g.Key, g => g.First());
        var go = gameObject;   // 뼈는 이름 먼저, 없으면 Humanoid 대응(BoneFind.cs)
        tL = BoneFind.Need(go, tr, thighL); cL = BoneFind.Need(go, tr, calfL); fL = BoneFind.Need(go, tr, footL); tR = BoneFind.Need(go, tr, thighR); cR = BoneFind.Need(go, tr, calfR); fR = BoneFind.Need(go, tr, footR);
        var sk = all.Where(t => t.name.StartsWith("Skirt_")).ToList();
        foreach (var top in sk.Where(t => !t.parent.name.StartsWith("Skirt_")))
        {
            var chain = new List<Node>(); var t = top;
            while (t != null)
            {
                var child = t.Cast<Transform>().FirstOrDefault(c => c.name.StartsWith("Skirt_"));
                var n = new Node { t = t, initLocal = t.localRotation };
                if (child != null) n.tailLocal = child.localPosition;
                else { var up = t.parent.name.StartsWith("Skirt_") ? t.localPosition : Vector3.down * 0.02f; n.tailLocal = up.normalized * 0.02f; }
                n.len = n.tailLocal.magnitude; chain.Add(n); t = child;
            }
            chains.Add(chain);
        }
        Debug.Log("SKIRT_SPRING chains=" + chains.Count + " nodes=" + chains.Sum(c => c.Count));
    }

    static Vector3 Closest(Vector3 p, Vector3 a, Vector3 b) { var ab = b - a; float t = Mathf.Clamp01(Vector3.Dot(p - a, ab) / Mathf.Max(1e-8f, ab.sqrMagnitude)); return a + ab * t; }
    Vector3 Collide(Vector3 p)
    {
        foreach (var cap in new[] { (tL.position, cL.position, thighRadius), (cL.position, fL.position, calfRadius), (tR.position, cR.position, thighRadius), (cR.position, fR.position, calfRadius) })
        {
            var q = Closest(p, cap.Item1, cap.Item2); var d = p - q; float r = cap.Item3 + nodeRadius;
            if (d.sqrMagnitude < r * r) p = q + (d.sqrMagnitude > 1e-12f ? d.normalized : Vector3.forward) * r;
        }
        return p;
    }

    void LateUpdate()
    {
        float dt = Mathf.Max(1e-4f, Time.deltaTime);
        foreach (var chain in chains)
        {
            foreach (var n in chain) n.t.localRotation = n.initLocal;   // 애니메이션이 정한 기본 방향에서 시작
            for (int i = 0; i < chain.Count; i++)
            {
                var n = chain[i]; Vector3 head = n.t.position;
                Vector3 restTail = n.t.TransformPoint(n.tailLocal);
                if (!started) { n.cur = n.prev = restTail; }
                Vector3 inertia = (n.cur - n.prev) * (1f - drag);
                Vector3 next = n.cur + inertia + (restTail - n.cur) * Mathf.Clamp01(stiffness * dt * 10f) + gravity * dt * dt;
                float worldLen = (restTail - head).magnitude;
                for (int k = 0; k < iterations; k++) { next = head + (next - head).normalized * worldLen; next = Collide(next); }
                next = head + (next - head).normalized * worldLen;
                n.prev = n.cur; n.cur = next;
                n.t.rotation = Quaternion.FromToRotation(restTail - head, next - head) * n.t.rotation;
            }
        }
        started = true;
    }
}
