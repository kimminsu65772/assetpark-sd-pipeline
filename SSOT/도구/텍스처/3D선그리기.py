# 3D선그리기.py — 3D에서 x = X인 세로 평면과 겉면이 만나는 선을, 여러 조각에 걸쳐 같은 굵기로 그린다(5-6). 그림을 그 자리에서 고쳐 쓴다.
# 앞섶처럼 몸의 한 x 자리를 따라 위아래로 이어지는 옷선을, UV 조각이 갈라진 자리에서도 끊김·어긋남 없이 그리려고 쓴다.
# 입력은 칸3D.py가 낸 칸별 3D 자리. 칸에서 선까지의 거리(m)로 가장자리를 매끈하게(1칸 폭으로 섞음) 칠한다.
# 사용: python 3D선그리기.py <그림> <칸3D.npy> <X(m)> <z0,z1(m)> <굵기(m)> <r.g.b> [--앞만]
#   --앞만: y < 0(앞쪽 겉면)인 칸만. 칸 하나의 크기(m)는 이웃 칸 사이 3D 거리의 중앙값으로 잰다.
import sys
import numpy as np
from PIL import Image
args = sys.argv[1:]
front = "--앞만" in args; args = [a for a in args if a != "--앞만"]
if len(args) != 6: raise SystemExit("사용: <그림> <칸3D.npy> <X> <z0,z1> <굵기> <r.g.b> [--앞만]")
path, tp, X, zr, wd, col = args
X = float(X); z0, z1 = (float(v) for v in zr.split(",")); wd = float(wd); col = np.array([float(v) for v in col.split(".")])
if not (z0 < z1 and wd > 0): raise SystemExit("z 범위나 굵기가 틀렸다")
T = np.load(tp)
if T.ndim != 2 or T.shape[1] != 5 or not len(T): raise SystemExit("칸3D 표가 비었거나 꼴이 다르다")
img = np.array(Image.open(path).convert("RGB")).astype(np.float32); H, W = img.shape[:2]
px, py = T[:, 0].astype(int), T[:, 1].astype(int)
if (px < 0).any() or (px >= W).any() or (py < 0).any() or (py >= H).any(): raise SystemExit("칸3D 표에 그림 밖 칸이 있다")
# 칸 크기(m): 같은 행에서 바로 옆 칸과의 3D 거리
key = py * W + px; order = np.argsort(key); k2 = key[order]
nb = np.nonzero(np.diff(k2) == 1)[0]
step = np.median(np.linalg.norm(T[order][nb + 1, 2:] - T[order][nb, 2:], axis=1)) if len(nb) else 1 / 3000
sel = (T[:, 4] >= z0) & (T[:, 4] <= z1) & ((T[:, 3] < 0) if front else True)
d = np.abs(T[:, 2] - X)
a = np.clip((wd / 2 - d) / step + 0.5, 0, 1) * sel
m = a > 0
if not m.any(): raise SystemExit("그릴 칸이 0이다(X·z 범위를 확인)")
img[py[m], px[m]] = img[py[m], px[m]] * (1 - a[m, None]) + col * a[m, None]
Image.fromarray(np.clip(img + 0.5, 0, 255).astype(np.uint8)).save(path)
print(f"3D선 x={X} z={z0}~{z1} 굵기 {wd*1000:.1f}mm(칸 {step*1000:.2f}mm): {int((a > 0.5).sum())}칸")
