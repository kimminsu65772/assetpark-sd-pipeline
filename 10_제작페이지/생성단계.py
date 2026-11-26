"""TRIPO 생성 계열 단계 화면의 서버 쪽 (작업 묶음 W10, 기능명세 2부 14·16·17·18절)

2 모델 생성 · 4 리토폴로지 · 5 텍스처 생성 · 6 Smart UV. 실행(승인·한 번만·가짜 실행)은 W07의 `승인.py`를 그대로 쓴다.

- 요청: 에이전트가 `에이전트.py 생성요청`으로 만든다. 값은 SSOT(`단계/2_TRIPO` "TRIPO 값", `단계/4_UV`)와
  `00_공통문서/조사자료/Tripo_3D_공식_2026-11-21/skill/commands/process.md`(tripo-cli 0.11.2)에서 온 기본값.
  2단계 입력은 상태.json의 2단계 `입력`(1단계가 둔 네 장), 4·5·6단계 입력은 에이전트가 `SSOT/도구/TRIPO입력내보내기.py`로 낸 파일.
- 승인을 막는 것(4-5에 더함): 2단계 입력 네 장 검사 실패, 4·5·6단계 입력 파일 없음, 6단계 입력이 삼각형 8만 넘음.
- 받은 뒤 확인: 에이전트가 `에이전트.py 생성확인`으로 `<단계 폴더>/확인.json`을 쓴다(2-2, 5-3, 4_UV 수치 등).
- 끝나는 조건: `단계완료검사`에 붙인다(2부 각 절의 "끝나는 조건").
"""

from __future__ import annotations

import json
import os
import re
import shlex
import struct
import subprocess
import sys
from pathlib import Path

서버 = None


class 요청오류(Exception):  # 묶기 전 자리
    pass


def 묶기(모듈) -> None:
    global 서버, 요청오류
    서버 = 모듈
    요청오류 = 모듈.요청오류


단계들 = (2, 4, 5, 6)
예산삼각형 = 20000       # SSOT 20_3D규격 "캐릭터 한 명의 예산": 삼각형 약 2만
UV한도삼각형 = 80000     # tripo mesh uv 입력 한도(쿼드는 둘로 셈). 넘으면 TRIPO가 받은 뒤 실패·환불
UV간격 = 8               # SSOT 4_UV 합격 수치: 조각 사이 8칸 이상(2048 기준)
방향순서 = ("front", "back", "left", "right")   # tripo generate multiview-to-model front back [left right]
안내판 = "0.11.2"        # 값·가격의 출처 판(process.md). 첫 실행 전에 에이전트가 그때의 도움말로 다시 확인(2부 16절 예외)
그림확장자 = (".png", ".jpg", ".jpeg")


def 텍스처값(a) -> str:
    """SSOT 2_TRIPO의 `조립 규격.TRIPO텍스처명령값` 덩어리(한 곳에만 적힌 값)를 그대로 읽는다."""
    글 = (a.폴더 / "SSOT" / "단계" / "2_TRIPO.md").read_text(encoding="utf-8")
    m = re.search(r"```조립 규격\.TRIPO텍스처명령값\s*\n(.*?)\n```", 글, re.S)
    if not m:
        raise 요청오류(500, "SSOT/단계/2_TRIPO.md에서 'TRIPO텍스처명령값' 덩어리를 찾지 못했습니다.")
    return " ".join(m.group(1).split())


