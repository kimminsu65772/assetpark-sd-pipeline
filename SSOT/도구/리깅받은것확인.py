# 리깅받은것확인.py — TRIPO 오토리깅으로 받은 FBX를 작업본과 비교한다(읽기 전용, 작업본은 저장하지 않는다. 공통 도구).
# 출처: 01_캐릭터/온천_검사/04_Blender/스크립트/리깅받은것_확인_v001.py에서 캐릭터 값(파츠 이름 네 개·UV 층 이름)을 선택으로 뺐다. 하는 일은 같다.
# 받은 것은 TRIPO 원본 방향·정규화 크기다. ÷ normalize_scale 뒤 z축 -90도 돌려 작업본 방향으로 되돌린다(TRIPO입력내보내기.py의 반대).
# 받은 것은 발바닥이 z = 0이 되도록 올라와 있다. 파츠 전체의 가장 낮은 z가 작업본과 같아지게 뼈대째 내려 비교한다(내린 값은 결과에 적는다).
# 본다: 뼈 이름·수(SSOT/20_3D규격.md 2절의 67개와 비교), 파츠마다 정점·면 수, (정점 자리, UV) 짝이 작업본 SmartUV와 같은지,
#       정점 자리 최대 거리, 그림 크기·이름, 가중치 없는 정점 수, 정점마다 따르는 뼈 수.
# 결과: <출력폴더>/받은것_비교.json, <출력폴더>/받은것_확인용.blend(되돌린 방향, 파츠 이름 그대로. 다각도검수.py 입력)
# 사용: SSOT/도구/블렌더실행.sh <작업본.blend> SSOT/도구/리깅받은것확인.py -- <model.fbx> <normalize_scale> <출력폴더> <SSOT/20_3D규격.md> [선택]
#   --파츠 a,b   비교할 파츠(기본: 이름이 "파츠_"로 시작하는 메시 전부)
#   --uv 이름    작업본의 비교할 UV 층(기본 SmartUV)
#   --돌림 도    받은 것을 되돌리는 z축 각도(기본 -90, TRIPO입력내보내기.py --돌림의 반대)
import bpy, sys, os, json, math, re
import numpy as np
from mathutils import Matrix

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
FBX, NS, OUT, SPEC = os.path.abspath(a[0]), float(a[1]), os.path.abspath(a[2]), a[3]
os.makedirs(OUT, exist_ok=True)
NAMES = 파츠목록(opt)
UV = opt.get("--uv", "SmartUV"); DEG = float(opt.get("--돌림", -90))

txt = open(SPEC, encoding="utf-8").read()
blk = re.search(r"```조립 규격\.뼈이름\n(.*?)```", txt, re.S).group(1)
SSOT_BONES = [b.strip() for b in blk.replace("\n", " ").split(",") if b.strip()]

def loops(o, uvname=None):
    me = o.data
    uv = me.uv_layers[uvname] if uvname and uvname in me.uv_layers else me.uv_layers[0]
    co = np.array([v.co for v in me.vertices]); mw = np.array(o.matrix_world)
    co = (np.c_[co, np.ones(len(co))] @ mw.T)[:, :3]
    vi = np.array([l.vertex_index for l in me.loops])
    return co, co[vi], np.array([d.uv for d in uv.data])

ref = {}
for n in NAMES:
    o = bpy.data.objects[n]
    co, lc, lu = loops(o, UV)
    ref[n] = dict(정점=len(o.data.vertices), 면=len(o.data.polygons), 루프=len(o.data.loops), co=co,
                  pairs={tuple(r) for r in np.c_[np.round(lc, 4), np.round(lu, 4)].tolist()})

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE']
assert len(arm) == 1, len(arm)
arm = arm[0]
# 되돌리기: 뼈대(뿌리)에 ÷NS, z DEG도(기본 -90)를 걸고 적용
R = Matrix.Rotation(math.radians(DEG), 4, 'Z') @ Matrix.Scale(1 / NS, 4)
arm.matrix_world = R @ arm.matrix_world
bpy.context.view_layer.update()
for o in bpy.data.objects: o.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

