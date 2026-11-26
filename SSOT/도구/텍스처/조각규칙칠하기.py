# 조각규칙칠하기.py — 옷 파츠(상체·하체)의 남은 얼룩을 조각별 규칙으로 지운다(5-6). v001(지킬 상자 밖 전부 덮기)은 얼굴용.
# 규칙(조각 번호는 조각지도.py가 낸 조각 지도의 번호):
#   --단색 a,b,..         조각 전체를 한 색으로(그 조각의 가장 흔한 색). a=r.g.b 로 색을 정할 수 있다(예: 14=40.36.40)
#   --줄 a,b:문턱[:r.g.b[:r.g.b]] 검은 띠의 흰 줄: 밝기를 살짝 흐린 뒤 문턱보다 밝으면 줄 색(밝은 칸의 중앙값 또는 두 번째 r.g.b), 아니면 바탕색(첫 r.g.b). 가장자리는 매끈하게
#   --바꿈 r.g.b=r.g.b;..  파츠의 조각 안에서 정확히 앞 색인 칸을 뒤 색으로(파츠끼리 같은 부위의 바탕색을 맞출 때). 맨 마지막에 한다
#   --지움 x0,y0,x1,y1;.. 상자 안에서 바탕과 다른 칸을 바탕색으로(깃 안쪽 그늘 등)
#   --선 x0,y0,x1,y1,방향,굵기[,r.g.b];..  토막 대신 P<x>.<y> 를 + 로 이으면 그 자리를 반드시 지나는 점(끝을 다른 선에 닿게 할 때)  지움 전에 상자 안 어두운 칸의 바깥 가장자리(방향 L·R·T·B 쪽에서 처음 만나는 어두운 칸)를 따라
#                         선 중심을 구해, 지운 뒤 같은 자리에 매끈한 선(원래 선 색)으로 다시 그린다(깃의 선)
#   --어둠 a,b:문턱:r.g.b[:x0,y0,x1,y1];..  조각(과 상자) 안을 두 색으로: 밝기를 살짝 흐린 뒤 문턱보다 어두우면 r.g.b(소매 안감 등), 아니면 바탕색. 가장자리 매끈
#   --테 a:폭:r.g.b:x0,y0,x1,y1;..  상자 안에서 조각 가장자리(조각 밖과 맞닿은 곳)부터 폭 칸까지를 r.g.b 한 색, 나머지 다른 칸은 바탕색(소매 끝 안감 테)
#   --솔기선(·--솔기선2) 굵기:r.g.b:조각[@지울반지름]:x.y,x.y,..;조각:x.y,..  두 조각에 걸친 선(앞섶 선처럼 UV 이음매 위에 놓인 선)을 이음매 가운데에 같은 굵기로 다시 그린다.
#                         조각마다 이음매의 UV 꺾은선(Blender에서 같은 모서리를 두 조각에서 읽은 것)을 주면, 둘레 14칸(또는 @로 준 반지름)의 어두운 칸을 지운 뒤 굵기의 반씩 양쪽 조각에 그린다
#   --테선 조각:폭:r.g.b:지울반지름:x.y,x.y,..;..  메시의 소매 끝 둘레(이음매)를 UV 꺾은선으로 주면, 둘레에서 지울반지름 안의 어두운 칸(밝기가 바탕보다 25 이상 낮음)을
#                         바탕색으로 지운 뒤, 꺾은선에서 조각 안쪽으로 폭 칸의 띠를 한 색으로 그린다(꺾은선을 중심으로 폭×2 굵기, 조각 밖은 잘림). 모든 자리에서 같은 폭
#   --티 a,b:넓이         흰 조각에서 넓이 이하의 외딴 점(가까운 15칸 안에 큰 무늬가 없는 것)을 지운다
# 마지막에 여백을 다시 채운다. 입력 그림은 고치지 않고 출력 폴더에 쓴다(같은 폴더면 덮어씀).
# 사용: python 조각규칙칠하기.py <조각지도 폴더> <그림 폴더> <출력 폴더> <파츠> [규칙...]
import sys, os, json, subprocess
import numpy as np, cv2
from PIL import Image

