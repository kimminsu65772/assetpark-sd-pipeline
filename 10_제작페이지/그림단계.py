"""1단계 그림 생성 화면의 서버 쪽 (작업 묶음 W09, 기능명세 2부 13절, 1부 2-1·4-4·5-4b)

- 생성: 요청문을 조립하고(`SSOT/도구/요청문_조립.py`, 한국어·영어) Codex에 **영어본**을 넘겨 그린다.
  기본은 **가짜 실행**(Codex를 부르지 않고 흉내 그림을 만듦, 한도를 쓰지 않음). 진짜 실행은 서버를 `--진짜실행`으로
  켰을 때만(W07과 같은 스위치: 돈·한도를 쓰는 실행을 진짜로). 진짜 실행 경로는 W09에서 시험하지 않았다.
- 4방향 시트를 받으면 서버가 곧바로 네 장으로 자른다(`SSOT/도구/시트_자르기.py`, 재생성·리사이즈 없이).
- 다섯 범주 판정표와 등신은 에이전트가 `에이전트.py 그림판정`으로 채운다(서버는 판정하지 않음).
- 승인: 기준 그림 → 시트를 만들 수 있게 됨. 시트(자른 네 장) → 네 장을 `03_TRIPO/실험_NNN_입력이미지/후보_A/`에 복사하고
  `SSOT/도구/TRIPO입력_검사.py`로 검사, 통과하면 2단계 입력으로 적는다.
- 새 캐릭터 입력: 캐릭터 폴더와 빈 상태.json, `제작페이지/01_그림생성/입력_<시각>.json`(2-1)을 만든다. 캐릭터 노트는 에이전트가 만든다.

파일(캐릭터마다): `제작페이지/01_그림생성/그림.json`(그림 목록과 승인·판정·설정 확인), 생성 폴더 `02_설정화/페이지생성_<시각>_<종류>/`.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import threading
import time
import zlib
from pathlib import Path

서버 = None


class 요청오류(Exception):  # 묶기 전 자리
    pass


def 묶기(모듈) -> None:
    global 서버, 요청오류
    서버 = 모듈
    요청오류 = 모듈.요청오류


처리종류 = ["손·발 모양", "비율·체형", "얼굴", "옷·색·무늬", "다른 방향과 안 맞음", "기타"]   # 1부 5-4b, 1단계
범주 = ["요구사항 준수", "구성의 정확성", "구조의 타당성", "시점 간 일관성", "판독 가능성"]     # 다섯 검사 범주(SSOT 40 1절)
판정값 = ("충족", "보완 필요", "사람 확인", "해당 없음")
등신범위 = (2.25, 2.75)        # SSOT 단계/1_이미지 1-4: 게임 공통 2.5 ±10%. 결과에 맞춰 넓히지 않는다
새캐릭터항목 = [               # SSOT/13_새캐릭터_입력항목.md "항목" 표(이름 → 반드시)
    ("이름", True), ("컨셉", True), ("헤어", True), ("의상", True), ("양말·신발", False), ("체형·인상", False),
    ("표정", False), ("뺄 것", False), ("참고 그림", False), ("기타", False)]
이름꼴 = re.compile(r"[0-9A-Za-z가-힣_]{1,40}")
codex모델 = "gpt-6.2-astra"   # SSOT 12 "명령줄 시험"의 명령
실행제한초 = 20 * 60

# 가짜 실행이 흉내 낼 결과(시험이 바꿔 씀): 성공 / 한도 / 자르기실패
가짜결과 = "성공"
가짜초 = 1.5

_실행중: set[str] = set()     # 캐릭터 이름. 캐릭터마다 한 번에 하나
_잠금 = threading.Lock()


def 모드() -> str:
    return 서버.승인.모드     # "가짜" / "진짜" (서버를 켤 때 정함)


def 폴더(a, 이름, 만들기=False) -> Path:
    return a.단계폴더(이름, 1, 만들기=만들기)


def 목록파일(a, 이름) -> Path:
    return 폴더(a, 이름) / "그림.json"


def 목록읽기(a, 이름) -> dict:
    p = 목록파일(a, 이름)
    if p.is_file() and a._안전한파일(p, a.캐릭터폴더(이름)):
        try:
            v = 서버.json_읽기(p)
            if isinstance(v, dict) and isinstance(v.get("그림"), list):
                return v
        except Exception:
            pass
    return {"꼴버전": 서버.꼴버전, "만든시각": 서버.지금(), "작업본해시": "", "그림": [], "설정확인": None}


def 목록쓰기(a, 이름, 값: dict) -> None:
    값["만든시각"] = 서버.지금()
    폴더(a, 이름, 만들기=True)
    서버.json_쓰기(목록파일(a, 이름), 값)


def 해시(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def 상대(a, p: Path) -> str:
    return p.relative_to(a.폴더).as_posix()


# ---------------------------------------------------------------- 캐릭터 노트

def 노트파일(a, 이름) -> Path:
    return a.노트루트 / f"{이름}.md"


def 노트읽기(a, 이름) -> dict:
    p = 노트파일(a, 이름)
    if not p.is_file():
        return {"있음": False, "경로": f"SSOT/캐릭터/{이름}.md", "설정": [], "해시": "", "기준그림": ""}
    글 = p.read_text(encoding="utf-8")
    설정, 안 = [], False
    for 줄 in 글.splitlines():
        if 줄.startswith("## "):
            안 = 줄.strip() == "## 설정"
            continue
        if 안 and 줄.startswith("|") and not 줄.startswith("| ---"):
            칸 = [x.strip() for x in 줄.strip().strip("|").split("|")]
            if len(칸) >= 3 and 칸[0] != "항목":
                설정.append({"항목": 칸[0], "조건": 칸[1], "상태": 칸[2]})
    m = re.search(r"^기준그림:[ \t]*(.*)$", 글, re.M)
    return {"있음": True, "경로": f"SSOT/캐릭터/{이름}.md", "설정": 설정, "해시": hashlib.sha256(글.encode()).hexdigest()[:12],
            "기준그림": (m.group(1).strip() if m else "")}


def 요청문읽기(a, 이름) -> dict:
    d = a.폴더 / "SSOT" / "조립결과" / 이름
    값 = {}
    for 종류, 파일 in (("기준", "요청문_기준"), ("시트", "요청문_시트")):
        k, e = d / f"{파일}.txt", d / f"{파일}_영어.txt"
        if k.is_file() or e.is_file():
            값[종류] = {"한국어": k.read_text(encoding="utf-8") if k.is_file() else "",
                       "영어": e.read_text(encoding="utf-8") if e.is_file() else "",
                       "경로": 상대(a, e) if e.is_file() else ""}
    return 값


def 다른캐릭터(a, 이름) -> list[dict]:
    """'다른 캐릭터와 나란히'에 쓸 것: 노트의 기준그림이 있는 다른 캐릭터."""
    목록 = []
    for n in a.캐릭터들():
        if n == 이름:
            continue
        노트 = 노트읽기(a, n)
        f = a.저장소파일(노트["기준그림"]) if 노트["기준그림"] else None
        if f and f.suffix.lower() in (".png", ".jpg", ".jpeg"):
            목록.append({"이름": n, "그림": 상대(a, f)})
    return 목록


# ---------------------------------------------------------------- 보기(화면이 그릴 것)

def 보기(a, 이름) -> dict:
    a.캐릭터폴더(이름)
    목록 = 목록읽기(a, 이름)
    노트 = 노트읽기(a, 이름)
    확인 = 목록.get("설정확인") or {}
    노트["확인됨"] = bool(노트["있음"] and 확인.get("노트해시") == 노트["해시"])
    그림 = []
    for g in 목록["그림"]:
        g = dict(g)
        g["없는파일"] = [x for x in g.get("파일", []) + g.get("자른것", []) if a.저장소파일(x) is None]
        그림.append(g)
    입력들 = sorted(p.name for p in 폴더(a, 이름).glob("입력_*.json")) if 폴더(a, 이름).is_dir() else []
    return {"노트": 노트, "요청문": 요청문읽기(a, 이름), "그림": 그림, "모드": 모드(),
            "실행중": 이름 in _실행중, "다른캐릭터": 다른캐릭터(a, 이름), "입력": 입력들,
            "처리종류": 처리종류, "범주": 범주, "등신범위": list(등신범위), "새캐릭터항목": [n for n, _ in 새캐릭터항목],
            "필수항목": [n for n, k in 새캐릭터항목 if k], "모자람": 완료모자람(a, 이름)}


def 바뀜(a, 이름) -> str:
    try:
        d = 폴더(a, 이름)
    except 요청오류:
        return ""
    조각 = [str(이름 in _실행중)]
    if d.is_dir():
        조각 += [f"{p.name}:{p.stat().st_mtime_ns}" for p in sorted(d.iterdir()) if p.is_file() and (p.name == "그림.json" or p.name.startswith("입력_"))]
    n = 노트파일(a, 이름)
    조각.append(f"노트:{n.stat().st_mtime_ns if n.is_file() else 0}")
    return hashlib.sha256("|".join(조각).encode()).hexdigest()[:12]


def 그림파일(a, 경로: str) -> Path:
    """화면이 띄울 그림: 저장소 안 `01_캐릭터/` 아래의 PNG·JPG만."""
    f = a.저장소파일(경로)
    if f is None or f.suffix.lower() not in (".png", ".jpg", ".jpeg") or not a.안쪽인가(f, a.캐릭터루트):
        raise 요청오류(404, "그림이 없습니다.")
    return f


# ---------------------------------------------------------------- 생성

def 찾기(목록: dict, 번호: str) -> dict | None:
    return next((g for g in 목록["그림"] if g.get("번호") == 번호), None)


def 승인된기준(목록: dict) -> dict | None:
    return next((g for g in reversed(목록["그림"]) if g.get("종류") == "기준" and g.get("승인") == "승인"), None)


def 생성막는이유(a, 이름, 종류: str) -> str:
    if 이름 in _실행중:
        return "생성하는 중입니다"
    노트 = 노트읽기(a, 이름)
    if not 노트["있음"]:
        return "캐릭터 노트가 없습니다 — Claude 앱에서 컨셉·헤어·의상을 알려 주세요"
    if 종류 == "시트" and not 승인된기준(목록읽기(a, 이름)):
        return "기준 그림을 먼저 승인하세요"
    return ""


def 생성(a, 이름, 몸: dict) -> dict:
    a._주인확인(몸.get("탭"), 이름)
    종류 = 몸.get("종류")
    if 종류 not in ("기준", "시트"):
        raise 요청오류(400, f"모르는 종류: {종류!r}")
    목록 = 목록읽기(a, 이름)
    노트 = 노트읽기(a, 이름)
    if 노트["있음"] and not (목록.get("설정확인") or {}).get("노트해시") == 노트["해시"]:
        if not 몸.get("설정확인"):
            raise 요청오류(409, "설정 표를 아직 확인하지 않았습니다.")
        목록["설정확인"] = {"노트해시": 노트["해시"], "시각": 서버.지금()}
        목록쓰기(a, 이름, 목록)
    with _잠금:
        이유 = 생성막는이유(a, 이름, 종류)
        if 이유:
            raise 요청오류(409, 이유)
        _실행중.add(이름)
    try:
        a.단계상태쓰기(이름, 1, {"상태": "진행 중"})
    except Exception:
        _실행중.discard(이름)
        raise
    서버.기록(f"그림 생성 시작: {종류} ({모드()} 실행)", a, 이름)
    threading.Thread(target=_생성하기, args=(a, 이름, 종류, 몸.get("다시") is True), daemon=True).start()
    return {"됨": True, "모드": 모드()}


def _새폴더(a, 이름, 종류) -> Path:
    d = a.캐릭터폴더(이름) / "02_설정화"
    시각 = 서버.지금(파일용=True)
    q, k = d / f"페이지생성_{시각}_{종류}", 2
    while q.exists():
        q, k = d / f"페이지생성_{시각}_{종류}_{k}", k + 1
    q.mkdir(parents=True)
    return q


def _조립(a, 이름) -> tuple[bool, str]:
    r = subprocess.run([sys.executable, str(a.폴더 / "SSOT" / "도구" / "요청문_조립.py"), 이름], cwd=a.폴더,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def _생성하기(a, 이름, 종류: str, 다시: bool) -> None:
    목록 = 목록읽기(a, 이름)
    번호 = f"{종류}{sum(1 for g in 목록['그림'] if g.get('종류') == 종류) + 1:03d}"
    항목 = {"번호": 번호, "종류": 종류, "만든시각": 서버.지금(), "실행": 모드(), "다시생성": 다시, "파일": [], "자른것": [],
            "요청문": "", "요청문해시": "", "판정": None, "등신": None, "등신근거": "", "승인": "대기", "승인시각": "",
            "조건미달승인": [], "탈락": False, "실패이유": "", "폴더": "", "참고그림": []}
    로그: list[str] = []
    try:
        d = _새폴더(a, 이름, 종류)
        항목["폴더"] = 상대(a, d)
        됨, 출력 = _조립(a, 이름)
        로그.append(출력)
        if not 됨:
            raise RuntimeError(f"요청문 조립 실패: {출력.splitlines()[-1] if 출력 else ''}")
        조립 = a.폴더 / "SSOT" / "조립결과" / 이름
        영어 = 조립 / f"요청문_{종류}_영어.txt"
        if not 영어.is_file():
            raise RuntimeError(f"영어 요청문이 없습니다: {상대(a, 영어)}")
        shutil.copy2(영어, d / 영어.name)
        한국어 = 조립 / f"요청문_{종류}.txt"
        if 한국어.is_file():
            shutil.copy2(한국어, d / 한국어.name)
        항목["요청문"], 항목["요청문해시"] = 상대(a, d / 영어.name), 해시(영어)
        참고 = _참고그림(a, 이름, 종류, 목록)
        항목["참고그림"] = 참고
        결과 = d / ("시트.png" if 종류 == "시트" else "기준그림.png")
        if 모드() == "진짜":
            _진짜(a, d, 영어, 참고, 결과, 로그)
        else:
            _가짜(종류, 결과, 로그)
        항목["파일"] = [상대(a, 결과)]
        항목["해시"] = 해시(결과)
        if 종류 == "시트":
            자른곳 = d / "자른것"
            r = subprocess.run([sys.executable, str(a.폴더 / "SSOT" / "도구" / "시트_자르기.py"), str(결과), str(자른곳)],
                               cwd=a.폴더, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
                               env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            로그.append(r.stdout + r.stderr)
            if r.returncode != 0:
                항목["자르기오류"] = _자르기이유(r, "다시 생성을 권합니다.")
            else:
                항목["자른것"] = [상대(a, p) for p in sorted(자른곳.glob("0*.png"))]
        글 = f"{'4방향 시트' if 종류 == '시트' else '기준 그림'} {번호} 생성 끝({'가짜 실행' if 모드() == '가짜' else 'Codex'})."
        if 항목.get("자르기오류"):
            글 += " " + 항목["자르기오류"]
        글 += " 에이전트가 다섯 범주 자가 검수와 등신을 채우면 승인할 수 있습니다."
        a.알림쓰기(이름, 1, 글, "결정 필요")
        a.단계상태쓰기(이름, 1, {"상태": "결정 대기"})
    except 한도 as e:
        항목["실패이유"] = str(e)
        a.알림쓰기(이름, 1, f"Codex 사용량 한도로 멈춤. {e} 멈춘 곳: {종류} 생성 전(요청문 조립까지 됨).", "막힘")
        a.단계상태쓰기(이름, 1, {"상태": "막힘"})
    except Exception as e:
        항목["실패이유"] = str(e)[:500]
        a.알림쓰기(이름, 1, f"{종류} 생성 실패: {str(e)[:300]}", "막힘")
        try:
            a.단계상태쓰기(이름, 1, {"상태": "막힘"})
        except Exception:
            pass
    finally:
        try:
            if 항목["폴더"]:
                (a.폴더 / 항목["폴더"] / "생성기록.json").write_text(json.dumps(dict(항목, 로그=로그), ensure_ascii=False, indent=1), encoding="utf-8")
            목록 = 목록읽기(a, 이름)
            목록["그림"].append(항목)
            목록쓰기(a, 이름, 목록)
            서버.기록(f"그림 생성 끝: {번호} {항목['실패이유'] or '됨'}", a, 이름)
        finally:
            _실행중.discard(이름)


def _참고그림(a, 이름, 종류, 목록) -> list[str]:
    """첨부할 참고 그림(SSOT/조립결과/<이름>/첨부그림.json). 시트의 '이 캐릭터의 기준 그림'은 페이지에서 승인한 기준 그림으로 바꾼다."""
    p = a.폴더 / "SSOT" / "조립결과" / 이름 / "첨부그림.json"
    try:
        목 = json.loads(p.read_text(encoding="utf-8")).get(종류) or []
    except Exception:
        목 = []
    기준 = 승인된기준(목록)
    결과 = []
    for x in 목:
        경로 = x.get("경로", "")
        if 종류 == "시트" and "기준 그림" in x.get("역할", "") and 기준:
            경로 = 기준["파일"][0]
        if a.저장소파일(경로):
            결과.append(경로)
    return 결과


def _자르기이유(r, 덧붙임: str) -> str:
    """시트_자르기.py가 실패한 까닭. 네 덩어리를 못 찾은 것과 도구가 다른 이유로 멈춘 것(메모리 부족 등)을 가른다."""
    출력 = (r.stdout + r.stderr).strip()
    if "캐릭터 구간이" in 출력:
        return f"네 덩어리를 찾지 못해 자르지 않았습니다. {덧붙임}".strip()
    끝줄 = 출력.splitlines()[-1][:200] if 출력 else f"종료 코드 {r.returncode}"
    return f"자르기 도구가 멈춰 자르지 못했습니다({끝줄}). 그림 문제가 아닐 수 있습니다 — 잠시 뒤 Claude 앱에서 다시 잘라 달라고 하세요."


class 한도(Exception):
    pass


def _가짜(종류, 결과: Path, 로그) -> None:
    """Codex를 부르지 않고 흉내 그림을 만든다(밝은 바탕에 어두운 사람 모양. 시트는 네 개를 띄어 놓아 자르기가 실제로 돈다)."""
    time.sleep(가짜초)
    if 가짜결과 == "한도":
        raise 한도("(가짜) 사용량 한도에 걸림. 풀리는 시각: 알 수 없음(가짜 실행)")
    if 종류 == "시트":
        w, h = 1600, 500
        모양 = [(140 + i * 400, 60) for i in range(4)] if 가짜결과 != "자르기실패" else [(140, 60), (420, 60), (1100, 60)]
    else:
        w, h = 600, 750
        모양 = [(180, 80)]
    화소 = bytearray(b"\xee\xe8\xe0" * (w * h))
    for x0, y0 in 모양:
        s = 1.0 if 종류 == "시트" else 1.6
        머리 = (x0 + int(60 * s), y0 + int(60 * s), int(55 * s))
        for y in range(h):
            for x in range(x0, min(w, x0 + int(150 * s))):
                안 = (x - 머리[0]) ** 2 + (y - 머리[1]) ** 2 <= 머리[2] ** 2
                몸 = y0 + int(110 * s) <= y <= y0 + int(330 * s) and x0 + int(15 * s) <= x <= x0 + int(105 * s)
                if 안 or 몸:
                    화소[(y * w + x) * 3:(y * w + x) * 3 + 3] = b"\x40\x38\x48"
    _png쓰기(결과, w, h, bytes(화소))
    로그.append(f"가짜 실행: {결과.name} {w}×{h}")


def _png쓰기(p: Path, w: int, h: int, rgb: bytes) -> None:
    줄 = b"".join(b"\x00" + rgb[y * w * 3:(y + 1) * w * 3] for y in range(h))

    def 덩이(k, v):
        return struct.pack(">I", len(v)) + k + v + struct.pack(">I", zlib.crc32(k + v) & 0xffffffff)
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + 덩이(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                  + 덩이(b"IDAT", zlib.compress(줄, 6)) + 덩이(b"IEND", b""))


def _진짜(a, d: Path, 영어: Path, 참고: list[str], 결과: Path, 로그) -> None:
    """Codex 명령줄로 그린다(SSOT 12 "명령줄 시험"의 명령). W09에서 시험하지 않음."""
    codex = shutil.which("codex")
    if not codex:
        raise RuntimeError("codex 명령을 찾지 못했습니다(PATH).")
    for x in 참고:
        shutil.copy2(a.폴더 / x, d / Path(x).name)
    지시 = ("Call the built-in image generation tool exactly once.\n"
            "Pass the attached image(s) as referenced_image_paths.\n"
            "Use the prompt below as the prompt, unchanged. Do not retry or edit.\n"
            f"Copy the resulting PNG byte-for-byte into the current folder as {결과.name}.\n"
            "Report the tool arguments, time, source path, size and SHA-256. Do not touch files outside this folder.\n\n")
    (d / "Codex_지시문.txt").write_text(지시 + 영어.read_text(encoding="utf-8"), encoding="utf-8")
    인자 = [codex, "exec", "-m", codex모델, "--sandbox", "workspace-write"]
    for x in 참고:
        인자 += ["-i", Path(x).name]
    인자 += ["-o", "보고_Codex.md", "-"]
    with open(d / "Codex_지시문.txt", "rb") as 입력:
        r = subprocess.run(인자, cwd=d, stdin=입력, capture_output=True, timeout=실행제한초)
    출력 = (r.stdout + r.stderr).decode("utf-8", "replace")
    (d / "Codex_로그.txt").write_text(출력, encoding="utf-8")
    로그.append(출력[-2000:])
    if re.search(r"usage limit|rate limit|try again (at|in)", 출력, re.I):
        m = re.search(r"try again (?:at|in) ([^\n.]+)", 출력, re.I)
        raise 한도(f"풀리는 시각: {m.group(1).strip() if m else '알 수 없음'}")
    if r.returncode != 0 or not 결과.is_file():
        raise RuntimeError(f"Codex가 그림을 남기지 않음(종료 코드 {r.returncode}). 로그: {상대(a, d / 'Codex_로그.txt')}")


# ---------------------------------------------------------------- 승인

def 승인막는이유(a, 이름, g: dict | None) -> str:
    if g is None:
        return "볼 그림이 없습니다"
    if 이름 in _실행중:
        return "생성하는 중입니다"
    if g.get("실패이유"):
        return "생성에 실패한 판입니다"
    if g.get("탈락"):
        return "탈락한 그림입니다"
    if g.get("승인") == "승인":
        return "이미 승인했습니다"
    if not g.get("판정"):
        return "에이전트 자가 검수(다섯 범주 판정표)가 아직 없습니다"
    if g.get("종류") == "시트" and len(g.get("자른것") or []) != 4:
        return "네 장으로 자르지 못했습니다 — 다시 생성하세요"
    if any(a.저장소파일(x) is None for x in g.get("파일", []) + g.get("자른것", [])):
        return "그림 파일이 없습니다"
    return ""


def 경고(g: dict) -> list[str]:
    """승인 전에 물을 것: 등신 범위 밖, '보완 필요' 판정."""
    w = []
    등신 = g.get("등신")
    if g.get("종류") == "기준" and (not isinstance(등신, (int, float)) or not 등신범위[0] <= 등신 <= 등신범위[1]):
        w.append(f"등신이 범위 밖입니다({등신 if 등신 is not None else '재지 않음'}, 범위 {등신범위[0]}~{등신범위[1]}). 결과에 맞춰 범위를 넓히지 않습니다.")
    for k, v in (g.get("판정") or {}).items():
        if isinstance(v, dict) and v.get("판정") == "보완 필요":
            w.append(f"{k}: 보완 필요 — {v.get('근거', '')}")
    return w


def 승인하기(a, 이름, 몸: dict) -> dict:
    a._주인확인(몸.get("탭"), 이름)
    목록 = 목록읽기(a, 이름)
    g = 찾기(목록, 몸.get("번호"))
    이유 = 승인막는이유(a, 이름, g)
    if 이유:
        raise 요청오류(409, 이유)
    w = 경고(g)
    if w and not 몸.get("그래도"):
        return {"됨": False, "경고": w}
    더 = {}
    if g["종류"] == "시트":
        더 = _TRIPO입력두기(a, 이름, g)
        if not 더["검사통과"]:
            raise 요청오류(409, f"TRIPO 입력 검사를 통과하지 못해 승인하지 않았습니다: {더['검사'][-300:]}")
    g.update({"승인": "승인", "승인시각": 서버.지금(), "조건미달승인": w}, **더)
    for x in 목록["그림"]:   # 같은 종류의 앞 승인은 대체됨
        if x is not g and x.get("종류") == g["종류"] and x.get("승인") == "승인":
            x["승인"] = "대체됨"
    목록쓰기(a, 이름, 목록)
    서버.기록(f"그림 승인: {g['번호']}{' (조건 미달: ' + '; '.join(w) + ')' if w else ''}", a, 이름)
    if g["종류"] == "시트":
        a.단계상태쓰기(이름, 2, {"입력": 더["입력"], "출처": "이 페이지(1단계 시트 승인)"})
        a.알림쓰기(이름, 1, f"시트 {g['번호']} 승인. 네 장을 {더['TRIPO폴더']}에 두었고 TRIPO 입력 검사 통과. '이 단계 끝'을 누를 수 있습니다.", "안내")
    else:
        a.알림쓰기(이름, 1, f"기준 그림 {g['번호']} 승인. 이제 4방향 시트를 생성할 수 있습니다.", "안내")
    return {"됨": True, "번호": g["번호"], "조건미달": w, **더}


def _TRIPO입력두기(a, 이름, g: dict) -> dict:
    t = a.캐릭터폴더(이름) / "03_TRIPO"
    t.mkdir(exist_ok=True)
    n = 1 + max([int(m.group(1)) for p in t.iterdir() if (m := re.fullmatch(r"실험_(\d{3})_입력이미지", p.name))] or [0])
    d = t / f"실험_{n:03d}_입력이미지" / "후보_A"
    d.mkdir(parents=True)
    for x in g["자른것"]:
        shutil.copy2(a.폴더 / x, d / Path(x).name)
    r = subprocess.run([sys.executable, str(a.폴더 / "SSOT" / "도구" / "TRIPO입력_검사.py"), str(d)], cwd=a.폴더,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    출력 = (r.stdout + r.stderr).strip()
    통과 = r.returncode == 0 and bool(출력) and 출력.splitlines()[-1].startswith("검사 통과")
    if not 통과:
        shutil.rmtree(d.parent)
    return {"TRIPO폴더": 상대(a, d), "검사": 출력, "검사통과": 통과,
            "입력": [상대(a, d / Path(x).name) for x in g["자른것"]] if 통과 else []}


def 완료모자람(a, 이름) -> list[str]:
    """1단계 끝나는 조건(2부 13절: 1_이미지 1-4·1-6·1-7, 탈락한 그림이 TRIPO 입력 자리에 없음)."""
    목록 = 목록읽기(a, 이름)
    모자람 = []
    기준 = 승인된기준(목록)
    if not 기준:
        모자람.append("승인한 기준 그림이 없음(1-4)")
    elif 기준.get("조건미달승인"):
        모자람.append(f"기준 그림을 조건 미달로 승인함: {'; '.join(기준['조건미달승인'])}")
    시트 = next((g for g in reversed(목록["그림"]) if g.get("종류") == "시트" and g.get("승인") == "승인"), None)
    if not 시트:
        모자람.append("승인한 4방향 시트(자른 네 장)가 없음(1-6)")
        return 모자람
    if 시트.get("조건미달승인"):
        모자람.append(f"시트를 조건 미달로 승인함: {'; '.join(시트['조건미달승인'])}")
    d = a.저장소파일(시트.get("TRIPO폴더", "") + "/01_front.png")
    if d is None:
        모자람.append(f"TRIPO 입력 폴더에 네 장이 없음(1-7): {시트.get('TRIPO폴더')}")
        return 모자람
    승인해시 = {해시(a.폴더 / x) for x in 시트["자른것"] if a.저장소파일(x)}
    있는것 = [p for p in d.parent.iterdir() if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")]
    낯선 = [p.name for p in 있는것 if 해시(p) not in 승인해시]
    if 낯선 or len(있는것) != 4:
        모자람.append(f"TRIPO 입력 폴더에 승인하지 않은 그림이 있거나 네 장이 아님: {낯선 or len(있는것)}")
    return 모자람


# ---------------------------------------------------------------- 에이전트가 쓰는 것

def 판정쓰기(a, 이름, v: dict) -> dict:
    """`에이전트.py 그림판정`: {번호, 판정: {범주: {판정, 근거}}, 등신, 등신근거, 탈락}."""
    모르는것 = set(v) - {"번호", "판정", "등신", "등신근거", "탈락"}
    if 모르는것:
        raise 요청오류(400, f"모르는 항목: {sorted(모르는것)}")
    목록 = 목록읽기(a, 이름)
    g = 찾기(목록, v.get("번호"))
    if g is None:
        raise 요청오류(400, f"그림 번호가 없습니다: {v.get('번호')!r} (있는 것: {[x.get('번호') for x in 목록['그림']]})")
    판정 = v.get("판정")
    if not isinstance(판정, dict) or set(판정) != set(범주):
        raise 요청오류(400, f"판정은 다섯 범주 모두여야 합니다: {범주}")
    for k, x in 판정.items():
        if not isinstance(x, dict) or x.get("판정") not in 판정값 or not isinstance(x.get("근거", ""), str):
            raise 요청오류(400, f"{k}: {{판정: {'/'.join(판정값)}, 근거: 글}} 꼴이어야 합니다.")
        if x["판정"] != "충족" and not x.get("근거", "").strip():
            raise 요청오류(400, f"{k}: '충족'이 아니면 근거가 있어야 합니다.")
    등신 = v.get("등신")
    if g["종류"] == "기준" and (not isinstance(등신, (int, float)) or isinstance(등신, bool) or not v.get("등신근거")):
        raise 요청오류(400, "기준 그림은 등신(숫자)과 등신근거(재는 법)가 있어야 합니다.")
    if g.get("승인") == "승인":
        raise 요청오류(409, "이미 승인한 그림의 판정은 바꾸지 않습니다.")
    g.update({"판정": 판정, "등신": 등신 if isinstance(등신, (int, float)) else None, "등신근거": v.get("등신근거", ""),
              "탈락": bool(v.get("탈락")), "판정시각": 서버.지금()})
    목록쓰기(a, 이름, 목록)
    a.단계상태쓰기(이름, 1, {"상태": "결정 대기"})
    서버.기록(f"그림 판정: {g['번호']} 등신 {g['등신']} 탈락 {g['탈락']}", a, 이름)
    return {"결과": "씀", "번호": g["번호"], "경고": 경고(g)}


def 등록하기(a, 이름, v: dict) -> dict:
    """`에이전트.py 그림등록`: 가져온 그림이나 Codex 앱에서 만든 그림을 1단계 목록에 넣는다.
    {종류: 기준|시트, 파일: 경로, 출처: 글}. 시트면 서버가 자른다."""
    종류, 파일 = v.get("종류"), v.get("파일")
    if 종류 not in ("기준", "시트") or not isinstance(파일, str):
        raise 요청오류(400, "{종류: 기준|시트, 파일: 경로, 출처: 글} 꼴로 주세요.")
    f = a.저장소파일(파일)
    if f is None or f.suffix.lower() not in (".png", ".jpg", ".jpeg"):
        raise 요청오류(400, f"저장소 안의 PNG·JPG가 아닙니다: {파일}")
    목록 = 목록읽기(a, 이름)
    번호 = f"{종류}{sum(1 for g in 목록['그림'] if g.get('종류') == 종류) + 1:03d}"
    d = _새폴더(a, 이름, 종류)
    q = d / ("시트" + f.suffix.lower() if 종류 == "시트" else "기준그림" + f.suffix.lower())
    shutil.copy2(f, q)
    항목 = {"번호": 번호, "종류": 종류, "만든시각": 서버.지금(), "실행": "등록", "출처": str(v.get("출처") or "다른 곳"),
            "원본": 파일, "파일": [상대(a, q)], "해시": 해시(q), "자른것": [], "요청문": "", "요청문해시": "", "판정": None,
            "등신": None, "등신근거": "", "승인": "대기", "승인시각": "", "조건미달승인": [], "탈락": False, "실패이유": "",
            "폴더": 상대(a, d), "참고그림": []}
    if 종류 == "시트":
        r = subprocess.run([sys.executable, str(a.폴더 / "SSOT" / "도구" / "시트_자르기.py"), str(q), str(d / "자른것")],
                           cwd=a.폴더, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        if r.returncode == 0:
            항목["자른것"] = [상대(a, p) for p in sorted((d / "자른것").glob("0*.png"))]
        else:
            항목["자르기오류"] = _자르기이유(r, "")
    목록["그림"].append(항목)
    목록쓰기(a, 이름, 목록)
    서버.기록(f"그림 등록: {번호} ← {파일}", a, 이름)
    return {"결과": "씀", "번호": 번호, "자르기오류": 항목.get("자르기오류", "")}


# ---------------------------------------------------------------- 새 캐릭터 입력

def 새캐릭터(a, 몸: dict) -> dict:
    항목들 = 몸.get("항목들")
    if not isinstance(항목들, dict) or not all(isinstance(항목들.get(n, ""), str) for n, _ in 새캐릭터항목):
        raise 요청오류(400, "항목들은 {항목 이름: 글} 꼴이어야 합니다.")
    빈 = [n for n, 꼭 in 새캐릭터항목 if 꼭 and not 항목들.get(n, "").strip()]
    if 빈:
        raise 요청오류(400, f"반드시 적을 칸이 비었습니다: {', '.join(빈)}")
    if sum(len(x) for x in 항목들.values()) > 20000:
        raise 요청오류(400, "너무 깁니다.")
    이름 = 항목들["이름"].strip().replace(" ", "_")
    if not 이름꼴.fullmatch(이름) or 이름.startswith("_"):
        raise 요청오류(400, "이름은 한글·영문·숫자·밑줄(_)로 40자까지입니다(폴더 이름으로 씀).")
    c = a.캐릭터루트 / 이름
    if c.exists():
        raise 요청오류(409, f"같은 이름의 캐릭터 폴더가 이미 있습니다: 01_캐릭터/{이름}/")
    c.mkdir(parents=True)
    a.새캐릭터(이름)
    참고 = [x.strip() for x in 항목들.get("참고 그림", "").splitlines() if x.strip()]
    d = 폴더(a, 이름, 만들기=True)
    시각 = 서버.지금(파일용=True)
    p = d / f"입력_{시각}.json"
    서버.json_쓰기(p, {"꼴버전": 서버.꼴버전, "만든시각": 서버.지금(), "작업본해시": "",
                      "항목들": {n: 항목들.get(n, "").strip() for n, _ in 새캐릭터항목}, "참고그림": 참고})
    a.알림쓰기(이름, 1, "새 캐릭터 입력을 받았습니다. Claude 앱에서 '보냈어'라고 알려 주세요 — 에이전트가 캐릭터 노트를 만들고 설정 표를 띄웁니다.", "결정 필요")
    서버.기록(f"새 캐릭터 입력: {상대(a, p)}", a, 이름)
    return {"됨": True, "이름": 이름, "파일": 상대(a, p)}
