// VrmSleeve.cs — UniVRM(VRM 0.x)의 VRMSpringBone으로 소매 사슬 뼈("Sleeve_<L|R>_<줄>_<마디>", SSOT/도구/리깅/소매리깅.py 사슬 방식)를 흔들고, 몸통에 공 모양 충돌체를 단다(겨드랑이 후보 C).
// 충돌체: 척추 줄기(Hip→Waist→Spine01→Spine02→NeckTwist01)의 마디마다 공 n개를 좌우로 offX만큼 벌린 두 줄로, 골반(Pelvis)에 같은 두 공, 허벅지(Thigh→Calf)에 공 n개(반지름 thighR).
//   좌우 방향은 시작할 때(기본 자세) R_Upperarm → L_Upperarm 방향으로 잰다. 반지름·간격은 월드 값이고 뼈의 lossyScale로 나눠 넣는다.
// 값은 문자열 "stiff,gravity,drag,hitRadius,bodyR,offX,thighR,n"으로 받는다. 뼈는 TRIPO 이름 먼저, 없으면 Humanoid 대응으로 찾는다(BoneFind.cs).
//   Humanoid에 없는 척추 덧뼈(Hip, Waist)가 없는 캐릭터는 찾은 척추 마디끼리만 잇는다.
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using VRM;

public class VrmSleeve : MonoBehaviour
{
    public string prm = "1.0,0.3,0.4,0.01,0.045,0.035,0.045,3";
    void Start()
    {
        var v = prm.Split(',').Select(s => float.Parse(s, System.Globalization.CultureInfo.InvariantCulture)).ToArray();
        var tr = GetComponentsInChildren<Transform>(true).GroupBy(t => t.name).ToDictionary(g => g.Key, g => g.First());
        int n = Mathf.Max(2, Mathf.RoundToInt(v[7]));
        Vector3 lat = (BoneFind.Need(gameObject, tr, "L_Upperarm").position - BoneFind.Need(gameObject, tr, "R_Upperarm").position).normalized;
        var groups = new List<VRMSpringBoneColliderGroup>();
        void Along(string bone, string child, float r, float off) => AlongT(BoneFind.Need(gameObject, tr, bone), BoneFind.Need(gameObject, tr, child), r, off);
        void AlongT(Transform b, Transform c, float r, float off)
        {
            var g = b.gameObject.AddComponent<VRMSpringBoneColliderGroup>(); float s = Mathf.Max(1e-6f, b.lossyScale.x);
            var list = new List<VRMSpringBoneColliderGroup.SphereCollider>();
            foreach (float sd in off > 0 ? new[] { -1f, 1f } : new[] { 0f })
                for (int i = 0; i < n; i++)
                {
                    Vector3 w = Vector3.Lerp(b.position, c.position, i / (float)(n - 1)) + lat * off * sd;
                    list.Add(new VRMSpringBoneColliderGroup.SphereCollider { Offset = b.InverseTransformPoint(w), Radius = r / s });
                }
            g.Colliders = list.ToArray(); groups.Add(g);
        }
        var spine = new[] { "Hip", "Waist", "Spine01", "Spine02", "NeckTwist01" }.Select(s => BoneFind.Find(gameObject, tr, s)).Where(t => t != null).ToArray();
        for (int i = 0; i + 1 < spine.Length; i++) AlongT(spine[i], spine[i + 1], v[4], v[5]);
        AlongT(BoneFind.Need(gameObject, tr, "Pelvis"), spine[0], v[4], v[5]);
        Along("L_Thigh", "L_Calf", v[6], 0); Along("R_Thigh", "R_Calf", v[6], 0);
        var sec = new GameObject("secondary_sleeve"); sec.transform.SetParent(transform, false);
        var sb = sec.AddComponent<VRMSpringBone>();
        sb.m_stiffnessForce = v[0]; sb.m_gravityPower = v[1]; sb.m_dragForce = v[2]; sb.m_hitRadius = v[3];
        sb.RootBones = tr.Values.Where(t => t.name.StartsWith("Sleeve_") && !t.parent.name.StartsWith("Sleeve_")).OrderBy(t => t.name).ToList();
        sb.ColliderGroups = groups.ToArray();
        sb.Setup(true);
        Debug.Log("VRM_SLEEVE roots=" + sb.RootBones.Count + " groups=" + groups.Count + " prm=" + prm + " scale=" + BoneFind.Need(gameObject, tr, "Spine02").lossyScale.x.ToString("F3"));
    }
}
