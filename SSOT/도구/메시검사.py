# 메시검사.py — 기본은 "조각 목록": 서로 이어지지 않은 조각을 크기와 상관없이 전부 한 칸씩 색칠해 보여 준다. 사용자가 그림을 훑어
# 입력 그림에 없는 것(노이즈 조각)을 직접 고른다(사용자 결정 2026-11-23: 후보를 사람이 보고 걸러낸다).
# 옵션으로 파츠 메시의 결함 후보(떠 있는 조각, 매달린 묶음, 아주 작은 면, 겹친 변, 작은 구멍, 패임, 돌출, 자체 가림)도 고른다.
# 근거 수치와 색칠한 모음 그림(긴 변 약 1000px)을 만든다. blend 파일은 읽기만 하고 저장하지 않는다. 메시 형태는 바꾸지 않는다.
# 교복 사무라이의 파츠검사_v001.py(01_캐릭터/교복_사무라이/04_Blender/SmartMesh_리깅보정/스크립트/)를 어느 캐릭터에나 쓰도록 옮긴 것이다.
#
# 사용(Git Bash):
#   SSOT/도구/블렌더실행.sh <blend> SSOT/도구/메시검사.py -- <출력폴더> [선택]
#   선택:
#     --객체 a,b           검사할 객체(기본: 이름이 "파츠_"로 시작하는 메시 전부). 가림 검사는 이 객체들끼리 본다
#     --장면 이름           검사할 장면(기본: 파일을 열었을 때의 장면)
#     --검사 a,b            할 검사(기본 조각). 조각 = 조각 목록. 그 밖에 플로터, 매달린묶음, 미세면, 겹친변, 작은구멍, 패임, 돌출, 자체가림.
#                           전부 = 조각 목록과 여덟 가지 모두. 여덟 가지는 노이즈보다 원래 모양이 훨씬 많이 걸린다(온천 검사 74개 중 노이즈 0)
#     --조각최대 N           조각 목록 그림에 넣을 조각 수(기본 60, 작은 것부터)
#     --확대 N              파츠마다 확대 그림을 만들 후보 수(기본 15. 0이면 확대 그림 없음). 순서는 위 검사 순서, 같은 종류는 면이 많은 것부터
#     --그림 요철,가림       파츠별 요철 색(빨강 돌출·파랑 패임)·가림 색(보라 자체 가림·파랑 다른 파츠에 가림) 모음 그림도 만든다
#   기준값(기본값은 교복 사무라이에서 정한 값. 확정 규칙이 아니다):
#     --미세면적 2e-6       이보다 작은 면은 미세 면. 단위는 (모델 높이)² — 모델 키가 1 m면 m²와 같다. 키가 다른 모델에도 같은 비율로 적용된다
#     --미세비율 0.08       이웃 면 넓이 중앙값의 이 비율 미만이면 미세 면
#     --매달린최대면 60      정점으로만 매달린 묶음으로 볼 최대 면 수
#     --플로터비율 0.02      파츠 면 수의 이 비율 미만인 떨어진 덩어리는 플로터 후보
#     --요철비율 0.010       파츠 대각선의 이 비율 이상 들어가거나 나온 곳은 패임·돌출 후보
#     --구멍비율 0.06        열린 테두리의 크기가 파츠 대각선의 이 비율 미만이면 작은 구멍 후보
#   결과(<출력폴더>/):
#     후보목록.md            사람이 읽는 표. 조각 목록(번호, 면 수, 크기, 자리, 다른 표면까지 거리, 보이는면 비율)과 여덟 가지 후보. 근거의 "보이는면_비율"은 다른 파츠까지 넣고 바깥(120방향)에서 보이는 면의 비율
#     검사결과.json          파츠별 수치와 후보 전부. 조각·후보마다 "면번호"(그 객체의 면 번호 전부) — 제작 페이지 3단계가 후보를 3D 보기에 칠한다
#     모음_조각_전체.png     조각(객체마다 가장 큰 조각, 곧 몸통을 뺀 것)을 빨강으로 칠한 12방향
#     모음_조각_N.png        조각마다 두 칸: 가까이(그 조각만 빨강, 다른 객체도 보임) · 넓게(같은 방향). 한 장에 조각 10개.
#                           어디서도 안 보이는 조각(그 방향에서 보이는 비율 0.05 미만)은 투시(X-ray)로 찍고 칸 이름에 "투시"를 붙인다
#     모음_전체.png          (여덟 가지 검사를 할 때) 모든 파츠를 함께 후보 색으로(12방향, 아래에서 올려다보는 각도 포함)
#     모음_<파츠>.png        파츠 하나만 후보 색으로(같은 12방향)
#     모음_확대_<파츠>_N.png 후보마다 두 칸: 가까이(그 후보만 색칠, 그 파츠만) · 넓게(같은 방향). 한 장에 후보 10개. 칸 위 글자가 후보 번호
#     _tmp/                 낱장(400px). git에 올리지 않는다
#   후보 색: 빨강 플로터, 주황 매달린 묶음, 분홍 미세 면, 노랑 겹친 변, 하늘 작은 구멍, 파랑 패임, 초록 돌출, 보라 자체 가림.
#   방향 표기는 다각도검수.py와 같다: az(0 = 앞에서 봄, 90 = 화면 오른쪽 +x에서 봄) / el(위로 +, 아래에서 올려다보면 -).
#   아래에서 올려다보는 각도를 빼지 않는다(사용자 결정 2026-11-23, SSOT/41_사용자_방침.md "치마 속").
#   후보는 수치로 고른 것이다. 지우거나 고치기 전에 그림으로 확인하고 사용자 승인을 받는다(SSOT/단계/3_메시.md).
#   정지 자세(REST)에서 검사한다. 면끼리 서로 뚫는 곳은 잡지 못한다.
#   확인(2026-11-23): 조각 목록 — 교복 사무라이의 눈 메시를 지우기 전 파일(보관_이전버전/…_v004.blend, --객체 tripo_node_a40cd2a6)에서
#   예전에 지운 눈·속눈썹·눈썹 8덩어리가 모두 한 칸씩 나왔다. 여덟 가지 — 교복 사무라이 작업본에서 원본 도구의 v024 결과(후보 142개)와
#   종류·면 수·자리가 모두 같았다.
import bpy, bmesh, sys, os, json, math, subprocess
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from collections import defaultdict

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if not args: raise SystemExit("사용: -- <출력폴더> [선택]  (머리말 주석 참고)")
OUT = os.path.abspath(args[0]); opt = {}; i = 1
while i < len(args): opt[args[i]] = args[i + 1]; i += 2
KINDS = ["플로터", "매달린묶음", "미세면", "겹친변", "작은구멍", "패임", "돌출", "자체가림"]
_spec = opt.get("--검사", "조각")
DO = set(KINDS) | {"조각"} if _spec == "전부" else set(_spec.split(","))
if DO - set(KINDS) - {"조각"}: raise SystemExit(f"모르는 검사: {DO - set(KINDS) - {'조각'}}")
PIECE_MAX = int(opt.get("--조각최대", 60))
MICRO_AREA_H2 = float(opt.get("--미세면적", 2e-6))
MICRO_RATIO = float(opt.get("--미세비율", 0.08))
HANG_MAX_FACES = int(opt.get("--매달린최대면", 60))
FLOATER_MAX_FRAC = float(opt.get("--플로터비율", 0.02))
DENT_FRAC = float(opt.get("--요철비율", 0.010))
HOLE_FRAC = float(opt.get("--구멍비율", 0.06))
ZOOM_N = int(opt.get("--확대", 15))
EXTRA = set(opt.get("--그림", "").split(",")) - {""}
SMOOTH_ITERS = 30; SHARP_DEG = 80.0
RES = 400; THUMB = 200; PER = 5
TMP = os.path.join(OUT, "_tmp"); os.makedirs(TMP, exist_ok=True)

