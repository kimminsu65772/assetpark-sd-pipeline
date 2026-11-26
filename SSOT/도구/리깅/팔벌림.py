# 팔벌림.py — 동작의 위팔을 몸 바깥쪽으로 벌린 새 Action을 만든다(공용 도구). 넓은 소매 옷에서 소매 안쪽이 몸통을 지나가지 않게 하려는 것.
# 위팔 뼈(Humanoid LeftUpperArm·RightUpperArm)의 회전만 바꾼다. 몸통·빗장뼈·아래팔·손의 회전은 그대로라, 아래팔·손은 위팔을 따라 함께 바깥으로 옮겨진다.
# 방식(리깅설정.json의 "팔벌림"):
#   최소각 = 프레임마다 위팔 방향이 가슴 뼈(Humanoid UpperChest)의 앞뒤·위아래 면에서 바깥으로 벌어진 각을 재어, "각도"보다 작으면 그 각도까지만 바깥으로 돌린다(이미 벌린 프레임은 그대로)
#   더하기 = 모든 프레임에서 위팔을 가슴 뼈의 앞뒤 축을 중심으로 "각도"만큼 바깥으로 돌린다
#   기준: 가슴 뼈의 기본 자세 축(뼈대 공간 +x = 캐릭터 왼쪽, 앞 = "앞" 값의 축). 뼈대 객체 변환은 단위행렬만 지원(아니면 멈춤).
# 실행: SSOT/도구/블렌더실행.sh <입력.blend> SSOT/도구/리깅/팔벌림.py -- <리깅설정.json> <출력.blend> <동작,동작,...> [방식:각도]
#   방식:각도를 안 주면 설정의 "팔벌림"을 쓴다. 지원 입력: 쿼터니언 회전, 위팔의 네 성분 키 시각이 같은 동작(매 프레임 키). 키가 없는 프레임은 고치지 않는다.
#   새 Action 이름: "Armature|A<M=최소각 / A=더하기><각도>_<원래 끝 이름>" (예: S70_Walk_Loop을 최소각 30으로 → AM30_S70_Walk_Loop)
import bpy, sys, json, math
from mathutils import Quaternion, Matrix, Vector
a = sys.argv[sys.argv.index("--") + 1:]; cfg = json.load(open(a[0], encoding="utf-8")); OUT = a[1]; NAMES = a[2].split(",")
P = dict(cfg["팔벌림"])
if len(a) > 3: P["방식"], P["각도"] = a[3].split(":")[0], float(a[3].split(":")[1])
MODE, DEG = P["방식"], float(P["각도"]); assert MODE in ("최소각", "더하기"), MODE
FWD = Vector(P.get("앞", [0, -1, 0])).normalized()   # 뼈대 공간에서 캐릭터 앞(기본 자세). 온천 검사 작업본은 -y
HM = cfg["humanoid"]; arm = bpy.data.objects[cfg["armature"]]; sc = bpy.context.scene; vl = bpy.context.view_layer
assert all(abs(arm.matrix_world[i][j] - (1.0 if i == j else 0.0)) < 1e-6 for i in range(4) for j in range(4)), "뼈대 객체 변환이 단위행렬이 아니다(지원하지 않음)"
CHEST = HM["UpperChest"]
SIDES = [(HM["LeftUpperArm"], +1.0), (HM["RightUpperArm"], -1.0)]   # 바깥 = +x(왼쪽 뼈) / -x(오른쪽 뼈)
made = []
for name in NAMES:
    src = [x for x in bpy.data.actions if x.name.split("|")[-1] == name]; assert len(src) == 1, (name, [x.name for x in bpy.data.actions]); src = src[0]
    tag = "A%s%d_%s" % ("M" if MODE == "최소각" else "A", round(DEG), name)
    act = src.copy(); act.name = "Armature|" + tag; act.use_fake_user = True
    bag = act.layers[0].strips[0].channelbag(act.slots[0])
    # 원본 동작으로 프레임마다 부모·가슴 자세를 먼저 모두 잰다(위팔만 바꾸므로 부모·가슴 자세는 바뀌지 않는다)
    arm.data.pose_position = 'POSE'; arm.animation_data_create(); arm.animation_data.action = src; arm.animation_data.action_slot = src.slots[0]
    plan = {}
    for bn, side in SIDES:
        path = 'pose.bones["%s"].rotation_quaternion' % bn
        fc = [bag.fcurves.find(path, index=i) for i in range(4)]; assert all(fc), "%s: 위팔 쿼터니언 곡선이 없다" % bn
        times = [[round(kp.co[0], 4) for kp in c.keyframe_points] for c in fc]
        assert all(x == times[0] for x in times), "%s: 쿼터니언 네 성분의 키 시각이 다르다(지원하지 않음)" % bn
        plan[bn] = (fc, times[0], side)
    keyset = sorted(set(t for bn in plan for t in plan[bn][1]))
    pose = {}
    for t in keyset:
        sc.frame_set(int(math.floor(t)), subframe=t - math.floor(t)); vl.update()
        pose[t] = {bn: (arm.pose.bones[bn].parent.matrix.to_3x3().copy(), arm.pose.bones[CHEST].matrix.to_3x3().copy(), arm.pose.bones[bn].matrix.to_3x3().copy()) for bn in plan}
    stat = []
    for bn, (fc, times, side) in plan.items():
        b = arm.data.bones[bn]; restrel = (b.parent.matrix_local.to_3x3().inverted() @ b.matrix_local.to_3x3())
        chest_rest = arm.data.bones[CHEST].matrix_local.to_3x3()
        n = 0; before = []; after = []
        for k, t in enumerate(times):
            Ppar, Pch, Marm = pose[t][bn]
            q = Quaternion([fc[i].keyframe_points[k].co[1] for i in range(4)])
            # 가슴 뼈 기준 축(기본 자세의 뼈대 공간 축을 가슴 뼈 자세로 돌린 것)
            R = Pch @ chest_rest.inverted(); out = (R @ Vector((side, 0, 0))).normalized(); fwd = (R @ FWD).normalized()
            d = (Marm @ Vector((0, 1, 0))).normalized()   # 위팔 뼈 방향(머리→꼬리)
            cur = math.degrees(math.asin(max(-1.0, min(1.0, d.dot(out)))))   # 앞뒤·위아래 면에서 바깥으로 벌어진 각
            before.append(cur)
            if MODE == "더하기": ang = DEG; axis = fwd * (-side)
            else:
                ang = DEG - cur
                if ang <= 0: after.append(cur); continue
                axis = d.cross(out);
                if axis.length < 1e-6: after.append(cur); continue
                axis.normalize()
            C = Quaternion(axis, math.radians(ang)).to_matrix()
            if MODE == "더하기" and (C @ d).dot(out) < d.dot(out): C = Quaternion(axis, -math.radians(ang)).to_matrix()   # 바깥쪽으로 도는지 확인
            B = Ppar @ restrel   # 부모 자세 × 기본 자세 상대 회전 (뼈대 공간, 위팔 회전 q 앞)
            qn = (B.inverted() @ C @ B @ q.to_matrix()).to_quaternion()
            if qn.dot(q) < 0: qn = -qn
            for i in range(4): fc[i].keyframe_points[k].co[1] = qn[i]
            after.append(math.degrees(math.asin(max(-1.0, min(1.0, (C @ d).normalized().dot(out))))))
            n += 1
        for c in fc:
            for kp in c.keyframe_points: kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
            c.update()
        stat.append("%s 바꾼 키 %d/%d, 벌림각 %.1f~%.1f → %.1f~%.1f" % (bn, n, len(times), min(before), max(before), min(after), max(after)))
    made.append(act.name); print("ARMOPEN", name, MODE, DEG, "->", act.name, "|", "; ".join(stat), flush=True)
if arm.animation_data: arm.animation_data.action = None
bpy.context.preferences.filepaths.save_version = 0
r = bpy.ops.wm.save_as_mainfile(filepath=OUT, relative_remap=True); assert 'FINISHED' in r
print("ARMOPEN_DONE", OUT, made)
