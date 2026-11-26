#!/usr/bin/env bash
# TRIPO리그체크.sh — TRIPO에 올릴 리깅 입력을 무료 rig-check로 확인한다(공식 가격: 리그 체크 무료, 2026-11-24 확인. 실행 뒤 credits_consumed도 출력한다).
# 리깅 입력은 반드시 SSOT/도구/TRIPO입력내보내기.py로 TRIPO 원본 방향(앞 +x)으로 낸 것을 쓴다. 방향이 틀리면 riggable false가 나온다.
# 사용(Git Bash): SSOT/도구/TRIPO리그체크.sh <입력.glb|fbx> <기록 폴더>
#   tripo 명령은 환경변수 TRIPO(기본 tripo). 결과: <기록 폴더>/리그체크_결과.json(응답), 리그체크_작업.json(작업 조회)
#   종료 코드: riggable true면 0, false면 1, 명령 실패면 2. rig_type(추천 몸 유형)을 함께 출력한다.
T="${TRIPO:-tripo}"; export PYTHONIOENCODING=utf-8
[ $# -lt 2 ] && { sed -n '2,6p' "$0"; exit 2; }
IN="$1"; OUT="$2"; mkdir -p "$OUT"
"$T" anim check "$IN" --json --yes --no-open -o "$OUT/tripo-out" > "$OUT/리그체크_결과.json" 2> "$OUT/리그체크_stderr.txt" || { cat "$OUT/리그체크_stderr.txt"; exit 2; }
id=$(python -c "import json,sys;print(json.load(open(sys.argv[1],encoding='utf-8'))['task_id'])" "$OUT/리그체크_결과.json") || exit 2
"$T" task get "$id" --json > "$OUT/리그체크_작업.json" || exit 2
python - "$OUT/리그체크_작업.json" <<'PY'
import json,sys,re
p=sys.argv[1]; s=open(p,encoding='utf-8').read(); s=re.sub(r'https?://[^"]+','<url 지움>',s); open(p,'w',encoding='utf-8').write(s)
d=json.loads(s); o=d.get("output") or {}
print(json.dumps({"task_id":d.get("task_id"),"riggable":o.get("riggable"),"rig_type":o.get("rig_type"),"credits_consumed":d.get("credits_consumed"),"normalize_scale":o.get("normalize_scale")},ensure_ascii=False))
sys.exit(0 if o.get("riggable") is True else 1)
PY
