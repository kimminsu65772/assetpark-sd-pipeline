# 선끝그리기.py — 잘린 선 끝(속눈썹 바깥끝 등)에 뾰족하게 가늘어지는 끝을 그려 붙인다(5-6). 그림을 그 자리에서 고쳐 쓴다.
# 방법: 잘린 단면(세로 선분 x, y0~y1)에서 끝점(tx, ty)까지 삼각형을 4배 초과 표본으로 매끈하게 칠한다. 색은 단면 칸들의 중앙값.
# 사용: python 선끝그리기.py <그림> <x,y0,y1> <tx,ty> [<x,y0,y1> <tx,ty> ...]
import sys
import numpy as np, cv2
from PIL import Image

if len(sys.argv) < 4 or (len(sys.argv) - 2) % 2: raise SystemExit("사용: <그림> <x,y0,y1> <tx,ty> [...]")
path = sys.argv[1]
img = np.array(Image.open(path).convert("RGB")).astype(np.float32)
H, W = img.shape[:2]; S = 4
for k in range(2, len(sys.argv), 2):
    x, y0, y1 = (float(v) for v in sys.argv[k].split(",")); tx, ty = (float(v) for v in sys.argv[k + 1].split(","))
    if not (0 <= x < W and 0 <= y0 < y1 < H and 0 <= tx < W and 0 <= ty < H): raise SystemExit(f"범위 밖: {sys.argv[k]} {sys.argv[k+1]}")
    col = np.median(img[int(y0):int(y1) + 1, int(x)], axis=0)
    if col.mean() > 120: raise SystemExit(f"단면 {sys.argv[k]}이 선 색이 아니다(평균 밝기 {col.mean():.0f})")
    bx0, by0 = int(min(x, tx)) - 3, int(min(y0, ty)) - 3; bx1, by1 = int(max(x, tx)) + 4, int(max(y1, ty)) + 4
    sub = np.zeros(((by1 - by0) * S, (bx1 - bx0) * S), np.uint8)
    pts = np.array([[x + 0.5, y0], [x + 0.5, y1 + 1], [tx + 0.5, ty + 0.5]]) - [bx0, by0]
    cv2.fillPoly(sub, [(pts * S).astype(np.int32)], 255, cv2.LINE_AA)
    a = cv2.resize(sub, (bx1 - bx0, by1 - by0), interpolation=cv2.INTER_AREA).astype(np.float32)[..., None] / 255
    reg = img[by0:by1, bx0:bx1]
    img[by0:by1, bx0:bx1] = np.minimum(reg, reg * (1 - a) + col * a)   # 이미 어두운 칸은 밝게 하지 않는다
    print(f"선끝 {sys.argv[k]} → {sys.argv[k+1]} 색 {col.astype(int).tolist()}")
Image.fromarray(np.clip(img + 0.5, 0, 255).astype(np.uint8)).save(path)
