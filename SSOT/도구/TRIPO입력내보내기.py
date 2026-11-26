# TRIPO입력내보내기.py — 작업본의 파츠를 TRIPO에 올릴 GLB 한 파일로 내보낸다. 방향을 TRIPO 원본 방향으로 돌려서 낸다. 작업본은 저장하지 않는다.
#
# 왜 돌리나(2026-11-24, 온천 검사 리깅에서 확인. SSOT/단계/2_TRIPO.md "모델 방향"):
#   작업본은 앞이 -y다(가져올 때 TRIPO 원본을 z축 -90도 돌림. 다각도검수.py도 앞 = -y를 전제로 한다).
#   TRIPO 원본은 앞이 +x다. 작업본 방향 그대로 올리면 rig-check가 riggable false를 준다(그림·파츠 수·파일 형식은 상관없었다).
#   그래서 메모리 안에서만 z축 +90도 돌려(앞 -y → +x) 내보낸다. 받은 것은 TRIPO받은것되돌리기.py로 되돌린다.
#
# 사용(Git Bash): SSOT/도구/블렌더실행.sh <작업본.blend> SSOT/도구/TRIPO입력내보내기.py -- <출력.glb> [선택]
#   --uv <이름>       내보낼 UV 층(기본 SmartUV). 이 층 하나만 나가도록 메모리 안에서 다른 UV 층을 지운다. 없으면 종료 코드 1
#   --그림            재질과 그림도 함께 낸다(기본: 재질 없이 형상과 UV만)
#   --객체 a,b        낼 객체(기본: 이름이 "파츠_"로 시작하는 메시 전부)
#   --돌림 <도>       z축 돌림 각도(기본 90). 앞이 -y가 아닌 작업본에만 바꾼다
# 확인: 내보낸 GLB를 빈 장면에 다시 읽어 객체마다 (정점 자리, UV) 짝이 돌린 작업본과 같은지(소수 넷째 자리, 반올림 경계는 거리 2e-4 안),
#       GLB의 TEXCOORD가 하나인지, --그림이면 그림 수가 객체 수와 같은지 본다. 앞이 +x인지도 본다:
#       발끝은 앞으로 나와 있으므로, 키의 아래 3% 정점(발)이 전체 정점 평균 x보다 +x쪽으로 -x쪽의 1.3배 넘게 나가면 앞 +x로 본다. 다르면 종료 코드 1.
#       결과는 <출력>_내보내기확인.json. 올리기 전에 SSOT/도구/TRIPO리그체크.sh(무료)로 riggable을 확인한다(리깅 입력일 때).
import bpy, sys, os, json, struct, math
import numpy as np
from mathutils import Matrix

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if not args: raise SystemExit("사용: -- <출력.glb> [--uv 이름] [--그림] [--객체 a,b] [--돌림 도]")
OUT = os.path.abspath(args[0]); opt = {}; i = 1
while i < len(args):
    if args[i] == "--그림": opt["--그림"] = True; i += 1
    else: opt[args[i]] = args[i + 1]; i += 2
UV = opt.get("--uv", "SmartUV"); DEG = float(opt.get("--돌림", 90))
ROT = Matrix.Rotation(math.radians(DEG), 4, 'Z')
os.makedirs(os.path.dirname(OUT), exist_ok=True)
NAMES = opt["--객체"].split(",") if "--객체" in opt else sorted(o.name for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("파츠_"))
if not NAMES: print("낼 객체가 없다"); sys.exit(1)

def pairs(o):
    me = o.data
    co = np.array([v.co for v in me.vertices]); mw = np.array(o.matrix_world)
    co = (np.c_[co, np.ones(len(co))] @ mw.T)[:, :3]
    vi = np.array([l.vertex_index for l in me.loops]); u = np.array([d.uv for d in me.uv_layers[0].data])
    return {tuple(r) for r in np.c_[np.round(co[vi], 4), np.round(u, 4)].tolist()}, co

