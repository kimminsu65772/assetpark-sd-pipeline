# 다각형채우기.py — 선의 가장자리에 파인 턱을 메우는 등, 그림 칸 좌표로 준 다각형을 한 색으로 매끈하게 칠한다(5-6). 그림을 그 자리에서 고쳐 쓴다.
# 색을 "어둠"으로 주면 다각형 둘레 6칸 안에서 가장 어두운 10% 칸의 중앙값(선 색)을 쓴다. 이미 더 어두운 칸은 밝게 하지 않는다(어둠일 때).
# 사용: python 다각형채우기.py <그림> <r.g.b|어둠> <x,y> <x,y> <x,y> [...]
import sys
import numpy as np, cv2
from PIL import Image
if len(sys.argv) < 6: raise SystemExit("사용: <그림> <r.g.b|어둠> <x,y> <x,y> <x,y> [...]")
img = np.array(Image.open(sys.argv[1]).convert("RGB")).astype(np.float32)
H, W = img.shape[:2]
P = np.array([[float(v) for v in t.split(",")] for t in sys.argv[3:]])
if (P < 0).any() or (P[:, 0] >= W).any() or (P[:, 1] >= H).any(): raise SystemExit("다각형이 그림 밖이다")
x0, y0 = np.floor(P.min(0)).astype(int) - 7; x1, y1 = np.ceil(P.max(0)).astype(int) + 8
x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
dark = sys.argv[2] == "어둠"
if dark:
    reg = img[y0:y1, x0:x1].reshape(-1, 3); L = reg.mean(-1)
    col = np.median(reg[L <= np.percentile(L, 10)], axis=0)
else:
    col = np.array([float(v) for v in sys.argv[2].split(".")])
S = 4
sub = np.zeros(((y1 - y0) * S, (x1 - x0) * S), np.uint8)
cv2.fillPoly(sub, [((P - [x0, y0]) * S).astype(np.int32)], 255, cv2.LINE_AA)
a = cv2.resize(sub, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA).astype(np.float32)[..., None] / 255
if not (a > 0.5).any(): raise SystemExit("칠할 칸이 없다")
reg = img[y0:y1, x0:x1]; new = reg * (1 - a) + col * a
img[y0:y1, x0:x1] = np.minimum(reg, new) if dark else new
Image.fromarray(np.clip(img + 0.5, 0, 255).astype(np.uint8)).save(sys.argv[1])
print(f"다각형채우기 {int((a > 0.5).sum())}칸 색 {col.astype(int).tolist()}")
