"""가져온 모델 파일 검사 (작업 묶음 W08, 기능명세 1부 4-3 "4. 검사")

서버(`가져오기.py`)가 창 없는 Blender로 부른다. 파일은 읽기만 하고 아무것도 저장하지 않는다(--돌리기 때만 새 blend를 씀).
    blender --background --factory-startup --disable-autoexec [<받은.blend>] --python 가져오기검사.py -- <받은 파일> <결과.json> <그림 폴더>
    blender ... --python 가져오기검사.py -- <받은 파일> <결과.json> - --돌리기 <z축 도> <출력.blend>     (OBJ·blend의 방향 되돌린 사본)

결과.json: 열림, 파츠(메시 객체) 수·이름, 면 수, UV 층(파츠마다 이름), 텍스처 장수, 뼈대와 뼈 수, 동작 수, 크기(Blender 좌표, z 위),
앞 방향 추정(발끝: 키의 아래 3% 정점이 평균에서 어느 쪽으로 더 나왔나 — SSOT/도구/TRIPO입력내보내기.py와 같은 방법),
그림 폴더에 네 방향 그림(`+x.png` = +x 쪽에서 본 모습 …).
"""
import bpy, sys, os, json, math
from mathutils import Matrix, Vector

a = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT, PICS = os.path.abspath(a[0]), os.path.abspath(a[1]), a[2]
ROT = None
if "--돌리기" in a:
    i = a.index("--돌리기"); ROT = (float(a[i + 1]), os.path.abspath(a[i + 2]))
ext = os.path.splitext(SRC)[1].lower()
info = {"열림": False, "형식": ext.lstrip(".")}


def 끝(값):
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(값, f, ensure_ascii=False, indent=1)
    print("가져오기검사:", json.dumps({k: v for k, v in 값.items() if k not in ("파츠이름", "UV층")}, ensure_ascii=False))


try:
    if ext != ".blend":
        bpy.ops.wm.read_factory_settings(use_empty=True)
        if ext == ".fbx":
            bpy.ops.import_scene.fbx(filepath=SRC)
        elif ext == ".glb":
            bpy.ops.import_scene.gltf(filepath=SRC)
        elif ext == ".obj":
            bpy.ops.wm.obj_import(filepath=SRC)
        else:
            raise RuntimeError(f"모르는 형식: {ext}")
    elif os.path.normcase(os.path.abspath(bpy.data.filepath or "")) != os.path.normcase(SRC):
        raise RuntimeError("blend 파일이 열리지 않았습니다.")
except Exception as e:
    info["이유"] = f"Blender가 파일을 열지 못함: {e}"
    끝(info)
    raise SystemExit(0)

sc = bpy.context.scene
meshes = [o for o in sc.objects if o.type == 'MESH' and len(o.data.polygons)]
arms = [o for o in sc.objects if o.type == 'ARMATURE']
if not meshes:
    info["이유"] = "파일은 열렸지만 면이 있는 메시가 없습니다."
    끝(info)
    raise SystemExit(0)

if ROT is not None:   # OBJ·blend: 뿌리 객체를 z축으로 돌려 적용하고 새 blend로 저장(받은 파일은 그대로)
    deg, dst = ROT
    roots = [o for o in sc.objects if o.parent is None]
    M = Matrix.Rotation(math.radians(deg), 4, 'Z')
    for o in roots:
        o.matrix_world = M @ o.matrix_world
    bpy.context.view_layer.update()
    for o in sc.objects:
        o.hide_set(False); o.hide_viewport = False; o.select_set(True)
    bpy.context.view_layer.objects.active = roots[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=dst, copy=True)
    끝({"열림": True, "돌림_z도": deg, "출력": dst, "객체": len(sc.objects)})
    raise SystemExit(0)

dg = bpy.context.evaluated_depsgraph_get()
allco = []
for o in meshes:
    mw = o.matrix_world
    allco += [mw @ v.co for v in o.data.vertices]
lo = Vector((min(c.x for c in allco), min(c.y for c in allco), min(c.z for c in allco)))
hi = Vector((max(c.x for c in allco), max(c.y for c in allco), max(c.z for c in allco)))
z0, z1 = lo.z, hi.z
foot = [c for c in allco if c.z < z0 + 0.03 * (z1 - z0)] or allco
mx = sum(c.x for c in allco) / len(allco); my = sum(c.y for c in allco) / len(allco)
쪽 = {"+x": max(c.x for c in foot) - mx, "-x": mx - min(c.x for c in foot),
      "+y": max(c.y for c in foot) - my, "-y": my - min(c.y for c in foot)}
