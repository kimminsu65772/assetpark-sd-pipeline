# 다각도검수.py — 정해 둔 방향 묶음으로 캐릭터를 찍어, 휴대폰에서 볼 만한 모음 그림(긴 변 약 1000px)을 만든다. 파일은 저장하지 않는다.
# 토큰 절약용(사용자 지시 2026-11-23): 검수 때마다 방향을 새로 정하는 스크립트를 쓰지 않고 이 도구 한 줄로 찍는다.
#
# 사용(Git Bash):
#   SSOT/도구/블렌더실행.sh <blend> SSOT/도구/다각도검수.py -- <출력폴더> <묶음들> [선택]
#   묶음(쉼표로 여러 개): 전신, 머리, 상체, 손, 발  (자리는 메시 크기에서 자동으로 잡는다)
#   선택:
#     --전 <다른 blend>      같은 이름의 객체를 그 파일에서 불러와 윗줄(전)·아랫줄(후)로 비교한다. 칸마다 바뀐 화소 수를 출력한다
#     --객체 a,b             찍을 객체(기본: 이름이 "파츠_"로 시작하는 메시 전부)
#     --숨김 a,b             뺄 객체(예: 파츠_헤어 → 가리는 머리카락 없이 얼굴 보기)
#     --추가 이름:cx,cy,cz:폭:az:el;az:el   정해 둔 묶음 밖의 방향·자리를 덧붙인다
#     --노멀없음              사용자 지정 노멀을 빼고 찍는다(형태 문제인지 음영 문제인지 가를 때)
#     --격자                  첫 번째 UV 층에 격자무늬(UV_GRID)를 입혀 찍는다(UV 검수용. 재질은 메모리 안에서만 바꾼다)
#     --텍스처                재질의 그림을 조명 없이(FLAT), 색 변환 없이(Standard) 찍는다(텍스처 검수용. 그림 색 그대로 보인다)
#     (아래에서 올려다보는 각도 el < 0도 찍는다. 전신 묶음에 아래 25도 두 장이 들어 있다. 사용자 결정 2026-11-23, SSOT/41_사용자_방침.md "치마 속")
#   방향 표기: az(수평각, 0 = 앞에서 봄, 90 = 화면 오른쪽 +x에서 봄) / el(위로 +). 캐릭터 앞 = -y, 위 = +z를 전제로 한다.
#   결과: <출력폴더>/모음_<묶음>[_N].png (모음 그림), <출력폴더>/_tmp/ (낱장, git에 올리지 않음)
#   모음 그림을 먼저 열고, 자세히 볼 칸은 _tmp의 낱장을 잘라 확대해서 연다(SSOT/41_사용자_방침.md "그림 여는 법").
import bpy, sys, os, math, json, subprocess
from mathutils import Vector, Matrix

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(args) < 2:
    raise SystemExit("사용: -- <출력폴더> <묶음들> [선택]  (머리말 주석 참고)")
OUT = os.path.abspath(args[0]); PRESETS = args[1].split(",")
opt = {}; i = 2
while i < len(args):
    k = args[i]
    if k in ("--노멀없음", "--아래허용", "--격자", "--텍스처"): opt[k] = True; i += 1   # --아래허용은 예전 명령과 맞추려고 받기만 한다
    else: opt[k] = args[i + 1]; i += 2
TMP = os.path.join(OUT, "_tmp"); os.makedirs(TMP, exist_ok=True)
RES = 400       # 낱장 해상도(확대해서 볼 때 쓴다)
THUMB = 200     # 모음 그림 한 칸
PER = 5         # 모음 그림 한 줄의 칸 수(5 × 200 = 1000px)

sc = bpy.context.scene
names = opt["--객체"].split(",") if "--객체" in opt else [o.name for o in sc.objects if o.type == 'MESH' and o.name.startswith("파츠_")]
hide = set(opt.get("--숨김", "").split(",")) - {""}
names = [n for n in names if n not in hide]
if not names: raise SystemExit("찍을 객체가 없다")
for lc in bpy.context.view_layer.layer_collection.children: lc.exclude = False   # 메모리 안에서만(저장하지 않음)
after = [bpy.data.objects[n] for n in names]

def load_before(path):
    with bpy.data.libraries.load(os.path.abspath(path)) as (src, dst):
        dst.meshes = [n for n in names if n in src.meshes]
    objs = []
    for n, me in zip([n for n in names], dst.meshes):
        if me is None: continue
        o = bpy.data.objects.new("_전_" + n, me); o.matrix_world = bpy.data.objects[n].matrix_world
        sc.collection.objects.link(o); objs.append(o)
    return objs
before = load_before(opt["--전"]) if "--전" in opt else None

if opt.get("--노멀없음"):
    for o in after + (before or []):
        with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o], selected_editable_objects=[o]):
            bpy.ops.mesh.customdata_custom_splitnormals_clear()

# 자리 잡기: 찍을 객체 전체의 크기에서
import numpy as np
P = np.concatenate([np.array([(o.matrix_world @ v.co)[:] for v in o.data.vertices]) for o in after])
mn, mx = P.min(0), P.max(0); H = mx[2] - mn[2]; cy = (mn[1] + mx[1]) / 2
def zc(a, b): return mn[2] + H * (a + b) / 2
def hand(side):
    q = P[P[:, 0] > mx[0] - 0.06 * H] if side > 0 else P[P[:, 0] < mn[0] + 0.06 * H]
    return q.mean(0)
