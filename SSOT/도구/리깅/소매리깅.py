# 소매리깅.py — 넓은 소매(기모노 소매 주머니 등)의 가중치를 바꾸거나 소매 전용 사슬 뼈를 넣는 공용 도구. 소매 안쪽이 몸통을 지나가는 것을 줄이려는 것.
# 실행: SSOT/도구/블렌더실행.sh <입력.blend> SSOT/도구/리깅/소매리깅.py -- <리깅설정.json> <방식> <출력.blend> [그림.png]
#   방식: 안쪽가중치 = 팔 줄기보다 아래로 늘어진 소매 중 몸 쪽을 향한 면의 가중치 일부를 몸쪽 뼈(설정 "몸쪽뼈", 예: 가슴·빗장뼈)로 옮긴다. 팔보다 늦게 따라오게(겨드랑이 후보 B)
#         사슬     = 소매 주머니에 팔 줄기에서 아래로 늘어진 사슬 뼈(한쪽 "줄" 개 × "마디" 개)를 넣고, 팔 줄기 아래 정점을 깊이에 따라 사슬 뼈로 옮긴다. 굽지 않는다(움직임은 게임 안 물리, 겨드랑이 후보 C)
#   그림.png를 주면 바뀐 몫(옮긴 가중치 비율)을 빨강으로 칠한 앞·뒤·옆 그림을 찍는다.
# 소매 = 설정 "파츠"에서 가장 큰 이어진 조각 중 기본 자세 |x| > 위팔 뼈 머리 |x| + "경계여유"(겨드랑이재기와 같은 기준). 좌우: Humanoid LeftUpperArm 쪽 = 뼈대 공간 +x.
# 팔 줄기 = 기본 자세의 위팔 머리 → 손 머리 직선. "깊이" = 앞뒤(y)를 뺀 x·z 면에서 줄기 아래쪽으로 떨어진 거리.
# 형태·정점 순서·면·UV는 바꾸지 않는다. 소매 밖 정점 가중치는 그대로. 뼈대와 파츠의 객체 변환은 단위행렬만 지원(아니면 멈춤).
# 설정(리깅설정.json의 "소매"): 파츠, 경계여유, 반복(몫 고르게 섞기 횟수),
#   안쪽가중치{세기(최대 옮길 몫), 깊이폭(이 깊이에서 몫이 다 참), 몸쪽뼈{"뼈 이름 또는 <좌우>Clavicle 꼴 Humanoid 이름": 비율}}
#   사슬{줄(한쪽 사슬 수), 마디(사슬마다 뼈 수), 줄기구간[시작, 끝](팔 줄기 위 비율, 사슬 뿌리를 놓을 구간), 깊이폭(이 깊이에서 사슬 몫이 1), 세기}
import bpy, sys, json, math, os, numpy as np
from mathutils import Vector, Matrix
from mathutils.kdtree import KDTree
sys.dont_write_bytecode = True
a = sys.argv[sys.argv.index("--") + 1:]; cfg = json.load(open(a[0], encoding="utf-8")); MODE = a[1]; OUT = os.path.abspath(a[2]); PNG = os.path.abspath(a[3]) if len(a) > 3 else None
assert MODE in ("안쪽가중치", "사슬"), MODE
SL = cfg["소매"]; HM = cfg["humanoid"]; sc = bpy.context.scene; vl = bpy.context.view_layer
arm = bpy.data.objects[cfg["armature"]]; up = bpy.data.objects[SL["파츠"]]; me = up.data
for _o in (arm, up):
    assert all(abs(_o.matrix_world[i][j] - (1.0 if i == j else 0.0)) < 1e-6 for i in range(4) for j in range(4)), "%s의 객체 변환이 단위행렬이 아니다(지원하지 않음)" % _o.name
vl.objects.active = arm
if bpy.context.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
arm.data.pose_position = 'REST'; vl.update()

