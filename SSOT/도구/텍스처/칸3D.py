# 칸3D.py — 조각 안 그림 칸마다 3D 자리(월드 좌표)를 구해 .npy(px, py, x, y, z)로 쓴다(5-6). Blender에서 돈다.
# 여러 조각에 걸친 선을 3D에서 한 번에 그릴 때(3D선그리기.py) 쓴다. 메시·그림은 바꾸지 않는다.
# 사용: 블렌더실행.sh <blend> 칸3D.py -- <출력.npy> <객체> <조각지도.npy> <조각 a,b> [--상자 x0,y0,x1,y1]
import bpy, sys
import numpy as np

a = sys.argv[sys.argv.index("--") + 1:]
if len(a) < 4: raise SystemExit("사용: -- <출력.npy> <객체> <조각지도.npy> <조각들> [--상자 ..]")
OUT, OBJ, LABP, IDS = a[:4]
opt = dict(zip(a[4::2], a[5::2]))
lab = np.flipud(np.load(LABP)); H, W = lab.shape
ids = [int(v) for v in IDS.split(",")]
for i in ids:
    if not (lab == i).any(): raise SystemExit(f"조각 {i}이(가) 조각 지도에 없다")
box = [int(v) for v in opt["--상자"].split(",")] if "--상자" in opt else [0, 0, W, H]
o = bpy.data.objects[OBJ]; me = o.data; mw = o.matrix_world
uvl = me.uv_layers[__import__("os").environ.get("TEX_UV") or 0].data
me.calc_loop_triangles()
rows = []; seen = np.zeros((H, W), bool)
for t in me.loop_triangles:
    U = np.array([tuple(uvl[l].uv) for l in t.loops]) * [W, -H] + [0, H]
    P = np.array([tuple(mw @ me.vertices[v].co) for v in t.vertices])
    x0, y0 = np.floor(U.min(0)).astype(int); x1, y1 = np.ceil(U.max(0)).astype(int)
    x0, y0 = max(x0, box[0]), max(y0, box[1]); x1, y1 = min(x1, box[2]), min(y1, box[3])
    if x0 >= x1 or y0 >= y1: continue
    ys, xs = np.mgrid[y0:y1, x0:x1]; pc = np.stack([xs + 0.5, ys + 0.5], -1).reshape(-1, 2)
    a_, b_, c_ = U; v0, v1 = b_ - a_, c_ - a_; den = v0[0] * v1[1] - v1[0] * v0[1]
    if abs(den) < 1e-9: continue
    d = pc - a_; l1 = (d[:, 0] * v1[1] - v1[0] * d[:, 1]) / den; l2 = (v0[0] * d[:, 1] - d[:, 0] * v0[1]) / den; l0 = 1 - l1 - l2
    ins = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
    for k in np.nonzero(ins)[0]:
        px, py = int(pc[k, 0]), int(pc[k, 1])
        if seen[py, px] or lab[py, px] not in ids: continue
        seen[py, px] = True
        p3 = l0[k] * P[0] + l1[k] * P[1] + l2[k] * P[2]
        rows.append((px, py, p3[0], p3[1], p3[2]))
if not rows: raise SystemExit("칸이 0이다(조각·상자를 확인)")
np.save(OUT, np.array(rows, np.float64))
print(f"칸3D {OBJ} 조각{ids} 상자{box}: {len(rows)}칸")
