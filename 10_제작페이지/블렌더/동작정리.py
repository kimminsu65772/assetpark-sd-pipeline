# 동작정리.py — 10단계 미리 보기용(작업 묶음 W14). 열린 blend에서 이름(| 뒤)이 앞붙임으로 시작하지 않는 Action을 지우고 다른 이름으로 저장한다.
# 작업본의 시험 동작(UAL_…, S70_… 등)이 미리 보기 동작과 이름이 겹쳐 보폭줄이기·팔벌림이 엉뚱한 동작을 고르지 않게 한다.
# 실행: SSOT/도구/블렌더실행.sh <입력.blend> 10_제작페이지/블렌더/동작정리.py -- <출력.blend> <앞붙임>
# 입력 blend는 고치지 않는다(다른 이름으로 저장).
import bpy, sys, traceback
try:
    a = sys.argv[sys.argv.index("--") + 1:]
    OUT, PFX = a[0], a[1]
    지움 = []
    for o in bpy.data.objects:
        if o.animation_data and o.animation_data.action and not o.animation_data.action.name.split("|")[-1].startswith(PFX):
            o.animation_data.action = None
    for act in list(bpy.data.actions):
        if not act.name.split("|")[-1].startswith(PFX):
            지움.append(act.name)
            bpy.data.actions.remove(act)
    남음 = [x.name for x in bpy.data.actions]
    bpy.context.preferences.filepaths.save_version = 0
    r = bpy.ops.wm.save_as_mainfile(filepath=OUT, relative_remap=True)
    assert 'FINISHED' in r
    print("ACTIONS_KEPT", len(남음), "REMOVED", len(지움), flush=True)
except Exception:
    traceback.print_exc(); print("ACTIONS_FAILED"); sys.exit(1)
