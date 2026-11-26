# SmartUV조사.py — TRIPO Smart UV 결과 FBX를 입력 FBX와 비교하고 UV 배치를 잰다. 파일은 바꾸지 않는다(공통 도구).
# 출처: 01_캐릭터/온천_검사/04_Blender/스크립트/SmartUV조사_v001.py를 그대로 옮겼다(캐릭터 값이 없음). 그림은 같은 폴더의 그림공통.py로 찍는다.
# 1) 객체·정점·면·쿼드 수, 2) 크기 되돌리기(÷normalize_scale)와 방향 맞추기 뒤 정점 위치 차이,
# 3) UV: 조각 수, 0~1 범위, 겹침(2048 칸), 조각 사이 가장 좁은 간격(2048 칸), 차지 비율, 조각별 밀도,
# 4) 그림: UV 배치(조각 색), 3D 격자무늬·조각 색 여러 방향. 그림은 <출력폴더>/_tmp/ 에 낱장으로.
# 사용: SSOT/도구/블렌더실행.sh - SSOT/도구/SmartUV조사.py -- <입력.fbx> <결과.fbx> <normalize_scale> <출력폴더> [그림=1]
#   결과 파일에 파츠가 여럿이면 환경 변수 PART=<객체 이름>. 아래 각도는 UNDER=1일 때만 찍는다(검수 그림에는 따로 더한다).
import bpy, sys, os, json, math, colorsys
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
a = sys.argv[sys.argv.index("--") + 1:]
INP, RES, NS, OUT = os.path.abspath(a[0]), os.path.abspath(a[1]), float(a[2]), os.path.abspath(a[3])
DRAW = (a[4] if len(a) > 4 else "1") == "1"
TMP = os.path.join(OUT, "_tmp"); os.makedirs(TMP, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)

def load(path, tag):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    info = [{"이름": o.name, "종류": o.type, "위치": [round(v, 5) for v in o.location],
             "회전": [round(math.degrees(v), 3) for v in o.rotation_euler], "크기": [round(v, 5) for v in o.scale],
             "부모": o.parent.name if o.parent else None} for o in new]
    ms = [o for o in new if o.type == 'MESH']
    # 여러 파츠가 든 결과 파일(전체로 보낸 것)이면 환경변수 PART의 객체만 남긴다
    if tag == "결과" and os.environ.get("PART"):
        drop = [o for o in ms if o.name != os.environ["PART"]]
        ms = [o for o in ms if o.name == os.environ["PART"]]
        new = [o for o in new if o.type != 'MESH' or o.name == os.environ["PART"]]
        for o in drop: bpy.data.objects.remove(o)
    for o in ms:
        mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
        o.data.transform(mw); o.matrix_world = Matrix.Identity(4)
    for o in new:
        if o.type != 'MESH': bpy.data.objects.remove(o)
    assert len(ms) == 1, (tag, len(ms))
    ms[0].name = tag
    return ms[0], info

A, infoA = load(INP, "입력")
B, infoB = load(RES, "결과")
rep = {"입력객체": infoA, "결과객체": infoB}

def topo(o):
    me = o.data; s = np.array([len(p.vertices) for p in me.polygons])
    return {"정점": len(me.vertices), "면": len(me.polygons), "쿼드": int((s == 4).sum()), "삼각형": int((s == 3).sum()),
            "그외": int((s > 4).sum()), "UV층": [u.name for u in me.uv_layers], "재질": [m.name if m else None for m in me.materials],
            "사용자지정노멀": me.has_custom_normals}
rep["입력"] = topo(A); rep["결과"] = topo(B)

def co_of(o):
    c = np.zeros(len(o.data.vertices) * 3); o.data.vertices.foreach_get("co", c); return c.reshape(-1, 3)
