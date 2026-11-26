// VrmSkirt.cs — UniVRM(VRM 0.x)의 VRMSpringBone으로 자락 사슬 뼈를 흔들고, 다리에 공 모양 충돌체(VRMSpringBoneColliderGroup)를 단다(후보 D, UniVRM 판).
// 사슬: "Skirt_<단>_<줄>" 뼈 중 부모가 자락 뼈가 아닌 것(맨 위)을 RootBones로 넣는다(SSOT/도구/리깅/자락리깅.py 사슬 방식).
// 충돌체: 허벅지·종아리 뼈마다 뼈를 따라 공 n개(머리→자식 뼈 머리), 골반에 공 1개. 값은 문자열 "stiff,gravity,drag,hitRadius,thighR,calfR,pelvisR,n"으로 받는다.
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using VRM;

public class VrmSkirt : MonoBehaviour
{
    public string prm = "1.0,0.3,0.4,0.01,0.045,0.032,0.07,4";
    void Start()
    {
        var v = prm.Split(',').Select(s => float.Parse(s, System.Globalization.CultureInfo.InvariantCulture)).ToArray();
        var tr = GetComponentsInChildren<Transform>(true).GroupBy(t => t.name).ToDictionary(g => g.Key, g => g.First());
        var groups = new List<VRMSpringBoneColliderGroup>();
        void Along(string bone, string child, float r, int n)
        {
            var b = BoneFind.Need(gameObject, tr, bone); var c = BoneFind.Need(gameObject, tr, child); var g = b.gameObject.AddComponent<VRMSpringBoneColliderGroup>();
            Vector3 local = b.InverseTransformPoint(c.position);
            // 공 반지름은 월드 기준 값. 뼈의 lossyScale로 나눠 로컬 값으로 넣는다
            float s = Mathf.Max(1e-6f, b.lossyScale.x);
            g.Colliders = Enumerable.Range(0, n).Select(i => new VRMSpringBoneColliderGroup.SphereCollider { Offset = local * (i / (float)(n - 1)), Radius = r / s }).ToArray();
            groups.Add(g);
        }
        int n = Mathf.RoundToInt(v[7]);
        Along("L_Thigh", "L_Calf", v[4], n); Along("R_Thigh", "R_Calf", v[4], n);
        Along("L_Calf", "L_Foot", v[5], n); Along("R_Calf", "R_Foot", v[5], n);
        var pelvis = BoneFind.Need(gameObject, tr, "Pelvis");   // 뼈는 이름 먼저, 없으면 Humanoid 대응(BoneFind.cs)
        var pg = pelvis.gameObject.AddComponent<VRMSpringBoneColliderGroup>(); pg.Colliders = new[] { new VRMSpringBoneColliderGroup.SphereCollider { Offset = Vector3.zero, Radius = v[6] / Mathf.Max(1e-6f, pelvis.lossyScale.x) } }; groups.Add(pg);
        var sec = new GameObject("secondary"); sec.transform.SetParent(transform, false);
        var sb = sec.AddComponent<VRMSpringBone>();
        sb.m_stiffnessForce = v[0]; sb.m_gravityPower = v[1]; sb.m_dragForce = v[2]; sb.m_hitRadius = v[3];
        sb.RootBones = tr.Values.Where(t => t.name.StartsWith("Skirt_") && !t.parent.name.StartsWith("Skirt_")).OrderBy(t => t.name).ToList();
        sb.ColliderGroups = groups.ToArray();
        sb.Setup(true);
        Debug.Log("VRM_SKIRT roots=" + sb.RootBones.Count + " groups=" + groups.Count + " prm=" + prm + " scale=" + tr["L_Thigh"].lossyScale.x.ToString("F3"));
    }
}