# 단계마다 기본 요청(무엇 · 명령 틀 · 크레딧). {입력}은 저장소 기준 경로(shlex로 감쌈)
def 기본값(a, 번호) -> dict:
    if 번호 == 2:
        return {"무엇": "모델 생성(메시만: P2.0, 쿼드, 면 제한 5,000, 텍스처 끔)",
                "틀": "tripo generate multiview-to-model {입력} --model tripo-p2 -p quad=true -p face_limit=5000 -p texture=false -p pbr=false --no-open",
                "크레딧": "모름", "근거": "SSOT 단계/2_TRIPO 2-1(사용자 결정 2026-11-23). 가격: P2는 100~130(텍스처 단계별) — 텍스처를 끈 값은 안내에 없어 '모름'"}
    if 번호 == 4:
        return {"무엇": "리토폴로지(smart retopology v3.0, 삼각형 20,000)",
                "틀": "tripo mesh decimate {입력} --model v3.0 --face-limit 20000",
                "크레딧": 35, "근거": f"2부 16절, process.md(tripo-cli {안내판}): v3.0 삼각형 35·쿼드 40, v2.0 30. 면 제한은 예산 20_3D규격(삼각형 약 2만)"}
    if 번호 == 5:
        return {"무엇": "텍스처 생성(정밀, PBR 끔, 조명 제거 켬)",
                "틀": "tripo model texture {입력} " + 텍스처값(a),
                "크레딧": 20, "근거": "SSOT 단계/2_TRIPO 'TRIPO 값'(정밀 20크레딧, 2026-11-22의 실제 값)"}
    if 번호 == 6:
        return {"무엇": "Smart UV(전체 1회, 그림 옮기기 켬)",
                "틀": "tripo mesh uv {입력}",
                "크레딧": 20, "근거": "2부 18절, SSOT 단계/4_UV: 그림 옮기기 켬 = --no-bake를 붙이지 않음, 20크레딧, 입력 삼각형 8만 이하"}
    raise 요청오류(400, f"{번호}단계는 TRIPO 생성 계열이 아닙니다(2·4·5·6).")


# ---------------------------------------------------------------- 파일

def 확인파일(a, 이름, 번호) -> Path:
    return a.단계폴더(이름, 번호, 만들기=False) / "확인.json"


def 확인읽기(a, 이름, 번호) -> dict | None:
    p = 확인파일(a, 이름, 번호)
    if not p.is_file():
        return None
    try:
        v = 서버.json_읽기(p)
        return v if isinstance(v, dict) else None
    except Exception:
        return None


def 상대(a, p: Path) -> str:
    return p.resolve().relative_to(a.폴더.resolve()).as_posix()


def 단계입력(a, 이름, 번호) -> list[str]:
    try:
        줄 = a.상태보기(이름)["단계"][번호 - 1]
    except Exception:
        return []
    return [x for x in 줄.get("입력") or [] if isinstance(x, str)]


def 네장정렬(입력: list[str]) -> tuple[list[str], str]:
    """front·back·left·right 이름이 든 네 장을 그 순서로. 못 맞추면 빈 목록과 이유."""
    그림 = [x for x in 입력 if x.lower().endswith(그림확장자)]
    if len(그림) != 4:
        return [], f"입력 그림이 네 장이 아님({len(그림)}장)"
    짝 = {}
    for x in 그림:
        이름 = Path(x).stem.lower()
        맞음 = [d for d in 방향순서 if d in 이름]
        if len(맞음) != 1:
            return [], f"방향(front·back·left·right)을 이름에서 알 수 없음: {Path(x).name}"
        짝[맞음[0]] = x
    if len(짝) != 4:
        return [], "네 방향이 하나씩 있지 않음"
    return [짝[d] for d in 방향순서], ""


def _열쇠(files: list[Path]) -> list:
    return [[str(f), f.stat().st_size, f.stat().st_mtime_ns] for f in files]