ca, cb_raw = co_of(A), co_of(B)
rep["결과_범위_받은그대로"] = [cb_raw.min(0).round(5).tolist(), cb_raw.max(0).round(5).tolist()]
# 크기 되돌리기: (좌표 - 이동) ÷ scale. 이동은 모르므로 범위 중심을 맞춘다. 방향은 z축 90도 단위와 축 바꿈 후보 중 가장 가까운 것.
from mathutils import kdtree
kd = kdtree.KDTree(len(ca))
for i, v in enumerate(ca): kd.insert(v, i)
kd.balance()
cands = {}
for name, R in {
    "그대로": np.eye(3),
    "z+90": np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]]), "z-90": np.array([[0, 1, 0], [-1, 0, 0], [0, 0, 1]]),
    "z180": np.array([[-1, 0, 0], [0, -1, 0], [0, 0, 1]]),
    "x+90": np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]]), "x-90": np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]]),
}.items():
    cb = (cb_raw / NS) @ R.T
    cb = cb - (cb.min(0) + cb.max(0)) / 2 + (ca.min(0) + ca.max(0)) / 2
    d = np.array([kd.find(v)[2] for v in cb])
    cands[name] = (float(d.max()), float(np.median(d)), cb)
best = min(cands, key=lambda k: cands[k][0])
cb = cands[best][2]
rep["방향후보_최대거리mm"] = {k: round(v[0] * 1000, 3) for k, v in cands.items()}
rep["맞춘방향"] = best
d =np.array([kd.find(v)[2] for v in cb]); idx = np.array([kd.find(v)[1] for v in cb])
rep["정점거리mm"] = {"최대": round(float(d.max()) * 1000, 4), "중앙": round(float(np.median(d)) * 1000, 4),
                  "0.01mm넘는정점": int((d > 1e-5).sum())}
rep["크기비_입력대결과"] = (np.ptp(ca, 0) / np.maximum(np.ptp(cb, 0), 1e-9)).round(6).tolist()
rep["정점순서같음"] = bool(len(ca) == len(cb) and (idx == np.arange(len(cb))).all())
rep["입력정점중_대응안된것"] = int(len(ca) - len(set(idx.tolist())))
# 면 대응: 정점 대응으로 면 정점 집합을 비교
fa = {frozenset(p.vertices) for p in A.data.polygons}
fb = [frozenset(int(idx[v]) for v in p.vertices) for p in B.data.polygons]
rep["결과면중_입력에같은면있음"] = int(sum(1 for f in fb if f in fa))
# 결과 메시를 입력 자리로 옮겨 둔다(그림용)
B.data.vertices.foreach_set("co", cb.ravel()); B.data.update()

# ---- UV ----
me = B.data; uvl = me.uv_layers.active.data
nl = len(me.loops)
uv = np.zeros(nl * 2); uvl.foreach_get("uv", uv); uv = uv.reshape(nl, 2)
lv = np.zeros(nl, dtype=np.int64); me.loops.foreach_get("vertex_index", lv)
rep["UV범위"] = [uv.min(0).round(5).tolist(), uv.max(0).round(5).tolist()]
# 조각: 같은 정점 + 같은 UV인 모서리를 잇는다
def find(p, x):
    while p[x] != x: p[x] = p[p[x]]; x = p[x]
    return x
key = np.concatenate([lv[:, None], np.round(uv * 1e6)], axis=1)
_, kid = np.unique(key, axis=0, return_inverse=True); kid = kid.ravel()
par = list(range(kid.max() + 1))
for p in me.polygons:
    ks = [kid[l] for l in p.loop_indices]
    r0 = find(par, ks[0])
    for k in ks[1:]: par[find(par, k)] = r0
root = np.array([find(par, k) for k in range(len(par))])
_, isl_of_key = np.unique(root, return_inverse=True)
poly_isl = np.array([isl_of_key[kid[p.loop_start]] for p in me.polygons])
nis = int(poly_isl.max() + 1)
me.calc_loop_triangles()
tri = np.array([t.loops[:] for t in me.loop_triangles]); tpoly = np.array([t.polygon_index for t in me.loop_triangles])
tisl = poly_isl[tpoly]
P = uv[tri]; Q = cb[lv[tri]]
sgn = (P[:, 1, 0] - P[:, 0, 0]) * (P[:, 2, 1] - P[:, 0, 1]) - (P[:, 2, 0] - P[:, 0, 0]) * (P[:, 1, 1] - P[:, 0, 1])
auv = 0.5 * np.abs(sgn); a3 = 0.5 * np.linalg.norm(np.cross(Q[:, 1] - Q[:, 0], Q[:, 2] - Q[:, 0]), axis=1)
iuv = np.bincount(tisl, auv, nis); i3 = np.bincount(tisl, a3, nis); ifc = np.bincount(poly_isl, minlength=nis)
# 뒤집힌 삼각형(조각 안에서 다수와 반대 방향)
flip = 0
for i in range(nis):
    s = sgn[tisl == i]; maj = np.sign(np.sum(np.sign(s)))
    flip += int((np.sign(s) == -maj).sum())
