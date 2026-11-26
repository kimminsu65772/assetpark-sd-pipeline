# 자락리깅.py — 치마·기모노 자락의 가중치 다시 계산(6-3)과 자락 전용 뼈(6-4)를 넣는 공용 도구.
# 교복 사무라이 `리깅_v031/치마가중치.py`(6-3)와 `치마리깅_v032/skirt.py`·`굽기.py`(Astra 작성)를 캐릭터 설정 파일로 값을 받게 고친 것.
# 실행: SSOT/도구/블렌더실행.sh <입력.blend> SSOT/도구/리깅/자락리깅.py -- <리깅설정.json> <방식> <출력.blend> [Action,Action,...]
#   방식: 가중치  = 6-3만(자락 아래쪽을 허벅지·골반으로 매끈하게 다시 나눔, 위쪽은 받은 가중치 유지)
#         고리     = 6-3 + 자락 뼈(둘레 N줄 × M단, 모두 골반 뼈의 자식) + 동작마다 굽기(후보 B). Action을 주면 그 동작만, 안 주면 "UAL_"로 시작하는 동작 전부
#         다듬기   = 받은(원본) 가중치를 유지하고, 이웃 정점과 고르게 섞어 들쭉날쭉함을 줄이고, 앞뒤 가운데에서 좌우 다리 몫이 넘어가는 폭을 넓힌다. 뼈는 넣지 않는다
#         사슬     = 6-3 + 자락 뼈(둘레 N줄, 줄마다 위에서 아래로 이어진 M마디 사슬, 맨 위가 골반 뼈의 자식). 굽지 않는다(후보 D. 움직임은 게임 안 물리가 맡음)
# 자락 = 설정의 "파츠"에서 가장 큰 이어진 조각(자락이 가장 큰 한 조각인 입력만 지원), 다리 = "다리조각" 번째 조각. 객체 변환이 단위행렬인 입력만 지원. 형태·정점 순서·면·UV는 바꾸지 않는다. 자락 밖 정점 가중치도 그대로 둔다.
# 설정(리깅설정.json의 "자락"): 골반뼈, 6-3{z_hi,z_lo,w,legmax}, 둘레, 단높이(아래→위), 여유, 앞자락_허벅지몫(0~1, 없으면 0. 환경 변수 FRONT_THIGH로 바꿀 수 있음).
import bpy, sys, os, math, json, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
sys.dont_write_bytecode = True
a = sys.argv[sys.argv.index("--") + 1:]
cfg = json.load(open(a[0], encoding="utf-8")); MODE = a[1]; OUT = a[2]; ACTS = a[3].split(",") if len(a) > 3 and a[3] else None
assert MODE in ("가중치", "고리", "사슬", "다듬기"), MODE
SK = cfg["자락"]; HM = cfg["humanoid"]; PELVIS = SK["골반뼈"]
LT, RT, LC, RC = HM["LeftUpperLeg"], HM["RightUpperLeg"], HM["LeftLowerLeg"], HM["RightLowerLeg"]
sc = bpy.context.scene; vl = bpy.context.view_layer; arm = bpy.data.objects[cfg["armature"]]; vl.objects.active = arm
if bpy.context.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
low = bpy.data.objects[SK["파츠"]]; me = low.data
from mathutils import Matrix
# 지원 입력: 뼈대와 자락 파츠의 객체 변환이 단위행렬(위치 0·회전 0·배율 1). 아니면 멈춘다(정점·뼈·BVH를 같은 좌표계로 본다). 독립 검수 Astra6 01
for _o in (arm, low):
    assert all(abs(_o.matrix_world[i][j] - (1.0 if i == j else 0.0)) < 1e-6 for i in range(4) for j in range(4)), "%s의 객체 변환이 단위행렬이 아니다(지원하지 않음)" % _o.name

