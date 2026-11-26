"""작업본(blend) → 3D 보기용 GLB 만들기 (작업 묶음 W01, 기능명세 1부 3-3·5-1절)

서버(`제작페이지.py`)가 부르고, 혼자서도 돌릴 수 있다:
    python 10_제작페이지/보기만들기.py --폴더 <저장소 루트> --캐릭터 <이름>      (상태.json의 `작업본`)
    python 10_제작페이지/보기만들기.py --작업본 <blend> --보기 <출력 폴더>       (경로를 직접)
    덧붙임: --다시(캐시가 있어도 다시 만듦)

하는 일:
1. 작업본의 SHA-256을 잰다. `보기/<앞 12자리>.glb`와 `.json`(검사 통과 기록)이 있으면 다시 만들지 않는다(캐시).
2. 없으면 창 없는 Blender(`SSOT/도구/블렌더실행.sh`)로 `블렌더/GLB만들기.py`를 돌려 임시 파일에 만든다.
3. 같은 방법으로 `검사/GLB검사.py`를 돌려 되읽어 확인한다(파츠마다 임의 면 50개의 면 번호·UV·위치, 면 수).
4. 작업본 해시를 다시 잰다. 실행 전후가 다르면(작업본을 누가 쓰는 중) 결과를 버리고 실패로 둔다.
5. 모두 통과하면 임시 파일을 `<해시>.glb`·`<해시>.json`으로 옮긴다. Blender 출력은 `<해시>_로그.txt`.
작업본은 읽기만 한다(Blender 스크립트에 저장 없음 + 4번의 해시 비교).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

여기 = Path(__file__).resolve().parent
도구폴더 = 여기.parent / "SSOT" / "도구"
실행도구 = 도구폴더 / "블렌더실행.sh"
만들기스크립트 = 여기 / "블렌더" / "GLB만들기.py"
검사스크립트 = 여기 / "검사" / "GLB검사.py"
한국 = timezone(timedelta(hours=9))
제한초 = 600


def 지금() -> str:
    return datetime.now(한국).isoformat(timespec="seconds")


def 해시(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for 조각 in iter(lambda: f.read(1 << 20), b""):
            h.update(조각)
    return h.hexdigest()


def bash찾기() -> str:
    """Git Bash. Windows의 System32\\bash.exe(WSL)는 쓰지 않는다."""
    후보 = [os.environ.get("가마우지_BASH", "")]
    for 뿌리 in (os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("ProgramFiles(x86)", ""),
                 os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")):
        if 뿌리:
            후보.append(os.path.join(뿌리, "Git", "bin", "bash.exe"))
    w = shutil.which("bash")
    if w and "system32" not in w.lower():
        후보.append(w)
    for c in 후보:
        if c and os.path.isfile(c):
            return c
    raise RuntimeError("Git Bash(bash.exe)를 찾지 못했습니다. 환경변수 가마우지_BASH에 경로를 넣어 주세요.")


def 블렌더(작업본: Path, 스크립트: Path, 인자: list[str], 로그) -> int:
    명령 = [bash찾기(), str(실행도구), str(작업본), str(스크립트), "--", *인자]
    환경 = dict(os.environ, PYTHONIOENCODING="utf-8", TAIL="200")
    로그.write(f"\n$ {' '.join(명령)}\n")
    로그.flush()
    r = subprocess.run(명령, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=환경, timeout=제한초,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    로그.write(r.stdout.decode("utf-8", "replace"))
    로그.write(f"[종료 코드 {r.returncode}]\n")
    로그.flush()
    return r.returncode


def 캐시(보기: Path, 짧은: str) -> dict | None:
    g, j = 보기 / f"{짧은}.glb", 보기 / f"{짧은}.json"
    if g.is_file() and j.is_file():
        try:
            정보 = json.loads(j.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if 정보.get("검사") == "통과":
            return 정보
    return None


_잠금들: dict[str, threading.Lock] = {}
_잠금들잠금 = threading.Lock()


def 만들기(작업본: Path, 보기: Path, 다시: bool = False) -> dict:
    """결과: {상태: 캐시|만듦|실패, 작업본해시, glb, 정보, 오류, 로그}. 같은 작업본을 동시에 두 번 만들지 않는다."""
    작업본 = Path(작업본).resolve()
    if not 작업본.is_file():
        return {"상태": "실패", "오류": f"작업본이 없습니다: {작업본}", "작업본해시": ""}
    전 = 해시(작업본)
    짧은 = 전[:12]
    with _잠금들잠금:
        잠금 = _잠금들.setdefault(str(작업본), threading.Lock())
    with 잠금:
        if not 다시:
            c = 캐시(보기, 짧은)
            if c:
                return {"상태": "캐시", "작업본해시": 짧은, "glb": str(보기 / f"{짧은}.glb"), "정보": c}
        보기.mkdir(parents=True, exist_ok=True)
        무시 = 보기 / ".gitignore"  # 기능명세 2절: 보기/의 GLB·로그는 git에 넣지 않는다
        if not 무시.exists():
            무시.write_text("*" + chr(10), encoding="utf-8")
        로그경로 = 보기 / f"{짧은}_로그.txt"
        임시glb = 보기 / f"{짧은}.만드는중.glb"
        임시json = 보기 / f"{짧은}.만드는중.json"
        시작 = time.monotonic()
        결과 = {"상태": "실패", "작업본해시": 짧은, "로그": str(로그경로)}
        try:
            with open(로그경로, "w", encoding="utf-8") as 로그:
                로그.write(f"{지금()} 작업본 {작업본}\nSHA-256 전 {전}\n")
                rc = 블렌더(작업본, 만들기스크립트, [str(임시glb), str(임시json)], 로그)
                if rc != 0 or not 임시glb.is_file() or not 임시json.is_file():
                    결과["오류"] = f"GLB 만들기 실패(Blender 종료 코드 {rc})"
                    return 결과
                rc2 = 블렌더(작업본, 검사스크립트, [str(임시glb)], 로그)
                후 = 해시(작업본)
                로그.write(f"SHA-256 후 {후}\n")
                if 후 != 전:
                    결과["오류"] = "만드는 동안 작업본이 바뀌었습니다(다른 곳에서 쓰는 중). 결과를 버립니다."
                    return 결과
                if rc2 != 0:
                    결과["오류"] = f"되읽기 검사 실패(종료 코드 {rc2}). 로그를 보세요."
                    return 결과
            정보 = json.loads(임시json.read_text(encoding="utf-8"))
            정보.update({"꼴버전": 1, "만든시각": 지금(), "작업본해시": 짧은, "작업본": str(작업본),
                       "검사": "통과", "걸린초": round(time.monotonic() - 시작, 1)})
            os.replace(임시glb, 보기 / f"{짧은}.glb")
            (보기 / f"{짧은}.json").write_text(json.dumps(정보, ensure_ascii=False, indent=2), encoding="utf-8")
            결과.update({"상태": "만듦", "glb": str(보기 / f"{짧은}.glb"), "정보": 정보})
            return 결과
        except subprocess.TimeoutExpired:
            결과["오류"] = f"Blender가 {제한초}초 안에 끝나지 않았습니다."
            return 결과
        except Exception as e:  # 서버를 멈추지 않게 글로 돌려준다
            결과["오류"] = f"{type(e).__name__}: {e}"
            return 결과
        finally:
            for p in (임시glb, 임시json):
                try:
                    p.unlink()
                except OSError:
                    pass


def 마지막glb(보기: Path) -> str | None:
    """검사를 통과한 GLB 가운데 가장 최근 것의 해시(작업본이 바뀌는 중일 때 대신 보여 줄 것)."""
    if not 보기.is_dir():
        return None
    후보 = [p for p in 보기.glob("*.glb") if ".만드는중" not in p.name and 캐시(보기, p.stem)]
    return max(후보, key=lambda p: p.stat().st_mtime).stem if 후보 else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="작업본 → 3D 보기용 GLB")
    ap.add_argument("--폴더")
    ap.add_argument("--캐릭터")
    ap.add_argument("--작업본")
    ap.add_argument("--보기")
    ap.add_argument("--다시", action="store_true")
    a = ap.parse_args(argv)
    if a.작업본 and a.보기:
        작업본, 보기 = Path(a.작업본), Path(a.보기)
    elif a.폴더 and a.캐릭터:
        c = Path(a.폴더) / "01_캐릭터" / a.캐릭터
        상태 = json.loads((c / "제작페이지" / "상태.json").read_text(encoding="utf-8"))
        if not 상태.get("작업본"):
            print("상태.json에 작업본이 적혀 있지 않습니다.")
            return 2
        작업본, 보기 = Path(a.폴더) / 상태["작업본"], c / "제작페이지" / "보기"
    else:
        ap.print_help()
        return 2
    r = 만들기(작업본, 보기, a.다시)
    print(json.dumps({k: v for k, v in r.items() if k != "정보"}, ensure_ascii=False, indent=2))
    return 0 if r["상태"] in ("캐시", "만듦") else 1


if __name__ == "__main__":
    sys.exit(main())
