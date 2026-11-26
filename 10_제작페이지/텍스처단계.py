"""7단계 텍스처 수정 화면의 서버 쪽 (작업 묶음 W12, 기능명세 2부 19절, SSOT 단계/5_텍스처 5-5~5-7)

- 에이전트 차례: 먼저 5-5(여백 채우기)·5-6(그림 정리 공통 공정)을 돌리고, (자동 검사기 후보 — 기능명세 28절대로
  검사기 시험 결과를 본 뒤에 붙임, 지금은 비어 있음) 누가 봐도 흠인 것은 묻지 않고 고친다. 끝나기 전 독립 검수(5-7).
- 에이전트가 쓰는 것(`에이전트.py`):
  `텍스처진행 <파일.json>` → `07_텍스처수정/진행.json`(순서 체크).
  `텍스처검수 <파일.json>` → `독립검수.json`에 회차 한 줄. 지적이 있으면 후보로 같은 목록에 넣는다
  (판단하지 않은 앞 후보·고친 것을 이어 담은 새 `후보_<시각>.json`, 지적은 누가 "독립 검수").
- 페이지가 쓰는 것: 사용자가 "독립 검수 받지 않음"을 적을 때 `독립검수.json`에 회차 한 줄(누가 "사용자").
- 끝나는 조건(2부 19절): 처리 안 된 묶음 없음, 독립 검수를 받았거나 "받지 않음"이 기록됨, 사용자 "이 단계 끝".
"""

from __future__ import annotations

from pathlib import Path

서버 = None


class 요청오류(Exception):  # 묶기 전 자리
    pass


def 묶기(모듈) -> None:
    global 서버, 요청오류
    서버 = 모듈
    요청오류 = 모듈.요청오류


번호 = 7
# SSOT 단계/5_텍스처의 정리 차례(5-5, 5-6)와 2부 19절 "누가". 독립 검수(5-7)는 독립검수.json으로 본다
순서 = ["여백 채우기(5-5, 조각지도 → 여백채우기)", "그림 정리 공통 공정(5-6, 단색화·얼룩·옷선·얼굴·대칭 무늬)",
       "누가 봐도 흠인 것을 묻지 않고 고침(고친 것 ✓)"]
검수상태들 = ("받음", "받지 않음")
누가들 = ("에이전트", "사용자")


def 폴더(a, 이름, 만들기=False) -> Path:
    return a.단계폴더(이름, 번호, 만들기=만들기)


def 읽기(p: Path) -> dict | None:
    if not p.is_file():
        return None
    try:
        v = 서버.json_읽기(p)
        return v if isinstance(v, dict) else None
    except Exception:
        return None


def 진행읽기(a, 이름) -> dict:
    try:
        v = 읽기(폴더(a, 이름) / "진행.json") or {}
    except Exception:
        v = {}
    줄 = v.get("순서") if isinstance(v.get("순서"), dict) else {}
    return {str(i): 줄.get(str(i)) for i in range(1, len(순서) + 1) if isinstance(줄.get(str(i)), dict)}


def 검수읽기(a, 이름) -> list[dict]:
    try:
        v = 읽기(폴더(a, 이름) / "독립검수.json") or {}
    except Exception:
        v = {}
    return [x for x in v.get("회차") or [] if isinstance(x, dict) and x.get("상태") in 검수상태들]


def 상대(a, p: Path) -> str:
    return p.resolve().relative_to(a.폴더.resolve()).as_posix()


def 최근후보(a, 이름) -> tuple[Path, dict] | None:
    try:
        목록 = sorted(폴더(a, 이름).glob("후보_*.json"))
    except Exception:
        return None
    for q in reversed(목록):
        v = 읽기(q)
        if v is not None:
            return q, v
    return None


def 보낸판단(a, 이름) -> set[tuple[str, str]]:
    s = set()
    for _, v in a.묶음들(이름, 번호):
        for x in v.get("후보판단") or []:
            if isinstance(x, dict):
                s.add((str(x.get("후보파일")), str(x.get("번호"))))
    return s


def 글자번호(n: int) -> str:
    """0 → A, 25 → Z, 26 → AA (W11과 같음)."""
    s = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


# ---------------------------------------------------------------- 에이전트 쪽

