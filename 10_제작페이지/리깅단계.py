"""8·9단계 리깅 화면의 서버 쪽 (작업 묶음 W13, 기능명세 2부 20·21절, SSOT 단계/6_리깅)

8 오토 리깅 — 실행(승인·한 번만·가짜 실행)은 W07의 `승인.py`를 그대로 쓴다.
- 요청: 에이전트가 `에이전트.py 리깅요청 <입력>`으로 만든다. 입력은 `SSOT/도구/TRIPO입력내보내기.py`로 TRIPO 원본 방향(앞 +x)으로 낸 GLB.
- 리그 체크(무료, 승인 필요 없음): 페이지 단추 → 서버가 가장 최근 요청의 입력으로 `tripo anim check`. 결과는 `08_오토리깅/리그체크.json`.
  가짜 실행 모드에서는 흉내만 낸다(`--가짜결과 실패`면 riggable false). 진짜 리그 체크는 시험하지 않았다.
- 승인을 막는 것(4-5에 더함): 리그 체크 없음·false·체크 뒤 입력이 바뀜·요청의 몸 유형이 체크 추천과 다름.
- 받은 뒤 확인: 에이전트가 `리깅확인`으로 `08_오토리깅/확인.json`(방향·되돌림·정점 자리 차·UV·가중치 없는 정점·뼈 수와 이름).
9 리깅 수정
- 에이전트가 시험 동작(걷기·달리기·잽·크로스)을 옮기고 교차를 재서 `리깅교차`로 `09_리깅수정/교차.json`(동작마다 관통이 남은 장).
- 치마·자락·소매 도구로 만든 후보는 `리깅비교`로 `09_리깅수정/비교.json`. 사용자가 고르면 페이지가 `고른후보.json`을 쓴다.
- 표시(칠하기·구간 리포트)는 W03의 보내기 묶음에 `자리.동작` {이름, 시작장, 끝장}을 붙여 간다.
"""

from __future__ import annotations

import hashlib
import json
import shlex
import subprocess
import time
from pathlib import Path

서버 = None


class 요청오류(Exception):  # 묶기 전 자리
    pass


def 묶기(모듈) -> None:
    global 서버, 요청오류
    서버 = 모듈
    요청오류 = 모듈.요청오류


오토 = 8
수정 = 9
단계들 = (오토, 수정)
SSOT뼈수 = 67   # SSOT 단계/6_리깅 "TRIPO 뼈대(67개)". 온천 검사는 78개(캐릭터 진행기록). 다르면 적되 막지 않음(2부 20절)
몸유형들 = ("biped", "quadruped", "hexapod", "octopod", "avian", "serpentine", "aquatic", "others")
# 2부 21절 시험 동작 묶음(사용자 2026-11-24). 동작 이름(GLB 클립)에서 이 낱말로 찾는다
시험동작 = (("걷기", ("walk",)), ("달리기", ("sprint", "run")), ("잽", ("jab",)), ("크로스", ("cross",)))
도구들 = ("자락리깅", "팔벌림", "소매리깅", "보폭줄이기", "기타")
안내판 = "0.11.2"


def 리깅값(몸: str) -> dict:
    return {"무엇": f"오토 리깅(TRIPO rig v3.0, {몸})",
            "틀": "tripo anim rig {입력} --model v3.0 --rig-type " + 몸 + " --out-format glb",
            "크레딧": "모름",
            "근거": f"SSOT 단계/6_리깅 6-0, process.md(tripo-cli {안내판}): biped 등은 rig v3.0이 기본, 몸 유형은 리그 체크 추천값. 가격은 안내에 없어 '모름'"}


# ---------------------------------------------------------------- 파일

def 폴더(a, 이름, 번호, 만들기=False) -> Path:
    return a.단계폴더(이름, 번호, 만들기=만들기)


def 읽기(p: Path) -> dict | None:
    if not p.is_file():
        return None
    try:
        v = 서버.json_읽기(p)
        return v if isinstance(v, dict) else None
    except Exception:
        return None


def 상대(a, p: Path) -> str:
    return p.resolve().relative_to(a.폴더.resolve()).as_posix()


