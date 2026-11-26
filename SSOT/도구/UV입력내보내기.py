# UV입력내보내기.py — 작업본의 파츠를 하나씩 FBX로 내보낸다(TRIPO Smart UV 입력). 작업본은 저장하지 않는다(공통 도구).
# 출처: 01_캐릭터/온천_검사/04_Blender/스크립트/UV입력내보내기_v001.py를 그대로 옮겼다(캐릭터 값이 없음, 파츠는 인자).
# 쿼드 그대로, 객체 변환이 없는 상태 그대로 내보낸다. 나중에 결과와 비교할 입력 수치(정점·면·쿼드·범위)를 json으로 남긴다.
# 사용: SSOT/도구/블렌더실행.sh <작업본.blend> SSOT/도구/UV입력내보내기.py -- <출력폴더> <파츠이름> [파츠이름...]   (환경 변수 WHOLE=<이름>이면 모두 한 FBX로도)
import bpy, sys, os, json
import numpy as np
a = sys.argv[sys.argv.index("--") + 1:]
OUT, NAMES = os.path.abspath(a[0]), a[1:]
os.makedirs(OUT, exist_ok=True)
info = {}
for name in NAMES:
    o = bpy.data.objects[name]
    me = o.data
    mw = [list(r) for r in o.matrix_world]
    co = np.array([v.co for v in me.vertices])
    sizes = [len(p.vertices) for p in me.polygons]
    info[name] = {
        "정점": len(me.vertices), "면": len(me.polygons),
        "쿼드": sum(1 for s in sizes if s == 4), "삼각형": sum(1 for s in sizes if s == 3),
        "그외": sum(1 for s in sizes if s > 4),
        "삼각형환산": sum(s - 2 for s in sizes),
        "최소": co.min(0).round(5).tolist(), "최대": co.max(0).round(5).tolist(),
        "UV층": [u.name for u in me.uv_layers], "재질": [m.name if m else None for m in me.materials],
        "사용자지정노멀": me.has_custom_normals, "객체변환": mw,
    }
    for x in bpy.context.view_layer.objects:
        x.select_set(False)
    o.hide_set(False); o.select_set(True)
    bpy.context.view_layer.objects.active = o
    path = os.path.join(OUT, name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'MESH'},
                             mesh_smooth_type='OFF', use_mesh_modifiers=False,
                             add_leaf_bones=False, bake_anim=False, path_mode='STRIP')
    info[name]["파일"] = os.path.basename(path)
    info[name]["파일크기"] = os.path.getsize(path)
    print("내보냄", name, info[name]["정점"], info[name]["면"], "쿼드", info[name]["쿼드"],
          "삼각형환산", info[name]["삼각형환산"], "사용자지정노멀", me.has_custom_normals, os.path.getsize(path), "bytes")
with open(os.path.join(OUT, "입력수치.json"), "w", encoding="utf-8") as f:
    json.dump(info, f, ensure_ascii=False, indent=1)
# 환경변수 WHOLE=파일이름 이면 지정한 파츠를 모두 한 FBX에 담아 한 번 더 내보낸다(객체는 나눈 채).
W = os.environ.get("WHOLE")
if W:
    for x in bpy.context.view_layer.objects: x.select_set(False)
    for name in NAMES: bpy.data.objects[name].select_set(True)
    path = os.path.join(OUT, W + ".fbx")
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'MESH'},
                             mesh_smooth_type='OFF', use_mesh_modifiers=False,
                             add_leaf_bones=False, bake_anim=False, path_mode='STRIP')
    info["_" + W] = {"파츠": NAMES, "파일": os.path.basename(path), "파일크기": os.path.getsize(path),
                     "삼각형환산합": sum(info[n]["삼각형환산"] for n in NAMES)}
    with open(os.path.join(OUT, "입력수치.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1)
    print("통째로 내보냄", path, info["_" + W])
print("완료")
