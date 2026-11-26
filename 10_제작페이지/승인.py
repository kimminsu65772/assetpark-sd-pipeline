"""돈이 드는 실행: 승인 요청과 TRIPO 실행 (작업 묶음 W07, 기능명세 1부 2-1 승인_<시각>.json · 4-4 · 4-5 · 9절 9번)

- 요청은 에이전트가 `에이전트.py 승인요청`으로 만든다(단계 화면 W09~W14가 같은 함수 `요청만들기`를 쓴다).
- 페이지는 요청의 값(명령·크레딧·횟수)을 그대로 보이고, 승인을 누르면 보인 값을 서버에 돌려보낸다.
  서버는 파일의 값해시가 명령의 SHA-256과 같고, 페이지가 보인 값이 파일 값과 같을 때만 **한 번** 실행한다.
- 실행 모드: 기본은 **가짜 실행**(TRIPO에 요청하지 않고 받은 값을 그대로 돌려주는 흉내, 크레딧을 쓰지 않음).
  진짜 실행은 서버를 `--진짜실행`으로 켰을 때만. 진짜 실행 경로는 W07에서 시험하지 않았다.
- API 키(`TRIPO_API_KEY`)는 실행할 때 환경 변수로만 넘기고, 화면·파일·로그에 적지 않는다(적힐 글은 모두 `가리기`를 거친다).
- 실행은 셸을 거치지 않는다: `node <tripo-cli의 cli.js> <인자…> --json`. `.cmd`를 부르지 않는다(인자 끼워 넣기를 막음).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path

서버 = None        # 제작페이지 모듈. 서버가 불러올 때 `묶기`로 넣는다(`python 제작페이지.py`로 켜면 그 모듈 이름이 __main__이라 여기서 import하면 둘이 됨)


class 요청오류(Exception):  # 묶기 전 자리. 묶으면 서버의 요청오류로 바뀐다
    pass


def 묶기(모듈) -> None:
    global 서버, 요청오류, 가짜잔액파일, 진짜잔액파일
    서버 = 모듈
    요청오류 = 모듈.요청오류
    가짜잔액파일 = 모듈.로컬 / "TRIPO잔액_가짜.json"
    진짜잔액파일 = 모듈.로컬 / "TRIPO잔액.json"

유료단계 = {2, 4, 5, 6, 8, 10}      # 결정 칸에 승인 상자가 있는 단계(결정.js 단추표와 같음). 10: TRIPO 동작 생성(W14)
허용명령 = {"generate", "model", "mesh", "anim", "make"}   # tripo 다음 낱말. redo·login·config·topup 등은 받지 않음
막는인자 = {"--no-wait", "-o", "--out", "--yes", "-y"}       # 받을 폴더는 서버가 정함, 끝까지 기다림
최대횟수 = 4
추가막기: dict = {}   # 번호 → 함수(앱, 이름, 승인 파일 값) → 막는 까닭(빈 글이면 안 막음). 단계 화면(W10~)이 붙인다
실행제한초 = 30 * 60
이름꼴 = re.compile(r"승인_[0-9T_-]+\.json")

# 실행 모드(서버가 켤 때 정함). 시험은 이 값을 바꿔 쓴다.
모드 = "가짜"                  # "가짜" / "진짜"
가짜결과 = "성공"              # 가짜 실행이 흉내 낼 결과: 성공 / 실패 / 잔액부족
가짜초 = 2.0                   # 가짜 실행이 걸리는 척하는 시간
가짜잔액파일: Path | None = None   # 묶기에서 정함(시험은 바꿔 씀)
진짜잔액파일: Path | None = None
가짜처음잔액 = 1000

_실행중: set[str] = set()      # 이 서버가 지금 돌리는 승인 파일(경로). 하나만 돌린다(TRIPO 계정이 하나)
_실행잠금 = threading.Lock()

종료코드뜻 = {
    1: "tripo-cli가 예기치 못한 오류로 끝남",
    2: "명령 값이 잘못됨(크레딧은 쓰지 않음)",
    3: "API 키 인증 실패 — 사용자 환경 변수 TRIPO_API_KEY를 확인",
    4: "TRIPO 잔액이 모자람 — 충전한 뒤 다시 생성",
    5: "내용 정책에 걸림",
    6: "TRIPO 작업이 실패함(TRIPO가 크레딧을 돌려준다고 함 — 잔액 전후로 확인)",
    7: "네트워크 오류 — 작업이 이미 제출됐을 수 있음. 다시 실행하지 말고 TRIPO 웹의 작업 기록과 잔액을 먼저 확인",
}


def 값해시(명령: str) -> str:
    return hashlib.sha256(명령.encode("utf-8")).hexdigest()


def 가리기(글) -> str:
    """API 키처럼 보이는 것과 환경 변수의 키 값을 지운다(화면·파일·로그에 적기 전에 늘 거침)."""
    s = str(글 if 글 is not None else "")
    키 = os.environ.get("TRIPO_API_KEY") or ""
    if len(키) >= 6:
        s = s.replace(키, "***")
    return re.sub(r"tsk_[A-Za-z0-9_\-]{6,}", "tsk_***", s)


# ---------------------------------------------------------------- 명령 검사

def 명령나누기(명령) -> list[str]:
    if not isinstance(명령, str) or not 명령.strip():
        raise 요청오류(400, "명령이 비었습니다.")
    if len(명령) > 4000 or "\n" in 명령 or "\r" in 명령 or "\0" in 명령:
        raise 요청오류(400, "명령은 4000자 이하의 한 줄이어야 합니다.")
    try:
        조각 = shlex.split(명령, posix=True)
    except ValueError as e:
        raise 요청오류(400, f"명령을 나누지 못했습니다(따옴표 짝): {e}")
    if len(조각) < 2 or 조각[0] != "tripo":
        raise 요청오류(400, "명령은 'tripo <generate|model|mesh|anim|make> …' 꼴이어야 합니다.")
    if 조각[1] not in 허용명령:
        raise 요청오류(400, f"받지 않는 tripo 명령: {조각[1]} (받는 것: {', '.join(sorted(허용명령))})")
    for t in 조각[2:]:
        if t.split("=", 1)[0] in 막는인자:
            raise 요청오류(400, f"명령에 넣을 수 없는 인자: {t} (받을 폴더·기다리기는 서버가 정함)")
    if 키같음(명령):
        raise 요청오류(400, "명령에 API 키처럼 보이는 글이 있습니다. 키는 환경 변수로만 씁니다.")
    return 조각


def 키같음(글: str) -> bool:
    return 가리기(글) != 글 or "--key" in 글.split()


def 실제인자(a: 서버.앱, 조각: list[str]) -> list[str]:
    """명령의 저장소 기준 파일 경로를 실제 경로로 바꾼다(실행 폴더가 따로라서). 바꾼 값이 '실제값'으로 남는다."""
    나머지 = []
    for t in 조각[1:]:
        f = None if t.startswith("-") or "=" in t else a.저장소파일(t)
        나머지.append(str(f) if f else t)
    if "--json" not in 나머지:
        나머지.append("--json")
    return 나머지


# ---------------------------------------------------------------- 파일

def 요청파일들(a: 서버.앱, 이름, 번호) -> list[Path]:
    d = a.단계폴더(이름, 번호, 만들기=False)
    c = a.캐릭터폴더(이름)
    if not d.is_dir():
        return []
    return sorted(q for q in d.glob("승인_*.json") if 이름꼴.fullmatch(q.name) and a._안전한파일(q, c))


def 요청읽기(a: 서버.앱, 이름, 번호, 파일: str) -> Path:
    if not isinstance(파일, str) or not 이름꼴.fullmatch(파일):
        raise 요청오류(400, f"승인 파일 이름이 잘못됨: {파일!r}")
    q = a.단계폴더(이름, 번호, 만들기=False) / 파일
    if not a._안전한파일(q, a.캐릭터폴더(이름)):
        raise 요청오류(404, f"승인 요청이 없습니다: {파일}")
    return q


def 새이름(d: Path, 앞: str) -> Path:
    시각 = 서버.지금(파일용=True)
    q, k = d / f"{앞}_{시각}.json", 2
    while q.exists():
        q, k = d / f"{앞}_{시각}_{k}.json", k + 1
    return q


def 값검사(무엇, 명령, 크레딧, 횟수) -> None:
    if not isinstance(무엇, str) or not 무엇.strip() or len(무엇) > 200:
        raise 요청오류(400, "'무엇'(예: 오토 리깅)이 비었거나 너무 깁니다.")
    명령나누기(명령)
    if not (크레딧 == "모름" or (isinstance(크레딧, (int, float)) and not isinstance(크레딧, bool) and 크레딧 >= 0)):
        raise 요청오류(400, "'크레딧'은 0 이상의 숫자 또는 \"모름\"이어야 합니다.")
    if not isinstance(횟수, int) or isinstance(횟수, bool) or not 1 <= 횟수 <= 최대횟수:
        raise 요청오류(400, f"'횟수'는 1~{최대횟수}의 정수여야 합니다.")


def 요청만들기(a: 서버.앱, 이름, 번호, 무엇, 명령, 크레딧, 횟수=1, 만든곳="에이전트", 앞요청=None) -> dict:
    """승인 요청(승인 "대기")을 쓴다. 같은 단계에 기다리는 요청이 있으면 그것은 "거절"(새 요청으로 바뀜, 무효)로 바꾼다."""
    if 번호 not in 유료단계:
        raise 요청오류(400, f"{번호}단계에는 승인 상자가 없습니다(유료 단계: {sorted(유료단계)}).")
    값검사(무엇, 명령, 크레딧, 횟수)
    d = a.단계폴더(이름, 번호, 만들기=True)
    바꾼 = []
    for q in 요청파일들(a, 이름, 번호):
        with 서버.파일잠금(q):
            v = 서버.json_읽기(q)
            if v.get("실행") == "실행 중":
                raise 요청오류(409, f"실행 중인 요청이 있어 새 요청을 만들지 않습니다: {q.name}")
            if v.get("승인") == "대기":
                v.update({"승인": "거절", "승인시각": 서버.지금(), "거절까닭": "새 요청으로 바뀜(값이 바뀌어 무효)"})
                서버.json_쓰기(q, v)
                바꾼.append(q.name)
    q = 새이름(d, "승인")
    명령 = 명령.strip()
    값 = {"꼴버전": 서버.꼴버전, "만든시각": 서버.지금(), "작업본해시": a._지금작업본해시(이름), "단계": 번호,
          "무엇": 무엇.strip(), "명령": 명령, "값해시": 값해시(명령), "크레딧": 크레딧, "횟수": 횟수,
          "승인": "대기", "승인시각": "", "실행": "안 함", "결과": {}, "만든곳": 만든곳}
    if 앞요청:
        값["앞요청"] = 앞요청
    with 서버.파일잠금(q):
        서버.json_쓰기(q, 값)
    서버.기록(f"승인 요청: {번호}단계 {q.name} ({무엇}, 크레딧 {크레딧}, {횟수}번, 값해시 {값['값해시'][:12]}){' 무효로 바꿈 ' + ', '.join(바꾼) if 바꾼 else ''}", a, 이름)
    return {"파일": q.relative_to(a.폴더).as_posix(), "값해시": 값["값해시"], "무효로바꾼것": 바꾼}


# ---------------------------------------------------------------- 잔액

def 잔액기록읽기() -> dict:
    p = 가짜잔액파일 if 모드 == "가짜" else 진짜잔액파일
    try:
        v = 서버.json_읽기(p)
        return {"잔액": v.get("잔액"), "시각": v.get("시각"), "가짜": 모드 == "가짜"}
    except Exception:
        if 모드 == "가짜":
            return {"잔액": 가짜처음잔액, "시각": None, "가짜": True}
        return {"잔액": None, "시각": None, "가짜": False}


def 잔액기록쓰기(잔액) -> None:
    p = 가짜잔액파일 if 모드 == "가짜" else 진짜잔액파일
    p.parent.mkdir(parents=True, exist_ok=True)
    with 서버.파일잠금(p):
        서버.json_쓰기(p, {"잔액": 잔액, "시각": 서버.지금(), "가짜": 모드 == "가짜"})


def tripo찾기() -> list[str] | None:
    """[node, cli.js]. 환경 변수 가마우지_TRIPO(cli.js 경로) → 로컬/tripo-cli 설치본. 없으면 None."""
    node = shutil.which("node")
    if not node:
        return None
    후보 = [os.environ.get("가마우지_TRIPO") or "",
            str(서버.로컬 / "tripo-cli" / "node_modules" / "tripo-cli" / "dist" / "cli.js")]
    for c in 후보:
        if c and os.path.isfile(c):
            return [node, c]
    return None


def tripo설치() -> list[str]:
    """`2_TRIPO` "TRIPO 값"의 도구 줄: 보존해 둔 tgz를 이 PC의 로컬 폴더에 설치(전역 설치 안 함). 시험 안 함."""
    tgz = 서버.여기.parent / "00_공통문서" / "조사자료" / "Tripo_3D_공식_2026-11-21" / "tripo-cli-0.11.2.tgz"
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm or not tgz.is_file():
        raise RuntimeError("tripo-cli를 설치할 수 없습니다(npm 또는 보존해 둔 tgz가 없음).")
    곳 = 서버.로컬 / "tripo-cli"
    곳.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([npm, "install", "--no-audit", "--no-fund", "--prefix", str(곳), str(tgz)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    t = tripo찾기()
    if r.returncode != 0 or not t:
        raise RuntimeError(f"tripo-cli 설치 실패: {가리기(r.stderr)[-400:]}")
    return t


def 진짜잔액묻기(t: list[str]) -> float | None:
    try:
        r = subprocess.run(t + ["balance", "--json"], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=60, env=os.environ.copy())
        v = 마지막json(r.stdout)
        b = v.get("balance") if isinstance(v, dict) else None
        return b if isinstance(b, (int, float)) else None
    except Exception:
        return None


def 마지막json(글: str):
    for 줄 in reversed((글 or "").strip().splitlines()):
        줄 = 줄.strip()
        if 줄.startswith("{"):
            try:
                return json.loads(줄)
            except ValueError:
                continue
    return None


# ---------------------------------------------------------------- 보기 (결정 칸)

def 보기(a: 서버.앱, 이름, 번호) -> dict | None:
    """결정 칸의 승인 상자에 그릴 것. 유료 단계가 아니면 None."""
    if 번호 not in 유료단계:
        return None
    잔액 = 잔액기록읽기()
    파일들 = 요청파일들(a, 이름, 번호)
    값 = {"모드": 모드, "잔액": 잔액, "요청": None, "요청수": len(파일들), "막는이유": "", "다시생성막는이유": ""}
    if not 파일들:
        값["막는이유"] = "아직 승인 요청이 없습니다(에이전트가 값을 정해 요청을 만듭니다)"
        값["다시생성막는이유"] = "다시 만들 앞 요청이 없습니다"
        return 값
    q = 파일들[-1]
    try:
        v = 서버.json_읽기(q)
    except Exception as e:
        값["막는이유"] = f"승인 파일을 읽지 못함: {e}"
        return 값
    if v.get("실행") == "실행 중" and str(q) not in _실행중:
        # 서버가 실행 중에 꺼졌다(이 서버는 돌리고 있지 않음). 다시 실행하지 않는다
        with 서버.파일잠금(q):
            v = 서버.json_읽기(q)
            if v.get("실행") == "실행 중" and str(q) not in _실행중:
                v["실행"] = "실패"
                v.setdefault("결과", {})["실패이유"] = "서버가 실행 중에 꺼짐 — TRIPO에서는 돌았을 수 있으니 TRIPO 웹의 작업 기록과 잔액을 먼저 확인"
                서버.json_쓰기(q, v)
    명령 = v.get("명령") if isinstance(v.get("명령"), str) else ""
    해시맞음 = v.get("값해시") == 값해시(명령)
    요청 = {"파일": q.name, "무엇": 가리기(v.get("무엇") or ""), "명령": 가리기(명령), "값해시": v.get("값해시") or "",
            "해시맞음": 해시맞음, "크레딧": v.get("크레딧"), "횟수": v.get("횟수"), "승인": v.get("승인"),
            "승인시각": v.get("승인시각") or "", "실행": v.get("실행"), "결과": v.get("결과") or {},
            "거절까닭": v.get("거절까닭") or "", "만든시각": v.get("만든시각") or "", "가짜": bool((v.get("결과") or {}).get("가짜"))}
    값["요청"] = 요청
    if v.get("승인") != "대기" or v.get("실행") != "안 함":
        값["막는이유"] = {"실행 중": "실행 중입니다", "실행됨": "이미 실행한 요청입니다(같은 승인으로 두 번 실행하지 않음)",
                       "실패": "실패한 요청입니다 — '다시 생성'으로 새 요청을 만드세요"}.get(v.get("실행"), "") \
            or ("무효인 요청입니다(" + (v.get("거절까닭") or "거절") + ")")
    elif not 해시맞음:
        값["막는이유"] = "값해시가 명령과 다릅니다 — 파일의 값이 바뀌어 이 요청은 무효입니다"
    else:
        try:
            명령나누기(명령)
        except 요청오류 as e:
            값["막는이유"] = e.글
    if not 값["막는이유"]:
        모자람 = 잔액모자람(잔액, v.get("크레딧"), v.get("횟수"))
        if 모자람:
            값["막는이유"] = 모자람
    if not 값["막는이유"] and 번호 in 추가막기:
        try:
            값["막는이유"] = 추가막기[번호](a, 이름, v) or ""
        except Exception as e:
            값["막는이유"] = f"단계 검사를 하지 못함: {e}"
    if _실행중:
        값["막는이유"] = 값["막는이유"] or "다른 실행이 끝나기를 기다리는 중입니다"
    if v.get("실행") == "실행 중":
        값["다시생성막는이유"] = "실행 중입니다"
    elif v.get("승인") == "대기" and v.get("실행") == "안 함":
        값["다시생성막는이유"] = "승인을 기다리는 요청이 이미 있습니다"
    return 값


def 잔액모자람(잔액: dict, 크레딧, 횟수) -> str:
    b = 잔액.get("잔액")
    if isinstance(b, (int, float)) and isinstance(크레딧, (int, float)) and isinstance(횟수, int):
        필요 = 크레딧 * 횟수
        if 필요 > b:
            return f"잔액이 모자랍니다(필요 {필요:g}, 잔액 {b:g}) — 충전한 뒤 '다시 생성'"
    return ""


def 바뀜조각(a: 서버.앱, 이름, 번호) -> list[str]:
    return [f"{q.name}:{q.stat().st_mtime_ns}" for q in 요청파일들(a, 이름, 번호)]


# ---------------------------------------------------------------- 승인과 실행

def 승인하기(a: 서버.앱, 이름, 번호, 몸: dict) -> dict:
    """승인 단추(4-5). 페이지가 보인 값(명령·크레딧·횟수)이 파일 값과 같고 값해시가 맞을 때만, 한 번 실행을 시작한다."""
    a._주인확인(몸.get("탭"), 이름)
    if 번호 not in 유료단계:
        raise 요청오류(400, f"{번호}단계에는 승인 상자가 없습니다.")
    q = 요청읽기(a, 이름, 번호, 몸.get("파일"))
    if 요청파일들(a, 이름, 번호)[-1] != q:
        raise 요청오류(409, "가장 최근 요청이 아닙니다. 화면을 다시 읽었습니다 — 새 값을 보고 승인하세요.")
    처리중 = [p.name for p, w in a.묶음들(이름, 번호) if w.get("묶음상태") == "처리 중"]
    if 처리중:
        raise 요청오류(409, f"에이전트가 처리 중이라 실행하지 않습니다: {', '.join(처리중)}")
    with _실행잠금:
        if _실행중:
            raise 요청오류(409, "다른 실행이 아직 끝나지 않았습니다. 끝난 뒤 승인하세요.")
        with 서버.파일잠금(q):
            v = 서버.json_읽기(q)
            명령 = v.get("명령") if isinstance(v.get("명령"), str) else ""
            if v.get("실행") != "안 함" or v.get("승인") != "대기":
                raise 요청오류(409, f"이 요청은 다시 실행하지 않습니다(승인 {v.get('승인')}, 실행 {v.get('실행')}).")
            if v.get("값해시") != 값해시(명령):
                raise 요청오류(409, "값해시가 명령과 다릅니다 — 파일의 값이 바뀌어 이 요청은 무효입니다.")
            보인값 = (몸.get("명령"), 몸.get("크레딧"), 몸.get("횟수"))
            if 보인값 != (가리기(명령), v.get("크레딧"), v.get("횟수")) or 몸.get("값해시") != v.get("값해시"):
                raise 요청오류(409, "화면에 보인 값과 파일의 값이 다릅니다 — 승인하지 않았습니다. 다시 읽은 값을 보고 승인하세요.")
            조각 = 명령나누기(명령)
            모자람 = 잔액모자람(잔액기록읽기(), v.get("크레딧"), v.get("횟수"))
            if 모자람:
                raise 요청오류(409, 모자람)
            막음 = 추가막기[번호](a, 이름, v) if 번호 in 추가막기 else ""
            if 막음:
                raise 요청오류(409, 막음)
            v.update({"승인": "승인", "승인시각": 서버.지금(), "실행": "실행 중", "실행모드": 모드})
            서버.json_쓰기(q, v)
            _실행중.add(str(q))
    try:
        a.단계상태쓰기(이름, 번호, {"상태": "진행 중"})
    except Exception:
        pass
    서버.기록(f"승인: {번호}단계 {q.name} 값해시 {v['값해시'][:12]} → 실행 시작({모드})", a, 이름)
    threading.Thread(target=_실행, args=(a, 이름, 번호, q, 조각, v), daemon=True).start()
    return {"됨": True, "파일": q.name, "실행": "실행 중", "모드": 모드}


def 다시생성(a: 서버.앱, 이름, 번호, 몸: dict) -> dict:
    """같은 값으로 새 승인 요청(4-4). 바로 실행하지 않는다."""
    a._주인확인(몸.get("탭"), 이름)
    파일들 = 요청파일들(a, 이름, 번호) if 번호 in 유료단계 else []
    if not 파일들:
        raise 요청오류(409, "다시 만들 앞 요청이 없습니다.")
    v = 서버.json_읽기(파일들[-1])
    if v.get("실행") == "실행 중":
        raise 요청오류(409, "실행 중입니다.")
    if v.get("승인") == "대기" and v.get("실행") == "안 함":
        raise 요청오류(409, "승인을 기다리는 요청이 이미 있습니다.")
    return dict(요청만들기(a, 이름, 번호, v.get("무엇"), v.get("명령"), v.get("크레딧"), v.get("횟수"),
                         만든곳="다시 생성", 앞요청=파일들[-1].name), 됨=True)


def _실행(a: 서버.앱, 이름, 번호, q: Path, 조각: list[str], 요청: dict) -> None:
    시작 = time.monotonic()
    받을곳 = a.단계폴더(이름, 번호, 만들기=True) / "받은것" / q.stem.replace("승인_", "")
    결과 = {"가짜": 모드 == "가짜", "작업번호": [], "실제값": "", "쓴크레딧": None, "잔액전": None, "잔액후": None,
            "받은파일": [], "실패이유": "", "종료코드": None}
    로그 = []
    try:
        받을곳.mkdir(parents=True, exist_ok=True)
        인자 = 실제인자(a, 조각)
        결과["실제값"] = 가리기("tripo " + " ".join(shlex.quote(t) for t in 인자))
        if 모드 == "가짜":
            결과 = _가짜실행(받을곳, 요청, 인자, 결과, 로그)
        else:
            결과 = _진짜실행(받을곳, 요청, 인자, 결과, 로그)
    except Exception as e:
        결과["실패이유"] = 결과["실패이유"] or f"서버 오류: {e!r}"
    결과["걸린초"] = round(time.monotonic() - 시작, 1)
    결과["받은파일"] = [p.relative_to(a.폴더).as_posix() for p in sorted(받을곳.rglob("*")) if p.is_file() and p.name != "tripo_로그.txt"] if 받을곳.is_dir() else []
    try:
        (받을곳 / "tripo_로그.txt").write_text(가리기("\n".join(로그)), encoding="utf-8")
    except OSError:
        pass
    결과 = json.loads(가리기(json.dumps(결과, ensure_ascii=False)))
    성공 = not 결과["실패이유"]
    with 서버.파일잠금(q):
        v = 서버.json_읽기(q)
        v["실행"] = "실행됨" if 성공 else "실패"
        v["결과"] = 결과
        v["실행끝시각"] = 서버.지금()
        서버.json_쓰기(q, v)
    with _실행잠금:
        _실행중.discard(str(q))
    가짜 = "(가짜 실행) " if 결과["가짜"] else ""
    잔액글 = f"잔액 {결과['잔액전']} → {결과['잔액후']}"
    try:
        if 성공:
            작업 = ", ".join(결과["작업번호"]) or "모름"
            a.단계상태쓰기(이름, 번호, {"상태": "결정 대기", "출처": f"이 페이지 (작업 {작업})"})
            a.알림쓰기(이름, 번호, f"{가짜}{요청.get('무엇')} 실행 끝: 작업 {작업}, 쓴 크레딧 {결과['쓴크레딧']}, {잔액글}. "
                              f"받은 파일 {len(결과['받은파일'])}개(`{받을곳.relative_to(a.폴더).as_posix()}`). 에이전트가 받은 파일을 확인합니다.", "안내")
        else:
            a.단계상태쓰기(이름, 번호, {"상태": "막힘"})
            a.알림쓰기(이름, 번호, f"{가짜}{요청.get('무엇')} 실행 실패: {결과['실패이유']}. {잔액글}(크레딧이 빠졌는지 확인).", "막힘")
    except Exception as e:
        서버.기록(f"실행 뒤 상태·알림을 쓰지 못함: {e!r}", a, 이름)
    서버.기록(f"실행 {'됨' if 성공 else '실패'}: {번호}단계 {q.name} 작업 {결과['작업번호']} 크레딧 {결과['쓴크레딧']} "
             f"{잔액글} {결과['실패이유']}".rstrip(), a, 이름)


def _가짜실행(받을곳: Path, 요청: dict, 인자: list[str], 결과: dict, 로그: list[str]) -> dict:
    """TRIPO에 요청하지 않는다. 받은 값을 그대로 적은 파일 하나를 '받은 파일'로 남긴다."""
    잔액전 = 잔액기록읽기()["잔액"]
    잔액기록쓰기(잔액전)
    결과["잔액전"] = 잔액전
    로그.append(f"가짜 실행: {' '.join(인자)}")
    time.sleep(가짜초)
    크레딧 = 요청.get("크레딧")
    쓸것 = (크레딧 if isinstance(크레딧, (int, float)) else 0) * (요청.get("횟수") or 1)
    if 가짜결과 == "잔액부족":
        결과.update(종료코드=4, 실패이유=종료코드뜻[4], 쓴크레딧=0, 잔액후=잔액전)
    elif 가짜결과 == "실패":
        결과.update(종료코드=6, 실패이유=종료코드뜻[6], 쓴크레딧=0, 잔액후=잔액전)
    else:
        for i in range(요청.get("횟수") or 1):
            결과["작업번호"].append(f"가짜-{uuid.uuid4().hex[:8]}")
        (받을곳 / "가짜_받은값.json").write_text(json.dumps(
            {"가짜": True, "받은명령": 요청.get("명령"), "실제인자": 인자, "작업번호": 결과["작업번호"]},
            ensure_ascii=False, indent=1), encoding="utf-8")
        결과.update(종료코드=0, 쓴크레딧=쓸것, 잔액후=잔액전 - 쓸것 if isinstance(잔액전, (int, float)) else None)
    if 결과["잔액후"] is not None:
        잔액기록쓰기(결과["잔액후"])
    로그.append(f"가짜 결과: {가짜결과}, 종료 코드 {결과['종료코드']}")
    return 결과


def _진짜실행(받을곳: Path, 요청: dict, 인자: list[str], 결과: dict, 로그: list[str]) -> dict:
    """tripo-cli를 셸 없이 부른다. W07에서는 시험하지 않았다(크레딧을 씀)."""
    if not os.environ.get("TRIPO_API_KEY"):  # 설치(npm)보다 먼저 본다
        결과["실패이유"] = "사용자 환경 변수 TRIPO_API_KEY가 없습니다(크레딧은 쓰지 않음)."
        return 결과
    t = tripo찾기() or tripo설치()
    잔액전 = 진짜잔액묻기(t)
    결과["잔액전"] = 잔액전
    if 잔액전 is not None:
        잔액기록쓰기(잔액전)
    쓴 = 0.0
    쓴앎 = True
    for i in range(요청.get("횟수") or 1):
        try:
            r = subprocess.run(t + 인자, cwd=받을곳, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=실행제한초, env=os.environ.copy())
        except subprocess.TimeoutExpired:
            결과["실패이유"] = f"{실행제한초 // 60}분 안에 끝나지 않음 — TRIPO에서는 아직 돌 수 있음. 다시 실행하지 말고 작업 기록 확인"
            break
        로그.append(f"[{i + 1}번째] 종료 코드 {r.returncode}\n--- stdout\n{r.stdout}\n--- stderr\n{r.stderr}")
        결과["종료코드"] = r.returncode
        v = 마지막json(r.stdout) or {}
        if v.get("task_id"):
            결과["작업번호"].append(str(v["task_id"]))
        c = v.get("credits_consumed")
        if isinstance(c, (int, float)):
            쓴 += c
        else:
            쓴앎 = False
        if r.returncode != 0:
            결과["실패이유"] = 종료코드뜻.get(r.returncode, f"종료 코드 {r.returncode}") + (f" — {v.get('error') or v.get('message')}" if isinstance(v, dict) and (v.get("error") or v.get("message")) else "")
            break
    잔액후 = 진짜잔액묻기(t)
    결과["잔액후"] = 잔액후
    if 잔액후 is not None:
        잔액기록쓰기(잔액후)
    if 쓴앎:
        결과["쓴크레딧"] = 쓴
    elif isinstance(잔액전, (int, float)) and isinstance(잔액후, (int, float)):
        결과["쓴크레딧"] = 잔액전 - 잔액후
    return 결과