sc = bpy.data.scenes[opt["--장면"]] if "--장면" in opt else bpy.context.scene
if bpy.context.window: bpy.context.window.scene = sc
VL = sc.view_layers[0]
for lc in VL.layer_collection.children: lc.exclude = False   # 메모리 안에서만(저장하지 않음)
for o in sc.objects:
    if o.type == 'ARMATURE': o.data.pose_position = 'REST'
names = opt["--객체"].split(",") if "--객체" in opt else sorted(o.name for o in sc.objects if o.type == 'MESH' and o.name.startswith("파츠_"))
parts = [sc.objects[n] for n in names]
if not parts: raise SystemExit("검사할 객체가 없다")
VL.update()

def world_bm(o):
    bm = bmesh.new(); bm.from_mesh(o.data); bm.transform(o.matrix_world); bm.normal_update()
    bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    return bm
BMS = {o.name: world_bm(o) for o in parts}
ALL = np.concatenate([np.array([v.co[:] for v in b.verts]) for b in BMS.values()])
MN, MX = ALL.min(0), ALL.max(0); H = float(MX[2] - MN[2])
MICRO_AREA = MICRO_AREA_H2 * H * H

# 모든 파츠를 합친 광선 검사용 나무(면 번호: 파츠마다 오프셋)
all_v, all_p, OFF = [], [], {}
for n, b in BMS.items():
    OFF[n] = (len(all_p), len(b.faces)); base = len(all_v)
    all_v += [v.co.copy() for v in b.verts]; all_p += [tuple(v.index + base for v in f.verts) for f in b.faces]
BVH_ALL = BVHTree.FromPolygons(all_v, all_p)

N_DIR = 120
DIRS = []
for k in range(N_DIR):
    z = 1 - 2 * (k + 0.5) / N_DIR; rr = math.sqrt(1 - z * z); ph = k * math.pi * (3 - math.sqrt(5))
    DIRS.append(Vector((rr * math.cos(ph), rr * math.sin(ph), z)))

def flood(seeds, nbr):
    seeds = list(seeds); idx = set(seeds); seen = set(); out = []
    for s in seeds:
        if s in seen: continue
        st = [s]; seen.add(s); cl = []
        while st:
            x = st.pop(); cl.append(x)
            for y in nbr(x):
                if y in idx and y not in seen: seen.add(y); st.append(y)
        out.append(cl)
    return out