def 파일열쇠(f: Path) -> str:
    h = hashlib.sha256()
    with open(f, "rb") as r:
        for 조각 in iter(lambda: r.read(1 << 20), b""):
            h.update(조각)
    return h.hexdigest()[:12]


def 쓰기(a, 이름, 번호, 파일이름: str, 값: dict) -> Path:
    p = 폴더(a, 이름, 번호, 만들기=True) / 파일이름
    서버.json_쓰기(p, {"꼴버전": 서버.꼴버전, "만든시각": 서버.지금(), "작업본해시": a._지금작업본해시(이름), **값})
    return p


def 최근요청(a, 이름) -> dict | None:
    for q in reversed(서버.승인.요청파일들(a, 이름, 오토)):
        v = 읽기(q)
        if v is not None:
            return dict(v, 파일=q.name)
    return None


def 요청입력(v: dict) -> list[str]:
    return 서버.생성단계.요청입력(v)


def 요청몸(v: dict) -> str:
    try:
        t = shlex.split(v.get("명령") or "", posix=True)
    except ValueError:
        return ""
    return t[t.index("--rig-type") + 1] if "--rig-type" in t[:-1] else ""


def 정보(a, 이름) -> dict:
    """3D 보기 GLB의 정보(W01 GLB만들기.py): 뼈대·동작·장초당·동작장. 없으면 빈 것."""
    try:
        h = a._지금작업본해시(이름)
        return (서버.보기만들기.캐시(a.보기폴더(이름, 만들기=False), h) or {}) if h else {}
    except Exception:
        return {}


# ---------------------------------------------------------------- 8단계: 요청·리그 체크·승인 막기

def 요청하기(a, 이름, 입력: str | None) -> dict:
    """에이전트 명령 `리깅요청`: 오토 리깅 승인 요청을 만든다. 몸 유형은 리그 체크 추천값(없으면 biped)."""
    f = a.저장소파일(입력 or "")
    if not f:
        raise 요청오류(400, "8단계 입력 파일(저장소 기준 경로)이 필요합니다: SSOT/도구/TRIPO입력내보내기.py로 TRIPO 원본 방향(앞 +x)으로 낸 GLB.")
    if f.suffix.lower() not in (".glb", ".fbx", ".obj", ".stl"):
        raise 요청오류(400, "입력은 GLB·FBX·OBJ·STL이어야 합니다(tripo anim).")
    체크 = 읽기(폴더(a, 이름, 오토) / "리그체크.json")
    몸 = (체크 or {}).get("rig_type") if (체크 or {}).get("입력") == 상대(a, f) else None
    몸 = 몸 if 몸 in 몸유형들 else "biped"
    기 = 리깅값(몸)
    명령 = 기["틀"].format(입력=shlex.quote(상대(a, f)))
    r = 서버.승인.요청만들기(a, 이름, 오토, 기["무엇"], 명령, 기["크레딧"], 1, 만든곳="에이전트 리깅요청")
    return dict(r, 무엇=기["무엇"], 명령=명령, 크레딧=기["크레딧"], 횟수=1, 근거=기["근거"])


