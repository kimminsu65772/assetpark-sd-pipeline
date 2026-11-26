"""파일 가져오기 (작업 묶음 W08, 기능명세 1부 4-3)

흐름:
1. 올리기: 페이지가 파일을 그대로 보낸다(POST /api/가져오기/올리기, application/octet-stream).
   서버는 `로컬/가져오기/<번호>/`에 받아 두고(아직 캐릭터 폴더에 쓰지 않음) 뒤에서 검사를 시작한다.
2. 검사: 그림(PNG·JPG)은 파이썬으로 머리·끝을 읽고, 모델(GLB·FBX·OBJ·blend)은 창 없는 Blender(`블렌더/가져오기검사.py`)로
   열어 크기·방향·파츠 수·UV 층·텍스처 장수·뼈대·뼈 수를 재고 네 방향 그림을 찍는다. 단계를 추정한다.
3. 넣기: 사용자가 단계·출처(·작업 번호)를 고르면 원본을 `01_캐릭터/<이름>/03_TRIPO/가져온것_<시각>/`에 그대로 복사하고,
   앞이 작업본 방향(-y)이 아니면 되돌린 사본을 만들어 그 단계 입력으로 쓴다(GLB·FBX는 `SSOT/도구/TRIPO받은것되돌리기.py`).
   `상태.json`에 입력·출처를 적는다. 그 단계에 입력이 있으면 "새 입력으로 바꾸기"를 골라야 하고, 옛 입력은 `03_TRIPO/이전입력_<시각>/`에 사본으로 남긴다.
4. 방향을 모르면 넣되 표시 "방향 확인 필요"를 달고, 네 방향 그림에서 사용자가 앞을 고르면 그때 되돌린 사본을 만든다.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import struct
import subprocess
import threading
import time
from pathlib import Path

서버 = None
요청오류 = Exception

그림형식 = {".png", ".jpg", ".jpeg"}
모델형식 = {".glb", ".fbx", ".obj", ".blend"}
큰모델 = 200 << 20      # 1부 4-3(사용자 확정): 넘으면 경고 후 계속할지 묻는다
큰그림 = 50 << 20
최대크기 = 4 << 30      # 이것보다 크면 받지 않는다(제안값)
여유 = 200 << 20        # 받기 전에 남아 있어야 할 디스크(받을 크기 말고)
보관초 = 24 * 3600      # 넣지 않은 임시 파일을 지우는 때
제한초 = 600
방향표시 = "방향 확인 필요"
돌림각 = {"-y": 0, "+x": -90, "-x": 90, "+y": 180}   # 앞이 이쪽이면 z축으로 이만큼 돌려 작업본 방향(앞 -y)으로
출처들 = ("TRIPO 웹", "다른 곳", "이 프로젝트의 다른 파일")
번호꼴 = re.compile(r"[0-9a-f]{16}")
면꼴 = re.compile(r"[+-][xy]")

_일: dict[str, dict] = {}
_잠금 = threading.Lock()
_블렌더잠금 = threading.Semaphore(1)   # Blender는 무거워 하나씩


def 묶기(모듈) -> None:
    global 서버, 요청오류
    서버 = 모듈
    요청오류 = 모듈.요청오류


def 임시뿌리() -> Path:
    return 서버.로컬 / "가져오기"


def 블렌더경로() -> str:
    p = os.environ.get("BLENDER") or r"C:\Program Files\Blender Foundation\Blender 5.3\blender.exe"
    if not os.path.isfile(p):
        raise RuntimeError(f"Blender를 찾지 못했습니다: {p} (환경 변수 BLENDER에 경로를 넣어 주세요)")
    return p


def 블렌더돌리기(blend: Path | None, 스크립트: Path, 인자: list[str], 로그: Path) -> int:
    명령 = [블렌더경로(), "--background", "--factory-startup", "--disable-autoexec", "--python-exit-code", "3"]
    if blend is not None:
        명령.append(str(blend))
    명령 += ["--python", str(스크립트), "--", *인자]
    with _블렌더잠금:
        r = subprocess.run(명령, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=제한초,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"),
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    with open(로그, "a", encoding="utf-8") as f:
        f.write(f"\n$ {' '.join(명령)}\n{r.stdout.decode('utf-8', 'replace')}[종료 코드 {r.returncode}]\n")
    return r.returncode


# ---------------------------------------------------------------- 그림·머리 검사(파이썬)

def 머리확인(p: Path, 확장자: str) -> str | None:
    """내용이 확장자와 맞는지. 틀리면 이유."""
    with open(p, "rb") as f:
        머리 = f.read(32)
    if 확장자 == ".png" and not 머리.startswith(b"\x89PNG\r\n\x1a\n"):
        return "확장자는 PNG인데 내용이 PNG가 아닙니다."
    if 확장자 in (".jpg", ".jpeg") and not 머리.startswith(b"\xff\xd8\xff"):
        return "확장자는 JPG인데 내용이 JPG가 아닙니다."
    if 확장자 == ".glb" and not 머리.startswith(b"glTF"):
        return "확장자는 GLB인데 내용이 GLB가 아닙니다."
    if 확장자 == ".blend" and not (머리.startswith(b"BLENDER") or 머리.startswith(b"\x28\xb5\x2f\xfd") or 머리.startswith(b"\x1f\x8b")):
        return "확장자는 blend인데 내용이 blend가 아닙니다."
    if 확장자 == ".fbx" and not (머리.startswith(b"Kaydara FBX Binary") or b"FBX" in 머리 or 머리.lstrip().startswith(b";")):
        return "확장자는 FBX인데 내용이 FBX가 아닙니다."
    if 확장자 == ".obj" and b"\x00" in 머리:
        return "확장자는 OBJ인데 글 파일이 아닙니다."
    return None


def 그림검사(p: Path, 확장자: str) -> dict:
    크기 = p.stat().st_size
    with open(p, "rb") as f:
        몸 = f.read(min(크기, 1 << 20))
        f.seek(max(0, 크기 - 64))
        꼬리 = f.read()
    if 확장자 == ".png":
        if len(몸) < 33 or 몸[12:16] != b"IHDR":
            return {"열림": False, "이유": "PNG 머리(IHDR)가 없습니다."}
        w, h = struct.unpack(">II", 몸[16:24])
        if b"IEND" not in 꼬리:
            return {"열림": False, "이유": "PNG 끝(IEND)이 없습니다. 받다가 잘린 파일로 보입니다."}
        return {"열림": True, "폭": w, "높이": h}
    i = 2
    while i + 9 < len(몸):
        if 몸[i] != 0xFF:
            i += 1
            continue
        표 = 몸[i + 1]
        if 표 in (0xC0, 0xC1, 0xC2, 0xC3):
            h, w = struct.unpack(">HH", 몸[i + 5:i + 9])
            if b"\xff\xd9" not in 꼬리:
                return {"열림": False, "이유": "JPG 끝 표시가 없습니다. 받다가 잘린 파일로 보입니다."}
            return {"열림": True, "폭": w, "높이": h}
        if 표 in (0xD8, 0x01) or 0xD0 <= 표 <= 0xD7:
            i += 2
            continue
        i += 2 + struct.unpack(">H", 몸[i + 2:i + 4])[0]
    return {"열림": False, "이유": "JPG에서 그림 크기를 찾지 못했습니다."}


def 단계추정(확장자: str, 검사: dict) -> tuple[int, str]:
    if 확장자 in 그림형식:
        return 1, "그림은 1단계 입력(기준 그림·시트·자른 네 장)으로 봅니다."
    뼈 = 검사.get("뼈대수", 0) > 0
    텍스처 = 검사.get("텍스처수", 0) > 0
    if 확장자 == ".blend":
        if 뼈:
            return 9, "뼈대가 있는 작업본 → 8단계를 마친 작업본(9단계 입력)으로 봅니다."
        if 텍스처:
            return 6, "텍스처가 있는 작업본 → 5단계를 마친 작업본(6단계 입력)으로 봅니다. Smart UV까지 마쳤으면 7로 고르세요."
        if 검사.get("파츠수", 0) > 1:
            return 4, "파츠로 나뉜 작업본 → 3단계를 마친 작업본(4단계 입력)으로 봅니다."
        return 3, "한 덩어리 작업본 → 3단계(메시 정리) 입력으로 봅니다."
    if 뼈:
        return 8, "뼈대가 있는 모델 → 8단계(오토 리깅)에서 받은 것으로 봅니다."
    if 텍스처:
        return 5, "텍스처가 입혀진 모델 → 5단계(텍스처 생성)에서 받은 것으로 봅니다."
    return 2, "뼈대·텍스처가 없는 모델 → 2단계(모델 생성)에서 받은 것으로 봅니다. 다른 곳의 메시면 3으로 고르세요."


# ---------------------------------------------------------------- 1. 올리기

def 안전한이름(글: str) -> str:
    이름 = os.path.basename(str(글 or "").replace("\\", "/")).strip()
    이름 = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", 이름).strip(" .")
    return 이름[:120] or "파일"


def 오래된것지우기() -> None:
    뿌리 = 임시뿌리()
    if not 뿌리.is_dir():
        return
    t = time.time()
    for d in 뿌리.iterdir():
        try:
            if d.is_dir() and 번호꼴.fullmatch(d.name) and t - d.stat().st_mtime > 보관초 and d.name not in _일:
                shutil.rmtree(d)
        except OSError:
            pass


def 올리기(a, 이름, 파일이름, 길이: int, 읽기, 큰파일: bool) -> dict:
    a.캐릭터폴더(이름)
    a.상태파일(이름)
    원래 = 안전한이름(파일이름)
    확장자 = os.path.splitext(원래)[1].lower()
    if 확장자 not in 그림형식 | 모델형식:
        raise 요청오류(415, f"받는 형식이 아닙니다({확장자 or '확장자 없음'}). PNG·JPG(그림), GLB·FBX·OBJ(모델), blend(작업본)만 받습니다.")
    if not isinstance(길이, int) or 길이 <= 0:
        raise 요청오류(400, "빈 파일입니다.")
    if 길이 > 최대크기:
        raise 요청오류(413, f"너무 큽니다({길이 >> 20} MB). {최대크기 >> 30} GB까지 받습니다.")
    한도 = 큰그림 if 확장자 in 그림형식 else 큰모델
    if 길이 > 한도 and not 큰파일:
        raise 요청오류(409, f"큰 파일입니다({길이 >> 20} MB, 기준 {한도 >> 20} MB). 계속하려면 '그래도 가져오기'를 누르세요.")
    뿌리 = 임시뿌리()
    뿌리.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(뿌리).free < 길이 * 2 + 여유:
        raise 요청오류(507, "디스크 공간이 모자랍니다(받아 두기와 캐릭터 폴더 복사에 파일 크기의 두 배가 필요).")
    오래된것지우기()
    번호 = secrets.token_hex(8)
    d = 뿌리 / 번호
    d.mkdir()
    p = d / ("원본" + 확장자)
    h = hashlib.sha256()
    남은 = 길이
    try:
        with open(p, "wb") as f:
            while 남은 > 0:
                조각 = 읽기(min(남은, 1 << 20))
                if not 조각:
                    raise 요청오류(400, "파일을 끝까지 받지 못했습니다(연결이 끊김).")
                f.write(조각)
                h.update(조각)
                남은 -= len(조각)
    except BaseException:
        shutil.rmtree(d, ignore_errors=True)
        raise
    일 = {"번호": 번호, "캐릭터": 이름, "원래이름": 원래, "확장자": 확장자, "크기": 길이, "해시": h.hexdigest(),
          "받은시각": 서버.지금(), "상태": "검사 중", "검사": None, "추정": None, "추정이유": "", "그림": []}
    with _잠금:
        _일[번호] = 일
    서버.기록(f"가져오기 받음: {원래} ({길이} 바이트) → 검사", a, 이름)
    threading.Thread(target=검사하기, args=(a, 번호), daemon=True).start()
    return 보기(a, 번호)


# ---------------------------------------------------------------- 2. 검사

def 검사하기(a, 번호: str) -> None:
    일 = _일[번호]
    d = 임시뿌리() / 번호
    p = d / ("원본" + 일["확장자"])
    확장자 = 일["확장자"]
    try:
        이유 = 머리확인(p, 확장자)
        if 이유:
            검사 = {"열림": False, "이유": 이유}
        elif 확장자 in 그림형식:
            검사 = 그림검사(p, 확장자)
        else:
            결과 = d / "검사.json"
            rc = 블렌더돌리기(p if 확장자 == ".blend" else None, 서버.여기 / "블렌더" / "가져오기검사.py",
                            [str(p), str(결과), str(d / "그림")], d / "검사로그.txt")
            if 결과.is_file():
                검사 = 서버.json_읽기(결과)
            else:
                검사 = {"열림": False, "이유": f"Blender가 파일을 열지 못함(종료 코드 {rc})."}
    except Exception as e:
        검사 = {"열림": False, "이유": f"검사하지 못함: {e}"}
    일["검사"] = 검사
    if 검사.get("열림"):
        일["추정"], 일["추정이유"] = 단계추정(확장자, 검사)
        일["그림"] = [n for n in 검사.get("그림", []) if (d / "그림" / f"{n}.png").is_file()]
        일["상태"] = "검사됨"
    else:
        일["상태"] = "열리지 않음"
    서버.기록(f"가져오기 검사: {일['원래이름']} → {일['상태']} {검사.get('이유') or ''}".rstrip(), a, 일["캐릭터"])


def 일찾기(번호) -> dict:
    if not isinstance(번호, str) or not 번호꼴.fullmatch(번호) or 번호 not in _일:
        raise 요청오류(404, "가져오던 파일을 찾지 못했습니다(서버를 다시 켰으면 처음부터 다시 가져오세요).")
    return _일[번호]


def 보기(a, 번호) -> dict:
    일 = 일찾기(번호)
    return {k: v for k, v in 일.items() if k != "해시"} | {"해시": 일["해시"][:12]}


def 그림파일(번호, 면) -> Path:
    일 = 일찾기(번호)
    if 면 == "원본" and 일["확장자"] in 그림형식 and 일["상태"] == "검사됨":
        return 임시뿌리() / 번호 / ("원본" + 일["확장자"])
    if not isinstance(면, str) or not 면꼴.fullmatch(면) or 면 not in 일["그림"]:
        raise 요청오류(404, "없는 그림입니다.")
    return 임시뿌리() / 번호 / "그림" / f"{면}.png"


def 넣은그림파일(a, 이름, 폴더, 면) -> Path:
    if not isinstance(폴더, str) or not re.fullmatch(r"가져온것_[0-9T_-]+", 폴더) or not isinstance(면, str) or not 면꼴.fullmatch(면):
        raise 요청오류(404, "없는 그림입니다.")
    c = a.캐릭터폴더(이름)
    p = c / "03_TRIPO" / 폴더 / f"보기_{면}.png"
    if not a._안전한파일(p, c):
        raise 요청오류(404, "없는 그림입니다.")
    return p


def 취소(a, 번호) -> dict:
    일 = 일찾기(번호)
    if 일["상태"] == "검사 중":
        raise 요청오류(409, "검사 중입니다. 끝난 뒤에 취소하세요.")
    with _잠금:
        _일.pop(번호, None)
    shutil.rmtree(임시뿌리() / 번호, ignore_errors=True)
    return {"됨": True}


# ---------------------------------------------------------------- 3. 넣기

def 새폴더(부모: Path, 머리: str) -> Path:
    시각 = 서버.지금(파일용=True)
    d = 부모 / f"{머리}_{시각}"
    n = 2
    while d.exists():
        d = 부모 / f"{머리}_{시각}_{n}"
        n += 1
    d.mkdir(parents=True)
    return d


def 파일sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for 조각 in iter(lambda: f.read(1 << 20), b""):
            h.update(조각)
    return h.hexdigest()


def 상대(a, p: Path) -> str:
    return p.resolve().relative_to(a.폴더).as_posix()


def 되돌린사본(a, 원본: Path, 확장자: str, 앞: str, 폴더: Path) -> tuple[Path, dict]:
    """앞이 -y가 아니면 z축으로 돌린 blend 사본을 만든다. GLB·FBX는 SSOT 도구(크기 1, 높이맞춤 끔), OBJ·blend는 가져오기검사.py."""
    각 = 돌림각[앞]
    출력 = 폴더 / f"되돌림_{원본.stem}.blend"
    로그 = 폴더 / "되돌리기로그.txt"
    if 확장자 in (".glb", ".fbx"):
        도구 = a.폴더 / "SSOT" / "도구" / "TRIPO받은것되돌리기.py"
        if not 도구.is_file():
            도구 = 서버.여기.parent / "SSOT" / "도구" / "TRIPO받은것되돌리기.py"
        rc = 블렌더돌리기(None, 도구, [str(원본), "1", str(출력), "--돌림", str(각), "--높이맞춤", "끔"], 로그)
    else:
        결과 = 폴더 / "되돌리기.json"
        rc = 블렌더돌리기(원본 if 확장자 == ".blend" else None, 서버.여기 / "블렌더" / "가져오기검사.py",
                        [str(원본), str(결과), "-", "--돌리기", str(각), str(출력)], 로그)
    if rc != 0 or not 출력.is_file():
        raise 요청오류(500, f"방향을 되돌린 사본을 만들지 못했습니다(종료 코드 {rc}). 기록: {상대(a, 로그)}")
    return 출력, {"앞": 앞, "돌림_z도": 각, "도구": "TRIPO받은것되돌리기.py" if 확장자 in (".glb", ".fbx") else "가져오기검사.py --돌리기",
                 "크기": "그대로(웹에서 받은 것은 normalize_scale을 모름)", "높이": "맞추지 않음"}


def 입력쓰기(a, 이름, 단계: int, 입력: list[str], 출처: str | None, 상태: str | None, 방향확인: bool | None) -> None:
    바꿀것 = {"입력": 입력}
    if 출처 is not None:
        바꿀것["출처"] = 출처
    if 상태 is not None:
        바꿀것["상태"] = 상태
    a.단계상태쓰기(이름, 단계, 바꿀것)
    if 방향확인 is None:
        return
    p = a.상태파일(이름)
    with 서버.파일잠금(p):
        값 = 서버.json_읽기(p)
        for 칸 in 값.get("단계", []):
            if isinstance(칸, dict) and 칸.get("번호") == 단계:
                표시 = [x for x in 칸.get("표시", []) if x != 방향표시]
                if 방향확인:
                    표시.append(방향표시)
                칸["표시"] = 표시
        서버.json_쓰기(p, 값)


def 넣기(a, 몸: dict) -> dict:
    일 = 일찾기(몸.get("번호"))
    이름 = 일["캐릭터"]
    if 몸.get("이름") != 이름:
        raise 요청오류(409, "다른 캐릭터에서 가져오던 파일입니다.")
    a._주인확인(몸.get("탭"), 이름)
    if 일["상태"] == "검사 중":
        raise 요청오류(409, "아직 검사 중입니다.")
    if 일["상태"] != "검사됨":
        raise 요청오류(409, f"열리지 않는 파일은 넣지 않습니다: {(일['검사'] or {}).get('이유', '')}")
    단계 = 몸.get("단계")
    if not isinstance(단계, int) or not 1 <= 단계 <= 11:
        raise 요청오류(400, "단계를 고르세요(1~11).")
    출처 = 몸.get("출처")
    if 출처 not in 출처들:
        raise 요청오류(400, f"출처를 고르세요: {' / '.join(출처들)}")
    작업번호 = str(몸.get("작업번호") or "").strip()[:80] if 출처 == "TRIPO 웹" else ""
    if 작업번호 and not re.fullmatch(r"[0-9A-Za-z._:-]+", 작업번호):
        raise 요청오류(400, "작업 번호에는 영문·숫자·- _ . : 만 씁니다.")
    확장자 = 일["확장자"]
    모델 = 확장자 in 모델형식
    앞 = 몸.get("앞") or (일["검사"].get("앞") if 모델 else None)
    if 모델 and 앞 not in (*돌림각, "모름"):
        raise 요청오류(400, "앞 방향은 +x / -x / +y / -y / 모름 중 하나입니다.")
    보기 = a.상태보기(이름)
    줄 = 보기["단계"][단계 - 1]
    if 줄["상태"] == "진행 중":
        raise 요청오류(409, f"{단계}단계는 에이전트가 일하는 중입니다. 끝난 뒤에 넣으세요.")
    옛입력 = list(줄["입력"])
    if 옛입력 and not 몸.get("바꾸기"):
        raise 요청오류(409, f"{단계}단계에 이미 입력이 있습니다. 덮어쓰지 않습니다. '새 입력으로 바꾸기'를 고르면 옛 입력은 이전입력 폴더에 사본으로 남습니다.")

    c = a.캐릭터폴더(이름)
    트리포 = c / "03_TRIPO"
    if 트리포.exists() and (not 트리포.is_dir() or not a.안쪽인가(트리포, c)):
        raise 요청오류(409, "03_TRIPO 폴더가 캐릭터 폴더 밖을 가리킵니다. 쓰지 않습니다.")
    임시 = 임시뿌리() / 일["번호"]
    with _잠금:
        if 일.get("넣는중"):
            raise 요청오류(409, "이미 넣는 중입니다.")
        일["넣는중"] = True
    try:
        폴더 = 새폴더(트리포, "가져온것")
        원본 = 폴더 / 일["원래이름"]
        shutil.copy2(임시 / ("원본" + 확장자), 원본)
        if 파일sha(원본) != 일["해시"]:
            raise 요청오류(500, "복사한 원본이 받은 파일과 다릅니다.")
        for n in 일["그림"]:
            shutil.copy2(임시 / "그림" / f"{n}.png", 폴더 / f"보기_{n}.png")
        if (임시 / "검사로그.txt").is_file():
            shutil.copy2(임시 / "검사로그.txt", 폴더 / "검사로그.txt")
        입력 = 원본
        되돌림 = None
        if 모델 and 앞 not in ("모름", "-y"):
            입력, 되돌림 = 되돌린사본(a, 원본, 확장자, 앞, 폴더)
        이전 = None
        if 옛입력:
            이전 = 새폴더(트리포, "이전입력")
            목록 = []
            for x in 옛입력:
                f = a.저장소파일(x)
                줄_ = {"원래경로": x}
                if f:
                    사본 = 이전 / f.name
                    k = 2
                    while 사본.exists():
                        사본 = 이전 / f"{f.stem}_{k}{f.suffix}"
                        k += 1
                    shutil.copy2(f, 사본)
                    줄_["사본"] = 상대(a, 사본)
                else:
                    줄_["사본"] = None
                    줄_["까닭"] = "파일이 없었음"
                목록.append(줄_)
            서버.json_쓰기(이전 / "이전입력.json", {
                "꼴버전": 서버.꼴버전, "만든시각": 서버.지금(), "작업본해시": a._지금작업본해시(이름),
                "단계": 단계, "옛출처": 줄["출처"], "옛상태": 줄["상태"], "입력": 목록, "바꾼가져오기": 상대(a, 폴더),
                "까닭": "옛 입력은 다른 단계나 작업본이 함께 쓸 수 있어 옮기지 않고 사본을 남김"})
        글출처 = {"TRIPO 웹": f"TRIPO 웹{f'(작업 {작업번호})' if 작업번호 else ''}, 웹에서 가져옴, 생성 설정 모름",
                 "다른 곳": "다른 곳, 가져옴",
                 "이 프로젝트의 다른 파일": "이 프로젝트의 다른 파일, 가져옴"}[출처]
        if 일["원래이름"] and 출처 != "TRIPO 웹":
            글출처 += f" ({일['원래이름']})"
        새상태 = "끝" if 단계 == 2 and 출처 == "TRIPO 웹" else "준비됨"   # 2부 14절: TRIPO 웹 모델이면 2단계는 "가져옴"으로 끝
        기록값 = {
            "꼴버전": 서버.꼴버전, "만든시각": 서버.지금(), "작업본해시": a._지금작업본해시(이름),
            "캐릭터": 이름, "원래이름": 일["원래이름"], "크기": 일["크기"], "SHA256": 일["해시"],
            "형식": 확장자.lstrip("."), "단계": 단계, "추정단계": 일["추정"], "추정이유": 일["추정이유"],
            "출처": 출처, "작업번호": 작업번호, "출처글": 글출처,
            "검사": 일["검사"], "앞": 앞 if 모델 else None, "되돌림": 되돌림,
            "원본": 상대(a, 원본), "입력": 상대(a, 입력), "이전입력": 상대(a, 이전) if 이전 else None,
            "상태": 새상태, "받은시각": 일["받은시각"],
        }
        서버.json_쓰기(폴더 / "가져오기.json", 기록값)
        입력쓰기(a, 이름, 단계, [상대(a, 입력)], 글출처, 새상태, 모델 and 앞 == "모름")
    except BaseException:
        일["넣는중"] = False
        raise
    with _잠금:
        _일.pop(일["번호"], None)
    shutil.rmtree(임시, ignore_errors=True)
    서버.기록(f"가져오기 넣음: {일['원래이름']} → {단계}단계 입력 {상대(a, 입력)} (출처 {출처}, 앞 {앞})", a, 이름)
    return {"됨": True, "폴더": 상대(a, 폴더), "입력": 상대(a, 입력), "단계": 단계, "방향확인필요": bool(모델 and 앞 == "모름"),
            "이전입력": 상대(a, 이전) if 이전 else None, "상태보기": a.상태보기(이름)}


# ---------------------------------------------------------------- 4. 넣은 뒤 앞 방향 고르기

def 가져온기록(a, 이름, 단계: int) -> tuple[Path, dict]:
    """그 단계 입력이 든 가져온것 폴더와 기록."""
    줄 = a.상태보기(이름)["단계"][단계 - 1]
    c = a.캐릭터폴더(이름)
    for x in 줄["입력"]:
        f = a.저장소파일(x)
        if f and f.parent.name.startswith("가져온것_") and f.parent.parent.name == "03_TRIPO" and a.안쪽인가(f, c):
            p = f.parent / "가져오기.json"
            if a._안전한파일(p, c):
                return f.parent, 서버.json_읽기(p)
    raise 요청오류(404, f"{단계}단계 입력이 가져온 파일이 아닙니다.")


def 넣은것보기(a, 이름, 단계) -> dict:
    if not isinstance(단계, int) or not 1 <= 단계 <= 11:
        raise 요청오류(400, "모르는 단계 번호입니다.")
    폴더, 값 = 가져온기록(a, 이름, 단계)
    return {"폴더": 폴더.name, "원래이름": 값.get("원래이름"), "앞": 값.get("앞"), "검사": 값.get("검사"),
            "그림": [n for n in ("+x", "-x", "+y", "-y") if (폴더 / f"보기_{n}.png").is_file()]}


def 방향고르기(a, 몸: dict) -> dict:
    이름, 단계, 앞 = 몸.get("이름"), 몸.get("단계"), 몸.get("앞")
    if not isinstance(단계, int) or not 1 <= 단계 <= 11:
        raise 요청오류(400, "모르는 단계 번호입니다.")
    if 앞 not in 돌림각:
        raise 요청오류(400, "앞 방향은 +x / -x / +y / -y 중 하나입니다.")
    a._주인확인(몸.get("탭"), 이름)
    if 방향표시 not in a.상태보기(이름)["단계"][단계 - 1]["표시"]:
        raise 요청오류(409, f"{단계}단계에는 '{방향표시}' 표시가 없습니다.")
    폴더, 값 = 가져온기록(a, 이름, 단계)
    원본 = a.저장소파일(값.get("원본"))
    if not 원본:
        raise 요청오류(409, "가져온 원본 파일이 없습니다.")
    확장자 = 원본.suffix.lower()
    입력, 되돌림 = (원본, None) if 앞 == "-y" else 되돌린사본(a, 원본, 확장자, 앞, 폴더)
    with 서버.파일잠금(폴더 / "가져오기.json"):
        값.update({"앞": 앞, "되돌림": 되돌림, "입력": 상대(a, 입력), "앞고른시각": 서버.지금()})
        서버.json_쓰기(폴더 / "가져오기.json", 값)
    입력쓰기(a, 이름, 단계, [상대(a, 입력)], None, None, False)
    서버.기록(f"가져온 것의 앞 방향을 고름: {단계}단계 앞 {앞} → 입력 {상대(a, 입력)}", a, 이름)
    return {"됨": True, "입력": 상대(a, 입력), "상태보기": a.상태보기(이름)}