def analyze(name):
    bm = BMS[name]; nV, nF = len(bm.verts), len(bm.faces)
    co = np.array([v.co[:] for v in bm.verts])
    bb_min, bb_max = co.min(0), co.max(0); diag = float(np.linalg.norm(bb_max - bb_min))
    areas = np.array([f.calc_area() for f in bm.faces]); total_area = float(areas.sum())
    own_off = OFF[name][0]
    cands = []
    def add(kind, faces, ev):
        faces = list(faces); vs = list({v.index for fi in faces for v in bm.faces[fi].verts}); pts = co[vs]
        c = pts.mean(0); r = float(np.linalg.norm(pts - c, axis=1).max())
        nn = sum((bm.faces[fi].normal * bm.faces[fi].calc_area() for fi in faces), Vector())
        cands.append({"id": "%s-%02d" % (kind, 1 + sum(1 for x in cands if x["kind"] == kind)), "kind": kind, "faces": len(faces),
                      "face_idx": faces, "centre": [round(float(x), 4) for x in c], "radius": round(r, 5),
                      "normal": [round(x, 3) for x in (nn.normalized() if nn.length > 0 else Vector((0, -1, 0)))], "evidence": ev})
    # 연결 구조
    vadj = lambda x: [e.other_vert(bm.verts[x]).index for e in bm.verts[x].link_edges]
    islands = flood(range(nV), vadj); v_isl = [0] * nV
    for k, cl in enumerate(islands):
        for vi in cl: v_isl[vi] = k
    fadj = lambda x: [g.index for e in bm.faces[x].edges for g in e.link_faces]
    comps = flood(range(nF), fadj)
    f_isl = [v_isl[f.verts[0].index] for f in bm.faces]
    isl_faces = defaultdict(list)
    for fi, k in enumerate(f_isl): isl_faces[k].append(fi)
    # 1) 떨어진 작은 덩어리
    if "플로터" in DO and len(isl_faces) > 1:
        for k, fl in isl_faces.items():
            if len(fl) < FLOATER_MAX_FRAC * nF:
                rest = [tuple(v.index for v in bm.faces[fi].verts) for fi in range(nF) if f_isl[fi] != k]
                t = BVHTree.FromPolygons([v.co for v in bm.verts], rest)
                ds = [t.find_nearest(bm.verts[vi].co)[3] for vi in islands[k]]
                add("플로터", fl, {"간격_최소_mm": round(min(ds) * 1000, 2), "간격_중앙_mm": round(float(np.median(ds)) * 1000, 2),
                                  "간격_최대_mm": round(max(ds) * 1000, 2), "파츠면수_비율": round(len(fl) / nF, 4)})
    # 2) 정점으로만 매달린 묶음
    hang = set()
    if "매달린묶음" in DO:
        for fl in comps:
            if len(fl) > HANG_MAX_FACES or len(fl) == len(isl_faces[f_isl[fl[0]]]): continue
            fs = set(fl); verts = {v for fi in fl for v in bm.faces[fi].verts}
            shared = [v for v in verts if any(g.index not in fs for g in v.link_faces)]
            add("매달린묶음", fl, {"공유정점": len(shared), "넓이_mm2": round(float(areas[fl].sum()) * 1e6, 2),
                                "열린변": sum(1 for fi in fl for e in bm.faces[fi].edges if len(e.link_faces) == 1)})
            hang |= fs
    # 3) 미세 면(절대·상대)
    nb_med = np.zeros(nF)
    for f in bm.faces:
        nb = {g.index for v in f.verts for g in v.link_faces if g is not f}
        nb_med[f.index] = np.median(areas[list(nb)]) if nb else areas[f.index]
    ratio = areas / np.maximum(nb_med, 1e-12)
    if "미세면" in DO:
        micro = [fi for fi in range(nF) if (areas[fi] < MICRO_AREA or ratio[fi] < MICRO_RATIO) and fi not in hang]
        for cl in flood(micro, lambda x: [g.index for v in bm.faces[x].verts for g in v.link_faces]):
            fs = set(cl); edges = {e for fi in cl for e in bm.faces[fi].edges}
            emb = sum(1 for e in edges if any(g.index not in fs for g in e.link_faces))
            add("미세면", cl, {"최소넓이_mm2": round(float(areas[cl].min()) * 1e6, 3), "이웃대비_최소": round(float(ratio[cl].min()), 3),
                             "이웃넓이중앙_mm2": round(float(np.median(nb_med[cl])) * 1e6, 2), "표면과_공유한_변": emb,
                             "열린변": sum(1 for e in edges if len(e.link_faces) == 1),
                             "참고": "표면에 변으로 박혀 있어 지우면 구멍" if emb else "표면과 변을 공유하지 않음"})
    # 4) 면이 3개 이상 붙은 변
    nm = [e for e in bm.edges if len(e.link_faces) > 2]
    if "겹친변" in DO and nm:
        nm_v = defaultdict(set)
        for e in nm:
            for v in e.verts: nm_v[v.index].add(e.index)
        for cl in flood([e.index for e in nm], lambda x: [j for v in bm.edges[x].verts for j in nm_v[v.index]]):
            es = [bm.edges[j] for j in cl]
            add("겹친변", sorted({f.index for e in es for f in e.link_faces}),
                {"변": len(es), "한변최대면": max(len(e.link_faces) for e in es), "길이_mm": round(sum(e.calc_length() for e in es) * 1000, 2)})
    # 5) 열린 테두리 고리
    be = [e for e in bm.edges if len(e.link_faces) == 1]
    bv = defaultdict(list)
    for e in be:
        for v in e.verts: bv[v.index].append(e.index)
    loops = flood([e.index for e in be], lambda x: [j for v in bm.edges[x].verts for j in bv[v.index]])
    loop_rows = []
    for cl in loops:
        es = [bm.edges[j] for j in cl]; vs = list({v.index for e in es for v in e.verts}); pts = co[vs]
        ext = float(np.linalg.norm(pts.max(0) - pts.min(0)))
        row = {"변": len(es), "둘레_mm": round(sum(e.calc_length() for e in es) * 1000, 2), "크기_mm": round(ext * 1000, 2),
               "파츠대각선_비율": round(ext / diag, 3), "중심": [round(float(x), 4) for x in pts.mean(0)]}
        loop_rows.append(row)
        if "작은구멍" in DO and ext < HOLE_FRAC * diag:
            add("작은구멍", sorted({f.index for e in es for f in e.link_faces}), row)
    loop_rows.sort(key=lambda r: -r["둘레_mm"])
    sharp = sum(1 for e in bm.edges if len(e.link_faces) == 2 and math.degrees(e.link_faces[0].normal.angle(e.link_faces[1].normal, 0.0)) > SHARP_DEG)
    # 6) 요철: Taubin 방식으로 매끈하게 한 표면과의 차이(법선 방향, + 튀어나옴)
    nbrs = [[e.other_vert(v).index for e in v.link_edges] for v in bm.verts]
    fixed = np.zeros(nV, bool)
    for e in be:
        for v in e.verts: fixed[v.index] = True
    dev = np.zeros(nV)
    if DO & {"패임", "돌출"} or "요철" in EXTRA:
        P = co.copy(); free = [k for k in range(nV) if not fixed[k] and nbrs[k]]
        for _ in range(SMOOTH_ITERS):
            for factor in (0.5, -0.53):
                Q = P.copy()
                for k in free: Q[k] = P[nbrs[k]].mean(0)
                P = P + factor * (Q - P)
        vn = np.array([v.normal[:] for v in bm.verts]); dev = ((co - P) * vn).sum(1)
    near_b = fixed.copy()
    for k in np.nonzero(fixed)[0]:
        for j in nbrs[k]: near_b[j] = True
    T = DENT_FRAC * diag
    for kind, mask in (("패임", dev < -T), ("돌출", dev > T)):
        if kind not in DO: continue
        for cl in flood(np.nonzero(mask & ~near_b)[0].tolist(), lambda x: nbrs[x]):
            if len(cl) >= 4:
                add(kind, sorted({f.index for vi in cl for f in bm.verts[vi].link_faces}),
                    {"정점": len(cl), "최대깊이_mm": round(float(np.abs(dev[cl]).max()) * 1000, 2), "파츠대각선_비율": round(float(np.abs(dev[cl]).max()) / diag, 4)})
    # 7) 바깥에서 보이지 않는 면(자기 파츠만 / 모든 파츠)
    bvh_self = BVHTree.FromPolygons([v.co.copy() for v in bm.verts], [tuple(v.index for v in f.verts) for f in bm.faces])
    vis_self = np.ones(nF, bool); vis_all = np.ones(nF, bool)
    main_k = max(isl_faces, key=lambda k: len(isl_faces[k]))   # 가장 큰 조각(몸통)
    piece_keys = [k for k in isl_faces if k != main_k] if "조각" in DO else []
    need_all = "자체가림" in DO or "가림" in EXTRA
    check = list(range(nF)) if need_all else sorted(fi for k in piece_keys for fi in isl_faces[k])
    if check:
        vis_self[check] = False; vis_all[check] = False
        def escapes(tree, p, d, own):
            for _ in range(4):   # 휘어진 사각형은 자기 자신에 걸릴 수 있으므로 자기 면에 맞은 것은 건너뛴다
                hit = tree.ray_cast(p, d, 5.0 * H)
                if hit[0] is None: return True
                if hit[2] != own: return False
                p = hit[0] + d * 1e-4 * H
            return False
        for fi in check:
            f = bm.faces[fi]; c = f.calc_center_median(); n = f.normal
            off = max(2e-4 * H, 0.03 * math.sqrt(areas[fi]))
            samples = [c] + [c.lerp(v.co, 0.5) for v in f.verts]
            for sgn in (1, -1):   # 열린 껍데기는 양면이 보일 수 있다
                nn = n * sgn
                for q in samples:
                    p = q + nn * off
                    for d in DIRS:
                        if d.dot(nn) < 0.15: continue
                        if not vis_self[fi] and escapes(bvh_self, p, d, fi): vis_self[fi] = True
                        if not vis_all[fi] and escapes(BVH_ALL, p, d, fi + own_off): vis_all[fi] = True
                        if vis_self[fi] and vis_all[fi]: break
                    if vis_self[fi] and vis_all[fi]: break
                if vis_self[fi] and vis_all[fi]: break
        if "자체가림" in DO:
            for cl in flood([fi for fi in range(nF) if not vis_self[fi]], lambda x: [g.index for e in bm.faces[x].edges for g in e.link_faces]):
                if len(cl) >= 3: add("자체가림", cl, {"파츠넓이_비율": round(float(areas[cl].sum()) / total_area, 4)})
    if "자체가림" in DO or "가림" in EXTRA:   # 다른 파츠까지 넣고 바깥에서 보이는 면의 비율(0이면 어디서도 안 보임)
        for c in cands: c["evidence"]["보이는면_비율"] = round(float(vis_all[c["face_idx"]].mean()), 2)
    # 조각 목록: 몸통을 뺀 조각 전부, 다른 표면(모든 객체)까지의 거리와 보이는 비율
    pieces = []
    for k in piece_keys:
        fl = isl_faces[k]; vs = islands[k]; pts = co[vs]
        own = {own_off + fi for fi in fl}
        rest = [pp for gi, pp in enumerate(all_p) if gi not in own]
        ds = [0.0]
        if rest:
            t = BVHTree.FromPolygons(all_v, rest); ds = [t.find_nearest(Vector(co[vi]))[3] for vi in vs]
        pieces.append({"면": len(fl), "정점": len(vs), "크기_mm": round(float(np.linalg.norm(pts.max(0) - pts.min(0))) * 1000, 1),
                       "중심": [round(float(x), 4) for x in pts.mean(0)], "다른표면까지_최소_mm": round(min(ds) * 1000, 2),
                       "다른표면까지_중앙_mm": round(float(np.median(ds)) * 1000, 2), "보이는면_비율": round(float(vis_all[fl].mean()), 2), "face_idx": fl})
    pieces.sort(key=lambda q: (q["면"], q["중심"]))
    pre = name.replace("파츠_", "") + " " if len(parts) > 1 else ""   # 객체가 하나면 이름을 붙이지 않는다(칸 이름이 짧게)
    for n, q in enumerate(pieces): q["번호"] = "%s조각%d" % (pre, n + 1)
    order = {k: n for n, k in enumerate(KINDS)}
    cands.sort(key=lambda c: (order[c["kind"]], -c["faces"]))
    for n, c in enumerate(cands): c["번호"] = "%s %d" % (name.replace("파츠_", ""), n + 1)
    stats = {"정점": nV, "면": nF, "대각선_m": round(diag, 4), "넓이_m2": round(total_area, 5),
             "정점섬": len(islands), "면있는조각": len(isl_faces), "몸통면": len(isl_faces[main_k]), "변으로이어진묶음": len(comps), "열린변": len(be), "열린고리": len(loops), "열린고리_큰것": loop_rows[:12],
             "겹친변": len(nm), f"{int(SHARP_DEG)}도넘게꺾인변": sharp,
             "면넓이_중앙_mm2": round(float(np.median(areas)) * 1e6, 2), "면넓이_최소_mm2": round(float(areas.min()) * 1e6, 4),
             "미세면적기준_mm2": round(MICRO_AREA * 1e6, 3), "미세면적미만": int((areas < MICRO_AREA).sum()), "이웃대비미만": int((ratio < MICRO_RATIO).sum()),
             "요철기준_mm": round(T * 1000, 2), "요철_최소_mm": round(float(dev.min()) * 1000, 2), "요철_최대_mm": round(float(dev.max()) * 1000, 2),
             "자기가림_넓이비율": round(float(areas[~vis_self].sum()) / total_area, 4), "모든파츠가림_넓이비율": round(float(areas[~vis_all].sum()) / total_area, 4)}
    return dict(cands=cands, pieces=pieces, stats=stats, dev=dev, T=T, vis_self=vis_self, vis_all=vis_all, bvh_self=bvh_self, diag=diag, co=co)

