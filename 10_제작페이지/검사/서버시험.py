"""서버의 파일 처리 시험(HTTP 없이 함수로). 임시 폴더에 가짜 저장소를 만들어 쓰고 지운다.

    python 검사/서버시험.py

시험하는 것: 상태.json 꼴(기능명세 2-1)로 만들고 읽기, 한 단계만 깨진 파일, 앞 단계 안 거침/앞 단계가 바뀜 기록,
모르는 항목 보존, 경로 경계(../, 절대 경로, 폴더, 연결점), 동시 쓰기, 새 캐릭터 동시 만들기.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import 제작페이지 as 서버  # noqa: E402

실패 = []


def 확인(조건, 글):
    print(("통과 " if 조건 else "실패 ") + 글)
    if not 조건:
        실패.append(글)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    뿌리 = Path(tempfile.mkdtemp(prefix="제작페이지시험_"))
    바깥 = Path(tempfile.mkdtemp(prefix="제작페이지바깥_"))
    서버.로컬 = 뿌리 / "_로컬"  # 이 PC의 진짜 로컬/에 시험 기록을 남기지 않는다
    try:
        for n in ("가", "나", "다"):
            (뿌리 / "01_캐릭터" / n).mkdir(parents=True)
        (뿌리 / "SSOT" / "캐릭터").mkdir(parents=True)
        (뿌리 / "SSOT" / "캐릭터" / "가.md").write_text("x", encoding="utf-8")
        (뿌리 / "01_캐릭터" / "가" / "그림.png").write_bytes(b"x")
        (바깥 / "비밀.txt").write_text("비밀", encoding="utf-8")
        a = 서버.앱(뿌리, 8765)

        # 1. 새 캐릭터 → 2-1 꼴
        v = a.새캐릭터("가")
        원본 = json.loads((뿌리 / "01_캐릭터/가/제작페이지/상태.json").read_text(encoding="utf-8"))
        확인(원본["꼴버전"] == 1 and 원본["만든시각"].endswith("+09:00") and 원본["작업본해시"] == "", "새 상태.json 머리(꼴버전·한국 시각·빈 해시)")
        확인(isinstance(원본["단계"], list) and [c["번호"] for c in 원본["단계"]] == list(range(1, 12)), "단계가 번호 1~11 목록")
        확인(all(d["상태"] == "입력 없음" for d in v["단계"]), "새 캐릭터 11단계 입력 없음")

        # 2. 모르는 항목 보존 + 단계 쓰기
        원본["사용자메모"] = "남아야 함"
        원본["단계"][0]["덧붙임"] = 1
        (뿌리 / "01_캐릭터/가/제작페이지/상태.json").write_text(json.dumps(원본, ensure_ascii=False), encoding="utf-8")
        a.단계상태쓰기("가", 1, {"상태": "끝", "입력": ["01_캐릭터/가/그림.png"]})
        a.단계상태쓰기("가", 2, {"상태": "끝"})
        a.단계상태쓰기("가", 4, {"상태": "진행 중"})
        v = a.상태보기("가")
        확인(v["단계"][3]["표시"] == ["앞 단계 안 거침"], "3단계가 끝이 아닌데 4단계 시작 → 앞 단계 안 거침")
        확인(v["단계"][1]["표시"] == [], "끝까지 거친 2단계에는 안 거침 없음")
        a.단계상태쓰기("가", 1, {"상태": "진행 중"})
        v = a.상태보기("가")
        확인("앞 단계가 바뀜" in v["단계"][1]["표시"] and "앞 단계 안 거침" not in v["단계"][1]["표시"], "1단계를 다시 고치면 2단계(끝)에 앞 단계가 바뀜")
        원본 = json.loads((뿌리 / "01_캐릭터/가/제작페이지/상태.json").read_text(encoding="utf-8"))
        확인(원본.get("사용자메모") == "남아야 함" and 원본["단계"][0].get("덧붙임") == 1, "모르는 항목을 지우지 않음")
        확인("캐릭터 노트 없음" not in v["단계"][0]["표시"] and "캐릭터 노트 없음" in a.새캐릭터("나")["단계"][0]["표시"], "캐릭터 노트 없음 표시")

        # 3. 한 단계만 깨짐
        깨짐 = json.loads((뿌리 / "01_캐릭터/나/제작페이지/상태.json").read_text(encoding="utf-8"))
        깨짐["단계"][2]["상태"] = ["목록"]
        깨짐["단계"][4]["입력"] = "글"
        del 깨짐["단계"][7]
        (뿌리 / "01_캐릭터/나/제작페이지/상태.json").write_text(json.dumps(깨짐, ensure_ascii=False), encoding="utf-8")
        v = a.상태보기("나")
        상태 = [d["상태"] for d in v["단계"]]
        확인(상태[2] == "알 수 없음" and 상태[7] == "알 수 없음" and 상태[0] == "입력 없음", f"깨진 단계만 알 수 없음({상태})")
        확인(v["단계"][4]["이유"] and "입력" in v["단계"][4]["이유"], "입력이 목록이 아니면 이유를 적음")

        # 4. 경로 경계
        확인(a.저장소파일("01_캐릭터/가/그림.png") is not None, "저장소 안 파일은 인정")
        for 나쁜 in ["../" * 8 + str(바깥 / "비밀.txt").replace(":", ""), str(바깥 / "비밀.txt"), "\\\\server\\share\\x", "01_캐릭터/가", "C:/Windows/win.ini"]:
            확인(a.저장소파일(나쁜) is None, f"경계 밖·폴더는 인정하지 않음: {나쁜[:40]}")
        연결 = 뿌리 / "01_캐릭터" / "가" / "바깥연결"
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(연결), str(바깥)], capture_output=True)
        if r.returncode == 0:
            확인(a.저장소파일("01_캐릭터/가/바깥연결/비밀.txt") is None, "연결점(정션)으로 바깥 파일을 읽지 않음")
            shutil.rmtree(뿌리 / "01_캐릭터" / "다", ignore_errors=True)
            subprocess.run(["cmd", "/c", "mklink", "/J", str(뿌리 / "01_캐릭터" / "다"), str(바깥)], capture_output=True)
            확인("다" not in a.캐릭터들(), "바깥을 가리키는 캐릭터 폴더(정션)는 목록에 없음")
            (뿌리 / "01_캐릭터" / "라").mkdir()
            subprocess.run(["cmd", "/c", "mklink", "/J", str(뿌리 / "01_캐릭터" / "라" / "제작페이지"), str(바깥)], capture_output=True)
            try:
                a.새캐릭터("라")
                확인(False, "바깥을 가리키는 제작페이지 폴더에는 쓰지 않음")
            except 서버.요청오류:
                확인(not (바깥 / "상태.json").exists(), "바깥을 가리키는 제작페이지 폴더에는 쓰지 않음")
        else:
            print("건너뜀: 정션을 만들지 못함")

        # 4b. 하드링크된 로그, 정션인 01_캐릭터
        로그 = 뿌리 / "01_캐릭터/가/제작페이지/서버로그.txt"
        로그.unlink(missing_ok=True)
        (바깥 / "로그.txt").write_text("", encoding="utf-8")
        if subprocess.run(["cmd", "/c", "mklink", "/H", str(로그), str(바깥 / "로그.txt")], capture_output=True).returncode == 0:
            a.단계상태쓰기("가", 3, {"출처": "하드링크 시험"})
            확인((바깥 / "로그.txt").read_text(encoding="utf-8") == "", "하드링크된 서버로그.txt에는 쓰지 않음")
            로그.unlink()
        뿌리2 = Path(tempfile.mkdtemp(prefix="제작페이지시험2_"))
        (바깥 / "캐릭터들" / "큐").mkdir(parents=True)
        if subprocess.run(["cmd", "/c", "mklink", "/J", str(뿌리2 / "01_캐릭터"), str(바깥 / "캐릭터들")], capture_output=True).returncode == 0:
            b = 서버.앱(뿌리2, 8765)
            확인(b.캐릭터들() == [], "01_캐릭터가 바깥을 가리키면 캐릭터 목록이 비어 있음")
            (뿌리2 / "01_캐릭터").rmdir()
        shutil.rmtree(뿌리2, ignore_errors=True)
        try:
            a.단계상태쓰기("가", 3, {"번호": 5})
            확인(False, "단계 쓰기로 번호·표시는 못 바꿈")
        except 서버.요청오류:
            확인(True, "단계 쓰기로 번호·표시는 못 바꿈")
        깨진 = 뿌리 / "01_캐릭터/나/제작페이지/상태.json"
        남은, 못봄 = a.진행중인단계()
        확인("나" in 못봄, f"깨진 상태 파일의 캐릭터는 끄기 점검에서 '점검 못 함'({못봄})")

        # 5. 동시 쓰기: 서로 다른 단계 갱신이 모두 남는가
        오류 = []

        def 쓰기(n):
            try:
                a.단계상태쓰기("가", n, {"출처": f"동시{n}"})
            except Exception as e:
                오류.append(repr(e))
        일꾼 = [threading.Thread(target=쓰기, args=(n,)) for n in range(5, 12) for _ in range(3)]
        [t.start() for t in 일꾼]
        [t.join() for t in 일꾼]
        v = a.상태보기("가")
        확인(not 오류 and all(v["단계"][n - 1]["출처"] == f"동시{n}" for n in range(5, 12)), f"동시 단계 쓰기 21번 모두 남음(오류 {오류[:2]})")
        기억오류 = []

        def 기억(i):
            try:
                a.기억쓰기("가", i % 11)
            except Exception as e:
                기억오류.append(repr(e))
        일꾼 = [threading.Thread(target=기억, args=(i,)) for i in range(24)]
        [t.start() for t in 일꾼]
        [t.join() for t in 일꾼]
        확인(not 기억오류, f"동시 기억 쓰기 24번 오류 없음({기억오류[:1]})")

        # 6. 새 캐릭터 동시 만들기: 한 번만 성공
        (뿌리 / "01_캐릭터" / "마").mkdir()
        결과 = []

        def 만들기():
            try:
                a.새캐릭터("마")
                결과.append("성공")
            except 서버.요청오류 as e:
                결과.append(e.코드)
        일꾼 = [threading.Thread(target=만들기) for _ in range(6)]
        [t.start() for t in 일꾼]
        [t.join() for t in 일꾼]
        확인(결과.count("성공") == 1 and 결과.count(409) == 5, f"새 캐릭터 동시 6번 → 성공 1, 거절 5 ({결과})")
    finally:
        for p in (뿌리 / "01_캐릭터").glob("*"):
            for 연결 in [p / "바깥연결", p / "제작페이지", p]:
                if 연결.is_junction():
                    연결.rmdir()
        shutil.rmtree(뿌리, ignore_errors=True)
        shutil.rmtree(바깥, ignore_errors=True)
    print(f"서버 시험: 실패 {len(실패)}개")
    return 1 if 실패 else 0


if __name__ == "__main__":
    sys.exit(main())
