"""3단계 메시 정리 화면의 서버 쪽 (작업 묶음 W11, 기능명세 2부 15절, 1부 3-1b)

3단계는 **두 번만 멈춘다**: 멈춤 1 계획 확인(순서 1~5 뒤), 멈춤 2 결과 확인(순서 6~10 뒤). 순서는 SSOT `단계/3_메시`.

- 에이전트가 쓰는 것(`에이전트.py`):
  `메시진행 <파일.json>` → `03_메시정리/진행.json`(순서 체크). 계획을 정하기 전에는 6~10을 끝으로 적지 못한다.
  `메시멈춤 <파일.json>` → `후보_<시각>.json`에 `멈춤`·`계획`(멈춤 1) 또는 `결과`(멈춤 2)를 더해 쓴다.
  `SSOT/도구/메시검사.py`의 `검사결과.json`에서 고른 조각·후보 번호를 주면 표시 항목(파츠·면 번호·근거 그림)으로 바꾼다.
- 페이지가 쓰는 것: 멈춤 1의 후보를 판단해 보낼 때 대칭 답(`멈춤답`)을 함께 보낸다. 서버가 보내기 파일에 넣고
  `03_메시정리/계획확정.json`을 쓴다. 한 번 정한 계획은 바꾸지 않는다(2부 15절 "뒤에서 바꾸지 않는다").
- 끝나는 조건: `단계완료검사[3]`(순서 1~10, 계획 확정, 결과 확인 판단을 보냄, 접합부별 판정, 여러 방향 그림, 처리 안 된 묶음 없음).
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


번호 = 3
# SSOT 단계/3_메시 "순서와 합격 기준"(초안)의 열 가지. 멈춤 1은 5 뒤, 멈춤 2는 10 뒤
순서 = ["가져오기와 구성 조사", "처음 정리: 노이즈 조각 후보(표시만)", "파츠 분리(헤어 / 얼굴 / 상체 / 하체)",
       "대칭으로 만들 조각·비대칭으로 둘 조각 정하기", "파츠별 대칭 중심 재기",
       "좌우 절반을 비교해 기준 쪽대로 대칭", "대칭으로 만들고 이음선 점검", "중심 정렬과 통합",
       "남은 결함 정리: 접합부 검사·흠 후보", "음영 손보기(노멀, 이상한 곳만)"]
멈춤들 = ("계획 확인", "결과 확인")
기준쪽들 = ("+x", "-x")          # 화면을 보는 사람 기준 오른쪽 = +x (메모리 "좌우는 바라보는 기준")
대칭답들 = ("에이전트 쪽", "반대쪽", "대칭 안 함")
판정들 = ("통과", "보완 필요", "사람 확인")


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


def 확정읽기(a, 이름) -> dict | None:
    try:
        return 읽기(폴더(a, 이름) / "계획확정.json")
    except Exception:
        return None


def 멈춤후보(a, 이름) -> tuple[Path, dict] | None:
    """가장 최근 후보 파일(페이지가 보이는 것과 같음)이 멈춤 후보이면 그것."""
    try:
        목록 = sorted(폴더(a, 이름).glob("후보_*.json"))
    except Exception:
        return None
    if not 목록:
        return None
    v = 읽기(목록[-1])
    return (목록[-1], v) if v and v.get("멈춤") in 멈춤들 else None


def 멈춤후보들(a, 이름, 멈춤) -> list[tuple[Path, dict]]:
    try:
        목록 = sorted(폴더(a, 이름).glob("후보_*.json"))
    except Exception:
        return []
    return [(q, v) for q in 목록 if (v := 읽기(q)) and v.get("멈춤") == 멈춤]


def 보낸판단(a, 이름) -> set[tuple[str, str]]:
    """보낸 묶음에 든 (후보파일, 번호)."""
    s = set()
    for _, v in a.묶음들(이름, 번호):
        for x in v.get("후보판단") or []:
            if isinstance(x, dict):
                s.add((str(x.get("후보파일")), str(x.get("번호"))))
    return s


def 상대(a, p: Path) -> str:
    return p.resolve().relative_to(a.폴더.resolve()).as_posix()


# ---------------------------------------------------------------- 에이전트 쪽

def 진행쓰기(a, 이름, v: dict) -> dict:
    """{끝: [순서 번호...], 글: {번호: 짧은 글}}. 끝으로 적은 것은 지우지 않는다(되돌리기는 작업본 사본으로)."""
    끝 = v.get("끝")
    if not isinstance(끝, list) or not 끝 or not all(isinstance(i, int) and not isinstance(i, bool) and 1 <= i <= len(순서) for i in 끝):
        raise 요청오류(400, f"'끝'은 1~{len(순서)}의 순서 번호 목록이어야 합니다.")
    글들 = v.get("글") or {}
    if not isinstance(글들, dict) or not all(isinstance(x, str) for x in 글들.values()):
        raise 요청오류(400, "'글'은 {순서 번호: 짧은 글} 꼴이어야 합니다.")
    if any(i >= 6 for i in 끝) and not 확정읽기(a, 이름):
        raise 요청오류(409, "멈춤 1(계획 확인)에서 사용자가 계획을 정하기 전에는 6~10을 끝으로 적지 못합니다(2부 15절).")
    p = 폴더(a, 이름, 만들기=True) / "진행.json"
    with 서버.파일잠금(p):
        전 = 읽기(p) or {}
        줄 = 전.get("순서") if isinstance(전.get("순서"), dict) else {}
        for i in 끝:
            줄[str(i)] = {"끝": True, "시각": 서버.지금(), "글": str(글들.get(str(i), ""))[:200]}
        서버.json_쓰기(p, {"꼴버전": 서버.꼴버전, "만든시각": 서버.지금(), "작업본해시": a._지금작업본해시(이름), "순서": 줄})
    서버.기록(f"메시 진행: 순서 {sorted(끝)} 끝", a, 이름)
    return {"결과": "씀", "파일": 상대(a, p), "끝난순서": sorted(int(k) for k in 줄)}


def 검사결과후보(a, 경로: str, 고른: list[str], 시작번호: int) -> list[dict]:
    """메시검사.py의 검사결과.json에서 고른 조각·후보 번호를 표시 항목으로 바꾼다(번호 A, B, …)."""
    p = a.저장소파일(경로)
    if p is None:
        raise 요청오류(400, f"검사결과 파일이 저장소 안에 없습니다: {경로}")
    try:
        r = 서버.json_읽기(p)
    except Exception as e:
        raise 요청오류(400, f"검사결과를 읽지 못했습니다: {e}")
    전부 = {}
    for 파츠, R in (r.get("파츠") or {}).items():
        for q in R.get("조각") or []:
            전부[str(q.get("번호"))] = (파츠, "조각", q)
        for c in R.get("후보") or []:
            전부[str(c.get("번호"))] = (파츠, c.get("kind", "후보"), c)
    없음 = [x for x in 고른 if x not in 전부]
    if 없음:
        raise 요청오류(400, f"검사결과에 없는 번호: {', '.join(없음[:5])}")
    목록 = []
    for k, 이름 in enumerate(고른):
        파츠, 종류, q = 전부[이름]
        면 = q.get("면번호")
        if not isinstance(면, list) or not 면:
            raise 요청오류(400, f"{이름}: 검사결과에 '면번호'(전부)가 없습니다. 고친 SSOT/도구/메시검사.py로 다시 돌려 주세요.")
        그림 = []
        if q.get("그림"):
            g = (p.parent / q["그림"]).resolve()
            if g.is_file():
                그림.append(상대(a, g))
        면수 = q.get("면", q.get("faces"))
        글 = f"{이름} · {종류} · 면 {면수}" + (f" · 크기 {q['크기_mm']} mm" if q.get("크기_mm") is not None else "") + \
            (f" · 보이는 면 {q['보이는면_비율']}" if q.get("보이는면_비율") is not None else "")
        목록.append({"번호": 글자번호(시작번호 + k), "누가": "에이전트", "종류": "후보", "판단": "",
                   "자리": {"파츠": [파츠], "면": {파츠: [int(i) for i in 면]}}, "반대쪽도": False,
                   "메모": 글, "근거그림": 그림, "검사번호": 이름})
    return 목록


def 글자번호(n: int) -> str:
    """0 → A, 25 → Z, 26 → AA."""
    s = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def 멈춤값검사(a, 이름, v: dict) -> dict:
    """메시멈춤 파일의 `멈춤`·`계획`/`결과`를 검사하고, 후보 파일에 더할 값을 돌려준다."""
    멈춤 = v.get("멈춤")
    if 멈춤 not in 멈춤들:
        raise 요청오류(400, f"'멈춤'은 {' / '.join(멈춤들)}.")
    진행 = 진행읽기(a, 이름)
    if 멈춤 == "계획 확인":
        if 확정읽기(a, 이름):
            raise 요청오류(409, "계획은 이미 정해졌습니다(계획확정.json). 정한 대칭 기준은 바꾸지 않습니다.")
        모자 = [i for i in range(1, 6) if str(i) not in 진행]
        if 모자:
            raise 요청오류(409, f"멈춤 1 전에 순서 {모자}를 끝으로 적어 주세요(메시진행).")
        계획 = v.get("계획")
        if not isinstance(계획, dict) or not isinstance(계획.get("파츠"), list) or not 계획["파츠"] or not isinstance(계획.get("대칭"), list):
            raise 요청오류(400, "'계획'은 {파츠: [{이름, 면}...], 대칭: [{파츠, 대칭, 기준쪽, 이유, 그림}...]} 꼴이어야 합니다.")
        for x in 계획["파츠"]:
            if not isinstance(x, dict) or not isinstance(x.get("이름"), str) or not isinstance(x.get("면"), int):
                raise 요청오류(400, f"파츠 한 줄이 {{이름, 면}} 꼴이 아님: {x!r}"[:200])
        본 = set()
        for x in 계획["대칭"]:
            if not isinstance(x, dict) or not isinstance(x.get("파츠"), str) or not isinstance(x.get("대칭"), bool):
                raise 요청오류(400, f"대칭 한 줄이 {{파츠, 대칭(참/거짓), 기준쪽, 이유, 그림}} 꼴이 아님: {x!r}"[:200])
            if x["파츠"] in 본:
                raise 요청오류(400, f"대칭 줄의 파츠가 겹칩니다: {x['파츠']}")
            본.add(x["파츠"])
            if x["대칭"] and x.get("기준쪽") not in 기준쪽들:
                raise 요청오류(400, f"{x['파츠']}: 대칭으로 만들면 '기준쪽'은 +x(화면 오른쪽) / -x.")
            if x["대칭"] and not x.get("그림"):
                raise 요청오류(400, f"{x['파츠']}: 좌우 절반을 나란히 놓은 그림이 있어야 합니다('그림').")
            for g in x.get("그림") or []:
                if not isinstance(g, str) or a.저장소파일(g) is None:
                    raise 요청오류(400, f"{x['파츠']}: 저장소 안에 없는 그림: {g}")
        return {"멈춤": 멈춤, "계획": 계획}
    if not 확정읽기(a, 이름):
        raise 요청오류(409, "멈춤 1(계획 확인)을 사용자가 아직 정하지 않았습니다.")
    모자 = [i for i in range(1, len(순서) + 1) if str(i) not in 진행]
    if 모자:
        raise 요청오류(409, f"멈춤 2 전에 순서 {모자}를 끝으로 적어 주세요(메시진행).")
    결과 = v.get("결과")
    if not isinstance(결과, dict) or not isinstance(결과.get("접합부판정"), list) or not isinstance(결과.get("다각도그림"), list):
        raise 요청오류(400, "'결과'는 {접합부판정: [{접합부, 판정, 근거}...], 다각도그림: [경로...]} 꼴이어야 합니다.")
    for x in 결과["접합부판정"]:
        if not isinstance(x, dict) or not isinstance(x.get("접합부"), str) or x.get("판정") not in 판정들:
            raise 요청오류(400, f"접합부 판정 한 줄이 {{접합부, 판정({'/'.join(판정들)}), 근거}} 꼴이 아님: {x!r}"[:200])
    for g in 결과["다각도그림"]:
        if not isinstance(g, str) or a.저장소파일(g) is None:
            raise 요청오류(400, f"저장소 안에 없는 다각도 그림: {g}")
    return {"멈춤": 멈춤, "결과": 결과}


def 멈춤뒤(a, 이름, 멈춤, 파일: str, 후보수: int, 고친수: int) -> None:
    if 멈춤 == "계획 확인":
        글 = f"멈춤 1 · 계획 확인: 지울 조각 후보 {후보수}개와 대칭 기준을 정해 주세요. 옆 기둥에서 대칭을 고르고 '계획 정하고 보내기'."
    else:
        글 = f"멈춤 2 · 결과 확인: 남은 흠 후보 {후보수}개, 묻지 않고 고친 것 {고친수}개. 판단해 보내거나 '이 단계 끝'."
    a.알림쓰기(이름, 번호, 글, "결정 필요")


# ---------------------------------------------------------------- 페이지 쪽(보내기에 붙는 대칭 답)

def 멈춤답검사(a, 이름, 몸: dict, 판단: list[dict]) -> dict | None:
    """보내기 몸의 `멈춤답`을 검사한다. 멈춤 1 후보를 판단해 보내면 대칭 답이 꼭 있어야 한다(한 번에 정함)."""
    m = 멈춤후보(a, 이름)
    답 = 몸.get("멈춤답")
    계획판단 = m and m[1].get("멈춤") == "계획 확인" and any(x.get("후보파일") == m[0].name for x in 판단)
    if 답 is None:
        if 계획판단 and not 확정읽기(a, 이름):
            raise 요청오류(400, "멈춤 1 후보를 보낼 때는 대칭 기준도 함께 정해야 합니다(옆 기둥 '계획 정하고 보내기').")
        return None
    if not m or not isinstance(답, dict) or 답.get("후보파일") != m[0].name or 답.get("멈춤") != m[1].get("멈춤"):
        raise 요청오류(409, "멈춤 답이 지금 멈춤 후보와 맞지 않습니다. 화면을 다시 읽습니다.")
    if m[1]["멈춤"] == "결과 확인":
        return {"멈춤": "결과 확인", "후보파일": m[0].name}
    if 확정읽기(a, 이름):
        raise 요청오류(409, "계획은 이미 정해졌습니다. 정한 대칭 기준은 바꾸지 않습니다.")
    대칭 = 답.get("대칭")
    줄들 = {x["파츠"]: x for x in m[1]["계획"]["대칭"]}
    if not isinstance(대칭, list) or {str(x.get("파츠")) for x in 대칭 if isinstance(x, dict)} != set(줄들):
        raise 요청오류(400, "대칭 답은 계획의 대칭 줄마다 하나씩 있어야 합니다.")
    정함 = []
    for x in 대칭:
        if x.get("답") not in 대칭답들:
            raise 요청오류(400, f"대칭 답은 {' / '.join(대칭답들)}.")
        원 = 줄들[x["파츠"]]
        if not 원["대칭"] and x["답"] != "대칭 안 함":
            쪽 = x.get("기준쪽")
            if 쪽 not in 기준쪽들:
                raise 요청오류(400, f"{x['파츠']}: 에이전트가 비대칭으로 둔 파츠를 대칭으로 만들려면 기준쪽(+x/-x)을 골라야 합니다.")
        elif x["답"] == "대칭 안 함":
            쪽 = None
        else:
            쪽 = 원["기준쪽"] if x["답"] == "에이전트 쪽" else ("-x" if 원["기준쪽"] == "+x" else "+x")
        정함.append({"파츠": x["파츠"], "대칭": 쪽 is not None, "기준쪽": 쪽, "답": x["답"], "에이전트기준쪽": 원.get("기준쪽")})
    return {"멈춤": "계획 확인", "후보파일": m[0].name, "대칭": 정함}


def 확정쓰기(a, 이름, 답: dict, 보낸파일: str) -> None:
    """멈춤 1 답을 보낸 뒤 계획확정.json을 쓴다(한 번만)."""
    if 답.get("멈춤") != "계획 확인":
        return
    p = 폴더(a, 이름, 만들기=True) / "계획확정.json"
    with 서버.파일잠금(p):
        if p.exists():
            return
        서버.json_쓰기(p, {"꼴버전": 서버.꼴버전, "만든시각": 서버.지금(), "작업본해시": a._지금작업본해시(이름),
                         "후보파일": 답["후보파일"], "보낸묶음": 보낸파일, "대칭": 답["대칭"]})
    서버.기록(f"메시 계획 정함: {보낸파일}", a, 이름)


# ---------------------------------------------------------------- 끝나는 조건과 화면

def 완료모자람(a, 이름) -> list[str]:
    모자람 = []
    진행 = 진행읽기(a, 이름)
    안끝 = [i for i in range(1, len(순서) + 1) if str(i) not in 진행]
    if 안끝:
        모자람.append(f"정리 순서 {', '.join(map(str, 안끝))}이 끝나지 않음")
    if not 확정읽기(a, 이름):
        모자람.append("멈춤 1(계획 확인)을 정하지 않음")
    결과들 = 멈춤후보들(a, 이름, "결과 확인")
    if not 결과들:
        모자람.append("멈춤 2(결과 확인) 후보가 없음 — 에이전트 '메시멈춤'")
    else:
        q, v = 결과들[-1]
        보낸 = 보낸판단(a, 이름)
        안판단 = [x.get("번호") for x in v.get("후보") or [] if (q.name, str(x.get("번호"))) not in 보낸]
        if 안판단:
            모자람.append(f"멈춤 2 후보 {len(안판단)}개를 판단해 보내지 않음")
        결과 = v.get("결과") or {}
        if not 결과.get("접합부판정"):
            모자람.append("접합부별 판정 기록이 없음")
        elif any(x.get("판정") != "통과" for x in 결과["접합부판정"]):
            모자람.append("접합부 판정에 '통과'가 아닌 것이 있음")
        if not 결과.get("다각도그림"):
            모자람.append("여러 방향 그림이 없음")
    안된 = [q.name for q, v in a.묶음들(이름, 번호) if v.get("묶음상태") in ("보냄", "처리 중")]
    if 안된:
        모자람.append(f"처리 안 된 묶음 {len(안된)}개")
    return 모자람


def 보기(a, 이름) -> dict:
    """옆 기둥에 그릴 것."""
    진행 = 진행읽기(a, 이름)
    m = 멈춤후보(a, 이름)
    멈춤 = None
    if m:
        q, v = m
        보낸 = 보낸판단(a, 이름)
        멈춤 = {"파일": q.name, "멈춤": v["멈춤"], "만든시각": v.get("만든시각", ""), "계획": v.get("계획"), "결과": v.get("결과"),
               "후보수": len(v.get("후보") or []), "고친것수": len(v.get("고친것") or []),
               "보냄": any(f == q.name for f, _ in 보낸)}
    return {"단계": 번호, "순서": [{"번호": i + 1, "글": t, "끝": str(i + 1) in 진행, "메모": (진행.get(str(i + 1)) or {}).get("글", "")}
                               for i, t in enumerate(순서)],
            "멈춤": 멈춤, "확정": 확정읽기(a, 이름), "대칭답들": list(대칭답들), "모자람": 완료모자람(a, 이름)}


def 바뀜(a, 이름) -> str:
    try:
        d = 폴더(a, 이름)
    except Exception:
        return ""
    조각 = []
    for p in [d / "진행.json", d / "계획확정.json"] + list(d.glob("후보_*.json")) + list(d.glob("보내기_*.json")):
        try:
            조각.append(f"{p.name}:{p.stat().st_mtime_ns}")
        except OSError:
            pass
    return "|".join(sorted(조각))