RESULT = {}
for o in parts:
    RESULT[o.name] = analyze(o.name)
    print("검사:", o.name, "조각", len(RESULT[o.name]["pieces"]), "후보", len(RESULT[o.name]["cands"]))

# ---------- 그림 ----------
KCOL = {"플로터": (1, 0, 0), "매달린묶음": (1, 0.45, 0), "미세면": (1, 0, 1), "겹친변": (1, 1, 0), "작은구멍": (0, 0.9, 0.9),
        "패임": (0.1, 0.3, 1), "돌출": (0, 0.8, 0.2), "자체가림": (0.5, 0.2, 0.8)}
GREY = (0.62, 0.62, 0.62)
def color_attr(o, name, per_face=None, per_vert=None):
    me = o.data
    a = me.color_attributes.get(name) or me.color_attributes.new(name, 'FLOAT_COLOR', 'CORNER')
    cols = np.zeros((len(me.loops), 4), np.float32); cols[:, 3] = 1
    pidx = np.zeros(len(me.loops), int); me.loops.foreach_get("vertex_index", pidx)   # 코너의 정점
    if per_vert is not None: cols[:, :3] = np.asarray(per_vert)[pidx]
    else:
        lp = np.zeros(len(me.polygons), int); me.polygons.foreach_get("loop_total", lp)
        cols[:, :3] = np.repeat(np.asarray(per_face), lp, axis=0)
    a.data.foreach_set("color", cols.ravel())