def islands(m):
    par = list(range(len(m.vertices)))
    def f(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    for e in m.edges:
        p, q = f(e.vertices[0]), f(e.vertices[1])
        if p != q: par[p] = q
    co = [v.co for v in m.vertices]; kd = KDTree(len(co))
    for i, c in enumerate(co): kd.insert(c, i)
    kd.balance()
    for i, c in enumerate(co):
        for _, j, _ in kd.find_range(c, 1e-6):
            p, q = f(i), f(j)
            if p != q: par[p] = q
    g = {}
    for i in range(len(co)): g.setdefault(f(i), []).append(i)
    return sorted(g.values(), key=len, reverse=True)
assert SK.get("조각", "가장큰조각") == "가장큰조각", "자락 선택은 지금 '가장큰조각'(파츠에서 가장 큰 이어진 조각)만 지원한다"   # Astra6 03
ISL = islands(me); SKV = set(ISL[0]); LGV = set(v for k in SK["다리조각"] for v in ISL[k])
me.calc_loop_triangles()
sk_tri = np.array([tuple(t.vertices) for t in me.loop_triangles if all(v in SKV for v in t.vertices)], dtype=int)
leg_tri = np.array([tuple(t.vertices) for t in me.loop_triangles if all(v in LGV for v in t.vertices)], dtype=int)
sk = np.unique(sk_tri); SKLIST = sk_tri.tolist(); LEGLIST = leg_tri.tolist()
arm.data.pose_position = 'REST'; vl.update()
MW = low.matrix_world
rest_co = np.array([list(MW @ v.co) for v in me.vertices])
print("자락 정점 %d 삼각형 %d, 다리 삼각형 %d" % (len(sk), len(sk_tri), len(leg_tri)))

def sm(t):
    t = min(1.0, max(0.0, t)); return t * t * (3 - 2 * t)
def smooth(x):
    x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)
def vweights(v):
    return {low.vertex_groups[g.group].name: g.weight for g in me.vertices[v].groups if g.weight > 1e-6}
def set_weights(v, d):
    for g in list(me.vertices[v].groups): low.vertex_groups[g.group].remove([v])
    for k, x in d.items():
        G = low.vertex_groups.get(k) or low.vertex_groups.new(name=k); G.add([v], x, 'REPLACE')

# ---------- 6-3: 자락 가중치 다시 계산 ----------
def weights_63():
    p = SK["6-3"]; z_hi, z_lo, w, legmax = p["z_hi"], p["z_lo"], p["w"], p["legmax"]
    cx = float(np.mean(rest_co[list(SKV), 0]))
    for v in sorted(SKV):
        d = vweights(v); P = rest_co[v]
        t = sm((z_hi - P[2]) / (z_hi - z_lo)); L = sm((P[0] - cx + w) / (2 * w))   # +x 쪽이 L_ 허벅지
        s0 = sum(d.values()); nw = {k: x / s0 * (1 - t) for k, x in d.items()}
        for k, x in ((LT, legmax * L), (RT, legmax * (1 - L)), (PELVIS, 1 - legmax)): nw[k] = nw.get(k, 0.0) + t * x
        nw = dict(sorted(((k, x) for k, x in nw.items() if x > 0.005), key=lambda kv: -kv[1])[:4]); s = sum(nw.values())
        set_weights(v, {k: x / s for k, x in nw.items()})
    me.update(); vl.update()
    print("WEIGHTS_63", p, "중심 x %.4f" % cx)

# ---------- 자락 뼈 ----------
COUNT = SK["둘레"]; FRONT_THIGH = float(os.environ.get("FRONT_THIGH", SK.get("앞자락_허벅지몫", 0))); LEVELS = list(SK["단높이"]); M = len(LEVELS); PREFIX = "Skirt_"
c2 = rest_co[sk]; CENTER = np.array([(c2[:, 0].min() + c2[:, 0].max()) / 2, (c2[:, 1].min() + c2[:, 1].max()) / 2])
ANGLE = np.arange(COUNT) * math.tau / COUNT
RADIAL = np.column_stack((np.cos(ANGLE), np.sin(ANGLE), np.zeros(COUNT)))
Z_TOP = float(c2[:, 2].max()); Z_HEM = float(c2[:, 2].min())
def ringname(j, i): return f"{PREFIX}{j + 1}_{i + 1:02d}"
def rings():
    az = np.arctan2(c2[:, 1] - CENTER[1], c2[:, 0] - CENTER[0]); radius = np.linalg.norm(c2[:, :2] - CENTER, axis=1); out = []
    for z in LEVELS:
        band = []
        for an in ANGLE:
            dist = (np.angle(np.exp(1j * (az - an))) / .23) ** 2 + ((c2[:, 2] - z) / .012) ** 2
            band.append(np.percentile(radius[np.argsort(dist)[:12]], 20))
        out.append(band)
    return np.array(out)
RADII = None
def node(j, i):
    d = RADIAL[i]; return Vector((*list(CENTER + RADII[j, i] * d[:2]), LEVELS[j]))