반대 = {"+x": "-x", "-x": "+x", "+y": "-y", "-y": "+y"}
후보 = [k for k, v in 쪽.items() if v > 1.3 * 쪽[반대[k]] and v > 0]
# 옆을 보면(발이 좌우로 벌어짐) 두 축 모두 비슷해 후보가 없고, 두 축 모두 한쪽으로 나오면 판단하지 않는다
앞 = 후보[0] if len(후보) == 1 else "모름"

images = [i for i in bpy.data.images if i.type == 'IMAGE' and (i.packed_file or i.filepath or i.has_data)]
없는그림 = [i.name for i in images if not i.packed_file and i.filepath and not os.path.isfile(bpy.path.abspath(i.filepath))]
info.update({
    "열림": True,
    "객체수": len(sc.objects),
    "파츠수": len(meshes),
    "파츠이름": [o.name for o in meshes][:50],
    "면수": sum(len(o.data.polygons) for o in meshes),
    "정점수": sum(len(o.data.vertices) for o in meshes),
    "UV층": {o.name: [l.name for l in o.data.uv_layers] for o in meshes[:50]},
    "UV있는파츠": sum(1 for o in meshes if len(o.data.uv_layers)),
    "UV층최대": max(len(o.data.uv_layers) for o in meshes),
    "텍스처수": len(images),
    "텍스처파일없음": len(없는그림),
    "뼈대수": len(arms),
    "뼈수": sum(len(o.data.bones) for o in arms),
    "동작수": len(bpy.data.actions),
    "크기": [round(hi.x - lo.x, 4), round(hi.y - lo.y, 4), round(hi.z - lo.z, 4)],
    "가장높은축": "xyz"[max(range(3), key=lambda k: (hi - lo)[k])],
    "발끝": {k: round(v, 4) for k, v in 쪽.items()},
    "앞": 앞,
})

# 네 방향 그림(Workbench, 직교). 앞을 모를 때 사용자가 고른다
if PICS != "-":
    os.makedirs(PICS, exist_ok=True)
    r = sc.render; r.engine = 'BLENDER_WORKBENCH'; r.resolution_x = r.resolution_y = 256; r.resolution_percentage = 100
    r.film_transparent = False; r.image_settings.file_format = 'PNG'
    sh = sc.display.shading
    if images and not 없는그림:   # 그림 파일을 못 찾으면 분홍으로 나오므로 회색으로
        sh.light = 'FLAT'; sh.color_type = 'TEXTURE'
        sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
    else:
        sh.light = 'STUDIO'; sh.color_type = 'SINGLE'; sh.single_color = (0.8, 0.8, 0.8)
    sh.show_cavity = False; sh.show_shadows = False; sh.show_object_outline = False; sh.show_backface_culling = False
    sc.world = sc.world or bpy.data.worlds.new("w"); sc.world.color = (0.05, 0.05, 0.05)
    cd = bpy.data.cameras.new("_가져오기캠"); cd.type = 'ORTHO'; cd.clip_start = 0.001
    cam = bpy.data.objects.new("_가져오기캠", cd); sc.collection.objects.link(cam); sc.camera = cam
    c = (lo + hi) / 2; size = max(hi - lo); cd.clip_end = size * 20 + 10; cd.ortho_scale = size * 1.1
    for o in sc.objects:
        if o.type not in ('MESH', 'CAMERA'):
            o.hide_render = True
    그림 = []
    for 이름, d in (("+x", Vector((1, 0, 0))), ("-x", Vector((-1, 0, 0))), ("+y", Vector((0, 1, 0))), ("-y", Vector((0, -1, 0)))):
        up = Vector((0, 0, 1)); y = up; x = y.cross(d).normalized()
        cam.matrix_world = Matrix.Translation(c + d * (size * 5 + 1)) @ Matrix((x, y, d)).transposed().to_4x4()
        r.filepath = os.path.join(PICS, f"{이름}.png")
        try:
            bpy.ops.render.render(write_still=True)
            그림.append(이름)
        except Exception as e:
            info["그림실패"] = repr(e)
            break
    info["그림"] = 그림

끝(info)
