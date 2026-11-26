"""파일 가져오기 시험 (W08 완료 조건: 그림·GLB·FBX·blend 하나씩, 방향이 틀린 모델 하나, 열리지 않는 파일 하나).

    python 검사/가져오기시험.py --원본 <저장소 루트> [--포트 8781] [--남기기]

- 스크래치(임시) 폴더에 가짜 저장소를 만든다: 온천 검사의 작업본·상태.json·시험 파일을 **복사**만 한다(원본에 쓰지 않음).
- 서버를 이 프로세스 안에서 다른 포트로 켜고, 브라우저처럼 HTTP로 올리기·검사·넣기를 부른다. 모델 검사는 진짜 Blender를 쓴다.
- 하나라도 실패하면 종료 코드 1.
"""
import argparse
import hashlib
import http.client
import json
import shutil
import sys
import tempfile
import threading
import time
import urllib.parse
from pathlib import Path

여기 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(여기))
import 제작페이지 as 서버  # noqa: E402
import 가져오기  # noqa: E402

캐릭터 = "온천_검사"
작업본상대 = "01_캐릭터/온천_검사/04_Blender/온천검사_작업본.blend"
시험파일 = {
    "그림.png": "01_캐릭터/온천_검사/01_컨셉아트/생성_v001/_격자_머리.png",
    "텍스처모델.glb": "01_캐릭터/온천_검사/03_TRIPO/실험_003_텍스처4K/tripo-out/detailed/tripo-out/texture-4-1f6a46ab/model.glb",
    "리깅.fbx": "01_캐릭터/온천_검사/03_TRIPO/실험_004_오토리깅/tripo-out/rig/tripo-out/rig-8d170cb5/model.fbx",
    "작업본사본.blend": 작업본상대,
    "방향틀림.glb": "01_캐릭터/온천_검사/03_TRIPO/실험_004_오토리깅/02_체크시험/원래방향.glb",   # TRIPO 원본 방향(앞 +x)
}
실패 = []


def 확인(조건, 글, 덧=None):
    print(("통과 " if 조건 else "실패 ") + 글 + (f"  ← {덧}" if 덧 is not None and not 조건 else ""), flush=True)
    if not 조건:
        실패.append(글)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


class 페이지:
    def __init__(self, 포트):
        self.포트 = 포트
        self.탭 = "가져오기시험탭"

    def _요청(self, 방법, 경로, 몸=None, 머리=None, 날것=None):
        c = http.client.HTTPConnection("127.0.0.1", self.포트, timeout=120)
        h = {"Host": f"127.0.0.1:{self.포트}"}
        b = None
        if 몸 is not None:
            b = json.dumps(몸, ensure_ascii=False).encode()
            h.update({"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{self.포트}"})
        if 날것 is not None:
            b = 날것
            h.update({"Content-Type": "application/octet-stream", "Origin": f"http://127.0.0.1:{self.포트}"})
        h.update(머리 or {})
        길, _, 질문 = 경로.partition("?")
        c.request(방법, urllib.parse.quote(길) + (f"?{urllib.parse.quote(질문, safe='=&%+')}" if 질문 else ""), body=b, headers=h)
        r = c.getresponse()
        몸글 = r.read()
        try:
            return r.status, json.loads(몸글 or b"{}")
        except ValueError:
            return r.status, {"_바이트": len(몸글)}

    def get(self, 경로, **질문):
        return self._요청("GET", 경로 + "?" + urllib.parse.urlencode(질문))

    def post(self, 경로, 몸):
        return self._요청("POST", 경로, dict(몸, 탭=self.탭))

    def 올리기(self, 파일: Path, 이름=None, 큰파일=False, 머리=None):
        q = urllib.parse.urlencode({"이름": 캐릭터, "파일": 이름 or 파일.name, "큰파일": "1" if 큰파일 else ""})
        return self._요청("POST", f"/api/가져오기/올리기?{q}", 날것=파일.read_bytes(), 머리=머리)

    def 검사기다리기(self, 번호, 초=180):
        끝 = time.time() + 초
        while time.time() < 끝:
            s, v = self.get("/api/가져오기", 번호=번호)
            if s != 200 or v.get("상태") != "검사 중":
                return v
            time.sleep(0.5)
        return {"상태": "시간 넘음"}


