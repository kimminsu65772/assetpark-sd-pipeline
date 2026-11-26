# 텍스처검사.py — 디자인과 상관없는 텍스처·메시 흠 "후보" 찾기. 흠이라고 판정하지 않는다. "여기를 봐야 한다"는 자리만 올린다.
# 판정은 사람이(또는 검수자가) 후보 자리의 그림을 보고 한다(SSOT/41_사용자_방침 "그림으로 직접 본 것만 고친다").
#
# 입력: 검사자료뽑기.py가 낸 자료 폴더(<파츠>.npz, mesh.json), 그림 폴더, 캐릭터 설정 파일(json), 출력 폴더
# 검사(이름 = 후보의 "검사" 칸):
#   이음매   3D에서는 붙어 있는데 UV에서 떨어진 모서리의 양쪽 색 차이(1.5칸 안쪽에서 읽음). 두 조각 바탕색 차이를 빼고,
#            이음매를 따라 잰 그 자리의 평소 색 변화보다 3배 넘게 큰 것만(평소 변화와 견주는 생각은 github.com/matty/agent-skills PR #16에서)
#   선굵기   어두운 선(조각 바탕보다 L이 20 넘게 어두운 가는 덩어리)의 폭을 3D 표면 기준(mm)으로 재어, 한 선 안에서 폭이 크게 바뀌는 곳
#   선끊김   선 끝이 이음매에 닿았는데 건너편에 선이 없거나 굵기가 다른 곳 / 3D에서 가까운(6mm 안) 다른 선 토막의 끝끼리(틈)
#   얼룩     조각 바탕색과 다른 아주 작은 덩어리(3D 넓이 12mm² 이하). 다른 무늬와 떨어져 있을수록 점수가 높다
#   여백     조각 밖 여백이 "16칸까지 가장 가까운 칸 색, 그 밖은 가장 가까운 조각의 둘레 평균"(SSOT/단계/5_텍스처)과 다른 곳, 검정 빈 칸
#   밀도     조각마다 텍셀 밀도(칸/m)가 파츠 중앙값의 0.67배 미만이거나 1.5배 넘는 곳
#   메시     구멍(작은 열린 고리), 떠 있는 작은 묶음, 이웃과 감김이 다른 모서리(뒤집힌 노멀), 넓이 0 면
#   좌우     3D 거울(x = 0) 자리끼리 색이 다른 곳 — 후보만. 일부러 비대칭인 곳은 설정의 "비대칭"으로 뺀다
#   그늘     단색이어야 할 조각 안의 넓고(가는 선이 아닌) 옅은 밝기 변화 — 후보만. 의도된 그라데이션은 설정의 "그라데이션"으로 뺀다
#   색       조각 바탕색이 설정의 "색목록"에 없거나, 다른 조각·파츠의 바탕색과 거의 같은데(채널 차이 6 이하) 다른 곳
# 헤어 파츠(설정 "헤어파츠")에는 이음매·얼룩·좌우만 돌린다(사용자 지시 2026-11-24).
#
# 설정 파일(json) 항목 — 모두 생략 가능:
#   "파츠": [...], "그림이름": "{}_구움.png", "그림": {"파츠_헤어": "../정밀_v026/파츠_헤어_정밀.png"}(파츠마다 그림 폴더 기준 경로, 그림이름보다 먼저), "헤어파츠": [...],
#   "색목록": [[r,g,b], ...]                     쓰는 색. 바탕색이 이 중 하나와 채널 차이 3 안이 아니면 "색" 후보
#   "비대칭": [자리, ...]                          좌우 검사에서 뺄 곳
#   "그라데이션": [자리, ...]                      그늘 검사에서 뺄 곳
#   "뺄곳": [자리, ...]                            모든 검사(또는 자리의 "검사" 목록에 적은 검사)에서 뺄 곳
#   자리 = {"파츠": 이름(없으면 모든 파츠), "조각": [번호], "그림상자": [x0,y0,x1,y1], "3D상자": [x0,y0,z0,x1,y1,z1](m), "검사": [...], "이유": "..."}
#     조각·그림상자·3D상자는 하나만 써도 되고, 여럿 쓰면 모두 맞아야 뺀다. 조각 번호는 SSOT/도구/텍스처/조각지도.py의 번호.
# 출력: <출력>/후보.json(전부), 후보.csv, 요약.json(검사별 수와 걸린 시간). 그림 칸 좌표는 왼쪽 위 (0,0).
# 사용: python 텍스처검사.py <자료 폴더> <그림 폴더> <설정.json> <출력 폴더> [--검사 이음매,선굵기,...]
import sys, os, json, time, csv
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
import cv2

ALL = ["이음매", "선굵기", "선끊김", "얼룩", "여백", "밀도", "메시", "좌우", "그늘", "색"]
HAIR_OK = {"이음매", "얼룩", "좌우"}
args = sys.argv[1:]
only = None
if "--검사" in args:
    k = args.index("--검사"); only = args[k + 1].split(","); del args[k:k + 2]
if len(args) != 4: raise SystemExit("사용: <자료 폴더> <그림 폴더> <설정.json> <출력 폴더> [--검사 a,b]")
DD, ID, CP, OUT = args
CFG = json.load(open(CP, encoding="utf-8"))
CHECKS = only or ALL
for c in CHECKS:
    if c not in ALL: raise SystemExit(f"모르는 검사: {c} (있는 것: {','.join(ALL)})")
PARTS = CFG.get("파츠") or (os.environ.get("TEX_PARTS") or "파츠_헤어,파츠_얼굴,파츠_상체,파츠_하체").split(",")
PAT = CFG.get("그림이름", "{}_구움.png"); HAIR = set(CFG.get("헤어파츠", ["파츠_헤어"]))
for key in ("비대칭", "그라데이션", "뺄곳"):
    for r in CFG.get(key, []):
        if not any(k in r for k in ("조각", "그림상자", "3D상자")) and "파츠" not in r: raise SystemExit(f"설정 {key}의 자리에 조각·그림상자·3D상자·파츠가 하나도 없다: {r}")
