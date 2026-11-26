# onsen_upper_compare.py — 상체 확대 촬영(-onsenView upper: al·ar·afu·abu·aq)을 실행별로 줄지어 동작마다 비교 GIF로 묶는다(정지 그림은 만들지 않음).
# 실행: PYTHONIOENCODING=utf-8 python Tools/onsen_upper_compare.py <출력 폴더> <줄 이름:실행 이름:동작 접두어,...> <동작,동작,...> [칸 크기=200] [최대 장수=80]
#   예: ... 원본:UP:,A:AX_A:AM40_,B:AX_B:,C:AX_C1:  S70_Walk_Loop,UAL_Punch_Jab
#   줄마다 _captures/<실행>/<접두어><동작>/ 를 읽는다. 프레임 수는 줄 중 가장 짧은 것에 맞춘다.
#   시간: 24fps. 프레임이 [최대 장수=80]을 넘으면 k장마다 1장만 쓴다(k = 올림(장수/최대)). GIF는 10 ms 단위라 각 장의 시각(장 번호 × k/24초)을 10 ms로 반올림한 차이를 길이로 쓴다(k=1이면 40·40·50 ms 꼴, 평균이 정확히 k/24초).
import os, sys
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SRC = os.path.join(ROOT, "_captures")
OUT = sys.argv[1]; ROWS = [r.split(":") for r in sys.argv[2].split(",")]; JOBS = sys.argv[3].split(","); S = int(sys.argv[4]) if len(sys.argv) > 4 else 200; MAXF = int(sys.argv[5]) if len(sys.argv) > 5 else 80
os.makedirs(OUT, exist_ok=True)
try: FONT = ImageFont.truetype(r"C:\Windows\Fonts\malgun.ttf", 14)
except OSError: FONT = ImageFont.load_default()
TAGS = ["al", "ar", "afu", "abu", "aq"]; LAB = {"al": "왼옆", "ar": "오른옆", "afu": "앞 아래 20°", "abu": "뒤 아래 20°", "aq": "쿼터뷰 위 25°"}
def lab(im, t):
    d = ImageDraw.Draw(im); w = int(d.textlength(t, font=FONT)) + 10; d.rectangle([0, 0, w, 19], fill=(50, 50, 50)); d.text((5, 1), t, fill=(255, 255, 0), font=FONT)
for job in JOBS:
    dirs = [os.path.join(SRC, run, pre + job) for _, run, pre in ROWS]
    n = min(len([f for f in os.listdir(d) if f.startswith("al_")]) for d in dirs)
    step = -(-n // MAXF); idx = list(range(0, n, step)); frames = []
    for i in idx:
        im = Image.new("RGB", (S * len(TAGS), S * len(ROWS)), (40, 40, 40))
        for r, ((name, run, pre), d) in enumerate(zip(ROWS, dirs)):
            for c, t in enumerate(TAGS):
                p = Image.open(os.path.join(d, "%s_%04d.png" % (t, i))).convert("RGB").resize((S, S), Image.LANCZOS)
                lab(p, "%s · %s · %d" % (name, LAB[t], i) if c == 0 else LAB[t]); im.paste(p, (c * S, r * S))
        frames.append(im)
    pal = frames[len(frames) // 2].quantize(colors=200, method=Image.Quantize.MEDIANCUT)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    tick = lambda k: int(round(k * step * 1000 / 24 / 10.0)) * 10
    dur = [tick(k + 1) - tick(k) for k in range(len(q))]
    q[0].save(os.path.join(OUT, job + ".gif"), save_all=True, append_images=q[1:], duration=dur, loop=0, disposal=1)
    print("DONE", job, "frames", len(q), "of", n, "step", step, os.path.getsize(os.path.join(OUT, job + ".gif")) // 1024, "KB")
