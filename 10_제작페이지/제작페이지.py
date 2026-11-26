"""가마우지 제작 페이지 서버 (작업 묶음 W00: 바탕)

켜기:
    python 제작페이지.py --폴더 <저장소 루트>
    python 제작페이지.py --폴더 <저장소 루트> --열지않음     (브라우저를 열지 않음)
    python 제작페이지.py --폴더 <저장소 루트> --진짜실행     (승인한 TRIPO 실행을 진짜로 함, 크레딧을 씀. 없으면 가짜 실행 — W07)
끄기:
    창 닫기 / Ctrl+C / python 제작페이지.py --폴더 <저장소 루트> --끄기 [--그래도]

규칙 (기능명세_v001.md 1부 6절):
- 127.0.0.1 에만 연다. 다른 주소로 여는 옵션은 없다.
- 기본 포트 8765. 쓰이는 중이면 다음 빈 포트(8765~8784)를 쓰고 주소를 출력한다.
- 같은 폴더를 보는 서버가 어느 포트에든 켜져 있으면 새로 켜지 않고 그 주소를 연다.
- 바깥 주소로 요청하지 않는다. 파이썬 표준 라이브러리만 쓴다.

파일:
- 화면: 이 폴더의 `정적/`. 디자인 토큰은 저장소의 `00_공통문서/제작페이지_설계/디자인토큰.css`를 그대로 내준다.
- 캐릭터마다: `01_캐릭터/<이름>/제작페이지/상태.json`(꼴은 기능명세 2-1), `서버로그.txt`.
- 이 PC에만 해당하는 것(마지막에 본 캐릭터·단계, TRIPO 잔액 기록, 서버 기록): 이 폴더의 `로컬/`(git에 넣지 않음).
- 읽고 쓰는 파일은 모두 `--폴더` 안의 실제 경로로 제한한다(연결점·절대 경로·네트워크 경로를 거름).
"""

from __future__ import annotations

import argparse
import re
import hashlib
import shutil
import http.client
import json
import mimetypes
import os
import socket
import sys
import tempfile
import threading
import time
import urllib.parse
import webbrowser
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath, PureWindowsPath

import 보기만들기  # W01: 작업본 → 3D 보기용 GLB
import 승인  # W07: 승인과 TRIPO 실행(아래 요청오류 뒤에서 묶음)
import 가져오기  # W08: 파일 가져오기(아래 요청오류 뒤에서 묶음)
import 그림단계  # W09: 1단계 그림 생성(아래 요청오류 뒤에서 묶음)
import 생성단계  # W10: 2·4·5·6단계(TRIPO 생성 계열)
import 메시단계  # W11: 3단계 메시 정리(두 번 멈춤)
import 텍스처단계  # W12: 7단계 텍스처 수정
import 리깅단계  # W13: 8·9단계 리깅
import 동작단계  # W14: 10·11단계 동작·내보내기

프로그램 = "가마우지-제작페이지"
판 = "W14"
주소 = "127.0.0.1"
기본포트 = 8765
포트수 = 20  # 8765~8784

여기 = Path(__file__).resolve().parent
정적 = 여기 / "정적"
로컬 = 여기 / "로컬"
토큰파일 = 여기.parent / "00_공통문서" / "제작페이지_설계" / "디자인토큰.css"

# 기능명세 2절의 <NN_단계> 폴더 이름과 화면 이름(번호 = 순서 + 1)
단계목록 = [
    ("01_그림생성", "그림 생성"),
    ("02_모델생성", "모델 생성"),
    ("03_메시정리", "메시 정리"),
    ("04_리토폴로지", "리토폴로지"),
    ("05_텍스처생성", "텍스처 생성"),
    ("06_SmartUV", "Smart UV"),
    ("07_텍스처수정", "텍스처 수정"),
    ("08_오토리깅", "오토 리깅"),
    ("09_리깅수정", "리깅 수정"),
    ("10_애니메이션", "애니메이션"),
    ("11_내보내기", "내보내기"),
]
# 기능명세 2-1 상태.json의 단계[].상태 값. "입력 없음"/"준비됨"은 입력 파일이 있는지로 서버가 다시 정한다(1부 4-2).
시작한상태 = {"진행 중", "결정 대기", "끝", "끝(조건 미달)", "막힘"}
끝상태 = {"끝", "끝(조건 미달)"}
허용상태 = 시작한상태 | {"입력 없음", "준비됨"}
허용표시 = {"앞 단계 안 거침", "앞 단계가 바뀜", "방향 확인 필요"}  # 마지막은 W08(가져온 모델의 앞을 모름)
꼴버전 = 1
탭유효초 = 150.0  # 숨은 탭은 브라우저가 타이머를 1분에 한 번까지 늦추므로 넉넉히. 닫힌 탭은 pagehide로 바로 놓는다.
한국 = timezone(timedelta(hours=9))
# 칠할 때 고르는 처리 종류(기능명세 1부 5-4b). 목록의 끝이 기본(고르지 않고 칠하면 그것). 1단계는 그림(2D) 위에 칠한다(W09).
처리목록 = {
    1: ["손·발 모양", "비율·체형", "얼굴", "옷·색·무늬", "다른 방향과 안 맞음", "기타"],
    3: ["지우기", "메우기(구멍)", "매끈하게", "모양이 이상함"],
    6: ["늘어남·찌그러짐", "기타"],
    7: ["선이 끊김·꺾임", "얼룩 지우기", "색이 틀림", "무늬를 지우기", "이상함"],
    9: ["관통", "찢어짐·늘어남", "움직임이 어색함", "떨림·튐", "기타"],
    10: ["관통", "찢어짐·늘어남", "움직임이 어색함", "떨림·튐", "기타"],
}
메모필수종류 = ["기타"]  # 이것을 고르면 메모 없이는 보낼 수 없다(5-4b)
취소한도 = 50          # 취소·다시 기록(5-4, 제안값)
# W06: 결정 칸과 에이전트 약속(1부 2-1·3·4-4·7)
묶음상태들 = ("작성 중", "보냄", "처리 중", "처리됨", "실패")
알림종류 = ("안내", "결정 필요", "막힘")
사본한도 = 10                 # 되돌리기 사본을 단계마다 몇 개 두나(8절, 사용자 확정). 넘으면 지울 후보만 알림
사본여유 = 200 << 20           # 사본을 만들 때 작업본 크기 말고 더 남아 있어야 할 디스크(제안값)
단계완료검사: dict = {}        # 번호 → 함수(앱, 이름) → 모자란 것 목록. 2부의 단계별 완료 조건은 W09~W14가 붙인다


def 지금(파일용: bool = False) -> str:
    t = datetime.now(한국)
    return t.strftime("%Y-%m-%dT%H%M") if 파일용 else t.isoformat(timespec="seconds")


# ---------------------------------------------------------------- 기록


_기록잠금 = threading.Lock()


def 기록(내용: str, 앱_: "앱 | None" = None, 캐릭터: str | None = None) -> None:
    줄 = f"{지금()} {내용}\n"
    with _기록잠금:
        로컬.mkdir(exist_ok=True)
        with open(로컬 / "서버로그.txt", "a", encoding="utf-8") as f:
            f.write(줄)
        if 앱_ is not None and 캐릭터 is not None:
            try:
                d = 앱_.제작페이지폴더(캐릭터, 만들기=False)
            except 요청오류:
                return
            로그 = d / "서버로그.txt"
            # 하드링크·연결된 로그는 저장소 밖 파일일 수 있으니 쓰지 않는다
            if d.is_dir() and (not 로그.exists() or (로그.is_file() and not 로그.is_symlink() and 로그.stat().st_nlink == 1)):
                with open(로그, "a", encoding="utf-8") as f:
                    f.write(줄)


# ---------------------------------------------------------------- 파일 읽고 쓰기


_파일잠금: dict[str, threading.Lock] = {}
_파일잠금잠금 = threading.Lock()


def 파일잠금(p: Path) -> threading.Lock:
    with _파일잠금잠금:
        return _파일잠금.setdefault(str(p).lower(), threading.Lock())


