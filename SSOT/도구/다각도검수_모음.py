# 다각도검수_모음.py — 다각도검수.py가 찍은 낱장을 모음 그림으로 붙인다(일반 파이썬 + PIL). 직접 부를 일은 없다.
# 사용: python 이_파일 <목록.json> <칸 크기> <한 줄 칸 수>
import sys, os, json
from PIL import Image, ImageDraw, ImageFont
import numpy as np
L = json.load(open(sys.argv[1], encoding="utf-8")); C = int(sys.argv[2]); PER = int(sys.argv[3])
rows = L["줄"]; OUT = L["출력"]
def font(n):
    for f in ("C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/gulim.ttc"):
        if os.path.exists(f): return ImageFont.truetype(f, n)
    return ImageFont.load_default()
F = font(14)
by = {}
for s in L["칸"]: by.setdefault(s["묶음"], []).append(s)
made = []
for g, items in by.items():
    for k in range(0, len(items), PER):
        part = items[k:k + PER]; LB = 18
        W = Image.new("RGB", (PER * C, len(rows) * (C + LB)), (20, 20, 20)); d = ImageDraw.Draw(W)
        for r, tag in enumerate(rows):
            for i, s in enumerate(part):
                x, y = i * C, r * (C + LB)
                W.paste(Image.open(s["그림"][tag]).convert("RGB").resize((C, C)), (x, y + LB))
                lab = f"{tag + ' ' if len(rows) > 1 else ''}{s['방향']}"
                if len(rows) > 1 and tag == "후":
                    a = np.asarray(Image.open(s["그림"]["전"]).convert("RGB")).astype(int)
                    b = np.asarray(Image.open(s["그림"]["후"]).convert("RGB")).astype(int)
                    n = int((np.abs(a - b).max(2) > 8).sum()); s["바뀐화소"] = n; lab += f"  바뀜 {n}"
                d.text((x + 4, y + 1), lab, fill=(255, 220, 0) if r == 0 else (150, 220, 255), font=F)
        name = f"모음_{g}" + (f"_{k // PER + 1}" if len(items) > PER else "") + ".png"
        W.save(os.path.join(OUT, name)); made.append(name)
print("모음 그림:", ", ".join(made))
if len(rows) > 1:
    ch = [f"{s['묶음']} {s['방향']}: {s['바뀐화소']}" for s in L["칸"] if s.get("바뀐화소")]
    print("바뀐 칸(화소 수):", "; ".join(ch) if ch else "없음")
