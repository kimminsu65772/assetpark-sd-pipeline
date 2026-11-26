# 여백채우기.py — UV 조각 밖의 빈 칸을 채운다(5-5). 조각 안의 칸은 건드리지 않는다(바뀌면 멈춤).
# 방식(사용자 결정 2026-11-23): 조각에서 16칸까지는 가장 가까운 조각 안 칸의 색, 그 밖은 가장 가까운 조각의 둘레 평균색.
# v001과 다른 점(독립 검수 1차 지적 05): "가장 가까운"을 칸 중심 사이의 곧은 거리(유클리드)로 정확히 잰다(scipy 거리 변환).
#   v001은 8방향 한 칸씩 넓히기(체스판 거리)와 1/4 격자를 써서 곧은 거리 기준과 다른 칸이 있었다.
#   16칸까지 = 곧은 거리 16 이하. 둘레 = 상하좌우 중 하나라도 조각 밖인 조각 안 칸. 평균은 반올림(0.5는 올림).
# 조각 지도는 조각지도.py가 낸 <파츠>_조각지도.npy(0 = 조각 밖, 행 0 = UV v 0). 같은 입력에 다시 돌려도 결과가 같다.
# 사용: python 여백채우기.py <조각지도 폴더> <그림 폴더> <그림 이름 꼴(예: {}_구움.png)> <출력 폴더> [가장자리폭=16] [--파츠 파츠_얼굴,..]
import sys, os, json, time
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

args = [a for a in sys.argv[1:]]
parts = None
if "--파츠" in args:
    k = args.index("--파츠"); parts = args[k + 1].split(","); del args[k:k + 2]
if len(args) < 4: raise SystemExit("사용: <조각지도 폴더> <그림 폴더> <이름 꼴> <출력 폴더> [가장자리폭] [--파츠 ..]")
MAPD, IND, PAT, OUTD = args[:4]
EDGE = float(args[4]) if len(args) > 4 else 16.0
if "{}" not in PAT: raise SystemExit(f"이름 꼴에 {{}}가 없다: {PAT}")
os.makedirs(OUTD, exist_ok=True)
NAMES = parts or (__import__("os").environ.get("TEX_PARTS") or "파츠_헤어,파츠_얼굴,파츠_상체,파츠_하체").split(",")

rep = {}
for n in NAMES:
    t0 = time.time()
    mp, ip = os.path.join(MAPD, f"{n}_조각지도.npy"), os.path.join(IND, PAT.format(n))
    if not os.path.exists(mp) or not os.path.exists(ip): raise SystemExit(f"{n}: 파일 없음 {mp if not os.path.exists(mp) else ip}")
    lab = np.flipud(np.load(mp)).copy()
    src = np.array(Image.open(ip).convert("RGB"))
    H, W = lab.shape
    if src.shape[:2] != (H, W): raise SystemExit(f"{n}: 그림 크기 {src.shape[:2]}와 조각 지도 {lab.shape}가 다르다")
    inside = lab > 0
    iy, ix = distance_transform_edt(~inside, return_distances=False, return_indices=True)   # 메모리를 아끼려고 거리는 따로 정수로 잰다
    gy, gx = np.indices((H, W), dtype=np.int32)
    d2 = (iy - gy).astype(np.int64) ** 2; d2 += (ix - gx).astype(np.int64) ** 2; del gy, gx
    out = src.copy()
    near = (~inside) & (d2 <= EDGE * EDGE)
    out[near] = src[iy[near], ix[near]]
    pad = np.pad(inside, 1, constant_values=False)
    ring = inside & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
    L = lab.max() + 1
    cnt = np.bincount(lab[ring], minlength=L).astype(np.float64)
    mean = np.stack([np.bincount(lab[ring], weights=src[..., c][ring].astype(np.float64), minlength=L) for c in range(3)], -1)
    mean = np.floor(mean / np.maximum(cnt, 1)[:, None] + 0.5).astype(np.uint8)
    far = (~inside) & (d2 > EDGE * EDGE)
    out[far] = mean[lab[iy[far], ix[far]]]
    if (out[inside] != src[inside]).any(): raise SystemExit(f"{n}: 조각 안 칸이 바뀜")
    Image.fromarray(out).save(os.path.join(OUTD, PAT.format(n)))
    del iy, ix, d2
    rep[n] = {"조각 밖 칸(%)": round(float((~inside).mean() * 100), 1), "16칸 밖 칸(%)": round(float(far.mean() * 100), 1),
              "걸린 시간(초)": round(time.time() - t0, 1)}
print("여백채우기v002 " + json.dumps(rep, ensure_ascii=False))