def install(chain):
    global RADII
    RADII = rings()
    assert not any(b.name.startswith(PREFIX) for b in arm.data.bones)
    bpy.ops.object.mode_set(mode='EDIT'); eb = arm.data.edit_bones
    for i in range(COUNT):
        for j in reversed(range(M)):   # 위 단부터
            b = eb.new(ringname(j, i)); b.head = node(j, i); d = RADIAL[i]
            if chain:
                b.tail = node(j - 1, i) if j > 0 else node(0, i) + Vector((0.3 * (node(0, i) - node(1, i)).x, 0.3 * (node(0, i) - node(1, i)).y, -(LEVELS[0] - Z_HEM) - 0.002))
                b.parent = eb[PELVIS] if j == M - 1 else eb[ringname(j + 1, i)]; b.use_connect = False
            else:
                b.tail = b.head + Vector((.003 * d[0], .003 * d[1], -.014)); b.parent = eb[PELVIS]
    bpy.ops.object.mode_set(mode='OBJECT')
    for j in range(M):
        for i in range(COUNT): low.vertex_groups.new(name=ringname(j, i))
    LEGB = {LT, RT, LC, RC, PELVIS, HM["Hips"]}
    for index in sk:
        v = me.vertices[int(index)]; old = vweights(int(index))
        keep = {k: w for k, w in old.items() if k not in LEGB}
        if FRONT_THIGH > 0:   # 앞자락만 허벅지 몫을 일부 남긴다(앞 = -y). 앞일수록, 아래일수록 많이
            az0 = math.atan2(rest_co[index, 1] - CENTER[1], rest_co[index, 0] - CENTER[0]); fr = sm(-math.sin(az0) * 1.4 - 0.2)
            low_ = sm((LEVELS[-1] - rest_co[index, 2]) / (LEVELS[-1] - LEVELS[0]))
            for k in (LT, RT):
                if old.get(k, 0) > 0: keep[k] = old[k] * FRONT_THIGH * fr * low_
        mobile = 1 - sum(keep.values())
        z = float(np.interp(rest_co[index, 2], LEVELS, np.arange(M)))
        an = (math.atan2(rest_co[index, 1] - CENTER[1], rest_co[index, 0] - CENTER[0]) % math.tau) * COUNT / math.tau
        j, i = min(math.floor(z), M - 2), math.floor(an); u, t = an % 1, z - j
        nodes = [(j, i, 1 - u - t), (j, i + 1, u), (j + 1, i, t)] if u + t <= 1 else [(j + 1, i + 1, u + t - 1), (j, i + 1, 1 - t), (j + 1, i, 1 - u)]
        cage = {}
        for band, col, w in nodes:
            if w > 1e-8: cage[ringname(band, col % COUNT)] = cage.get(ringname(band, col % COUNT), 0) + w
        cage = dict(sorted(cage.items(), key=lambda kv: -kv[1])[:4 - len(keep)])
        set_weights(int(index), {**keep, **{k: mobile * w / sum(cage.values()) for k, w in cage.items() if mobile * w > 0}})
    me.update(); vl.update()
    print("INSTALL", "사슬" if chain else "고리", "앞자락 허벅지몫 %.2f" % FRONT_THIGH, "뼈 %d개 추가(%d줄 x %d단), 중심 (%.4f, %.4f), 단 %s" % (COUNT * M, COUNT, M, CENTER[0], CENTER[1], LEVELS))

# ---------- 굽기(후보 B). Astra 원본의 계산을 옮김. 단, 원본 skirt.py의 relax_folds(자락 자체 교차 완화)는 옮기지 않았다(후보 B를 쓰지 않기로 해 생략, 독립 검수 Astra6 02). 다시 쓰려면 그 함수와 전체 프레임 재검증을 먼저 옮긴다 ----------
def evaluated():
    obj = low.evaluated_get(bpy.context.evaluated_depsgraph_get()); co = np.empty(len(obj.data.vertices) * 3, np.float32)
    obj.data.vertices.foreach_get('co', co); return co.reshape(-1, 3).astype(float)
def hip_matrix():
    h = arm.pose.bones[PELVIS]; return h.matrix @ h.bone.matrix_local.inverted()
def gradients():
    hip_inv = hip_matrix().inverted(); swings = []
    for nm, sgn in ((LT, 1), (RT, -1)):
        b = arm.pose.bones[nm]
        axis = np.array(hip_inv @ b.tail) - np.array(hip_inv @ b.head); base = np.array(b.bone.tail_local) - np.array(b.bone.head_local)
        axis /= np.linalg.norm(axis); base /= np.linalg.norm(base)
        swing = Vector(base).rotation_difference(Vector(axis)); v = np.array(swing @ Vector((0, 0, -1)))
        dot = RADIAL @ v; tilt = math.acos(np.clip(-v[2], -1, 1)); angle = tilt * np.maximum(0, dot / max(1e-8, np.linalg.norm(v[:2])))
        influence = smooth((sgn * np.cos(ANGLE) + .93) / 1.10); swings.append(np.maximum(0, angle) * influence)
    return np.maximum(*swings)