for o in parts:
    R = RESULT[o.name]; nF = len(o.data.polygons)
    fc = np.tile(GREY, (nF, 1))
    for c in reversed(R["cands"]):   # 앞 순서(플로터 등)가 위에 칠해지게
        fc[c["face_idx"]] = KCOL[c["kind"]]
    color_attr(o, "검사_후보", per_face=fc)
    s = np.clip(R["dev"] / (2 * R["T"]), -1, 1)
    color_attr(o, "검사_요철", per_vert=np.stack([0.65 + 0.35 * np.maximum(0, s), 0.65 - 0.45 * np.abs(s), 0.65 + 0.35 * np.maximum(0, -s)], 1))
    color_attr(o, "검사_가림", per_face=[GREY if R["vis_all"][fi] else ((0.5, 0.2, 0.8) if not R["vis_self"][fi] else (0.2, 0.5, 0.9)) for fi in range(nF)])
    o.data.update()
def use_attr(name):
    for o in parts:
        a = o.data.color_attributes.get(name)
        if a is None: continue
        o.data.color_attributes.active_color = a   # Workbench는 활성 색 속성을 쓴다
        o.data.color_attributes.render_color_index = list(o.data.color_attributes).index(a)
        o.data.update()   # 바꾼 것을 렌더가 보게 한다

