# 조각지도.py — 작업본 파츠마다 UV 층(환경변수 TEX_UV, 없으면 첫 번째 층)을 그림 크기로 칠한 "조각 지도"를 .npy로 낸다. 작업본은 저장하지 않는다.
# 조각 번호: UV에서 이어진 면끼리(같은 모서리를 같은 UV 좌표로 나누는 면) 한 조각. 0 = 조각 밖, 1부터 = 조각 번호.
# 칸이 조각에 조금이라도 걸치면(칸 중심에서 0.71칸 안에 삼각형) 조각 안으로 본다(교복 사무라이 여백 채우기와 같은 기준).
# 사용: 블렌더실행.sh <작업본.blend> 조각지도.py -- <출력폴더> [크기=2048]
import bpy, sys, os, json
import numpy as np

a = sys.argv[sys.argv.index("--") + 1:]
OUT = os.path.abspath(a[0]); N = int(a[1]) if len(a) > 1 else 2048
os.makedirs(OUT, exist_ok=True)
NAMES = (__import__("os").environ.get("TEX_PARTS") or "파츠_헤어,파츠_얼굴,파츠_상체,파츠_하체").split(",")
rep = {}
for n in NAMES:
    me = bpy.data.objects[n].data
    me.calc_loop_triangles()
    nl = len(me.loops)
    uv = np.zeros(nl * 2, dtype=np.float32); me.uv_layers[__import__("os").environ.get("TEX_UV") or 0].data.foreach_get("uv", uv); uv = uv.reshape(nl, 2)
    # 면 단위 조각: 모서리를 함께 쓰고 양쪽 UV가 같으면 이어짐
    par = list(range(len(me.polygons)))
    def f(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    edge = {}
    for p in me.polygons:
        ls = list(p.loop_indices)
        for k in range(len(ls)):
            l0, l1 = ls[k], ls[(k + 1) % len(ls)]
            v0, v1 = me.loops[l0].vertex_index, me.loops[l1].vertex_index
            key = (min(v0, v1), max(v0, v1))
            u0 = tuple(np.round(uv[l0], 6)); u1 = tuple(np.round(uv[l1], 6))
            sig = {v0: u0, v1: u1}
            if key in edge:
                q, s2 = edge[key]
                if s2 == sig:
                    ra, rb = f(p.index), f(q)
                    if ra != rb: par[ra] = rb
            else:
                edge[key] = (p.index, sig)
    roots = {}
    isl = np.array([roots.setdefault(f(i), len(roots) + 1) for i in range(len(me.polygons))], dtype=np.int32)
    lab = np.zeros((N, N), dtype=np.int32)
    tri = np.array([t.loops[:] for t in me.loop_triangles], dtype=np.int64)
    tpoly = np.array([t.polygon_index for t in me.loop_triangles])
    P = uv[tri] * N
    for ti in range(len(tri)):
        x = P[ti, :, 0]; y = P[ti, :, 1]
        x0, x1 = int(max(0, np.floor(x.min()) - 2)), int(min(N - 1, np.ceil(x.max()) + 2))
        y0, y1 = int(max(0, np.floor(y.min()) - 2)), int(min(N - 1, np.ceil(y.max()) + 2))
        d = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
        L = isl[tpoly[ti]]
        if abs(d) < 1e-12:
            for k in range(3):
                for t_ in np.linspace(0, 1, 9):
                    xx = x[k] + (x[(k + 1) % 3] - x[k]) * t_; yy = y[k] + (y[(k + 1) % 3] - y[k]) * t_
                    lab[int(min(N - 1, max(0, np.floor(yy)))), int(min(N - 1, max(0, np.floor(xx))))] = L
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        w0 = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / d
        w1 = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / d
        w2 = 1.0 - w0 - w1
        e = [np.hypot(x[2] - x[1], y[2] - y[1]), np.hypot(x[0] - x[2], y[0] - y[2]), np.hypot(x[1] - x[0], y[1] - y[0])]
        tol = [0.7072 * ei / abs(d) for ei in e]
        inside = (w0 >= -tol[0]) & (w1 >= -tol[1]) & (w2 >= -tol[2])
        sub = lab[y0:y1 + 1, x0:x1 + 1]
        sub[inside & (sub == 0)] = L
    np.save(os.path.join(OUT, f"{n}_조각지도.npy"), lab)   # 행 0 = UV v 0(그림의 아래쪽)
    rep[n] = {"조각": int(isl.max()), "조각 안 칸(%)": round(float((lab > 0).mean() * 100), 1)}
print("조각지도 " + json.dumps(rep, ensure_ascii=False))