ref_minz = min(float(r["co"][:, 2].min()) for r in ref.values())
got_minz = min(min((o.matrix_world @ v.co).z for v in o.data.vertices) for o in bpy.data.objects if o.type == 'MESH')
DZ = got_minz - ref_minz
arm.matrix_world = Matrix.Translation((0, 0, -DZ)) @ arm.matrix_world
bpy.context.view_layer.update()
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bones = [b.name for b in arm.data.bones]
info = {"파일": FBX, "normalize_scale": NS, "내린높이": round(DZ, 6),
        "뼈": {"수": len(bones), "뿌리": [b.name for b in arm.data.bones if b.parent is None],
              "SSOT에_없는것": [b for b in bones if b not in SSOT_BONES],
              "받은것에_없는것": [b for b in SSOT_BONES if b not in bones], "전부": bones},
        "그림": [(i.name, list(i.size)) for i in bpy.data.images],
        "동작": [x.name for x in bpy.data.actions], "파츠": {}}
ok = True
for n in NAMES:
    o = bpy.data.objects.get(n)
    if o is None: info["파츠"][n] = "없음"; ok = False; continue
    me = o.data
    co, lc, lu = loops(o)
    p = {tuple(r) for r in np.c_[np.round(lc, 4), np.round(lu, 4)].tolist()}
    r = ref[n]
    # 정점 자리: 받은 정점마다 작업본의 가장 가까운 정점까지 거리
    d = np.sqrt(((co[:, None, :] - r["co"][None, :, :]) ** 2).sum(-1)).min(1)
    d2 = np.sqrt(((r["co"][:, None, :] - co[None, :, :]) ** 2).sum(-1)).min(1)
    gi = {g.index: g.name for g in o.vertex_groups}
    cnt = np.array([sum(1 for g in v.groups if g.weight > 0) for v in me.vertices])
    wsum = np.array([sum(g.weight for g in v.groups) for v in me.vertices])
    used = sorted({gi[g.group] for v in me.vertices for g in v.groups if g.weight > 0})
    same_uv = len(p ^ r["pairs"])
    info["파츠"][n] = {"정점_받은것": len(me.vertices), "정점_작업본": r["정점"], "면_받은것": len(me.polygons), "면_작업본": r["면"],
                     "루프_받은것": len(me.loops), "루프_작업본": r["루프"], "UV층": [u.name for u in me.uv_layers],
                     "정점거리_최대mm(받은것→작업본)": round(float(d.max()) * 1000, 3),
                     "정점거리_최대mm(작업본→받은것)": round(float(d2.max()) * 1000, 3),
                     "자리UV짝_다른수": same_uv, "자리UV짝_작업본": len(r["pairs"]),
                     "가중치없는정점": int((cnt == 0).sum()), "따르는뼈수_분포": {int(k): int(v) for k, v in zip(*np.unique(cnt, return_counts=True))},
                     "가중치합_최소": round(float(wsum.min()), 4), "가중치합_최대": round(float(wsum.max()), 4),
                     "쓰는뼈": used, "재질": [m.name for m in me.materials]}
    ok = ok and int((cnt == 0).sum()) == 0
info["판정_가중치없는정점0"] = ok
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "받은것_확인용.blend"))
json.dump(info, open(os.path.join(OUT, "받은것_비교.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
short = {k: v for k, v in info.items() if k != "파츠"}; short["뼈"] = {k: v for k, v in info["뼈"].items() if k != "전부"}
print(json.dumps(short, ensure_ascii=False))
for n, v in info["파츠"].items():
    print(n, json.dumps({k: x for k, x in v.items() if k not in ("쓰는뼈",)}, ensure_ascii=False), "쓰는뼈수", len(v["쓰는뼈"]) if isinstance(v, dict) else "")