rep["UV뒤집힌삼각형"] = flip
dens = np.sqrt(iuv / np.maximum(i3, 1e-12))
gdens = math.sqrt(iuv.sum() / i3.sum())
# 2048 칸 래스터
N = 2048; idm = np.full((N, N), -1, np.int32); cnt = np.zeros((N, N), np.int16); ovp = {}
for t in range(len(tri)):
    x = P[t, :, 0] * N; y = P[t, :, 1] * N
    x0, x1 = int(max(0, math.floor(x.min()))), int(min(N - 1, math.ceil(x.max())))
    y0, y1 = int(max(0, math.floor(y.min()))), int(min(N - 1, math.ceil(y.max())))
    if x1 < x0 or y1 < y0: continue
    gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + .5, np.arange(y0, y1 + 1) + .5)
    dd = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
    if abs(dd) < 1e-12: continue
    w0 = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / dd
    w1 = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / dd
    ins = (w0 >= 0) & (w1 >= 0) & (w0 + w1 <= 1)
    strict = (w0 > 1e-6) & (w1 > 1e-6) & (w0 + w1 < 1 - 1e-6)
    sub = idm[y0:y1 + 1, x0:x1 + 1]
    hit = strict & (cnt[y0:y1 + 1, x0:x1 + 1] > 0)
    if hit.any():
        for o_ in np.unique(sub[hit]):
            k_ = (int(min(o_, tisl[t])), int(max(o_, tisl[t])))
            ovp[k_] = ovp.get(k_, 0) + int((hit & (sub == o_)).sum())
    sub[ins] = tisl[t]
    cnt[y0:y1 + 1, x0:x1 + 1] += strict
rep["UV차지비율"] = round(float((idm >= 0).mean()), 4)
rep["겹친칸_2048"] = int((cnt > 1).sum())
# 겹친 조각 짝(같은 번호 짝 = 한 조각 안에서 접혀 겹침). 번호는 아래 "조각" 목록의 번호
rep["겹친조각짝"] = [{"짝": list(k), "칸": v} for k, v in sorted(ovp.items(), key=lambda kv: -kv[1])]
# 간격: 조각마다 다른 조각까지 가장 가까운 칸 거리(가로세로 0~24칸 이동으로 찾음)
gap = {}
for s in range(1, 25):
    for dx, dy in [(s, 0), (0, s)]:
        a1 = idm[:N - dy, :N - dx]; a2 = idm[dy:, dx:]
        m = (a1 >= 0) & (a2 >= 0) & (a1 != a2)
        if m.any():
            for i in np.unique(np.concatenate([a1[m], a2[m]])):
                gap.setdefault(int(i), s - 1)
rep["가장좁은간격_2048칸"] = min(gap.values()) if gap else ">23"
rep["간격8칸미만조각수"] = int(sum(1 for v in gap.values() if v < 8))
# 조각 목록(넓은 순)
order = np.argsort(-i3)
cen = np.zeros((nis, 3))
for i in range(nis): cen[i] = cb[np.unique(lv[tri[tisl == i]].ravel())].mean(0)
rep["조각수"] = nis
rep["조각"] = [{"번호": int(i), "면": int(ifc[i]), "3D넓이cm2": round(float(i3[i]) * 1e4, 2), "UV넓이": round(float(iuv[i]), 5),
              "밀도비": round(float(dens[i] / gdens), 3), "중심": cen[i].round(3).tolist(), "가장좁은간격": gap.get(int(i))} for i in order]
