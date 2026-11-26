"""10·11단계 동작·내보내기 시험 — 고르기·옮기기·옮김 기록·TRIPO 동작 승인·처리의 쪽·9단계로 넘어온 리포트·Unity 경로·잠금·덮어쓰기·검사표·봄 (작업 묶음 W14, 기능명세 2부 22·23·24절)

    python 10_제작페이지/검사/동작시험.py --원본 <저장소 루트> [--포트 8783] [--남기기]

- 스크래치(임시) 폴더에 가짜 저장소를 만든다: 원본 온천 검사 `상태.json`과 그림 한 장만 **복사**. 작업본·동작 모음(GLB·FBX)·Unity 프로젝트는 작은 가짜.
  리깅설정.json을 두지 않아 미리 보기 만들기는 "못 만듦"(Blender를 부르지 않음). TRIPO는 가짜 실행. 원본에도, 진짜 Unity 프로젝트에도 쓰지 않음.
- 일부러 일으키는 예외: 고른 것 없이 옮기기, 모음에 없는 동작, 다른 단계에서 명령, 이름 없는 옮김 줄, 까닭 없는 실패 줄, 8단계 실행 없이 TRIPO 동작 요청,
  프리셋 6개, 쪽 없는 처리, 상대 경로·한글 이름·버전 다름·옮긴 동작 없음·같은 이름(덮어쓰기 안 함)·사본 없는 덮어쓰기 결과·그림 없이 봄, 작업본이 바뀜.
"""
from __future__ import annotations

import argparse
import json
import shutil
import struct
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

여기 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(여기))
sys.path.insert(0, str(여기 / "검사"))
import 제작페이지 as 서버  # noqa: E402
import 승인  # noqa: E402
from 흐름시험 import 페이지, 확인, 실패  # noqa: E402
import 흐름시험  # noqa: E402

캐릭터 = "온천_검사"