info = {"돌림_z도": DEG, "UV층": UV, "그림": bool(opt.get("--그림")), "객체": {}}
before = {}
if bpy.context.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
for o in bpy.data.objects:
    try: o.select_set(False)
    except RuntimeError: pass
for n in NAMES:
    o = bpy.data.objects.get(n)
    if o is None or o.type != 'MESH': print("없는 객체", n); sys.exit(1)
    me = o.data
    layers = [u.name for u in me.uv_layers]
    if UV not in layers: print("UV 층 없음", n, layers); sys.exit(1)
    for name in layers:
        if name != UV: me.uv_layers.remove(me.uv_layers[name])   # 메모리 안에서만
    me.uv_layers[UV].active = True; me.uv_layers[UV].active_render = True
    if o.parent: mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
    o.matrix_world = ROT @ o.matrix_world                         # 메모리 안에서만
    before[n], co = pairs(o)
    info["객체"][n] = {"UV층_원래": layers, "정점": len(me.vertices), "면": len(me.polygons)}
    o.hide_viewport = False; o.hide_set(False); o.select_set(True)

# 앞 방향 확인(발끝): 돌린 뒤 키의 아래 3% 정점의 x가 전체 평균 x에서 +쪽으로 더 멀리 나가야 앞 +x
allco = np.vstack([pairs(bpy.data.objects[n])[1] for n in NAMES])
z0, z1 = allco[:, 2].min(), allco[:, 2].max(); foot = allco[allco[:, 2] < z0 + 0.03 * (z1 - z0)]
mx = allco[:, 0].mean(); fwd, back = float(foot[:, 0].max() - mx), float(mx - foot[:, 0].min())
info["발끝_앞뒤"] = [round(fwd, 4), round(back, 4)]; info["앞이_+x"] = fwd > 1.3 * back   # 옆을 보면(돌림 0·180) 거의 같고, 뒤를 보면(-90) 작다

bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                          export_skins=False, export_animations=False, export_apply=False,
                          export_texcoords=True, export_normals=True,
                          export_materials='EXPORT' if opt.get("--그림") else 'NONE', export_yup=True)
info["파일"] = OUT; info["크기"] = os.path.getsize(OUT)
with open(OUT, "rb") as f:
    f.read(12); ln, _ = struct.unpack("<II", f.read(8)); js = json.loads(f.read(ln))
info["GLB_TEXCOORD"] = {m["name"]: sorted({k for p in m["primitives"] for k in p["attributes"] if k.startswith("TEXCOORD")}) for m in js["meshes"]}
info["GLB_그림수"] = len(js.get("images", []))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=OUT)
ok = all(v == ["TEXCOORD_0"] for v in info["GLB_TEXCOORD"].values())
if opt.get("--그림"): ok = ok and info["GLB_그림수"] == len(NAMES)
info["다시읽기"] = {}
for o in [x for x in bpy.data.objects if x.type == 'MESH']:
    key = next((n for n in NAMES if o.name.startswith(n) or o.data.name.startswith(n)), None)
    if key is None: info["다시읽기"][o.name] = "이름 모름"; ok = False; continue
    p = pairs(o)[0]; b = before[key]; far = 0.0
    for X, Y in ((b - p, p), (p - b, b)):
        if X:
            A, B = np.array(sorted(X)), np.array(sorted(Y))
            far = max(far, max(float(np.abs(B - r).max(1).min()) for r in A))
    same = len(p) == len(b) and far < 2e-4
    info["다시읽기"][key] = {"짝수": len(b), "같음": same, "어긋난짝_최대거리": far}
    ok = ok and same
ok = ok and len(info["다시읽기"]) == len(NAMES) and info["앞이_+x"]
info["판정"] = "통과" if ok else "실패"
json.dump(info, open(os.path.splitext(OUT)[0] + "_내보내기확인.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: info[k] for k in ("돌림_z도", "크기", "GLB_TEXCOORD", "GLB_그림수", "다시읽기", "판정") }, ensure_ascii=False), "앞이_+x", info.get("앞이_+x"))
sys.exit(0 if ok else 1)
