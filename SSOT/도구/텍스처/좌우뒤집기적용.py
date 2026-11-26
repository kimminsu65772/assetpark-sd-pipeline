# 좌우뒤집기적용.py — 좌우뒤집기.py가 낸 대응표대로 그림의 칸을 거울 자리 색(쌍선형)으로 바꾼다. 여백은 다시 채우지 않는다.
# 사용: python 좌우뒤집기적용.py <대응표.npy> <입력 그림> <출력 그림> [--원 cx,cy,r | --눈동자 x0,y0,x1,y1]
#       --원: 대응표 가운데 이 원 안의 칸만 바꾼다
#       --반사점 x0,y0,x1,y1: 상자 안 눈동자(아래 --눈동자와 같은 볼록 껍질) 속의 흰 반사점(밝기 > 170)을 눈동자 색으로 메우고(cv2 inpaint),
#           대응표의 읽을 자리가 밝은(> 170) 칸 가운데 눈동자 안에 떨어지는 칸만 옮겨 그린다(반사점만 옮김)
#       --눈동자: 상자 안 입력 그림의 눈동자 색 칸(밝기 40~130, 파랑이 초록보다 4 이상 큼)의 가장 큰 덩어리를 볼록 껍질로 감싼 자리만 바꾼다(반사점 포함)
import sys
import numpy as np
from PIL import Image
if len(sys.argv) not in (4, 6) or (len(sys.argv) == 6 and sys.argv[4] not in ("--원", "--눈동자", "--반사점")): raise SystemExit("사용: <대응표.npy> <입력 그림> <출력 그림> [--원 cx,cy,r | --눈동자 x0,y0,x1,y1]")
T = np.load(sys.argv[1]); img = np.array(Image.open(sys.argv[2]).convert("RGB")).astype(np.float32)
if T.ndim != 2 or T.shape[1] != 4 or len(T) == 0: raise SystemExit("대응표가 비었거나 꼴이 다르다")
H, W = img.shape[:2]
if len(sys.argv) == 6 and sys.argv[4] == "--반사점":
    import cv2
    x0, y0, x1, y1 = (int(v) for v in sys.argv[5].split(","))
    reg = img[y0:y1, x0:x1]; L = reg.mean(-1)
    m = ((L > 40) & (L < 130) & (reg[..., 2] - reg[..., 1] > 4)).astype(np.uint8)
    n, cc, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    if n < 2: raise SystemExit("상자 안에 눈동자 색이 없다")
    k = 1 + int(np.argmax(st[1:, 4])); ys, xs = np.nonzero(cc == k)
    hull = cv2.convexHull(np.stack([xs, ys], 1).astype(np.int32))
    iris = np.zeros(m.shape, np.uint8); cv2.fillPoly(iris, [hull], 1)
    iris = cv2.erode(iris, np.ones((3, 3), np.uint8))
    bright = ((L > 170) & (iris > 0)).astype(np.uint8)
    nb, cb, sb, _ = cv2.connectedComponentsWithStats(bright, connectivity=8)
    old = np.zeros_like(bright)
    for j in range(1, nb):   # 껍질 가장자리에 닿지 않는 밝은 덩어리 = 반사점
        if (cv2.dilate((cb == j).astype(np.uint8), np.ones((3, 3), np.uint8)) & (1 - iris)).sum() == 0: old |= (cb == j).astype(np.uint8)
    if not old.any(): raise SystemExit("지울 반사점을 찾지 못했다")
    old = cv2.dilate(old, np.ones((5, 5), np.uint8))
    fixed = cv2.inpaint(np.clip(reg + 0.5, 0, 255).astype(np.uint8), old, 6, cv2.INPAINT_TELEA).astype(np.float32)
    img[y0:y1, x0:x1] = fixed
    xs_, ys_ = np.clip(T[:, 2] - 0.5, 0, W - 1).astype(int), np.clip(T[:, 3] - 0.5, 0, H - 1).astype(int)
    keep = (img[ys_, xs_].mean(-1) > 170) & (T[:, 0] >= x0) & (T[:, 0] < x1) & (T[:, 1] >= y0) & (T[:, 1] < y1)
    keep[keep] = iris[T[keep, 1].astype(int) - y0, T[keep, 0].astype(int) - x0] > 0
    T = T[keep]
    if len(T) == 0: raise SystemExit("옮길 반사점 칸이 없다")
    print(f"반사점: 지운 칸 {int(old.sum())}")
elif len(sys.argv) == 6 and sys.argv[4] == "--눈동자":
    import cv2
    x0, y0, x1, y1 = (int(v) for v in sys.argv[5].split(","))
    reg = img[y0:y1, x0:x1]; L = reg.mean(-1)
    m = ((L > 40) & (L < 130) & (reg[..., 2] - reg[..., 1] > 4)).astype(np.uint8)
    n, cc, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    if n < 2: raise SystemExit("상자 안에 눈동자 색이 없다")
    k = 1 + int(np.argmax(st[1:, 4])); ys, xs = np.nonzero(cc == k)
    hull = cv2.convexHull(np.stack([xs, ys], 1).astype(np.int32))
    mask = np.zeros(m.shape, np.uint8); cv2.fillPoly(mask, [hull], 1)
    keep = (T[:, 0] >= x0) & (T[:, 0] < x1) & (T[:, 1] >= y0) & (T[:, 1] < y1)
    keep[keep] = mask[T[keep, 1].astype(int) - y0, T[keep, 0].astype(int) - x0] > 0
    T = T[keep]
    if len(T) == 0: raise SystemExit("눈동자 자리에 바꿀 칸이 없다")
elif len(sys.argv) == 6:
    cx, cy, r = (float(v) for v in sys.argv[5].split(","))
    T = T[(T[:, 0] + 0.5 - cx) ** 2 + (T[:, 1] + 0.5 - cy) ** 2 <= r * r]
    if len(T) == 0: raise SystemExit("원 안에 바꿀 칸이 없다")
bad = (T[:, 0] < 0) | (T[:, 0] >= W) | (T[:, 1] < 0) | (T[:, 1] >= H) | (T[:, 2] < 0) | (T[:, 2] > W) | (T[:, 3] < 0) | (T[:, 3] > H)
if bad.any(): raise SystemExit(f"대응표에 그림 밖 자리가 {int(bad.sum())}개 있다")
px, py = T[:, 0].astype(int), T[:, 1].astype(int)
x = np.clip(T[:, 2] - 0.5, 0, W - 1.001); y = np.clip(T[:, 3] - 0.5, 0, H - 1.001)
x0, y0 = x.astype(int), y.astype(int); fx, fy = (x - x0)[:, None], (y - y0)[:, None]
src = img.copy()
img[py, px] = src[y0, x0] * (1 - fx) * (1 - fy) + src[y0, x0 + 1] * fx * (1 - fy) + src[y0 + 1, x0] * (1 - fx) * fy + src[y0 + 1, x0 + 1] * fx * fy
Image.fromarray(np.clip(img + 0.5, 0, 255).astype(np.uint8)).save(sys.argv[3])
print(f"좌우뒤집기 적용: {len(T)}칸")
