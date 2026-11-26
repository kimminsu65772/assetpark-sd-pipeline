"""부위 목록 만들기 (작업 묶음 W05, 기능명세 1부 5-2b, 2-1 "부위.json")

에이전트가 부른다(사용자가 손으로 고르지 않음). 3단계에서 파츠를 나눈 뒤 처음, 면이 바뀌는 단계(리토폴로지, UV) 뒤에 다시:
    python 10_제작페이지/부위만들기.py --폴더 <저장소 루트> --캐릭터 <이름>

하는 일:
1. `상태.json`의 작업본을 창 없는 Blender로 열어 `블렌더/부위만들기.py`를 돌린다(작업본은 저장하지 않음, 전후 해시 비교).
2. 옛 `부위.json`에서 사용자가 바꾼 이름을 이어받는다(같은 파츠에서 면이 절반 넘게 겹치거나, 면이 바뀌었으면
   중심이 파츠 크기의 10% 안이고 면 수가 0.5~2배인 부위). 부위 하나는 옛 이름 하나만 받는다.
3. `제작페이지/부위.json`으로 쓴다(반쯤 쓴 파일이 남지 않게 임시 파일 → 바꿔 넣기). Blender 출력은 `보기/부위_로그.txt`.

W06의 `에이전트.py 부위 <파일.json>`은 2·3번(`이어받기`, `쓰기`)을 그대로 쓰면 된다.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import 보기만들기

여기 = Path(__file__).resolve().parent
스크립트 = 여기 / "블렌더" / "부위만들기.py"
한국 = timezone(timedelta(hours=9))
겹침기준 = 0.5
중심기준 = 0.10


def 지금() -> str:
    return datetime.now(한국).isoformat(timespec="seconds")


def 이어받기(새: list[dict], 옛: list[dict], 파츠크기: dict[str, float]) -> int:
    """옛 목록에서 사용자가 바꾼 이름을 새 목록에 옮긴다. 옮긴 수를 돌려준다."""
    짝들 = []
    for i, o in enumerate(옛):
        if not o.get("사용자가바꾼이름"):
            continue
        옛면 = set(o.get("면") or [])
        for j, n in enumerate(새):
            if n.get("파츠") != o.get("파츠"):
                continue
            새면 = set(n["면"])
            겹 = len(옛면 & 새면) / max(1, len(옛면 | 새면))
            if 겹 >= 겹침기준:
                짝들.append((1 + 겹, i, j))
                continue
            c1, c2 = o.get("중심"), n.get("중심")
            if not (c1 and c2) or not 옛면:
                continue
            거리 = sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5
            크기 = 파츠크기.get(n["파츠"]) or 1.0
            비 = len(새면) / len(옛면)
            if 거리 <= 중심기준 * 크기 and 0.5 <= 비 <= 2:
                짝들.append((1 - 거리 / (중심기준 * 크기) * 0.5, i, j))   # 0.5~1: 면이 겹치는 짝보다 뒤
    쓴옛, 쓴새, 수 = set(), set(), 0
    for _, i, j in sorted(짝들, reverse=True):
        if i in 쓴옛 or j in 쓴새:
            continue
        쓴옛.add(i); 쓴새.add(j)
        새[j]["이름"] = 옛[i]["이름"]
        새[j]["사용자가바꾼이름"] = True
        수 += 1
    return 수


def 목록다듬기(날것: dict, 작업본해시: str, 옛값: dict | None) -> dict:
    부위 = []
    for r in 날것.get("부위", []):
        부위.append({"이름": r["이름"], "파츠": r["파츠"], "면": r["면"], "사용자가바꾼이름": False,
                   "자동이름": r.get("자동이름", r["이름"]), "중심": r.get("중심"), "근거": r.get("근거", "")})
    파츠크기 = {p["이름"]: p.get("크기") or 1.0 for p in 날것.get("파츠", [])}
    받은 = 이어받기(부위, (옛값 or {}).get("부위") or [], 파츠크기)
    # 화면에서 이름을 바꿀 때 가리키는 번호(파일 안에서만 쓰는 값)
    for i, r in enumerate(부위, 1):
        r["번호"] = i
    return {"꼴버전": 1, "만든시각": 지금(), "작업본해시": 작업본해시, "부위": 부위,
            "파츠": 날것.get("파츠", []), "이어받은이름": 받은, "만든곳": "10_제작페이지/부위만들기.py"}


def 쓰기(p: Path, 값: dict) -> None:
    fd, 임시 = tempfile.mkstemp(prefix=p.name + ".", suffix=".쓰는중", dir=p.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(값, f, ensure_ascii=False, indent=1)
            f.write("\n")
        os.replace(임시, p)
    finally:
        if os.path.exists(임시):
            os.remove(임시)


def 만들기(작업본: Path, 부위파일: Path, 로그경로: Path) -> dict:
    작업본 = Path(작업본).resolve()
    if not 작업본.is_file():
        return {"상태": "실패", "오류": f"작업본이 없습니다: {작업본}"}
    전 = 보기만들기.해시(작업본)
    부위파일.parent.mkdir(parents=True, exist_ok=True)
    로그경로.parent.mkdir(parents=True, exist_ok=True)
    임시 = 부위파일.with_name("부위.만드는중.json")
    try:
        with open(로그경로, "w", encoding="utf-8") as 로그:
            로그.write(f"{지금()} 작업본 {작업본}\nSHA-256 전 {전}\n")
            rc = 보기만들기.블렌더(작업본, 스크립트, [str(임시)], 로그)
            후 = 보기만들기.해시(작업본)
            로그.write(f"SHA-256 후 {후}\n")
        if rc != 0 or not 임시.is_file():
            return {"상태": "실패", "오류": f"부위 만들기 실패(Blender 종료 코드 {rc})", "로그": str(로그경로)}
        if 후 != 전:
            return {"상태": "실패", "오류": "만드는 동안 작업본이 바뀌었습니다. 결과를 버립니다.", "로그": str(로그경로)}
        날것 = json.loads(임시.read_text(encoding="utf-8"))
        옛값 = None
        if 부위파일.is_file():
            try:
                옛값 = json.loads(부위파일.read_text(encoding="utf-8"))
            except ValueError:
                옛값 = None
        값 = 목록다듬기(날것, 전[:12], 옛값)
        쓰기(부위파일, 값)
        return {"상태": "만듦", "파일": str(부위파일), "작업본해시": 전[:12], "부위수": len(값["부위"]),
                "이어받은이름": 값["이어받은이름"], "로그": str(로그경로)}
    finally:
        try:
            임시.unlink()
        except OSError:
            pass


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="작업본 → 부위 목록(부위.json)")
    ap.add_argument("--폴더", required=True)
    ap.add_argument("--캐릭터", required=True)
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    c = Path(a.폴더) / "01_캐릭터" / a.캐릭터
    상태 = json.loads((c / "제작페이지" / "상태.json").read_text(encoding="utf-8"))
    if not 상태.get("작업본"):
        print(json.dumps({"상태": "실패", "오류": "상태.json에 작업본이 적혀 있지 않습니다."}, ensure_ascii=False))
        return 1
    r = 만들기(Path(a.폴더) / 상태["작업본"], c / "제작페이지" / "부위.json", c / "제작페이지" / "보기" / "부위_로그.txt")
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0 if r["상태"] == "만듦" else 1


if __name__ == "__main__":
    sys.exit(main())