os.makedirs(OUT, exist_ok=True)

def to_lab(rgb):
    return cv2.cvtColor(rgb.astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)

def region_mask(r, part, lab, pos):
    if "파츠" in r and r["파츠"] != part: return None
    m = lab > 0
    if "조각" in r: m &= np.isin(lab, r["조각"])
    if "그림상자" in r:
        x0, y0, x1, y1 = r["그림상자"]; bm = np.zeros_like(m); bm[max(y0, 0):y1, max(x0, 0):x1] = True; m &= bm
    if "3D상자" in r:
        b = r["3D상자"]; p = pos
        with np.errstate(invalid="ignore"):
            m &= (p[..., 0] >= b[0]) & (p[..., 1] >= b[1]) & (p[..., 2] >= b[2]) & (p[..., 0] <= b[3]) & (p[..., 1] <= b[4]) & (p[..., 2] <= b[5])
    return m

def excl_mask(kind, check, part, lab, pos):
    m = np.zeros(lab.shape, bool)
    for r in CFG.get(kind, []):
        if kind == "뺄곳" and "검사" in r and check not in r["검사"]: continue
        rm = region_mask(r, part, lab, pos)
        if rm is not None: m |= rm
    return m

def zhang_suen(img):
    # 가는 뼈대(Zhang-Suen). img: bool 2D
    I = np.pad(img.astype(np.uint8), 1)
    while True:
        changed = False
        for step in (0, 1):
            P2, P3, P4, P5 = I[:-2, 1:-1], I[:-2, 2:], I[1:-1, 2:], I[2:, 2:]
            P6, P7, P8, P9 = I[2:, 1:-1], I[2:, :-2], I[1:-1, :-2], I[:-2, :-2]
            nb = [P2, P3, P4, P5, P6, P7, P8, P9]
            B = sum(n.astype(int) for n in nb)
            A = sum(((nb[i] == 0) & (nb[(i + 1) % 8] == 1)).astype(int) for i in range(8))
            C = I[1:-1, 1:-1] == 1
            if step == 0: m = C & (B >= 2) & (B <= 6) & (A == 1) & ((P2 * P4 * P6) == 0) & ((P4 * P6 * P8) == 0)
            else: m = C & (B >= 2) & (B <= 6) & (A == 1) & ((P2 * P4 * P8) == 0) & ((P2 * P6 * P8) == 0)
            if m.any():
                I[1:-1, 1:-1][m] = 0; changed = True
        if not changed: break
    return I[1:-1, 1:-1].astype(bool)

K8 = np.ones((3, 3), int)
cands = []; times = {}; summary = {}

def add(check, part, desc, score, box, isl=None, p3=None, extra=None):
    x0, y0, x1, y1 = [int(v) for v in box]
    c = {"검사": check, "파츠": part, "조각": None if isl is None else int(isl), "상자": [x0, y0, x1, y1],
         "가운데": [int((x0 + x1) / 2), int((y0 + y1) / 2)], "3D": None if p3 is None else [round(float(v), 4) for v in p3],
         "점수": round(float(score), 2), "설명": desc}
    if extra: c.update(extra)
    for k in ("점들", "건너편점들"):          # 자리를 정확히 가리키는 칸(최대 300개). 상자보다 이것으로 본다
        if k in c:
            a_ = np.asarray(c[k]).reshape(-1, 2)
            if len(a_) > 300: a_ = a_[np.linspace(0, len(a_) - 1, 300).astype(int)]
            c[k] = a_.astype(int).tolist()
    cands.append(c)