if len(sys.argv) < 5 or (len(sys.argv) - 5) % 2: raise SystemExit("사용: <조각지도 폴더> <그림 폴더> <출력 폴더> <파츠> [--규칙 값 ...]")
MAPD, IND, OUTD, PART = sys.argv[1:5]
opt = dict(zip(sys.argv[5::2], sys.argv[6::2]))
if len(opt) != len(sys.argv[5::2]): raise SystemExit("같은 규칙을 두 번 주었다(한 규칙 안에서 ;로 이어 쓴다)")
KNOWN = {"--단색", "--줄", "--지움", "--선", "--어둠", "--테", "--솔기선", "--솔기선2", "--테선", "--티", "--바꿈"}
bad = [k for k in opt if k not in KNOWN]
if bad: raise SystemExit(f"모르는 규칙: {bad}")
empty = [k for k, v in opt.items() if not v.strip() or v.startswith("--")]
if empty: raise SystemExit(f"값이 빈 규칙: {empty}")
os.makedirs(OUTD, exist_ok=True)
lab = np.flipud(np.load(os.path.join(MAPD, f"{PART}_조각지도.npy")))
img = np.array(Image.open(os.path.join(IND, f"{PART}_구움.png")).convert("RGB"))
if img.shape[:2] != lab.shape: raise SystemExit(f"그림 크기 {img.shape[:2]}와 조각 지도 {lab.shape}가 다르다")
HAVE = set(np.unique(lab).tolist()) - {0}
def need(ids, rule):
    miss = [i for i in ids if i not in HAVE]
    if miss: raise SystemExit(f"{rule}: 조각 {miss}이(가) {PART} 조각 지도에 없다")
    return ids
need([int(t.partition("=")[0]) for t in opt.get("--단색", "").split(",") if t], "--단색")
if "--줄" in opt: need([int(v) for v in opt["--줄"].split(":")[0].split(",")], "--줄")
if "--티" in opt: need([int(v) for v in opt["--티"].split(":")[0].split(",")], "--티")
for t in [t for t in opt.get("--어둠", "").split(";") if t]: need([int(v) for v in t.split(":")[0].split(",")], "--어둠")
for t in [t for t in opt.get("--테", "").split(";") if t]: need([int(t.split(":")[0])], "--테")
for SK in ("--솔기선", "--솔기선2"):
    for t in [t for t in opt[SK].split(":", 2)[2].split(";") if t] if SK in opt else []: need([int(t.split(":")[0].partition("@")[0])], SK)
for t in [t for t in opt.get("--테선", "").split(";") if t]: need([int(t.split(":")[0])], "--테선")
for b in [b for b in opt.get("--지움", "").split(";") if b]:
    v = [int(x) for x in b.split(",")]
    if len(v) != 4 or not (0 <= v[0] < v[2] <= lab.shape[1] and 0 <= v[1] < v[3] <= lab.shape[0]): raise SystemExit(f"--지움 상자가 그림 밖이거나 꼴이 틀렸다: {b}")
    if not (lab[v[1]:v[3], v[0]:v[2]] > 0).any(): raise SystemExit(f"--지움 상자 안에 조각이 없다: {b}")
out = img.copy(); rep = {}

