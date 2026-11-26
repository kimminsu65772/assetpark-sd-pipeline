# 검사자료뽑기.py — 텍스처·메시 자동 검사(텍스처검사.py)가 쓸 자료를 작업본에서 뽑는다. Blender에서 돈다. 작업본은 저장하지 않는다.
# 파츠마다 <출력>/<파츠>.npz 하나:
#   pos (H,W,3) float32  조각 안 그림 칸의 3D 자리(월드, m). 조각 밖은 NaN. 그림 칸 좌표는 왼쪽 위가 (0,0)
#   seam (E,16)          이음매 모서리: 3D에서는 한 모서리인데 UV에서 두 자리로 갈린 것. 열: A끝0 xy, A끝1 xy, B끝0 xy, B끝1 xy(그림 칸, 같은 정점끼리 짝), 3D 끝0 xyz, 3D 끝1 xyz, 0, 0
#   bnd (E,10)           열린 가장자리(면 하나만 쓰는 모서리): UV 끝0 xy, 끝1 xy, 3D 끝0 xyz, 끝1 xyz
#   mir (K,4)            좌우 짝: 칸 (px,py)의 3D 자리를 x = 0으로 뒤집은 자리에서 가장 가까운 겉면 점의 그림 자리 (qx,qy). 2칸 간격, |x| > 2mm, 거리 MAXD 안만
#   tri3d (T,) float     삼각형의 3D 넓이(m²), triuv (T,) 그림 칸 넓이, trip (T,) 면 번호 → 텍셀 밀도용
#   그리고 mesh.json(구멍·떠 있는 조각·뒤집힌 노멀 후보)을 함께 쓴다.
# 조각 지도는 SSOT/도구/텍스처/조각지도.py가 낸 것을 쓴다(같은 UV 층).
#   거울면: x = MX 평면. --거울x 자동(기본)이면 정점을 뒤집었을 때 가장 많이 맞는 x(교복 사무라이는 x 0.04 부근에 서 있다). 값은 npz의 mx와 mesh.json에 남긴다.
# 사용: 블렌더실행.sh <작업본.blend> 검사자료뽑기.py -- <출력폴더> <조각지도 폴더> [--파츠 a,b] [--크기 2048] [--거울최대 0.004] [--거울x 자동|숫자]
#   UV 층은 환경변수 TEX_UV(없으면 첫 번째 층), 파츠 이름은 TEX_PARTS 또는 --파츠(SSOT/도구/텍스처/와 같음).
import bpy, sys, os, json
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

a = sys.argv[sys.argv.index("--") + 1:]
if len(a) < 2: raise SystemExit("사용: -- <출력폴더> <조각지도 폴더> [--파츠 a,b] [--크기 2048] [--거울최대 0.004]")
OUT, MAPD = os.path.abspath(a[0]), os.path.abspath(a[1]); opt = dict(zip(a[2::2], a[3::2]))
NAMES = (opt.get("--파츠") or os.environ.get("TEX_PARTS") or "파츠_헤어,파츠_얼굴,파츠_상체,파츠_하체").split(",")
N = int(opt.get("--크기", 2048)); MAXD = float(opt.get("--거울최대", 0.004))
os.makedirs(OUT, exist_ok=True)
UVL = os.environ.get("TEX_UV") or 0
meshrep = {}
if opt.get("--거울x", "자동") == "자동":
    xs_all = np.concatenate([np.array([(bpy.data.objects[n].matrix_world @ v.co).x for v in bpy.data.objects[n].data.vertices]) for n in NAMES if n in bpy.data.objects])
    # 정점을 x = c로 뒤집었을 때 3mm 안에 정점이 있는 비율이 가장 큰 c(중앙값 ±8cm를 1mm, 다시 0.1mm 간격으로)
    from mathutils.kdtree import KDTree
    VA = np.concatenate([np.array([tuple(bpy.data.objects[n].matrix_world @ v.co) for v in bpy.data.objects[n].data.vertices]) for n in NAMES if n in bpy.data.objects])
    kd = KDTree(len(VA))
    for i, v in enumerate(VA): kd.insert(v, i)
    kd.balance()
    smp = VA[np.linspace(0, len(VA) - 1, min(3000, len(VA))).astype(int)]
    def score(c): return sum(1 for v in smp if kd.find((2 * c - v[0], v[1], v[2]))[2] < 0.003)
    m0 = float(np.median(xs_all)); best = max(np.arange(m0 - 0.08, m0 + 0.08, 0.001), key=score)
    MX = float(max(np.arange(best - 0.001, best + 0.001, 0.0001), key=score))
    print(f"거울면 찾기: 뒤집어 맞는 정점 {score(MX)}/{len(smp)}")
else: MX = float(opt["--거울x"])
print(f"거울면 x = {MX:.4f}")

