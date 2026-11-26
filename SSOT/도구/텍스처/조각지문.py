# 조각지문.py — 조각 지도의 조각마다 칸 수를 "지문"으로 저장하거나, 저장한 지문과 비교한다(5-6).
# 정리 규칙은 조각 번호로 부위를 가리키므로, UV나 메시가 바뀌어 번호가 달라지면 엉뚱한 곳을 칠한다. 정리를 돌리기 전에 비교해 다르면 멈춘다
# (교복 사무라이 정리_v030의 조각지문.json과 같은 생각).
# 사용: python 조각지문.py <조각지도 폴더> <지문.json> [--만들기] [--파츠 a,b]
import sys, os, json
import numpy as np
args = sys.argv[1:]
make = "--만들기" in args; args = [a for a in args if a != "--만들기"]
parts = None
if "--파츠" in args:
    k = args.index("--파츠"); parts = args[k + 1].split(","); del args[k:k + 2]
if len(args) != 2: raise SystemExit("사용: <조각지도 폴더> <지문.json> [--만들기] [--파츠 ..]")
MAPD, JP = args
names = parts or sorted(f[:-len("_조각지도.npy")] for f in os.listdir(MAPD) if f.endswith("_조각지도.npy"))
if not names: raise SystemExit("조각 지도가 없다")
got = {n: np.bincount(np.load(os.path.join(MAPD, f"{n}_조각지도.npy")).ravel()).tolist()[1:] for n in names}
if make:
    json.dump(got, open(JP, "w", encoding="utf-8"), ensure_ascii=False); print(f"지문 저장: {JP} ({', '.join(f'{n} {len(v)}조각' for n, v in got.items())})")
else:
    want = json.load(open(JP, encoding="utf-8")); bad = []
    for n in names:
        if n not in want: bad.append(f"{n}: 지문에 없음"); continue
        if got[n] != want[n]:
            d = [i + 1 for i in range(max(len(got[n]), len(want[n]))) if i >= len(got[n]) or i >= len(want[n]) or got[n][i] != want[n][i]]
            bad.append(f"{n}: 다른 조각 {len(d)}개, 예 {d[:8]}")
    if bad: raise SystemExit("조각 지문이 다르다(UV·메시가 바뀌었으면 규칙의 조각 번호를 다시 찾는다): " + "; ".join(bad))
    print(f"조각 지문 같음: {', '.join(names)}")
