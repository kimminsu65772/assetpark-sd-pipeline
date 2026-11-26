# 텍스처바꿔보기.py — 작업본 파츠 재질의 그림을 다른 폴더의 그림으로 바꾼 검수용 사본을 따로 저장한다(작업본은 저장하지 않음).
# 그림은 사본에 포장한다. 비교 그림(다각도검수.py --전)용.
# 사용: 블렌더실행.sh <작업본.blend> 텍스처바꿔보기.py -- <그림 폴더> <그림 이름 꼴(예: {}_구움.png)> <저장할 blend>
import bpy, sys, os
a = sys.argv[sys.argv.index("--") + 1:]
D, PAT, OUT = os.path.abspath(a[0]), a[1], os.path.abspath(a[2])
for n in (__import__("os").environ.get("TEX_PARTS") or "파츠_헤어,파츠_얼굴,파츠_상체,파츠_하체").split(","):
    m = bpy.data.objects[n].data.materials[0]
    tn = next(nd for nd in m.node_tree.nodes if nd.type == 'TEX_IMAGE')
    img = bpy.data.images.load(os.path.join(D, PAT.format(n)), check_existing=False)
    img.pack(); tn.image = img
    print(n, img.size[:])
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT, copy=True)
print("저장", OUT)