def mode_color(m):
    px = img[m].astype(np.int64)
    key = px[:, 0] * 65536 + px[:, 1] * 256 + px[:, 2]
    v, c = np.unique(key, return_counts=True); k = v[c.argmax()]
    return np.array([k // 65536, (k // 256) % 256, k % 256], np.uint8)

def off_mask(m, base, tol=3):
    return m & (np.abs(img.astype(int) - base.astype(int)).max(-1) > tol)

# 단색
for tok in [t for t in opt.get("--단색", "").split(",") if t]:
    i, _, col = tok.partition("=")
    m = lab == int(i); base = np.array([int(v) for v in col.split(".")], np.uint8) if col else mode_color(m)
    n = int((m & (np.abs(out.astype(int) - base.astype(int)).max(-1) > 0)).sum()); out[m] = base
    rep[f"단색{i}"] = {"색": base.tolist(), "바꾼 칸": n}

# 줄(검은 띠의 흰 줄)
if "--줄" in opt:
    ids, thr, *bc = opt["--줄"].split(":"); thr = float(thr); sc = bc[1] if len(bc) > 1 else None
    L = cv2.GaussianBlur(img.mean(-1).astype(np.float32), (0, 0), 1.5)
    for i in [int(v) for v in ids.split(",")]:
        m = lab == i; base = np.array([int(v) for v in bc[0].split(".")], np.uint8) if bc else mode_color(m)
        sm = cv2.GaussianBlur(((L > thr) & m).astype(np.float32), (0, 0), 1.2) > 0.5   # 줄 가장자리 매끈하게
        stripe = sm & m
        scol = np.array([int(v) for v in sc.split(".")], np.uint8) if sc else (np.median(img[stripe & (img.mean(-1) > thr)], axis=0).astype(np.uint8) if stripe.any() else base)
        out[m] = base; out[stripe] = scol
        rep[f"줄{i}"] = {"바탕": base.tolist(), "줄색": scol.tolist(), "줄 칸": int(stripe.sum())}

# 어둠(안감 등: 어두운 테는 한 색, 그 둘레 회색 그늘은 바탕색)
for spec in [t for t in opt.get("--어둠", "").split(";") if t]:
    ids, thr, col, *bx = spec.split(":"); thr = float(thr); col = np.array([int(v) for v in col.split(".")], np.uint8)
    region = np.ones(lab.shape, bool)
    if bx:
        x0, y0, x1, y1 = [int(v) for v in bx[0].split(",")]; region = np.zeros(lab.shape, bool); region[y0:y1, x0:x1] = True
    L = cv2.GaussianBlur(img.mean(-1).astype(np.float32), (0, 0), 1.5)
    for i in [int(v) for v in ids.split(",")]:
        m = (lab == i) & region; base = mode_color(lab == i)
        dk = (cv2.GaussianBlur(((L < thr) & m).astype(np.float32), (0, 0), 1.2) > 0.5) & m
        ch = m & ((np.abs(img.astype(int) - base.astype(int)).max(-1) > 3) | dk)
        out[ch] = base; out[dk] = col
        rep[f"어둠{i}{bx}"] = {"어두운 칸": int(dk.sum()), "바꾼 칸": int(ch.sum())}

# 테(조각 가장자리를 따라 같은 폭의 띠)
for spec in [t for t in opt.get("--테", "").split(";") if t]:
    i, wd, col, bx = spec.split(":"); i = int(i); wd = float(wd); col = np.array([int(v) for v in col.split(".")], np.uint8)
    x0, y0, x1, y1 = [int(v) for v in bx.split(",")]
    region = np.zeros(lab.shape, bool); region[y0:y1, x0:x1] = True
    isl = lab == i; base = mode_color(isl)
    S = 4   # 초과 표본으로 거리를 재서 띠 안쪽 경계를 매끈하게
    sub = isl[y0 - 2:y1 + 2, x0 - 2:x1 + 2].astype(np.uint8)
    big = cv2.resize(sub, (sub.shape[1] * S, sub.shape[0] * S), interpolation=cv2.INTER_NEAREST)
    big = cv2.GaussianBlur(big.astype(np.float32), (0, 0), S * 0.8) > 0.5
    dist = cv2.distanceTransform(big.astype(np.uint8), cv2.DIST_L2, 5) / S
    a = cv2.resize(((dist > 0) & (dist <= wd)).astype(np.float32), (sub.shape[1], sub.shape[0]), interpolation=cv2.INTER_AREA)
    alpha = np.zeros(lab.shape, np.float32); alpha[y0 - 2:y1 + 2, x0 - 2:x1 + 2] = a
    m = isl & region
    ch = m & ((np.abs(img.astype(int) - base.astype(int)).max(-1) > 3) | (alpha > 0))
    out[ch] = base
    al = (alpha * m)[..., None]
    out[:] = np.where(al > 0, (out * (1 - al) + col * al), out).astype(np.uint8)
    rep[f"테{i}"] = {"테 칸": int((alpha * m > 0.5).sum()), "바꾼 칸": int(ch.sum())}

# 선 찾기(지우기 전, 원래 그림에서). 한 선을 여러 토막으로 찾을 때는 토막을 + 로 잇는다(이어지는 순서로 붙여 한 줄로 그린다)
def scan(seg):
    x0, y0, x1, y1, d, w, *lc = seg.split(","); x0, y0, x1, y1, w = int(x0), int(y0), int(x1), int(y1), int(w)
    if d not in ("L", "R", "T", "B"): raise SystemExit(f"--선: 방향은 L·R·T·B 가운데 하나: {d}")
    dark = img.mean(-1) < 110
    bl = lab[y0:y1, x0:x1][dark[y0:y1, x0:x1] & (lab[y0:y1, x0:x1] > 0)]
    if len(bl) == 0: raise SystemExit(f"--선: 상자 {seg}에 어두운 칸이 없다")
    dark = dark & (lab == np.bincount(bl).argmax())   # 상자 안 어두운 칸이 가장 많은 조각 하나에서만 찾는다
    pts = []
    if d in "LR":
        for y in range(y0, y1):
            xs = np.nonzero(dark[y, x0:x1])[0]
            if len(xs): pts.append((x0 + (xs[0] + w / 2 if d == "L" else xs[-1] - w / 2), y))
    else:
        for x in range(x0, x1):
            ys = np.nonzero(dark[y0:y1, x])[0]
            if len(ys): pts.append((x, y0 + (ys[0] + w / 2 if d == "T" else ys[-1] - w / 2)))
    col = np.array([float(v) for v in lc[0].split(".")]) if lc else np.median(img[y0:y1, x0:x1][dark[y0:y1, x0:x1]], axis=0)
    return np.array(pts, np.float32), w, col, int(np.bincount(bl).argmax())
lines = []
for spec in [s for s in opt.get("--선", "").split(";") if s]:
    pts = None; anchors = []
    for seg in spec.split("+"):
        if seg.startswith("P"):
            ap = np.array([[float(v) for v in seg[1:].split(".")]], np.float32)
            if pts is None: anchors.append(0); pts = ap; first = False
            else: anchors.append(len(pts)); pts = np.concatenate([pts, ap])
            continue
        q, w, col, isl = scan(seg)
        if pts is not None and len(q):
            ends = [pts[-1]] + ([pts[0]] if first else [])   # 첫 토막만 방향을 뒤집을 수 있다
            best = min(((np.linalg.norm(e - qq), ei, qi) for ei, e in enumerate(ends) for qi, qq in enumerate((q[0], q[-1]))))
            if best[1] == 1: pts = pts[::-1]
            if best[2] == 1: q = q[::-1]
            pts = np.concatenate([pts, q]); first = False
        else: pts = q; first = True
    # 매끈하게(꺾임 없이): 1칸 간격으로 다시 놓고, 길이를 변수로 한 4차 다항식에 맞춘다. 토막 이음매·가장자리 들쭉날쭉이 사라진다
    # (사용자 방침 2026-11-23: 옷선을 따라 이어지는 선에는 꺾임이 없어야 한다)
    seg_len = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    t = np.arange(0, seg_len[-1], 1.0)
    pa = pts[anchors]; ta = seg_len[anchors]
    pts = np.stack([np.interp(t, seg_len, pts[:, j]) for j in (0, 1)], 1)
    tf = np.r_[t, ta] / t[-1]; wt = np.r_[np.ones(len(t)), np.full(len(ta), 200.0)]   # 지나야 할 점은 무게를 크게
    tt = t / t[-1]
    pts = np.stack([np.polyval(np.polyfit(tf, np.r_[pts[:, j], pa[:, j]], 4, w=wt), tt) for j in (0, 1)], 1).astype(np.float32)
    x0, y0 = np.floor(pts.min(0)).astype(int) - 2; x1, y1 = np.ceil(pts.max(0)).astype(int) + 2
    lines.append((pts, w, col, (max(x0, 0), max(y0, 0), x1, y1), isl))

# 지움
for b in [s for s in opt.get("--지움", "").split(";") if s]:
    x0, y0, x1, y1 = [int(v) for v in b.split(",")]
    box = np.zeros(lab.shape, bool); box[y0:y1, x0:x1] = True
    for i in np.unique(lab[box]):
        if i == 0: continue
        m = lab == i; base = mode_color(m); t = off_mask(m, base) & box
        out[t] = base; rep[f"지움{b}/{i}"] = int(t.sum())

# 솔기선(이음매 위의 선): 지우고 그 조각 안쪽 반을 그림. V 선보다 먼저 그려 V 선 끝이 위에 얹히게
for SK in ("--솔기선", "--솔기선2"):   # 2는 굵기·색이 다른 두 번째 묶음
    if SK not in opt: continue
    w, col, *rest = opt[SK].split(":", 2); w = float(w); col = np.array([float(v) for v in col.split(".")])
    for part in rest[0].split(";"):
        i, pl = part.split(":"); i, _, rr = i.partition("@"); i = int(i); rr = float(rr) if rr else 14.0   # 조각@지울반지름
        P = np.array([[float(v) for v in q.split(".")] for q in pl.split(",")], np.float32)
        isl = lab == i; base = mode_color(isl)
        er = np.zeros(lab.shape, np.uint8); cv2.polylines(er, [P.round().astype(np.int32).reshape(-1, 1, 2)], False, 1, int(2 * rr))
        t = (er > 0) & isl & (out.mean(-1) < base.mean() - 12); out[t] = base
        S = 4
        x0, y0 = np.floor(P.min(0)).astype(int) - 12; x1, y1 = np.ceil(P.max(0)).astype(int) + 12
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, lab.shape[1]), min(y1, lab.shape[0])
        sub = np.zeros(((y1 - y0) * S, (x1 - x0) * S), np.uint8)
        cv2.polylines(sub, [((P - [x0, y0]) * S).astype(np.int32).reshape(-1, 1, 2)], False, 255, int(w * S), cv2.LINE_AA)
        a = cv2.resize(sub, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA).astype(np.float32) / 255 * isl[y0:y1, x0:x1]
        out[y0:y1, x0:x1] = (out[y0:y1, x0:x1] * (1 - a[..., None]) + col * a[..., None]).astype(np.uint8)
        if not (a > 0.5).any(): raise SystemExit(f"{SK} 조각 {i}: 꺾은선이 조각 밖이라 그린 칸이 0이다")
        rep[f"{SK[2:]}{i}"] = {"지운 칸": int(t.sum()), "그린 칸": int((a > 0.5).sum())}

# 테선(소매 끝 둘레를 따라 같은 폭의 띠)
for spec in [t for t in opt.get("--테선", "").split(";") if t]:
    i, wd, col, rad, pl = spec.split(":"); i = int(i); wd = float(wd); rad = float(rad); col = np.array([float(v) for v in col.split(".")])
    isl = lab == i
    if not isl.any(): raise SystemExit(f"--테선: 조각 {i}이(가) 조각 지도에 없다")
    P = np.array([[float(v) for v in q.split(".")] for q in pl.split(",")], np.float32)
    if len(P) < 2: raise SystemExit("--테선: 꺾은선 점이 2개보다 적다")
    base = mode_color(isl)
    er = np.zeros(lab.shape, np.uint8); cv2.polylines(er, [P.round().astype(np.int32).reshape(-1, 1, 2)], False, 1, int(2 * rad))
    t = (er > 0) & isl & (out.astype(int).mean(-1) < base.astype(int).mean() - 25); out[t] = base
    x0, y0 = np.floor(P.min(0)).astype(int) - int(wd) - 4; x1, y1 = np.ceil(P.max(0)).astype(int) + int(wd) + 4
    x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, lab.shape[1]), min(y1, lab.shape[0]); S = 4
    sub = np.zeros(((y1 - y0) * S, (x1 - x0) * S), np.uint8)
    cv2.polylines(sub, [((P - [x0, y0]) * S).astype(np.int32).reshape(-1, 1, 2)], False, 255, int(2 * wd * S), cv2.LINE_AA)
    a = cv2.resize(sub, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA).astype(np.float32) / 255 * isl[y0:y1, x0:x1]
    out[y0:y1, x0:x1] = (out[y0:y1, x0:x1] * (1 - a[..., None]) + col * a[..., None]).astype(np.uint8)
    if not (a > 0.5).any(): raise SystemExit(f"--테선 조각 {i}: 꺾은선이 조각 밖이라 그린 칸이 0이다")
    rep[f"테선{i}"] = {"지운 칸": int(t.sum()), "그린 칸": int((a > 0.5).sum())}

