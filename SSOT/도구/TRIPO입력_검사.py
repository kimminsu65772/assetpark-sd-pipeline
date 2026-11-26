# -*- coding: utf-8 -*-
"""TRIPO 멀티뷰 입력 폴더의 파일 이름을 검사한다(lint). 아무것도 고치지 않는다.

쓰는 법(저장소 루트에서):
    PYTHONIOENCODING=utf-8 python SSOT/도구/TRIPO입력_검사.py <입력 폴더>

TRIPO CLI 0.11.2의 `generate multiview-to-model`은 파일 이름에 든 방향 낱말로 방향을 정한다
(배포본 dist/pipeline/make.js의 assignViews). 아래 낱말 규칙은 그 코드를 그대로 옮긴 것이다.
CLI가 바뀌면 이 파일도 함께 확인한다.

통과 조건(하나라도 어기면 종료 코드 1):
- 그림 파일(.png .jpg .jpeg .webp)이 2~4장이다.
- 각 파일 이름에 방향 낱말이 정확히 하나만 들어 있다(둘 이상이면 CLI가 front→back→left→right 순서로
  먼저 맞는 쪽을 고르므로 뜻과 다르게 들어갈 수 있다. 하나도 없으면 자리 순서로 채워진다).
- 같은 방향이 두 파일에 겹치지 않는다.
- front가 있다.
- 파일 이름 앞의 번호가 있으면 01 front, 02 left, 03 back, 04 right와 맞는다(SSOT 파일 이름 규칙).
"""
import re
import sys
from pathlib import Path

방향_낱말 = {  # CLI 0.11.2 assignViews와 같은 정규식, 같은 순서
    "front": re.compile(r"front|正面|前", re.I),
    "back": re.compile(r"back|背面|后", re.I),
    "left": re.compile(r"left|左", re.I),
    "right": re.compile(r"right|右", re.I),
}
번호_방향 = {"01": "front", "02": "left", "03": "back", "04": "right"}
그림_확장자 = {".png", ".jpg", ".jpeg", ".webp"}


def main():
    if len(sys.argv) != 2:
        raise SystemExit("쓰는 법: python SSOT/도구/TRIPO입력_검사.py <입력 폴더>")
    폴더 = Path(sys.argv[1])
    if not 폴더.is_dir():
        raise SystemExit(f"오류: 폴더가 없다 {폴더}")
    파일들 = sorted(p for p in 폴더.iterdir() if p.suffix.lower() in 그림_확장자)
    문제 = []
    if not 2 <= len(파일들) <= 4:
        문제.append(f"그림이 {len(파일들)}장이다(2~4장이어야 한다)")
    배정 = {}
    for p in 파일들:
        맞은 = [v for v, re_ in 방향_낱말.items() if re_.search(p.name)]
        if len(맞은) == 0:
            문제.append(f"{p.name}: 방향 낱말이 없다")
            continue
        if len(맞은) > 1:
            문제.append(f"{p.name}: 방향 낱말이 둘 이상이다 {맞은} (CLI는 {맞은[0]}로 넣는다)")
            continue
        방향 = 맞은[0]
        if 방향 in 배정:
            문제.append(f"{p.name}: {방향}이 {배정[방향]}와 겹친다")
            continue
        배정[방향] = p.name
        번호 = p.name[:2]
        if 번호 in 번호_방향 and 번호_방향[번호] != 방향:
            문제.append(f"{p.name}: 번호 {번호}는 {번호_방향[번호]} 자리인데 이름은 {방향}이다")
    if "front" not in 배정:
        문제.append("front 그림이 없다")
    for 방향 in ["front", "left", "back", "right"]:
        print(f"{방향:5} <- {배정.get(방향, '(없음)')}")
    if 문제:
        for x in 문제:
            print("문제:", x)
        raise SystemExit(1)
    print(f"검사 통과 {len(배정)}장")


if __name__ == "__main__":
    main()
