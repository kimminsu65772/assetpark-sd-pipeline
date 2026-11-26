# 동작찍기.py — 리깅된 캐릭터에 동작 프레임을 넣고 여러 방향(아래에서 올려다보는 각도 포함)으로 찍어 모음 그림을 만든다(공용 도구, 읽기 전용).
# 자락 = 설정 "자락.파츠"에서 가장 큰 이어진 조각(그런 입력만 지원), 다리 = "다리조각" 번째 조각. 자락(치마) 조각은 빨강, 다리 조각은 노랑, 나머지 파츠는 회색 계열로 칠한다. 자세마다 다리–자락, 자락끼리 서로 뚫는 삼각형 쌍 수를 출력한다.
# 실행: SSOT/도구/블렌더실행.sh <리깅.blend> SSOT/도구/리깅/동작찍기.py -- <리깅설정.json> <출력 폴더> <칸 크기> <작업;작업;...> [시점묶음]
#   작업 = <그림 이름>=<자세>,<자세>,...   자세 = rest | <Action 끝 이름>:<프레임>   (예: 걷기=rest,UAL_Walk_Loop:9,UAL_Walk_Loop:25)
#   한 작업 = 한 장. 줄마다 자세 하나, 칸마다 시점 하나. 시점묶음: 하체(기본) | 전신
#   먼저 실행할 스크립트를 환경 변수 PRE로 주면 자세를 넣기 전에 메모리 안에서 실행한다(가중치 시험용, blend는 저장하지 않음).
import bpy, sys, os, math, json, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
a = sys.argv[sys.argv.index("--") + 1:]
cfg = json.load(open(a[0], encoding="utf-8")); OUTD = os.path.abspath(a[1]); RES = int(a[2])
JOBS = [(j.split("=")[0], j.split("=")[1].split(",")) for j in a[3].split(";")]
VSET = a[4] if len(a) > 4 else "하체"
os.makedirs(OUTD, exist_ok=True)
SK = cfg["자락"]
VIEWS = {"하체": [(0, 0, .27, .62), (-40, 10, .27, .62), (90, 0, .27, .62), (180, 0, .27, .62), (0, -30, .25, .62), (-90, -30, .25, .62)],
         "전신": [(0, 0, .5, 1.2), (-40, 15, .5, 1.2), (90, 0, .5, 1.2), (180, 0, .5, 1.2), (0, -25, .5, 1.2), (180, -25, .5, 1.2)]}[VSET]
sc = bpy.context.scene; vl = bpy.context.view_layer; arm = bpy.data.objects[cfg["armature"]]; vl.objects.active = arm
if bpy.context.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
if os.environ.get("PRE"):
    P = os.environ["PRE"]; exec(compile(open(P, encoding="utf-8").read(), P, "exec"), {"bpy": bpy, "__file__": P, "__name__": "pre"}); print("PRE_DONE", P)
MS = [o for o in sc.objects if o.type == 'MESH' and o.visible_get()]
for o in sc.objects: o.hide_render = o not in MS

def islands(me):
    par = list(range(len(me.vertices)))
    def f(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    for e in me.edges:
        p, q = f(e.vertices[0]), f(e.vertices[1])
        if p != q: par[p] = q
    co = [v.co for v in me.vertices]; kd = KDTree(len(co))
    for i, c in enumerate(co): kd.insert(c, i)
    kd.balance()
    for i, c in enumerate(co):
        for _, j, _ in kd.find_range(c, 1e-6):
            p, q = f(i), f(j)
            if p != q: par[p] = q
    g = {}
    for i in range(len(co)): g.setdefault(f(i), []).append(i)
    return sorted(g.values(), key=len, reverse=True)
low = bpy.data.objects[SK["파츠"]]; isl = islands(low.data)
vlab = {}
for v in isl[0]: vlab[v] = "자락"
for k in SK["다리조각"]:
    for v in isl[k]: vlab[v] = "다리"
FL = [max(set(ls), key=ls.count) for ls in ([vlab.get(v, "기타") for v in p.vertices] for p in low.data.polygons)]
COL = {"자락": (0.9, 0.2, 0.2), "다리": (1.0, 0.85, 0.2), "기타": (0.55, 0.55, 0.55)}
PC = [(0.3, 0.3, 0.34), (1.0, 0.75, 0.6), (0.3, 0.5, 0.9), (0.6, 0.6, 0.6)]
for n, o in enumerate(MS):
    me = o.data; at = me.color_attributes.new("찍기색", 'FLOAT_COLOR', 'CORNER')
    for p in me.polygons:
        c = COL[FL[p.index]] if o == low else PC[{"파츠_헤어": 0, "파츠_얼굴": 1, "파츠_상체": 2}.get(o.name, 3)]
        for k in p.loop_indices: at.data[k].color = (c[0], c[1], c[2], 1.0)
    me.color_attributes.active_color = at; me.color_attributes.render_color_index = list(me.color_attributes).index(at); me.update()

arm.data.pose_position = 'REST'; vl.update()
pts = np.array([list(o.matrix_world @ v.co) for o in MS for v in o.data.vertices]); lo, hi = pts.min(0), pts.max(0); H = hi[2] - lo[2]
HIP = cfg["humanoid"]["Hips"]; hip0 = (arm.matrix_world @ arm.data.bones[HIP].head_local).copy()
arm.data.pose_position = 'POSE'
SKT = [tuple(p.vertices) for p in low.data.polygons if FL[p.index] == "자락"]; LGT = [tuple(p.vertices) for p in low.data.polygons if FL[p.index] == "다리"]

def set_pose(spec):
    ad = arm.animation_data
    for pb in arm.pose.bones: pb.location = (0, 0, 0); pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    if spec == "rest":
        if ad: ad.action = None
        for pb in arm.pose.bones: pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0)
        vl.update(); return
    an, fr = spec.rsplit(":", 1); act = [x for x in bpy.data.actions if x.name.endswith("|" + an) or x.name == an][0]
    ad.action = act
    if getattr(act, "slots", None): ad.action_slot = act.slots[0]
    sc.frame_set(int(float(fr)), subframe=float(fr) % 1); vl.update()