# 선 다시 그리기(초과 표본으로 매끈하게)
for pts, w, col, (x0, y0, x1, y1), isl in lines:
    S = 4
    sub = np.zeros(((y1 - y0 + 2 * w) * S, (x1 - x0 + 2 * w) * S), np.uint8)
    p = ((pts - [x0 - w, y0 - w]) * S).astype(np.int32).reshape(-1, 1, 2)
    cv2.polylines(sub, [p], False, 255, thickness=w * S, lineType=cv2.LINE_AA)
    a = cv2.resize(sub, (x1 - x0 + 2 * w, y1 - y0 + 2 * w), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    ys, xs = slice(max(y0 - w, 0), y1 + w), slice(max(x0 - w, 0), x1 + w)
    a = a[: out[ys, xs].shape[0], : out[ys, xs].shape[1]] * (lab[ys, xs] == isl)   # 선은 그 조각 안에만
    out[ys, xs] = (out[ys, xs] * (1 - a[..., None]) + col * a[..., None]).astype(np.uint8)
    rep[f"선{x0},{y0}"] = {"점": len(pts), "색": col.astype(int).tolist(), "처음": pts[0].round(1).tolist(), "끝": pts[-1].round(1).tolist()}

# 티(외딴 점)
if "--티" in opt:
    ids, area = opt["--티"].split(":"); area = int(area)
    for i in [int(v) for v in ids.split(",")]:
        m = lab == i; base = mode_color(m); t = off_mask(m, base, 10).astype(np.uint8)
        n, cc, st, _ = cv2.connectedComponentsWithStats(t, connectivity=8)
        big = np.isin(cc, np.nonzero(st[:, 4] > area)[0]) & (cc > 0)
        near = cv2.dilate(big.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))) > 0
        small = np.isin(cc, np.nonzero((st[:, 4] <= area))[0]) & (cc > 0) & ~near
        grow = cv2.dilate(small.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0   # 점 둘레의 옅은 칸까지
        tt = grow & off_mask(m, base) ; out[tt] = base
        rep[f"티{i}"] = int(tt.sum())

# 바꿈(맨 마지막)
for t in [t for t in opt.get("--바꿈", "").split(";") if t]:
    a_, b_ = t.split("="); ca = np.array([int(v) for v in a_.split(".")]); cb = np.array([int(v) for v in b_.split(".")], np.uint8)
    m = (lab > 0) & (out.astype(int) == ca).all(-1); out[m] = cb; rep[f"바꿈{a_}"] = int(m.sum())
    if not m.any(): raise SystemExit(f"--바꿈: {a_} 색인 칸이 없다")
for k in ("--선",):
    for spec in [x for x in opt.get(k, "").split(";") if x]:
        if not any(not seg.startswith("P") for seg in spec.split("+")): raise SystemExit(f"{k}: 찾을 토막이 없다 {spec}")
Image.fromarray(out).save(os.path.join(OUTD, f"{PART}_구움.png"))
print("얼룩지우기v002 " + PART + " " + json.dumps(rep, ensure_ascii=False), flush=True)
here = os.path.dirname(os.path.abspath(__file__))
import gc   # 이 컴퓨터는 가상 메모리 여유가 적어, 여백 채우기를 부르기 전에 큰 배열을 놓아 준다
for _k in [k for k, v in list(globals().items()) if type(v).__name__ == "ndarray"]: del globals()[_k]
gc.collect()
subprocess.run([sys.executable, os.path.join(here, "여백채우기.py"), MAPD, OUTD, "{}_구움.png", OUTD, "--파츠", PART], check=True, stdout=subprocess.DEVNULL)