def islands(m):
    par = list(range(len(m.vertices)))
    def f(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    for e in m.edges:
        p, q = f(e.vertices[0]), f(e.vertices[1])
        if p != q: par[p] = q
    kd = KDTree(len(m.vertices))
    for i, v in enumerate(m.vertices): kd.insert(v.co, i)
    kd.balance()
    for i, v in enumerate(m.vertices):
        for _, j, _ in kd.find_range(v.co, 1e-6):
            p, q = f(i), f(j)
            if p != q: par[p] = q
    g = {}
    for i in range(len(m.vertices)): g.setdefault(f(i), []).append(i)
    return sorted(g.values(), key=len, reverse=True)

CO = np.array([v.co[:] for v in me.vertices]); NO = np.array([v.normal[:] for v in me.vertices])
big = np.array(islands(me)[0])
B = lambda h: arm.data.bones[HM[h]]
ua = abs(B("LeftUpperArm").head_local.x); sleeve = big[np.abs(CO[big, 0]) > ua + SL["경계여유"]]
# 이웃(모서리) 목록: 몫을 고르게 섞을 때 쓴다(같은 자리 정점은 묶음)
nb = [set() for _ in me.vertices]
for e in me.edges: i, j = e.vertices; nb[i].add(j); nb[j].add(i)
kd = KDTree(len(me.vertices))
for i, v in enumerate(me.vertices): kd.insert(v.co, i)
kd.balance()
for i, v in enumerate(me.vertices):
    for _, j, _ in kd.find_range(v.co, 1e-6):
        if j != i: nb[i].add(j)
def smooth(share, idx, it):
    s = share.copy(); S = set(idx.tolist())
    for _ in range(it):
        t = s.copy()
        for i in idx:
            n = [j for j in nb[i] if j in S]
            if n: t[i] = 0.5 * s[i] + 0.5 * np.mean(s[n])
        s = t
    return s

def side_info(side):   # side = "Left"/"Right"
    sg = 1.0 if side == "Left" else -1.0
    h0 = B(side + "UpperArm").head_local; h1 = B(side + "Hand").head_local
    p0 = np.array([h0.x, h0.z]); p1 = np.array([h1.x, h1.z]); u = (p1 - p0) / np.linalg.norm(p1 - p0)
    dn = np.array([u[1], -u[0]]) if sg > 0 else np.array([-u[1], u[0]])   # 줄기에 수직, 아래쪽
    if dn[1] > 0: dn = -dn
    idx = sleeve[np.sign(CO[sleeve, 0]) == sg]
    xz = CO[idx][:, [0, 2]] - p0
    t = xz @ u / np.linalg.norm(p1 - p0); depth = xz @ dn
    return sg, idx, t, depth, p0, p1, u, dn

def add_w(vidx, bone, w):
    g = up.vertex_groups.get(bone) or up.vertex_groups.new(name=bone); g.add([int(vidx)], float(w), 'ADD')
def move_share(i, share, targets):   # targets: {뼈: 비율}. 정점 i의 기존 가중치를 (1-share)배로 줄이고 share를 targets에 나눈다
    if share <= 1e-4: return
    gn = up.vertex_groups
    for gg in list(me.vertices[i].groups):
        name = gn[gg.group].name
        gn[gg.group].add([int(i)], gg.weight * (1 - share), 'REPLACE')
    tot = sum(targets.values())
    for bn, r in targets.items(): add_w(i, bn, share * r / tot)

SHARE = np.zeros(len(me.vertices)); report = []
if MODE == "안쪽가중치":
    P = SL["안쪽가중치"]
    for side in ("Left", "Right"):
        sg, idx, t, depth, *_ = side_info(side)
        inner = np.clip((1 - NO[idx, 0] * sg) / 2, 0, 1)   # 노멀이 몸 쪽(안쪽)을 향하면 1, 바깥이면 0, 앞뒤를 향하면 0.5
        s = P["세기"] * np.clip(depth / P["깊이폭"], 0, 1) * inner
        SHARE[idx] = s
        SHARE = smooth(SHARE, idx, SL["반복"])
        tg = {}
        for k, r in P["몸쪽뼈"].items():
            bn = HM[side + k] if (side + k) in HM else HM.get(k, k); tg[bn] = r
        for i in idx: move_share(i, SHARE[i], tg)
        report.append("%s: 소매 정점 %d, 옮긴 몫>0.05 %d, >0.3 %d, 최대 %.2f, 대상 %s" % (side, len(idx), (SHARE[idx] > .05).sum(), (SHARE[idx] > .3).sum(), SHARE[idx].max(), tg))
else:
    P = SL["사슬"]; NC, NS = int(P["줄"]), int(P["마디"])
    bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); vl.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT'); eb = arm.data.edit_bones
    chains = {}
    for side in ("Left", "Right"):
        sg, idx, t, depth, p0, p1, u, dn = side_info(side)
        L = np.linalg.norm(p1 - p0); ts = np.linspace(P["줄기구간"][0], P["줄기구간"][1], NC)
        ymid = float(np.median(CO[idx, 1]))
        chains[side] = []
        for c, tc in enumerate(ts):
            root2 = p0 + u * L * tc
            near = idx[np.abs(t - tc) < 0.5 / NC]
            dmax = float(np.max((CO[near][:, [0, 2]] - p0) @ dn)) if len(near) else 0.05
            joints = [root2 + dn * dmax * k / NS for k in range(NS + 1)]
            # 부모: 뿌리가 팔꿈치 앞이면 위팔, 뒤면 아래팔
            el = B(side + "LowerArm").head_local; tel = ((np.array([el.x, el.z]) - p0) @ u) / L
            parent = eb[HM[side + ("UpperArm" if tc < tel else "LowerArm")]]
            prev = parent; names = []
            for k in range(NS):
                nm = "Sleeve_%s_%d_%d" % (side[0], c, k); b = eb.new(nm)
                b.head = Vector((joints[k][0], ymid, joints[k][1])); b.tail = Vector((joints[k + 1][0], ymid, joints[k + 1][1]))
                b.parent = prev; b.use_connect = k > 0; b.use_deform = True; prev = b; names.append(nm)
            chains[side].append((tc, names, joints))
    bpy.ops.object.mode_set(mode='OBJECT')
    for side in ("Left", "Right"):
        sg, idx, t, depth, p0, p1, u, dn = side_info(side)
        ch = chains[side]; tcs = np.array([x[0] for x in ch])
        s = P["세기"] * np.clip(depth / P["깊이폭"], 0, 1); SHARE[idx] = s; SHARE = smooth(SHARE, idx, SL["반복"])
        for n, i in enumerate(idx):
            sh = SHARE[i]
            if sh <= 1e-4: continue
            # 사슬 사이: 줄기 위 위치 t로 가까운 두 사슬에 선형으로, 사슬 안: 깊이로 마디에 선형으로
            tt = float(np.clip(t[n], tcs[0], tcs[-1])); c1 = int(np.searchsorted(tcs, tt)); c1 = min(max(c1, 1), len(tcs) - 1) if len(tcs) > 1 else 0
            if len(tcs) > 1: c0 = c1 - 1; wc1 = (tt - tcs[c0]) / (tcs[c1] - tcs[c0]); pairs = [(c0, 1 - wc1), (c1, wc1)]
            else: pairs = [(0, 1.0)]
            tg = {}
            for c, wc in pairs:
                _, names, joints = ch[c]; dl = np.linalg.norm(np.array(joints[-1]) - np.array(joints[0]))
                fk = float(np.clip(depth[n] / max(dl, 1e-6), 0, 1)) * NS; k = min(int(fk), NS - 1)
                tg[names[k]] = tg.get(names[k], 0) + wc
            move_share(i, sh, tg)
        report.append("%s: 사슬 %d줄 × %d마디(뿌리 줄기 비율 %s), 소매 정점 %d, 옮긴 몫>0.05 %d, 최대 %.2f" % (side, NC, NS, [round(x, 2) for x in tcs], len(idx), (SHARE[idx] > .05).sum(), SHARE[idx].max()))
