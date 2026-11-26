# 메시검사_모음.py — 메시검사.py가 찍은 낱장을 모음 그림(칸 200px, 한 줄 칸 수는 장마다)으로 붙인다(일반 파이썬 + PIL). 직접 부를 일은 없다.
# 사용: python 이_파일 <모음목록.json>
import sys, os, json
from PIL import Image, ImageDraw, ImageFont
L = json.load(open(sys.argv[1], encoding="utf-8")); C = L["칸"]; OUT = L["출력"]
def font(n):
    for f in ("C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/gulim.ttc"):
        if os.path.exists(f): return ImageFont.truetype(f, n)
    return ImageFont.load_default()
F = font(13); LB = 18
made = []
for sh in L["장"]:
    t = sh["칸"]; PER = sh.get("한줄", L["한줄"])
    if not t: continue
    rows = (len(t) + PER - 1) // PER
    W = Image.new("RGB", (PER * C, rows * (C + LB)), (20, 20, 20)); d = ImageDraw.Draw(W)
    for i, s in enumerate(t):
        x, y = (i % PER) * C, (i // PER) * (C + LB)
        W.paste(Image.open(s["그림"]).convert("RGB").resize((C, C)), (x, y + LB))
        d.text((x + 4, y + 1), s["라벨"], fill=(255, 220, 0), font=F)
    W.save(os.path.join(OUT, sh["파일"])); made.append(sh["파일"])
print("모음 그림 %d장:" % len(made), ", ".join(made))