def json_읽기(p: Path):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def json_쓰기(p: Path, 값) -> None:
    """반쯤 쓴 파일이 남지 않도록 같은 폴더의 고유한 임시 파일에 쓴 뒤 바꿔 넣는다. 부르는 쪽이 파일잠금을 잡는다."""
    fd, 임시 = tempfile.mkstemp(prefix=p.name + ".", suffix=".쓰는중", dir=p.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(값, f, ensure_ascii=False, indent=2)
            f.write("\n")
        for 번 in range(5):  # 다른 프로그램(백신·탐색기)이 잠깐 잡고 있을 때
            try:
                os.replace(임시, p)
                return
            except PermissionError:
                if 번 == 4:
                    raise
                time.sleep(0.05 * (번 + 1))
    finally:
        if os.path.exists(임시):
            os.remove(임시)


_해시캐시: dict[tuple, str] = {}


def 파일해시(p: Path) -> str:
    """SHA-256 앞 12자리(기능명세 2절 작업본해시). 크기·수정 시각이 같으면 다시 읽지 않는다. 없으면 빈 글."""
    try:
        st = p.stat()
    except OSError:
        return ""
    열쇠 = (str(p), st.st_size, st.st_mtime_ns)
    if 열쇠 in _해시캐시:
        return _해시캐시[열쇠]
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for 조각 in iter(lambda: f.read(1 << 20), b""):
            h.update(조각)
    값 = h.hexdigest()[:12]
    _해시캐시[열쇠] = 값
    return 값


class 요청오류(Exception):
    def __init__(self, 코드: int, 글: str):
        super().__init__(글)
        self.코드 = 코드
        self.글 = 글


승인.묶기(sys.modules[__name__])  # W07 모듈이 이 모듈의 요청오류·로컬·앱 함수를 쓴다
가져오기.묶기(sys.modules[__name__])  # W08
그림단계.묶기(sys.modules[__name__])  # W09
단계완료검사[1] = 그림단계.완료모자람  # W09: 1단계 끝나는 조건(2부 13절)
생성단계.묶기(sys.modules[__name__])  # W10
for _n in 생성단계.단계들:  # W10: 2·4·5·6단계 끝나는 조건(2부 14·16·17·18절)과 승인을 막는 단계별 까닭
    단계완료검사[_n] = (lambda n: lambda a, 이름: 생성단계.완료모자람(a, 이름, n))(_n)
    승인.추가막기[_n] = (lambda n: lambda a, 이름, v: 생성단계.막는이유(a, 이름, n, v))(_n)
메시단계.묶기(sys.modules[__name__])  # W11
단계완료검사[3] = 메시단계.완료모자람  # W11: 3단계 끝나는 조건(2부 15절)
텍스처단계.묶기(sys.modules[__name__])  # W12
단계완료검사[7] = 텍스처단계.완료모자람  # W12: 7단계 끝나는 조건(2부 19절)
리깅단계.묶기(sys.modules[__name__])  # W13
for _n in 리깅단계.단계들:  # W13: 8·9단계 끝나는 조건(2부 20·21절)
    단계완료검사[_n] = (lambda n: lambda a, 이름: 리깅단계.완료모자람(a, 이름, n))(_n)
승인.추가막기[8] = lambda a, 이름, v: 리깅단계.막는이유(a, 이름, 8, v)  # W13: 리그 체크 없음·false면 승인을 막음
동작단계.묶기(sys.modules[__name__])  # W14
for _n in 동작단계.단계들:  # W14: 10·11단계 끝나는 조건(2부 22·23절)
    단계완료검사[_n] = (lambda n: lambda a, 이름: 동작단계.완료모자람(a, 이름, n))(_n)


class 앱:
    def __init__(self, 폴더: Path, 포트: int):
        self.폴더 = 폴더.resolve()
        self.포트 = 포트
        self.캐릭터루트 = self.폴더 / "01_캐릭터"
        self.노트루트 = self.폴더 / "SSOT" / "캐릭터"
        self.탭: dict[str, dict[str, dict]] = {}
        self.탭잠금 = threading.Lock()
        self.서버: ThreadingHTTPServer | None = None
        self.모델작업: dict[str, dict] = {}  # 캐릭터 → {해시, 시작, 결과}  (W01)
        self.모델잠금 = threading.Lock()

    # ---- 경로 경계

    def 안쪽인가(self, p: Path, 바깥: Path) -> bool:
        try:
            return p.resolve().is_relative_to(바깥.resolve())
        except OSError:
            return False

    def 저장소파일(self, 글) -> Path | None:
        """상태.json에 적힌 '저장소 루트 기준' 경로를 실제 파일로. 경계 밖·절대·네트워크·폴더면 None."""
        if not isinstance(글, str) or not 글.strip():
            return None
        if PureWindowsPath(글).anchor or PurePosixPath(글).anchor or 글.startswith(("\\\\", "//")):
            return None
        정리 = os.path.normpath(글)
        if 정리 == ".." or 정리.startswith(".." + os.sep):
            return None
        p = self.폴더 / 정리
        if not os.path.isfile(p):  # 없는 파일은 여기서 빨리 끝낸다(resolve는 느림)
            return None
        try:
            실제 = p.resolve()
        except OSError:
            return None
        return 실제 if 실제.is_relative_to(self.폴더) and 실제.is_file() else None

    # ---- 캐릭터

    def 캐릭터들(self) -> list[str]:
        if not self.캐릭터루트.is_dir():
            return []
        return sorted(
            d.name for d in self.캐릭터루트.iterdir()
            if d.is_dir() and not d.name.startswith((".", "_")) and self.안쪽인가(d, self.폴더)
        )

    def 캐릭터폴더(self, 이름) -> Path:
        """목록에 있는 이름만 받는다(경로를 벗어나는 이름·연결점을 막음)."""
        if not isinstance(이름, str) or 이름 not in self.캐릭터들():
            raise 요청오류(404, f"캐릭터 폴더가 없습니다: {이름}")
        return self.캐릭터루트 / 이름

    def 제작페이지폴더(self, 이름, 만들기: bool) -> Path:
        c = self.캐릭터폴더(이름)
        d = c / "제작페이지"
        if not self.안쪽인가(c, self.폴더) or (d.exists() and (not d.is_dir() or not self.안쪽인가(d, c))):
            raise 요청오류(409, "제작페이지 폴더가 캐릭터 폴더 밖을 가리킵니다. 쓰지 않습니다.")
        if 만들기:
            d.mkdir(exist_ok=True)
        return d

    # ---- 3D 보기용 GLB (W01, 기능명세 5-1)

    def 보기폴더(self, 이름, 만들기: bool) -> Path:
        d = self.제작페이지폴더(이름, 만들기=만들기) / "보기"
        if d.exists() and (not d.is_dir() or not self.안쪽인가(d, self.캐릭터폴더(이름))):
            raise 요청오류(409, "보기 폴더가 캐릭터 폴더 밖을 가리킵니다.")
        if 만들기:
            d.mkdir(exist_ok=True)
        return d

    def 모델(self, 이름, 다시: bool = False) -> dict:
        """작업본의 GLB가 있으면 주소를, 없으면 뒤에서 만들기 시작하고 "만드는 중"을 돌려준다(화면은 다시 묻는다).
        상태: 작업본 없음 / 됨 / 만드는 중 / 실패. "마지막"은 검사를 통과한 가장 최근 GLB(바뀌는 중에 대신 보일 것)."""
        p = self.상태파일(이름)
        작업본 = json_읽기(p).get("작업본") if p.is_file() else None
        f = self.저장소파일(작업본)
        if not f:
            return {"상태": "작업본 없음", "작업본": 작업본 or ""}
        if f.suffix.lower() != ".blend":
            return {"상태": "실패", "오류": "작업본이 .blend 파일이 아닙니다.", "작업본": 작업본}
        짧은 = 파일해시(f)
        보기 = self.보기폴더(이름, 만들기=True)
        주소 = lambda h: urllib.parse.quote(f"/보기/{이름}/{h}.glb")
        마지막 = 보기만들기.마지막glb(보기)
        # 전후 비교(W02)의 "전": 지금 해시가 아닌, 검사를 통과한 GLB 가운데 가장 최근 것
        전후보 = [p for p in 보기.glob("*.glb") if ".만드는중" not in p.name and p.stem != 짧은 and 보기만들기.캐시(보기, p.stem)]
        전 = max(전후보, key=lambda p: p.stat().st_mtime).stem if 전후보 else None
        기본 = {"작업본": 작업본, "작업본해시": 짧은, "마지막": 주소(마지막) if 마지막 else None, "전": 주소(전) if 전 else None}
        정보 = None if 다시 else 보기만들기.캐시(보기, 짧은)
        if 정보:
            return dict(기본, 상태="됨", 주소=주소(짧은), 정보=정보)
        with self.모델잠금:
            일 = self.모델작업.get(이름)
            if 일 and 일["결과"] is None:
                return dict(기본, 상태="만드는 중", 경과초=round(time.monotonic() - 일["시작"], 1), 만드는해시=일["해시"])
            if 일 and 일["해시"] == 짧은 and not 다시:
                r = 일["결과"]
                if r["상태"] == "실패":
                    로그 = r.get("로그")
                    return dict(기본, 상태="실패", 오류=r.get("오류"),
                                로그=os.path.relpath(로그, self.폴더) if 로그 else None)
            새일 = {"해시": 짧은, "시작": time.monotonic(), "결과": None}
            self.모델작업[이름] = 새일

        def 돌리기():
            try:
                r = 보기만들기.만들기(f, 보기, 다시=다시)
            except Exception as e:
                r = {"상태": "실패", "오류": repr(e)}
            새일["결과"] = r
            기록(f"GLB {r['상태']} {짧은} {r.get('오류') or ''}".rstrip(), self, 이름)

        threading.Thread(target=돌리기, daemon=True).start()
        return dict(기본, 상태="만드는 중", 경과초=0.0, 만드는해시=짧은)

    def 보기파일(self, 이름, 파일: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{12}\.glb", 파일):
            raise 요청오류(404, "없는 파일입니다.")
        p = self.보기폴더(이름, 만들기=False) / 파일
        if not p.is_file() or p.is_symlink() or not self.안쪽인가(p, self.캐릭터폴더(이름)):
            raise 요청오류(404, "없는 파일입니다.")
        return p

    def 상태파일(self, 이름) -> Path:
        p = self.제작페이지폴더(이름, 만들기=False) / "상태.json"
        if p.exists() and (p.is_symlink() or not p.is_file() or p.stat().st_nlink != 1):
            raise 요청오류(409, "상태.json이 일반 파일이 아닙니다(링크).")
        return p

    def 캐릭터목록(self) -> list[dict]:
        목록 = []
        for n in self.캐릭터들():
            try:
                있음 = self.상태파일(n).is_file()
            except 요청오류:
                있음 = False
            목록.append({"이름": n, "상태파일있음": 있음, "노트있음": (self.노트루트 / f"{n}.md").is_file()})
        return 목록

    # ---- 상태.json (기능명세 2-1)

    def 상태보기(self, 이름) -> dict:
        """상태.json을 읽어 화면에 쓸 단계 11줄을 만든다(1부 4-2 규칙). 한 단계가 깨져도 나머지는 보인다."""
        p = self.상태파일(이름)
        노트있음 = (self.노트루트 / f"{이름}.md").is_file()
        결과 = {
            "이름": 이름, "폴더": f"01_캐릭터/{이름}/", "있음": p.is_file(), "노트있음": 노트있음,
            "오류": None, "수정시각": None, "작업본": "", "작업본해시": "", "작업본해시_파일": "", "단계": [],
        }
        원본 = None
        if 결과["있음"]:
            결과["수정시각"] = p.stat().st_mtime_ns
            try:
                원본 = json_읽기(p)
                if not isinstance(원본, dict):
                    raise ValueError("맨 바깥이 객체가 아님")
            except Exception as e:
                결과["오류"] = f"상태.json을 읽지 못함: {e}"
        줄들: dict[int, dict] = {}
        if isinstance(원본, dict):
            if 원본.get("꼴버전") != 꼴버전:
                결과["오류"] = f"모르는 꼴버전: {원본.get('꼴버전')!r} (이 서버는 {꼴버전})"
            결과["작업본해시_파일"] = 원본.get("작업본해시") or ""
            작업본 = 원본.get("작업본")
            if isinstance(작업본, str) and 작업본:
                결과["작업본"] = 작업본
                f = self.저장소파일(작업본)
                결과["작업본해시"] = 파일해시(f) if f else ""
            단계값 = 원본.get("단계")
            if not isinstance(단계값, list):
                결과["오류"] = 결과["오류"] or "상태.json의 '단계'가 목록이 아님"
            else:
                for 칸 in 단계값:
                    if isinstance(칸, dict) and isinstance(칸.get("번호"), int) and 1 <= 칸["번호"] <= 11:
                        if 칸["번호"] in 줄들:
                            줄들[칸["번호"]] = {"_오류": f"번호 {칸['번호']}가 두 번 있음"}
                        else:
                            줄들[칸["번호"]] = 칸
        for i, (열쇠, 화면이름) in enumerate(단계목록):
            번호 = i + 1
            줄 = {"번호": 번호, "열쇠": 열쇠, "이름": 화면이름, "상태": "입력 없음", "이유": None,
                  "입력": [], "없는입력": [], "출처": None, "바뀐시각": None, "표시": []}
            if 결과["있음"] and not isinstance(원본, dict):
                줄["상태"], 줄["이유"] = "알 수 없음", 결과["오류"]
            elif 결과["있음"] and not isinstance((원본 or {}).get("단계"), list):
                줄["상태"], 줄["이유"] = "알 수 없음", 결과["오류"]
            elif 결과["있음"]:
                칸 = 줄들.get(번호)
                if 칸 is None:
                    줄["상태"], 줄["이유"] = "알 수 없음", f"상태.json에 {번호}단계가 없음"
                elif "_오류" in 칸:
                    줄["상태"], 줄["이유"] = "알 수 없음", 칸["_오류"]
                else:
                    self._줄채우기(줄, 칸)
            if 번호 == 1 and not 노트있음:
                줄["표시"].append("캐릭터 노트 없음")
            결과["단계"].append(줄)
        return 결과

    def _줄채우기(self, 줄: dict, 칸: dict) -> None:
        문제 = []
        입력 = 칸.get("입력", [])
        if not isinstance(입력, list) or not all(isinstance(x, str) for x in 입력):
            문제.append("'입력'이 글 목록이 아님")
            입력 = []
        줄["입력"] = 입력
        줄["없는입력"] = [x for x in 입력 if self.저장소파일(x) is None]
        출처 = 칸.get("출처")
        줄["출처"] = 출처 if isinstance(출처, str) else None
        줄["바뀐시각"] = 칸.get("바뀐시각") if isinstance(칸.get("바뀐시각"), str) else None
        표시 = 칸.get("표시", [])
        if not isinstance(표시, list):
            문제.append("'표시'가 목록이 아님")
            표시 = []
        줄["표시"] = [x for x in 표시 if isinstance(x, str) and x in 허용표시]
        모르는표시 = [x for x in 표시 if not (isinstance(x, str) and x in 허용표시)]
        if 모르는표시:
            문제.append(f"모르는 표시: {모르는표시}")
        적힌 = 칸.get("상태", "입력 없음")
        if not isinstance(적힌, str) or 적힌 not in 허용상태:
            줄["상태"] = "알 수 없음"
            문제.insert(0, f"모르는 상태 값: {적힌!r}")
        elif 적힌 in 시작한상태:
            줄["상태"] = 적힌
        else:
            줄["상태"] = "준비됨" if 입력 and not 줄["없는입력"] else "입력 없음"
        if 문제:
            줄["이유"] = " · ".join(문제)

    def 새캐릭터(self, 이름) -> dict:
        d = self.제작페이지폴더(이름, 만들기=True)
        p = d / "상태.json"
        with 파일잠금(p):
            if p.exists():
                raise 요청오류(409, "상태.json이 이미 있습니다. 덮어쓰지 않습니다.")
            시각 = 지금()
            값 = {
                "꼴버전": 꼴버전, "만든시각": 시각, "작업본해시": "", "캐릭터": 이름, "작업본": "",
                "단계": [{"번호": i + 1, "상태": "입력 없음", "입력": [], "출처": "", "표시": [], "바뀐시각": 시각}
                         for i in range(len(단계목록))],
            }
            json_쓰기(p, 값)
        기록(f"새 캐릭터 상태 파일을 만듦: {p.relative_to(self.폴더).as_posix()}", self, 이름)
        return self.상태보기(이름)

    def 단계상태쓰기(self, 이름, 번호: int, 바꿀것: dict) -> dict:
        """한 단계의 값을 바꿔 쓴다(뒤의 작업 묶음이 쓰는 자리). 모르는 항목은 그대로 둔다.
        - 시작하지 않은 단계가 시작되는데 앞 단계 중 끝이 아닌 것이 있으면 그 단계에 '앞 단계 안 거침'.
        - 끝인 단계를 다시 고치기 시작하면(끝이 아닌 상태로 바뀜) 뒤의 끝인 단계마다 '앞 단계가 바뀜'."""
        if not isinstance(번호, int) or not 1 <= 번호 <= 11:
            raise 요청오류(400, f"모르는 단계 번호: {번호}")
        # 번호와 표시는 서버 규칙으로만 바꾼다
        모르는것 = set(바꿀것) - {"상태", "입력", "출처"}
        if 모르는것:
            raise 요청오류(400, f"바꿀 수 없는 항목: {sorted(모르는것)}")
        if "상태" in 바꿀것 and (not isinstance(바꿀것["상태"], str) or 바꿀것["상태"] not in 허용상태):
            raise 요청오류(400, f"모르는 상태 값: {바꿀것['상태']}")
        p = self.상태파일(이름)
        with 파일잠금(p):
            값 = json_읽기(p)
            단계 = 값.get("단계")
            if not isinstance(단계, list):
                raise 요청오류(409, "상태.json의 '단계'가 목록이 아님")
            찾기 = {c.get("번호"): c for c in 단계 if isinstance(c, dict)}
            칸 = 찾기.get(번호)
            if 칸 is None:
                칸 = {"번호": 번호}
                단계.append(칸)
                단계.sort(key=lambda c: c.get("번호", 99) if isinstance(c, dict) else 99)
            시각 = 지금()
            전 = 칸.get("상태", "입력 없음")
            후 = 바꿀것.get("상태", 전)
            칸.update(바꿀것)
            칸["바뀐시각"] = 시각
            표시 = 칸.setdefault("표시", [])
            if 전 not in 시작한상태 and 후 in 시작한상태:
                앞 = [찾기.get(n, {}).get("상태") for n in range(1, 번호)]
                if any(s not in 끝상태 for s in 앞) and "앞 단계 안 거침" not in 표시:
                    표시.append("앞 단계 안 거침")
            if 전 in 끝상태 and 후 not in 끝상태:
                for n in range(번호 + 1, 12):
                    c = 찾기.get(n)
                    if c and c.get("상태") in 끝상태 and "앞 단계가 바뀜" not in c.setdefault("표시", []):
                        c["표시"].append("앞 단계가 바뀜")
                        c["바뀐시각"] = 시각
            if 값.get("작업본"):
                f = self.저장소파일(값["작업본"])
                값["작업본해시"] = 파일해시(f) if f else ""
            json_쓰기(p, 값)
        기록(f"상태를 씀: {번호}단계 {바꿀것}", self, 이름)
        return self.상태보기(이름)

    # ---- 칠하기와 표시 (W03, 기능명세 2-1·3·4-4·5-4·5-4b·5-5)

    def 단계폴더(self, 이름, 번호, 만들기: bool) -> Path:
        if not isinstance(번호, int) or not 1 <= 번호 <= 11:
            raise 요청오류(400, f"모르는 단계 번호: {번호}")
        c = self.캐릭터폴더(이름)
        d = self.제작페이지폴더(이름, 만들기=만들기) / 단계목록[번호 - 1][0]
        if d.exists() and (not d.is_dir() or d.is_symlink() or not self.안쪽인가(d, c)):
            raise 요청오류(409, "단계 폴더가 캐릭터 폴더 밖을 가리킵니다. 쓰지 않습니다.")
        if 만들기:
            d.mkdir(exist_ok=True)
        return d

    def _안전한파일(self, p: Path, 캐릭터폴더: Path) -> bool:
        return p.is_file() and not p.is_symlink() and p.stat().st_nlink == 1 and self.안쪽인가(p, 캐릭터폴더)

    def _지금작업본해시(self, 이름) -> str:
        p = self.상태파일(이름)
        if not p.is_file():
            return ""
        try:
            f = self.저장소파일(json_읽기(p).get("작업본"))
        except Exception:
            return ""
        return 파일해시(f) if f else ""

    def 표시읽기(self, 이름, 번호) -> dict:
        """한 단계의 작성 중 표시, 취소 기록, 보낸 묶음(처리 결과 포함), 가장 최근 후보 파일."""
        d = self.단계폴더(이름, 번호, 만들기=False)
        c = self.캐릭터폴더(이름)
        결과 = {"단계": 번호, "처리목록": 처리목록.get(번호, []), "메모필수": 메모필수종류,
                "작업본해시": self._지금작업본해시(이름), "작성중": None, "기록": None, "묶음": [], "후보": None, "오류": []}
        if not d.is_dir():
            return 결과

        def 읽기(p: Path):
            if not self._안전한파일(p, c):
                return None
            try:
                v = json_읽기(p)
                return v if isinstance(v, dict) else None
            except Exception as e:
                결과["오류"].append(f"{p.name}을 읽지 못함: {e}")
                return None

        결과["작성중"] = 읽기(d / "작성중.json")
        결과["기록"] = 읽기(d / "작성중_기록.json")
        처리들: dict[str, dict] = {}
        for p in sorted(d.glob("처리_*.json")):
            v = 읽기(p)
            if v and isinstance(v.get("묶음"), str):
                처리들[v["묶음"]] = dict(v, 파일=p.name)  # 같은 묶음의 처리가 여럿이면 가장 최근 것
        for p in sorted(d.glob("보내기_*.json")):
            v = 읽기(p)
            if v is None:
                continue
            결과["묶음"].append({"파일": p.name, "묶음상태": v.get("묶음상태"), "만든시각": v.get("만든시각"),
                               "작업본해시": v.get("작업본해시"), "표시": v.get("표시") or [], "후보판단": v.get("후보판단") or [],
                               "합친묶음": v.get("합친묶음") or [], "처리": 처리들.get(p.name)})
        후보파일 = sorted(d.glob("후보_*.json"))
        if 후보파일:
            v = 읽기(후보파일[-1])
            if v is not None:
                결과["후보"] = {"파일": 후보파일[-1].name, "만든이": v.get("만든이"), "작업본해시": v.get("작업본해시") or "",
                              "후보": v.get("후보") or [], "고친것": v.get("고친것") or []}
        return 결과

    def 표시바뀜(self, 이름, 번호) -> str:
        """에이전트가 쓰는 파일(후보·보내기·처리)의 이름과 수정 시각을 묶은 값. 화면이 다시 읽을지 정한다."""
        try:
            d = self.단계폴더(이름, 번호, 만들기=False)
        except 요청오류:
            return ""
        if not d.is_dir():
            return ""
        조각 = [f"{p.name}:{p.stat().st_mtime_ns}" for p in sorted(d.iterdir())
               if p.is_file() and p.name.startswith(("후보_", "보내기_", "처리_"))]
        return hashlib.sha256("|".join(조각).encode()).hexdigest()[:12] if 조각 else ""

    def _표시검사(self, 목록, 번호: int) -> list[dict]:
        if not isinstance(목록, list):
            raise 요청오류(400, "'표시'가 목록이 아님")
        if len(목록) > 1000:
            raise 요청오류(400, "표시가 너무 많습니다(1000개 넘음).")
        종류들 = 처리목록.get(번호)
        if not 종류들:
            raise 요청오류(400, f"{번호}단계에서는 칠하지 않습니다.")
        본번호, 면합 = set(), 0
        for x in 목록:
            if not isinstance(x, dict):
                raise 요청오류(400, "표시 한 줄이 객체가 아님")
            n = x.get("번호")
            if not isinstance(n, str) or not n or len(n) > 8 or n in 본번호:
                raise 요청오류(400, f"표시 번호가 비었거나 겹침: {n!r}")
            본번호.add(n)
            if x.get("누가") != "사용자":
                raise 요청오류(400, "페이지가 쓰는 표시의 '누가'는 '사용자'뿐입니다.")
            if x.get("종류") not in 종류들:
                raise 요청오류(400, f"{번호}단계에 없는 처리 종류: {x.get('종류')!r}")
            자리 = x.get("자리")
            if not isinstance(자리, dict) or not isinstance(자리.get("파츠"), list) or not isinstance(자리.get("면"), dict):
                raise 요청오류(400, f"표시 {n}의 '자리'가 2-1 꼴이 아님")
            if 번호 == 1:  # W09: 그림(2D) 위 표시. 자리.그림 = {파일, 범위[[x1,y1],[x2,y2]], 획[[x,y]...], 붓}
                그 = 자리.get("그림")
                if (not isinstance(그, dict) or not isinstance(그.get("파일"), str) or self.저장소파일(그["파일"]) is None
                        or not isinstance(그.get("범위"), list) or len(그["범위"]) != 2
                        or not all(isinstance(q, list) and len(q) == 2 and all(isinstance(t, (int, float)) for t in q) for q in 그["범위"])
                        or not isinstance(그.get("획", []), list) or len(그.get("획", [])) > 5000):
                    raise 요청오류(400, f"표시 {n}의 '자리.그림'이 {{파일, 범위}} 꼴이 아니거나 그림이 없음")
            if not all(isinstance(p, str) for p in 자리["파츠"]):
                raise 요청오류(400, f"표시 {n}의 파츠 이름이 글이 아님")
            if 번호 in (9, 10) and "동작" in 자리:  # W13: 자리.동작 {이름, 시작장, 끝장}(2-1), 구간 리포트는 면이 없어도 됨
                d = 자리["동작"]
                if (not isinstance(d, dict) or not isinstance(d.get("이름"), str) or not d["이름"]
                        or not all(isinstance(d.get(k), int) and not isinstance(d.get(k), bool) for k in ("시작장", "끝장"))
                        or d["끝장"] < d["시작장"]):
                    raise 요청오류(400, f"표시 {n}의 '자리.동작'이 {{이름, 시작장, 끝장}} 꼴이 아님")
            elif 번호 in (9, 10) and not 자리["면"]:
                raise 요청오류(400, f"표시 {n}에 칠한 면도 동작 구간도 없음")
            for p, 면 in 자리["면"].items():
                if not isinstance(면, list) or not all(isinstance(i, int) and not isinstance(i, bool) and i >= 0 for i in 면):
                    raise 요청오류(400, f"표시 {n}의 면 번호가 0 이상의 정수 목록이 아님({p})")
                면합 += len(면)
            if not isinstance(x.get("반대쪽도", False), bool):
                raise 요청오류(400, f"표시 {n}의 '반대쪽도'가 참/거짓이 아님")
            if not isinstance(x.get("메모", ""), str) or len(x.get("메모", "")) > 4000:
                raise 요청오류(400, f"표시 {n}의 메모가 글이 아니거나 너무 김")
            h = x.get("작업본해시", "")
            if not isinstance(h, str) or not re.fullmatch(r"[0-9a-f]{0,12}", h):
                raise 요청오류(400, f"표시 {n}의 작업본해시가 잘못됨")
        if 면합 > 2_000_000:
            raise 요청오류(400, "칠한 면이 너무 많습니다.")
        return 목록

    def _후보판단검사(self, 목록) -> list[dict]:
        if not isinstance(목록, list):
            raise 요청오류(400, "'후보판단'이 목록이 아님")
        for x in 목록:
            if (not isinstance(x, dict) or not isinstance(x.get("후보파일"), str) or not re.fullmatch(r"후보_[0-9T_-]+\.json", x["후보파일"])
                    or not isinstance(x.get("번호"), str) or x.get("판단") not in ("고칠 것", "둘 것", "모름")):
                raise 요청오류(400, f"후보 판단 한 줄이 2-1 꼴이 아님: {x!r}"[:200])
        return 목록

    def _주인확인(self, 탭, 이름) -> None:
        if not isinstance(탭, str) or not 탭:
            raise 요청오류(400, "탭 번호가 없습니다.")
        # 등록은 하지 않고 확인만 한다(창을 닫을 때의 마지막 저장이 탭을 다시 붙잡지 않게). 다른 탭이 주인이면 거부
        탭 = 탭[:64]
        t = time.monotonic()
        with self.탭잠금:
            무리 = {k: v for k, v in self.탭.get(이름, {}).items() if t - v["마지막"] <= 탭유효초}
        if 무리 and min(무리, key=lambda k: 무리[k]["처음"]) != 탭:
            raise 요청오류(409, "이 캐릭터가 다른 탭에서 열려 있어 저장하지 않습니다.")

    def 작성중쓰기(self, 이름, 번호, 몸: dict) -> dict:
        """작성중.json(2-1)과 취소 기록(작성중_기록.json, 페이지만 쓰고 읽음)을 쓴다."""
        self._주인확인(몸.get("탭"), 이름)
        표시 = self._표시검사(몸.get("표시", []), 번호)
        판단 = self._후보판단검사(몸.get("후보판단", []))
        기록값 = 몸.get("기록")
        if 기록값 is not None and (not isinstance(기록값, dict) or not all(isinstance(기록값.get(k, []), list) for k in ("취소", "다시"))):
            raise 요청오류(400, "'기록'은 {취소: [...], 다시: [...]} 꼴이어야 합니다.")
        d = self.단계폴더(이름, 번호, 만들기=True)
        c = self.캐릭터폴더(이름)
        p = d / "작성중.json"
        for q in (p, d / "작성중_기록.json"):
            if q.exists() and not self._안전한파일(q, c):
                raise 요청오류(409, f"{q.name}이 일반 파일이 아닙니다(링크).")
        with 파일잠금(p):
            if 몸.get("묶음번호") is not None:  # 그사이 보냈으면(다른 창에서) 옛 작성 중으로 덮지 않는다
                전 = json_읽기(p) if p.is_file() else {}
                if 전.get("묶음번호", 0) != 몸["묶음번호"]:
                    raise 요청오류(409, "그사이 이 단계의 표시를 보냈습니다. 화면을 다시 읽습니다.")
            값 = {"꼴버전": 꼴버전, "만든시각": 지금(), "작업본해시": self._지금작업본해시(이름), "단계": 번호,
                  "묶음상태": "작성 중", "표시": 표시, "후보판단": 판단, "결정": "없음",
                  "다음번호": 몸.get("다음번호") if isinstance(몸.get("다음번호"), int) else len(표시) + 1,
                  "묶음번호": 몸.get("묶음번호") if isinstance(몸.get("묶음번호"), int) else 0}
            json_쓰기(p, 값)
            if 기록값 is not None:
                json_쓰기(d / "작성중_기록.json", {"꼴버전": 꼴버전, "만든시각": 값["만든시각"], "작업본해시": 값["작업본해시"],
                                               "취소": 기록값.get("취소", [])[-취소한도:], "다시": 기록값.get("다시", [])[-취소한도:]})
        return {"됨": True, "만든시각": 값["만든시각"]}

    def 보내기쓰기(self, 이름, 번호, 몸: dict) -> dict:
        """보내기_<시각>.json을 쓰고 작성 중을 비운다(취소 기록도 여기서 끊긴다). 앞 묶음이 아직 '보냄'이면
        '합치기'(참/거짓)를 꼭 받는다(화면이 사용자에게 물은 답)."""
        self._주인확인(몸.get("탭"), 이름)
        표시 = self._표시검사(몸.get("표시", []), 번호)
        판단 = self._후보판단검사(몸.get("후보판단", []))
        멈춤답 = 메시단계.멈춤답검사(self, 이름, 몸, 판단) if 번호 == 메시단계.번호 else None  # W11: 멈춤 1의 대칭 답(후보가 없어도 보냄)
        if not 표시 and not 판단 and not 멈춤답:
            raise 요청오류(400, "보낼 것이 없습니다.")
        빈메모 = [x["번호"] for x in 표시 if x["종류"] in 메모필수종류 and not str(x.get("메모", "")).strip()]
        if 빈메모:
            raise 요청오류(400, f"'기타'는 메모가 있어야 보낼 수 있습니다: {', '.join(빈메모)}")
        d = self.단계폴더(이름, 번호, 만들기=True)
        c = self.캐릭터폴더(이름)
        p = d / "작성중.json"
        with 파일잠금(p):
            전작성 = json_읽기(p) if self._안전한파일(p, c) else {}
            if 몸.get("묶음번호", 0) != 전작성.get("묶음번호", 0):
                raise 요청오류(409, "그사이 이 단계의 표시를 보냈습니다. 화면을 다시 읽습니다.")
            남은 = []
            for q in sorted(d.glob("보내기_*.json")):
                try:
                    if self._안전한파일(q, c) and json_읽기(q).get("묶음상태") == "보냄":
                        남은.append(q.name)
                except Exception:
                    pass
            합치기 = 몸.get("합치기")
            if 남은 and not isinstance(합치기, bool):
                raise 요청오류(409, f"앞 묶음을 아직 처리하지 않았습니다: {', '.join(남은)}. 합칠지 따로 보낼지 정해 주세요.")
            합친 = 남은 if 합치기 else []
            if 합친:  # 앞 묶음의 표시·판단을 이 묶음에 함께 넣는다(앞 묶음 파일은 그대로 둔다. 에이전트는 합친묶음을 건너뜀)
                옛표시, 옛판단 = [], []
                for q in 합친:
                    v = json_읽기(d / q)
                    옛표시 += [x for x in v.get("표시") or [] if isinstance(x, dict)]
                    옛판단 += [x for x in v.get("후보판단") or [] if isinstance(x, dict)]
                지금번호 = {x["번호"] for x in 표시}
                표시 = [x for x in 옛표시 if x.get("번호") not in 지금번호] + 표시
                지금판단 = {(x["후보파일"], x["번호"]) for x in 판단}
                판단 = [x for x in 옛판단 if (x.get("후보파일"), x.get("번호")) not in 지금판단] + 판단
            시각 = 지금(파일용=True)
            q, k = d / f"보내기_{시각}.json", 2
            while q.exists():
                q, k = d / f"보내기_{시각}_{k}.json", k + 1
            값 = {"꼴버전": 꼴버전, "만든시각": 지금(), "작업본해시": self._지금작업본해시(이름), "단계": 번호,
                  "묶음상태": "보냄", "표시": 표시, "후보판단": 판단, "결정": "없음", "합친묶음": 합친}
            if 멈춤답:
                값["멈춤답"] = 멈춤답
            json_쓰기(q, 값)
            json_쓰기(p, {"꼴버전": 꼴버전, "만든시각": 지금(), "작업본해시": 값["작업본해시"], "단계": 번호,
                          "묶음상태": "작성 중", "표시": [], "후보판단": [], "결정": "없음",
                          "다음번호": 몸.get("다음번호") if isinstance(몸.get("다음번호"), int) else 1,
                          "묶음번호": 전작성.get("묶음번호", 0) + 1})
            기록p = d / "작성중_기록.json"
            if self._안전한파일(기록p, c):
                기록p.unlink()
        if 멈춤답:
            메시단계.확정쓰기(self, 이름, 멈춤답, q.name)
        기록(f"보냄: {번호}단계 {q.name} (표시 {len(표시)}, 후보 판단 {len(판단)}, 합침 {합친})", self, 이름)
        return {"됨": True, "파일": q.relative_to(self.폴더).as_posix(), "표시수": len(표시), "판단수": len(판단)}

    # ---- 결정 칸과 에이전트 약속 (W06, 기능명세 1부 2-1·3·4-4·7·7-1). 에이전트 명령(`에이전트.py`)도 이 함수들을 쓴다.

    def 묶음들(self, 이름, 번호) -> list[tuple[Path, dict]]:
        """그 단계의 보내기 묶음(파일 이름 순 = 보낸 순)."""
        d = self.단계폴더(이름, 번호, 만들기=False)
        c = self.캐릭터폴더(이름)
        목록 = []
        if not d.is_dir():
            return 목록
        for q in sorted(d.glob("보내기_*.json")):
            if not self._안전한파일(q, c):
                continue
            try:
                v = json_읽기(q)
            except Exception:
                continue
            if isinstance(v, dict):
                목록.append((q, v))
        return 목록

    def 밀린묶음(self, 이름, 번호) -> list[str]:
        """보냈는데 처리가 끝나지 않은 묶음("보냄"·"처리 중")."""
        return [q.name for q, v in self.묶음들(이름, 번호) if v.get("묶음상태") in ("보냄", "처리 중")]

    def 묶음상태쓰기(self, 이름, 번호, 파일: str, 새상태: str, 더할것: dict | None = None) -> list[str]:
        """묶음 하나와, 그 묶음에 합쳐진 앞 묶음들의 상태를 바꾼다(7절 6번: 페이지 파일 가운데 에이전트가 바꾸는 유일한 값).
        합쳐진 앞 묶음에는 `합쳐진곳`을 적는다. 바꾼 파일 이름 목록을 돌려준다."""
        if 새상태 not in 묶음상태들:
            raise 요청오류(400, f"모르는 묶음 상태: {새상태}")
        if not isinstance(파일, str) or not re.fullmatch(r"보내기_[0-9T_-]+\.json", 파일):
            raise 요청오류(400, f"묶음 파일 이름이 잘못됨: {파일!r}")
        d = self.단계폴더(이름, 번호, 만들기=False)
        c = self.캐릭터폴더(이름)
        q = d / 파일
        if not self._안전한파일(q, c):
            raise 요청오류(404, f"묶음이 없습니다: {파일}")
        바꾼 = []
        with 파일잠금(q):
            v = json_읽기(q)
            v["묶음상태"] = 새상태
            v.update(더할것 or {})
            json_쓰기(q, v)
        바꾼.append(파일)
        for 앞 in v.get("합친묶음") or []:
            p = d / str(앞)
            if re.fullmatch(r"보내기_[0-9T_-]+\.json", str(앞)) and self._안전한파일(p, c):
                with 파일잠금(p):
                    w = json_읽기(p)
                    w["묶음상태"] = 새상태
                    w["합쳐진곳"] = 파일
                    json_쓰기(p, w)
                바꾼.append(str(앞))
        기록(f"묶음 상태: {번호}단계 {', '.join(바꾼)} → {새상태}", self, 이름)
        return 바꾼

    def 알림읽기(self, 이름, 번호) -> dict | None:
        try:
            d = self.단계폴더(이름, 번호, 만들기=False)
        except 요청오류:
            return None
        p = d / "알림.json"
        if not self._안전한파일(p, self.캐릭터폴더(이름)):
            return None
        try:
            v = json_읽기(p)
            return v if isinstance(v, dict) else None
        except Exception:
            return None

    def 알림쓰기(self, 이름, 번호, 글, 종류: str = "안내") -> dict:
        """알림.json을 쓴다. 앞 알림은 알림기록.json의 `기록`에 쌓는다(2-1)."""
        if 종류 not in 알림종류:
            raise 요청오류(400, f"알림 종류는 {' / '.join(알림종류)} 가운데 하나: {종류!r}")
        if not isinstance(글, str) or not 글.strip() or len(글) > 2000:
            raise 요청오류(400, "알림 글이 비었거나 너무 깁니다(2000자까지).")
        d = self.단계폴더(이름, 번호, 만들기=True)
        c = self.캐릭터폴더(이름)
        p, 쌓을곳 = d / "알림.json", d / "알림기록.json"
        for q in (p, 쌓을곳):
            if q.exists() and not self._안전한파일(q, c):
                raise 요청오류(409, f"{q.name}이 일반 파일이 아닙니다(링크).")
        값 = {"꼴버전": 꼴버전, "만든시각": 지금(), "작업본해시": self._지금작업본해시(이름), "단계": 번호,
              "글": 글.strip(), "종류": 종류}
        with 파일잠금(p):
            전 = self.알림읽기(이름, 번호)
            if 전:
                with 파일잠금(쌓을곳):
                    try:
                        쌓기 = json_읽기(쌓을곳) if 쌓을곳.is_file() else {}
                    except Exception:
                        쌓기 = {}
                    if not isinstance(쌓기, dict) or not isinstance(쌓기.get("기록"), list):
                        쌓기 = {"꼴버전": 꼴버전, "만든시각": 지금(), "작업본해시": 값["작업본해시"], "단계": 번호, "기록": []}
                    쌓기["기록"].append(전)
                    json_쓰기(쌓을곳, 쌓기)
            json_쓰기(p, 값)
        기록(f"알림: {번호}단계 [{종류}] {글.strip()[:80]}", self, 이름)
        return 값

    def 작업본파일(self, 이름) -> Path | None:
        p = self.상태파일(이름)
        if not p.is_file():
            return None
        try:
            return self.저장소파일(json_읽기(p).get("작업본"))
        except Exception:
            return None

    def 되돌리기폴더(self, 이름, 번호, 만들기: bool) -> Path:
        d = self.단계폴더(이름, 번호, 만들기=만들기) / "되돌리기"
        if d.exists() and (not d.is_dir() or d.is_symlink() or not self.안쪽인가(d, self.캐릭터폴더(이름))):
            raise 요청오류(409, "되돌리기 폴더가 캐릭터 폴더 밖을 가리킵니다.")
        if 만들기:
            d.mkdir(exist_ok=True)
        return d

    def 되돌리기목록(self, 이름, 번호) -> list[dict]:
        """사본 목록, 새것 먼저. 사본마다 옆의 같은 이름 .json에 그때의 알림·까닭·해시."""
        d = self.되돌리기폴더(이름, 번호, 만들기=False)
        c = self.캐릭터폴더(이름)
        if not d.is_dir():
            return []
        목록 = []
        for q in sorted(d.glob("*.blend"), reverse=True):
            if not re.fullmatch(r"[0-9T_-]+\.blend", q.name) or not self._안전한파일(q, c):
                continue
            정보 = {}
            m = q.with_suffix(".json")
            if self._안전한파일(m, c):
                try:
                    정보 = json_읽기(m)
                except Exception:
                    정보 = {}
            목록.append({"파일": q.name, "경로": q.relative_to(self.폴더).as_posix(), "시각": 정보.get("만든시각") or q.stem,
                       "알림": 정보.get("알림") or "", "까닭": 정보.get("까닭") or "", "작업본해시": 정보.get("작업본해시") or "",
                       "크기": q.stat().st_size})
        return 목록

    def 사본만들기(self, 이름, 번호, 까닭: str) -> dict:
        """작업본을 `되돌리기/<시각>.blend`로 복사한다(7절 2번). 디스크가 모자라면 만들지 않는다(8절).
        사본이 10개를 넘으면 지울 후보만 돌려준다(지우지 않음)."""
        f = self.작업본파일(이름)
        if not f:
            raise 요청오류(409, "상태.json의 작업본이 없거나 저장소 밖입니다. 사본을 만들지 않습니다.")
        d = self.되돌리기폴더(이름, 번호, 만들기=True)
        크기 = f.stat().st_size
        남은 = shutil.disk_usage(d).free
        if 남은 < 크기 + 사본여유:
            raise 요청오류(507, f"디스크 공간이 모자랍니다(남은 {남은 // (1 << 20)}MB, 필요 {(크기 + 사본여유) // (1 << 20)}MB). 고치지 마세요.")
        시각 = 지금(파일용=True)
        q, k = d / f"{시각}.blend", 2
        while q.exists() or q.with_suffix(".json").exists():
            q, k = d / f"{시각}_{k}.blend", k + 1
        원해시 = 파일해시(f)
        임시 = q.with_name(q.name + ".쓰는중")
        shutil.copy2(f, 임시)
        os.replace(임시, q)
        새해시 = 파일해시(q)
        if 새해시 != 원해시:
            q.unlink()
            raise 요청오류(500, "사본이 원본과 다릅니다(복사 중 작업본이 바뀜). 다시 해 주세요.")
        알림 = self.알림읽기(이름, 번호) or {}
        with 파일잠금(q.with_suffix(".json")):
            json_쓰기(q.with_suffix(".json"), {"꼴버전": 꼴버전, "만든시각": 지금(), "작업본해시": 새해시, "단계": 번호,
                                              "작업본": f.relative_to(self.폴더).as_posix(), "까닭": 까닭, "알림": 알림.get("글", "")})
        목록 = self.되돌리기목록(이름, 번호)
        기록(f"되돌리기 사본: {번호}단계 {q.name} ({까닭}, {새해시})", self, 이름)
        return {"파일": q.relative_to(self.폴더).as_posix(), "작업본해시": 새해시, "사본수": len(목록),
                "지울후보": [x["경로"] for x in 목록[사본한도:]]}

    def 완료모자람(self, 이름, 번호) -> list[str]:
        """'이 단계 끝'에서 모자란 것(4-4). 2부의 단계별 완료 조건은 단계 화면(W09~W14)이 `단계완료검사`에 붙인다."""
        모자람 = []
        try:
            d = self.단계폴더(이름, 번호, 만들기=False)
            p = d / "작성중.json"
            if self._안전한파일(p, self.캐릭터폴더(이름)):
                n = len(json_읽기(p).get("표시") or [])
                if n:
                    모자람.append(f"보내지 않은 표시 {n}개가 작성 중으로 남아 있음")
        except (요청오류, OSError, ValueError):
            pass
        검사 = 단계완료검사.get(번호)
        if 검사:
            모자람 += 검사(self, 이름)
        return 모자람

    def 결정보기(self, 이름, 번호) -> dict:
        """결정 칸이 그릴 것: 알림, 묶음 상태, 되돌리기 목록, 단계 상태."""
        지금h = self._지금작업본해시(이름)
        알림 = self.알림읽기(이름, 번호)
        if 알림:
            h = 알림.get("작업본해시") or ""
            알림 = {"글": 알림.get("글") or "", "종류": 알림.get("종류") if 알림.get("종류") in 알림종류 else "안내",
                  "시각": 알림.get("만든시각") or "", "옛것": bool(h and 지금h and h != 지금h)}
        묶음 = self.묶음들(이름, 번호)
        다시보낸 = {v.get("다시보낸묶음") for _, v in 묶음}
        보기 = self.상태보기(이름)
        줄 = 보기["단계"][번호 - 1]
        진행중 = [f"{x['번호']}단계" for x in 보기["단계"] if x["상태"] == "진행 중"]
        return {"단계": 번호, "상태": 줄["상태"], "알림": 알림, "작업본해시": 지금h,
                "밀린묶음": [q.name for q, v in 묶음 if v.get("묶음상태") in ("보냄", "처리 중")],
                "처리중": [q.name for q, v in 묶음 if v.get("묶음상태") == "처리 중"] + 진행중,
                "실패묶음": [q.name for q, v in 묶음 if v.get("묶음상태") == "실패" and q.name not in 다시보낸],
                "되돌리기": self.되돌리기목록(이름, 번호) if 보기["있음"] else [],
                "작업본있음": bool(self.작업본파일(이름)),
                "승인": 승인.보기(self, 이름, 번호) if 보기["있음"] else None}

    def 결정바뀜(self, 이름, 번호) -> str:
        """결정 칸을 다시 읽을지 정할 값: 알림·묶음·처리·되돌리기 파일."""
        try:
            d = self.단계폴더(이름, 번호, 만들기=False)
        except 요청오류:
            return ""
        if not d.is_dir():
            return ""
        조각 = [f"{p.name}:{p.stat().st_mtime_ns}" for p in sorted(d.iterdir())
               if p.is_file() and (p.name == "알림.json" or p.name.startswith(("보내기_", "처리_", "승인_")))]
        r = d / "되돌리기"
        if r.is_dir():
            조각 += [f"r/{p.name}:{p.stat().st_mtime_ns}" for p in sorted(r.iterdir()) if p.is_file()]
        return hashlib.sha256("|".join(조각).encode()).hexdigest()[:12] if 조각 else ""

    def 결정쓰기(self, 이름, 번호, 몸: dict) -> dict:
        """결정 단추(4-4): 이 단계 끝 / 그래도 끝 / 고쳐 줘."""
        self._주인확인(몸.get("탭"), 이름)
        결정 = 몸.get("결정")
        if 결정 in ("이 단계 끝", "그래도 끝"):
            밀림 = self.밀린묶음(이름, 번호)
            if 밀림:
                raise 요청오류(409, f"보내고 처리되지 않은 묶음이 있어 끝으로 할 수 없습니다: {', '.join(밀림)}")
            모자람 = self.완료모자람(이름, 번호)
            if 모자람 and 결정 == "이 단계 끝":
                return {"됨": False, "모자람": 모자람}
            새 = "끝(조건 미달)" if 모자람 else "끝"
            self.단계상태쓰기(이름, 번호, {"상태": 새})
            기록(f"결정: {번호}단계 {결정} → {새} {모자람 or ''}".rstrip(), self, 이름)
            return {"됨": True, "상태": 새, "모자람": 모자람}
        if 결정 == "고쳐 줘":
            self.단계상태쓰기(이름, 번호, {"상태": "결정 대기"})
            기록(f"결정: {번호}단계 고쳐 줘", self, 이름)
            return {"됨": True, "상태": "결정 대기", "글": "Claude 앱에서 무엇을 고칠지 말씀해 주세요."}
        raise 요청오류(400, f"모르는 결정: {결정!r}")

    def 뒤단계바뀜(self, 이름, 번호) -> list[int]:
        """되돌리기 뒤: 시작한 뒤 단계마다 '앞 단계가 바뀜'(4-4)."""
        p = self.상태파일(이름)
        바꾼 = []
        with 파일잠금(p):
            값 = json_읽기(p)
            for c in 값.get("단계") or []:
                if isinstance(c, dict) and isinstance(c.get("번호"), int) and c["번호"] > 번호 and c.get("상태") in 시작한상태:
                    표시 = c.setdefault("표시", [])
                    if "앞 단계가 바뀜" not in 표시:
                        표시.append("앞 단계가 바뀜")
                        c["바뀐시각"] = 지금()
                        바꾼.append(c["번호"])
            if 바꾼:
                json_쓰기(p, 값)
        return 바꾼

    def 되돌리기쓰기(self, 이름, 번호, 몸: dict) -> dict:
        """고른 사본으로 작업본을 바꾼다. 바꾸기 전 작업본도 사본으로 남긴다(4-4, 1부 9절 10번)."""
        self._주인확인(몸.get("탭"), 이름)
        파일 = 몸.get("사본")
        if not isinstance(파일, str) or not re.fullmatch(r"[0-9T_-]+\.blend", 파일):
            raise 요청오류(400, "고른 사본 이름이 잘못됐습니다.")
        보기 = self.상태보기(이름)
        진행중 = [f"{x['번호']}단계" for x in 보기["단계"] if x["상태"] == "진행 중"]
        처리중 = [q.name for q, v in self.묶음들(이름, 번호) if v.get("묶음상태") == "처리 중"]
        if 진행중 or 처리중:
            raise 요청오류(409, f"에이전트가 처리 중이라 되돌리지 않습니다: {', '.join(진행중 + 처리중)}")
        d = self.되돌리기폴더(이름, 번호, 만들기=False)
        고른 = d / 파일
        if not self._안전한파일(고른, self.캐릭터폴더(이름)):
            raise 요청오류(404, f"사본이 없습니다: {파일}")
        f = self.작업본파일(이름)
        if not f:
            raise 요청오류(409, "상태.json의 작업본이 없습니다.")
        남긴 = self.사본만들기(이름, 번호, f"되돌리기 전 작업본({파일}로 바꾸기 전)")
        목표 = 파일해시(고른)
        임시 = f.with_name(f.name + ".되돌리는중")
        shutil.copyfile(고른, 임시)
        os.replace(임시, f)
        os.utime(f)  # 수정 시각을 지금으로(화면이 작업본 바뀜을 알아채게)
        if 파일해시(f) != 목표:
            raise 요청오류(500, "되돌린 작업본이 사본과 다릅니다. 남긴 사본으로 다시 되돌려 주세요: " + 남긴["파일"])
        self.단계상태쓰기(이름, 번호, {"상태": "결정 대기", "출처": "이 페이지(되돌리기)"})
        뒤 = self.뒤단계바뀜(이름, 번호)
        기록(f"되돌림: {번호}단계 {파일} → 작업본 {목표}, 앞 작업본은 {남긴['파일']}, 뒤 단계 표시 {뒤}", self, 이름)
        return {"됨": True, "되돌린사본": 고른.relative_to(self.폴더).as_posix(), "남긴사본": 남긴["파일"],
                "작업본해시": 목표, "뒤단계": 뒤, "지울후보": 남긴["지울후보"]}

    def 다시보내기쓰기(self, 이름, 번호, 몸: dict) -> dict:
        """'실패'한 묶음을 같은 내용으로 새 묶음으로 보낸다(3-2: 실패한 묶음은 다시 보낼 수 있음)."""
        self._주인확인(몸.get("탭"), 이름)
        파일 = 몸.get("묶음")
        짝 = {q.name: (q, v) for q, v in self.묶음들(이름, 번호)}
        if 파일 not in 짝 or 짝[파일][1].get("묶음상태") != "실패":
            raise 요청오류(400, "실패한 묶음이 아닙니다.")
        밀림 = self.밀린묶음(이름, 번호)
        if 밀림:
            raise 요청오류(409, f"앞 묶음을 아직 처리하지 않았습니다: {', '.join(밀림)}")
        d = self.단계폴더(이름, 번호, 만들기=False)
        옛 = 짝[파일][1]
        시각 = 지금(파일용=True)
        q, k = d / f"보내기_{시각}.json", 2
        while q.exists():
            q, k = d / f"보내기_{시각}_{k}.json", k + 1
        with 파일잠금(q):
            json_쓰기(q, {"꼴버전": 꼴버전, "만든시각": 지금(), "작업본해시": self._지금작업본해시(이름), "단계": 번호,
                          "묶음상태": "보냄", "표시": 옛.get("표시") or [], "후보판단": 옛.get("후보판단") or [],
                          "결정": "없음", "합친묶음": [], "다시보낸묶음": 파일})
        기록(f"다시 보냄: {번호}단계 {파일} → {q.name}", self, 이름)
        return {"됨": True, "파일": q.relative_to(self.폴더).as_posix()}

    # ---- 이 PC에만 해당하는 것

    # ---- 부위 목록 (W05, 기능명세 1부 5-2b, 2-1 "부위.json"). 만드는 것은 에이전트(`부위만들기.py`), 페이지는 읽기와 이름 바꾸기만

    def 부위파일(self, 이름) -> Path:
        return self.제작페이지폴더(이름, 만들기=False) / "부위.json"

    def 부위읽기(self, 이름) -> dict:
        p = self.부위파일(이름)
        지금h = self._지금작업본해시(이름)
        if not p.exists():
            return {"있음": False, "지금해시": 지금h, "부위": []}
        if not self._안전한파일(p, self.캐릭터폴더(이름)):
            raise 요청오류(409, "부위.json이 일반 파일이 아닙니다(링크).")
        try:
            v = json_읽기(p)
        except Exception as e:
            return {"있음": True, "오류": f"부위.json을 읽지 못함: {e}", "지금해시": 지금h, "부위": []}
        부위 = [r for r in (v.get("부위") or []) if isinstance(r, dict) and isinstance(r.get("면"), list)
              and isinstance(r.get("파츠"), str) and isinstance(r.get("이름"), str)]
        h = v.get("작업본해시") or ""
        return {"있음": True, "작업본해시": h, "지금해시": 지금h, "옛것": bool(지금h) and h != 지금h,
                "만든시각": v.get("만든시각"), "부위": [{k: r.get(k) for k in ("번호", "이름", "파츠", "면", "사용자가바꾼이름", "자동이름")}
                                                    for r in 부위]}

    def 부위이름쓰기(self, 이름, 몸: dict) -> dict:
        """이름 바꾸기. 빈 이름이면 자동 이름으로 되돌린다. 다시 만들 때 이어받도록 사용자가바꾼이름을 켠다."""
        self._주인확인(몸.get("탭"), 이름)
        번호, 새 = 몸.get("번호"), 몸.get("새이름")
        if not isinstance(번호, int) or isinstance(번호, bool):
            raise 요청오류(400, "부위 번호가 없습니다.")
        if not isinstance(새, str):
            raise 요청오류(400, "새 이름이 글이 아닙니다.")
        새 = " ".join(새.split())
        if len(새) > 40 or any(c in 새 for c in "›<>"):
            raise 요청오류(400, "이름은 40자까지, › < > 는 쓸 수 없습니다.")
        p = self.부위파일(이름)
        if not p.exists() or not self._안전한파일(p, self.캐릭터폴더(이름)):
            raise 요청오류(404, "부위 목록이 없습니다.")
        with 파일잠금(p):
            v = json_읽기(p)
            if 몸.get("작업본해시") is not None and 몸.get("작업본해시") != (v.get("작업본해시") or ""):
                raise 요청오류(409, "그사이 부위 목록을 다시 만들었습니다. 목록을 다시 읽습니다.")
            r = next((r for r in v.get("부위") or [] if isinstance(r, dict) and r.get("번호") == 번호), None)
            if r is None:
                raise 요청오류(404, "그 번호의 부위가 없습니다.")
            if 새 and 새 != r.get("이름") and any(x is not r and x.get("파츠") == r.get("파츠") and x.get("이름") == 새 for x in v["부위"]):
                raise 요청오류(400, f"같은 파츠에 '{새}'가 이미 있습니다.")
            if 새 and 새 != r.get("자동이름"):
                r["이름"], r["사용자가바꾼이름"] = 새, True
            else:
                r["이름"], r["사용자가바꾼이름"] = r.get("자동이름") or r.get("이름"), False
            json_쓰기(p, v)
        return {"됨": True, "이름": r["이름"], "사용자가바꾼이름": r["사용자가바꾼이름"]}

    def 기억읽기(self) -> dict:
        try:
            return json_읽기(로컬 / "기억.json").get(str(self.폴더), {})
        except Exception:
            return {}

    def 기억쓰기(self, 캐릭터, 단계) -> None:
        로컬.mkdir(exist_ok=True)
        p = 로컬 / "기억.json"
        with 파일잠금(p):
            try:
                모두 = json_읽기(p)
            except Exception:
                모두 = {}
            if 모두.get(str(self.폴더)) == {"캐릭터": 캐릭터, "단계": 단계}:
                return
            모두[str(self.폴더)] = {"캐릭터": 캐릭터, "단계": 단계}
            json_쓰기(p, 모두)

    def 잔액(self) -> dict:
        """TRIPO 잔액은 서버가 마지막으로 기록한 값만 보인다(바깥에 묻지 않음). 기록은 W07이 쓴다."""
        return 승인.잔액기록읽기()  # W07: 가짜 실행 모드면 가짜 잔액(`가짜`: 참)

    # ---- 여러 탭 (기능명세 1부 6절): 먼저 연 탭이 놓거나(닫힘) 오래 소식이 없을 때까지 주인

    def 탭알림(self, 탭: str, 캐릭터: str | None, 놓기: bool) -> dict:
        t = time.monotonic()
        with self.탭잠금:
            for 무리 in self.탭.values():
                for k in [k for k, v in 무리.items() if t - v["마지막"] > 탭유효초]:
                    del 무리[k]
            for 이름, 무리 in self.탭.items():
                if 이름 != 캐릭터 or 놓기:
                    무리.pop(탭, None)
            if 놓기 or not 캐릭터 or not 탭:
                return {"주인": True, "다른탭": 0}
            무리 = self.탭.setdefault(캐릭터, {})
            if 탭 not in 무리:
                무리[탭] = {"처음": t, "마지막": t}
            무리[탭]["마지막"] = t
            주인 = min(무리, key=lambda k: 무리[k]["처음"])
            return {"주인": 주인 == 탭, "다른탭": len(무리) - 1}

    def 바뀜표(self, 캐릭터: str | None) -> dict:
        """화면이 다시 읽을지 정할 값: 상태.json과 작업본의 수정 시각."""
        if 캐릭터 is None:
            return {}
        p = self.상태파일(캐릭터)
        표 = {"상태": p.stat().st_mtime_ns if p.is_file() else 0, "작업본": 0}
        try:
            q = self.부위파일(캐릭터)
            표["부위"] = q.stat().st_mtime_ns if q.is_file() else 0
        except (요청오류, OSError):
            표["부위"] = 0
        if p.is_file():
            try:
                f = self.저장소파일(json_읽기(p).get("작업본"))
                표["작업본"] = f.stat().st_mtime_ns if f else 0
            except Exception:
                pass
        return 표

    def 진행중인단계(self) -> tuple[list[str], list[str]]:
        """(진행 중인 단계, 점검하지 못한 캐릭터)."""
        남은, 못봄 = [], []
        for n in self.캐릭터들():
            try:
                보기 = self.상태보기(n)
                for 줄 in 보기["단계"]:
                    if 줄["상태"] == "진행 중":
                        남은.append(f"{n} {줄['번호']} {줄['이름']}")
                if 보기["있음"] and (보기["오류"] or any(줄["상태"] == "알 수 없음" for 줄 in 보기["단계"])):
                    못봄.append(n)  # 깨진 상태 파일: 진행 중인지 알 수 없음
            except Exception:
                못봄.append(n)
        return 남은, 못봄


# ---------------------------------------------------------------- HTTP


mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/javascript", ".mjs")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("model/gltf-binary", ".glb")


동작쓰기 = {  # W14: 10·11단계 페이지 단추(POST)
    "/api/동작/고르기": 동작단계.고르기, "/api/동작/옮기기": 동작단계.옮기기요청,
    "/api/내보내기/경로": 동작단계.경로정하기, "/api/내보내기/요청": 동작단계.내보내기요청, "/api/내보내기/봄": 동작단계.봄쓰기,
}


def 처리기만들기(a: 앱):
    class 처리기(BaseHTTPRequestHandler):
        server_version = "GamaujiPage/W00"

        def log_message(self, fmt, *args):  # 터미널을 조용히(요청마다 찍지 않음)
            pass

        # -- 공통 검사: 이 PC의 주소로 온 요청만 받는다(DNS 다시 묶기 막음)
        def _주소확인(self) -> bool:
            host = (self.headers.get("Host") or "").lower()
            if host not in {f"127.0.0.1:{a.포트}", f"localhost:{a.포트}"}:
                self._보내기(403, {"오류": "이 PC의 주소(127.0.0.1)로만 엽니다."})
                return False
            return True

        def _보내기(self, 코드: int, 값, 종류: str = "application/json; charset=utf-8"):
            몸 = 값 if isinstance(값, bytes) else json.dumps(값, ensure_ascii=False).encode("utf-8")
            self.send_response(코드)
            self.send_header("Content-Type", 종류)
            self.send_header("Content-Length", str(len(몸)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            # 다른 사이트의 페이지 안에 이 화면을 넣지 못하게 한다
            self.send_header("Content-Security-Policy", "frame-ancestors 'none'")
            self.send_header("X-Frame-Options", "DENY")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(몸)

        def _파일(self, p: Path):
            try:
                몸 = p.read_bytes()
            except OSError:
                return self._보내기(404, {"오류": "파일이 없습니다."})
            종류 = "model/gltf-binary" if p.suffix == ".glb" else (mimetypes.guess_type(p.name)[0] or "application/octet-stream")
            if 종류.startswith("text/") or 종류 in ("application/json", "image/svg+xml"):
                종류 += "; charset=utf-8"
            self._보내기(200, 몸, 종류)

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            if not self._주소확인():
                return
            u = urllib.parse.urlsplit(self.path)
            경로 = urllib.parse.unquote(u.path)
            질문 = urllib.parse.parse_qs(u.query)
            try:
                if 경로 in ("/", "/index.html"):
                    return self._파일(정적 / "index.html")
                if 경로 == "/디자인토큰.css":
                    return self._파일(토큰파일)
                if 경로.startswith("/정적/"):
                    p = (정적 / 경로[len("/정적/"):]).resolve()
                    if not p.is_relative_to(정적.resolve()) or not p.is_file():
                        return self._보내기(404, {"오류": "파일이 없습니다."})
                    return self._파일(p)
                if 경로 == "/api/정보":
                    return self._보내기(200, {
                        "프로그램": 프로그램, "판": 판, "주소": 주소, "포트": a.포트,
                        "폴더": str(a.폴더), "pid": os.getpid(),
                        "단계목록": [{"번호": i + 1, "열쇠": k, "이름": n, "처리": 처리목록.get(i + 1, [])} for i, (k, n) in enumerate(단계목록)],
                        "메모필수": 메모필수종류, "취소한도": 취소한도, "실행모드": 승인.모드,
                    })
                if 경로 == "/api/캐릭터":
                    return self._보내기(200, {"캐릭터": a.캐릭터목록(), "기억": a.기억읽기(), "잔액": a.잔액()})
                if 경로 == "/api/모델":
                    return self._보내기(200, a.모델((질문.get("이름") or [None])[0], 다시=(질문.get("다시") or [""])[0] == "1"))
                if 경로.startswith("/보기/"):
                    조각 = 경로[len("/보기/"):].split("/")
                    if len(조각) != 2:
                        return self._보내기(404, {"오류": "없는 주소입니다."})
                    return self._파일(a.보기파일(조각[0], 조각[1]))
                if 경로 == "/api/생성단계":  # W10: 2·4·5·6단계 옆 기둥
                    try:
                        n = int((질문.get("단계") or ["0"])[0])
                    except ValueError:
                        n = 0
                    return self._보내기(200, 생성단계.보기(a, (질문.get("이름") or [None])[0], n))
                if 경로 == "/api/메시":  # W11: 3단계 옆 기둥
                    return self._보내기(200, 메시단계.보기(a, (질문.get("이름") or [None])[0]))
                if 경로 == "/api/리깅":  # W13: 8·9단계 옆 기둥·시간 막대
                    try:
                        n = int((질문.get("단계") or ["0"])[0])
                    except ValueError:
                        n = 0
                    return self._보내기(200, 리깅단계.보기(a, (질문.get("이름") or [None])[0], n))
                if 경로 == "/api/동작":  # W14: 10·11단계 옆 기둥
                    try:
                        n = int((질문.get("단계") or ["0"])[0])
                    except ValueError:
                        n = 0
                    return self._보내기(200, 동작단계.보기(a, (질문.get("이름") or [None])[0], n))
                if 경로 == "/api/동작/파일":  # W14: 동작 모음 GLB·미리 보기 GLB
                    q = lambda k: (질문.get(k) or [None])[0]
                    a.캐릭터폴더(q("이름"))
                    return self._파일(동작단계.파일(a, q("이름"), q("종류") or "", q("해시")))
                if 경로 == "/api/텍스처":  # W12: 7단계 옆 기둥
                    return self._보내기(200, 텍스처단계.보기(a, (질문.get("이름") or [None])[0]))
                if 경로 == "/api/상태":
                    return self._보내기(200, a.상태보기((질문.get("이름") or [None])[0]))
                if 경로 == "/api/부위":
                    return self._보내기(200, a.부위읽기((질문.get("이름") or [None])[0]))
                if 경로 == "/api/결정":
                    단 = (질문.get("단계") or [""])[0]
                    return self._보내기(200, a.결정보기((질문.get("이름") or [None])[0], int(단) if 단.isdigit() else None))
                if 경로 == "/api/가져오기":
                    return self._보내기(200, 가져오기.보기(a, (질문.get("번호") or [None])[0]))
                if 경로 == "/api/가져오기/그림":
                    return self._파일(가져오기.그림파일((질문.get("번호") or [None])[0], (질문.get("면") or [None])[0]))
                if 경로 == "/api/가져온것":
                    단 = (질문.get("단계") or [""])[0]
                    return self._보내기(200, 가져오기.넣은것보기(a, (질문.get("이름") or [None])[0], int(단) if 단.isdigit() else None))
                if 경로 == "/api/가져온것/그림":
                    q = lambda k: (질문.get(k) or [None])[0]
                    return self._파일(가져오기.넣은그림파일(a, q("이름"), q("폴더"), q("면")))
                if 경로 == "/api/그림":
                    return self._보내기(200, 그림단계.보기(a, (질문.get("이름") or [None])[0]))
                if 경로 == "/api/그림/파일":
                    return self._파일(그림단계.그림파일(a, (질문.get("경로") or [""])[0]))
                if 경로 == "/api/표시":
                    단 = (질문.get("단계") or [""])[0]
                    return self._보내기(200, a.표시읽기((질문.get("이름") or [None])[0], int(단) if 단.isdigit() else None))
                return self._보내기(404, {"오류": "없는 주소입니다."})
            except 요청오류 as e:
                return self._보내기(e.코드, {"오류": e.글})
            except Exception as e:
                기록(f"오류 GET {경로}: {e!r}")
                return self._보내기(500, {"오류": f"서버 오류: {e}"})

        def _올리기(self, 질문):
            """W08: 파일 몸을 그대로 받는다. 교차 출처는 위의 Origin 검사와, 이 형식이 사전 확인을 부르는데 허락하지 않는 것으로 막는다."""
            if (self.headers.get("Content-Type") or "") != "application/octet-stream":
                return self._보내기(415, {"오류": "파일은 application/octet-stream으로 보내 주세요."})
            q = lambda k: (질문.get(k) or [""])[0]
            길이 = 0
            try:
                길이 = int(self.headers.get("Content-Length") or 0)
                return self._보내기(200, 가져오기.올리기(a, q("이름") or None, q("파일"), 길이, self.rfile.read, q("큰파일") == "1"))
            except 요청오류 as e:
                self.close_connection = True   # 읽지 않은 몸이 남아 있을 수 있음
                if e.코드 in (409, 413, 415, 507) and 0 < 길이 <= 64 << 20:   # 작은 몸은 읽어 버려 브라우저가 답을 받게
                    try:
                        self.rfile.read(길이)
                    except OSError:
                        pass
                return self._보내기(e.코드, {"오류": e.글})
            except Exception as e:
                self.close_connection = True
                기록(f"오류 가져오기 올리기: {e!r}")
                return self._보내기(500, {"오류": f"서버 오류: {e}"})

        def do_POST(self):
            if not self._주소확인():
                return
            # 다른 사이트의 페이지가 이 서버로 보내는 것을 막는다:
            # JSON 형식만 받고(교차 출처면 사전 확인이 필요해지고, 우리는 허락하지 않음), Origin이 있으면 같아야 한다.
            출처 = self.headers.get("Origin")
            if 출처 is not None and 출처 not in (f"http://127.0.0.1:{a.포트}", f"http://localhost:{a.포트}"):
                return self._보내기(403, {"오류": "다른 곳에서 온 요청은 받지 않습니다."})
            u = urllib.parse.urlsplit(self.path)
            경로 = urllib.parse.unquote(u.path)
            if 경로 == "/api/가져오기/올리기":
                return self._올리기(urllib.parse.parse_qs(u.query))
            if not (self.headers.get("Content-Type") or "").startswith("application/json"):
                return self._보내기(415, {"오류": "JSON으로 보내 주세요."})
            try:
                길이 = int(self.headers.get("Content-Length") or 0)
                if 길이 < 0:
                    raise 요청오류(400, "Content-Length가 잘못됐습니다.")
                if 길이 > 16 << 20:
                    raise 요청오류(413, "너무 큽니다.")
                몸 = json.loads(self.rfile.read(길이) or b"{}")
                if not isinstance(몸, dict):
                    raise 요청오류(400, "객체로 보내 주세요.")
                if 경로 == "/api/새캐릭터":
                    return self._보내기(200, a.새캐릭터(몸.get("이름")))
                if 경로 == "/api/기억":
                    캐릭터, 단계 = 몸.get("캐릭터"), 몸.get("단계")
                    if 캐릭터 is not None:
                        a.캐릭터폴더(캐릭터)
                    a.기억쓰기(캐릭터, 단계 if isinstance(단계, int) and 0 <= 단계 <= 10 else None)
                    return self._보내기(200, {"됨": True})
                if 경로 == "/api/탭":
                    탭 = str(몸.get("탭") or "")[:64]
                    캐릭터 = 몸.get("캐릭터")
                    if 캐릭터 is not None:
                        a.캐릭터폴더(캐릭터)
                    답 = a.탭알림(탭, 캐릭터, bool(몸.get("놓기")))
                    답["바뀜"] = a.바뀜표(캐릭터)
                    if 캐릭터 is not None and isinstance(몸.get("단계"), int):
                        답["바뀜"]["표시"] = a.표시바뀜(캐릭터, 몸["단계"])
                        답["바뀜"]["결정"] = a.결정바뀜(캐릭터, 몸["단계"])
                        if 몸["단계"] == 1:
                            답["바뀜"]["그림"] = 그림단계.바뀜(a, 캐릭터)  # W09
                        if 몸["단계"] in 생성단계.단계들:
                            답["바뀜"]["생성"] = 생성단계.바뀜(a, 캐릭터, 몸["단계"])  # W10
                        if 몸["단계"] == 메시단계.번호:
                            답["바뀜"]["메시"] = 메시단계.바뀜(a, 캐릭터)  # W11
                        if 몸["단계"] == 텍스처단계.번호:
                            답["바뀜"]["텍스처"] = 텍스처단계.바뀜(a, 캐릭터)  # W12
                        if 몸["단계"] in 리깅단계.단계들:
                            답["바뀜"]["리깅"] = 리깅단계.바뀜(a, 캐릭터, 몸["단계"])  # W13
                        if 몸["단계"] in 동작단계.단계들:
                            답["바뀜"]["동작"] = 동작단계.바뀜(a, 캐릭터, 몸["단계"])  # W14
                        if 몸["단계"] == 동작단계.애니:
                            답["바뀜"]["리깅"] = 리깅단계.바뀜(a, 캐릭터, 몸["단계"])  # W14: 10단계 시간 막대도 리깅단계.js가 그림
                    return self._보내기(200, 답)
                if 경로 == "/api/작성중":
                    return self._보내기(200, a.작성중쓰기(몸.get("이름"), 몸.get("단계"), 몸))
                if 경로 == "/api/부위이름":
                    return self._보내기(200, a.부위이름쓰기(몸.get("이름"), 몸))
                if 경로 == "/api/보내기":
                    return self._보내기(200, a.보내기쓰기(몸.get("이름"), 몸.get("단계"), 몸))
                if 경로 == "/api/결정":
                    return self._보내기(200, a.결정쓰기(몸.get("이름"), 몸.get("단계"), 몸))
                if 경로 == "/api/되돌리기":
                    return self._보내기(200, a.되돌리기쓰기(몸.get("이름"), 몸.get("단계"), 몸))
                if 경로 == "/api/리깅/리그체크":  # W13: 8단계 리그 체크(무료)
                    return self._보내기(200, 리깅단계.리그체크하기(a, 몸.get("이름"), 몸))
                if 경로 == "/api/리깅/후보고르기":  # W13: 9단계 후보 비교에서 고르기
                    return self._보내기(200, 리깅단계.후보고르기(a, 몸.get("이름"), 몸))
                if 경로 in 동작쓰기:  # W14: 10·11단계 단추
                    return self._보내기(200, 동작쓰기[경로](a, 몸.get("이름"), 몸))
                if 경로 == "/api/텍스처/검수안받음":  # W12: 독립 검수 받지 않음 적기
                    return self._보내기(200, 텍스처단계.안받음쓰기(a, 몸.get("이름"), 몸))
                if 경로 == "/api/다시보내기":
                    return self._보내기(200, a.다시보내기쓰기(몸.get("이름"), 몸.get("단계"), 몸))
                if 경로 == "/api/승인":
                    return self._보내기(200, 승인.승인하기(a, 몸.get("이름"), 몸.get("단계"), 몸))
                if 경로 == "/api/다시생성":
                    return self._보내기(200, 승인.다시생성(a, 몸.get("이름"), 몸.get("단계"), 몸))
                if 경로 == "/api/그림/생성":
                    return self._보내기(200, 그림단계.생성(a, 몸.get("이름"), 몸))
                if 경로 == "/api/그림/승인":
                    return self._보내기(200, 그림단계.승인하기(a, 몸.get("이름"), 몸))
                if 경로 == "/api/그림/새캐릭터":
                    return self._보내기(200, 그림단계.새캐릭터(a, 몸))
                if 경로 == "/api/가져오기/넣기":
                    return self._보내기(200, 가져오기.넣기(a, 몸))
                if 경로 == "/api/가져오기/취소":
                    return self._보내기(200, 가져오기.취소(a, 몸.get("번호")))
                if 경로 == "/api/가져오기/방향":
                    return self._보내기(200, 가져오기.방향고르기(a, 몸))
                if 경로 == "/api/끄기":
                    남은, 못봄 = a.진행중인단계()
                    if (남은 or 못봄) and not 몸.get("그래도"):
                        return self._보내기(409, {"경고": "에이전트가 일하는 중인 단계가 있거나, 점검하지 못한 캐릭터가 있습니다.",
                                                  "단계": 남은, "점검못함": 못봄})
                    기록(f"끄기 요청을 받음(진행 중: {남은}, 점검 못 함: {못봄})")
                    self._보내기(200, {"됨": True})
                    threading.Thread(target=a.서버.shutdown, daemon=True).start()
                    return
                return self._보내기(404, {"오류": "없는 주소입니다."})
            except 요청오류 as e:
                return self._보내기(e.코드, {"오류": e.글})
            except json.JSONDecodeError:
                return self._보내기(400, {"오류": "JSON을 읽지 못했습니다."})
            except Exception as e:
                기록(f"오류 POST {경로}: {e!r}")
                return self._보내기(500, {"오류": f"서버 오류: {e}"})

    return 처리기


class 서버(ThreadingHTTPServer):
    # Windows의 SO_REUSEADDR는 이미 쓰는 포트에도 묶이게 하므로 끄고, 포트를 독점한다.
    allow_reuse_address = False
    daemon_threads = True

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


# ---------------------------------------------------------------- 켜기


def 정보묻기(포트: int) -> dict | None:
    """그 포트에 이 프로그램이 켜져 있으면 정보를, 아니면 None."""
    try:
        c = http.client.HTTPConnection(주소, 포트, timeout=1.5)
        c.request("GET", "/api/%EC%A0%95%EB%B3%B4", headers={"Host": f"{주소}:{포트}"})
        r = c.getresponse()
        if r.status != 200:
            return None
        v = json.loads(r.read())
        return v if v.get("프로그램") == 프로그램 else None
    except Exception:
        return None


def 쓰이는중(포트: int) -> bool:
    """묶어 보아 실패하면 쓰이는 중. (Windows에서는 닫힌 포트에 접속해 보는 것이 1초 가까이 걸려 묶어 본다.)"""
    with socket.socket() as s:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            s.bind((주소, 포트))
            return False
        except OSError:
            return True


def 같은폴더서버(폴더: Path) -> int | None:
    """8765~8784 전체에서 같은 폴더를 보는 서버의 포트."""
    for 포트 in range(기본포트, 기본포트 + 포트수):
        if 쓰이는중(포트):
            v = 정보묻기(포트)
            if v and Path(v["폴더"]) == 폴더:
                return 포트
    return None


class 켜기잠금:
    """같은 폴더 서버를 둘이 동시에 켜지 않도록 하는 파일 잠금(오래된 것은 무시)."""

    def __init__(self, 폴더: Path):
        로컬.mkdir(exist_ok=True)
        self.p = 로컬 / f"켜는중_{hashlib.sha256(str(폴더).lower().encode()).hexdigest()[:12]}.lock"
        self.fd = None

    def __enter__(self):
        끝 = time.monotonic() + 15
        while True:
            try:
                self.fd = os.open(self.p, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                return self
            except FileExistsError:
                try:
                    if time.time() - self.p.stat().st_mtime > 30:
                        self.p.unlink()
                        continue
                except OSError:
                    continue
                if time.monotonic() > 끝:
                    raise SystemExit("다른 켜기가 끝나지 않았습니다. 잠시 뒤 다시 켜 주세요.")
                time.sleep(0.2)

    def 놓기(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
            try:
                self.p.unlink()
            except OSError:
                pass

    def __exit__(self, *_):
        self.놓기()


def 켜기(폴더: Path, 열기: bool) -> int:
    with 켜기잠금(폴더) as 잠금:
        있는포트 = 같은폴더서버(폴더)
        if 있는포트 is not None:
            url = f"http://{주소}:{있는포트}/"
            print(f"이미 켜져 있습니다: {url}", flush=True)
            if 열기:
                webbrowser.open(url)
            return 0
        s = a = None
        for 포트 in range(기본포트, 기본포트 + 포트수):
            if 쓰이는중(포트):
                print(f"(포트 {포트}는 쓰이는 중이라 다음 포트를 봅니다)", flush=True)
                continue
            a = 앱(폴더, 포트)
            try:
                s = 서버((주소, 포트), 처리기만들기(a))
                break
            except OSError:
                print(f"(포트 {포트}에 묶지 못해 다음 포트를 봅니다)", flush=True)
        if s is None:
            print(f"빈 포트를 찾지 못했습니다({기본포트}~{기본포트 + 포트수 - 1}).", file=sys.stderr, flush=True)
            return 2
        잠금.놓기()  # 묶었으니 다른 켜기는 이제 이 서버를 찾는다
    a.서버 = s
    url = f"http://{주소}:{a.포트}/"
    기록(f"켜짐 {url} 폴더={폴더} pid={os.getpid()}")
    print(f"가마우지 제작 페이지: {url}  (이 PC에서만 열림, 끄려면 Ctrl+C)", flush=True)
    print(f"TRIPO 실행: {'진짜(승인하면 크레딧을 씀)' if 승인.모드 == '진짜' else '가짜(크레딧을 쓰지 않음, 진짜는 --진짜실행)'}", flush=True)
    if 열기:
        threading.Timer(0.3, webbrowser.open, args=(url,)).start()
    t = threading.Thread(target=s.serve_forever, kwargs={"poll_interval": 0.3}, daemon=True)
    t.start()
    경고시각 = 0.0
    try:
        while t.is_alive():
            try:
                t.join(0.5)
            except KeyboardInterrupt:
                남은, 못봄 = a.진행중인단계()
                if (남은 or 못봄) and time.monotonic() - 경고시각 > 5:
                    경고시각 = time.monotonic()
                    print(f"경고: 에이전트가 일하는 중인 단계 {남은}, 점검하지 못한 캐릭터 {못봄}. "
                          "그래도 끄려면 5초 안에 Ctrl+C를 한 번 더 누르세요.", flush=True)
                    continue
                s.shutdown()
    finally:
        s.server_close()
        기록(f"꺼짐 {url}")
        print("꺼졌습니다.", flush=True)
    return 0


def 끄기(폴더: Path, 그래도: bool) -> int:
    포트 = 같은폴더서버(폴더)
    if 포트 is None:
        print("켜져 있는 서버가 없습니다.", flush=True)
        return 0
    try:
        c = http.client.HTTPConnection(주소, 포트, timeout=5)
        c.request("POST", "/api/%EB%81%84%EA%B8%B0", body=json.dumps({"그래도": 그래도}).encode(),
                  headers={"Host": f"{주소}:{포트}", "Content-Type": "application/json"})
        r = c.getresponse()
        답 = json.loads(r.read() or b"{}")
    except Exception as e:
        print(f"끄지 못했습니다: {e}", flush=True)
        return 1
    if r.status == 409:
        print(f"끄지 않았습니다: {답.get('경고')} 진행 중 {답.get('단계')}, 점검 못 함 {답.get('점검못함')}"
              "  (그래도 끄려면 --그래도)", flush=True)
        return 1
    if r.status != 200 or not 답.get("됨"):
        print(f"끄지 못했습니다: HTTP {r.status} {답}", flush=True)
        return 1
    for _ in range(30):
        if not 쓰이는중(포트):
            print(f"껐습니다: http://{주소}:{포트}/", flush=True)
            return 0
        time.sleep(0.1)
    print(f"끄기 요청은 받았지만 아직 꺼지지 않았습니다: http://{주소}:{포트}/", flush=True)
    return 1


def main(argv=None) -> int:
    for 흐름 in (sys.stdout, sys.stderr):
        try:
            흐름.reconfigure(encoding="utf-8")
        except Exception:
            pass
    p = argparse.ArgumentParser(description="가마우지 제작 페이지 서버(127.0.0.1에만 엶)")
    p.add_argument("--폴더", default=str(여기.parent), help="저장소 루트(기본: 이 프로그램의 위 폴더)")
    p.add_argument("--열지않음", action="store_true", help="켤 때 브라우저를 열지 않음")
    p.add_argument("--끄기", action="store_true", help="켜져 있는 서버를 끔")
    p.add_argument("--그래도", action="store_true", help="--끄기와 함께: 진행 중인 단계가 있어도 끔")
    p.add_argument("--진짜실행", action="store_true", help="승인한 TRIPO 실행을 진짜로 한다(크레딧을 씀). 없으면 가짜 실행(W07)")
    p.add_argument("--가짜결과", choices=["성공", "실패", "잔액부족"], default="성공", help="가짜 실행이 흉내 낼 결과(시험용)")
    인자 = p.parse_args(argv)
    승인.모드 = "진짜" if 인자.진짜실행 else "가짜"
    승인.가짜결과 = 인자.가짜결과
    폴더 = Path(인자.폴더).resolve()
    if not 폴더.is_dir():
        print(f"폴더가 없습니다: {폴더}", file=sys.stderr)
        return 2
    if 인자.끄기:
        return 끄기(폴더, 인자.그래도)
    return 켜기(폴더, not 인자.열지않음)


if __name__ == "__main__":
    sys.exit(main())
