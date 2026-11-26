# onsen_compare.py — _captures/<이름>/<동작>/{q,f,u}_####.png 를 동작마다 비교 GIF(줄 = 이름, 칸 = 쿼터뷰·정면·올려다봄)와 정지 비교 그림으로 묶는다.
# 실행: PYTHONIOENCODING=utf-8 python Tools/onsen_compare.py <출력 폴더> <이름,이름,...> [칸 크기=240]
import os, sys
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SRC = os.path.join(ROOT, "_captures")
OUT = sys.argv[1]; NAMES = sys.argv[2].split(","); S = int(sys.argv[3]) if len(sys.argv) > 3 else 240
os.makedirs(OUT, exist_ok=True)
try: FONT = ImageFont.truetype(r"C:\Windows\Fonts\malgun.ttf", 16)
except OSError: FONT = ImageFont.load_default()
LAB = {"q": "쿼터뷰(위 35°)", "f": "정면(위 10°)", "u": "앞 아래 25°"}
def lab(im, t):
    d = ImageDraw.Draw(im); w = int(d.textlength(t, font=FONT)) + 12; d.rectangle([0, 0, w, 22], fill=(50, 50, 50)); d.text((6, 1), t, fill=(240, 240, 240), font=FONT)
jobs = sorted(os.listdir(os.path.join(SRC, NAMES[0])))
for job in jobs:
    d0 = os.path.join(SRC, NAMES[0], job)
    if not os.path.isdir(d0): continue
    n = min(len([f for f in os.listdir(os.path.join(SRC, nm, job)) if f.startswith("q_")]) for nm in NAMES)
    frames = []
    for i in range(n):
        im = Image.new("RGB", (S * 3, S * len(NAMES)), (40, 40, 40))
        for r, nm in enumerate(NAMES):
            for c, t in enumerate("qfu"):
                p = Image.open(os.path.join(SRC, nm, job, "%s_%04d.png" % (t, i))).convert("RGB").resize((S, S), Image.LANCZOS)
                lab(p, nm + " · " + LAB[t] if c == 0 else LAB[t]); im.paste(p, (c * S, r * S))
        frames.append(im)
    pal = frames[len(frames) // 2].quantize(colors=200, method=Image.Quantize.MEDIANCUT)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    dur = [50 if i % 6 == 5 else 40 for i in range(len(q))]   # GIF는 10ms 단위라 40ms 다섯 번 + 50ms 한 번으로 24fps(평균 41.7ms)를 맞춘다(Astra6 11)
    q[0].save(os.path.join(OUT, job + ".gif"), save_all=True, append_images=q[1:], duration=dur, loop=0, disposal=1)
    picks = [0, n // 4, n // 2, 3 * n // 4]
    sheet = Image.new("RGB", (S * 3 * 2, S * len(NAMES) * 2), (40, 40, 40))
    for k, i in enumerate(picks): sheet.paste(frames[i], ((k % 2) * S * 3, (k // 2) * S * len(NAMES)))
    sheet.save(os.path.join(OUT, job + "_정지4장.png"))
    print("DONE", job, n, "frames", os.path.getsize(os.path.join(OUT, job + ".gif")) // 1024, "KB")