def 입력검사(a, 이름) -> dict:
    """2단계 입력 네 장 검사(`SSOT/도구/TRIPO입력_검사.py`). 파일 크기·시각이 같으면 앞 결과를 쓴다."""
    네장, 이유 = 네장정렬(단계입력(a, 이름, 2))
    if not 네장:
        return {"통과": False, "출력": 이유, "입력": []}
    파일 = [a.저장소파일(x) for x in 네장]
    if None in 파일:
        return {"통과": False, "출력": "입력 그림 가운데 없는 파일이 있음", "입력": 네장}
    if len({f.parent for f in 파일}) != 1:
        return {"통과": False, "출력": "네 장이 한 폴더에 있지 않음(검사 도구는 폴더 하나를 봄)", "입력": 네장}
    기록 = a.단계폴더(이름, 2, 만들기=True) / "입력검사.json"
    열쇠 = _열쇠(파일)
    if 기록.is_file():
        try:
            v = 서버.json_읽기(기록)
            if v.get("열쇠") == 열쇠:
                return v
        except Exception:
            pass
    r = subprocess.run([sys.executable, str(a.폴더 / "SSOT" / "도구" / "TRIPO입력_검사.py"), str(파일[0].parent)], cwd=a.폴더,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    출력 = (r.stdout + r.stderr).strip()
    v = {"열쇠": 열쇠, "입력": 네장, "통과": r.returncode == 0 and bool(출력) and 출력.splitlines()[-1].startswith("검사 통과"),
         "출력": 출력[-2000:], "시각": 서버.지금()}
    서버.json_쓰기(기록, v)
    return v


def glb삼각형(p: Path) -> int | None:
    """GLB의 삼각형 수(모드 4 primitive의 인덱스 수 ÷ 3, 인덱스가 없으면 정점 수 ÷ 3). 읽지 못하면 None."""
    try:
        with open(p, "rb") as f:
            머리 = f.read(20)
            if len(머리) < 20 or 머리[:4] != b"glTF":
                return None
            길이, 종류 = struct.unpack("<II", 머리[12:20])
            if 종류 != 0x4E4F534A:
                return None
            g = json.loads(f.read(길이).decode("utf-8"))
        acc = g.get("accessors") or []
        n = 0
        for m in g.get("meshes") or []:
            for pr in m.get("primitives") or []:
                if pr.get("mode", 4) != 4:
                    continue
                i = pr.get("indices")
                c = acc[i]["count"] if isinstance(i, int) else acc[pr["attributes"]["POSITION"]]["count"]
                n += c // 3
        return n
    except Exception:
        return None


def 보기삼각형(a, 이름, 해시: str | None) -> int | None:
    if not 해시:
        return None
    p = a.보기폴더(이름, 만들기=False) / f"{해시}.glb"
    return glb삼각형(p) if p.is_file() else None


def 보기파츠수(a, 이름, 해시: str | None) -> int | None:
    if not 해시:
        return None
    try:
        v = 서버.보기만들기.캐시(a.보기폴더(이름, 만들기=False), 해시)
        return len(v.get("파츠") or []) if v else None
    except Exception:
        return None


def 전해시(a, 이름) -> str | None:
    """3D 보기의 '전'과 같은 것: 지금 해시가 아닌, 검사를 통과한 가장 최근 GLB."""
    try:
        r = a.모델(이름)
    except Exception:
        return None
    전 = r.get("전")
    return Path(전).stem if 전 else None


# ---------------------------------------------------------------- 요청과 승인 막기

def 요청입력(v: dict) -> list[str]:
    """승인 파일의 명령에서 입력 파일(저장소 기준 경로)을 꺼낸다."""
    try:
        조각 = shlex.split(v.get("명령") or "", posix=True)
    except ValueError:
        return []
    입력 = []
    for t in 조각[3:]:   # 'tripo <무리> <명령>' 다음, 첫 '-'로 시작하는 인자 앞까지가 입력 파일
        if t.startswith("-"):
            break
        입력.append(t)
    return 입력


def 요청하기(a, 이름, 번호, 입력: str | None) -> dict:
    """에이전트 명령 `생성요청`: SSOT 기본값으로 승인 요청을 만든다(W07 `승인.요청만들기`)."""
    기 = 기본값(a, 번호)
    if 번호 == 2:
        if 입력:
            raise 요청오류(400, "2단계 입력은 상태.json의 2단계 입력(1단계가 둔 네 장)을 씁니다. 파일을 주지 마세요.")
        r = 입력검사(a, 이름)
        if not r["통과"]:
            raise 요청오류(409, f"입력 네 장 검사 실패 — 요청을 만들지 않았습니다: {r['출력'][-300:]}")
        파일들 = r["입력"]
    else:
        f = a.저장소파일(입력 or "")
        if not f:
            raise 요청오류(400, f"{번호}단계 입력 파일(저장소 기준 경로)이 필요합니다: SSOT/도구/TRIPO입력내보내기.py로 낸 GLB/FBX.")
        if f.suffix.lower() not in (".glb", ".fbx", ".obj", ".gltf"):
            raise 요청오류(400, "입력은 GLB·FBX·OBJ·GLTF여야 합니다.")
        if 번호 == 6:
            n = glb삼각형(f) if f.suffix.lower() == ".glb" else None
            if n is not None and n > UV한도삼각형:
                raise 요청오류(409, f"입력이 삼각형 {n:,}개로 8만을 넘습니다 — Smart UV 요청을 만들지 않았습니다(4단계 리토폴로지 먼저).")
        파일들 = [상대(a, f)]
    명령 = 기["틀"].format(입력=" ".join(shlex.quote(x) for x in 파일들))
    r = 서버.승인.요청만들기(a, 이름, 번호, 기["무엇"], 명령, 기["크레딧"], 1, 만든곳="에이전트 생성요청")
    return dict(r, 무엇=기["무엇"], 명령=명령, 크레딧=기["크레딧"], 횟수=1, 근거=기["근거"])


def 막는이유(a, 이름, 번호, v: dict) -> str:
    """승인 단추를 막는 단계별 까닭(W07 `승인.추가막기`). 빈 글이면 막지 않음."""
    if 번호 == 2:
        r = 입력검사(a, 이름)
        if not r["통과"]:
            return f"입력 네 장 검사 실패: {r['출력'].splitlines()[-1] if r['출력'] else '이유 없음'}"
        if 요청입력(v) != r["입력"]:
            return "요청의 입력이 지금 2단계 입력(네 장)과 다릅니다 — 에이전트에게 요청을 다시 만들어 달라고 하세요"
        return ""
    입력 = 요청입력(v)
    if not 입력 or any(a.저장소파일(x) is None for x in 입력):
        return f"요청의 입력 파일이 없습니다: {', '.join(입력) or '(없음)'}"
    if 번호 == 6:
        f = a.저장소파일(입력[0])
        n = glb삼각형(f) if f.suffix.lower() == ".glb" else None
        if n is not None and n > UV한도삼각형:
            return f"입력이 삼각형 {n:,}개로 8만을 넘습니다(TRIPO가 받은 뒤 실패·환불하는 경우라 미리 막음)"
    return ""


# ---------------------------------------------------------------- 받은 뒤 확인(에이전트)

확인항목 = {   # 단계 → (반드시 있어야 하는 항목, 쓸 수 있는 항목)
    2: ({"파일구성", "면수", "방향"}, {"파일구성", "면수", "방향", "텍스처해상도", "뼈수", "동작", "받은파일", "메모"}),
    4: ({"면수전", "면수후", "파츠수전", "파츠수후", "대칭점검", "접합부점검"},
        {"면수전", "면수후", "파츠수전", "파츠수후", "대칭점검", "접합부점검", "고친것", "받은파일", "메모"}),
    5: ({"받은그림", "정점자리같음", "형태", "UV", "객체구성"},
        {"받은그림", "정점자리같음", "형태", "UV", "뼈대", "가중치", "객체구성", "받은파일", "메모"}),
    6: ({"겹침", "최소간격", "UV범위안", "뒤집힌삼각형", "그림비교통과", "격자직접봄"},
        {"겹침", "최소간격", "UV범위안", "뒤집힌삼각형", "그림비교통과", "격자직접봄", "가다듬음", "다시구움", "파츠", "받은파일", "메모"}),
}


def 확인쓰기(a, 이름, 번호, v: dict) -> dict:
    """에이전트 명령 `생성확인`: 받은 파일 확인 결과를 `확인.json`에 쓴다. 그림 경로는 저장소 안에 실제로 있어야 한다."""
    if 번호 not in 단계들:
        raise 요청오류(400, "생성확인은 2·4·5·6단계에서만 씁니다.")
    꼭, 됨 = 확인항목[번호]
    if not isinstance(v, dict):
        raise 요청오류(400, "확인 파일은 JSON 객체여야 합니다.")
    모르는것 = set(v) - 됨
    if 모르는것:
        raise 요청오류(400, f"모르는 항목: {sorted(모르는것)} (쓸 수 있는 것: {sorted(됨)})")
    빠짐 = 꼭 - set(v)
    if 빠짐:
        raise 요청오류(400, f"빠진 항목: {sorted(빠짐)}")
    for k in ("대칭점검", "접합부점검", "정점자리같음", "UV범위안", "그림비교통과", "격자직접봄", "가다듬음", "다시구움"):
        if k in v and not isinstance(v[k], bool):
            raise 요청오류(400, f"'{k}'은 참/거짓이어야 합니다.")
    for k in ("면수전", "면수후", "파츠수전", "파츠수후", "겹침", "최소간격", "뒤집힌삼각형"):
        if k in v and not (isinstance(v[k], (int, float)) and not isinstance(v[k], bool) and v[k] >= 0):
            raise 요청오류(400, f"'{k}'은 0 이상의 숫자여야 합니다.")
    for k in ("받은그림", "받은파일"):
        if k in v:
            if not isinstance(v[k], list) or not all(isinstance(x, str) for x in v[k]):
                raise 요청오류(400, f"'{k}'은 저장소 기준 경로의 목록이어야 합니다.")
            없음 = [x for x in v[k] if a.저장소파일(x) is None]
            if 없음:
                raise 요청오류(400, f"'{k}'에 없는 파일: {없음[:3]}")
    if 번호 == 5 and not all(x.lower().endswith(그림확장자) for x in v["받은그림"]):
        raise 요청오류(400, "'받은그림'은 PNG·JPG여야 합니다(화면에 작게 띄움).")
    값 = dict(v, 만든시각=서버.지금(), 작업본해시=a._지금작업본해시(이름), 만든곳="10_제작페이지/에이전트.py 생성확인")
    p = a.단계폴더(이름, 번호, 만들기=True) / "확인.json"
    서버.json_쓰기(p, 값)
    서버.기록(f"받은 뒤 확인: {번호}단계 {p.name}", a, 이름)
    return {"결과": "씀", "파일": 상대(a, p), "모자람": 완료모자람(a, 이름, 번호)}


# ---------------------------------------------------------------- 끝나는 조건(2부 14·16·17·18절)

def 마지막실행(a, 이름, 번호) -> dict | None:
    for q in reversed(서버.승인.요청파일들(a, 이름, 번호)):
        try:
            v = 서버.json_읽기(q)
        except Exception:
            continue
        if v.get("실행") in ("실행됨", "실패", "실행 중"):
            return dict(v, 파일=q.name)
    return None


def 완료모자람(a, 이름, 번호) -> list[str]:
    모자람 = []
    실행 = 마지막실행(a, 이름, 번호)
    가져옴 = (a.상태보기(이름)["단계"][번호 - 1] or {}).get("출처") in 서버.가져오기.출처들   # W08 가져오기로 받은 입력
    if 가져옴 and 번호 == 2:
        return []   # 2부 14절: TRIPO 웹에서 받은 모델을 가져오면 이 단계는 "가져옴"으로 끝
    if not 가져옴:
        if not 실행 or 실행.get("실행") != "실행됨":
            모자람.append("실행해 받은 결과가 없음(승인 → 실행됨)")
        elif (실행.get("결과") or {}).get("쓴크레딧") is None:
            모자람.append("서버가 실제로 쓴 크레딧을 기록하지 못함")
    c = 확인읽기(a, 이름, 번호)
    if not c:
        모자람.append({2: "받은 파일 확인(2-2)이 없음 — 에이전트 '생성확인'", 4: "리토폴로지 결과 확인이 없음 — 에이전트 '생성확인'",
                    5: "받은 파일 확인(5-3)이 없음 — 에이전트 '생성확인'", 6: "UV 수치 점검이 없음 — 에이전트 '생성확인'"}[번호])
        return 모자람
    if 실행 and c.get("만든시각", "") < (실행.get("실행끝시각") or ""):
        모자람.append("확인이 마지막 실행보다 오래됨 — 새로 받은 것을 다시 확인해야 함")
    if 번호 == 4:
        if c["면수후"] > 예산삼각형:
            모자람.append(f"면 수(삼각형) {c['면수후']:,}개가 예산 {예산삼각형:,}을 넘음")
        if c["파츠수후"] != c["파츠수전"]:
            모자람.append(f"파츠 수가 바뀜: {c['파츠수전']} → {c['파츠수후']}")
        if not c["대칭점검"]:
            모자람.append("대칭을 다시 점검하지 않음")
        if not c["접합부점검"]:
            모자람.append("접합부를 다시 점검하지 않음")
    if 번호 == 5 and not c["정점자리같음"]:
        모자람.append("받은 메시의 정점 자리가 작업본과 다름")
    if 번호 == 6:
        if c["겹침"] != 0:
            모자람.append(f"UV 겹침 {c['겹침']}곳(0이어야 함, 한 조각 안의 접힘 포함)")
        if c["최소간격"] < UV간격:
            모자람.append(f"조각 사이 최소 간격 {c['최소간격']}칸(8칸 이상, 2048 기준)")
        if not c["UV범위안"]:
            모자람.append("UV가 0~1 밖으로 나감")
        if c["뒤집힌삼각형"] != 0:
            모자람.append(f"뒤집힌 삼각형 {c['뒤집힌삼각형']}개")
        if not c["그림비교통과"]:
            모자람.append("옮겨진 그림이 원래 그림과 다르게 보임(같은 방향 그림 비교)")
        if not c["격자직접봄"]:
            모자람.append("격자 그림을 에이전트가 직접 보지 않음")
        if c.get("가다듬음") and not c.get("다시구움"):
            모자람.append("Blender에서 UV를 가다듬었는데 그림을 다시 옮겨 굽지 않음(5-4)")
    return 모자람


# ---------------------------------------------------------------- 화면

def 보기(a, 이름, 번호) -> dict:
    """옆 기둥에 그릴 것."""
    if 번호 not in 단계들:
        raise 요청오류(400, "2·4·5·6단계만 있습니다.")
    기 = 기본값(a, 번호)
    값 = {"단계": 번호, "기본": {"무엇": 기["무엇"], "틀": 기["틀"], "크레딧": 기["크레딧"], "근거": 기["근거"]},
         "확인": 확인읽기(a, 이름, 번호), "모자람": 완료모자람(a, 이름, 번호), "예산삼각형": 예산삼각형, "UV한도삼각형": UV한도삼각형,
         "UV간격": UV간격, "안내판": 안내판}
    실행 = 마지막실행(a, 이름, 번호)
    값["실행"] = {"파일": 실행["파일"], "실행": 실행.get("실행"), "가짜": bool((실행.get("결과") or {}).get("가짜")),
                 "받은파일": (실행.get("결과") or {}).get("받은파일") or [], "끝시각": 실행.get("실행끝시각") or ""} if 실행 else None
    if 번호 in (2, 5):
        r = 입력검사(a, 이름)
        값["입력그림"] = r["입력"]
        값["입력검사"] = {"통과": r["통과"], "출력": (r["출력"] or "").splitlines()[-1:] }
    if 번호 in (4, 6):
        h = a._지금작업본해시(이름)
        전 = 전해시(a, 이름)
        값["면수"] = {"지금": 보기삼각형(a, 이름, h), "전": 보기삼각형(a, 이름, 전),
                    "파츠지금": 보기파츠수(a, 이름, h), "파츠전": 보기파츠수(a, 이름, 전)}
    return 값


def 바뀜(a, 이름, 번호) -> str:
    """맥박이 보는 것: 확인.json·승인 파일·입력검사의 바뀐 시각."""
    try:
        d = a.단계폴더(이름, 번호, 만들기=False)
    except Exception:
        return ""
    조각 = []
    for p in [d / "확인.json", d / "입력검사.json"] + list(d.glob("승인_*.json")):
        try:
            조각.append(f"{p.name}:{p.stat().st_mtime_ns}")
        except OSError:
            pass
    return "|".join(sorted(조각))
