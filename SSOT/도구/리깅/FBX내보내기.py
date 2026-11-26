# FBX내보내기.py — 뼈대와 그 뼈대를 따르는 메시, 들어 있는 모든 동작을 FBX 하나로 내보내고, 옆에 Unity Humanoid 뼈 대응표(<이름>.humanoid.txt)를 쓴다(공용 도구, blend는 저장하지 않음).
# 교복 사무라이 `…/유니티샘플_v033/FBX내보내기.py`를 고친 것. Unity 쪽 설정은 ModelSample/Assets/Editor/OnsenSetup.cs가 이 대응표를 읽는다.
# 실행: SSOT/도구/블렌더실행.sh <리깅.blend> SSOT/도구/리깅/FBX내보내기.py -- <리깅설정.json> <출력.fbx>
import bpy, sys, json, os, traceback
try:
    a = sys.argv[sys.argv.index("--") + 1:]; cfg = json.load(open(a[0], encoding="utf-8")); OUT = a[1]
    arm = bpy.data.objects[cfg["armature"]]; vl = bpy.context.view_layer; vl.objects.active = arm
    if bpy.context.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
    arm.data.pose_position = 'POSE'
    if arm.animation_data: arm.animation_data.action = None
    for pb in arm.pose.bones: pb.location = (0, 0, 0); pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    bpy.ops.object.select_all(action='DESELECT')
    parts = [o for o in bpy.data.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' and m.object == arm for m in o.modifiers)]
    for o in [arm] + parts: o.hide_set(False); o.hide_viewport = False; o.select_set(True)
    print("PARTS", [o.name for o in parts], "ACTIONS", sorted(x.name for x in bpy.data.actions), "fps", bpy.context.scene.render.fps)
    r = bpy.ops.export_scene.fbx(filepath=OUT, use_selection=True, object_types={'MESH', 'ARMATURE'}, add_leaf_bones=False, use_armature_deform_only=False, bake_anim=True, bake_anim_use_all_actions=True,
                                 bake_anim_use_nla_strips=False, bake_anim_step=1, bake_anim_simplify_factor=0, path_mode='COPY', embed_textures=True,
                                 apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL')   # Unity에서 뼈 크기 배율이 1이 되게(UniVRM 스프링본이 배율로 반지름을 키움)
    assert 'FINISHED' in r
    with open(os.path.splitext(OUT)[0] + ".humanoid.txt", "w", encoding="utf-8") as fh:
        for k, v in cfg["humanoid"].items(): fh.write("%s=%s\n" % (k, v))
    print("FBX_DONE", OUT)
except Exception:
    traceback.print_exc(); print("FBX_FAILED"); sys.exit(1)
