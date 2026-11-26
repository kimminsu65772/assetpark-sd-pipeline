# 선끝가늘게.py — 잘라 낸 눈썹 안쪽 끝을 참고 그림처럼 점점 가늘어지게 다듬는다(얼굴 그림만, 그 자리에서 고쳐 씀).
# 방법: 끝에서 LEN칸 안의 세로줄마다 눈썹 선의 가운데(어두운 정도로 가중한 행)와 굵기를 구하고, 끝으로 갈수록 굵기를 줄여
#       가운데에서 먼 칸부터 피부색으로 섞는다. 눈썹 선의 자리와 기울기는 그대로 둔다.
# 사용: python 선끝가늘게.py <얼굴 그림> <행 범위 y0,y1> <끝 x:방향(L이면 x가 커질수록 끝, R이면 작아질수록 끝)> [...] [--길이 40] [--피부 237,197,181]
import sys
import numpy as np
from PIL import Image

path = sys.argv[1]; y0, y1 = (int(v) for v in sys.argv[2].split(","))
args = sys.argv[3:]; LEN = 40; SKIN = np.array([237, 197, 181], float); ends = []
i = 0
while i < len(args):
    if args[i] == "--길이": LEN = int(args[i + 1]); i += 2
    elif args[i] == "--피부": SKIN = np.array([float(v) for v in args[i + 1].split(",")]); i += 2
    else:
        if ":" not in args[i]: raise SystemExit(f"끝은 x:방향 꼴: {args[i]}")
        x, d = args[i].split(":")
        if d not in ("L", "R"): raise SystemExit(f"방향은 L 또는 R: {args[i]}")
        ends.append((int(x), d)); i += 1
if not ends: raise SystemExit("다듬을 끝이 없다")
img = np.array(Image.open(path).convert("RGB")).astype(float)
L = img.mean(-1); sL = SKIN.mean()
for xe, d in ends:
    cols = range(xe - LEN, xe + 1) if d == "L" else range(xe, xe + LEN + 1)
    if not any((sL - L[y0:y1, x]).max() > 40 for x in cols): raise SystemExit(f"끝 {xe}:{d} 둘레에 눈썹(피부보다 어두운 칸)이 없다")
    for x in cols:
        t = (xe - x) / LEN if d == "L" else (x - xe) / LEN     # 1 = 끝에서 멀다, 0 = 끝
        w = np.clip((sL - L[y0:y1, x]) / max(1.0, sL - L[y0:y1, x].min()), 0, 1)
        if w.sum() < 0.5: continue
        ys = np.arange(y0, y1)
        c = (w * ys).sum() / w.sum()
        half = max(0.6, (w > 0.3).sum() / 2.0)
        keep = half * (0.2 + 0.8 * t)                           # 끝에서 굵기 20%
        dist = np.abs(ys - c)
        a = np.clip((dist - keep) / 1.0, 0, 1)                  # 1 = 피부로
        img[y0:y1, x] = img[y0:y1, x] * (1 - a[:, None]) + SKIN * a[:, None]
Image.fromarray(np.clip(np.round(img), 0, 255).astype(np.uint8)).save(path)
print("눈썹 끝 다듬음", ends, "길이", LEN)
