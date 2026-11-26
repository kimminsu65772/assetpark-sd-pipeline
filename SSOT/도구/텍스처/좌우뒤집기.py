# 좌우뒤집기.py — 한쪽을 고친 텍스처를 3D 거울(x = 0)로 반대쪽에 옮겨 그린다(5-6, 대칭 부위는 한쪽을 고쳐 뒤집어 씀).
# 방법: 대상 조각의 칸마다 UV 삼각형을 찾아 3D 자리를 구하고, x를 뒤집은 자리에서 가장 가까운 면 위 점의 UV를 구해 원본 그림에서
#       쌍선형으로 읽어 온다. 3D x가 기준 쪽과 반대인 칸만 바꾼다(기준 쪽 칸과 가운데 선 위는 그대로). 메시는 바꾸지 않는다.
#       거울 자리가 메시에서 MAXD(m)보다 멀면(대칭이 아닌 곳) 그 칸은 바꾸지 않고 수를 센다.
# 두 단계: (1) Blender에서 대응표(바꿀 칸 → 원본 UV 자리)를 .npy로 쓴다(이 파일). (2) 시스템 파이썬에서 좌우뒤집기적용.py가 그림에 적용한다.
#       Blender 파이썬에는 PIL이 없고, Blender 이미지로 읽고 쓰면 색이 바뀔 수 있어 그림은 Blender 밖에서 다룬다.
# 사용: 블렌더실행.sh <blend> 좌우뒤집기.py -- <대응표.npy> <객체> <조각지도.npy> <조각 a,b> <기준 쪽 +x|-x> [--상자 x0,y0,x1,y1] [--최대거리 0.002] [--옮김 dx]
#       --옮김 dx: 뒤집지 않고 x로 dx(m)만큼 옮긴 자리에서 읽는다(눈동자 반사점처럼 좌우가 같은 쪽에 있어야 하는 무늬)
#       --상자는 그림 칸 좌표(왼쪽 위 0,0)로 바꿀 범위를 줄인다.
import bpy, sys, os
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

a = sys.argv[sys.argv.index("--") + 1:]
if len(a) < 5: raise SystemExit("사용: -- <대응표.npy> <객체> <조각지도> <조각들> <+x|-x> [--상자 ..] [--최대거리 ..]")
OUT, OBJ, LABP, IDS, SIDE = a[:5]
opt = dict(zip(a[5::2], a[6::2]))
if SIDE not in ("+x", "-x"): raise SystemExit(f"기준 쪽은 +x 또는 -x: {SIDE}")
lab = np.flipud(np.load(LABP))
H, W = lab.shape
ids = [int(v) for v in IDS.split(",")]
for i in ids:
    if not (lab == i).any(): raise SystemExit(f"조각 {i}이(가) 조각 지도에 없다")
box = [int(v) for v in opt["--상자"].split(",")] if "--상자" in opt else [0, 0, W, H]
MAXD = float(opt.get("--최대거리", 0.002))
sgn = 1.0 if SIDE == "+x" else -1.0
SHIFT = float(opt["--옮김"]) if "--옮김" in opt else None

o = bpy.data.objects[OBJ]; me = o.data; mw = o.matrix_world
uvl = me.uv_layers[__import__("os").environ.get("TEX_UV") or 0].data
me.calc_loop_triangles()
tris = me.loop_triangles
P = np.array([[tuple(mw @ me.vertices[v].co) for v in t.vertices] for t in tris])            # (T,3,3)
U = np.array([[tuple(uvl[l].uv) for l in t.loops] for t in tris]) * [W, -H] + [0, H]        # 그림 칸 좌표 (T,3,2)
bvh = BVHTree.FromPolygons([tuple(mw @ v.co) for v in me.vertices], [tuple(t.vertices) for t in tris])

def bary(p, a_, b_, c_):
    v0, v1, v2 = b_ - a_, c_ - a_, p - a_
    d00, d01, d11 = v0 @ v0, v0 @ v1, v1 @ v1; d20, d21 = v2 @ v0, v2 @ v1
    den = d00 * d11 - d01 * d01
    if abs(den) < 1e-20: return None
    v = (d11 * d20 - d01 * d21) / den; w = (d00 * d21 - d01 * d20) / den
    return np.array([1 - v - w, v, w])

rows = []; done = 0; far = 0; seen = np.zeros((H, W), bool)
for ti in range(len(tris)):
    u = U[ti]
    x0, y0 = np.floor(u.min(0)).astype(int); x1, y1 = np.ceil(u.max(0)).astype(int)
    x0, y0 = max(x0, box[0]), max(y0, box[1]); x1, y1 = min(x1, box[2]), min(y1, box[3])
    if x0 >= x1 or y0 >= y1: continue
    ys, xs = np.mgrid[y0:y1, x0:x1]; pc = np.stack([xs + 0.5, ys + 0.5], -1).reshape(-1, 2)
    # 2D 무게중심 좌표
    a_, b_, c_ = u; v0, v1 = b_ - a_, c_ - a_; den = v0[0] * v1[1] - v1[0] * v0[1]
    if abs(den) < 1e-9: continue
    d = pc - a_; l1 = (d[:, 0] * v1[1] - v1[0] * d[:, 1]) / den; l2 = (v0[0] * d[:, 1] - d[:, 0] * v0[1]) / den; l0 = 1 - l1 - l2
    inside = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
    for k in np.nonzero(inside)[0]:
        px, py = int(pc[k, 0]), int(pc[k, 1])
        if seen[py, px] or lab[py, px] not in ids: continue
        seen[py, px] = True
        p3 = l0[k] * P[ti, 0] + l1[k] * P[ti, 1] + l2[k] * P[ti, 2]
        if p3[0] * sgn >= 0: continue                     # 기준 쪽(과 가운데)은 그대로
        q = Vector((-p3[0], p3[1], p3[2])) if SHIFT is None else Vector((p3[0] + SHIFT, p3[1], p3[2]))
        loc, nrm, fi, dist = bvh.find_nearest(q)
        if loc is None or dist > MAXD: far += 1; continue
        bb = bary(np.array(loc), P[fi, 0], P[fi, 1], P[fi, 2])
        if bb is None: far += 1; continue
        su = bb @ U[fi]
        if lab[min(max(int(su[1]), 0), H - 1), min(max(int(su[0]), 0), W - 1)] not in ids: far += 1; continue
        rows.append((px, py, su[0], su[1])); done += 1
np.save(OUT, np.array(rows, np.float64))
print(f"좌우뒤집기 {OBJ} 조각{ids} 기준{SIDE} 상자{box}: 바꾼 칸 {done}, 거울 자리를 못 찾은 칸 {far}")
if done == 0: raise SystemExit("바꾼 칸이 0이다(조각·상자·기준 쪽을 확인)")