for name in NAMES:
    if name not in bpy.data.objects: raise SystemExit(f"객체가 없다: {name}")
    o = bpy.data.objects[name]; me = o.data; mw = o.matrix_world
    lp = os.path.join(MAPD, f"{name}_조각지도.npy")
    if not os.path.exists(lp): raise SystemExit(f"조각 지도가 없다: {lp}")
    lab = np.flipud(np.load(lp)); H, W = lab.shape
    if (H, W) != (N, N): raise SystemExit(f"{name}: 조각 지도 크기 {lab.shape}가 --크기 {N}과 다르다")
    me.calc_loop_triangles()
    nl = len(me.loops)
    uv = np.zeros(nl * 2, np.float64); me.uv_layers[UVL].data.foreach_get("uv", uv); uv = uv.reshape(-1, 2)
    UVpx = uv * [W, -H] + [0, H]                                   # 루프마다 그림 칸 좌표
    V = np.array([tuple(mw @ v.co) for v in me.vertices], np.float64)
    tris = me.loop_triangles
    TL = np.array([t.loops[:] for t in tris], np.int64); TV = np.array([t.vertices[:] for t in tris], np.int64)
    TP = np.array([t.polygon_index for t in tris], np.int64)
    P3 = V[TV]; U2 = UVpx[TL]
    # 1) 칸마다 3D 자리
    pos = np.full((H, W, 3), np.nan, np.float32)
    for ti in range(len(TL)):
        u = U2[ti]
        x0, y0 = np.floor(u.min(0)).astype(int); x1, y1 = np.ceil(u.max(0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, W), min(y1, H)
        if x0 >= x1 or y0 >= y1: continue
        ys, xs = np.mgrid[y0:y1, x0:x1]; pc = np.stack([xs + 0.5, ys + 0.5], -1).reshape(-1, 2)
        a_, b_, c_ = u; v0, v1 = b_ - a_, c_ - a_; den = v0[0] * v1[1] - v1[0] * v0[1]
        if abs(den) < 1e-9: continue
        d = pc - a_; l1 = (d[:, 0] * v1[1] - v1[0] * d[:, 1]) / den; l2 = (v0[0] * d[:, 1] - d[:, 0] * v0[1]) / den; l0 = 1 - l1 - l2
        ins = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
        if not ins.any(): continue
        p3 = l0[ins, None] * P3[ti, 0] + l1[ins, None] * P3[ti, 1] + l2[ins, None] * P3[ti, 2]
        px = pc[ins, 0].astype(int); py = pc[ins, 1].astype(int)
        pos[py, px] = p3
    # 조각 안인데 칸 중심이 삼각형에 안 걸린 가장자리 칸(조각지도는 0.71칸 너그러움). 검사 쪽에서 가까운 칸 자리로 메운다
    miss = (lab > 0) & np.isnan(pos[..., 0])
    # 2) 모서리: 이음매와 열린 가장자리
    edge = {}
    for p in me.polygons:
        ls = list(p.loop_indices)
        for k in range(len(ls)):
            l0_, l1_ = ls[k], ls[(k + 1) % len(ls)]
            v0_, v1_ = me.loops[l0_].vertex_index, me.loops[l1_].vertex_index
            key = (min(v0_, v1_), max(v0_, v1_))
            edge.setdefault(key, []).append((p.index, v0_, v1_, l0_, l1_))
    seam, bnd, wind, nonman = [], [], [], 0
    for (va, vb), uses in edge.items():
        if len(uses) == 1:
            _, v0_, v1_, l0_, l1_ = uses[0]
            bnd.append([*UVpx[l0_], *UVpx[l1_], *V[v0_], *V[v1_]]); continue
        if len(uses) > 2: nonman += 1; continue
        (pa, a0, a1, la0, la1), (pb, b0, b1, lb0, lb1) = uses
        if a0 == b0: wind.append(((V[va] + V[vb]) / 2).tolist(), )           # 같은 방향으로 지나감 = 이웃과 감김 방향이 다름
        A = {a0: UVpx[la0], a1: UVpx[la1]}; B = {b0: UVpx[lb0], b1: UVpx[lb1]}
        if np.abs(A[va] - B[va]).max() > 1e-3 or np.abs(A[vb] - B[vb]).max() > 1e-3:
            seam.append([*A[va], *A[vb], *B[va], *B[vb], *V[va], *V[vb], 0, 0])
    # 3) 떠 있는 조각(정점으로 이어진 묶음)과 구멍(열린 가장자리 고리)
    par = list(range(len(me.vertices)))
    def f(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    for (va, vb) in edge:
        ra, rb = f(va), f(vb)
        if ra != rb: par[ra] = rb
    comp = {}
    for i in range(len(me.vertices)): comp.setdefault(f(i), []).append(i)
    comps = sorted(([len(c), V[c].min(0).tolist(), V[c].max(0).tolist()] for c in comp.values()), key=lambda c: c[0])
    bverts = {}
    for (va, vb), uses in edge.items():
        if len(uses) == 1: bverts.setdefault(va, []).append(vb); bverts.setdefault(vb, []).append(va)
    seen = set(); loops = []
    for s in bverts:
        if s in seen: continue
        st = [s]; grp = []
        while st:
            x = st.pop()
            if x in seen: continue
            seen.add(x); grp.append(x); st.extend(bverts[x])
        pts = V[grp]; loops.append({"정점": len(grp), "가운데": pts.mean(0).round(4).tolist(), "폭(m)": round(float(np.ptp(pts, 0).max()), 4)})
    loops.sort(key=lambda l: l["정점"])
    # 뒤집힌 노멀: 닫힌 묶음이면 부피 부호, 아니면 이웃과 감김이 다른 모서리
    vol_neg = []
    for c in comp.values():
        cs = set(c)
        fs = [t for t in range(len(TV)) if TV[t, 0] in cs]
        if not fs: continue
        pp = P3[fs]; vol = np.einsum("ij,ij->i", pp[:, 0], np.cross(pp[:, 1], pp[:, 2])).sum() / 6
        if vol < 0 and not any(v in bverts for v in c): vol_neg.append({"정점": len(c), "가운데": V[c].mean(0).round(4).tolist(), "부피": float(vol)})
    meshrep[name] = {"정점": len(me.vertices), "면": len(me.polygons), "떠있는묶음": [{"정점": c[0], "상자": [np.round(c[1], 4).tolist(), np.round(c[2], 4).tolist()]} for c in comps],
                     "열린가장자리고리": loops, "감김다른모서리": [np.round(w, 4).tolist() for w in wind], "세면이상모서리": nonman, "닫힌묶음_부피음수": vol_neg,
                     "넓이0면": int(sum(1 for p in me.polygons if p.area < 1e-10))}
    # 4) 좌우 짝(2칸 간격)
    bvh = BVHTree.FromPolygons([tuple(v) for v in V], [tuple(t) for t in TV])
    ys, xs = np.nonzero((lab > 0) & ~np.isnan(pos[..., 0]))
    k = (ys % 2 == 0) & (xs % 2 == 0); ys, xs = ys[k], xs[k]
    pp = pos[ys, xs].astype(np.float64)
    k = np.abs(pp[:, 0] - MX) > 0.002; ys, xs, pp = ys[k], xs[k], pp[k]
    hit_t = np.full(len(pp), -1, np.int64); hit_p = np.zeros((len(pp), 3))
    for i in range(len(pp)):
        loc, nrm, fi, dist = bvh.find_nearest(Vector((2 * MX - pp[i, 0], pp[i, 1], pp[i, 2])), MAXD)
        if loc is not None: hit_t[i] = fi; hit_p[i] = loc
    ok = hit_t >= 0
    tt = hit_t[ok]; q = hit_p[ok]; A_, B_, C_ = P3[tt, 0], P3[tt, 1], P3[tt, 2]
    v0, v1, v2 = B_ - A_, C_ - A_, q - A_
    d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1); d20 = (v2 * v0).sum(1); d21 = (v2 * v1).sum(1)
    den = d00 * d11 - d01 * d01; den[np.abs(den) < 1e-20] = 1e-20
    bv = (d11 * d20 - d01 * d21) / den; bw = (d00 * d21 - d01 * d20) / den; bu = 1 - bv - bw
    quv = bu[:, None] * U2[tt, 0] + bv[:, None] * U2[tt, 1] + bw[:, None] * U2[tt, 2]
    mir = np.stack([xs[ok], ys[ok], quv[:, 0], quv[:, 1]], 1).astype(np.float32)
    # 5) 텍셀 밀도용 넓이
    tri3d = 0.5 * np.linalg.norm(np.cross(P3[:, 1] - P3[:, 0], P3[:, 2] - P3[:, 0]), axis=1)
    e1, e2 = U2[:, 1] - U2[:, 0], U2[:, 2] - U2[:, 0]; triuv = 0.5 * np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0])
    tric = U2.mean(1)
    np.savez_compressed(os.path.join(OUT, f"{name}.npz"), pos=pos, lab=lab.astype(np.int32), seam=np.array(seam, np.float32).reshape(-1, 16),
                        bnd=np.array(bnd, np.float32).reshape(-1, 10), mir=mir, tri3d=tri3d, triuv=triuv, tric=tric.astype(np.float32), mx=np.float64(MX))
    print(f"검사자료 {name}: 칸 {int((~np.isnan(pos[..., 0])).sum())}, 조각 안인데 자리 없음 {int(miss.sum())}, 이음매 {len(seam)}, 열린 가장자리 {len(bnd)}, "
          f"좌우 짝 {len(mir)}/{len(pp)}, 떠있는묶음 {len(comps)}, 감김다름 {len(wind)}")
meshrep["거울면x"] = MX
json.dump(meshrep, open(os.path.join(OUT, "mesh.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("검사자료 끝: " + OUT)