def cross():
    dg = bpy.context.evaluated_depsgraph_get(); ev = low.evaluated_get(dg); co = [ev.matrix_world @ v.co for v in ev.data.vertices]
    S = BVHTree.FromPolygons(co, SKT); L = BVHTree.FromPolygons(co, LGT)
    self_ = sum(1 for i, j in S.overlap(S) if i < j and not set(SKT[i]) & set(SKT[j]))
    return len(S.overlap(L)), self_

cd = bpy.data.cameras.new("c"); cd.type = 'ORTHO'; cd.clip_start = 0.01; cd.clip_end = 100
cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam); sc.camera = cam
r = sc.render; r.engine = 'BLENDER_WORKBENCH'; r.resolution_x = r.resolution_y = RES; r.resolution_percentage = 100; r.image_settings.file_format = 'PNG'
r.film_transparent = False; sc.view_settings.view_transform = 'Standard'
sh = sc.display.shading; sh.show_object_outline = False; sh.show_shadows = False; sh.show_backface_culling = False; sh.show_xray = False
sh.light = 'STUDIO'; sh.color_type = 'VERTEX'; sh.show_cavity = True; sh.cavity_type = 'BOTH'
sc.world = bpy.data.worlds.new("w"); sc.world.color = (0.55, 0.55, 0.6)
nums = {}
for name, specs in JOBS:
    rows = []
    for spec in specs:
        set_pose(spec); c = cross(); nums["%s|%s" % (name, spec)] = c; print("CROSS", name, spec, "다리-자락 %d 자락끼리 %d" % c, flush=True)
        shift = (arm.matrix_world @ arm.pose.bones[HIP].head) - hip0; shift.z = 0
        tiles = []
        for yaw, pitch, zc, wd in VIEWS:
            y, p = math.radians(yaw), math.radians(pitch)
            d = Vector((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p)))
            cd.ortho_scale = wd * H; ctr = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2] + zc * H)) + shift
            cam.location = ctr + d * 10 * H; cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
            pth = os.path.join(OUTD, "_t.png"); r.filepath = pth; bpy.ops.render.render(write_still=True)
            im = bpy.data.images.load(pth); x = np.array(im.pixels[:], dtype=np.float32).reshape(RES, RES, 4); bpy.data.images.remove(im); os.remove(pth)
            x[:, :2, :3] = 1; x[:, -2:, :3] = 1; x[:2, :, :3] = 1; x[-2:, :, :3] = 1; tiles.append(x)
        rows.append(np.concatenate(tiles, axis=1))
    sheet = np.concatenate(list(reversed(rows)), axis=0); h, w = sheet.shape[:2]
    out = os.path.join(OUTD, name + ".png")
    o = bpy.data.images.new("s", w, h, alpha=True); o.pixels = sheet.ravel(); o.filepath_raw = out; o.file_format = 'PNG'; o.save(); bpy.data.images.remove(o)
    print("SHOT_DONE", os.path.basename(out), w, h, flush=True)
with open(os.path.join(OUTD, "교차수.json"), "w", encoding="utf-8") as fh: json.dump(nums, fh, ensure_ascii=False, indent=1)
print("ALL_DONE", len(JOBS))
