# 텍스처받은것확인.py — TRIPO 텍스처 결과 GLB를 작업본과 비교하고, 검수 그림용 blend를 따로 만든다. 작업본은 저장하지 않는다(공통 도구).
# 출처: 01_캐릭터/온천_검사/04_Blender/스크립트/텍스처받은것_확인_v001.py에서 캐릭터 값(파츠 이름 네 개·UV 층 이름)을 선택으로 뺐다. 하는 일은 같다.
# 비교: 파츠마다 정점 자리(정규화를 되돌린 뒤 가장 가까운 작업본 정점까지 거리), UV(받은 루프마다 같은 자리 작업본 루프의 SmartUV와 같은 값이 있는지),
#       면·삼각형 수, UV 층 수, 재질과 그림 크기.
# 정규화 되돌리기: 받은 것 = 원래 × s + t. s는 TRIPO가 준 normalize_scale, t는 파츠 전체를 합친 외접 상자 중심에서 구한다.
# 사용: SSOT/도구/블렌더실행.sh <작업본.blend> SSOT/도구/텍스처받은것확인.py -- <받은 model.glb> <normalize_scale> <출력폴더> [선택]
#   --파츠 a,b   비교할 파츠(기본: 이름이 "파츠_"로 시작하는 메시 전부)
#   --uv 이름    작업본의 비교할 UV 층(기본 SmartUV)
import bpy, sys, os, json
import numpy as np
from mathutils import Vector, kdtree

def 선택값(a):
    """위치 인자와 --이름 값 선택을 나눈다. --파츠 a,b / --uv 이름 / --돌림 도"""
    pos, opt, i = [], {}, 0
    while i < len(a):
        if a[i].startswith("--"): opt[a[i]] = a[i + 1]; i += 2
        else: pos.append(a[i]); i += 1
    return pos, opt
def 파츠목록(opt):
    if "--파츠" in opt: return opt["--파츠"].split(",")
    n = sorted(o.name for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("파츠_"))
    if not n: raise SystemExit("파츠가 없다: 이름이 '파츠_'로 시작하는 메시가 없으면 --파츠 a,b로 준다")
    return n

a, opt = 선택값(sys.argv[sys.argv.index("--") + 1:])
GLB, S, OUT = os.path.abspath(a[0]), float(a[1]), os.path.abspath(a[2])
os.makedirs(OUT, exist_ok=True)
NAMES = 파츠목록(opt)
UV = opt.get("--uv", "SmartUV")

def world_co(o):
    mw = o.matrix_world
    return np.array([(mw @ v.co)[:] for v in o.data.vertices])

orig = {n: bpy.data.objects[n] for n in NAMES}
oco = {n: world_co(orig[n]) for n in NAMES}
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=GLB)
new = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
got = {}
for o in new:
    k = next((n for n in NAMES if o.name.startswith(n) or o.data.name.startswith(n)), None)
    if k: got[k] = o
assert set(got) == set(NAMES), [o.name for o in new]
gco = {n: world_co(got[n]) for n in NAMES}
allo = np.concatenate(list(oco.values())); allg = np.concatenate(list(gco.values()))
co_o = (allo.min(0) + allo.max(0)) / 2; co_g = (allg.min(0) + allg.max(0)) / 2
t = co_g - S * co_o
info = {"normalize_scale": S, "추정_translation(블렌더 좌표)": t.round(7).tolist(), "파츠": {}}
ok = True
for n in NAMES:
    o, g = orig[n], got[n]
    gc = (gco[n] - t) / S
    kd = kdtree.KDTree(len(oco[n]))
    for i, c in enumerate(oco[n]): kd.insert(c, i)
    kd.balance()
    near = [kd.find(c) for c in gc]
    dist = np.array([d for _, _, d in near]); idx = [i for _, i, _ in near]
    # 작업본: 정점마다 SmartUV 값 모음
    ouv = o.data.uv_layers[UV].data
    per = {}
    for l in o.data.loops:
        per.setdefault(l.vertex_index, []).append(tuple(ouv[l.index].uv))
    guv = g.data.uv_layers[0].data
    bad = 0; worst = 0.0
    for l in g.data.loops:
        u = np.array(guv[l.index].uv)
        cand = np.array(per[idx[l.vertex_index]])
        d = float(np.abs(cand - u).max(1).min())
        worst = max(worst, d)
        if d > 1e-3: bad += 1
    tri_o = sum(len(p.vertices) - 2 for p in o.data.polygons)
    tri_g = sum(len(p.vertices) - 2 for p in g.data.polygons)
    imgs = []
    for m in g.data.materials:
        if m and m.use_nodes:
            for nd in m.node_tree.nodes:
                if nd.type == 'TEX_IMAGE' and nd.image:
                    imgs.append({"재질": m.name, "그림": nd.image.name, "크기": list(nd.image.size)})
    info["파츠"][n] = {
        "정점_작업본": len(o.data.vertices), "정점_받은것": len(g.data.vertices),
        "삼각형환산_작업본": tri_o, "삼각형_받은것": tri_g,
        "정점거리_최대_mm": round(float(dist.max()) * 1000, 4),
        "UV층_받은것": [u.name for u in g.data.uv_layers],
        "UV_루프수": len(g.data.loops), "UV_다른루프(>0.001)": bad, "UV_가장큰차이": round(worst, 6),
        "그림": imgs,
    }
    ok = ok and dist.max() < 1e-4 and bad == 0 and tri_o == tri_g
info["판정"] = "UV·형태 그대로" if ok else "다름(세부 확인)"
with open(os.path.join(OUT, "받은것_비교.json"), "w", encoding="utf-8") as f:
    json.dump(info, f, ensure_ascii=False, indent=1)
print(json.dumps(info, ensure_ascii=False))

# 검수 그림용 blend: 작업본 파츠를 지우고 받은 것을 원래 자리로 되돌려 같은 이름으로 둔다(따로 저장, 작업본은 그대로)
for n in NAMES:
    bpy.data.objects.remove(orig[n], do_unlink=True)
for n in NAMES:
    g = got[n]
    me = g.data
    mw = g.matrix_world.copy()
    for v in me.vertices:
        w = mw @ v.co
        v.co = Vector(((np.array(w[:]) - t) / S).tolist())
    g.matrix_world = g.matrix_world.Identity(4); g.parent = None
    g.name = n; me.name = n
for o in [o for o in bpy.data.objects if o not in set(got.values()) and o.type == 'EMPTY' and o not in before]:
    bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.file.pack_all()
p = os.path.join(OUT, "받은것_확인용.blend")
bpy.ops.wm.save_as_mainfile(filepath=p, copy=True)
print("저장", p)
