# 동작옮기기.py — 다른 뼈대의 동작을 캐릭터 뼈대로 옮겨 새 Action으로 저장한다(공용 도구). 원본은 UAL1(Universal Animation Library 1, CC0) 또는 다른 캐릭터의 FBX.
# 교복 사무라이 `…/유니티샘플_v033/동작옮기기.py`를 캐릭터 설정 파일(리깅설정.json의 humanoid 표)로 뼈 이름을 받게 고친 것.
# 실행: SSOT/도구/블렌더실행.sh <캐릭터.blend> SSOT/도구/리깅/동작옮기기.py -- <리깅설정.json> <원본.fbx> <출력.blend> <동작,동작,...> [원본 리깅설정.json] [새 이름 앞붙임]
#   원본 리깅설정을 안 주면 UAL1 뼈 이름으로 본다. 새 Action 이름은 "Armature|<앞붙임><동작>"(앞붙임 기본 UAL_, 동작 이름의 .001 같은 꼬리는 뗌).
# 방법: 두 뼈대의 기준 자세를 뼈 방향으로 맞춘 뒤, 원본 뼈가 기준 자세에서 돌아간 만큼을 캐릭터 뼈에 세계 축 기준으로 준다.
#       골반 이동은 (골반 높이 - 바닥 높이)의 비율로 줄인다. 바닥 높이는 그 뼈대를 따르는 메시의 가장 낮은 점. 원본 30fps를 24fps로 다시 뽑는다.
# 입력 blend는 고치지 않는다(다른 이름으로 저장). 원본 fps는 FBX를 가져온 뒤 장면 fps로 읽고, 24fps로 다시 뽑는다.
import bpy, sys, math, json, traceback
from mathutils import Matrix, Vector, Quaternion
try:
    a = sys.argv[sys.argv.index("--") + 1:]; CFG, FBX, OUT, NAMES = a[0], a[1], a[2], a[3].split(",")
    SCFG = a[4] if len(a) > 4 and a[4] != "-" else None; PFX = a[5] if len(a) > 5 else "UAL_"
    cfg = json.load(open(CFG, encoding="utf-8")); HM = cfg["humanoid"]
    sc = bpy.context.scene; vl = bpy.context.view_layer; T = bpy.data.objects[cfg["armature"]]; vl.objects.active = T
    if bpy.context.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
    sc.render.fps = 24; sc.render.fps_base = 1
    T.data.pose_position = 'POSE'
    if not T.animation_data: T.animation_data_create()
    def skinned(A): return [o for o in bpy.data.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' and m.object == A for m in o.modifiers)]   # 그 뼈대를 따르는 메시만(Astra6 04)
    ground_t = min((o.matrix_world @ v.co).z for o in skinned(T) for v in o.data.vertices)
    keep = {k: set(getattr(bpy.data, k)) for k in ("objects", "meshes", "armatures", "materials", "images", "actions", "collections", "textures")}
    bpy.ops.import_scene.fbx(filepath=FBX); fps_src = sc.render.fps / sc.render.fps_base; sc.render.fps = 24; sc.render.fps_base = 1
    S = [o for o in bpy.data.objects if o not in keep["objects"] and o.type == 'ARMATURE'][0]
    fps_s, fps_t = float(fps_src), 24.0
    # 원본 뼈 이름 → Humanoid 이름. 원본 설정이 있으면 그 표를 뒤집어 쓰고, 없으면 UAL1 이름
    if SCFG:
        U = {v: k for k, v in json.load(open(SCFG, encoding="utf-8"))["humanoid"].items()}
    else:
        U = {"pelvis": "Hips", "spine_01": "Spine", "spine_02": "Chest", "spine_03": "UpperChest", "neck_01": "Neck", "Head": "Head"}
        for s, side in (("l", "Left"), ("r", "Right")):
            U.update({"clavicle_" + s: side + "Shoulder", "upperarm_" + s: side + "UpperArm", "lowerarm_" + s: side + "LowerArm", "hand_" + s: side + "Hand",
                      "thigh_" + s: side + "UpperLeg", "calf_" + s: side + "LowerLeg", "foot_" + s: side + "Foot", "ball_" + s: side + "Toes"})
            for f, F in (("thumb", "Thumb"), ("index", "Index"), ("middle", "Middle"), ("ring", "Ring"), ("pinky", "Little")):
                for i_, P in ((1, "Proximal"), (2, "Intermediate"), (3, "Distal")): U["%s_0%d_%s" % (f, i_, s)] = "%s %s %s" % (side, F, P)
    UH = {h: s for s, h in U.items()}   # Humanoid 이름 → 원본 뼈 이름
    # 방향 맞추기에 쓸 Humanoid 자식(없으면 None)
    HC = {"Hips": "Spine", "Spine": "Chest", "Chest": "UpperChest", "UpperChest": "Neck", "Neck": "Head", "Head": None}
    for side in ("Left", "Right"):
        HC.update({side + "Shoulder": side + "UpperArm", side + "UpperArm": side + "LowerArm", side + "LowerArm": side + "Hand", side + "Hand": side + " Middle Proximal",
                   side + "UpperLeg": side + "LowerLeg", side + "LowerLeg": side + "Foot", side + "Foot": side + "Toes", side + "Toes": None})
        for F in ("Thumb", "Index", "Middle", "Ring", "Little"):
            HC.update({"%s %s Proximal" % (side, F): "%s %s Intermediate" % (side, F), "%s %s Intermediate" % (side, F): "%s %s Distal" % (side, F), "%s %s Distal" % (side, F): None})
    def hchild(h):   # 자식이 양쪽 뼈대에 다 있는 첫 Humanoid 자식(UpperChest가 없으면 Neck으로 건너뜀)
        c = HC.get(h)
        while c and not (c in HM and c in UH): c = HC.get(c)
        return c
    CH = {s: (UH[hchild(h)] if hchild(h) else None) for s, h in U.items()}
    MAP = []
    for s, h in U.items():
        if h not in HM: continue
        t = HM[h]; c = CH[s]; tc = HM.get(U[c]) if c else None
        if s not in S.data.bones: continue
        assert t in T.data.bones, (s, t)
        MAP.append((s, t, c if tc else None, tc))
    order = [b.name for b in T.data.bones]; MAP.sort(key=lambda m: order.index(m[1]))
    SW = S.matrix_world; TW = T.matrix_world
    def srest(n): return SW @ S.data.bones[n].head_local
    def trest(n): return TW @ T.data.bones[n].head_local
    def flat(v): v = Vector((v.x, v.y, 0)); return v.normalized()
    LT, LF, LH, HIP = HM["LeftToes"], HM["LeftFoot"], HM["LeftHand"], HM["Hips"]
    SP, SLT, SLF, SLH = UH["Hips"], UH["LeftToes"], UH["LeftFoot"], UH["LeftHand"]
    fs = flat(srest(SLT) - srest(SLF)); ft = flat(T.matrix_world @ T.data.bones[LT].tail_local - trest(LF)) if (trest(LT) - trest(LF)).length < 1e-6 else flat(trest(LT) - trest(LF))
    ang = math.atan2(fs.x * ft.y - fs.y * ft.x, fs.dot(ft)); G = Quaternion((0, 0, 1), ang)
    cx = trest(HIP).x; chk = (G @ (srest(SLH) - srest(SP))).x * (trest(LH).x - cx)
    assert chk > 0, "좌우가 뒤집혀 있다"
    smeshes = [o for o in skinned(S) if o not in keep["objects"]]
    ground_s = min((o.matrix_world @ v.co).z for o in smeshes for v in o.data.vertices) if smeshes else 0.0
    ratio = (trest(HIP).z - ground_t) / (srest(SP).z - ground_s); assert trest(HIP).z > ground_t and srest(SP).z > ground_s, "골반이 바닥보다 낮다"
    print("ALIGN 원본을 Z축으로 %.1f도 돌림, 크기 비율 %.3f, 바닥 대상 %.4f 원본 %.4f, 뼈 %d개, 원본 %.0ffps" % (math.degrees(ang), ratio, ground_t, ground_s, len(MAP), fps_s))
    A = {}; RQ = {}
    for s, t, sc_, tc in MAP:
        RQ[t] = (TW @ T.data.bones[t].matrix_local).to_quaternion()
        if sc_ is None: A[t] = Quaternion(); continue
        ds = G @ (srest(sc_) - srest(s)); dt = trest(tc) - trest(t)
        A[t] = dt.normalized().rotation_difference(ds.normalized())
    SR = {s: (SW @ S.data.bones[s].matrix_local).to_quaternion() for s, *_ in MAP}
    p_s0 = srest(SP); p_t0 = trest(HIP); Ginv = G.inverted(); TWinv = TW.inverted()
    ad_t = T.animation_data; made = []
    for name in NAMES:
        c = [x for x in bpy.data.actions if x not in keep["actions"] and x.name.endswith("|" + name)]; assert len(c) == 1, (name, [x.name for x in c]); src = c[0]
        S.animation_data.action = src
        if src.slots: S.animation_data.action_slot = src.slots[0]
        f0, f1 = src.frame_range; n = math.ceil((f1 - f0) * fps_t / fps_s - 1e-6)
        act = bpy.data.actions.new("Armature|%s%s" % (PFX, name.split(".")[0])); act.use_fake_user = True; ad_t.action = act
        for pb in T.pose.bones:
            pb.location = (0, 0, 0); pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
        prev = {}
        for k in range(n + 1):
            ts = min(f1, f0 + k * fps_s / fps_t); sc.frame_set(int(math.floor(ts)), subframe=ts - math.floor(ts)); vl.update()
            sq = {s: (SW @ S.pose.bones[s].matrix).to_quaternion() for s, *_ in MAP}; sp = SW @ S.pose.bones[SP].head
            for s, t, sc_, tc in MAP:
                pb = T.pose.bones[t]; D = G @ (sq[s] @ SR[s].inverted()) @ Ginv; q = (D @ A[t] @ RQ[t])
                if t == HIP: head = p_t0 + (G @ (sp - p_s0)) * ratio
                else: head = TW @ (pb.parent.matrix @ pb.parent.bone.matrix_local.inverted() @ pb.bone.matrix_local).translation
                pb.matrix = TWinv @ Matrix.LocRotScale(head, q, (1, 1, 1)); vl.update()
                if t in prev and prev[t].dot(pb.rotation_quaternion) < 0: pb.rotation_quaternion = -pb.rotation_quaternion
                prev[t] = pb.rotation_quaternion.copy(); pb.keyframe_insert("rotation_quaternion", frame=k + 1)
                if t == HIP: pb.keyframe_insert("location", frame=k + 1)
        assert len(act.slots) == 1, len(act.slots)
        made.append(act.name); print("RETARGET", name, "원본 %d~%d (%.0ffps) -> 1~%d (24fps)" % (f0, f1, fps_s, n + 1), flush=True)
    ad_t.action = None
    for pb in T.pose.bones: pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0)
    sc.frame_set(1)
    for k in ("objects", "meshes", "armatures", "materials", "images", "textures", "collections", "actions"):
        for d in list(getattr(bpy.data, k)):
            if d not in keep[k] and d.name not in made: getattr(bpy.data, k).remove(d)
    bpy.context.preferences.filepaths.save_version = 0
    r = bpy.ops.wm.save_as_mainfile(filepath=OUT, relative_remap=True); assert 'FINISHED' in r
    print("RETARGET_DONE", OUT, made)
except Exception:
    traceback.print_exc(); print("RETARGET_FAILED"); sys.exit(1)