r = sc.render; r.engine = 'BLENDER_WORKBENCH'; r.resolution_x = r.resolution_y = RES; r.resolution_percentage = 100
r.film_transparent = False; r.image_settings.file_format = 'PNG'
sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'VERTEX'
sh.show_cavity = False; sh.show_shadows = False; sh.show_object_outline = False; sh.show_backface_culling = False; sh.show_xray = False
sc.world = sc.world or bpy.data.worlds.new("w"); sc.world.color = (0.05, 0.05, 0.05)
cd = bpy.data.cameras.new("_검사캠"); cd.type = 'ORTHO'; cd.clip_start = 0.001; cd.clip_end = 100
cam = bpy.data.objects.new("_검사캠", cd); sc.collection.objects.link(cam); sc.camera = cam
def vdir(az, el):
    a, e = math.radians(az), math.radians(el)
    return Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))).normalized()
def shoot(path, c, w, d):
    d = Vector(d).normalized(); up = Vector((0, 0, 1)) if abs(d.z) < 0.99 else Vector((0, 1, 0))
    y = (up - up.dot(d) * d).normalized(); x = y.cross(d).normalized()
    cam.matrix_world = Matrix.Translation(Vector(c) + d * 10 * H) @ Matrix((x, y, d)).transposed().to_4x4()
    cd.clip_end = 30 * H; cd.ortho_scale = w; r.filepath = path
    bpy.ops.render.render(write_still=True, scene=sc.name)
def visible(objs):
    keep = set(objs)
    for o in sc.objects:
        if o.type == 'MESH': o.hide_render = o not in keep
# 둘레 12방향: 눈높이 8 + 위 60도 + 아래 25도 앞뒤 + 바로 아래(아래 각도를 빼지 않는다)
RING = [(0, 0), (45, 0), (90, 0), (135, 0), (180, 0), (225, 0), (270, 0), (315, 0), (0, 60), (0, -25), (180, -25), (0, -90)]
sheets = []   # (파일 이름, [(라벨, 그림)], 한 줄 칸 수)
n_shot = [0]
def tile(label, c, w, d):
    p = os.path.join(TMP, "%04d.png" % n_shot[0]); n_shot[0] += 1; shoot(p, c, w, d); return (label, p)
def ring_sheet(fname, objs, attr):
    visible(objs); use_attr(attr)
    P = np.concatenate([RESULT[o.name]["co"] for o in objs]); mn, mx = P.min(0), P.max(0)
    c = (mn + mx) / 2; w = float(max(mx[2] - mn[2], mx[0] - mn[0], mx[1] - mn[1])) * 1.1
    sheets.append((fname, [tile(f"{az}/{el}", c, w, vdir(az, el)) for az, el in RING], PER))
def best_dir(pts, own):
    # 모든 객체를 넣고, 그 조각 자신에 맞은 것은 건너뛰며 가장 잘 보이는 방향(앞쪽을 조금 더 좋아한다)
    best = None
    for d in DIRS:
        fr = 0
        for q in pts:
            p = q + d * 3e-4 * H
            for _ in range(8):
                hit = BVH_ALL.ray_cast(p, d, 5.0 * H)
                if hit[0] is None: fr += 1; break
                if hit[2] not in own: break
                p = hit[0] + d * 1e-4 * H
        fr /= len(pts); s = fr + 0.08 * max(0, -d.y)
        if best is None or s > best[0]: best = (s, d, fr)
    return best[1], best[2]