def 가짜glb(p: Path, 동작들: list[str]) -> None:
    j = json.dumps({"asset": {"version": "2.0"}, "animations": [{"name": n, "channels": [], "samplers": []} for n in 동작들]}).encode()
    j += b" " * (-len(j) % 4)
    p.write_bytes(b"glTF" + struct.pack("<II", 2, 12 + 8 + len(j)) + struct.pack("<II", len(j), 0x4E4F534A) + j)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--원본", required=True)
    ap.add_argument("--포트", type=int, default=8783)
    ap.add_argument("--남기기", action="store_true")
    인자 = ap.parse_args()
    원본 = Path(인자.원본).resolve()
    뿌리 = Path(tempfile.mkdtemp(prefix="동작시험_"))
    c원, c = 원본 / "01_캐릭터" / 캐릭터, 뿌리 / "01_캐릭터" / 캐릭터
    (c / "제작페이지").mkdir(parents=True)
    작업본 = c / "04_Blender" / "가짜_작업본.blend"
    작업본.parent.mkdir()
    작업본.write_bytes(b"BLENDER-v4 W14 fake")
    모음 = 뿌리 / "_모음"
    모음.mkdir()
    가짜glb(모음 / "UAL1.glb", ["Walk_Loop", "Punch_Jab", "Roll", "Idle_Loop"])
    (모음 / "UAL1.fbx").write_bytes(b"Kaydara FBX fake")
    입력 = c / "03_TRIPO" / "리깅입력" / "입력.glb"
    입력.parent.mkdir(parents=True)
    입력.write_bytes(b"glTF fake")
    그림 = c / "04_Blender" / "찍은것" / "play.png"
    그림.parent.mkdir()
    shutil.copy2(c원 / "04_Blender" / "메시정리_v001" / "10_메시검사" / "모음_조각_1.png", 그림)
    그림글 = 그림.relative_to(뿌리).as_posix()
    상태 = json.loads((c원 / "제작페이지" / "상태.json").read_text(encoding="utf-8"))
    상태["작업본"] = 작업본.relative_to(뿌리).as_posix()
    상태["동작모음"] = {"이름": "UAL1", "glb": str(모음 / "UAL1.glb"), "fbx": str(모음 / "UAL1.fbx")}
    for 칸 in 상태["단계"]:
        칸.update(상태="끝" if 칸["번호"] <= 9 else "입력 없음", 표시=[], 입력=[], 출처="")
    (c / "제작페이지" / "상태.json").write_text(json.dumps(상태, ensure_ascii=False, indent=2), encoding="utf-8")
    유니티 = 뿌리 / "_Unity"
    for 이름, 버전 in ((유니티, "6000.3.7f1"), (뿌리 / "_Unity옛", "2022.3.1f1")):
        (이름 / "ProjectSettings").mkdir(parents=True)
        (이름 / "ProjectSettings" / "ProjectVersion.txt").write_text(f"m_EditorVersion: {버전}\n", encoding="utf-8")
    (유니티 / "Assets" / "Character").mkdir(parents=True)
    (유니티 / "Assets" / "Character" / "OnsenGirl.fbx").write_bytes(b"old")
    (유니티 / "Temp").mkdir()
    (유니티 / "Temp" / "UnityLockfile").write_bytes(b"")
    유니티전 = sorted(str(x) for x in 유니티.rglob("*"))
    print(f"가짜 저장소: {뿌리}")

    서버.로컬 = 뿌리 / "_로컬"
    승인.모드 = "가짜"
    a = 서버.앱(뿌리, 인자.포트)
    s = 서버.서버(("127.0.0.1", 인자.포트), 서버.처리기만들기(a))
    a.서버 = s
    threading.Thread(target=s.serve_forever, kwargs={"poll_interval": 0.2}, daemon=True).start()
    p = 페이지(인자.포트)
    에이전트 = lambda *x: 흐름시험.에이전트(뿌리, *x)
    단10, 단11 = ("--단계", "10"), ("--단계", "11")
    d10, d11 = c / "제작페이지" / "10_애니메이션", c / "제작페이지" / "11_내보내기"

    def 값파일(v) -> str:
        f = 뿌리 / f"값_{time.monotonic_ns()}.json"
        f.write_text(json.dumps(v, ensure_ascii=False), encoding="utf-8")
        return str(f)

    def 옆(n):
        return p.get("/api/동작", 이름=캐릭터, 단계=n)[1]

    def 승인누름(n):
        r = p.get("/api/결정", 이름=캐릭터, 단계=n)[1]["승인"]["요청"]
        return p.post("/api/승인", {"이름": 캐릭터, "단계": n, "파일": r["파일"], "명령": r["명령"], "크레딧": r["크레딧"],
                                   "횟수": r["횟수"], "값해시": r["값해시"]})

    def 실행기다림(n, 초=10.0):
        끝 = time.monotonic() + 초
        while time.monotonic() < 끝:
            r = (p.get("/api/결정", 이름=캐릭터, 단계=n)[1]["승인"] or {}).get("요청") or {}
            if r.get("실행") in ("실행됨", "실패"):
                return r
            time.sleep(0.1)
        return {}

    try:
        p.post("/api/탭", {"캐릭터": 캐릭터, "단계": 10})
        # ---------------------------------------------------------------- 10단계
        v = 옆(10)
        확인(v["모음"]["동작"] == ["Walk_Loop", "Punch_Jab", "Roll", "Idle_Loop"] and not v["모음"]["오류"], f"모음 목록(GLB에서 읽음) → {v['모음']}")
        확인(v["미리"]["상태"] == "못 만듦" and "리깅설정" in v["미리"]["오류"], f"리깅설정 없음 → 미리 보기 못 만듦(원래 인형만) → {v['미리']}")
        def 날것(**q):
            u = f"http://127.0.0.1:{인자.포트}" + urllib.parse.quote("/api/동작/파일") + "?" + urllib.parse.urlencode(q)
            try:
                with urllib.request.urlopen(u) as r:
                    return r.status, r.read()
            except urllib.error.HTTPError as e:
                return e.code, b""
        st, 몸 = 날것(이름=캐릭터, 종류="모음")
        확인(st == 200 and 몸[:4] == b"glTF", "모음 GLB를 줌(원래 인형 미리 보기)")
        st, _ = 날것(이름=캐릭터, 종류="끈것", 해시="../../x")
        확인(st == 400, "미리 보기 파일 해시가 이상하면 400")
        st, r = p.post("/api/동작/옮기기", {"이름": 캐릭터})
        확인(st == 409, "고른 것 없이 옮기기 → 409")
        st, r = p.post("/api/동작/고르기", {"이름": 캐릭터, "고른": ["없는것"]})
        확인(st == 409, "모음에 없는 동작 고르기 → 409")
        st, r = p.post("/api/동작/고르기", {"이름": 캐릭터, "고른": ["Roll", "Walk_Loop", "Punch_Jab"]})
        확인(st == 200 and 옆(10)["고른"] == ["Walk_Loop", "Punch_Jab", "Roll"], "고르기(모음 순서로 저장)")
        st, r = p._요청("POST", "/api/동작/고르기", {"이름": 캐릭터, "탭": "다른탭", "고른": []})
        확인(st == 409, "다른 탭에서는 고르지 못함")
        st, r = p.post("/api/동작/옮기기", {"이름": 캐릭터})
        확인(st == 200 and json.loads((뿌리 / r["파일"]).read_text(encoding="utf-8"))["동작"] == ["Walk_Loop", "Punch_Jab", "Roll"], "옮기기 요청 파일")
        rc, r = 에이전트("동작옮김", 값파일({"동작": [{"원본": "Walk_Loop", "성공": True}]}), *단10)
        확인(rc == 1 and "이름" in r["오류"], "이름 없는 옮김 줄 거부")
        rc, r = 에이전트("동작옮김", 값파일({"동작": [{"원본": "Roll", "성공": False}]}), *단10)
        확인(rc == 1 and "까닭" in r["오류"], "까닭 없는 실패 줄 거부")
        옮김 = {"동작": [{"원본": "Walk_Loop", "이름": "Armature|AM40_S70_Walk_Loop", "성공": True, "자동처리": ["보폭"], "장수": 33, "교차수": 2, "관통장": [5], "새관통": False, "장초당": 24, "시작장": 1},
                        {"원본": "Punch_Jab", "이름": "Armature|AM40_UAL_Punch_Jab", "성공": True, "장수": 30, "교차수": 4, "관통장": [12, 13], "새관통": True},
                        {"원본": "Roll", "성공": False, "까닭": "뼈 이름이 대응표에 없음"}]}
        rc, r = 에이전트("동작옮김", 값파일(옮김), "--단계", "9")
        확인(rc == 1, "동작옮김은 10단계에서만")
        rc, r = 에이전트("동작옮김", 값파일(옮김), *단10)
        확인(rc == 0 and r["실패"] == ["Roll"] and r["새관통"] == ["Punch_Jab"], f"옮김 기록 → {r}")
        알림 = json.loads((d10 / "알림.json").read_text(encoding="utf-8"))
        확인(알림["종류"] == "막힘" and "Roll" in 알림["글"], f"옮기지 못한 것 → 알림 막힘 → {알림['글']}")
        v = 옆(10)
        확인(any("Roll" in x for x in v["모자람"]), f"끝나는 조건: 고른 동작 중 실패 → {v['모자람']}")
        lv = p.get("/api/리깅", 이름=캐릭터, 단계=10)[1]
        확인([x["이름"] for x in lv["교차"]["동작"]] == ["Armature|AM40_S70_Walk_Loop", "Armature|AM40_UAL_Punch_Jab"] and lv["새관통"] == ["Armature|AM40_UAL_Punch_Jab"],
             "10단계 시간 막대 값(옮김 기록의 성공한 동작, 새 관통)")
        p.post("/api/동작/고르기", {"이름": 캐릭터, "고른": ["Walk_Loop", "Punch_Jab"]})
        확인(옆(10)["모자람"] == [], f"고른 동작 모두 성공 → 끝나는 조건 채움 → {옆(10)['모자람']}")

        # 리포트: 쪽(동작 / 리깅), 9단계로 넘어감
        h = p.get("/api/상태", 이름=캐릭터)[1]["작업본해시"]
        표 = [{"번호": "1", "누가": "사용자", "종류": "관통", "자리": {"파츠": [], "면": {}, "동작": {"이름": "Armature|AM40_UAL_Punch_Jab", "시작장": 12, "끝장": 14}, "구간": True}, "메모": "소매", "작업본해시": h},
              {"번호": "2", "누가": "사용자", "종류": "관통", "자리": {"파츠": [], "면": {}}, "메모": "", "작업본해시": h}]
        st, r = p.post("/api/보내기", {"이름": 캐릭터, "단계": 10, "표시": 표})
        확인(st == 400, "면도 구간도 없는 10단계 표시 거부")
        st, r = p.post("/api/보내기", {"이름": 캐릭터, "단계": 10, "표시": 표[:1]})
        묶 = r["파일"].split("/")[-1]
        확인(st == 200 and "처리 안 된" in " ".join(옆(10)["모자람"]), "보낸 묶음이 처리 전이면 끝나는 조건 모자람")
        에이전트("받기", 묶, *단10)
        rc, r = 에이전트("처리", 묶, 값파일({"결과": [{"번호": "1", "처리": "안 고침", "이유": "가중치"}]}), *단10)
        확인(rc == 1 and "쪽" in r["오류"], "10단계 처리에 쪽이 없으면 거부")
        rc, r = 에이전트("처리", 묶, 값파일({"결과": [{"번호": "1", "처리": "안 고침", "이유": "가중치 쪽", "쪽": "리깅"}]}), *단10)
        넘 = p.get("/api/리깅", 이름=캐릭터, 단계=9)[1]["넘어온"]
        확인(rc == 0 and len(넘) == 1 and 넘[0]["동작"]["시작장"] == 12 and 넘[0]["메모"] == "소매", f"리깅 쪽 → 9단계 '10단계에서 넘어온 리포트' → {넘}")

        # TRIPO 동작 생성(승인)
        rc, r = 에이전트("동작생성요청", "walk,run", *단10)
        확인(rc == 1 and "작업 번호" in r["오류"], "8단계 실행 없이 TRIPO 동작 요청 → 거부")
        rc, r = 에이전트("동작생성요청", "a,b,c,d,e,f", *단10)
        확인(rc == 1 and "5" in r["오류"], "프리셋 6개 → 거부")
        에이전트("리깅요청", 입력.relative_to(뿌리).as_posix(), "--단계", "8")
        p.post("/api/리깅/리그체크", {"이름": 캐릭터})
        승인누름(8)
        실행기다림(8)
        확인(p.get("/api/결정", 이름=캐릭터, 단계=10)[1]["승인"]["요청"] is None, "요청 전 10단계 승인 상자 값 없음(화면에서 숨김)")
        rc, r = 에이전트("동작생성요청", "walk,run", *단10)
        확인(rc == 0 and r["명령"].startswith("tripo anim retarget") and "preset:walk preset:run" in r["명령"] and r["크레딧"] == "모름" and r["횟수"] == 2,
             f"TRIPO 동작 요청 → {r.get('명령', r)}")
        st, r = 승인누름(10)
        확인(st == 200 and 실행기다림(10).get("실행") == "실행됨" and 옆(10)["생성실행"]["실행"] == "실행됨", "TRIPO 동작 승인 → 가짜 실행됨")

        # ---------------------------------------------------------------- 11단계
        v = 옆(11)
        확인("경로" in v["Unity"]["잠김"], f"경로 없음 → 잠김 → {v['Unity']['잠김']}")
        st, r = p.post("/api/내보내기/요청", {"이름": 캐릭터})
        확인(st == 409 and "잠김" in r["오류"], "경로 없이 내보내기 → 409")
        st, r = p.post("/api/내보내기/경로", {"이름": 캐릭터, "경로": "상대/경로", "넣을이름": "OnsenGirl"})
        확인(st == 400, "상대 경로 거부")
        st, r = p.post("/api/내보내기/경로", {"이름": 캐릭터, "경로": str(뿌리 / "_없음"), "넣을이름": "OnsenGirl"})
        확인(st == 409, "Unity 프로젝트가 아닌 폴더 거부")
        st, r = p.post("/api/내보내기/경로", {"이름": 캐릭터, "경로": str(유니티), "넣을이름": "온천"})
        확인(st == 400, "넣을 이름이 영어가 아니면 거부")
        st, r = p.post("/api/내보내기/경로", {"이름": 캐릭터, "경로": str(뿌리 / "_Unity옛"), "넣을이름": "OnsenGirl"})
        확인(st == 200 and "버전" in r["Unity"]["잠김"], "버전이 다르면 저장은 되고 잠김")
        st, r = p.post("/api/내보내기/요청", {"이름": 캐릭터})
        확인(st == 409 and "버전" in r["오류"], "버전 다름 → 내보내기 409")
        st, r = p.post("/api/내보내기/경로", {"이름": 캐릭터, "경로": str(유니티), "넣을이름": "OnsenGirl"})
        u = r["Unity"]
        확인(st == 200 and u["버전같음"] and u["열림"] and u["같은이름"] == ["Assets/Character/OnsenGirl.fbx"] and not u["잠김"], f"경로 고르기 → {u}")
        확인(json.loads((c / "제작페이지" / "상태.json").read_text(encoding="utf-8"))["Unity"]["넣을이름"] == "OnsenGirl", "상태.json의 Unity에 저장")
        st, r = p.post("/api/내보내기/요청", {"이름": 캐릭터})
        확인(st == 409 and "덮어쓸까요" in r["오류"], "같은 이름 → 덮어쓸지 물음(409)")
        st, r = p.post("/api/내보내기/요청", {"이름": 캐릭터, "덮어쓰기": True})
        req = json.loads((뿌리 / r["파일"]).read_text(encoding="utf-8")) if st == 200 else {}
        확인(st == 200 and req["덮어쓰기"] and req["Unity열림"] and req["동작"] == ["Armature|AM40_S70_Walk_Loop", "Armature|AM40_UAL_Punch_Jab"], "덮어쓰기 요청(열림·동작 목록)")
        확인("열려" in json.loads((d11 / "알림.json").read_text(encoding="utf-8"))["글"], "Unity가 열려 있음 → 알림")
        st, r = p.post("/api/내보내기/봄", {"이름": 캐릭터})
        확인(st == 409, "그림 없이 봄 → 409")
        결과 = {"요청파일": sorted(d11.glob("요청_*.json"))[-1].name,
                "파일": [{"경로": "Assets/Character/OnsenGirl.fbx", "종류": "FBX"}],
                "검사": [{"항목": "Humanoid 대응", "상태": "경고", "글": "새끼손가락"}], "표시": {"7-5": True, "7-6": True, "7-7": False}, "그림": [그림글]}
        rc, r = 에이전트("내보내기결과", 값파일(결과), *단11)
        확인(rc == 1 and "사본" in r["오류"], "덮어쓴 요청인데 사본이 없으면 거부")
        rc, r = 에이전트("내보내기결과", 값파일(dict(결과, 요청파일="요청_없음.json", 사본="x")), *단11)
        확인(rc == 1 and "요청파일" in r["오류"], "다른 요청 파일 → 거부")
        rc, r = 에이전트("내보내기결과", 값파일(dict(결과, 사본="_Unity_사본/OnsenGirl.fbx")), *단11)
        확인(rc == 0, "검사표 씀")
        모 = 옆(11)["모자람"]
        확인(any("7-7" in x for x in 모) and any("봄" in x for x in 모) and not any("실패" in x for x in 모), f"7-7 거짓·봄 없음 → 모자람(경고는 막지 않음) → {모}")
        rc, r = 에이전트("내보내기결과", 값파일(dict(결과, 사본="_Unity_사본/OnsenGirl.fbx", 표시={"7-5": True, "7-6": True, "7-7": True})), *단11)
        st, r = p.post("/api/내보내기/봄", {"이름": 캐릭터})
        확인(st == 200 and 옆(11)["모자람"] == [] and 옆(11)["봄"], f"봄 → 끝나는 조건 채움 → {옆(11)['모자람']}")
        작업본.write_bytes(b"BLENDER-v4 W14 fake changed")
        확인(any("오래됨" in x for x in 옆(11)["모자람"]) and any("오래됨" in x for x in 옆(10)["모자람"]), "작업본이 바뀌면 옮김·검사표가 오래됨")
        확인(sorted(str(x) for x in 유니티.rglob("*")) == 유니티전 and (유니티 / "Assets" / "Character" / "OnsenGirl.fbx").read_bytes() == b"old",
             "서버는 Unity 프로젝트에 아무것도 쓰지 않음")
    finally:
        s.shutdown()
        if not 인자.남기기:
            shutil.rmtree(뿌리, ignore_errors=True)
    print("모두 통과" if not 실패 else f"실패 {len(실패)}개")
    return 1 if 실패 else 0


if __name__ == "__main__":
    sys.exit(main())
