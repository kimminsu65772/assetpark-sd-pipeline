# 거울조각선.py — 한 조각에 짧은 직선들(예: 발가락 사이 선)을 그리고, 거울 대응 조각(가로·세로를 바꾼 모양)에 같은 선을 옮겨 그린다(5-6).
# 한쪽 발(기준 조각)에 그리고, 반대쪽 발 조각에는 UV 조각의 대응(전치 = 거울)으로 옮겨 똑같이 그린다(대칭은 한쪽 먼저, 뒤집어 씀).
# 선은 4배 초과 표본으로 그려 가장자리가 매끈하다. 선은 그 조각 안에만 그린다. 마지막에 여백을 다시 채운다.
# 사용: python 거울조각선.py <조각지도 폴더> <그림 폴더(덮어씀)> <파츠> <기준조각> <대응조각> <선들: x0.y0-x1.y1;..> [--굵기 3] [--색 200.140.125]
#   대응: 기준 조각과 대응 조각의 감싼 상자 왼쪽 위를 맞추고 가로·세로를 바꾼다(온천 검사 하체 18 ↔ 16, 겹침 비율 0.996으로 확인).
import sys, os, subprocess
import numpy as np, cv2
from PIL import Image

MAPD, D, PART, A, Bi, SPEC = sys.argv[1:7]
opt = dict(zip(sys.argv[7::2], sys.argv[8::2]))
W = float(opt.get("--굵기", 3)); COL = np.array([float(v) for v in opt.get("--색", "200.140.125").split(".")])
lab = np.flipud(np.load(os.path.join(MAPD, f"{PART}_조각지도.npy")))
path = os.path.join(D, f"{PART}_구움.png")
img = np.array(Image.open(path).convert("RGB")).astype(np.float32)
A, Bi = int(A), int(Bi)
def corner(i):
    ys, xs = np.nonzero(lab == i); return xs.min(), ys.min()
for i in (A, Bi):
    if not (lab == i).any(): raise SystemExit(f"조각 {i}이(가) 조각 지도에 없다")
def bbox(i):
    ys, xs = np.nonzero(lab == i); return lab[ys.min():ys.max() + 1, xs.min():xs.max() + 1] == i
ma, mb = bbox(A), bbox(Bi).T
h, w = min(ma.shape[0], mb.shape[0]), min(ma.shape[1], mb.shape[1])
iou = (ma[:h, :w] & mb[:h, :w]).sum() / max(1, (ma[:h, :w] | mb[:h, :w]).sum())
if iou < 0.98: raise SystemExit(f"조각 {A}과 {Bi}(가로세로 바꿈)의 겹침 {iou:.3f}이 0.98보다 작다: 거울 대응이 아니다")
ax, ay = corner(A); bx, by = corner(Bi)
lines = [[tuple(float(v) for v in p.split(".")) for p in l.split("-")] for l in SPEC.split(";") if l]
S = 4
def draw(isl, segs):
    ys, xs = np.nonzero(lab == isl); x0, y0, x1, y1 = xs.min() - 4, ys.min() - 4, xs.max() + 5, ys.max() + 5
    sub = np.zeros(((y1 - y0) * S, (x1 - x0) * S), np.uint8)
    for (p, q) in segs:
        cv2.line(sub, (int((p[0] - x0) * S), int((p[1] - y0) * S)), (int((q[0] - x0) * S), int((q[1] - y0) * S)), 255, int(W * S), cv2.LINE_AA)
    a = cv2.resize(sub, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA).astype(np.float32) / 255 * (lab[y0:y1, x0:x1] == isl)
    img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - a[..., None]) + COL * a[..., None]
    return int((a > 0.5).sum())
if not lines: raise SystemExit("그릴 선이 없다")
n1 = draw(A, lines)
mir = [tuple((bx + (pt[1] - ay), by + (pt[0] - ax)) for pt in l) for l in lines]
n2 = draw(Bi, mir)
if n1 == 0 or abs(n1 - n2) > max(10, 0.05 * n1): raise SystemExit(f"그린 칸이 0이거나 두 발이 다르다: {n1} / {n2}")
Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(path)
print(f"발가락선 {PART} 조각{A}: {n1}칸, 조각{Bi}: {n2}칸, 대응 선: {[[tuple(round(v,1) for v in p) for p in l] for l in mir]}", flush=True)
here = os.path.dirname(os.path.abspath(__file__))
import gc   # 이 컴퓨터는 가상 메모리 여유가 적어, 여백 채우기를 부르기 전에 큰 배열을 놓아 준다
for _k in [k for k, v in list(globals().items()) if type(v).__name__ == "ndarray"]: del globals()[_k]
gc.collect()
subprocess.run([sys.executable, os.path.join(here, "여백채우기.py"), MAPD, D, "{}_구움.png", D, "--파츠", PART], check=True, stdout=subprocess.DEVNULL)