json.dump(rep, open(os.path.join(OUT, "조사수치.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for k in ["입력", "결과", "맞춘방향", "방향후보_최대거리mm", "정점거리mm", "크기비_입력대결과", "정점순서같음", "입력정점중_대응안된것",
          "결과면중_입력에같은면있음", "UV범위", "조각수", "UV차지비율", "겹친칸_2048", "겹친조각짝", "UV뒤집힌삼각형", "가장좁은간격_2048칸", "간격8칸미만조각수"]:
    print(k, rep[k])
print("결과객체", rep["결과객체"])
print("넓은조각10", [(c["면"], c["3D넓이cm2"], c["밀도비"], c["중심"]) for c in rep["조각"][:10]])
print("작은조각", sum(1 for c in rep["조각"] if c["면"] <= 3), "개(면 3 이하)")
if not DRAW:
    print("완료"); sys.exit(0)

# ---- 그림 ----
import 그림공통 as G
# 조각 색: 넓은 순서대로 색상환을 돌며 고른다. 좌우 짝은 같은 넓이라 이웃 번호가 되어 색이 다르다.
rank = np.empty(nis, int); rank[order] = np.arange(nis)
def colr(i):
    h = (rank[i] * 0.618034) % 1.0
    return colorsys.hsv_to_rgb(h, 0.65, 0.95)
pal = np.array([colr(i) for i in range(nis)])
# (1) UV 배치: 2048 칸 지도 → 1024로 줄여 저장. 배경 검정, 조각 색, 간격 8칸 미만 조각은 흰 테두리 대신 목록으로 알린다.
img = np.zeros((N, N, 3)); m = idm >= 0; img[m] = pal[idm[m]]
img[cnt > 1] = 1.0   # 겹친 칸은 흰색
# 겹친 조각은 3D 그림에서도 흰색으로 칠한다
ovi = sorted({i for k in ovp for i in k})
rep_ov_centers = {int(i): cen[i].round(3).tolist() for i in ovi}
print("겹친조각 중심", rep_ov_centers, "면", {int(i): int(ifc[i]) for i in ovi})
for i in ovi: pal[i] = (1.0, 1.0, 1.0)
small = img[::2, ::2]
im = bpy.data.images.new("uvmap", 1024, 1024)
im.pixels = np.concatenate([small, np.ones((1024, 1024, 1))], axis=2).ravel()
im.filepath_raw = os.path.join(TMP, "UV배치_조각색.png"); im.file_format = 'PNG'; im.save()
# (2) 3D: 조각 색(모서리 색) / 격자무늬
A.hide_render = True
ca_ = me.color_attributes.new("조각색", 'BYTE_COLOR', 'CORNER')
col = np.zeros((nl, 4)); col[:, 3] = 1
for p in me.polygons:
    for l in p.loop_indices: col[l, :3] = pal[poly_isl[p.index]]
ca_.data.foreach_set("color", col.ravel()); me.color_attributes.active_color = ca_
grid = bpy.data.images.new("격자", 1024, 1024); grid.generated_type = 'UV_GRID'
mat = bpy.data.materials.new("격자재질"); mat.use_nodes = True
tn = mat.node_tree.nodes.new("ShaderNodeTexImage"); tn.image = grid
bs = mat.node_tree.nodes["Principled BSDF"]; mat.node_tree.links.new(tn.outputs[0], bs.inputs[0])
me.materials.clear(); me.materials.append(mat)
center = ((cb.min(0) + cb.max(0)) / 2).tolist(); scale = float(np.ptp(cb, 0).max()) * 1.25
views = [("앞", 0, 0), ("앞_오른쪽30", 30, 0), ("앞_왼쪽30", -30, 0), ("오른쪽에서", 90, 0), ("왼쪽에서", -90, 0),
         ("뒤", 180, 0), ("앞위25", 0, 25), ("뒤위25", 180, 25)]
# 아래에서 올려다보는 각도는 기모노 속 그림이 되므로 기본으로 찍지 않는다. 얼굴·헤어처럼 기모노가 없는 파츠만 UNDER=1로 켠다.
if os.environ.get("UNDER") == "1": views.append(("앞아래25", 0, -25))
for mode, ct in [("조각색", 'VERTEX'), ("격자", 'TEXTURE')]:
    G.setup(res=330, light='STUDIO', color_type=ct)
    for n, az, el in views:
        G.shoot(os.path.join(TMP, f"{mode}_{n}.png"), center, G.dirvec(az, el), scale)
json.dump({"보기": [v[0] for v in views]}, open(os.path.join(TMP, "보기.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("그림 완료")
