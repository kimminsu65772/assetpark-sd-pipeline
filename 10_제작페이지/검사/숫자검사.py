"""디자인규격_v001.md 7절 1번 — 숫자 검사.

`정적/`의 CSS·HTML·JS(라이브러리 `정적/lib/` 제외)에서 디자인 토큰 밖의 `px` 값과 `#색`을 센다.
- 6절의 예외: `0`, 테두리·바깥선 속성(border*, outline*)의 `1px`. 그 밖의 `1px`(예: padding:1px)은 센다.
- 음수(-10px), 정수부 없는 소수(.5px), 대문자 단위(PX)도 센다. CSS 주석 속 숫자는 세지 않는다.
0개가 아니면 종료 코드 1.

    python 검사/숫자검사.py            # 검사
    python 검사/숫자검사.py --자가시험  # 일부러 틀린 예와 맞는 예로 검사기 자체를 시험
"""
import re
import sys
from pathlib import Path

여기 = Path(__file__).resolve().parent.parent
정적 = 여기 / "정적"
px = re.compile(r"(?<![\w.#-])(-?(?:\d+\.?\d*|\.\d+))px\b", re.IGNORECASE)
색 = re.compile(r"(?<![\w&])#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")
선언 = re.compile(r"([a-zA-Z-]+)\s*:\s*([^;{}]*)")
주석 = re.compile(r"/\*.*?\*/", re.DOTALL)


def 주석지우기(글: str) -> str:
    """줄 번호가 바뀌지 않도록 주석을 같은 수의 줄바꿈으로 바꾼다."""
    return 주석.sub(lambda m: "\n" * m.group(0).count("\n"), 글)


def 검사(글: str, 이름: str) -> list[tuple]:
    걸림 = []
    for 번호, 줄 in enumerate(주석지우기(글).splitlines(), 1):
        속성자리 = [(m.start(2), m.end(2), m.group(1).lower()) for m in 선언.finditer(줄)]
        for m in px.finditer(줄):
            값 = float(m.group(1))
            if 값 == 0:
                continue
            속성 = next((p for a, b, p in 속성자리 if a <= m.start() < b), "")
            if 값 == 1 and 속성.startswith(("border", "outline")):
                continue
            걸림.append((이름, 번호, m.group(0), 속성 or "?", 줄.strip()))
        for m in 색.finditer(줄):
            걸림.append((이름, 번호, m.group(0), "색", 줄.strip()))
    return 걸림


def 자가시험() -> int:
    틀림 = ".a{padding:1px;margin-left:-10px;gap:.5px;font-size:13PX;color:#fff}\n"
    맞음 = "/* 설명: 12px, #fff */\n.b{border:1px solid var(--c-line);outline:1px solid red;margin:0;padding:var(--sp-2)}\n"
    a, b = len(검사(틀림, "틀림")), len(검사(맞음, "맞음"))
    print(f"자가시험: 틀린 예 {a}개 잡음(기대 5), 맞는 예 {b}개(기대 0)")
    return 0 if (a, b) == (5, 0) else 1


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if "--자가시험" in sys.argv:
        return 자가시험()
    걸림 = []
    파일수 = 0
    for p in sorted(정적.rglob("*")):
        if p.suffix not in (".css", ".html", ".js", ".mjs") or "lib" in p.relative_to(정적).parts:
            continue
        파일수 += 1
        걸림 += 검사(p.read_text(encoding="utf-8"), p.relative_to(여기).as_posix())
    for 이름, 번호, 값, 속성, 줄 in 걸림:
        print(f"{이름}:{번호}: {값} ({속성})  | {줄[:120]}")
    print(f"숫자 검사: 파일 {파일수}개, 토큰 밖 값 {len(걸림)}개")
    return 1 if 걸림 else 0


if __name__ == "__main__":
    sys.exit(main())
