# 텍스처옮겨굽기.py — TRIPO가 칠해 준 그림(TRIPO가 새로 편 UV 위)을 작업본의 UV(첫 번째 층, 기본 SmartUV)로 옮겨 굽는다. 작업본은 저장하지 않는다(공통 도구).
# 출처: 01_캐릭터/온천_검사/04_Blender/스크립트/텍스처옮겨굽기_v001.py에서 캐릭터 값(모으기의 파츠 이름 네 개·UV 층 이름)을 선택으로 뺐다. 하는 일은 같다.
# 방법: Cycles 굽기, 선택→활성(받은 파츠 → 작업본 파츠), DIFFUSE의 색(COLOR)만. 조명·그늘은 굽지 않고 받은 그림 색 그대로 옮긴다.
#       형태가 같으므로(정점 거리 0 mm) 광선 거리는 아주 짧게 둔다.
# 메모리가 적어 파츠 하나씩 돌린다.
# 사용: SSOT/도구/블렌더실행.sh <작업본.blend> SSOT/도구/텍스처옮겨굽기.py -- <받은 model.glb> <normalize_scale> <출력폴더> <파츠이름> [크기=4096] [여백=16] [--uv 이름]
#   모으기: SSOT/도구/블렌더실행.sh <작업본.blend> SSOT/도구/텍스처옮겨굽기.py -- 모으기 <출력폴더> [--파츠 a,b] [--uv 이름]
#     --파츠 기본: 이름이 "파츠_"로 시작하는 메시 전부. --uv 기본 SmartUV
#     → 작업본 파츠에 구운 그림을 입힌 검수용 blend(<출력폴더>/구운것_확인용.blend)를 따로 저장한다.
import bpy, sys, os
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
UV = opt.get("--uv", "SmartUV")

def material_with(img, name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = img
    uvn = nt.nodes.new("ShaderNodeUVMap"); uvn.uv_map = UV
    nt.links.new(uvn.outputs["UV"], tn.inputs["Vector"])
    nt.links.new(tn.outputs["Color"], bsdf.inputs["Base Color"])
    nt.nodes.active = tn
    return m, tn

if a[0] == "모으기":
    OUT = os.path.abspath(a[1])
    for n in 파츠목록(opt):
        img = bpy.data.images.load(os.path.join(OUT, f"{n}_구움.png"))
        img.pack()
        m, _ = material_with(img, f"{n}_구움")
        me = bpy.data.objects[n].data
        me.materials.clear(); me.materials.append(m)
        me.uv_layers.active = me.uv_layers[UV]
    p = os.path.join(OUT, "구운것_확인용.blend")
    bpy.ops.wm.save_as_mainfile(filepath=p, copy=True)
    print("저장", p)
    raise SystemExit(0)

GLB, S, OUT, PART = os.path.abspath(a[0]), float(a[1]), os.path.abspath(a[2]), a[3]
SIZE = int(a[4]) if len(a) > 4 else 4096
MARGIN = int(a[5]) if len(a) > 5 else 16
os.makedirs(OUT, exist_ok=True)

before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=GLB)
new = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
src = next(o for o in new if o.name.startswith(PART) or o.data.name.startswith(PART))
for o in new:
    if o is not src: bpy.data.objects.remove(o, do_unlink=True)
# 정규화 되돌리기(자리 이동은 0이었다: 받은것_비교.json)
src.matrix_world = Matrix.Scale(1 / S, 4) @ src.matrix_world
dst = bpy.data.objects[PART]
me = dst.data
assert me.uv_layers[0].name == UV
me.uv_layers.active = me.uv_layers[UV]

img = bpy.data.images.new(f"{PART}_구움", SIZE, SIZE, alpha=False)
img.colorspace_settings.name = 'sRGB'
m, _ = material_with(img, f"{PART}_굽기")
me.materials.clear(); me.materials.append(m)   # 메모리 안에서만

sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'; sc.cycles.samples = 4
bk = sc.render.bake
bk.use_selected_to_active = True; bk.cage_extrusion = 0.002; bk.max_ray_distance = 0.004
bk.margin = MARGIN; bk.margin_type = 'EXTEND'
bk.use_pass_direct = False; bk.use_pass_indirect = False; bk.use_pass_color = True
if bpy.context.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
for o in bpy.context.view_layer.objects:
    try: o.select_set(False)
    except RuntimeError: pass
for o in (src, dst):
    o.hide_set(False); o.hide_render = False; o.hide_viewport = False
src.select_set(True); dst.select_set(True)
bpy.context.view_layer.objects.active = dst
bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, use_selected_to_active=True,
                    cage_extrusion=0.002, max_ray_distance=0.004, margin=MARGIN, target='IMAGE_TEXTURES')
p = os.path.join(OUT, f"{PART}_구움.png")
img.filepath_raw = p; img.file_format = 'PNG'; img.save()
print("구움", PART, SIZE, "여백", MARGIN, p)
