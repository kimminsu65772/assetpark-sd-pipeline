# 지킬상자밖덮기.py — 단색화한 그림에서 남은 얼룩을 지운다(5-6, 사용자가 다각도로 보고 정한 범위).
# 방법: 파츠의 조각마다 가장 흔한 색(= 단색화한 바탕색)을 구하고, "지킬 상자" 밖에서 그 색과 다른 조각 안 칸을 모두 그 색으로 덮는다.
#       지킬 상자(그림 칸 좌표, 왼쪽 위 0,0, 2048칸) 안은 건드리지 않는다(눈·볼터치·입·눈썹 등 남길 무늬).
#       --조각 a,b 를 주면 그 조각들만 덮는다(지정 안 하면 파츠 전체).
# 마지막에 여백을 다시 채운다. 원래 그림은 고치지 않고 출력 폴더에 쓴다.
# 사용: python 지킬상자밖덮기.py <조각지도 폴더> <그림 폴더> <출력 폴더> <파츠> [--지킴 x0,y0,x1,y1;...] [--조각 a,b]
import sys, os, json, subprocess
import numpy as np
from PIL import Image

if len(sys.argv) < 5 or (len(sys.argv) - 5) % 2: raise SystemExit("사용: <조각지도 폴더> <그림 폴더> <출력 폴더> <파츠> [--지킴 ..] [--조각 ..]")
MAPD, IND, OUTD, PART = sys.argv[1:5]
opt = dict(zip(sys.argv[5::2], sys.argv[6::2]))
bad = [k for k in opt if k not in ("--지킴", "--조각")]
if bad: raise SystemExit(f"모르는 인자: {bad}")
if any((not v.strip()) or v.startswith("--") for v in opt.values()): raise SystemExit("값이 빈 인자가 있다")
for b in [b for b in opt.get("--지킴", "").split(";") if b]:
    if len(b.split(",")) != 4: raise SystemExit(f"--지킴 상자는 x0,y0,x1,y1: {b}")
boxes = [tuple(int(v) for v in b.split(",")) for b in opt.get("--지킴", "").split(";") if b]
only = {int(v) for v in opt["--조각"].split(",")} if "--조각" in opt else None
os.makedirs(OUTD, exist_ok=True)
NAMES = (__import__("os").environ.get("TEX_PARTS") or "파츠_헤어,파츠_얼굴,파츠_상체,파츠_하체").split(",")
for n in NAMES:   # 다른 파츠는 그대로 옮겨 둔다
    if n != PART and os.path.abspath(IND) != os.path.abspath(OUTD):
        Image.open(os.path.join(IND, f"{n}_구움.png")).save(os.path.join(OUTD, f"{n}_구움.png"))
lab = np.flipud(np.load(os.path.join(MAPD, f"{PART}_조각지도.npy")))
if only is not None and (only - set(np.unique(lab).tolist())): raise SystemExit(f"--조각 {sorted(only - set(np.unique(lab).tolist()))}이(가) 조각 지도에 없다")
img = np.array(Image.open(os.path.join(IND, f"{PART}_구움.png")).convert("RGB"))
H, W = lab.shape
protect = np.zeros((H, W), bool)
for x0, y0, x1, y1 in boxes:
    protect[y0:y1, x0:x1] = True
out = img.copy(); rep = {}
for i in range(1, lab.max() + 1):
    if only is not None and i not in only: continue
    m = lab == i
    if not m.any(): continue
    px = img[m]
    key = px[:, 0].astype(np.int64) * 65536 + px[:, 1].astype(np.int64) * 256 + px[:, 2]
    vals, cnt = np.unique(key, return_counts=True)
    k = vals[cnt.argmax()]; base = np.array([k // 65536, (k // 256) % 256, k % 256], np.uint8)
    diff = np.abs(img.astype(int) - base).max(-1) > 3
    tgt = m & diff & ~protect
    out[tgt] = base
    if tgt.any(): rep[i] = {"바탕": base.tolist(), "덮은 칸": int(tgt.sum())}
Image.fromarray(out).save(os.path.join(OUTD, f"{PART}_구움.png"))
print("얼룩지우기 " + PART + " " + json.dumps(rep, ensure_ascii=False), flush=True)
here = os.path.dirname(os.path.abspath(__file__))
import gc   # 이 컴퓨터는 가상 메모리 여유가 적어, 여백 채우기를 부르기 전에 큰 배열을 놓아 준다
for _k in [k for k, v in list(globals().items()) if type(v).__name__ == "ndarray"]: del globals()[_k]
gc.collect()
subprocess.run([sys.executable, os.path.join(here, "여백채우기.py"), MAPD, OUTD, "{}_구움.png", OUTD], check=True, stdout=subprocess.DEVNULL)
