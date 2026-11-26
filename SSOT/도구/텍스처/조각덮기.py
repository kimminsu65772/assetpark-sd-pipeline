# 조각덮기.py — 손으로 고친 자리를 보관한 조각 그림(RGBA, 알파 255인 칸만)을 그림에 덮어쓴다(5-6). 그림을 그 자리에서 고쳐 쓴다.
# 스크립트로 옮기지 못한 손질(예: 온천 검사 얼굴 한쪽 눈썹의 층진 토막 지우기·바깥 끝 다듬기, 2026-11-23)을 다시 만들 수 있게 하려고 쓴다.
# 조각 그림은 같은 크기(2048)이고, 알파가 0이 아니면서 255도 아닌 칸이 있으면 멈춘다(반투명 손질은 받지 않음).
# 사용: python 조각덮기.py <그림> <조각 그림 RGBA>
import sys
import numpy as np
from PIL import Image
if len(sys.argv) != 3: raise SystemExit("사용: <그림> <조각 그림 RGBA>")
img = np.array(Image.open(sys.argv[1]).convert("RGB"))
pt = np.array(Image.open(sys.argv[2]))
if pt.ndim != 3 or pt.shape[2] != 4: raise SystemExit("조각 그림이 RGBA가 아니다")
if pt.shape[:2] != img.shape[:2]: raise SystemExit(f"크기가 다르다 {pt.shape[:2]} {img.shape[:2]}")
al = pt[..., 3]
if ((al > 0) & (al < 255)).any(): raise SystemExit("반투명 칸이 있다")
m = al == 255
if not m.any(): raise SystemExit("덮을 칸이 없다")
img[m] = pt[..., :3][m]
Image.fromarray(img).save(sys.argv[1])
print(f"조각덮기: {int(m.sum())}칸")
