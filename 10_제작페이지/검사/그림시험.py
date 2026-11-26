"""1단계 그림 생성 화면의 서버 흐름 시험 (작업 묶음 W09, 기능명세 2부 13절 · 24절)

    python 10_제작페이지/검사/그림시험.py --원본 <저장소 루트> [--포트 8781] [--남기기]

- 스크래치(임시) 폴더에 가짜 저장소를 만든다: 원본의 SSOT 전체, 온천 검사 상태.json·기준 그림, 교복 사무라이의 참고 그림을
  **복사**만 한다(원본에 쓰지 않음. 끝에 원본 상태.json의 해시가 그대로인지 확인).
- 서버를 이 프로세스 안에서 다른 포트에 켜고(사용자의 8765는 건드리지 않음), 페이지가 하는 요청은 HTTP로,
  에이전트가 하는 일(그림판정)은 `에이전트.py`를 따로 실행해서 한다.
- Codex는 부르지 않는다(가짜 실행). 일부러 일으키는 예외: 노트 없음, 설정 확인 전, 판정 전 승인, 기준 승인 전 시트,
  등신 범위 밖, 자르기 실패, 사용량 한도, 그림 밖 경로, 필수 칸 빈 새 캐릭터.
- 실패가 하나라도 있으면 종료 코드 1. `--남기기`면 가짜 저장소를 지우지 않고 경로를 찍는다(화면 시험에 씀).
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
from pathlib import Path

여기 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(여기))
import 제작페이지 as 서버  # noqa: E402

캐릭터 = "온천_검사"
실패 = []


def 확인(조건, 글):
    print(("통과 " if 조건 else "실패 ") + 글, flush=True)
    if not 조건:
        실패.append(글)


def 해시(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


class 페이지:
    def __init__(self, 포트):
        self.포트 = 포트
        self.탭 = "그림시험탭"

    def _요청(self, 방법, 경로, 몸=None):
        c = http.client.HTTPConnection("127.0.0.1", self.포트, timeout=60)
        h = {"Host": f"127.0.0.1:{self.포트}"}
        b = None
        if 몸 is not None:
            b = json.dumps(몸, ensure_ascii=False).encode()
            h.update({"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{self.포트}"})
        길, _, 질문 = 경로.partition("?")
        c.request(방법, urllib.parse.quote(길) + (f"?{질문}" if 질문 else ""), body=b, headers=h)
        r = c.getresponse()
        몸 = r.read()
        try:
            return r.status, json.loads(몸 or b"{}")
        except ValueError:
            return r.status, {"_바이트": len(몸)}

    def get(self, 주소, **질문):
        return self._요청("GET", 주소 + "?" + urllib.parse.urlencode(질문))

    def post(self, 경로, 몸):
        return self._요청("POST", 경로, dict(몸, 탭=self.탭))


def 에이전트(뿌리: Path, *인자, 이름=캐릭터) -> tuple[int, dict]:
    r = subprocess.run([sys.executable, str(여기 / "에이전트.py"), *인자, "--캐릭터", 이름, "--폴더", str(뿌리)],
                       capture_output=True, text=True, encoding="utf-8")
    try:
        return r.returncode, json.loads(r.stdout)
    except ValueError:
        return r.returncode, {"오류": (r.stdout + r.stderr)[-400:]}


def 판정(뿌리, 번호, 등신=2.5, 손="충족", 탈락=False) -> tuple[int, dict]:
    f = 뿌리 / f"_판정_{번호}.json"
    v = {"번호": 번호, "판정": {k: {"판정": "충족", "근거": "가짜 그림(시험)"} for k in 서버.그림단계.범주}, "탈락": 탈락}
    v["판정"]["구조의 타당성"] = {"판정": 손, "근거": "손 모양(시험)"}
    if 번호.startswith("기준"):
        v["판정"]["시점 간 일관성"] = {"판정": "해당 없음", "근거": "한 장"}
        v.update(등신=등신, 등신근거="정수리~신발 바닥 ÷ 정수리~턱(시험)")
    f.write_text(json.dumps(v, ensure_ascii=False), encoding="utf-8")
    return 에이전트(뿌리, "그림판정", str(f), "--단계", "1")


def 기다리기(p, 이름=캐릭터, 초=30):
    끝 = time.monotonic() + 초
    while time.monotonic() < 끝:
        _, v = p.get("/api/그림", 이름=이름)
        if not v.get("실행중"):
            return v
        time.sleep(0.3)
    return v


def 만들기(원본: Path) -> Path:
    뿌리 = Path(tempfile.mkdtemp(prefix="그림시험_"))
    shutil.copytree(원본 / "SSOT", 뿌리 / "SSOT", ignore=shutil.ignore_patterns("조립결과"))
    c원, c = 원본 / "01_캐릭터" / 캐릭터, 뿌리 / "01_캐릭터" / 캐릭터
    (c / "제작페이지").mkdir(parents=True)
    상태 = json.loads((c원 / "제작페이지" / "상태.json").read_text(encoding="utf-8"))
    상태["작업본"], 상태["작업본해시"] = "", ""
    for 칸 in 상태["단계"]:
        칸.update(상태="입력 없음", 입력=[], 표시=[], 출처="")
    (c / "제작페이지" / "상태.json").write_text(json.dumps(상태, ensure_ascii=False, indent=2), encoding="utf-8")
    for 상 in ["01_캐릭터/온천_검사/01_컨셉아트/온천_검사_A포즈_v002.png",
              "01_캐릭터/교복_사무라이/01_컨셉아트/교복_사무라이_A포즈_v003.png",
              "01_캐릭터/교복_사무라이/02_설정화/실험_004/세션_A/EXP004_세션_A_멀티뷰원본_v001.png",
              *[f"01_캐릭터/교복_사무라이/03_TRIPO/실험_004_입력이미지/후보_A/{n}" for n in
                ("01_front.png", "02_profile_facing_left.png", "03_back.png", "04_profile_facing_right.png")]]:
        (뿌리 / 상).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(원본 / 상, 뿌리 / 상)
    return 뿌리


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--원본", required=True)
    ap.add_argument("--포트", type=int, default=8781)
    ap.add_argument("--남기기", action="store_true")
    인자 = ap.parse_args()
    원본 = Path(인자.원본).resolve()
    원본상태 = 원본 / "01_캐릭터" / 캐릭터 / "제작페이지" / "상태.json"
    원본해시 = 해시(원본상태)
    원본설정화 = sorted(p.name for p in (원본 / "01_캐릭터" / 캐릭터 / "02_설정화").glob("*")) if (원본 / "01_캐릭터" / 캐릭터 / "02_설정화").is_dir() else []
    뿌리 = 만들기(원본)
    print(f"가짜 저장소: {뿌리}")
    서버.로컬 = 뿌리 / "_로컬"
    서버.그림단계.가짜초 = 0.2
    a = 서버.앱(뿌리, 인자.포트)
    s = 서버.서버(("127.0.0.1", 인자.포트), 서버.처리기만들기(a))
    a.서버 = s
    threading.Thread(target=s.serve_forever, kwargs={"poll_interval": 0.2}, daemon=True).start()
    p = 페이지(인자.포트)
    c = 뿌리 / "01_캐릭터" / 캐릭터
    try:
        p.post("/api/탭", {"캐릭터": 캐릭터, "단계": 1})
        st, v = p.get("/api/그림", 이름=캐릭터)
        확인(st == 200 and v["노트"]["있음"] and len(v["노트"]["설정"]) >= 5 and not v["노트"]["확인됨"], f"보기: 노트 설정 {len(v['노트']['설정'])}줄, 확인 전")
        확인(v["모드"] == "가짜", "기본은 가짜 실행")
        확인(any(x["이름"] == "교복_사무라이" for x in v["다른캐릭터"]), "다른 캐릭터와 나란히: 교복 사무라이 기준 그림")

        # 생성 막힘: 설정 확인 전, 시트(기준 승인 전)
        st, v = p.post("/api/그림/생성", {"이름": 캐릭터, "종류": "기준"})
        확인(st == 409 and "설정" in v.get("오류", ""), f"설정 표 확인 전 생성 거부: {v.get('오류')}")
        st, v = p.post("/api/그림/생성", {"이름": 캐릭터, "종류": "시트", "설정확인": True})
        확인(st == 409 and "기준 그림을 먼저" in v.get("오류", ""), f"기준 승인 전 시트 생성 거부: {v.get('오류')}")

        # 기준 그림 생성
        st, v = p.post("/api/그림/생성", {"이름": 캐릭터, "종류": "기준", "설정확인": True})
        확인(st == 200 and v.get("모드") == "가짜", "기준 그림 생성 시작(가짜)")
        st2, v2 = p.post("/api/그림/생성", {"이름": 캐릭터, "종류": "기준", "설정확인": True})
        확인(st2 == 409, f"생성 중 두 번째 생성 거부: {v2.get('오류')}")
        v = 기다리기(p)
        g = v["그림"][-1]
        확인(g["번호"] == "기준001" and g["파일"] and not g["실패이유"], f"기준001 생김: {g['파일']} {g['실패이유']}")
        확인(g["요청문"].endswith("요청문_기준_영어.txt") and (뿌리 / g["요청문"]).is_file(), f"영어 요청문 사본: {g['요청문']}")
        확인((뿌리 / g["폴더"] / "요청문_기준.txt").is_file() and (뿌리 / g["폴더"] / "생성기록.json").is_file(), "한국어 요청문 사본과 생성기록")
        확인(v["요청문"].get("기준", {}).get("영어", "").strip() != "" and v["요청문"]["기준"]["한국어"].strip() != "", "화면용 한국어·영어 요청문")
        확인(v["노트"]["확인됨"], "설정 확인을 기록함(노트 해시)")
        _, 상 = p.get("/api/상태", 이름=캐릭터)
        확인(상["단계"][0]["상태"] == "결정 대기", f"1단계 상태 결정 대기: {상['단계'][0]['상태']}")
        _, 결 = p.get("/api/결정", 이름=캐릭터, 단계=1)
        확인(결["알림"] and "생성 끝" in 결["알림"]["글"], f"알림: {결['알림'] and 결['알림']['글']}")
        st, 몸 = p.get("/api/그림/파일", 경로=g["파일"][0])
        확인(st == 200 and 몸.get("_바이트", 0) > 1000, "그림 파일을 내줌")
        st, _ = p.get("/api/그림/파일", 경로="SSOT/00_시작.md")
        확인(st == 404, "01_캐릭터 밖·그림 아닌 파일은 내주지 않음")

        # 판정 전 승인 거부 → 판정(등신 범위 밖) → 경고 → 판정 고침 → 승인
        st, v = p.post("/api/그림/승인", {"이름": 캐릭터, "번호": "기준001"})
        확인(st == 409 and "자가 검수" in v.get("오류", ""), f"판정 전 승인 거부: {v.get('오류')}")
        rc, v = 판정(뿌리, "기준001", 등신="둘")
        확인(rc == 1, f"등신이 숫자가 아니면 판정 거부: {v.get('오류')}")
        rc, v = 판정(뿌리, "기준001", 등신=3.0, 손="보완 필요")
        확인(rc == 0 and len(v["경고"]) == 2, f"판정 씀, 경고 2개(등신 범위 밖, 보완 필요): {v.get('경고')}")
        st, v = p.post("/api/그림/승인", {"이름": 캐릭터, "번호": "기준001"})
        확인(st == 200 and v["됨"] is False and any("범위 밖" in x for x in v["경고"]), "범위 밖이면 승인 전에 묻는다(됨: 거짓)")
        rc, v = 판정(뿌리, "기준001", 등신=2.5)
        확인(rc == 0 and not v["경고"], "판정 고침(등신 2.5)")
        st, v = p.post("/api/그림/승인", {"이름": 캐릭터, "번호": "기준001"})
        확인(st == 200 and v["됨"] and not v["조건미달"], "기준001 승인")
        st, v = p.post("/api/그림/승인", {"이름": 캐릭터, "번호": "기준001"})
        확인(st == 409, "같은 그림 두 번 승인 거부")
        rc, v = 판정(뿌리, "기준001", 등신=2.6)
        확인(rc == 1, "승인한 그림의 판정은 바꾸지 않음")

        # 시트: 자르기 실패 → 승인 막힘
        서버.그림단계.가짜결과 = "자르기실패"
        p.post("/api/그림/생성", {"이름": 캐릭터, "종류": "시트"})
        v = 기다리기(p)
        g = v["그림"][-1]
        확인(g["종류"] == "시트" and g.get("자르기오류") and not g["자른것"], f"자르기 실패: {g.get('자르기오류')}")
        _, 결 = p.get("/api/결정", 이름=캐릭터, 단계=1)
        확인("자르지 않았습니다" in 결["알림"]["글"], "자르기 실패를 알림에")
        판정(뿌리, g["번호"])
        st, v = p.post("/api/그림/승인", {"이름": 캐릭터, "번호": g["번호"]})
        확인(st == 409 and "네 장" in v.get("오류", ""), f"자르지 못한 시트 승인 거부: {v.get('오류')}")

        # 사용량 한도 → 막힘
        서버.그림단계.가짜결과 = "한도"
        p.post("/api/그림/생성", {"이름": 캐릭터, "종류": "시트", "다시": True})
        v = 기다리기(p)
        _, 상 = p.get("/api/상태", 이름=캐릭터)
        _, 결 = p.get("/api/결정", 이름=캐릭터, 단계=1)
        확인(상["단계"][0]["상태"] == "막힘" and 결["알림"]["종류"] == "막힘" and "한도" in 결["알림"]["글"], f"한도 → 막힘: {결['알림']['글']}")

        # 시트 성공 → 네 장 → 판정 → 승인 → TRIPO 입력
        서버.그림단계.가짜결과 = "성공"
        p.post("/api/그림/생성", {"이름": 캐릭터, "종류": "시트", "다시": True})
        v = 기다리기(p)
        g = v["그림"][-1]
        확인(len(g["자른것"]) == 4 and all((뿌리 / x).is_file() for x in g["자른것"]), f"시트를 네 장으로 자름: {[Path(x).name for x in g['자른것']]} {g.get('자르기오류', '')}{g.get('실패이유', '')}")
        if len(g["자른것"]) != 4:
            print("   ", json.loads((뿌리 / g["폴더"] / "생성기록.json").read_text(encoding="utf-8")).get("로그", [])[-1][-600:] if g["폴더"] else g)
        확인(any("페이지생성_" in x for x in g["참고그림"]), f"시트 참고 그림에 승인한 기준 그림: {g['참고그림']}")
        _, 결 = p.post("/api/결정", {"이름": 캐릭터, "단계": 1, "결정": "이 단계 끝"})
        확인(결.get("됨") is False and any("시트" in x for x in 결["모자람"]), f"시트 승인 전 '이 단계 끝' → 모자람: {결.get('모자람')}")
        판정(뿌리, g["번호"])
        st, v = p.post("/api/그림/승인", {"이름": 캐릭터, "번호": g["번호"]})
        t = 뿌리 / v.get("TRIPO폴더", "_")
        확인(st == 200 and v["됨"] and v["검사통과"] and len(list(t.glob("*.png"))) == 4, f"시트 승인 → {v.get('TRIPO폴더')} 네 장, 검사 통과")
        _, 상 = p.get("/api/상태", 이름=캐릭터)
        확인(len(상["단계"][1]["입력"]) == 4 and 상["단계"][1]["상태"] == "준비됨", f"2단계 입력 네 장, 상태 {상['단계'][1]['상태']}")

        # 탈락한 그림이 입력 자리에 섞이면 끝나는 조건이 막는다
        shutil.copy2(뿌리 / "01_캐릭터/온천_검사/01_컨셉아트/온천_검사_A포즈_v002.png", t / "99_extra.png")
        _, 결 = p.post("/api/결정", {"이름": 캐릭터, "단계": 1, "결정": "이 단계 끝"})
        확인(결.get("됨") is False and any("승인하지 않은" in x for x in 결["모자람"]), f"TRIPO 입력에 낯선 그림 → 모자람: {결.get('모자람')}")
        (t / "99_extra.png").unlink()
        _, 결 = p.post("/api/결정", {"이름": 캐릭터, "단계": 1, "결정": "이 단계 끝"})
        확인(결.get("됨") and 결["상태"] == "끝", f"이 단계 끝 → {결.get('상태')} {결.get('모자람')}")

        # 그림 위 표시(2D): 작성 중 → 보내기
        그파일 = v.get("입력", [""])[0] or g["자른것"][0]
        표 = {"번호": "①", "누가": "사용자", "종류": "손·발 모양", "자리": {"파츠": [], "면": {}, "그림": {"파일": g["자른것"][2], "범위": [[10, 20], [60, 80]], "획": [{"붓": 8, "점": [[30, 40], [40, 60]]}]}},
             "반대쪽도": False, "메모": "뒤 모습 손", "작업본해시": ""}
        st, v = p.post("/api/작성중", {"이름": 캐릭터, "단계": 1, "표시": [표], "후보판단": [], "다음번호": 2, "묶음번호": 0})
        확인(st == 200, f"1단계 작성 중 저장: {v}")
        나쁜 = json.loads(json.dumps(표))
        나쁜["자리"]["그림"]["파일"] = "01_캐릭터/온천_검사/없는그림.png"
        st, v = p.post("/api/작성중", {"이름": 캐릭터, "단계": 1, "표시": [나쁜], "후보판단": [], "다음번호": 2, "묶음번호": 0})
        확인(st == 400, f"없는 그림 위 표시 거부: {v.get('오류')}")
        st, v = p.post("/api/작성중", {"이름": 캐릭터, "단계": 1, "표시": [dict(표, 종류="지우기")], "후보판단": [], "다음번호": 2, "묶음번호": 0})
        확인(st == 400, "1단계에 없는 처리 종류 거부")
        st, v = p.post("/api/보내기", {"이름": 캐릭터, "단계": 1, "표시": [표], "후보판단": [], "다음번호": 2, "묶음번호": 0})
        보낸 = 뿌리 / v.get("파일", "_")
        확인(st == 200 and 보낸.is_file() and json.loads(보낸.read_text(encoding="utf-8"))["표시"][0]["자리"]["그림"]["범위"] == [[10, 20], [60, 80]], f"보내기 파일: {v.get('파일')}")

        # 새 캐릭터 입력
        항목 = {n: "" for n in ["이름", "컨셉", "헤어", "의상", "양말·신발", "체형·인상", "표정", "뺄 것", "참고 그림", "기타"]}
        st, v = p.post("/api/그림/새캐릭터", {"항목들": dict(항목, 이름="시험_캐릭터", 컨셉="궁수")})
        확인(st == 400 and "헤어" in v.get("오류", ""), f"필수 칸 빈 새 캐릭터 거부: {v.get('오류')}")
        st, v = p.post("/api/그림/새캐릭터", {"항목들": dict(항목, 이름="../밖", 컨셉="a", 헤어="b", 의상="c")})
        확인(st == 400, "경로를 벗어나는 이름 거부")
        st, v = p.post("/api/그림/새캐릭터", {"항목들": dict(항목, 이름="시험_캐릭터", 컨셉="숲의 궁수", 헤어="갈색 단발", 의상="초록 망토", 기타="모자 없음")})
        입력 = 뿌리 / v.get("파일", "_")
        확인(st == 200 and 입력.is_file() and json.loads(입력.read_text(encoding="utf-8"))["항목들"]["기타"] == "모자 없음"
             and (뿌리 / "01_캐릭터/시험_캐릭터/제작페이지/상태.json").is_file(), f"새 캐릭터 입력: {v.get('파일')}")
        st, v = p.post("/api/그림/새캐릭터", {"항목들": dict(항목, 이름="시험_캐릭터", 컨셉="a", 헤어="b", 의상="c")})
        확인(st == 409, "같은 이름 새 캐릭터 거부")
        p.post("/api/탭", {"캐릭터": "시험_캐릭터", "단계": 1})
        st, v = p.post("/api/그림/생성", {"이름": "시험_캐릭터", "종류": "기준", "설정확인": True})
        확인(st == 409 and "캐릭터 노트가 없습니다" in v.get("오류", ""), f"노트 없는 캐릭터 생성 거부: {v.get('오류')}")
        _, 상 = p.get("/api/상태", 이름="시험_캐릭터")
        확인("캐릭터 노트 없음" in 상["단계"][0]["표시"], "1단계에 '캐릭터 노트 없음'")

        # 그림등록(가져온 그림)
        f = 뿌리 / "_등록.json"
        f.write_text(json.dumps({"종류": "기준", "파일": "01_캐릭터/온천_검사/01_컨셉아트/온천_검사_A포즈_v002.png", "출처": "시험"}, ensure_ascii=False), encoding="utf-8")
        rc, v = 에이전트(뿌리, "그림등록", str(f), "--단계", "1")
        확인(rc == 0 and v["번호"] == "기준002", f"그림등록: {v}")
    finally:
        s.shutdown()
    확인(해시(원본상태) == 원본해시, "원본 상태.json 그대로")
    지금설정화 = sorted(p.name for p in (원본 / "01_캐릭터" / 캐릭터 / "02_설정화").glob("*")) if (원본 / "01_캐릭터" / 캐릭터 / "02_설정화").is_dir() else []
    확인(지금설정화 == 원본설정화, "원본 캐릭터 폴더에 생성 폴더가 생기지 않음")
    if 인자.남기기:
        print(f"남김: {뿌리}")
    else:
        shutil.rmtree(뿌리, ignore_errors=True)
    print(f"\n실패 {len(실패)}개" if 실패 else "\n모두 통과")
    return 1 if 실패 else 0


if __name__ == "__main__":
    sys.exit(main())
