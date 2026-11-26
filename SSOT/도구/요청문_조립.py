# -*- coding: utf-8 -*-
"""SSOT 볼트의 노트에서 Codex용 이미지 요청문을 조립한다.

쓰는 법(저장소 루트에서):
    PYTHONIOENCODING=utf-8 python SSOT/도구/요청문_조립.py <캐릭터 노트 이름>

읽는 것
- SSOT/10_공통스타일.md      머리말 속성(등신, 참고 그림 경로)과 `조립 공통.*` 블록
- SSOT/11_이미지요청문_틀.md  `조립 틀.*`, `조립 방향.*`, `조립 참고.*` 블록
- SSOT/캐릭터/<이름>.md       머리말 속성과 `조립 캐릭터.*` 블록

만드는 것: SSOT/조립결과/<이름>/요청문_{기준,front,left,back,right,시트}.txt (한국어),
          같은 이름 끝에 _영어 를 붙인 영어본(Codex에 넘기는 것), 첨부그림.json
(캐릭터 노트에 기준그림이 없으면 요청문_기준.txt와 그 영어본만 만든다)

영어본: 블록마다 이름 앞에 `영어.`를 붙인 블록(예: `조립 영어.공통.손`)을 같은 노트에 두고,
조립할 때 같은 이름의 한국어 블록 대신 쓴다. {{…}} 자리의 이름은 한국어와 같다.

줄 짝 검사(빠진 조건 찾기): 한국어 블록과 영어 블록, 한국어 조립본과 영어 조립본을 줄마다 맞대어
줄 수, 줄 모양(빈 줄 / `### ` / `- ` / `1. ` / 글), {{…}} 자리, 숫자가 같은지 본다.
영어 블록이 없거나 짝이 어긋나면 아무 파일도 쓰지 않고 종료 코드 1로 멈춘다.

채워지지 않은 자리가 남거나 필요한 블록이 없으면 종료 코드 1로 멈춘다.
"""
import json
import re
import sys
from pathlib import Path

볼트 = Path(__file__).resolve().parent.parent
루트 = 볼트.parent
방향들 = ["front", "left", "back", "right"]
멀티뷰_파일 = {
    "front": "01_front.png",
    "left": "02_profile_facing_left.png",
    "back": "03_back.png",
    "right": "04_profile_facing_right.png",
}


def 읽기(경로):
    글 = 경로.read_text(encoding="utf-8")
    속성 = {}
    m = re.match(r"---\n(.*?)\n---\n", 글, re.S)
    if m:
        for 줄 in m.group(1).splitlines():
            if ":" in 줄:
                k, v = 줄.split(":", 1)
                속성[k.strip()] = v.strip()
    블록 = {}
    for m in re.finditer(r"^```조립 (\S+)[ \t]*\n(.*?)\n```[ \t]*$", 글, re.S | re.M):
        if m.group(1) in 블록:
            raise SystemExit(f"오류: {경로.name}에 블록 '{m.group(1)}'이 두 번 있다")
        블록[m.group(1)] = m.group(2).strip("\n")
    return 속성, 블록


영어 = "영어."
역할_영어 = {
    "컨셉 초안": "concept draft",
    "스타일 참고": "style reference",
    "스타일 참고(같은 방향)": "style reference (same view)",
    "이 캐릭터의 기준 그림": "this character's reference image",
    "고칠 그림": "image to fix",
}


def 줄모양(줄):
    """줄 짝 검사에서 견주는 것: 줄의 종류, {{…}} 자리, 숫자."""
    s = 줄.strip()
    if not s:
        종류 = "빈 줄"
    elif s.startswith("### "):
        종류 = "제목"
    elif s.startswith("- "):
        종류 = "목록"
    elif re.match(r"\d+\. ", s):
        종류 = "번호 목록"
    else:
        종류 = "글"
    자리 = sorted(set(re.findall(r"\{\{[^{}]+\}\}", s)))
    숫자 = re.findall(r"\d+(?:\.\d+)?", re.sub(r"\{\{[^{}]+\}\}", "", s))
    return 종류, 자리, 숫자


def 짝검사(이름, 한글, 영글):
    """두 글을 줄마다 맞대어 어긋난 곳을 목록으로 돌려준다."""
    문제 = []
    가, 나 = 한글.split("\n"), 영글.split("\n")
    if len(가) != len(나):
        문제.append(f"{이름}: 줄 수가 다르다(한국어 {len(가)}줄, 영어 {len(나)}줄)")
    for i, (k, e) in enumerate(zip(가, 나), 1):
        a, b = 줄모양(k), 줄모양(e)
        for 뜻, x, y in zip(("줄 모양이", "{{…}} 자리가", "숫자가"), a, b):
            if x != y:
                문제.append(f"{이름} {i}째 줄: {뜻} 다르다 {x} / {y}\n    한국어: {k}\n    영어: {e}")
    return 문제