ZC, ZR = 4, 5   # 확대 그림은 한 줄 4칸(둘) × 5줄 = 10개, 800 × 1090px
if "조각" in DO:
    for o in parts:
        fc = np.tile(GREY, (len(o.data.polygons), 1))
        for q in RESULT[o.name]["pieces"]: fc[q["face_idx"]] = (1, 0, 0)
        color_attr(o, "검사_조각", per_face=fc); color_attr(o, "검사_조각하나", per_face=np.tile(GREY, (len(o.data.polygons), 1)))
    ring_sheet("모음_조각_전체.png", parts, "검사_조각")
    allp = sorted(((o, q) for o in parts for q in RESULT[o.name]["pieces"]), key=lambda t: t[1]["면"])[:PIECE_MAX]
    visible(parts); use_attr("검사_조각하나"); tiles = []
    for o, q in allp:
        bm = BMS[o.name]; nF = len(o.data.polygons)
        fc = np.tile(GREY, (nF, 1)); fc[q["face_idx"]] = (1, 0, 0); color_attr(o, "검사_조각하나", per_face=fc); o.data.update()
        pts = [bm.faces[fi].calc_center_median() for fi in q["face_idx"][::max(1, len(q["face_idx"]) // 40)]]
        d, fr = best_dir(pts, {OFF[o.name][0] + fi for fi in q["face_idx"]})
        q["보는방향"] = [round(x, 2) for x in d]; q["그방향에서_보이는비율"] = round(fr, 2)
        xr = fr < 0.05; sh.show_xray = xr; sh.xray_alpha = 0.3
        z = max(0.04 * H, q["크기_mm"] / 1000 * 1.8); ctr = Vector(q["중심"])
        tiles.append(tile(f"{q['번호']} 면{q['면']}" + (" 투시" if xr else ""), ctr, z, d))
        tiles.append(tile("넓게", ctr, min(H * 1.1, z * 5), d))
        sh.show_xray = False; color_attr(o, "검사_조각하나", per_face=np.tile(GREY, (nF, 1))); o.data.update()
    for k in range(0, len(tiles), ZC * ZR):
        fn = f"모음_조각_{k // (ZC * ZR) + 1}.png"; sheets.append((fn, tiles[k:k + ZC * ZR], ZC))
        for o, q in allp[k // 2:(k + ZC * ZR) // 2]: q["그림"] = fn
if DO & set(KINDS): ring_sheet("모음_전체.png", parts, "검사_후보")
for o in parts:
    short = o.name.replace("파츠_", "")
    if DO & set(KINDS): ring_sheet(f"모음_{short}.png", [o], "검사_후보")
    if "요철" in EXTRA: ring_sheet(f"모음_{short}_요철.png", [o], "검사_요철")
    if "가림" in EXTRA: ring_sheet(f"모음_{short}_가림.png", [o], "검사_가림")
# 후보 확대: 그 후보만 칠하고, 파츠 자신에 가리지 않는 방향을 골라 가까이·넓게
for o in parts:
    R = RESULT[o.name]; bm = BMS[o.name]; short = o.name.replace("파츠_", ""); tiles = []
    visible([o]); nF = len(o.data.polygons)
    for c in R["cands"][:ZOOM_N]:
        ctr = Vector(c["centre"]); nrm = Vector(c["normal"])
        pts = [bm.faces[fi].calc_center_median() for fi in c["face_idx"][:40]]
        best = None
        for d in DIRS:
            fr = sum(1 for q in pts if R["bvh_self"].ray_cast(q + d * 3e-4 * H, d, 5.0 * H)[0] is None) / len(pts)
            s = fr + 0.12 * abs(d.dot(nrm)) + 0.08 * max(0, -d.y)
            if best is None or s > best[0]: best = (s, d, fr)
        d = best[1]; c["보는방향"] = [round(x, 2) for x in d]; c["그방향에서_보이는비율"] = round(best[2], 2)
        fc = np.tile(GREY, (nF, 1)); fc[c["face_idx"]] = KCOL[c["kind"]]; color_attr(o, "검사_하나", per_face=fc); o.data.update(); use_attr("검사_하나")
        z = max(0.03 * H, c["radius"] * 2.6)
        tiles.append(tile(c["번호"] + " " + c["kind"], ctr, z, d))
        tiles.append(tile("넓게", ctr, min(R["diag"] * 1.1, z * 4), d))
    for k in range(0, len(tiles), ZC * ZR):
        fn = f"모음_확대_{short}_{k // (ZC * ZR) + 1}.png"; sheets.append((fn, tiles[k:k + ZC * ZR], ZC))
        for c in R["cands"][:ZOOM_N][k // 2:(k + ZC * ZR) // 2]: c["그림"] = fn

json.dump({"출력": OUT, "칸": THUMB, "한줄": PER, "장": [{"파일": f, "한줄": per, "칸": [{"라벨": l, "그림": p} for l, p in t]} for f, t, per in sheets]},
          open(os.path.join(TMP, "모음목록.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
compose = os.path.join(os.path.dirname(os.path.abspath(__file__)), "메시검사_모음.py")
res = subprocess.run(["python", compose, os.path.join(TMP, "모음목록.json")], capture_output=True, text=True, encoding="utf-8")
if res.returncode != 0: print(res.stderr.strip()); raise SystemExit("모음 그림 만들기 실패")

# ---------- 기록 ----------
TH = {"미세면적_높이제곱비": MICRO_AREA_H2, "미세면적_mm2": round(MICRO_AREA * 1e6, 3), "미세비율": MICRO_RATIO, "매달린최대면": HANG_MAX_FACES,
      "플로터비율": FLOATER_MAX_FRAC, "요철비율": DENT_FRAC, "구멍비율": HOLE_FRAC, "매끈하게반복": SMOOTH_ITERS}
report = {"도구": "SSOT/도구/메시검사.py", "파일": bpy.data.filepath, "장면": sc.name, "자세": "REST", "모델높이_m": round(H, 4), "기준값": TH,
          "검사": [k for k in ["조각"] + KINDS if k in DO], "그림": [s[0] for s in sheets],
          "파츠": {n: {"수치": R["stats"], "조각": [{k: v for k, v in q.items() if k != "face_idx"} | {"면번호": [int(i) for i in q["face_idx"]]} for q in R["pieces"]], "후보수": len(R["cands"]),
                     "후보": [{k: v for k, v in c.items() if k != "face_idx"} | {"면번호_앞12": c["face_idx"][:12], "면번호": [int(i) for i in c["face_idx"]]} for c in R["cands"]]}
                 for n, R in RESULT.items()}}
json.dump(report, open(os.path.join(OUT, "검사결과.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
def ev(e): return ", ".join(f"{k} {v}" for k, v in e.items() if not isinstance(v, list))
L = [f"# 메시 검사 후보", "", f"- 파일: `{bpy.data.filepath}` (장면 {sc.name}, 정지 자세). 모델 높이 {H:.3f} m",
     f"- 검사: {', '.join(k for k in ['조각'] + KINDS if k in DO)}",
     "- 후보는 수치로 고른 것이다. 그림으로 확인하고 승인받기 전에는 지우거나 고치지 않는다.",
     "- 자리(mm)는 x 화면 오른쪽 +, y 뒤쪽 +, z 위 +.", ""]
if "조각" in DO:
    L += ["## 조각 목록", "", "객체마다 가장 큰 조각(몸통)을 뺀, 서로 이어지지 않은 조각 전부(작은 것부터). 입력 그림에 없는 것이 노이즈 후보다.",
          "다른 표면까지 = 이 조각의 정점에서 다른 조각·객체 표면까지 거리. 보이는면 = 모든 객체를 넣고 바깥 120방향에서 보이는 면의 비율(0이면 어디서도 안 보임).", "",
          "| 객체 | 면 | 몸통 면 | 조각 수 |", "| --- | --- | --- | --- |"]
    L += [f"| {n} | {R['stats']['면']} | {R['stats']['몸통면']} | {len(R['pieces'])} |" for n, R in RESULT.items()]
    L += ["", "| 번호 | 면 | 크기 mm | 자리 x,y,z (mm) | 다른 표면까지 최소/중앙 mm | 보이는면 | 그림 |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for q in sorted((q for R in RESULT.values() for q in R["pieces"]), key=lambda q: q["면"]):
        L.append(f"| {q['번호']} | {q['면']} | {q['크기_mm']} | {','.join(str(round(x * 1000)) for x in q['중심'])} | {q['다른표면까지_최소_mm']} / {q['다른표면까지_중앙_mm']} | {q['보이는면_비율']} | {q.get('그림', '')} |")
    L.append("")
if DO & set(KINDS): L += [f"## 결함 후보 (기준값: {', '.join(f'{k} {v}' for k, v in TH.items())})", ""]
if DO & set(KINDS): L += ["| 파츠 | 면 | " + " | ".join(KINDS) + " | 합계 |", "| --- | --- | " + " | ".join("---" for _ in KINDS) + " | --- |"]
for n, R in (RESULT.items() if DO & set(KINDS) else []):
    cnt = [sum(1 for c in R["cands"] if c["kind"] == k) for k in KINDS]
    L.append(f"| {n} | {R['stats']['면']} | " + " | ".join(str(x) for x in cnt) + f" | {sum(cnt)} |")
for n, R in RESULT.items():
    if not DO & set(KINDS): break
    L += ["", f"### {n}", "", "| 번호 | 종류 | 면 | 자리 x,y,z (mm) | 근거 | 그림 |", "| --- | --- | --- | --- | --- | --- |"]
    for c in R["cands"]:
        L.append(f"| {c['번호']} | {c['kind']} | {c['faces']} | {','.join(str(round(x * 1000)) for x in c['centre'])} | {ev(c['evidence'])} | {c.get('그림', '')} |")
open(os.path.join(OUT, "후보목록.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print(res.stdout.strip())
print("조각:", sum(len(R["pieces"]) for R in RESULT.values()), "| 후보:", sum(len(R["cands"]) for R in RESULT.values()), "| 결과:", OUT)
