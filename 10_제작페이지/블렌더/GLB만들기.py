"""작업본(blend) → 제작 페이지 3D 보기용 GLB (작업 묶음 W01, 기능명세 1부 3-3·5-1절)

실행(창 없이, 저장소 루트에서, Git Bash):
    SSOT/도구/블렌더실행.sh <작업본.blend> 10_제작페이지/블렌더/GLB만들기.py -- <출력.glb> <정보.json>

하는 일:
- 내보낼 파츠: 메시 객체 가운데 렌더에서 숨기지 않은 것(객체와 그 컬렉션 모두). 예: `보관` 컬렉션의
  `TRIPO_원본`(렌더 숨김)은 빠진다. 파츠의 부모 뼈대(아마추어)와 그 동작(액션)도 함께 넣는다.
- 파츠마다 면 속성 `_FACEID`(정수, 작업본의 면 번호)를 붙인다. glTF는 면을 삼각형으로 나누고 정점을 쪼개므로,
  삼각형마다 이 값으로 원래 면을 찾는다. three.js에서는 `geometry.attributes._faceid`(이름이 소문자로 바뀜).
- UV는 첫 번째 UV 층(uv_layers[0])만 남겨 TEXCOORD_0으로 내보낸다. 텍스처는 GLB 안에 넣는다.
- 작업본은 저장하지 않는다(위 변경은 이 Blender 실행의 메모리에서만). 끝에 저장 함수를 부르지 않는다.

정보.json: 파츠마다 면 수·UV 층 이름·재질, 뼈대·동작 이름, 찾지 못한 텍스처, Blender 판.
"""

import json
import os
import sys

import bpy

면속성 = "_FACEID"


def 인자():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(a) != 2:
        raise SystemExit("인자: -- <출력.glb> <정보.json>")
    return os.path.abspath(a[0]), os.path.abspath(a[1])


def 렌더에보임(o) -> bool:
    if o.hide_render:
        return False
    return not any(c.hide_render for c in o.users_collection)


def main():
    출력, 정보파일 = 인자()
    파츠 = [o for o in bpy.data.objects if o.type == "MESH" and 렌더에보임(o)]
    if not 파츠:
        raise SystemExit("내보낼 메시 객체가 없습니다(렌더에 보이는 메시 0개).")
    뼈대 = sorted({o.parent for o in 파츠 if o.parent and o.parent.type == "ARMATURE"}, key=lambda x: x.name)
    for o in 파츠:
        for m in o.modifiers:
            if m.type == "ARMATURE" and m.object and m.object not in 뼈대:
                뼈대.append(m.object)

    정보 = {"파츠": [], "뼈대": [b.name for b in 뼈대], "동작": sorted(a.name for a in bpy.data.actions),
            "빠진객체": sorted(o.name for o in bpy.data.objects if o.type == "MESH" and o not in 파츠),
            "찾지못한텍스처": [], "블렌더": bpy.app.version_string, "면속성": 면속성,
            # W13: 3D 보기의 장 번호를 Blender 장 번호와 맞추려고(9단계 시간 막대)
            "장초당": bpy.context.scene.render.fps / (bpy.context.scene.render.fps_base or 1),
            "동작장": {a.name: [round(a.frame_range[0]), round(a.frame_range[1])] for a in bpy.data.actions}}

    for o in 파츠:
        me = o.data
        if me.users > 1:  # 다른 객체와 메시를 함께 쓰면 그 객체에도 번지므로 이 실행 안에서만 따로 떼어 쓴다
            o.data = me = me.copy()
        uv이름 = me.uv_layers[0].name if me.uv_layers else None
        # 첫 번째 UV 층만 남긴다(메모리에서만). 재질의 UV 맵 노드가 다른 층을 가리키면 그 이름도 첫 층으로.
        while len(me.uv_layers) > 1:
            me.uv_layers.remove(me.uv_layers[-1])
        if uv이름:
            me.uv_layers[0].active = True
            me.uv_layers[0].active_render = True
        if 면속성 in me.attributes:
            me.attributes.remove(me.attributes[면속성])
        at = me.attributes.new(면속성, "INT", "FACE")
        at.data.foreach_set("value", list(range(len(me.polygons))))
        재질 = []
        for m in me.materials:
            if not m:
                continue
            재질.append(m.name)
            for n in (m.node_tree.nodes if m.node_tree else []):
                if n.type == "UVMAP" and uv이름:
                    n.uv_map = uv이름
        정보["파츠"].append({"이름": o.name, "면수": len(me.polygons), "UV층": uv이름, "재질": 재질,
                           "수정자": [m.type for m in o.modifiers]})

    for im in bpy.data.images:
        if im.source == "FILE" and not im.packed_file:
            p = bpy.path.abspath(im.filepath)
            if not os.path.isfile(p):
                정보["찾지못한텍스처"].append({"이름": im.name, "경로": im.filepath})

    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    고를것 = 파츠 + 뼈대
    보이게한것 = []
    for o in 고를것:
        if o.name not in bpy.context.view_layer.objects:
            raise SystemExit(f"뷰 레이어에서 빠진 객체라 고를 수 없습니다: {o.name}")
        if o.hide_get():
            o.hide_set(False)
            보이게한것.append(o.name)
        o.select_set(True)
    bpy.context.view_layer.objects.active = 파츠[0]

    os.makedirs(os.path.dirname(출력), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=출력,
        export_format="GLB",
        use_selection=True,
        export_apply=False,          # 수정자를 적용하지 않음(면 번호가 작업본과 같게). 아마추어는 스킨으로
        export_attributes=True,      # _FACEID
        export_texcoords=True,
        export_normals=True,
        export_materials="EXPORT",
        export_image_format="AUTO",
        export_skins=True,
        export_animations=bool(뼈대),
        export_animation_mode="ACTIONS",
        export_yup=True,
    )
    if not os.path.isfile(출력):
        raise SystemExit("GLB가 만들어지지 않았습니다.")
    정보["보이게한객체"] = 보이게한것
    정보["크기"] = os.path.getsize(출력)
    with open(정보파일, "w", encoding="utf-8") as f:
        json.dump(정보, f, ensure_ascii=False, indent=2)
    print(f"GLB 만듦: 파츠 {len(파츠)}개, 면 {sum(p['면수'] for p in 정보['파츠'])}개, "
          f"동작 {len(정보['동작'])}개, 찾지 못한 텍스처 {len(정보['찾지못한텍스처'])}개, {정보['크기']} 바이트")


main()