def 진행쓰기(a, 이름, v: dict) -> dict:
    """{끝: [순서 번호...], 글: {번호: 짧은 글}}. 끝으로 적은 것은 지우지 않는다."""
    끝 = v.get("끝")
    if not isinstance(끝, list) or not 끝 or not all(isinstance(i, int) and not isinstance(i, bool) and 1 <= i <= len(순서) for i in 끝):
        raise 요청오류(400, f"'끝'은 1~{len(순서)}의 순서 번호 목록이어야 합니다.")
    글들 = v.get("글") or {}
    if not isinstance(글들, dict) or not all(isinstance(x, str) for x in 글들.values()):
        raise 요청오류(400, "'글'은 {순서 번호: 짧은 글} 꼴이어야 합니다.")
    p = 폴더(a, 이름, 만들기=True) / "진행.json"
    with 서버.파일잠금(p):
        전 = 읽기(p) or {}
        줄 = 전.get("순서") if isinstance(전.get("순서"), dict) else {}
        for i in 끝:
            줄[str(i)] = {"끝": True, "시각": 서버.지금(), "글": str(글들.get(str(i), ""))[:200]}
        서버.json_쓰기(p, {"꼴버전": 서버.꼴버전, "만든시각": 서버.지금(), "작업본해시": a._지금작업본해시(이름), "순서": 줄})
    서버.기록(f"텍스처 진행: 순서 {sorted(끝)} 끝", a, 이름)
    return {"결과": "씀", "파일": 상대(a, p), "끝난순서": sorted(int(k) for k in 줄)}


def 회차쓰기(a, 이름, 줄: dict) -> dict:
    p = 폴더(a, 이름, 만들기=True) / "독립검수.json"
    with 서버.파일잠금(p):
        전 = 읽기(p) or {}
        회차 = [x for x in 전.get("회차") or [] if isinstance(x, dict)]
        줄 = {"차": len(회차) + 1, "시각": 서버.지금(), "작업본해시": a._지금작업본해시(이름), **줄}
        회차.append(줄)
        서버.json_쓰기(p, {"꼴버전": 서버.꼴버전, "회차": 회차})
    서버.기록(f"텍스처 독립 검수 {줄['차']}차: {줄['상태']} ({줄.get('누가')})", a, 이름)
    return 줄


def 검수값검사(a, 이름, v: dict) -> dict:
    """텍스처검수 파일: {상태: 받음|받지 않음, 검수자, 보고, 이유, 넓은그림: [...], 지적: [표시 항목...]}.
    지적은 후보로 넣을 표시 항목(누가는 비워도 "독립 검수"로 채움). 번호는 비우면 앞 후보 다음 글자로."""
    상태 = v.get("상태")
    if 상태 not in 검수상태들:
        raise 요청오류(400, f"'상태'는 {' / '.join(검수상태들)}.")
    for k in ("검수자", "보고", "이유"):
        if v.get(k) is not None and not isinstance(v.get(k), str):
            raise 요청오류(400, f"'{k}'는 글이어야 합니다.")
    if 상태 == "받지 않음" and not str(v.get("이유") or "").strip():
        raise 요청오류(400, "받지 않음이면 '이유'를 적어 주세요(예: Codex 사용량 한도).")
    if 상태 == "받음" and v.get("보고") and a.저장소파일(v["보고"]) is None:
        raise 요청오류(400, f"저장소 안에 없는 보고 파일: {v['보고']}")
    넓은 = v.get("넓은그림") or []
    if not isinstance(넓은, list) or not all(isinstance(g, str) and a.저장소파일(g) is not None for g in 넓은):
        raise 요청오류(400, "'넓은그림'은 저장소 안의 그림 경로 목록이어야 합니다.")
    지적 = v.get("지적") or []
    if not isinstance(지적, list) or (지적 and 상태 != "받음"):
        raise 요청오류(400, "'지적'은 목록이고, 상태가 '받음'일 때만 씁니다.")
    return {"상태": 상태, "누가": "에이전트", "검수자": str(v.get("검수자") or "Codex Astra"), "보고": v.get("보고") or "",
            "이유": str(v.get("이유") or ""), "넓은그림": 넓은, "지적": 지적}


