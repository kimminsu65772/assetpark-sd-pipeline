#!/usr/bin/env bash
# 블렌더실행.sh — 창 없는 Blender를 돌리고, 시작·렌더 로그("Saved:" 줄 등)를 걸러 스크립트가 print한 결과와 오류만 보여 준다.
# 토큰 절약용(사용자 지시 2026-11-23). 종료 코드는 Blender 것을 그대로 돌려준다. 실패하면 전체 로그 경로를 알려 준다.
# 사용(Git Bash): SSOT/도구/블렌더실행.sh <blend 파일 | -> <스크립트.py> [-- 스크립트 인자...]
#   blend 자리에 - 를 주면 빈 장면에서 시작한다. 보여 줄 줄 수는 환경변수 TAIL(기본 80).
BL="${BLENDER:-C:/Program Files/Blender Foundation/Blender 5.3/blender.exe}"
export PYTHONIOENCODING=utf-8
[ $# -lt 2 ] && { sed -n '2,6p' "$0"; exit 2; }
blend="$1"; py="$2"; shift 2
log="$(mktemp)"
if [ "$blend" = "-" ]; then "$BL" --background --python-exit-code 3 --python "$py" "$@" >"$log" 2>&1
else "$BL" --background "$blend" --python-exit-code 3 --python "$py" "$@" >"$log" 2>&1; fi
rc=$?
saved=$(grep -c 'Saved:' "$log")
grep -vE 'Saved:|^Fra:|Time:|Read blend|^Blender [0-9]|Blender quit|addon_utils|^[[:space:]]*$|^Info: Saved|^정보: 저장된' "$log" | tail -n "${TAIL:-80}"
[ "$saved" -gt 0 ] && echo "[그림 ${saved}장 저장]"
if [ $rc -ne 0 ]; then echo "[Blender 종료 코드 $rc] 전체 로그: $log"; else rm -f "$log"; fi
exit $rc