def 채우기(글, 값, 깊이=0):
    if 깊이 > 5:
        raise SystemExit("오류: 블록이 서로를 끝없이 가리킨다")

    def 바꿈(m):
        이름 = m.group(1)
        if 이름 not in 값:
            return m.group(0)
        return 채우기(값[이름], 값, 깊이 + 1)

    return re.sub(r"\{\{([^{}]+)\}\}", 바꿈, 글)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("쓰는 법: python SSOT/도구/요청문_조립.py <캐릭터 노트 이름>")
    이름 = sys.argv[1]
    캐릭터_노트 = 볼트 / "캐릭터" / f"{이름}.md"
    if not 캐릭터_노트.exists():
        raise SystemExit(f"오류: {캐릭터_노트} 가 없다")

    공통_속성, 공통_블록 = 읽기(볼트 / "10_공통스타일.md")
    _, 틀_블록 = 읽기(볼트 / "11_이미지요청문_틀.md")
    캐릭터_속성, 캐릭터_블록 = 읽기(캐릭터_노트)

    # 블록의 줄 짝 검사: 한국어 블록마다 영어 블록이 있고 줄마다 짝이 맞아야 한다
    짝문제 = []
    for 노트이름, 블록들 in (("10_공통스타일", 공통_블록), ("11_이미지요청문_틀", 틀_블록), (이름, 캐릭터_블록)):
        for k in 블록들:
            if k.startswith(영어):
                if k[len(영어):] not in 블록들:
                    짝문제.append(f"{노트이름}: 영어 블록 '{k}'에 짝인 한국어 블록이 없다")
            elif 영어 + k not in 블록들:
                짝문제.append(f"{노트이름}: 블록 '{k}'의 영어 블록 '{영어 + k}'이 없다")
            else:
                짝문제 += 짝검사(f"{노트이름} '{k}'", 블록들[k], 블록들[영어 + k])
    if 짝문제:
        for x in 짝문제:
            print("오류(줄 짝):", x)
        raise SystemExit(1)

    값 = {}
    값.update(공통_블록)
    값.update(틀_블록)
    값.update(캐릭터_블록)
    값["등신"] = 캐릭터_속성.get("등신") or 공통_속성.get("등신", "")

    필요 = ["캐릭터.소개", "캐릭터.헤어와의상", "캐릭터.이어지는부위", "캐릭터.제외"]
    for k in 필요:
        if k not in 값:
            raise SystemExit(f"오류: 캐릭터 노트에 블록 '{k}'이 없다")
        for 줄 in 값[k].splitlines() + 값.get(영어 + k, "").splitlines():
            if 줄.lstrip("- ").startswith("("):
                raise SystemExit(f"오류: 캐릭터 노트의 블록 '{k}'(또는 영어 블록)에 틀의 예시가 남아 있다: {줄}")

    스타일참고 = 캐릭터_속성.get("스타일참고", "아니오") == "예"
    컨셉초안 = 캐릭터_속성.get("컨셉초안", "")
    기준그림 = 캐릭터_속성.get("기준그림", "")
    스타일_그림 = 공통_속성.get("스타일_참고그림", "")
    스타일_멀티뷰_폴더 = 공통_속성.get("멀티뷰_참고폴더", "")

    def 조립(값, 영어본):
        결과 = {}
        첨부 = {}

        def 참고글(문단들):
            return "".join(p + "\n\n" for p in 문단들 if p)


        # 기준 그림
        문단, 그림 = [], []
        if 컨셉초안:
            문단.append(값["참고.컨셉초안"])
            그림.append({"역할": "컨셉 초안", "경로": 컨셉초안})
        if 스타일참고:
            문단.append(값["공통.스타일참고"])
            그림.append({"역할": "스타일 참고", "경로": 스타일_그림})
        결과["기준"] = 채우기(값["틀.기준"], {**값, "참고": 참고글(문단)})
        첨부["기준"] = 그림

        # 방향별과 시트는 이 캐릭터의 기준 그림이 정해진 뒤에만 만든다
        for d in (방향들 if 기준그림 else []):
            문단 = [값["참고.기준그림"]]
            그림 = [{"역할": "이 캐릭터의 기준 그림", "경로": 기준그림}]
            if 스타일참고:
                문단.append(값["공통.스타일참고"])
                if 스타일_멀티뷰_폴더:
                    그림.append({"역할": "스타일 참고(같은 방향)", "경로": f"{스타일_멀티뷰_폴더}/{멀티뷰_파일[d]}"})
                else:
                    그림.append({"역할": "스타일 참고", "경로": 스타일_그림})
            방향값 = {**값, "참고": 참고글(문단),
                   "방향.설명": 값[f"방향.{d}.설명"], "방향.세부": 값[f"방향.{d}.세부"]}
            결과[d] = 채우기(값["틀.방향"], 방향값)
            첨부[d] = 그림

        # 시트
        if 기준그림:
            문단 = [값["참고.기준그림"]]
            그림 = [{"역할": "이 캐릭터의 기준 그림", "경로": 기준그림}]
            if 스타일참고:
                문단.append(값["공통.스타일참고"])
                그림.append({"역할": "스타일 참고", "경로": 공통_속성.get("멀티뷰_참고그림", "") or 스타일_그림})
            결과["시트"] = 채우기(값["틀.시트"], {**값, "참고": 참고글(문단)})
            첨부["시트"] = 그림
        elif not 영어본:
            print("알림: 캐릭터 노트에 기준그림이 없어 기준 그림용 요청문만 만든다")

        # 수정: 캐릭터 노트에 수정대상과 캐릭터.수정 블록이 있을 때만
        수정대상 = 캐릭터_속성.get("수정대상", "")
        if 수정대상 and "캐릭터.수정" in 값:
            결과["수정"] = 채우기(값["틀.수정"], 값)
            첨부["수정"] = [{"역할": "고칠 그림", "경로": 수정대상}]

        # 그림을 두 장 이상 넘기면 어느 것이 무엇인지 요청문 맨 앞에 적는다
        for 종류 in 결과:
            if len(첨부[종류]) > 1:
                줄바꿈 = chr(10)
                if 영어본:
                    순서 = 줄바꿈.join(f"{i}. {역할_영어[g['역할']]}" for i, g in enumerate(첨부[종류], 1))
                    머리 = f"There are {len(첨부[종류])} attached images, in this order:"
                else:
                    순서 = 줄바꿈.join(f"{i}. {g['역할']}" for i, g in enumerate(첨부[종류], 1))
                    머리 = f"첨부한 그림은 {len(첨부[종류])}장이고 순서는 다음과 같다."
                결과[종류] = f"{머리}{줄바꿈}{순서}{줄바꿈}{줄바꿈}" + 결과[종류]
        return 결과, 첨부

    값_영어 = {**값, **{k[len(영어):]: v for k, v in 값.items() if k.startswith(영어)}}
    결과, 첨부 = 조립(값, False)
    결과_영어, _ = 조립(값_영어, True)

    # 조립본의 줄 짝 검사
    for 종류 in 결과:
        짝문제 += 짝검사(f"조립본 {종류}", 결과[종류], 결과_영어[종류])
    if 짝문제:
        for x in 짝문제:
            print("오류(줄 짝):", x)
        raise SystemExit(1)

    출력 = 볼트 / "조립결과" / 이름
    출력.mkdir(parents=True, exist_ok=True)
    문제 = []
    for 종류, 글 in 결과.items():
        for 말, 본 in (("", 글), ("(영어) ", 결과_영어[종류])):
            남음 = re.findall(r"\{\{[^{}]+\}\}", 본)
            if 남음:
                문제.append(f"{말}{종류}: 채워지지 않은 자리 {sorted(set(남음))}")
        for g in 첨부[종류]:
            p = g["경로"]
            if p and not p.startswith("(") and not (루트 / p).exists():
                문제.append(f"{종류}: 첨부 그림이 없다 {p}")
            if not p:
                문제.append(f"{종류}: 첨부 그림 경로가 비었다({g['역할']})")
    if 문제:
        for x in 문제:
            print("오류:", x)
        raise SystemExit(1)
    for 종류, 글 in 결과.items():
        (출력 / f"요청문_{종류}.txt").write_text(글.rstrip("\n") + "\n", encoding="utf-8", newline="\n")
        (출력 / f"요청문_{종류}_영어.txt").write_text(
            결과_영어[종류].rstrip("\n") + "\n", encoding="utf-8", newline="\n")
    (출력 / "첨부그림.json").write_text(
        json.dumps(첨부, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for 종류, 글 in 결과.items():
        print(f"{종류}: {len(글)}자, 영어 {len(결과_영어[종류])}자, 첨부 {len(첨부[종류])}장")
    print(f"조립 완료 {len(결과)}개(한국어·영어 각각, 줄 짝 검사 통과) -> {출력.relative_to(루트)}")


if __name__ == "__main__":
    main()