def solve():
    angles = gradients(); hip = hip_matrix(); inv = np.array(hip.inverted())
    co = evaluated() @ inv[:3, :3].T + inv[:3, 3]
    tree = BVHTree.FromPolygons(co.tolist(), LEGLIST, all_triangles=True)
    amt = np.minimum(angles, 1.7); zgrid = np.array(LEVELS)[:, None]
    lift = (Z_TOP - zgrid) * (1 - np.cos(amt * .61))
    disp = np.zeros_like(RADII)
    for j, z in enumerate(LEVELS):
        for i, an in enumerate(ANGLE):
            outer = 0
            for da in [-.12, 0, .12]:
                d = np.array([math.cos(an + da), math.sin(an + da), 0.])
                for dz in ([-.009, 0, .012, .024, .036, .048] if j == M - 1 else [-.009, 0, .009]):
                    origin = np.r_[CENTER, .0] + .38 * d; origin[2] = z + lift[j, i] + dz
                    hit = tree.ray_cast(origin, -d, .38)
                    if hit[0] is not None: outer = max(outer, .38 - hit[3])
            disp[j, i] = max(0, outer + SK["여유"] - RADII[j, i])
    disp[-1] *= 1.52
    ext = disp.copy()
    for _ in range(14):
        avg = (np.roll(ext, 1, axis=1) + np.roll(ext, -1, axis=1) + 2 * ext) * .25; ext = np.maximum(disp, avg)
    active = min(1, float(np.max(angles)) / .20)
    for j in range(M):
        for i, d in enumerate(RADIAL):
            p = arm.pose.bones[ringname(j, i)]
            slope = (ext[j, (i + 1) % COUNT] - ext[j, (i - 1) % COUNT]) / (2 * math.tau / COUNT); tangent = np.array([-d[1], d[0], 0])
            move = (d * ext[j, i] + tangent * np.clip(.26 * slope, -.018, .018)) * active; move[2] = lift[j, i]
            p.location = p.bone.matrix_local.to_quaternion().inverted() @ Vector(move)
    vl.update(); resolve_contacts(float(np.max(angles)))
    return angles
WAIST = (-.2, 1., .28, .07)
def resolve_contacts(swing):
    for _ in range(16):
        pts = evaluated().tolist()
        st = BVHTree.FromPolygons(pts, SKLIST, all_triangles=True); lt = BVHTree.FromPolygons(pts, LEGLIST, all_triangles=True)
        hits = st.overlap(lt)
        if not hits: break
        points = rest_co[sk_tri[np.unique([i for i, j in hits])]].mean(axis=1)
        az = np.arctan2(points[:, 1] - CENTER[1], points[:, 0] - CENTER[0]); dist = np.angle(np.exp(1j * (ANGLE[:, None] - az[None, :])))
        for j, z in enumerate(LEVELS):
            dz = z - np.clip(points[:, 2], LEVELS[0], LEVELS[-1]); aw, zw = (.42, .027) if swing > .08 else WAIST[2:]
            bump = .0035 * np.exp(-.5 * ((dist / aw) ** 2 + (dz[None, :] / zw) ** 2)).max(axis=1)
            for i, value in enumerate(bump):
                p = arm.pose.bones[ringname(j, i)]
                p.location += p.bone.matrix_local.to_quaternion().inverted() @ Vector((RADIAL[i] if swing > .08 else (WAIST[0] * RADIAL[i] + np.array([0., 0., WAIST[1]]))) * value)
        vl.update()
def bake(action):
    ad = arm.animation_data; ad.action = action; ad.action_slot = action.slots[0]
    start, end = map(int, action.frame_range); bones = [p for p in arm.pose.bones if p.name.startswith(PREFIX)]
    values = np.empty((end - start + 1, len(bones), 3))
    for row, frame in enumerate(range(start, end + 1)):
        sc.frame_set(frame); solve(); values[row] = [tuple(p.location) for p in bones]
    for row, frame in enumerate(range(start, end)):
        sc.frame_set(frame, subframe=.5); mid = .5 * (values[row] + values[row + 1])
        for p, loc in zip(bones, mid): p.location = loc
        vl.update(); resolve_contacts(float(np.max(gradients())))
        values[row:row + 2] += np.array([tuple(p.location) for p in bones]) - mid
    bag = action.layers[0].strips[0].channelbag(ad.action_slot)
    for i, p in enumerate(bones):
        path = p.path_from_id("location")
        for axis in range(3):
            old = bag.fcurves.find(path, index=axis)
            if old: bag.fcurves.remove(old)
            fc = bag.fcurves.new(path, index=axis); pts = fc.keyframe_points; pts.add(len(values))
            pts.foreach_set("co", np.column_stack((np.arange(start, end + 1), values[:, i, axis])).astype(np.float32).ravel())
            for k in pts: k.interpolation = 'LINEAR'
            fc.update()
    print("BAKED", action.name, len(values), len(bones), flush=True)


