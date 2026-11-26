# onsen_zoom.py — 아랫도리 확대 칸(zs_/zu_)을 실행 이름별로 줄지어 비교 그림 두 장(걷기·달리기 / 쪼그림·칼)으로 만든다.
# 실행: PYTHONIOENCODING=utf-8 python Tools/onsen_zoom.py <출력 접두어> <이름,이름,...>
import sys, os
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_captures")
F = ImageFont.truetype(r"C:\Windows\Fonts\malgun.ttf", 15)
OUT, ROWS = sys.argv[1], sys.argv[2].split(",")
SETS = {"걷기달리기": [("UAL_Walk_Loop", "zs", 8, "걷기 8"), ("UAL_Walk_Loop", "zs", 24, "걷기 24"), ("UAL_Walk_Loop", "zu", 8, "걷기 8 아래"), ("UAL_Sprint_Loop", "zs", 4, "달리기 4"), ("UAL_Sprint_Loop", "zu", 12, "달리기 12 아래")],
        "쪼그림칼": [("UAL_Crouch_Idle_Loop", "zs", 0, "쪼그림 0"), ("UAL_Crouch_Idle_Loop", "zu", 35, "쪼그림 35 아래"), ("UAL_Sword_Attack", "zs", 12, "칼 12"), ("UAL_Sword_Attack", "zs", 24, "칼 24"), ("UAL_Sword_Attack", "zu", 24, "칼 24 아래")]}
for key, cols in SETS.items():
    S = 1000 // len(cols); im = Image.new("RGB", (S * len(cols), S * len(ROWS)), (40, 40, 40)); d = ImageDraw.Draw(im)
    for r, n in enumerate(ROWS):
        for c, (j, v, f, lab) in enumerate(cols):
            im.paste(Image.open(os.path.join(ROOT, n, j, "%s_%04d.png" % (v, f))).convert("RGB").resize((S, S), Image.LANCZOS), (c * S, r * S))
            d.rectangle([c * S, r * S, c * S + 160, r * S + 20], fill=(40, 40, 40)); d.text((c * S + 3, r * S + 1), "%s %s" % (n, lab), fill=(255, 255, 0), font=F)
    p = os.path.join(ROOT, "비교_보기", "%s_%s.png" % (OUT, key)); im.save(p); print(p, im.size)