# 가중치 합 1로 맞추기(소매 정점만)
gn = up.vertex_groups
for i in sleeve:
    tot = sum(g.weight for g in me.vertices[i].groups)
    if tot > 0 and abs(tot - 1) > 1e-5:
        for g in list(me.vertices[i].groups): gn[g.group].add([int(i)], g.weight / tot, 'REPLACE')
print("SLEEVE", MODE, "뼈 수", len(arm.data.bones), "|", " ; ".join(report), flush=True)
if PNG:
    at = me.color_attributes.new("소매몫", 'FLOAT_COLOR', 'POINT')
    for i, x in enumerate(SHARE): at.data[i].color = (1.0, 1 - x, 1 - x, 1)
    me.color_attributes.active_color = at; me.color_attributes.render_color_index = list(me.color_attributes).index(at)
    hide = {o.name: o.hide_render for o in sc.objects}
    for o in sc.objects: o.hide_render = o.name != up.name
    r = sc.render; r.engine = 'BLENDER_WORKBENCH'; r.resolution_x = r.resolution_y = 500; sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'VERTEX'; sh.show_cavity = True
    cd = bpy.data.cameras.new("c"); cd.type = 'ORTHO'; cd.ortho_scale = 0.45; cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam); sc.camera = cam
    tiles = []; ctr = Vector((0, float(np.median(CO[big, 1])), float(np.median(CO[sleeve, 2]))))
    for yaw, pitch in ((0, 0), (180, 0), (-90, 0), (-45, -30)):
        y, p = math.radians(yaw), math.radians(pitch); d = Vector((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p)))
        cam.location = ctr + d * 5; cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        pth = PNG + "_t.png"; r.filepath = pth; bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(pth); tiles.append(np.array(im.pixels[:], dtype=np.float32).reshape(500, 500, 4)); bpy.data.images.remove(im); os.remove(pth)
    sheet = np.concatenate([np.concatenate(tiles[2:], 1), np.concatenate(tiles[:2], 1)], 0)
    o = bpy.data.images.new("s", 1000, 1000, alpha=True); o.pixels = sheet.ravel(); o.filepath_raw = PNG; o.file_format = 'PNG'; o.save()
    bpy.data.objects.remove(cam); bpy.data.cameras.remove(cd); me.color_attributes.remove(me.color_attributes["소매몫"])
    for o in sc.objects: o.hide_render = hide.get(o.name, o.hide_render)
    print("SLEEVE_PNG", PNG)
arm.data.pose_position = 'POSE'
bpy.context.preferences.filepaths.save_version = 0
r = bpy.ops.wm.save_as_mainfile(filepath=OUT, relative_remap=True); assert 'FINISHED' in r
print("SLEEVE_DONE", OUT)
