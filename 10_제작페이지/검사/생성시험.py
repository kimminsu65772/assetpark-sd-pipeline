"""2·4·5·6단계(TRIPO 생성 계열) 시험 — 가짜 실행만 (작업 묶음 W10, 기능명세 2부 14·16·17·18·24절)

    python 10_제작페이지/검사/생성시험.py --원본 <저장소 루트> [--포트 8779] [--남기기]

- 스크래치(임시) 폴더에 가짜 저장소를 만든다: 원본의 온천 검사 `상태.json`·캐릭터 노트·TRIPO 입력 네 장(PNG),
  `SSOT/단계/2_TRIPO.md`, `SSOT/도구/TRIPO입력_검사.py`만 **복사**한다. 작업본은 작은 가짜 파일, 입력 GLB는 머리만 있는 가짜 GLB.
  원본에 쓰지 않음, TRIPO에 요청하지 않음, 크레딧을 쓰지 않음.
- 서버를 이 프로세스 안에서 다른 포트에 켠다(사용자의 8765는 건드리지 않음). 실행 모드는 가짜로 고정.
- 일부러 일으키는 예외(2부 24절): 입력 없음, 입력 검사 실패, 입력 파일 없음, 삼각형 8만 넘음, 확인 값 미달.
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
from pathlib import Path

여기 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(여기))
sys.path.insert(0, str(여기 / "검사"))
import 제작페이지 as 서버  # noqa: E402
import 승인  # noqa: E402
import 생성단계  # noqa: E402
from 흐름시험 import 페이지, 확인, 실패  # noqa: E402
import 흐름시험  # noqa: E402

캐릭터 = "온천_검사"


def 가짜glb(p: Path, 삼각형: int) -> str:
    """JSON 덩어리만 있는 GLB(삼각형 수를 accessor count로)."""
    g = {"asset": {"version": "2.0"}, "accessors": [{"count": 삼각형 * 3, "componentType": 5125, "type": "SCALAR"},
                                                    {"count": 3, "componentType": 5126, "type": "VEC3"}],
         "meshes": [{"primitives": [{"attributes": {"POSITION": 1}, "indices": 0}]}]}
    j = json.dumps(g).encode()
    j += b" " * (-len(j) % 4)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(j)) + struct.pack("<II", len(j), 0x4E4F534A) + j)
    return p.as_posix()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--원본", required=True)
    ap.add_argument("--포트", type=int, default=8779)
    ap.add_argument("--남기기", action="store_true")
    인자 = ap.parse_args()
    원본 = Path(인자.원본).resolve()
    뿌리 = Path(tempfile.mkdtemp(prefix="생성시험_"))
    c원 = 원본 / "01_캐릭터" / 캐릭터
    c = 뿌리 / "01_캐릭터" / 캐릭터
    (c / "제작페이지").mkdir(parents=True)
    작업본 = c / "04_Blender" / "가짜_작업본.blend"
    작업본.parent.mkdir()
    작업본.write_bytes(b"BLENDER-v4 W10 fake")
    입력폴더 = c / "03_TRIPO" / "실험_001_입력이미지" / "후보_A"
    입력폴더.mkdir(parents=True)
    for f in sorted((c원 / "03_TRIPO" / "실험_001_입력이미지").rglob("*.png"))[:4]:
        shutil.copy2(f, 입력폴더 / f.name)
    네장 = [f.relative_to(뿌리).as_posix() for f in sorted(입력폴더.glob("*.png"))]
    상태 = json.loads((c원 / "제작페이지" / "상태.json").read_text(encoding="utf-8"))
    상태["작업본"] = 작업본.relative_to(뿌리).as_posix()
    for 칸 in 상태["단계"]:
        칸.update(상태="끝" if 칸["번호"] == 1 else "입력 없음", 표시=[], 입력=[], 출처="")
    (c / "제작페이지" / "상태.json").write_text(json.dumps(상태, ensure_ascii=False, indent=2), encoding="utf-8")
    for x in ("SSOT/캐릭터/온천_검사.md", "SSOT/단계/2_TRIPO.md", "SSOT/도구/TRIPO입력_검사.py"):
        (뿌리 / x).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(원본 / x, 뿌리 / x)
    print(f"가짜 저장소: {뿌리}")

    서버.로컬 = 뿌리 / "_로컬"
    승인.가짜잔액파일 = 서버.로컬 / "TRIPO잔액_가짜.json"
    승인.진짜잔액파일 = 서버.로컬 / "TRIPO잔액.json"
    승인.모드, 승인.가짜결과, 승인.가짜초 = "가짜", "성공", 0.3
    a = 서버.앱(뿌리, 인자.포트)
    s = 서버.서버(("127.0.0.1", 인자.포트), 서버.처리기만들기(a))
    a.서버 = s
    threading.Thread(target=s.serve_forever, kwargs={"poll_interval": 0.2}, daemon=True).start()
    p = 페이지(인자.포트)
    에이전트 = lambda *x: 흐름시험.에이전트(뿌리, *x)

    def 값파일(v) -> str:
        f = 뿌리 / f"값_{time.monotonic_ns()}.json"
        f.write_text(json.dumps(v, ensure_ascii=False), encoding="utf-8")
        return str(f)

    def 결정(n):
        return p.get("/api/결정", 이름=캐릭터, 단계=n)[1]

    def 승인누름(n):
        r = 결정(n)["승인"]["요청"]
        return p.post("/api/승인", {"이름": 캐릭터, "단계": n, "파일": r["파일"], "명령": r["명령"], "크레딧": r["크레딧"],
                                   "횟수": r["횟수"], "값해시": r["값해시"]})

    def 기다리기(n, 초=10.0):
        끝 = time.monotonic() + 초
        while time.monotonic() < 끝:
            r = (결정(n).get("승인") or {}).get("요청") or {}
            if r.get("실행") in ("실행됨", "실패"):
                return r
            time.sleep(0.1)
        return {}

    def 옆(n):
        return p.get("/api/생성단계", 이름=캐릭터, 단계=n)

    def 끝누름(n, 결정값="이 단계 끝"):
        return p.post("/api/결정", {"이름": 캐릭터, "단계": n, "결정": 결정값})

    try:
        p.post("/api/탭", {"캐릭터": 캐릭터, "단계": 2})
        확인(옆(3)[0] == 400, "옆 기둥은 2·4·5·6단계만(3단계 → 400)")
        for n in 생성단계.단계들:
            st, v = 옆(n)
            확인(st == 200 and v["기본"]["틀"].startswith("tripo "), f"{n}단계 옆 기둥: 기본 명령 '{v['기본']['틀'][:48]}…'")

        # ---- 2단계
        rc, v = 에이전트("생성요청", "--단계", "2")
        확인(rc == 1 and "검사 실패" in v.get("오류", ""), f"2단계: 입력이 없으면 생성요청 거부 → {v.get('오류', '')[:50]}")
        a.단계상태쓰기(캐릭터, 2, {"입력": 네장, "출처": "이 페이지(1단계 시트 승인)"})
        rc, v = 에이전트("생성요청", "--단계", "2")
        확인(rc == 0 and v["크레딧"] == "모름", "2단계: 입력 네 장 검사 통과 → 생성요청 씀(크레딧 '모름')")
        r = 결정(2)["승인"]["요청"]
        확인(all(x in r["명령"] for x in 네장) and "face_limit=5000" in r["명령"] and "texture=false" in r["명령"],
             "2단계 명령: 네 장 + P2·쿼드·면 5,000·텍스처 끔")
        확인(not 결정(2)["승인"]["막는이유"], "2단계: 승인 막지 않음")
        뺀것 = 뿌리 / 네장[3]
        임시 = 뺀것.with_suffix(".bak")
        뺀것.rename(임시)
        확인("검사 실패" in 결정(2)["승인"]["막는이유"], f"2단계: 입력 한 장이 없어지면 승인 잠김 → {결정(2)['승인']['막는이유'][:50]}")
        st, v = 승인누름(2)
        확인(st == 409, "2단계: 잠긴 채 승인을 보내면 서버가 거부(409)")
        임시.rename(뺀것)
        st, v = 옆(2)
        확인(len(v["모자람"]) == 2, f"2단계 끝나는 조건(실행 전): {v['모자람']}")
        st, v = 승인누름(2)
        r = 기다리기(2)
        확인(st == 200 and r.get("실행") == "실행됨" and r.get("가짜"), "2단계: 승인 → 가짜 실행 → 실행됨")
        st, v = 끝누름(2)
        확인(not v.get("됨") and any("2-2" in x for x in v.get("모자람", [])), f"2단계: 확인 없이 '이 단계 끝' → 모자람 {v.get('모자람')}")
        rc, v = 에이전트("생성확인", 값파일({"파일구성": "FBX 1개"}), "--단계", "2")
        확인(rc == 1 and "빠진 항목" in v.get("오류", ""), "2단계 생성확인: 빠진 항목이 있으면 거부")
        rc, v = 에이전트("생성확인", 값파일({"파일구성": "FBX 1개", "면수": 11065, "방향": "앞 +x", "몰래": 1}), "--단계", "2")
        확인(rc == 1 and "모르는 항목" in v.get("오류", ""), "2단계 생성확인: 모르는 항목 거부")
        rc, v = 에이전트("생성확인", 값파일({"파일구성": "FBX 1개", "면수": 11065, "방향": "앞 +x(TRIPO 원본)"}), "--단계", "2")
        확인(rc == 0 and v["모자람"] == [], "2단계 생성확인 씀 → 모자람 없음")
        st, v = 끝누름(2)
        확인(v.get("됨") and v.get("상태") == "끝", f"2단계: '이 단계 끝' → {v.get('상태')}")

        # ---- 4단계
        rc, v = 에이전트("생성요청", "--단계", "4")
        확인(rc == 1 and "입력 파일" in v.get("오류", ""), "4단계: 입력 파일 없이 생성요청 거부")
        g4 = Path(가짜glb(c / "제작페이지" / "04_리토폴로지" / "보낼것" / "입력.glb", 20257)).relative_to(뿌리).as_posix()
        rc, v = 에이전트("생성요청", g4, "--단계", "4")
        r = 결정(4)["승인"]["요청"]
        확인(rc == 0 and r["크레딧"] == 35 and "mesh decimate" in r["명령"] and "--model v3.0" in r["명령"] and "--face-limit 20000" in r["명령"],
             "4단계 요청: decimate v3.0 면 20,000, 35크레딧")
        (뿌리 / g4).rename(뿌리 / (g4 + ".bak"))
        확인("입력 파일이 없습니다" in 결정(4)["승인"]["막는이유"], "4단계: 요청의 입력 파일이 없어지면 승인 잠김")
        (뿌리 / (g4 + ".bak")).rename(뿌리 / g4)
        st, v = 승인누름(4)
        확인(st == 200, f"4단계: 승인 보냄 → {st} {v.get('오류', '')}")
        확인(기다리기(4).get("실행") == "실행됨", "4단계: 가짜 실행됨")
        rc, v = 에이전트("생성확인", 값파일({"면수전": 20257, "면수후": 25000, "파츠수전": 4, "파츠수후": 3, "대칭점검": False, "접합부점검": True}), "--단계", "4")
        확인(rc == 0 and len(v["모자람"]) == 3, f"4단계: 예산 넘음·파츠 수 바뀜·대칭 안 봄 → {v['모자람']}")
        st, v = 끝누름(4)
        확인(not v.get("됨") and len(v.get("모자람", [])) == 3, "4단계: '이 단계 끝' → 모자람 3")
        st, v = 끝누름(4, "그래도 끝")
        확인(v.get("상태") == "끝(조건 미달)", f"4단계: '그래도 끝' → {v.get('상태')}")
        rc, v = 에이전트("생성확인", 값파일({"면수전": 20257, "면수후": 19980, "파츠수전": 4, "파츠수후": 4, "대칭점검": True, "접합부점검": True}), "--단계", "4")
        확인(rc == 0 and v["모자람"] == [], "4단계: 고친 확인 → 모자람 없음")

        # ---- 5단계
        g5 = Path(가짜glb(c / "제작페이지" / "05_텍스처생성" / "보낼것" / "입력.glb", 19980)).relative_to(뿌리).as_posix()
        rc, v = 에이전트("생성요청", g5, "--단계", "5")
        r = 결정(5)["승인"]["요청"]
        확인(rc == 0 and r["크레딧"] == 20 and "model texture" in r["명령"] and "--texture-quality detailed -p pbr=false -p delight=true" in r["명령"],
             "5단계 요청: SSOT 'TRIPO텍스처명령값' 그대로, 20크레딧")
        승인누름(5)
        기다리기(5)
        rc, v = 에이전트("생성확인", 값파일({"받은그림": [g5], "정점자리같음": True, "형태": "같음", "UV": "새로 펴짐", "객체구성": "4개"}), "--단계", "5")
        확인(rc == 1 and "PNG" in v.get("오류", ""), "5단계 생성확인: 받은그림이 그림이 아니면 거부")
        rc, v = 에이전트("생성확인", 값파일({"받은그림": [네장[0]], "정점자리같음": False, "형태": "같음", "UV": "새로 펴짐", "객체구성": "4개"}), "--단계", "5")
        확인(rc == 0 and any("정점 자리" in x for x in v["모자람"]), "5단계: 정점 자리가 다르면 끝나지 않음")
        st, v = 옆(5)
        확인(v["확인"]["받은그림"] == [네장[0]] and len(v["입력그림"]) == 4, "5단계 옆 기둥: 받은 그림 1장, 입력 그림 4장")

        # ---- 6단계
        큰 = Path(가짜glb(c / "제작페이지" / "06_SmartUV" / "보낼것" / "큰.glb", 90000)).relative_to(뿌리).as_posix()
        rc, v = 에이전트("생성요청", 큰, "--단계", "6")
        확인(rc == 1 and "8만" in v.get("오류", ""), "6단계: 입력 삼각형 9만 → 생성요청 거부")
        g6 = Path(가짜glb(c / "제작페이지" / "06_SmartUV" / "보낼것" / "입력.glb", 19980))
        rc, v = 에이전트("생성요청", g6.relative_to(뿌리).as_posix(), "--단계", "6")
        r = 결정(6)["승인"]["요청"]
        확인(rc == 0 and r["크레딧"] == 20 and "mesh uv" in r["명령"] and "--no-bake" not in r["명령"], "6단계 요청: mesh uv, 그림 옮기기 켬(--no-bake 없음), 20크레딧")
        가짜glb(g6, 81000)   # 요청 뒤에 입력이 바뀜
        확인("8만" in 결정(6)["승인"]["막는이유"], "6단계: 요청 뒤 입력이 8만 넘으면 승인 잠김")
        가짜glb(g6, 19980)
        승인누름(6)
        기다리기(6)
        rc, v = 에이전트("생성확인", 값파일({"겹침": 2, "최소간격": 4, "UV범위안": False, "뒤집힌삼각형": 1, "그림비교통과": False,
                                       "격자직접봄": False, "가다듬음": True}), "--단계", "6")
        확인(rc == 0 and len(v["모자람"]) == 7, f"6단계: 수치 불합격 7가지 → {len(v['모자람'])}")
        rc, v = 에이전트("생성확인", 값파일({"겹침": 0, "최소간격": 8, "UV범위안": True, "뒤집힌삼각형": 0, "그림비교통과": True,
                                       "격자직접봄": True}), "--단계", "6")
        확인(rc == 0 and v["모자람"] == [], "6단계: 합격 수치 → 모자람 없음")

        # ---- 가져온 모델(2부 14절: 2단계는 '가져옴'으로 끝)
        a.단계상태쓰기(캐릭터, 2, {"출처": "TRIPO 웹"})
        확인(생성단계.완료모자람(a, 캐릭터, 2) == [], "2단계: 출처가 'TRIPO 웹'(가져옴)이면 끝나는 조건 없음")
        확인(생성단계.glb삼각형(Path("없는파일.glb")) is None, "GLB가 아니면 삼각형 수 None")
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