def _진짜체크(a, f: Path, 로그: list[str]) -> dict:
    """tripo anim check → task get (SSOT/도구/TRIPO리그체크.sh와 같은 차례). 시험하지 않았다."""
    t = 서버.승인.tripo찾기()
    if not t:
        raise 요청오류(409, "tripo-cli가 이 PC에 없습니다(로컬/tripo-cli). 진짜 리그 체크를 할 수 없습니다.")
    def 부르기(인자):
        r = subprocess.run(t + 인자, cwd=str(a.폴더), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        로그.append(f"{' '.join(인자[:2])}: 종료 코드 {r.returncode}")
        if r.returncode != 0:
            raise 요청오류(502, f"리그 체크 실패: {서버.승인.가리기(r.stderr)[-300:]}")
        return json.loads(r.stdout[r.stdout.index("{"):])
    v = 부르기(["anim", "check", str(f), "--json", "--yes", "--no-open"])
    일 = 부르기(["task", "get", str(v["task_id"]), "--json"])
    o = 일.get("output") or {}
    return {"riggable": o.get("riggable"), "rig_type": o.get("rig_type"), "작업번호": 일.get("task_id"),
            "쓴크레딧": 일.get("credits_consumed")}


def 리그체크하기(a, 이름, 몸: dict) -> dict:
    """페이지 단추 '리그 체크'(무료). 가장 최근 오토 리깅 요청의 입력으로 한다."""
    a._주인확인(몸.get("탭"), 이름)
    v = 최근요청(a, 이름)
    입력 = 요청입력(v) if v else []
    f = a.저장소파일(입력[0]) if 입력 else None
    if not f:
        raise 요청오류(409, "리그 체크할 입력이 없습니다. 에이전트가 입력을 내고 '리깅요청'을 먼저 해야 합니다.")
    로그: list[str] = []
    가짜 = 서버.승인.모드 != "진짜"
    if 가짜:
        r = {"riggable": 서버.승인.가짜결과 != "실패", "rig_type": "biped", "작업번호": "가짜-리그체크", "쓴크레딧": 0}
        로그.append(f"가짜 리그 체크(가짜 결과: {서버.승인.가짜결과})")
    else:
        r = _진짜체크(a, f, 로그)
    p = 쓰기(a, 이름, 오토, "리그체크.json", dict(r, 입력=상대(a, f), 입력열쇠=파일열쇠(f), 가짜=가짜, 요청파일=v["파일"], 로그=로그))
    서버.기록(f"리그 체크: riggable {r['riggable']} ({'가짜' if 가짜 else '진짜'})", a, 이름)
    if r["riggable"] is True:
        a.알림쓰기(이름, 오토, f"리그 체크 통과(riggable true, {r.get('rig_type') or '몸 유형 모름'}){' · 가짜' if 가짜 else ''}. "
                  + ("요청의 몸 유형이 추천과 다르면 에이전트에게 다시 요청해 달라고 하세요." if 요청몸(v) != r.get("rig_type") else "승인할 수 있습니다."), "결정 필요")
    else:
        a.알림쓰기(이름, 오토, "리그 체크 false — 승인을 막았습니다. 원인 후보: 입력 방향(가장 흔함, 온천 검사 기록: 작업본은 앞 −y, TRIPO는 앞 +x)."
                  " 에이전트가 SSOT/도구/TRIPO입력내보내기.py로 다시 내야 합니다.", "막힘")
    return {"됨": True, "파일": 상대(a, p), "riggable": r["riggable"], "rig_type": r.get("rig_type"), "가짜": 가짜}


def 체크상태(a, 이름, v: dict | None) -> tuple[dict | None, str]:
    """(리그체크 값, 막는 까닭). 까닭이 빈 글이면 체크가 지금 요청에 맞고 riggable true."""
    체크 = 읽기(폴더(a, 이름, 오토) / "리그체크.json")
    입력 = 요청입력(v) if v else []
    if not 체크:
        return None, "리그 체크(무료)를 먼저 눌러 주세요"
    if not 입력 or 체크.get("입력") != 입력[0]:
        return 체크, "리그 체크가 지금 요청의 입력과 다른 파일을 봄 — 다시 눌러 주세요"
    f = a.저장소파일(입력[0])
    if not f or 파일열쇠(f) != 체크.get("입력열쇠"):
        return 체크, "리그 체크 뒤 입력 파일이 바뀜 — 다시 눌러 주세요"
    if 체크.get("riggable") is not True:
        return 체크, "리그 체크가 false — 원인 후보: 입력 방향(가장 흔함). 에이전트가 TRIPO입력내보내기.py로 다시 내야 함"
    if 체크.get("rig_type") and 요청몸(v) != 체크["rig_type"]:
        return 체크, f"요청의 몸 유형({요청몸(v)})이 리그 체크 추천({체크['rig_type']})과 다름 — 에이전트에게 요청을 다시 만들어 달라고 하세요"
    return 체크, ""


def 막는이유(a, 이름, 번호, v: dict) -> str:
    """승인 단추를 막는 까닭(W07 `승인.추가막기[8]`)."""
    입력 = 요청입력(v)
    if not 입력 or any(a.저장소파일(x) is None for x in 입력):
        return f"요청의 입력 파일이 없습니다: {', '.join(입력) or '(없음)'}"
    return 체크상태(a, 이름, v)[1]


# ---------------------------------------------------------------- 8단계: 받은 뒤 확인(에이전트)

확인꼭 = {"방향", "되돌림", "정점자리차", "UV같음", "가중치없는정점", "뼈수"}
확인됨 = 확인꼭 | {"뼈이름", "정점수전", "정점수후", "정점수다름", "받은파일", "그림", "메모"}


def 확인쓰기(a, 이름, v: dict) -> dict:
    """에이전트 명령 `리깅확인`(SSOT 6_리깅 6-0의 끝 표시): `08_오토리깅/확인.json`."""
    if not isinstance(v, dict):
        raise 요청오류(400, "확인 파일은 JSON 객체여야 합니다.")
    if set(v) - 확인됨:
        raise 요청오류(400, f"모르는 항목: {sorted(set(v) - 확인됨)} (쓸 수 있는 것: {sorted(확인됨)})")
    if 확인꼭 - set(v):
        raise 요청오류(400, f"빠진 항목: {sorted(확인꼭 - set(v))}")
    for k in ("방향", "되돌림", "UV같음"):
        if not isinstance(v[k], bool):
            raise 요청오류(400, f"'{k}'은 참/거짓이어야 합니다.")
    for k in ("정점자리차", "가중치없는정점", "뼈수", "정점수전", "정점수후"):
        if k in v and not (isinstance(v[k], (int, float)) and not isinstance(v[k], bool) and v[k] >= 0):
            raise 요청오류(400, f"'{k}'은 0 이상의 숫자여야 합니다(정점자리차는 mm).")
    if "뼈이름" in v and (not isinstance(v["뼈이름"], list) or not all(isinstance(x, str) for x in v["뼈이름"])):
        raise 요청오류(400, "'뼈이름'은 글 목록이어야 합니다.")
    for k in ("받은파일", "그림"):
        if k in v:
            if not isinstance(v[k], list) or not all(isinstance(x, str) and a.저장소파일(x) for x in v[k]):
                raise 요청오류(400, f"'{k}'은 저장소 안에 있는 파일 경로 목록이어야 합니다.")
    if v.get("정점수전") is not None and v.get("정점수후") is not None and v["정점수전"] != v["정점수후"] and not str(v.get("정점수다름") or "").strip():
        raise 요청오류(400, "정점 수가 다르면 '정점수다름'에 같은 자리 겹침인지 확인한 것을 적어 주세요(2부 20절 예외).")
    p = 쓰기(a, 이름, 오토, "확인.json", dict(v, 만든곳="10_제작페이지/에이전트.py 리깅확인"))
    서버.기록(f"오토 리깅 확인: {p.name}", a, 이름)
    if v["뼈수"] != SSOT뼈수:
        a.알림쓰기(이름, 오토, f"뼈 수 {v['뼈수']}개 — SSOT 6_리깅의 TRIPO 뼈대 {SSOT뼈수}개와 다릅니다. 막지 않습니다(뼈 이름 규격은 50_미정과_초안 2절, 사용자 결정 전).", "안내")
    return {"결과": "씀", "파일": 상대(a, p), "모자람": 완료모자람(a, 이름, 오토)}


# ---------------------------------------------------------------- 9단계: 교차·비교(에이전트), 후보 고르기(페이지)

def 시험동작찾기(이름: str) -> str:
    s = 이름.lower()
    for 보임, 낱말 in 시험동작:
        if any(w in s for w in 낱말):
            return 보임
    return ""


def 교차쓰기(a, 이름, v: dict) -> dict:
    """`리깅교차`: {동작: [{이름(GLB 동작 이름), 장수, 교차수, 관통장: [장 번호], 찍은그림: [...], 장초당?, 시작장?}], 확인범위: 글}."""
    목록 = v.get("동작") if isinstance(v, dict) else None
    if not isinstance(목록, list) or not 목록:
        raise 요청오류(400, "'동작'은 동작마다 {이름, 장수, 교차수, 관통장} 목록이어야 합니다.")
    for x in 목록:
        if not isinstance(x, dict) or not isinstance(x.get("이름"), str) or not x["이름"]:
            raise 요청오류(400, "동작 한 줄에 '이름'(GLB의 동작 이름)이 없습니다.")
        for k in ("장수", "교차수"):
            if not (isinstance(x.get(k), int) and not isinstance(x.get(k), bool) and x[k] >= 0):
                raise 요청오류(400, f"{x['이름']}: '{k}'은 0 이상의 정수여야 합니다.")
        if not isinstance(x.get("관통장", []), list) or not all(isinstance(i, int) and not isinstance(i, bool) for i in x.get("관통장", [])):
            raise 요청오류(400, f"{x['이름']}: '관통장'은 장 번호(정수) 목록이어야 합니다.")
        if not all(isinstance(g, str) and a.저장소파일(g) for g in x.get("찍은그림", [])):
            raise 요청오류(400, f"{x['이름']}: '찍은그림'은 저장소 안의 그림 경로 목록이어야 합니다(동작찍기.py).")
        for k in ("장초당", "시작장"):
            if k in x and not (isinstance(x[k], (int, float)) and not isinstance(x[k], bool) and x[k] >= 0):
                raise 요청오류(400, f"{x['이름']}: '{k}'은 0 이상의 숫자여야 합니다.")
    p = 쓰기(a, 이름, 수정, "교차.json", {"동작": 목록, "확인범위": str(v.get("확인범위") or "")[:400]})
    합 = sum(x["교차수"] for x in 목록)
    서버.기록(f"리깅 교차 기록: 동작 {len(목록)}개, 교차 {합}", a, 이름)
    a.알림쓰기(이름, 수정, f"시험 동작 {len(목록)}개의 교차를 쟀습니다(교차 {합}, 관통이 남은 장은 시간 막대의 빨간 눈금). 재생해 보고 이상한 곳을 멈춘 장면에 칠하거나 구간 리포트로 보내 주세요.", "결정 필요")
    return {"결과": "씀", "파일": 상대(a, p), "교차합": 합}


def 비교쓰기(a, 이름, v: dict) -> dict:
    """`리깅비교`: {후보: [{번호, 이름, 도구, 값, 그림, 교차수, 새흠}], 설명}. 새 비교를 쓰면 앞의 고른 것은 기록으로만 남는다."""
    목록 = v.get("후보") if isinstance(v, dict) else None
    if not isinstance(목록, list) or not 목록:
        raise 요청오류(400, "'후보'는 {번호, 이름, 도구, 그림} 목록이어야 합니다.")
    본 = set()
    for x in 목록:
        if not isinstance(x, dict) or not isinstance(x.get("번호"), str) or not x["번호"] or x["번호"] in 본:
            raise 요청오류(400, "후보마다 겹치지 않는 '번호'(예: A)가 있어야 합니다.")
        본.add(x["번호"])
        if not isinstance(x.get("이름"), str) or not x["이름"]:
            raise 요청오류(400, f"후보 {x['번호']}: '이름'이 없습니다.")
        if x.get("도구") not in 도구들:
            raise 요청오류(400, f"후보 {x['번호']}: '도구'는 {' / '.join(도구들)}.")
        if not all(isinstance(g, str) and a.저장소파일(g) for g in x.get("그림", [])):
            raise 요청오류(400, f"후보 {x['번호']}: '그림'은 저장소 안의 그림 경로 목록이어야 합니다.")
        if "교차수" in x and not (isinstance(x["교차수"], int) and not isinstance(x["교차수"], bool) and x["교차수"] >= 0):
            raise 요청오류(400, f"후보 {x['번호']}: '교차수'는 0 이상의 정수.")
        for k in ("값", "새흠"):
            if k in x and not isinstance(x[k], str):
                raise 요청오류(400, f"후보 {x['번호']}: '{k}'는 글.")
    p = 쓰기(a, 이름, 수정, "비교.json", {"후보": 목록, "설명": str(v.get("설명") or "")[:400], "비교번호": str(time.time_ns())})
    서버.기록(f"리깅 후보 비교: {len(목록)}개", a, 이름)
    a.알림쓰기(이름, 수정, f"후보 {len(목록)}개를 비교 줄에 올렸습니다. 그림을 보고 하나를 골라 주세요(새 흠이 있는 후보도 고를 수 있음).", "결정 필요")
    return {"결과": "씀", "파일": 상대(a, p)}


def 비교읽기(a, 이름) -> dict | None:
    try:
        return 읽기(폴더(a, 이름, 수정) / "비교.json")
    except Exception:
        return None


def 후보고르기(a, 이름, 몸: dict) -> dict:
    """페이지 '후보 고르기': `09_리깅수정/고른후보.json`. 에이전트가 읽고 그 후보를 작업본에 넣는다."""
    a._주인확인(몸.get("탭"), 이름)
    비 = 비교읽기(a, 이름)
    번호 = 몸.get("번호")
    if not 비 or 번호 not in {x.get("번호") for x in 비.get("후보") or []}:
        raise 요청오류(409, "고를 후보가 없습니다(비교가 바뀌었을 수 있음). 화면을 새로 고쳐 주세요.")
    후 = next(x for x in 비["후보"] if x.get("번호") == 번호)
    p = 쓰기(a, 이름, 수정, "고른후보.json", {"번호": 번호, "이름": 후["이름"], "비교번호": 비.get("비교번호", ""), "누가": "사용자"})
    서버.기록(f"리깅 후보 고름: {번호} {후['이름']}", a, 이름)
    return {"됨": True, "파일": 상대(a, p), "번호": 번호}


def 고른읽기(a, 이름, 비: dict | None) -> dict | None:
    try:
        g = 읽기(폴더(a, 이름, 수정) / "고른후보.json")
    except Exception:
        return None
    return g if g and 비 and g.get("비교번호") == 비.get("비교번호") else None


# ---------------------------------------------------------------- 끝나는 조건(2부 20·21절)

def 완료모자람(a, 이름, 번호) -> list[str]:
    모자람 = []
    if 번호 == 오토:
        가져옴 = (a.상태보기(이름)["단계"][번호 - 1] or {}).get("출처") in 서버.가져오기.출처들   # W08: 뼈대가 있는 모델을 가져옴
        실행 = 서버.생성단계.마지막실행(a, 이름, 오토)
        if not 가져옴:
            if not 실행 or 실행.get("실행") != "실행됨":
                모자람.append("오토 리깅을 실행해 받은 결과가 없음(리그 체크 → 승인 → 실행됨)")
            체크 = 읽기(폴더(a, 이름, 오토) / "리그체크.json")
            if not 체크 or 체크.get("riggable") is not True:
                모자람.append("리그 체크 riggable true 기록이 없음")
        c = 읽기(폴더(a, 이름, 오토) / "확인.json")
        if not c:
            모자람.append("받은 것 확인(6-0)이 없음 — 에이전트 '리깅확인'")
            return 모자람
        if 실행 and c.get("만든시각", "") < (실행.get("실행끝시각") or ""):
            모자람.append("확인이 마지막 실행보다 오래됨 — 새로 받은 것을 다시 확인해야 함")
        if not c["방향"] or not c["되돌림"]:
            모자람.append("받은 것을 작업본 방향으로 되돌리지 않음(TRIPO받은것되돌리기.py)")
        if c["정점자리차"] != 0:
            모자람.append(f"정점 자리 차 {c['정점자리차']} mm(0이어야 함)")
        if not c["UV같음"]:
            모자람.append("받은 것의 UV가 작업본과 다름")
        if c["가중치없는정점"] != 0:
            모자람.append(f"가중치 없는 정점 {c['가중치없는정점']}개(0이어야 함)")
        return 모자람
    안된 = [q.name for q, v in a.묶음들(이름, 번호) if v.get("묶음상태") in ("보냄", "처리 중")]
    if 안된:
        모자람.append(f"처리 안 된 묶음 {len(안된)}개(사용자가 본 관통은 고침 또는 둠으로 처리돼야 함)")
    교 = 읽기(폴더(a, 이름, 수정) / "교차.json")
    if not 교:
        모자람.append("교차 수 기록이 없음 — 에이전트 '리깅교차'")
    elif 교.get("작업본해시") != a._지금작업본해시(이름):
        모자람.append("교차 기록이 지금 작업본보다 오래됨 — 다시 재야 함")
    return 모자람


# ---------------------------------------------------------------- 화면

def 보기(a, 이름, 번호) -> dict:
    """옆 기둥·시간 막대에 그릴 것."""
    if 번호 not in 단계들 + (10,):
        raise 요청오류(400, "8·9·10단계만 있습니다.")
    g = 정보(a, 이름)
    값 = {"단계": 번호, "모자람": 완료모자람(a, 이름, 번호), "뼈대": g.get("뼈대") or [], "glb동작": g.get("동작") or [],
         "장초당": g.get("장초당"), "동작장": g.get("동작장") or {}, "SSOT뼈수": SSOT뼈수}
    if 번호 == 오토:
        v = 최근요청(a, 이름)
        체크, 까닭 = 체크상태(a, 이름, v) if v else (읽기(폴더(a, 이름, 오토) / "리그체크.json"), "에이전트가 아직 입력을 내고 '리깅요청'을 하지 않음")
        실행 = 서버.생성단계.마지막실행(a, 이름, 오토)
        값.update({"기본": {k: 리깅값("biped")[k] for k in ("무엇", "크레딧", "근거")},
                  "요청": {"파일": v["파일"], "입력": (요청입력(v) or [""])[0], "몸": 요청몸(v), "승인": v.get("승인"), "실행": v.get("실행")} if v else None,
                  "체크": 체크, "체크까닭": 까닭, "가짜모드": 서버.승인.모드 != "진짜",
                  "실행": {"실행": 실행.get("실행"), "가짜": bool((실행.get("결과") or {}).get("가짜")), "끝시각": 실행.get("실행끝시각") or ""} if 실행 else None,
                  "확인": 읽기(폴더(a, 이름, 오토) / "확인.json")})
        return 값
    if 번호 == 10:   # W14: 10단계 시간 막대. 교차는 에이전트 '동작옮김' 기록(옮김.json)의 성공한 동작
        옮 = 읽기(폴더(a, 이름, 10) / "옮김.json") or {}
        줄 = [x for x in 옮.get("동작") or [] if isinstance(x, dict) and x.get("성공") and x.get("이름")]
        값.update({"교차": dict(옮, 동작=줄) if 옮 else None, "교차옛것": bool(옮 and 옮.get("작업본해시") != a._지금작업본해시(이름)),
                  "동작보임": {n: next((x["원본"] for x in 줄 if x["이름"] == n), "") or 시험동작찾기(n) for n in 값["glb동작"]},
                  "새관통": [x["이름"] for x in 줄 if x.get("새관통")]})
        return 값
    교 = 읽기(폴더(a, 이름, 수정) / "교차.json")
    비 = 비교읽기(a, 이름)
    동작들 = {x["이름"]: x for x in (교 or {}).get("동작") or [] if isinstance(x, dict)}
    있는것 = {시험동작찾기(n) for n in list(동작들) + list(값["glb동작"])}
    값.update({"교차": 교, "교차옛것": bool(교 and 교.get("작업본해시") != a._지금작업본해시(이름)),
              "시험동작": [{"이름": n, "있음": n in 있는것} for n, _ in 시험동작],
              "동작보임": {n: 시험동작찾기(n) for n in 값["glb동작"]},
              "비교": 비, "고른후보": 고른읽기(a, 이름, 비),
              "넘어온": 서버.동작단계.넘어온리포트(a, 이름)})   # W14: 10단계에서 리깅 쪽으로 넘어온 리포트
    return 값


def 바뀜(a, 이름, 번호) -> str:
    try:
        d = 폴더(a, 이름, 번호)
    except Exception:
        return ""
    조각 = []
    더 = []
    try:
        if 번호 == 9:   # W14: 10단계 처리 결과(넘어온 리포트)
            더 = list(폴더(a, 이름, 10).glob("처리_*.json"))
    except Exception:
        pass
    for p in [d / "리그체크.json", d / "확인.json", d / "교차.json", d / "비교.json", d / "고른후보.json", d / "옮김.json"] + list(d.glob("승인_*.json")) + list(d.glob("보내기_*.json")) + 더:
        try:
            조각.append(f"{p.name}:{p.stat().st_mtime_ns}")
        except OSError:
            pass
    return "|".join(sorted(조각))
