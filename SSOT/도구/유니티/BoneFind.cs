// BoneFind.cs — 촬영·흔들림 스크립트(OnsenPlay·SkirtSpring·VrmSkirt·VrmSleeve)가 뼈를 찾는 곳(W15, 2026-11-24).
// 먼저 TRIPO 뼈 이름(온천 검사에서 쓴 이름: L_Foot, Pelvis …)으로 찾는다. 그 이름이 없으면 Animator의 Humanoid 대응(HumanBodyBones)으로 찾는다.
// 그래서 온천 검사에서는 전과 같은 뼈를 쓰고, 뼈 이름이 다른 캐릭터는 Humanoid 설정(OnsenSetup.cs가 대응표로 만듦)만 되어 있으면 그대로 쓴다.
// Humanoid에 없는 뼈(Hip, Waist 등 TRIPO 덧뼈)는 이름으로만 찾고, 없으면 null을 돌려준다(부르는 쪽이 그 마디를 건너뜀).
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

public static class BoneFind
{
    // TRIPO 뼈 이름 → Humanoid 뼈. 여기 없는 이름은 이름으로만 찾는다.
    static readonly Dictionary<string, HumanBodyBones> Human = new Dictionary<string, HumanBodyBones>
    {
        { "Pelvis", HumanBodyBones.Hips }, { "Spine01", HumanBodyBones.Spine }, { "Spine02", HumanBodyBones.Chest }, { "NeckTwist01", HumanBodyBones.Neck },
        { "L_Upperarm", HumanBodyBones.LeftUpperArm }, { "R_Upperarm", HumanBodyBones.RightUpperArm },
        { "L_Thigh", HumanBodyBones.LeftUpperLeg }, { "R_Thigh", HumanBodyBones.RightUpperLeg },
        { "L_Calf", HumanBodyBones.LeftLowerLeg }, { "R_Calf", HumanBodyBones.RightLowerLeg },
        { "L_Foot", HumanBodyBones.LeftFoot }, { "R_Foot", HumanBodyBones.RightFoot },
        { "L_ToeBase", HumanBodyBones.LeftToes }, { "R_ToeBase", HumanBodyBones.RightToes },
    };

    public static Dictionary<string, Transform> All(GameObject root) =>
        root.GetComponentsInChildren<Transform>(true).GroupBy(t => t.name).ToDictionary(g => g.Key, g => g.First());

    // 찾지 못하면 null
    public static Transform Find(GameObject root, Dictionary<string, Transform> tr, string name)
    {
        if (tr.TryGetValue(name, out var t)) return t;
        if (!Human.TryGetValue(name, out var hb)) return null;
        var anim = root.GetComponentInChildren<Animator>(true);
        if (anim == null || !anim.isHuman) return null;
        return anim.GetBoneTransform(hb);
    }

    // 꼭 있어야 하는 뼈: 없으면 이름을 적어 멈춘다
    public static Transform Need(GameObject root, Dictionary<string, Transform> tr, string name)
    {
        var t = Find(root, tr, name);
        if (t == null) throw new KeyNotFoundException("뼈를 찾지 못함: " + name + " (이름도 Humanoid 대응도 없음)");
        return t;
    }
}