def 단계줄(p: 페이지, 번호):
    return p.get("/api/상태", 이름=캐릭터)[1]["단계"][번호 - 1]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--원본", required=True)
    ap.add_argument("--포트", type=int, default=8781)
    ap.add_argument("--남기기", action="store_true")
    인자 = ap.parse_args()
    원본 = Path(인자.원본).resolve()
    뿌리 = Path(tempfile.mkdtemp(prefix="가져오기시험_"))
    c원 = 원본 / "01_캐릭터" / 캐릭터
    c = 뿌리 / "01_캐릭터" / 캐릭터
    (c / "04_Blender").mkdir(parents=True)
    shutil.copy2(원본 / 작업본상대, 뿌리 / 작업본상대)
    (c / "제작페이지").mkdir(parents=True)
    상태 = json.loads((c원 / "제작페이지" / "상태.json").read_text(encoding="utf-8"))
    for 칸 in 상태["단계"]:
        칸.update({"상태": "입력 없음", "입력": [], "표시": [], "출처": ""})
    (c / "제작페이지" / "상태.json").write_text(json.dumps(상태, ensure_ascii=False, indent=2), encoding="utf-8")
    (뿌리 / "SSOT" / "캐릭터").mkdir(parents=True)
    shutil.copy2(원본 / "SSOT" / "캐릭터" / f"{캐릭터}.md", 뿌리 / "SSOT" / "캐릭터" / f"{캐릭터}.md")
    자료 = 뿌리 / "_시험파일"
    자료.mkdir()
    for 이름, 상대 in 시험파일.items():
        shutil.copy2(원본 / 상대, 자료 / 이름)
    (자료 / "깨진.glb").write_bytes(b"glTF" + bytes(range(256)) * 8)          # 머리만 GLB, 몸은 쓰레기
    (자료 / "가짜그림.png").write_bytes(b"this is not a png")                   # 확장자만 PNG
    (자료 / "메모.txt").write_text("x", encoding="utf-8")
    # 앞을 판단할 수 없는 모델: 발 쪽이 어느 쪽으로도 나오지 않는 길쭉한 상자(OBJ)
    v = [(x, y, z) for z in (0, 1.0) for y in (-0.1, 0.1) for x in (-0.15, 0.15)]
    f = [(1, 2, 4, 3), (5, 7, 8, 6), (1, 5, 6, 2), (3, 4, 8, 7), (1, 3, 7, 5), (2, 6, 8, 4)]
    (자료 / "상자.obj").write_text("".join(f"v {x} {y} {z}\n" for x, y, z in v) + "".join("f " + " ".join(map(str, q)) + "\n" for q in f), encoding="utf-8")
    원본해시 = {n: sha(c원.parent.parent / 상대) for n, 상대 in 시험파일.items()}
    print(f"가짜 저장소: {뿌리}")

    서버.로컬 = 뿌리 / "_로컬"
    a = 서버.앱(뿌리, 인자.포트)
    s = 서버.서버(("127.0.0.1", 인자.포트), 서버.처리기만들기(a))
    a.서버 = s
    threading.Thread(target=s.serve_forever, kwargs={"poll_interval": 0.2}, daemon=True).start()
    p = 페이지(인자.포트)
    try:
        p.post("/api/탭", {"캐릭터": 캐릭터, "단계": 1})

        def 가져와(파일, **덧):
            st, v = p.올리기(자료 / 파일)
            확인(st == 200 and v.get("번호"), f"{파일}: 올리기 200", (st, v))
            return p.검사기다리기(v["번호"]) if st == 200 else v

        def 넣어(v, 단계, 출처="TRIPO 웹", **덧):
            return p.post("/api/가져오기/넣기", dict({"번호": v["번호"], "이름": 캐릭터, "단계": 단계, "출처": 출처}, **덧))

        # ---- 받지 않는 것
        st, v = p.올리기(자료 / "메모.txt")
        확인(st == 415, "txt는 받지 않음(415)", (st, v))
        try:
            st, v = p.올리기(자료 / "그림.png", 머리={"Origin": "http://evil.example"})
        except ConnectionError:   # 서버가 몸을 읽지 않고 403을 보낸 뒤 닫으면 보내던 쪽은 끊김으로 봄
            st, v = 403, {}
        확인(st == 403 and not list((서버.로컬 / "가져오기").glob("*")), "다른 출처의 올리기는 거부(403), 받아 둔 것 없음", (st, v))
        st, v = p._요청("POST", "/api/가져오기/올리기?" + urllib.parse.urlencode({"이름": 캐릭터, "파일": "a.png"}), 날것=b"x", 머리={"Content-Type": "text/plain"})
        확인(st == 415, "text/plain 몸은 거부(415)", (st, v))

        # ---- 1. 그림
        v = 가져와("그림.png")
        확인(v.get("상태") == "검사됨" and v["검사"].get("폭", 0) > 0, "그림: 열림·크기", v.get("검사"))
        확인(v.get("추정") == 1, "그림: 1단계로 추정", v.get("추정"))
        st, g = p._요청("GET", f"/api/가져오기/그림?번호={v['번호']}&면=원본")
        확인(st == 200, "그림: 미리 보기 내줌", st)
        st, r = 넣어(v, 1, "다른 곳")
        확인(st == 200, "그림: 넣기", r)
        줄 = 단계줄(p, 1)
        보존 = 뿌리 / r["폴더"] / "그림.png"
        확인(줄["입력"] == [r["입력"]] and 줄["상태"] == "준비됨" and "다른 곳" in (줄["출처"] or ""), "그림: 1단계 입력·출처·준비됨", 줄)
        확인(r["폴더"].startswith("01_캐릭터/온천_검사/03_TRIPO/가져온것_") and 보존.is_file() and sha(보존) == 원본해시["그림.png"], "그림: 원본 그대로 03_TRIPO/가져온것_시각/에 보존")
        확인(not (서버.로컬 / "가져오기" / v["번호"]).exists(), "그림: 받아 둔 임시 파일 지움")

        # ---- 2. GLB(텍스처, 작업본 방향으로 올렸던 것 → 그대로)
        v = 가져와("텍스처모델.glb")
        g = v.get("검사") or {}
        확인(v.get("상태") == "검사됨" and g.get("텍스처수", 0) > 0 and g.get("UV있는파츠") == g.get("파츠수"), "GLB: 열림·텍스처·UV", g)
        확인(v.get("추정") == 5, "GLB: 텍스처 → 5단계로 추정", v.get("추정"))
        확인(g.get("앞") == "-y" and len(v.get("그림", [])) == 4, "GLB: 앞 -y 추정, 네 방향 그림", (g.get("앞"), g.get("발끝")))
        st, r = 넣어(v, 5, "TRIPO 웹", 작업번호="1f6a46ab")
        확인(st == 200 and r["입력"].endswith("/텍스처모델.glb"), "GLB: 앞이 -y면 원본 사본을 그대로 입력으로", r)
        줄 = 단계줄(p, 5)
        확인("작업 1f6a46ab" in (줄["출처"] or "") and "생성 설정 모름" in (줄["출처"] or ""), "GLB: 출처 'TRIPO 웹(작업 …), 웹에서 가져옴, 생성 설정 모름'", 줄["출처"])

        # ---- 2b. 방향이 틀린 모델(TRIPO 원본 방향 GLB, 앞 +x)
        v = 가져와("방향틀림.glb")
        g = v.get("검사") or {}
        확인(g.get("앞") == "+x", "방향 틀림: 앞 +x(TRIPO 원본 방향)로 추정", (g.get("앞"), g.get("발끝")))
        st, r = 넣어(v, 4, "다른 곳")
        확인(st == 200 and r["입력"].endswith("되돌림_방향틀림.blend"), "방향 틀림: 되돌린 사본(blend)을 입력으로", r)
        기록 = json.loads((뿌리 / r["폴더"] / "가져오기.json").read_text(encoding="utf-8")) if st == 200 else {}
        확인((기록.get("되돌림") or {}).get("돌림_z도") == -90 and sha(뿌리 / r["폴더"] / "방향틀림.glb") == 원본해시["방향틀림.glb"],
             "방향 틀림: z -90도(SSOT 되돌리기 도구), 원본은 그대로 보존", 기록.get("되돌림"))
        if st == 200:   # 되돌린 사본을 다시 검사해 앞이 -y인지
            st2, v2 = p.올리기(뿌리 / r["입력"], 이름="되돌림확인.blend")
            v2 = p.검사기다리기(v2["번호"])
            확인(v2.get("검사", {}).get("앞") == "-y" and v2["검사"].get("파츠수") == g.get("파츠수"), "방향 틀림: 되돌린 사본의 앞이 -y, 파츠 수 같음", v2.get("검사"))
            p.post("/api/가져오기/취소", {"번호": v2["번호"]})

        # ---- 이미 입력이 있음
        v = 가져와("텍스처모델.glb")
        st, r2 = 넣어(v, 5, "TRIPO 웹")
        확인(st == 409 and "이미 입력" in r2.get("오류", ""), "이미 입력이 있으면 덮어쓰지 않음(409)", (st, r2))
        옛 = 단계줄(p, 5)["입력"]
        st, r2 = 넣어(v, 5, "TRIPO 웹", 바꾸기=True)
        확인(st == 200 and r2.get("이전입력"), "'새 입력으로 바꾸기' → 넣음", r2)
        if st == 200:
            이전 = json.loads((뿌리 / r2["이전입력"] / "이전입력.json").read_text(encoding="utf-8"))
            확인(이전["입력"][0]["원래경로"] == 옛[0] and (뿌리 / 이전["입력"][0]["사본"]).is_file() and (뿌리 / 옛[0]).is_file(),
                 "옛 입력은 이전입력_시각/에 사본, 원래 파일도 그대로", 이전)

        # ---- 3. FBX(뼈대)
        v = 가져와("리깅.fbx")
        g = v.get("검사") or {}
        확인(v.get("상태") == "검사됨" and g.get("뼈대수") == 1 and g.get("뼈수", 0) > 10, "FBX: 열림·뼈대·뼈 수", g)
        확인(v.get("추정") == 8, "FBX: 뼈대 → 8단계로 추정", v.get("추정"))
        st, r = 넣어(v, 8, "TRIPO 웹")
        확인(st == 200 and (g.get("앞") == "-y" or r["입력"].endswith(".blend")), "FBX: 넣기(앞이 -y가 아니면 되돌린 사본)", (g.get("앞"), r))

        # ---- 4. blend(작업본 사본)
        v = 가져와("작업본사본.blend")
        g = v.get("검사") or {}
        확인(v.get("상태") == "검사됨" and g.get("파츠수") == 5 and g.get("앞") == "-y", "blend: 열림·파츠 5·앞 -y", g)
        확인(v.get("추정") == 9, "blend: 뼈대 있는 작업본 → 9단계로 추정", v.get("추정"))
        st, r = 넣어(v, 9, "이 프로젝트의 다른 파일")
        확인(st == 200 and r["입력"].endswith("작업본사본.blend") and not r["방향확인필요"], "blend: 되돌리지 않고 원본 사본을 입력으로", r)

        # ---- 5. 열리지 않는 파일
        for 이름 in ("깨진.glb", "가짜그림.png"):
            v = 가져와(이름)
            확인(v.get("상태") == "열리지 않음" and v.get("검사", {}).get("이유"), f"{이름}: 열리지 않음 + 이유", v.get("검사"))
            st, r = 넣어(v, 3)
            확인(st == 409, f"{이름}: 넣기 거부(409)", (st, r))
            p.post("/api/가져오기/취소", {"번호": v["번호"]})

        # ---- 6. 방향을 모름(OBJ 상자) → 넣고 "방향 확인 필요" → 나중에 고름
        v = 가져와("상자.obj")
        확인(v.get("상태") == "검사됨" and v["검사"].get("앞") == "모름", "OBJ: 앞을 판단 못 함", v.get("검사"))
        st, r = 넣어(v, 3, "다른 곳")
        확인(st == 200 and r["방향확인필요"] and "방향 확인 필요" in 단계줄(p, 3)["표시"], "OBJ: 넣되 '방향 확인 필요' 표시", r)
        st, b = p.get("/api/가져온것", 이름=캐릭터, 단계=3)
        확인(st == 200 and len(b.get("그림", [])) == 4, "OBJ: 넣은 뒤에도 네 방향 그림을 내줌", b)
        st, gg = p._요청("GET", "/api/가져온것/그림?" + urllib.parse.urlencode({"이름": 캐릭터, "폴더": b.get("폴더", ""), "면": "+x"}))
        확인(st == 200, "OBJ: 넣은 그림 내줌", st)
        st, r = p.post("/api/가져오기/방향", {"이름": 캐릭터, "단계": 3, "앞": "+x"})
        줄 = 단계줄(p, 3)
        확인(st == 200 and r["입력"].endswith("되돌림_상자.blend") and "방향 확인 필요" not in 줄["표시"] and 줄["입력"] == [r["입력"]],
             "OBJ: 앞을 고르면 되돌린 사본이 입력, 표시 지움", (st, r))
        st, r = p.post("/api/가져오기/방향", {"이름": 캐릭터, "단계": 3, "앞": "+x"})
        확인(st == 409, "표시가 없으면 방향 고르기 거부", (st, r))

        # ---- 7. 큰 파일 경고(기준을 작게 바꿔 흉내)
        가져오기.큰그림 = 100
        st, v = p.올리기(자료 / "그림.png")
        확인(st == 409 and "큰 파일" in v.get("오류", ""), "큰 그림: '그래도'가 없으면 경고(409)", (st, v))
        st, v = p.올리기(자료 / "그림.png", 큰파일=True)
        확인(st == 200, "큰 그림: '그래도 가져오기'면 받음", (st, v))
        가져오기.큰그림 = 50 << 20
        if st == 200:
            p.검사기다리기(v["번호"])
            st, r = p.post("/api/가져오기/취소", {"번호": v["번호"]})
            확인(st == 200 and not (서버.로컬 / "가져오기" / v["번호"]).exists(), "취소하면 받아 둔 파일 지움", r)

        # ---- 8. 2단계 + TRIPO 웹 = "가져옴"으로 끝
        v = 가져와("텍스처모델.glb")
        st, r = 넣어(v, 2, "TRIPO 웹")
        줄 = 단계줄(p, 2)
        확인(st == 200 and 줄["상태"] == "끝" and "앞 단계 안 거침" in 줄["표시"], "2단계 TRIPO 웹 → 끝(앞 단계 안 거침 표시)", 줄)

        # ---- 다른 탭은 넣지 못함
        v = 가져와("그림.png")
        p.탭 = "다른탭"
        p._요청("POST", "/api/탭", {"탭": "다른탭", "캐릭터": 캐릭터, "단계": 1})
        st, r = 넣어(v, 1, "다른 곳", 바꾸기=True)
        확인(st == 409 and "다른 탭" in r.get("오류", ""), "다른 탭에서는 넣기 거부", (st, r))
        p.탭 = "가져오기시험탭"

        # ---- 원본에 쓰지 않았는지
        확인(all(sha(c원.parent.parent / 상대) == 원본해시[n] for n, 상대 in 시험파일.items()), "원본 시험 파일이 그대로")
        확인(not list((c원 / "03_TRIPO").glob("가져온것_*")), "원본 캐릭터 폴더에 가져온것_ 폴더 없음")
    finally:
        s.shutdown()
        if 인자.남기기:
            print(f"남김: {뿌리}")
        else:
            shutil.rmtree(뿌리, ignore_errors=True)
    print(f"\n실패 {len(실패)}개" + (": " + " / ".join(실패) if 실패 else ""))
    return 1 if 실패 else 0


if __name__ == "__main__":
    sys.exit(main())