# ---------- 다듬기: 원본 가중치 유지 + 고르게 섞기 + 가운데 폭 넓히기 ----------
def jag(vs):
    s = set(vs); d = []
    for e in me.edges:
        a_, b_ = e.vertices
        if a_ in s and b_ in s:
            A, B = vweights(a_), vweights(b_); ks = set(A) | set(B)
            d.append(max(abs(A.get(k, 0) - B.get(k, 0)) for k in ks) if ks else 0)
    d = np.array(d); return {"변": int(len(d)), "차>0.3": int((d > .3).sum()), "차>0.5": int((d > .5).sum()), "최대": round(float(d.max()), 3), "평균": round(float(d.mean()), 3)}
def smooth_orig():
    p = dict(SK.get("다듬기", {}))
    if os.environ.get("DADEUM"): p.update(zip(("반복", "세기", "가운데폭"), map(float, os.environ["DADEUM"].split(","))))   # 시험용: "반복,세기,가운데폭"
    n_it, a_, w2 = int(p.get("반복", 6)), float(p.get("세기", .5)), float(p.get("가운데폭", .06))
    z_keep = float(p.get("윗단유지", Z_TOP - .03))   # 이 높이 위(띠 바로 아래)는 그대로 둔다
    vs = sorted(SKV); nb = {v: set() for v in vs}
    for e in me.edges:
        a0, b0 = e.vertices
        if a0 in SKV and b0 in SKV: nb[a0].add(b0); nb[b0].add(a0)
    print("JAG_BEFORE", jag(vs))
    W = {v: vweights(v) for v in vs}; cx = float(CENTER[0])
    def mix(d, f):
        out = {}
        for k, x in d.items(): out[k] = out.get(k, 0) + x * f
        return out
    for _ in range(n_it):
        N = {}
        for v in vs:
            if rest_co[v, 2] > z_keep or not nb[v]: N[v] = W[v]; continue
            avg = {}
            for u in nb[v]:
                for k, x in W[u].items(): avg[k] = avg.get(k, 0) + x / len(nb[v])
            m = mix(W[v], 1 - a_)
            for k, x in avg.items(): m[k] = m.get(k, 0) + x * a_
            N[v] = m
        W = N
    pairs = [(HM[s + "UpperLeg"], HM[o + "UpperLeg"]) for s, o in (("Left", "Right"),)] + [(HM["LeftLowerLeg"], HM["RightLowerLeg"])]
    for v in vs:
        if rest_co[v, 2] > z_keep: continue
        f = sm((rest_co[v, 0] - cx + w2) / (2 * w2))   # +x 쪽이 L_
        d = dict(W[v])
        for lb, rb in pairs:
            tot = d.get(lb, 0) + d.get(rb, 0)
            if tot > 0: d[lb] = tot * f; d[rb] = tot * (1 - f)
        d = dict(sorted(((k, x) for k, x in d.items() if x > 0.005), key=lambda kv: -kv[1])[:4]); s = sum(d.values())
        set_weights(v, {k: x / s for k, x in d.items()})
    me.update(); vl.update()
    print("JAG_AFTER", jag(vs), "값", {"반복": n_it, "세기": a_, "가운데폭": w2, "윗단유지": round(z_keep, 3)})

if MODE == "다듬기": smooth_orig()
else: weights_63()
if MODE in ("고리", "사슬"):
    install(MODE == "사슬")
    arm.data.pose_position = 'POSE'; vl.update()
if MODE == "고리":
    acts = [x for x in bpy.data.actions if (ACTS is None and x.name.split("|")[-1].startswith("UAL_")) or (ACTS and x.name.split("|")[-1] in ACTS)]
    for x in acts: bake(x)
    arm.animation_data.action = None
    for p in arm.pose.bones:
        if p.name.startswith(PREFIX): p.location = (0, 0, 0)
arm.data.pose_position = 'POSE'; sc.frame_set(1)
bpy.context.preferences.filepaths.save_version = 0
r = bpy.ops.wm.save_as_mainfile(filepath=OUT, relative_remap=True); assert 'FINISHED' in r
print("SKIRT_DONE", MODE, OUT)
