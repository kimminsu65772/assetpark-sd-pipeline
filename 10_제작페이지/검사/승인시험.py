"""승인과 TRIPO 실행 시험 — 가짜 실행만 (작업 묶음 W07, 기능명세 1부 4-5·9절 9번, 29절 W07 완료 조건)

    python 10_제작페이지/검사/승인시험.py --원본 <저장소 루트> [--포트 8778] [--남기기]

- 스크래치(임시) 폴더에 가짜 저장소를 만든다: 원본의 온천 검사 `상태.json`과 캐릭터 노트만 **복사**하고,
  작업본은 작은 가짜 파일로 둔다(원본에 쓰지 않음, TRIPO에 요청하지 않음, 크레딧을 쓰지 않음).
- 서버를 이 프로세스 안에서 다른 포트에 켠다(사용자의 8765는 건드리지 않음). 실행 모드는 가짜로 고정.
- 가짜 API 키를 환경 변수에 넣고 돌린 뒤, 가짜 저장소의 모든 파일·서버 응답·로그에서 그 키를 찾는다(0이어야 함).
- 통과/실패를 줄마다 찍는다. 실패가 하나라도 있으면 종료 코드 1.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

여기 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(여기))
sys.path.insert(0, str(여기 / "검사"))
import 제작페이지 as 서버  # noqa: E402
import 승인  # noqa: E402
from 흐름시험 import 페이지, 확인, 실패  # noqa: E402
import 흐름시험  # noqa: E402

캐릭터 = "온천_검사"
가짜키 = "tsk_W07시험가짜키_" + "x9Q2" * 6
응답모음: list[str] = []


def 에이전트(뿌리, *인자):
    rc, v = 흐름시험.에이전트(뿌리, *인자)
    응답모음.append(json.dumps(v, ensure_ascii=False))
    return rc, v


def 결정(p, 단계=2):
    st, v = p.get("/api/결정", 이름=캐릭터, 단계=단계)
    응답모음.append(json.dumps(v, ensure_ascii=False))
    return v


def 승인보내기(p, r, **바꿀것):
    몸 = {"이름": 캐릭터, "단계": 2, "파일": r["파일"], "명령": r["명령"], "크레딧": r["크레딧"], "횟수": r["횟수"], "값해시": r["값해시"]}
    몸.update(바꿀것)
    st, v = p.post("/api/승인", 몸)
    응답모음.append(json.dumps(v, ensure_ascii=False))
    return st, v


def 기다리기(p, 파일, 초=10.0):
    끝 = time.monotonic() + 초
    while time.monotonic() < 끝:
        r = (결정(p).get("승인") or {}).get("요청") or {}
        if r.get("파일") == 파일 and r.get("실행") in ("실행됨", "실패"):
            return r
        time.sleep(0.1)
    return {}


def 요청파일(뿌리, 값) -> str:
    f = 뿌리 / f"요청_{time.monotonic_ns()}.json"
    f.write_text(json.dumps(값, ensure_ascii=False), encoding="utf-8")
    return str(f)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--원본", required=True)
    ap.add_argument("--포트", type=int, default=8778)
    ap.add_argument("--남기기", action="store_true")
    인자 = ap.parse_args()
    원본 = Path(인자.원본).resolve()
    뿌리 = Path(tempfile.mkdtemp(prefix="승인시험_"))
    c원 = 원본 / "01_캐릭터" / 캐릭터
    c = 뿌리 / "01_캐릭터" / 캐릭터
    (c / "제작페이지").mkdir(parents=True)
    작업본 = c / "04_Blender" / "가짜_작업본.blend"
    작업본.parent.mkdir()
    작업본.write_bytes(b"BLENDER-v4 W07 fake")
    상태 = json.loads((c원 / "제작페이지" / "상태.json").read_text(encoding="utf-8"))
    상태["작업본"] = 작업본.relative_to(뿌리).as_posix()
    for 칸 in 상태["단계"]:
        칸["상태"] = "끝" if 칸["번호"] == 1 else "입력 없음"
        칸["표시"] = []
    (c / "제작페이지" / "상태.json").write_text(json.dumps(상태, ensure_ascii=False, indent=2), encoding="utf-8")
    (뿌리 / "SSOT" / "캐릭터").mkdir(parents=True)
    shutil.copy2(원본 / "SSOT" / "캐릭터" / f"{캐릭터}.md", 뿌리 / "SSOT" / "캐릭터" / f"{캐릭터}.md")
    그림 = c / "02_설정화" / "앞.png"
    그림.parent.mkdir()
    그림.write_bytes(b"\x89PNG\r\n\x1a\n")
    그림상대 = 그림.relative_to(뿌리).as_posix()
    print(f"가짜 저장소: {뿌리}")

    # 서버(이 프로세스 안, 다른 포트). 가짜 실행 고정, 잔액·로그는 가짜 저장소 안
    서버.로컬 = 뿌리 / "_로컬"
    승인.가짜잔액파일 = 서버.로컬 / "TRIPO잔액_가짜.json"
    승인.진짜잔액파일 = 서버.로컬 / "TRIPO잔액.json"
    승인.모드, 승인.가짜결과, 승인.가짜초 = "가짜", "성공", 0.5
    승인.추가막기.clear()   # W10의 단계별 검사(2단계 입력 네 장 등)는 생성시험.py가 본다. 여기서는 W07 승인 흐름만
    os.environ["TRIPO_API_KEY"] = 가짜키
    a = 서버.앱(뿌리, 인자.포트)
    s = 서버.서버(("127.0.0.1", 인자.포트), 서버.처리기만들기(a))
    a.서버 = s
    threading.Thread(target=s.serve_forever, kwargs={"poll_interval": 0.2}, daemon=True).start()
    p = 페이지(인자.포트)
    d2 = c / "제작페이지" / "02_모델생성"
    좋은명령 = f"tripo generate multiview-to-model {그림상대} --model tripo-p2 -p quad=true -p face_limit=5000"
    try:
        p.post("/api/탭", {"캐릭터": 캐릭터, "단계": 2})
        v = 결정(p)
        확인(v["승인"] and v["승인"]["요청"] is None and "요청이 없습니다" in v["승인"]["막는이유"] and v["승인"]["잔액"]["가짜"],
             "요청 전: 승인 상자에 '요청 없음', 승인 막힘, 잔액은 가짜")
        확인(결정(p, 3)["승인"] is None, "유료가 아닌 단계(3)에는 승인 상자가 없음")

        # 1) 받지 않는 명령
        for 명령, 뜻 in [("tripo login --key abc", "tripo login"), (좋은명령 + " --out x", "--out"),
                       (좋은명령 + " -p key=" + 가짜키, "키처럼 보이는 글"), ("rm -rf /", "tripo가 아님"),
                       ("tripo redo", "tripo redo")]:
            rc, v = 에이전트(뿌리, "승인요청", 요청파일(뿌리, {"무엇": "모델 생성", "명령": 명령, "크레딧": 100}), "--단계", "2")
            확인(rc == 1, f"승인요청 거부: {뜻} → {v.get('오류', '')[:60]}")
        rc, v = 에이전트(뿌리, "승인요청", 요청파일(뿌리, {"무엇": "x", "명령": 좋은명령, "크레딧": 1}), "--단계", "3")
        확인(rc == 1, "유료가 아닌 단계(3)의 승인요청 거부")

        # 2) 요청 → 보인 값과 다른 값으로 승인하면 거부
        rc, v = 에이전트(뿌리, "승인요청", 요청파일(뿌리, {"무엇": "모델 생성", "명령": 좋은명령, "크레딧": 100, "횟수": 1}), "--단계", "2")
        확인(rc == 0 and v["값해시"], "승인요청 씀(값해시 = 명령의 SHA-256)")
        r = 결정(p)["승인"]["요청"]
        확인(r["승인"] == "대기" and r["실행"] == "안 함" and r["해시맞음"] and r["명령"] == 좋은명령, "승인 상자: 명령 그대로, 대기")
        st, v = 승인보내기(p, r, 명령=r["명령"] + " ")
        확인(st == 409 and "다릅니다" in v.get("오류", ""), "보인 명령이 한 글자 다르면 승인 거부")
        st, v = 승인보내기(p, r, 크레딧=10)
        확인(st == 409, "보인 크레딧이 다르면 승인 거부")

        # 3) 파일의 명령이 바뀜(값해시는 옛것) → 무효
        q = d2 / r["파일"]
        w = json.loads(q.read_text(encoding="utf-8"))
        w["명령"] = 좋은명령.replace("5000", "9000")
        q.write_text(json.dumps(w, ensure_ascii=False), encoding="utf-8")
        g = 결정(p)["승인"]
        확인("값해시" in g["막는이유"] and not g["요청"]["해시맞음"], "파일의 값이 바뀌면 값해시가 안 맞아 승인 막힘")
        st, v = 승인보내기(p, g["요청"])
        확인(st == 409 and "무효" in v.get("오류", ""), "값해시가 안 맞는 요청은 승인해도 실행 안 함")

        # 4) 새 요청이 옛 대기 요청을 무효로 바꿈
        옛 = r
        rc, v = 에이전트(뿌리, "승인요청", 요청파일(뿌리, {"무엇": "모델 생성", "명령": 좋은명령, "크레딧": 100, "횟수": 1}), "--단계", "2")
        확인(rc == 0 and 옛["파일"] in v["무효로바꾼것"], "새 요청을 쓰면 앞의 대기 요청은 '거절'(무효)")
        st, v = 승인보내기(p, 옛)
        확인(st == 409, "무효가 된 옛 요청으로 승인 거부")

        # 5) 바르게 승인 → 한 번만 실행
        r = 결정(p)["승인"]["요청"]
        st, v = 승인보내기(p, r)
        확인(st == 200 and v.get("실행") == "실행 중" and v.get("모드") == "가짜", "바른 값으로 승인 → 서버가 실행 시작(가짜)")
        st2, v2 = 승인보내기(p, r)
        확인(st2 == 409, f"실행 중에 같은 승인 다시 누름 → 거부({v2.get('오류', '')[:40]})")
        g = 결정(p)
        확인(g["상태"] == "진행 중" and g["승인"]["요청"]["실행"] == "실행 중", "실행 중: 단계 '진행 중', 승인 상자 '실행 중'")
        끝 = 기다리기(p, r["파일"])
        결 = 끝.get("결과") or {}
        확인(끝.get("실행") == "실행됨" and 결.get("가짜") and 결.get("작업번호") and 결["작업번호"][0].startswith("가짜-"), f"실행됨: 작업 {결.get('작업번호')}")
        확인(결.get("쓴크레딧") == 100 and 결.get("잔액전") == 1000 and 결.get("잔액후") == 900, f"쓴 크레딧·잔액 전후 기록: {결.get('쓴크레딧')}, {결.get('잔액전')}→{결.get('잔액후')}")
        확인(str(그림) in 결.get("실제값", "") and 결.get("실제값", "").endswith("--json"), "실제로 쓴 값(실제 경로, --json) 기록")
        확인(len(결.get("받은파일") or []) == 1 and (뿌리 / 결["받은파일"][0]).is_file(), f"받은 파일을 단계 폴더에 둠: {결.get('받은파일')}")
        st3, v3 = 승인보내기(p, r)
        확인(st3 == 409, "실행됨인 요청은 다시 승인해도 실행 안 함")
        g = 결정(p)
        확인(g["상태"] == "결정 대기" and g["알림"] and "가짜 실행" in g["알림"]["글"], f"끝: 단계 '결정 대기', 알림: {g['알림']['글'][:50] if g['알림'] else None}")
        확인(json.loads(승인.가짜잔액파일.read_text(encoding="utf-8"))["잔액"] == 900, "가짜 잔액 기록 900(진짜 잔액 기록 파일은 안 씀)")
        확인(not 승인.진짜잔액파일.exists(), "진짜 잔액 기록 파일을 만들지 않음")
        확인(p.get("/api/캐릭터")[1]["잔액"]["잔액"] == 900, "윗줄 잔액(/api/캐릭터)도 900")

        # 6) 다시 생성 → 같은 값의 새 대기 요청, 바로 실행하지 않음
        st, v = p.post("/api/다시생성", {"이름": 캐릭터, "단계": 2})
        g = 결정(p)["승인"]
        확인(st == 200 and g["요청"]["승인"] == "대기" and g["요청"]["실행"] == "안 함" and g["요청"]["명령"] == 좋은명령, "다시 생성: 같은 값의 새 요청(대기), 실행 안 함")
        st, v = p.post("/api/다시생성", {"이름": 캐릭터, "단계": 2})
        확인(st == 409, "대기 요청이 있으면 다시 생성 막힘")

        # 7) 잔액 부족 → 승인 막힘
        rc, v = 에이전트(뿌리, "승인요청", 요청파일(뿌리, {"무엇": "모델 생성", "명령": 좋은명령, "크레딧": 500, "횟수": 2}), "--단계", "2")
        g = 결정(p)["승인"]
        확인("잔액이 모자랍니다" in g["막는이유"], f"잔액 부족이면 승인 막힘: {g['막는이유']}")
        st, v = 승인보내기(p, g["요청"])
        확인(st == 409 and "잔액" in v.get("오류", ""), "잔액 부족이면 서버도 승인 거부")

        # 8) 크레딧 모름 → 승인할 수 있음. 가짜 실패 → 막힘·알림
        rc, v = 에이전트(뿌리, "승인요청", 요청파일(뿌리, {"무엇": "모델 생성", "명령": 좋은명령, "크레딧": "모름"}), "--단계", "2")
        g = 결정(p)["승인"]
        확인(g["요청"]["크레딧"] == "모름" and not g["막는이유"], "크레딧 모름이어도 승인할 수 있음")
        승인.가짜결과 = "실패"
        st, v = 승인보내기(p, g["요청"])
        끝 = 기다리기(p, g["요청"]["파일"])
        g2 = 결정(p)
        확인(끝.get("실행") == "실패" and "실패" in (끝.get("결과") or {}).get("실패이유", "") and g2["상태"] == "막힘" and g2["알림"]["종류"] == "막힘",
             f"실행 실패: 단계 '막힘', 알림 막힘({(끝.get('결과') or {}).get('실패이유', '')[:30]})")
        확인((끝.get("결과") or {}).get("잔액전") == (끝.get("결과") or {}).get("잔액후"), "실패: 잔액 전후를 적어 크레딧이 빠졌는지 확인")
        승인.가짜결과 = "잔액부족"
        p.post("/api/다시생성", {"이름": 캐릭터, "단계": 2})
        g = 결정(p)["승인"]
        승인보내기(p, g["요청"])
        끝 = 기다리기(p, g["요청"]["파일"])
        확인(끝.get("실행") == "실패" and "잔액" in (끝.get("결과") or {}).get("실패이유", ""), "TRIPO가 잔액 부족(종료 코드 4)이라고 하면 실패와 이유")
        승인.가짜결과 = "성공"

        # 9) 서버가 실행 중에 꺼진 요청 → 다시 실행하지 않고 실패로
        p.post("/api/다시생성", {"이름": 캐릭터, "단계": 2})
        g = 결정(p)["승인"]["요청"]
        q = d2 / g["파일"]
        w = json.loads(q.read_text(encoding="utf-8"))
        w.update({"승인": "승인", "실행": "실행 중"})
        q.write_text(json.dumps(w, ensure_ascii=False), encoding="utf-8")
        g = 결정(p)["승인"]["요청"]
        확인(g["실행"] == "실패" and "꺼짐" in g["결과"].get("실패이유", ""), "실행 중에 서버가 꺼진 요청: 다시 실행하지 않고 실패와 이유")

        # 10) 진짜 실행 모드: 키가 없으면 실행 전에 멈춤(바깥 요청 없음, 크레딧 안 씀)
        승인.모드 = "진짜"
        os.environ.pop("TRIPO_API_KEY")
        p.post("/api/다시생성", {"이름": 캐릭터, "단계": 2})
        g = 결정(p)["승인"]["요청"]
        승인보내기(p, g)
        끝 = 기다리기(p, g["파일"])
        확인(끝.get("실행") == "실패" and "TRIPO_API_KEY" in (끝.get("결과") or {}).get("실패이유", ""), "진짜 모드에서 키가 없으면 실행 전에 실패(크레딧 안 씀)")
        승인.모드 = "가짜"

        # 11) 다른 탭이면 승인 막힘
        다른 = 페이지(인자.포트)
        다른.탭 = "다른탭"
        다른.post("/api/탭", {"캐릭터": 캐릭터, "단계": 2})
        p.post("/api/다시생성", {"이름": 캐릭터, "단계": 2})
        g = 결정(p)["승인"]["요청"]
        st, v = 다른.post("/api/승인", {"이름": 캐릭터, "단계": 2, "파일": g["파일"], "명령": g["명령"], "크레딧": g["크레딧"], "횟수": g["횟수"], "값해시": g["값해시"]})
        확인(st == 409 and "다른 탭" in v.get("오류", ""), "늦게 연 탭에서는 승인 거부")

        # 12) API 키가 화면·기록·로그 어디에도 없음
        나온곳 = []
        for f in 뿌리.rglob("*"):
            if f.parent == 뿌리 and f.name.startswith("요청_"):
                continue  # 시험이 일부러 키를 넣은 입력 파일(에이전트가 거부한 것)
            if f.is_file() and 가짜키.encode() in f.read_bytes():
                나온곳.append(f.relative_to(뿌리).as_posix())
        if any(가짜키 in t for t in 응답모음):
            나온곳.append("서버·에이전트 응답")
        확인(not 나온곳, f"API 키 검색: 가짜 저장소의 파일 {sum(1 for f in 뿌리.rglob('*') if f.is_file())}개와 응답 {len(응답모음)}개에서 0곳 {나온곳}")
    finally:
        s.shutdown()
        s.server_close()
        if 인자.남기기:
            print(f"남김: {뿌리}")
        else:
            shutil.rmtree(뿌리, ignore_errors=True)
    print(f"\n실패 {len(실패)}개" if 실패 else "\n모두 통과")
    return 1 if 실패 else 0


if __name__ == "__main__":
    sys.exit(main())
