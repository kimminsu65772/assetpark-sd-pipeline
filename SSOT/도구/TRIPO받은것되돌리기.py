# TRIPO받은것되돌리기.py — TRIPO에서 받은 파일(FBX/GLB, 뼈대가 있어도 됨)을 작업본 방향·크기·높이로 되돌려 blend로 저장한다. 작업본은 저장하지 않는다.
# TRIPO입력내보내기.py의 반대: ÷ normalize_scale → z축 -90도(앞 +x → -y) → 높이 맞춤.
# 높이: TRIPO 리깅은 발바닥이 z = 0이 되게 올려 돌려준다(2026-11-24 온천 검사). 받은 것 전체의 가장 낮은 z를 작업본 파츠의 가장 낮은 z에 맞춘다.
#   (텍스처·UV 작업은 자리를 옮기지 않았다. 그때는 맞춤 값이 0에 가깝게 나온다.) 맞춘 값은 결과에 적는다.
# 뼈대가 있으면 뼈대째 옮기고 적용한다(뿌리 객체를 옮긴 뒤 전부 transform_apply).
# 사용(Git Bash): SSOT/도구/블렌더실행.sh <작업본.blend> SSOT/도구/TRIPO받은것되돌리기.py -- <받은 파일> <normalize_scale> <출력.blend> [--돌림 -90] [--높이맞춤 끔]
#   normalize_scale은 그 작업의 task.json 값. 출력 blend 옆에 <출력>_되돌리기.json(맞춘 값, 객체 목록, 뼈 수)
import bpy, sys, os, json, math
from mathutils import Matrix, Vector

a = sys.argv[sys.argv.index("--") + 1:]
if len(a) < 3: raise SystemExit("사용: -- <받은 파일> <normalize_scale> <출력.blend> [--돌림 -90] [--높이맞춤 끔]")
SRC, NS, OUT = os.path.abspath(a[0]), float(a[1]), os.path.abspath(a[2])
opt = {a[i]: a[i + 1] for i in range(3, len(a) - 1, 2)}
DEG = float(opt.get("--돌림", -90)); FIT = opt.get("--높이맞춤", "켬") != "끔"

ref = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("파츠_")]
ref_minz = min(min((o.matrix_world @ v.co).z for v in o.data.vertices) for o in ref) if ref else None

bpy.ops.wm.read_factory_settings(use_empty=True)
if SRC.lower().endswith(".fbx"): bpy.ops.import_scene.fbx(filepath=SRC)
else: bpy.ops.import_scene.gltf(filepath=SRC)
roots = [o for o in bpy.data.objects if o.parent is None]
M = Matrix.Rotation(math.radians(DEG), 4, 'Z') @ Matrix.Scale(1 / NS, 4)
for o in roots: o.matrix_world = M @ o.matrix_world
bpy.context.view_layer.update()
for o in bpy.data.objects: o.select_set(True)
bpy.context.view_layer.objects.active = roots[0]
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
dz = 0.0
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
if FIT and ref_minz is not None and meshes:
    got = min(min((o.matrix_world @ v.co).z for v in o.data.vertices) for o in meshes)
    dz = got - ref_minz
    for o in roots: o.matrix_world = Matrix.Translation((0, 0, -dz)) @ o.matrix_world
    bpy.context.view_layer.update()
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
info = {"받은파일": SRC, "normalize_scale": NS, "돌림_z도": DEG, "내린높이": round(dz, 6), "높이맞춤": FIT and ref_minz is not None,
        "객체": [(o.name, o.type) for o in bpy.data.objects],
        "뼈수": {o.name: len(o.data.bones) for o in bpy.data.objects if o.type == 'ARMATURE'}}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
json.dump(info, open(os.path.splitext(OUT)[0] + "_되돌리기.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in info.items() if k != "객체"}, ensure_ascii=False))