# ---------- 파츠별 자료 읽기 ----------
D = {}
for part in PARTS:
    zp = os.path.join(DD, f"{part}.npz"); ip = os.path.join(ID, CFG.get("그림", {}).get(part, PAT.format(part)))
    if not os.path.exists(zp): raise SystemExit(f"자료가 없다: {zp}")
    if not os.path.exists(ip): raise SystemExit(f"그림이 없다: {ip}")
    z = np.load(zp); img = np.array(Image.open(ip).convert("RGB"))
    lab = z["lab"]; pos = z["pos"].copy()
    if img.shape[:2] != lab.shape: raise SystemExit(f"{part}: 그림 크기 {img.shape[:2]}와 자료 {lab.shape}가 다르다")
    inside = lab > 0
    miss = inside & np.isnan(pos[..., 0])
    if miss.any():
        have = ~np.isnan(pos[..., 0]); iy, ix = ndi.distance_transform_edt(~have, return_distances=False, return_indices=True)
        pos[miss] = pos[iy[miss], ix[miss]]
    H, W = lab.shape
    L = lab.max() + 1
    key = lab.astype(np.int64)[inside] * (1 << 24) + (img[inside][:, 0].astype(np.int64) << 16) + (img[inside][:, 1].astype(np.int64) << 8) + img[inside][:, 2]
    u, cnt = np.unique(key, return_counts=True)
    isl_of = u >> 24; order = np.lexsort((-cnt, isl_of)); first = np.ones(len(order), bool); first[1:] = isl_of[order][1:] != isl_of[order][:-1]
    base = np.zeros((L, 3), np.uint8); area = np.bincount(lab.ravel(), minlength=L)
    for idx in order[first]:
        rgb = u[idx] & 0xFFFFFF; base[isl_of[idx]] = [(rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255]
    # 칸 하나의 3D 크기(m): 같은 조각의 오른쪽 이웃과의 거리, 조각마다 중앙값
    dx = np.linalg.norm(pos[:, 1:] - pos[:, :-1], axis=-1); same = (lab[:, 1:] == lab[:, :-1]) & inside[:, 1:]
    ts = np.full(L, np.nan)
    li = lab[:, 1:][same]; dv = dx[same]
    ordr = np.argsort(li, kind="stable"); li_s, dv_s = li[ordr], dv[ordr]; br = np.searchsorted(li_s, np.arange(L + 1))
    for i in range(1, L):
        if br[i + 1] > br[i]: ts[i] = np.median(dv_s[br[i]:br[i + 1]])
    med_ts = np.nanmedian(ts[1:]); ts = np.where(np.isfinite(ts) & (ts > 0), ts, med_ts)   # 3D 크기 0(한 점에 몰린 조각)도 중앙값으로
    D[part] = dict(img=img, lab=lab, pos=pos, inside=inside, base=base, area=area, ts=ts, z=z, LAB=to_lab(img), H=H, W=W)
    # 무늬 밀도: 둘레 약 15mm 안에서 바탕과 다른 칸의 비율. 꽃무늬처럼 잘게 흩어진 무늬 안의 후보는 점수를 낮춘다(디자인과 상관없이)

def dE_to_base(d):
    bl = to_lab(d["base"][None])[0]
    return np.linalg.norm(d["LAB"] - bl[d["lab"]], axis=-1) * d["inside"], bl

def add_density():
    for part, d in D.items():
        dE, _ = dE_to_base(d)
        win = int(max(5, round(0.015 / np.median(d["ts"][1:]))))
        dev = ((dE > 10) & d["inside"]).astype(np.float32)
        num = cv2.boxFilter(dev, -1, (win, win), normalize=False); den = cv2.boxFilter(d["inside"].astype(np.float32), -1, (win, win), normalize=False)
        d["dens"] = num / np.maximum(den, 1)
add_density()
def dw(part, x, y):
    d = D[part]; y = int(min(max(y, 0), d["H"] - 1)); x = int(min(max(x, 0), d["W"] - 1)); return 1.0 / (1.0 + 8.0 * float(d["dens"][y, x]))

def bbox_of(mask_coords):
    ys, xs = mask_coords; return [xs.min(), ys.min(), xs.max() + 1, ys.max() + 1]

# ---------- 이음매 표본(여러 검사가 씀) ----------
SEAMS = {}
BL = {part: to_lab(d["base"][None])[0] for part, d in D.items()}
for part, d in D.items():
    s = d["z"]["seam"]; img, lab, pos, LABc = d["img"], d["lab"], d["pos"], d["LAB"]; H, W = d["H"], d["W"]
    rows = []
    for ei, e in enumerate(s):
        A0, A1, B0, B1, P0, P1 = e[0:2], e[2:4], e[4:6], e[6:8], e[8:11], e[11:14]
        n = int(max(2, np.ceil(max(np.linalg.norm(A1 - A0), np.linalg.norm(B1 - B0)) / 2)))
        for t in (np.arange(n) + 0.5) / n:
            p3 = P0 + (P1 - P0) * t; sides = []
            for Q0, Q1 in ((A0, A1), (B0, B1)):
                q = Q0 + (Q1 - Q0) * t; dvec = Q1 - Q0; nn = np.array([-dvec[1], dvec[0]]); nn /= (np.linalg.norm(nn) + 1e-9)
                best = None
                for sg in (1, -1):
                    r = q + sg * 1.5 * nn; xi, yi = int(np.floor(r[0])), int(np.floor(r[1]))
                    if not (0 <= xi < W and 0 <= yi < H) or lab[yi, xi] == 0: continue
                    dd = np.linalg.norm(pos[yi, xi] - p3)
                    if best is None or dd < best[0]: best = (dd, xi, yi, sg)
                sides.append(best)
            if sides[0] is None or sides[1] is None: continue
            (_, xa, ya, sa), (_, xb, yb, sb) = sides
            la, lb = lab[ya, xa], lab[yb, xb]
            de = float(np.linalg.norm((LABc[ya, xa] - LABc[yb, xb]) - (BL[part][la] - BL[part][lb])))   # 두 조각의 바탕색 차이(재질 경계)는 뺀다
            rows.append((xa, ya, xb, yb, p3[0], p3[1], p3[2], de, lab[ya, xa], lab[yb, xb], ei, 0.0))
    S = np.array(rows, np.float64).reshape(-1, 12)
    # 평소 색 변화(matty/agent-skills PR #16의 생각을 따름, 코드는 보지 않음): 이음매를 따라 같은 쪽 이웃 표본끼리의 색 차이를
    # 모서리 안 앞뒤 5표본 창의 중앙값으로 잰다. 꽃무늬처럼 원래 자주 바뀌는 곳은 크고, 단색 천은 0에 가깝다. 두 쪽 가운데 큰 값
    for ei in np.unique(S[:, 10]).astype(int) if len(S) else []:
        idx = np.nonzero(S[:, 10] == ei)[0]
        if len(idx) < 2: continue
        loc = np.zeros(len(idx))
        for cx, cy in ((0, 1), (2, 3)):
            c = LABc[S[idx, cy].astype(int), S[idx, cx].astype(int)]
            dd = np.linalg.norm(np.diff(c, axis=0), axis=1); dd = np.concatenate([dd, dd[-1:]])
            for k in range(len(idx)):
                loc[k] = max(loc[k], np.median(dd[max(0, k - 5):k + 6]))
        S[idx, 11] = loc
    SEAMS[part] = S

def cluster3d(P, link):
    # 3D 점을 link(m) 안이면 한 묶음으로(격자 + 합집합)
    if len(P) == 0: return np.zeros(0, int)
    g = np.floor(P / link).astype(np.int64); par = np.arange(len(P))
    def f(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    cell = {}
    for i, c in enumerate(map(tuple, g)): cell.setdefault(c, []).append(i)
    for c, ids in cell.items():
        for dxx in (-1, 0, 1):
            for dyy in (-1, 0, 1):
                for dzz in (-1, 0, 1):
                    o = cell.get((c[0] + dxx, c[1] + dyy, c[2] + dzz))
                    if not o: continue
                    for i in ids:
                        for j in o:
                            if j > i and np.linalg.norm(P[i] - P[j]) <= link:
                                ra, rb = f(i), f(j)
                                if ra != rb: par[ra] = rb
    return np.array([f(i) for i in range(len(P))])

def run(check, fn):
    if check not in CHECKS: return
    t0 = time.time(); n0 = len(cands); fn(); times[check] = round(time.time() - t0, 1); summary[check] = len(cands) - n0

# ---------- 1. 이음매 색 끊김 ----------
def chk_seam():
    for part, S in SEAMS.items():
        d = D[part]
        ex = excl_mask("뺄곳", "이음매", part, d["lab"], d["pos"])
        bad = S[(S[:, 7] > 12) & (S[:, 7] > 3 * S[:, 11])]          # 평소 변화의 3배를 넘는 것만
        bad = bad[~ex[bad[:, 1].astype(int), bad[:, 0].astype(int)] & ~ex[bad[:, 3].astype(int), bad[:, 2].astype(int)]]
        if not len(bad): continue
        cl = cluster3d(bad[:, 4:7], 0.003)
        for c in np.unique(cl):
            b = bad[cl == c]
            if len(b) < 2 and b[:, 7].max() < 25: continue
            ia, ib = int(np.bincount(b[:, 8].astype(int)).argmax()), int(np.bincount(b[:, 9].astype(int)).argmax())
            ln = len(b) * 2 * d["ts"][ia] * 1000
            boxA = [b[:, 0].min() - 3, b[:, 1].min() - 3, b[:, 0].max() + 4, b[:, 1].max() + 4]
            boxB = [b[:, 2].min() - 3, b[:, 3].min() - 3, b[:, 2].max() + 4, b[:, 3].max() + 4]
            add("이음매", part, f"이음매 양쪽 색 차이(두 조각 바탕색 차이를 뺀 것) ΔE 평균 {b[:, 7].mean():.0f}(최대 {b[:, 7].max():.0f}), 평소 변화 {b[:, 11].mean():.1f}, 길이 약 {ln:.0f}mm, 조각 {ia}|{ib}",
                b[:, 7].mean() * min(ln, 20) / (1 + b[:, 11].mean() / 4), boxA, ia, b[np.argmax(b[:, 7]), 4:7], {"건너편상자": [int(v) for v in boxB], "건너편조각": ib, "점들": b[:, 0:2], "건너편점들": b[:, 2:4]})

# ---------- 2·3. 선 ----------
LINES = {}   # part -> dict(mask, comps, ends...)
def build_lines():
    for part, d in D.items():
        if part in HAIR: continue
        dE, bl = dE_to_base(d); Lc = d["LAB"][..., 0]; lab = d["lab"]
        baseL = bl[:, 0][lab]
        dark = d["inside"] & (baseL > 35) & (Lc < baseL - 20)
        dark &= ~(excl_mask("뺄곳", "선굵기", part, lab, d["pos"]) & excl_mask("뺄곳", "선끊김", part, lab, d["pos"]))
        cl, n = ndi.label(dark, K8)
        dt = ndi.distance_transform_edt(dark)
        sl = ndi.find_objects(cl)
        comps = []
        for i, s in enumerate(sl, 1):
            if s is None: continue
            m = cl[s] == i
            if m.sum() < 8: continue
            y0, x0 = s[0].start, s[1].start
            sk = zhang_suen(m)
            ys, xs = np.nonzero(sk)
            if len(ys) < 3: continue
            P = np.pad(sk, 1).astype(int); nbc = sum(np.roll(np.roll(P, a, 0), b, 1) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0))[1:-1, 1:-1]
            endm = sk & (nbc == 1)
            ey, ex = np.nonzero(endm)
            isl = int(np.bincount(lab[s][m]).argmax()); tsm = d["ts"][isl] * 1000
            w = (2 * dt[s][sk] - 1).clip(1) * tsm                      # 뼈대 칸마다 폭(mm)
            comps.append(dict(id=i, isl=isl, y0=y0, x0=x0, sk=(ys + y0, xs + x0), w=w, ends=list(zip(ex + x0, ey + y0)), tsm=tsm,
                              box=[x0, y0, s[1].stop, s[0].stop], area=int(m.sum())))
        LINES[part] = dict(dark=dark, cl=cl, dt=dt, comps=comps, exw=excl_mask("뺄곳", "선굵기", part, lab, d["pos"]), exb=excl_mask("뺄곳", "선끊김", part, lab, d["pos"]))

def chk_width():
    for part, Ld in LINES.items():
        d = D[part]
        for c in Ld["comps"]:
            ys, xs = c["sk"]
            if len(ys) < 15: continue
            ex = np.array(c["ends"]).reshape(-1, 2)
            far = np.ones(len(ys), bool)
            for (x, y) in ex: far &= np.hypot(xs - x, ys - y) > 4
            if far.sum() < 8: continue
            far &= ~Ld["exw"][ys, xs]
            if far.sum() < 8: continue
            w = c["w"][far]; lo, hi = np.percentile(w, 10), np.percentile(w, 90)
            if hi / max(lo, 1e-6) >= 1.8 and hi - lo >= 0.6:
                k = np.argmax(np.where(far, c["w"], -1)); kk = np.argmin(np.where(far, c["w"], 1e9))
                add("선굵기", part, f"한 선 안에서 폭이 {lo:.1f}~{hi:.1f}mm로 바뀜(뼈대 {len(ys)}칸, 가장 굵은 곳 {xs[k]},{ys[k]}, 가는 곳 {xs[kk]},{ys[kk]})",
                    (hi - lo) * np.sqrt(len(ys)) * dw(part, xs[k], ys[k]), [xs[k] - 8, ys[k] - 8, xs[k] + 9, ys[k] + 9], c["isl"], d["pos"][ys[k], xs[k]],
                    {"건너편상자": [int(xs[kk]) - 8, int(ys[kk]) - 8, int(xs[kk]) + 9, int(ys[kk]) + 9], "선상자": [int(v) for v in c["box"]]})

def chk_break():
    ENDS = []   # (part, comp idx, x, y, 3D, width mm, near_seam)
    for part, Ld in LINES.items():
        d = D[part]; S = SEAMS[part]; lab = d["lab"]; inside = d["inside"]
        edt_out = ndi.distance_transform_edt(inside)
        for ci, c in enumerate(Ld["comps"]):
            ys, xs = c["sk"]
            for (x, y) in c["ends"]:
                if Ld["exb"][y, x]: continue
                dd_ = np.hypot(xs - x, ys - y); near = (dd_ >= 3) & (dd_ <= 10)
                if not near.any(): near = dd_ <= 10
                wend = float(np.median(c["w"][near]))
                p3 = d["pos"][y, x]
                rec = dict(part=part, ci=ci, x=int(x), y=int(y), p3=p3, w=wend, isl=c["isl"], seam=False)
                if edt_out[y, x] <= 5 and len(S):
                    # 이 조각 쪽 이음매 표본 가운데 가까운 것
                    dA = np.hypot(S[:, 0] - x, S[:, 1] - y); dB = np.hypot(S[:, 2] - x, S[:, 3] - y)
                    ia, ib = np.argmin(dA), np.argmin(dB)
                    if min(dA[ia], dB[ib]) <= 7:
                        rec["seam"] = True
                        if dA[ia] <= dB[ib]: ox, oy = S[ia, 2], S[ia, 3]
                        else: ox, oy = S[ib, 0], S[ib, 1]
                        ox, oy = int(ox), int(oy); oisl = lab[oy, ox]
                        r = max(3, int(np.ceil(1.0 / (d["ts"][oisl] * 1000))))
                        y0_, y1_, x0_, x1_ = max(oy - r, 0), oy + r + 1, max(ox - r, 0), ox + r + 1
                        win = Ld["dark"][y0_:y1_, x0_:x1_]
                        ownL = BL[part][c["isl"]][0]
                        if not win.any() and (d["LAB"][y0_:y1_, x0_:x1_, 0] < ownL - 20).any(): continue   # 건너편 조각 바탕이 어두워 선이 그 색으로 이어짐
                        if not win.any():
                            add("선끊김", part, f"선 끝이 이음매에 닿았는데 건너편(조각 {oisl}, {ox},{oy})에 선이 없음. 선 폭 {wend:.1f}mm",
                                wend * 10 * dw(part, x, y), [x - 6, y - 6, x + 7, y + 7], c["isl"], p3, {"건너편상자": [ox - 6, oy - 6, ox + 7, oy + 7], "건너편조각": int(oisl)})
                        else:
                            wo = float((2 * Ld["dt"][y0_:y1_, x0_:x1_][win].max() - 1).clip(1) * d["ts"][oisl] * 1000)
                            if max(wo, wend) / max(min(wo, wend), 1e-6) >= 1.7 and abs(wo - wend) >= 0.5:
                                add("선끊김", part, f"이음매 양쪽 선 폭이 다름 {wend:.1f}mm | {wo:.1f}mm(건너편 조각 {oisl}, {ox},{oy})",
                                    abs(wo - wend) * 5, [x - 6, y - 6, x + 7, y + 7], c["isl"], p3, {"건너편상자": [ox - 6, oy - 6, ox + 7, oy + 7], "건너편조각": int(oisl)})
                rec["len"] = len(ys)
                ENDS.append(rec)
    # 3D에서 가까운 다른 선 토막 끝끼리(파츠를 넘어서도) = 틈. 끝점을 3D 6mm 안에서 묶고, 묶음마다 후보 하나
    ENDS = [e for e in ENDS if e["len"] >= 10]                     # 아주 짧은 부스러기는 얼룩 검사가 본다
    if not ENDS: return
    P = np.array([e["p3"] for e in ENDS], np.float64)
    G = 0.006
    cl = cluster3d(P, G)
    for c in np.unique(cl):
        idx = np.nonzero(cl == c)[0]
        comps = {(ENDS[i]["part"], ENDS[i]["ci"]) for i in idx}
        if len(comps) < 2: continue
        es = [ENDS[i] for i in idx]
        if all(e["seam"] for e in es) and len({e["part"] for e in es}) == 1 and len(es) == 2 and np.linalg.norm(es[0]["p3"] - es[1]["p3"]) < 0.0015: continue
        gap = min(np.linalg.norm(P[i] - P[j]) for i in idx for j in idx if (ENDS[i]["part"], ENDS[i]["ci"]) != (ENDS[j]["part"], ENDS[j]["ci"]))
        ws = [e["w"] for e in es]; a = es[0]
        many = len(es) >= 4
        sc = ((G - gap) * 1000 + (max(ws) - min(ws))) * dw(a["part"], a["x"], a["y"]) * (0.25 if many else 1.0)
        parts = sorted({e["part"] for e in es})
        extra = {"끝점": [[e["part"], e["x"], e["y"]] for e in es]}
        others = [e for e in es if e["part"] != a["part"] or e["ci"] != a["ci"]]
        if others: extra.update({"건너편파츠": others[0]["part"], "건너편상자": [others[0]["x"] - 6, others[0]["y"] - 6, others[0]["x"] + 7, others[0]["y"] + 7]})
        add("선끊김", a["part"], f"선 토막 끝 {len(es)}개가 3D {gap*1000:.1f}mm 안에 모임(틈·어긋남 후보{', 무늬일 수 있음' if many else ''}), 폭 {min(ws):.1f}~{max(ws):.1f}mm, 파츠 {'+'.join(parts)}",
            sc, [min(e["x"] for e in es if e["part"] == a["part"]) - 6, min(e["y"] for e in es if e["part"] == a["part"]) - 6,
                 max(e["x"] for e in es if e["part"] == a["part"]) + 7, max(e["y"] for e in es if e["part"] == a["part"]) + 7], a["isl"], a["p3"], extra)

# ---------- 4. 작은 얼룩 ----------
def chk_blob():
    for part, d in D.items():
        dE, _ = dE_to_base(d); lab = d["lab"]
        dev = (dE > 10) & ~excl_mask("뺄곳", "얼룩", part, lab, d["pos"])
        cl, n = ndi.label(dev, K8)
        if n == 0: continue
        sizes = np.bincount(cl.ravel()); big = (sizes >= 0); big[0] = False
        # 떨어진 정도: 다른 덩어리까지 거리(칸). 큰 덩어리(무늬)만의 거리 지도
        sl = ndi.find_objects(cl)
        tsmap = d["ts"][lab] * 1000
        amm = ndi.sum(tsmap ** 2, cl, np.arange(n + 1))
        dist_other = ndi.distance_transform_edt(~dev)
        for i, s in enumerate(sl, 1):
            if s is None or sizes[i] < 2 or amm[i] > 12: continue
            m = cl[s] == i; isl = int(np.bincount(lab[s][m]).argmax())
            y0, y1, x0, x1 = s[0].start, s[0].stop, s[1].start, s[1].stop
            pad = 30; Y0, Y1, X0, X1 = max(y0 - pad, 0), y1 + pad, max(x0 - pad, 0), x1 + pad
            others = dev[Y0:Y1, X0:X1] & (cl[Y0:Y1, X0:X1] != i)
            if others.any():
                dto = ndi.distance_transform_edt(~others); mm = np.zeros_like(others); mm[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0] = m
                gap = float(dto[mm].min()) * d["ts"][isl] * 1000
            else: gap = 10.0
            md = float(dE[s][m].mean())
            add("얼룩", part, f"작은 덩어리 {sizes[i]}칸({amm[i]:.1f}mm²), 바탕과 ΔE {md:.0f}, 이웃 무늬까지 {gap:.1f}mm",
                md * np.sqrt(sizes[i]) * (1 + min(gap, 10) / 3) * dw(part, (x0 + x1) / 2, (y0 + y1) / 2), [x0, y0, x1, y1], isl, d["pos"][y0 + np.nonzero(m)[0][0], x0 + np.nonzero(m)[1][0]])

# ---------- 5. 여백 ----------
def chk_pad():
    for part, d in D.items():
        lab, img, inside = d["lab"], d["img"].astype(np.int16), d["inside"]
        iy, ix = ndi.distance_transform_edt(~inside, return_distances=False, return_indices=True)
        gy, gx = np.indices(lab.shape); d2 = (iy - gy) ** 2 + (ix - gx) ** 2; del gy, gx
        exp = img.copy(); near = ~inside & (d2 <= 256); exp[near] = img[iy[near], ix[near]]
        pad = np.pad(inside, 1); ring = inside & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
        Lx = lab.max() + 1; cnt = np.bincount(lab[ring], minlength=Lx)
        mean = np.stack([np.bincount(lab[ring], weights=img[..., c][ring].astype(float), minlength=Lx) for c in range(3)], -1)
        mean = np.floor(mean / np.maximum(cnt, 1)[:, None] + 0.5)
        far = ~inside & (d2 > 256); exp[far] = mean[lab[iy[far], ix[far]]]
        bad = ~inside & (np.abs(exp - img).max(-1) > 8)
        black = ~inside & (img.max(-1) == 0)
        cl, n = ndi.label(bad | black, K8)
        sizes = np.bincount(cl.ravel())
        for i, s in enumerate(ndi.find_objects(cl), 1):
            if s is None or sizes[i] < 20: continue
            m = cl[s] == i; nb = int((black[s] & m).sum()); isl = int(lab[iy[s][m][0], ix[s][m][0]])
            add("여백", part, f"여백 {sizes[i]}칸이 기준(16칸 가장자리 색·그 밖 둘레 평균)과 다름{f', 검정 {nb}칸' if nb else ''}. 가장 가까운 조각 {isl}",
                np.sqrt(sizes[i]), [s[1].start, s[0].start, s[1].stop, s[0].stop], isl,
                None, {"점들": np.stack(np.nonzero(m)[::-1], 1) + [s[1].start, s[0].start]})
        summary.setdefault("여백_칸수", {})[part] = {"다른칸": int(bad.sum()), "검정": int(black.sum())}

# ---------- 6. 텍셀 밀도 ----------
def chk_density():
    for part, d in D.items():
        if part in HAIR: continue
        z = d["z"]; tc = np.clip(z["tric"].astype(int), 0, d["W"] - 1); li = d["lab"][tc[:, 1], tc[:, 0]]
        Lx = d["lab"].max() + 1
        a3 = np.bincount(li, weights=z["tri3d"], minlength=Lx); au = np.bincount(li, weights=z["triuv"], minlength=Lx)
        ok = (a3 > 0) & (np.arange(Lx) > 0)
        dens = np.zeros(Lx); dens[ok] = np.sqrt(au[ok] / a3[ok])
        idx = np.nonzero(ok)[0]; w = a3[idx]; o = np.argsort(dens[idx]); cw = np.cumsum(w[o]); med = dens[idx][o][np.searchsorted(cw, cw[-1] / 2)]
        summary.setdefault("밀도_중앙값(칸/m)", {})[part] = round(float(med))
        for i in idx:
            r = dens[i] / med
            if (r < 0.67 or r > 1.5) and a3[i] >= 1e-4:
                ys, xs = np.nonzero(d["lab"] == i)
                add("밀도", part, f"조각 {i} 밀도 {dens[i]:.0f}칸/m = 파츠 중앙값의 {r:.2f}배(3D {a3[i]*1e4:.1f}cm²)", abs(np.log(r)) * np.sqrt(a3[i] * 1e4),
                    bbox_of((ys, xs)), i)

# ---------- 7. 메시 ----------
def chk_mesh():
    mj = json.load(open(os.path.join(DD, "mesh.json"), encoding="utf-8"))
    for part in PARTS:
        m = mj.get(part)
        if not isinstance(m, dict): continue
        if not m: continue
        for l in m["열린가장자리고리"]:
            if l["정점"] <= 8 and l["폭(m)"] < 0.01:
                add("메시", part, f"작은 열린 고리(구멍 후보) 정점 {l['정점']}, 폭 {l['폭(m)']*1000:.1f}mm, 자리 {l['가운데']}", 5, [0, 0, 0, 0], None, l["가운데"])
        tot = m["정점"]
        for c in m["떠있는묶음"]:
            if c["정점"] < 0.01 * tot:
                cen = (np.array(c["상자"][0]) + np.array(c["상자"][1])) / 2
                add("메시", part, f"떠 있는 작은 묶음 정점 {c['정점']}(파츠의 {c['정점']/tot*100:.1f}%), 상자 {c['상자']}", 3, [0, 0, 0, 0], None, cen)
        for w in m["감김다른모서리"]:
            add("메시", part, f"이웃 면과 감김 방향이 다른 모서리(뒤집힌 노멀 후보) {w}", 4, [0, 0, 0, 0], None, w)
        for v in m["닫힌묶음_부피음수"]:
            add("메시", part, f"닫힌 묶음의 부피가 음수(노멀이 안쪽) 정점 {v['정점']}, 자리 {v['가운데']}", 6, [0, 0, 0, 0], None, v["가운데"])
        if m["넓이0면"]: add("메시", part, f"넓이 0인 면 {m['넓이0면']}개", 2, [0, 0, 0, 0])
        if m["세면이상모서리"]: add("메시", part, f"면 셋 이상이 쓰는 모서리 {m['세면이상모서리']}개", 2, [0, 0, 0, 0])
        summary.setdefault("메시_수", {})[part] = {"열린고리": len(m["열린가장자리고리"]), "떠있는묶음": len(m["떠있는묶음"]), "감김다름": len(m["감김다른모서리"])}

# ---------- 8. 좌우 ----------
def chk_sym():
    for part, d in D.items():
        mir = d["z"]["mir"]
        if not len(mir): continue
        lab, pos, LABc = d["lab"], d["pos"], d["LAB"]
        px, py = mir[:, 0].astype(int), mir[:, 1].astype(int); qx = np.clip(mir[:, 2].astype(int), 0, d["W"] - 1); qy = np.clip(mir[:, 3].astype(int), 0, d["H"] - 1)
        mx = float(d["z"]["mx"]) if "mx" in d["z"] else 0.0
        keep = (pos[py, px, 0] > mx) & (lab[qy, qx] > 0)
        ex = excl_mask("비대칭", "좌우", part, lab, pos) | excl_mask("뺄곳", "좌우", part, lab, pos)
        keep &= ~ex[py, px] & ~ex[qy, qx]
        px, py, qx, qy = px[keep], py[keep], qx[keep], qy[keep]
        de = np.linalg.norm(LABc[py, px] - LABc[qy, qx], axis=-1)
        bad = de > 15
        grid = np.zeros((d["H"] // 2 + 1, d["W"] // 2 + 1), bool); grid[py[bad] // 2, px[bad] // 2] = True
        grid = ndi.binary_closing(grid, np.ones((3, 3)))
        cl, n = ndi.label(grid, K8)
        if n == 0: continue
        gid = cl[py // 2, px // 2]
        for i in range(1, n + 1):
            sel = (gid == i) & bad
            if sel.sum() < 3: continue
            isl = int(np.bincount(lab[py[sel], px[sel]]).argmax())
            add("좌우", part, f"거울 자리끼리 색이 다름 {sel.sum()*4}칸쯤, ΔE 평균 {de[sel].mean():.0f}(+x 쪽 조각 {isl}, 거울 쪽 조각 {int(np.bincount(lab[qy[sel], qx[sel]]).argmax())})",
                de[sel].mean() * np.sqrt(sel.sum()) * dw(part, np.median(px[sel]), np.median(py[sel])), [px[sel].min(), py[sel].min(), px[sel].max() + 2, py[sel].max() + 2], isl,
                pos[py[sel][0], px[sel][0]], {"건너편상자": [int(qx[sel].min()), int(qy[sel].min()), int(qx[sel].max()) + 2, int(qy[sel].max()) + 2],
                 "점들": np.stack([px[sel], py[sel]], 1), "건너편점들": np.stack([qx[sel], qy[sel]], 1)})

# ---------- 9. 구운 그늘 ----------
def chk_shade():
    for part, d in D.items():
        if part in HAIR: continue
        dE, _ = dE_to_base(d); lab = d["lab"]
        m = (dE > 4) & d["inside"]
        m &= ~excl_mask("그라데이션", "그늘", part, lab, d["pos"]) & ~excl_mask("뺄곳", "그늘", part, lab, d["pos"])
        wide = ndi.binary_opening(m, np.ones((9, 9), bool))          # 폭 9칸보다 가는 선·무늬는 빠진다
        wide &= lab == ndi.grey_erosion(lab, size=(3, 3))            # 조각 경계 걸침 제거
        cl, n = ndi.label(wide, K8)
        sizes = np.bincount(cl.ravel())
        for i, s in enumerate(ndi.find_objects(cl), 1):
            if s is None or sizes[i] < 150: continue
            mm = cl[s] == i; isl = int(np.bincount(lab[s][mm]).argmax())
            v = dE[s][mm]
            hv = np.bincount(np.round(v).astype(int)); pk = int(hv.argmax())
            if (np.abs(v - pk) <= 3).mean() > 0.5: continue              # 칸 절반 넘게 한 값 = 한 색으로 칠한 면·굵은 선(그늘은 값이 퍼져 있다)
            if np.percentile(v, 90) - np.percentile(v, 10) < 8: continue   # 한 색으로 고르게 칠한 면(띠의 줄, 테 등)은 그늘이 아니다
            soft = float((v < 0.5 * np.percentile(v, 90)).mean())       # 옅은 칸의 비율: 그늘은 서서히 바뀌어 높고, 칠한 면은 낮다
            if soft < 0.1: continue
            yy, xx = np.nonzero(mm); cy, cx = int(yy[len(yy) // 2] + s[0].start), int(xx[len(xx) // 2] + s[1].start)
            add("그늘", part, f"단색이어야 할 조각 {isl} 안의 넓은 밝기 변화 {sizes[i]}칸, ΔE 중앙 {np.median(v):.0f}(최대 {v.max():.0f}), 옅은 칸 비율 {soft:.2f}",
                np.sqrt(sizes[i]) * np.median(v) * (0.5 + soft), [s[1].start, s[0].start, s[1].stop, s[0].stop], isl, d["pos"][cy, cx],
                {"점들": np.stack([xx + s[1].start, yy + s[0].start], 1)})

# ---------- 10. 색 ----------
def chk_color():
    pal = np.array(CFG.get("색목록", []), np.int16).reshape(-1, 3)
    rows = []
    for part, d in D.items():
        for i in range(1, len(d["base"])):
            if d["area"][i] < 2000: continue
            rows.append((part, i, d["base"][i].astype(np.int16), d["area"][i]))
    for part, i, c, a in rows:
        if part in HAIR and not len(pal): continue
        if len(pal) and np.abs(pal - c).max(1).min() > 3:
            ys, xs = np.nonzero(D[part]["lab"] == i)
            add("색", part, f"조각 {i} 바탕색 {tuple(int(v) for v in c)}가 색목록에 없음(가장 가까운 {tuple(int(v) for v in pal[np.abs(pal - c).max(1).argmin()])})", 5, bbox_of((ys, xs)), i)
    seen = set()
    for x in range(len(rows)):
        for y in range(x + 1, len(rows)):
            dc = int(np.abs(rows[x][2] - rows[y][2]).max())
            inpal = lambda c: len(pal) and np.abs(pal - c).max(1).min() <= 3
            if 0 < dc <= 6 and not (inpal(rows[x][2]) and inpal(rows[y][2])):     # 둘 다 색목록에 있으면 일부러 다른 색
                k = (tuple(rows[x][2]), tuple(rows[y][2]))
                if k in seen: continue
                seen.add(k); seen.add(k[::-1])
                ys, xs = np.nonzero(D[rows[x][0]]["lab"] == rows[x][1])
                add("색", rows[x][0], f"바탕색이 거의 같은데 다름: {rows[x][0]} 조각 {rows[x][1]} {tuple(int(v) for v in rows[x][2])} ↔ {rows[y][0]} 조각 {rows[y][1]} {tuple(int(v) for v in rows[y][2])}(채널 차이 {dc})",
                    4 + dc, bbox_of((ys, xs)), rows[x][1], None, {"건너편파츠": rows[y][0], "건너편조각": int(rows[y][1])})

def hair_filter():
    global cands
    cands = [c for c in cands if not (c["파츠"] in HAIR and c["검사"] not in HAIR_OK)]

t_all = time.time()
run("이음매", chk_seam)
if "선굵기" in CHECKS or "선끊김" in CHECKS:
    t0 = time.time(); build_lines(); times["선(공통)"] = round(time.time() - t0, 1)
run("선굵기", chk_width); run("선끊김", chk_break); run("얼룩", chk_blob); run("여백", chk_pad); run("밀도", chk_density)
run("메시", chk_mesh); run("좌우", chk_sym); run("그늘", chk_shade); run("색", chk_color)
hair_filter()
for c in cands: c["순위"] = 0
for chk in ALL:
    cs = sorted([c for c in cands if c["검사"] == chk], key=lambda c: -c["점수"])
    for r, c in enumerate(cs, 1): c["순위"] = r
cands.sort(key=lambda c: (ALL.index(c["검사"]), c["순위"]))
json.dump(cands, open(os.path.join(OUT, "후보.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
with open(os.path.join(OUT, "후보.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f); w.writerow(["검사", "순위", "파츠", "조각", "상자", "점수", "설명"])
    for c in cands: w.writerow([c["검사"], c["순위"], c["파츠"], c["조각"], " ".join(map(str, c["상자"])), c["점수"], c["설명"]])
cnt = {k: sum(1 for c in cands if c["검사"] == k) for k in ALL if k in CHECKS}
json.dump({"후보수": cnt, "걸린시간(초)": times, "전체(초)": round(time.time() - t_all, 1), "기타": {k: v for k, v in summary.items() if not isinstance(v, int)}},
          open(os.path.join(OUT, "요약.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("텍스처검사 후보 " + json.dumps(cnt, ensure_ascii=False) + f" ({round(time.time() - t_all)}초) → {OUT}")