def 지적후보(a, 이름, 지적: list[dict]) -> dict:
    """지적을 후보로: 판단하지 않은 앞 후보와 고친 것을 이어 담고, 지적에 다음 글자 번호를 붙인다."""
    m = 최근후보(a, 이름)
    이어 = []
    고친것 = []
    if m:
        q, v = m
        보낸 = 보낸판단(a, 이름)
        이어 = [x for x in v.get("후보") or [] if isinstance(x, dict) and (q.name, str(x.get("번호"))) not in 보낸]
        고친것 = [x for x in v.get("고친것") or [] if isinstance(x, dict)]
    쓴 = {str(x.get("번호")) for x in 이어 + 고친것}
    k = 0
    새 = []
    for x in 지적:
        if not isinstance(x, dict):
            raise 요청오류(400, "지적 한 줄이 객체가 아닙니다.")
        x = dict(x)
        x.setdefault("누가", "독립 검수")
        x.setdefault("종류", "이상함")
        x.setdefault("반대쪽도", False)
        if not x.get("번호"):
            while 글자번호(k) in 쓴:
                k += 1
            x["번호"] = 글자번호(k)
        쓴.add(x["번호"])
        새.append(x)
    return {"만든이": "독립 검수", "후보": 이어 + 새, "고친것": 고친것}


def 검수뒤(a, 이름, 줄: dict, 후보수: int) -> None:
    if 줄["상태"] == "받지 않음":
        return
    글 = f"독립 검수 {줄['차']}차를 받음({줄['검수자']}): 지적 {줄['지적수']}개를 후보로 넣었습니다." if 줄["지적수"] else \
        f"독립 검수 {줄['차']}차를 받음({줄['검수자']}): 지적 없음."
    if 줄["넓은그림"]:
        글 += " 넓게 본 그림을 옆 기둥에 두었습니다. 멈출 곳은 사용자가 정합니다."
    a.알림쓰기(이름, 번호, 글, "결정 필요" if 후보수 else "안내")


# ---------------------------------------------------------------- 페이지 쪽

def 안받음쓰기(a, 이름, 몸: dict) -> dict:
    """사용자가 '독립 검수 받지 않음'을 적는다(2부 19절 끝나는 조건)."""
    a._주인확인(몸.get("탭"), 이름)
    이유 = str(몸.get("이유") or "").strip()[:200] or "사용자가 받지 않기로 함"
    줄 = 회차쓰기(a, 이름, {"상태": "받지 않음", "누가": "사용자", "검수자": "", "보고": "", "이유": 이유, "넓은그림": [], "지적수": 0})
    return {"됨": True, "회차": 줄}


# ---------------------------------------------------------------- 끝나는 조건과 화면

def 완료모자람(a, 이름) -> list[str]:
    모자람 = []
    if not 검수읽기(a, 이름):
        모자람.append("독립 검수를 받지 않았고 '받지 않음'도 적지 않음")
    안된 = [q.name for q, v in a.묶음들(이름, 번호) if v.get("묶음상태") in ("보냄", "처리 중")]
    if 안된:
        모자람.append(f"처리 안 된 묶음 {len(안된)}개")
    return 모자람


def 보기(a, 이름) -> dict:
    """옆 기둥에 그릴 것."""
    진행 = 진행읽기(a, 이름)
    회차 = 검수읽기(a, 이름)
    m = 최근후보(a, 이름)
    후보 = None
    if m:
        q, v = m
        보낸 = 보낸판단(a, 이름)
        목록 = [x for x in v.get("후보") or [] if isinstance(x, dict)]
        누가: dict[str, int] = {}
        for x in 목록:
            k = str(x.get("누가") or v.get("만든이") or "에이전트")
            누가[k] = 누가.get(k, 0) + 1
        후보 = {"파일": q.name, "수": len(목록), "누가": 누가, "고친것수": len(v.get("고친것") or []),
              "안판단": sum(1 for x in 목록 if (q.name, str(x.get("번호"))) not in 보낸)}
    return {"단계": 번호,
            "순서": [{"번호": i + 1, "글": t, "끝": str(i + 1) in 진행, "메모": (진행.get(str(i + 1)) or {}).get("글", "")}
                   for i, t in enumerate(순서)],
            "검수": 회차[-1] if 회차 else None, "검수회차": len(회차), "후보": 후보,
            "자동검사기": None,   # 기능명세 28절: 검사기 시험 결과를 본 뒤에 붙인다
            "모자람": 완료모자람(a, 이름)}


def 바뀜(a, 이름) -> str:
    try:
        d = 폴더(a, 이름)
    except Exception:
        return ""
    조각 = []
    for p in [d / "진행.json", d / "독립검수.json"] + list(d.glob("후보_*.json")) + list(d.glob("보내기_*.json")):
        try:
            조각.append(f"{p.name}:{p.stat().st_mtime_ns}")
        except OSError:
            pass
    return "|".join(sorted(조각))