EIGHT = [(a, 0) for a in range(0, 360, 45)]
PRESET = {
    "전신": [((0, cy, zc(0, 1)), H * 1.08, EIGHT + [(0, 25), (180, 25), (0, -25), (180, -25)])],
    "머리": [((0, cy, zc(0.56, 1)), H * 0.56, [(0, 0), (30, 0), (330, 0), (90, 0), (270, 0), (180, 0), (0, 35), (180, 40), (0, 90), (45, 20)])],
    "상체": [((0, cy, zc(0.3, 0.65)), H * 0.5, [(0, 0), (30, 10), (330, 10), (90, 0), (270, 0), (180, 0), (0, 30), (180, 30)])],
    "손": [(tuple(hand(+1)), H * 0.15, [(0, 0), (45, 20), (90, 0), (0, 60), (180, 0)]),
           (tuple(hand(-1)), H * 0.15, [(0, 0), (315, 20), (270, 0), (0, 60), (180, 0)])],
    "발": [((0, cy, zc(0, 0.1)), H * 0.24, [(0, 15), (45, 20), (315, 20), (90, 5), (270, 5), (180, 20), (0, 50), (135, 30), (225, 30)])],
}
jobs = []   # (묶음, 중심, 폭, az, el)
for p in PRESETS:
    if p not in PRESET: raise SystemExit(f"모르는 묶음: {p} (전신, 머리, 상체, 손, 발)")
    for c, w, vs in PRESET[p]:
        for az, el in vs: jobs.append((p, c, w, az, el))
if "--추가" in opt:
    nm, c, w, vs = opt["--추가"].split(":", 3)
    for v in vs.split(";"):
        az, el = (float(x) for x in v.split(":"))
        jobs.append((nm, tuple(float(x) for x in c.split(",")), float(w), az, el))

# 렌더 설정(Workbench, 회색, 직교)
r = sc.render; r.engine = 'BLENDER_WORKBENCH'; r.resolution_x = r.resolution_y = RES; r.resolution_percentage = 100
r.film_transparent = False; r.image_settings.file_format = 'PNG'
sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'SINGLE'; sh.single_color = (0.8, 0.8, 0.8)
if opt.get("--격자"):   # UV 검수: 첫 번째 UV 층에 격자무늬. 재질은 메모리 안에서만 바꾼다(파일은 저장하지 않음)
    gimg = bpy.data.images.new("_격자", 1024, 1024); gimg.generated_type = 'UV_GRID'
    gm = bpy.data.materials.new("_격자재질"); gm.use_nodes = True
    tn = gm.node_tree.nodes.new("ShaderNodeTexImage"); tn.image = gimg; gm.node_tree.nodes.active = tn
    for o in after + (before or []):
        if not o.data.uv_layers: raise SystemExit(f"UV 층이 없다: {o.name}")
        o.data.uv_layers.active_index = 0; o.data.uv_layers[0].active_render = True
        o.data.materials.clear(); o.data.materials.append(gm)
    sh.color_type = 'TEXTURE'
if opt.get("--텍스처"):
    sh.light = 'FLAT'; sh.color_type = 'TEXTURE'
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'   # 그림 색이 그대로 나오게(AgX는 색을 바꾼다)
sh.show_cavity = False; sh.show_shadows = False; sh.show_object_outline = False; sh.show_backface_culling = False
sc.world = sc.world or bpy.data.worlds.new("w"); sc.world.color = (0.05, 0.05, 0.05)
cd = bpy.data.cameras.new("_검수캠"); cd.type = 'ORTHO'; cd.clip_start = 0.001; cd.clip_end = 100
cam = bpy.data.objects.new("_검수캠", cd); sc.collection.objects.link(cam); sc.camera = cam
def shoot(path, c, w, az, el):
    a, e = math.radians(az), math.radians(el)
    d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))).normalized()
    up = Vector((0, 0, 1)) if abs(d.z) < 0.99 else Vector((0, 1, 0))
    y = (up - up.dot(d) * d).normalized(); x = y.cross(d).normalized()
    cam.matrix_world = Matrix.Translation(Vector(c) + d * 10) @ Matrix((x, y, d)).transposed().to_4x4()
    cd.ortho_scale = w; r.filepath = path
    bpy.ops.render.render(write_still=True)
def visible(objs):
    keep = set(objs)
    for o in sc.objects:
        if o.type == 'MESH': o.hide_render = o not in keep
rows = [("후", after)] if before is None else [("전", before), ("후", after)]
shots = []
for p, c, w, az, el in jobs:
    item = dict(묶음=p, 방향=f"{int(az)}/{int(el)}", 그림={})
    for tag, objs in rows:
        visible(objs)
        fn = os.path.join(TMP, f"{p}_{int(az)}_{int(el)}_{tag}_{len(shots):02d}.png")
        shoot(fn, c, w, az, el); item["그림"][tag] = fn
    shots.append(item)
json.dump(dict(출력=OUT, 줄=[t for t, _ in rows], 칸=shots), open(os.path.join(TMP, "목록.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# 모음 그림은 일반 파이썬(PIL)으로 붙인다. Blender 파이썬에는 PIL이 없다.
compose = os.path.join(os.path.dirname(os.path.abspath(__file__)), "다각도검수_모음.py")
res = subprocess.run(["python", compose, os.path.join(TMP, "목록.json"), str(THUMB), str(PER)], capture_output=True, text=True, encoding="utf-8")
print(res.stdout.strip())
if res.returncode != 0:
    print(res.stderr.strip()); raise SystemExit("모음 그림 만들기 실패")
