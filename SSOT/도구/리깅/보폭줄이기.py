# 보폭줄이기.py — 동작의 다리 움직임(허벅지·종아리·발 뼈가 기본 자세에서 돌아간 양)을 비율만큼 줄인 새 Action을 만든다(공용 도구).
# 기모노처럼 보폭이 좁아야 하는 옷을 위한 것. 각 키의 회전(부모 기준)을 기본 자세 쪽으로 slerp한다. 골반 이동·몸통·팔은 그대로 둔다.
# 실행: SSOT/도구/블렌더실행.sh <입력.blend> SSOT/도구/리깅/보폭줄이기.py -- <리깅설정.json> <출력.blend> <동작,동작,...> [비율,비율,...]
#   비율을 안 주면 리깅설정.json의 "보폭"을 쓴다. 지원 입력: 쿼터니언 회전, 네 성분의 키 시각이 같은 동작(동작옮기기.py가 만든 매 프레임 키). 오일러 회전 뼈는 건너뛴다.
#   새 Action 이름: "Armature|S<비율×100>_<원래 이름에서 앞붙임 UAL_ 등을 뗀 것>" (예: UAL_Walk_Loop, 0.7 → S70_Walk_Loop)
import bpy, sys, json
from mathutils import Quaternion
a = sys.argv[sys.argv.index("--") + 1:]; cfg = json.load(open(a[0], encoding="utf-8")); OUT = a[1]; NAMES = a[2].split(","); FAC = [float(x) for x in a[3].split(",")] if len(a) > 3 else [float(cfg["보폭"])]
HM = cfg["humanoid"]; arm = bpy.data.objects[cfg["armature"]]
LEG = [HM[s + b] for s in ("Left", "Right") for b in ("UpperLeg", "LowerLeg", "Foot")]
made = []
for name in NAMES:
    src = [x for x in bpy.data.actions if x.name.split("|")[-1] == name]; assert len(src) == 1, (name, [x.name for x in bpy.data.actions]); src = src[0]
    base = name.split("_", 1)[1] if "_" in name else name
    for f in FAC:
        act = src.copy(); act.name = "Armature|S%d_%s" % (round(f * 100), base); act.use_fake_user = True
        bag = act.layers[0].strips[0].channelbag(act.slots[0]); n = 0
        for b in LEG:
            path = 'pose.bones["%s"].rotation_quaternion' % b
            fc = [bag.fcurves.find(path, index=i) for i in range(4)]
            if not all(fc): continue
            times = [[round(kp.co[0], 4) for kp in c.keyframe_points] for c in fc]
            assert all(x == times[0] for x in times), "%s: 쿼터니언 네 성분의 키 시각이 다르다(지원하지 않음)" % b   # Astra6 05
            if f == 1.0: continue   # 비율 1은 원본 곡선 그대로
            for k in range(len(fc[0].keyframe_points)):
                q = Quaternion([fc[i].keyframe_points[k].co[1] for i in range(4)])
                assert (q if q.w >= 0 else -q).angle <= 3.1416 * 0.95, "%s 프레임 %s: 기본 자세에서 170도 넘게 돈 키(줄이면 방향이 튐)" % (b, times[0][k])
                r = Quaternion((1, 0, 0, 0)).slerp(q, f)
                if r.dot(q) < 0: r = -r
                for i in range(4): fc[i].keyframe_points[k].co[1] = r[i]
                n += 1
            for c in fc:
                for kp in c.keyframe_points: kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'   # 핸들은 키에서 다시 계산
            for c in fc: c.update()
        made.append(act.name); print("STRIDE", name, "x%.2f" % f, "->", act.name, "키", n, flush=True)
bpy.context.preferences.filepaths.save_version = 0
r = bpy.ops.wm.save_as_mainfile(filepath=OUT, relative_remap=True); assert 'FINISHED' in r
print("STRIDE_DONE", OUT, made)
