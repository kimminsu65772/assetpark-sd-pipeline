# 그림공통.py — 창 없는 Workbench 렌더 도우미. 다른 스크립트(SmartUV조사.py)가 import 해서 쓴다. 파일을 저장하지 않는다(공통 도구).
# 출처: 01_캐릭터/온천_검사/04_Blender/스크립트/그림공통.py를 그대로 옮겼다.
import bpy, math, os
from mathutils import Vector

def setup(res=800, light='STUDIO', outline=False, color_type='SINGLE'):
    sc = bpy.context.scene
    r = sc.render
    r.engine = 'BLENDER_WORKBENCH'; r.resolution_x = r.resolution_y = res; r.resolution_percentage = 100
    r.film_transparent = False; r.image_settings.file_format = 'PNG'
    sh = sc.display.shading
    sh.light = light; sh.color_type = color_type; sh.single_color = (0.8, 0.8, 0.8)
    sh.show_cavity = False; sh.show_shadows = False; sh.show_object_outline = outline
    sh.show_backface_culling = os.environ.get("CULL") == "1"
    if sc.world is None: sc.world = bpy.data.worlds.new("w")
    sc.world.color = (0.05, 0.05, 0.05)
    cam = sc.camera
    if cam is None:
        cd = bpy.data.cameras.new("검사캠"); cd.type = 'ORTHO'; cd.clip_start = 0.001; cd.clip_end = 50
        cam = bpy.data.objects.new("검사캠", cd); sc.collection.objects.link(cam); sc.camera = cam
    return cam

def shoot(path, center, direction, scale, up=(0, 0, 1), dist=5.0):
    """direction: 카메라가 물체를 바라보는 쪽에서 물체로 향하는 벡터가 아니라, 물체 중심에서 카메라 쪽으로의 벡터."""
    sc = bpy.context.scene; cam = sc.camera
    d = Vector(direction).normalized(); c = Vector(center)
    cam.location = c + d * dist
    upv = Vector(up)
    if abs(d.dot(upv.normalized())) > 0.99: upv = Vector((0, 1, 0))
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    # to_track_quat에 up을 Y로 맞추고 roll 보정
    q = (-d).to_track_quat('-Z', 'Y')
    cam.rotation_euler = q.to_euler()
    # 수직 보정: 카메라 Y축이 up에 가장 가깝게
    import mathutils
    m = cam.rotation_euler.to_matrix()
    zc = -d
    yc = (upv - upv.dot(-zc) * (-zc)).normalized() if False else (upv - upv.dot(d) * d).normalized()
    xc = yc.cross(d).normalized()
    M = mathutils.Matrix((xc, yc, d)).transposed()
    cam.rotation_euler = M.to_euler()
    cam.data.ortho_scale = scale
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)

def dirvec(az_deg, el_deg):
    """az 0 = 앞(-y에서 봄), 90 = 화면 오른쪽(+x)에서 봄. el 위로 +."""
    az, el = math.radians(az_deg), math.radians(el_deg)
    return (math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))

def components(me):
    """면마다 조각 번호(면 수 많은 순 1부터)를 돌려준다. 구성조사_v001과 같은 번호."""
    import bmesh, numpy as np
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    comp = [-1] * len(bm.verts); n = 0
    for v in bm.verts:
        if comp[v.index] >= 0: continue
        stack = [v]; comp[v.index] = n
        while stack:
            u = stack.pop()
            for e in u.link_edges:
                w = e.other_vert(u)
                if comp[w.index] < 0: comp[w.index] = n; stack.append(w)
        n += 1
    fc = np.array([comp[f.verts[0].index] for f in bm.faces]); bm.free()
    order = np.argsort(-np.bincount(fc, minlength=n), kind='stable')
    remap = np.empty(n, int); remap[order] = np.arange(1, n + 1)
    return remap[fc]

def make_subset(o, face_ids, name):
    """o의 일부 면만 가진 임시 객체(메모리 안)."""
    import bmesh
    keep = set(int(i) for i in face_ids)
    bm = bmesh.new(); bm.from_mesh(o.data); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in keep], context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    m = bpy.data.meshes.new(name); bm.to_mesh(m); bm.free()
    ob = bpy.data.objects.new(name, m); ob.matrix_world = o.matrix_world
    bpy.context.scene.collection.objects.link(ob); return ob
