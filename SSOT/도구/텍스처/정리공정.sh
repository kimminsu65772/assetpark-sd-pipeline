#!/usr/bin/env bash
# 정리공정.sh — 텍스처 그림 정리(5-6)를 캐릭터의 공정 파일대로, 받은 그림에서 끝까지 한 번에 다시 만든다(공통 도구).
# 출처: 01_캐릭터/온천_검사/04_Blender/스크립트/텍스처정리_v004_만들기.sh에서 캐릭터와 상관없는 틀(멈춤 규칙·지문 비교·Blender 부르기·마지막 여백 채우기)만
#       이 파일로 옮기고, 캐릭터 값(경로·조각 번호·좌표·색)은 캐릭터의 공정 파일로 뺐다. 하는 일과 순서는 같다.
# 같은 입력이면 같은 그림이 나온다. 단계마다 실패하면 멈춘다(set -e).
# 사용(Git Bash, 저장소 루트에서): bash SSOT/도구/텍스처/정리공정.sh <공정 파일.sh> <출력 폴더>
#   예: bash SSOT/도구/텍스처/정리공정.sh 01_캐릭터/온천_검사/04_Blender/텍스처정리_v004/정리공정.sh <출력 폴더>
# 공정 파일(캐릭터 쪽, bash로 읽음)이 정하는 것:
#   MAP=<조각지도 폴더>  FP=<조각지문.json>  BLEND=<작업본.blend>  PARTS="a,b"(쉼표로, 있으면 TEX_PARTS로 모든 도구에 넘김. 비우면 도구 기본 네 파츠)  UVNAME=<UV 층>(있으면 TEX_UV, 비우면 첫 층)
#   steps() { … }  — 단계들. 결과 그림 <파츠>_구움.png를 $OUT에 둔다. 중간 결과는 $MID.
#   steps 안에서 쓸 수 있는 것: $T(이 폴더), $MAP, $OUT, $MID, blender <스크립트> [-- 인자](작업본으로 창 없는 Blender), winpath <경로>(Windows 경로)
# 이 파일이 하는 것: 0) 조각 번호가 규칙을 쓴 때와 같은지 지문 비교(UV·메시가 바뀌면 멈춤) → steps → 마지막) 여백 채우기(곧은 거리 기준)
# 시험: 환경 변수 BLEND_OVERRIDE=<사본.blend>면 공정 파일의 BLEND 대신 그 사본을 쓴다.
set -euo pipefail
export PYTHONIOENCODING=utf-8
T=SSOT/도구/텍스처
RECIPE=${1:?공정 파일}
OUT=${2:?출력 폴더}
MID=$OUT/_중간
PARTS=""; UVNAME=""
. "$RECIPE"
[ -n "$PARTS" ] && export TEX_PARTS=$PARTS
[ -n "$UVNAME" ] && export TEX_UV=$UVNAME
: "${MAP:?공정 파일에 MAP이 없다}" "${FP:?공정 파일에 FP가 없다}" "${BLEND:?공정 파일에 BLEND가 없다}"
[ -n "${BLEND_OVERRIDE:-}" ] && BLEND=$BLEND_OVERRIDE
declare -F steps >/dev/null || { echo "공정 파일에 steps 함수가 없다" >&2; exit 2; }
blender() { SSOT/도구/블렌더실행.sh "$BLEND" "$@"; }
winpath() { cygpath -w "$1"; }
mkdir -p "$OUT" "$MID"

# 0) 지문 비교
python $T/조각지문.py "$MAP" "$FP"

# 1~) 캐릭터 단계
steps

# 마지막) 여백 채우기
python $T/여백채우기.py "$MAP" "$OUT" "{}_구움.png" "$OUT"
echo "끝: $OUT"
