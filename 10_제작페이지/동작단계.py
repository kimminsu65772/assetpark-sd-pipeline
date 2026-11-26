"""10·11단계 동작·내보내기 화면의 서버 쪽 (작업 묶음 W14, 기능명세 2부 22·23절, SSOT 단계/7_Unity)

10 애니메이션
- 동작 모음: `상태.json`의 `"동작모음"` {이름, glb, fbx}. 목록은 GLB의 animations 이름(FBX의 "Armature|<이름>"과 같음, UAL1은 43개).
- 미리 보기: 단계를 열면(옆 기둥이 물으면) 서버가 뒤에서 모음의 모든 동작을 이 캐릭터에 옮긴 GLB를 만든다.
  작업본 해시마다 `보기/동작미리/<해시>/`에 한 번만(끈것.glb = 옮기기만, 켠것.glb = 보폭줄이기·팔벌림까지).
  차례: 동작옮기기.py(앞붙임 P_) → 동작정리.py(P_ 말고 지움) → GLB만들기.py → (리깅설정에 있으면) 보폭줄이기.py → 팔벌림.py → GLB만들기.py.
  작업본은 읽기만 한다(도구들이 모두 다른 이름으로 저장). 다 되기 전에는 모음의 원래 인형 GLB를 그대로 보인다.
- 고르기(체크)는 페이지가 `10_애니메이션/고른동작.json`, '옮기기'는 `옮기기요청_<시각>.json`. 실제 옮기기·자동 처리·교차 재기는 에이전트가 하고
  `에이전트.py 동작옮김`으로 `옮김.json`을 쓴다(동작마다 성공·교차 수·관통 장·새 관통).
- TRIPO 동작 생성: 에이전트 `동작생성요청 <프리셋,…>` → 승인 상자(W07). `tripo anim retarget <8단계 오토 리깅 작업 번호> --animation preset:…`.
  해 본 적 없음 — 첫 실행 전에 값·가격을 승인 상자에서 확인(2부 22절 예외). 가짜 실행이 기본.
- 리포트(칠하기·구간)는 9단계와 같다(W13 리깅단계.js의 시간 막대). 에이전트가 처리 결과 줄마다 "쪽"(동작 / 리깅)을 적고,
  리깅 쪽은 9단계 옆 기둥에 "10단계에서 넘어온 리포트"로 보인다.
11 내보내기
- Unity 프로젝트: `상태.json`의 `"Unity"` {경로, 넣을이름}. 페이지가 경로를 받아 `ProjectSettings/ProjectVersion.txt`의 버전을 SSOT(6000.3.7f1)와 비교.
  경로 없음·버전 다름 → 내보내기 잠김. `Temp/UnityLockfile`이 있으면 Unity가 열려 있음(알림만). `Assets/Character/<넣을이름>.*`이 있으면 덮어쓸지 묻는다.
- '내보내기'는 `11_내보내기/요청_<시각>.json`을 남긴다. 이 서버는 Unity 프로젝트에 아무것도 쓰지 않는다. FBX 내보내기(7-4)·Unity 설정(7-5)·
  찍기(7-6·7-7)는 에이전트가 하고 `에이전트.py 내보내기결과`로 `검사표.json`. 사용자가 Play 그림을 보면 '봄'(`봄.json`).
"""

from __future__ import annotations

import json
import os
import re
import shlex
import struct
import subprocess
import threading
import time
from pathlib import Path

서버 = None


class 요청오류(Exception):  # 묶기 전 자리
    pass


def 묶기(모듈) -> None:
    global 서버, 요청오류
    서버 = 모듈
    요청오류 = 모듈.요청오류


애니 = 10
내보 = 11
단계들 = (애니, 내보)
SSOT유니티 = "6000.3.7f1"     # SSOT 단계/7_Unity "버전과 프로젝트"
가져오기방식 = "Humanoid"       # 같은 노트 "가져오는 방식"(초안)
넣을곳 = "Assets/Character"     # 7-5
미리앞 = "P_"                  # 미리 보기 동작 앞붙임(작업본의 UAL_ 동작과 겹치지 않게)
꼬리표 = re.compile(r"^(?:P_|S\d+_|A[MA]\d+_)+")   # 동작옮기기·보폭줄이기·팔벌림이 붙이는 앞붙임
블렌더제한초 = 3600
프리셋 = re.compile(r"^[a-z0-9_:-]{1,40}$")
검사상태 = ("통과", "경고", "실패")
표시들 = ("7-5", "7-6", "7-7")


# ---------------------------------------------------------------- 파일

def 폴더(a, 이름, 번호, 만들기=False) -> Path:
    return a.단계폴더(이름, 번호, 만들기=만들기)


def 읽기(p: Path) -> dict | None:
    if not p.is_file():
        return None
    try:
        v = 서버.json_읽기(p)
        return v if isinstance(v, dict) else None
    except Exception:
        return None


def 상대(a, p: Path) -> str:
    return p.resolve().relative_to(a.폴더.resolve()).as_posix()


def 쓰기(a, 이름, 번호, 파일이름: str, 값: dict) -> Path:
    p = 폴더(a, 이름, 번호, 만들기=True) / 파일이름
    서버.json_쓰기(p, {"꼴버전": 서버.꼴버전, "만든시각": 서버.지금(), "작업본해시": a._지금작업본해시(이름), **값})
    return p


def 상태값(a, 이름) -> dict:
    return 읽기(a.상태파일(이름)) or {}


def 상태에쓰기(a, 이름, 열쇠: str, 값) -> None:
    """상태.json의 위 칸 하나(동작모음·Unity)를 바꾼다. 단계 줄은 건드리지 않는다."""
    p = a.상태파일(이름)
    with 서버.파일잠금(p):
        v = 서버.json_읽기(p)
        v[열쇠] = 값
        서버.json_쓰기(p, v)


def 리깅설정(a, 이름) -> dict:
    return 읽기(a.캐릭터폴더(이름) / "04_Blender" / "리깅설정.json") or {}


def 자동처리(설정: dict) -> list[str]:
    """리깅설정.json에 값이 있는 자동 처리(2부 22절 '보폭·팔 벌림·굽기')."""
    return [n for k, n in (("보폭", "보폭"), ("팔벌림", "팔 벌림"), ("자락", "굽기")) if 설정.get(k)]


# ---------------------------------------------------------------- 동작 모음

_모음캐시: dict = {}


def glb동작(p: Path) -> list[str]:
    """GLB의 JSON 조각에서 animations 이름만 읽는다(Blender 없이)."""
    열쇠 = (str(p), p.stat().st_mtime_ns)
    if 열쇠 in _모음캐시:
        return _모음캐시[열쇠]
    with open(p, "rb") as f:
        머리 = f.read(12)
        if len(머리) != 12 or 머리[:4] != b"glTF":
            raise 요청오류(409, f"동작 모음 GLB가 아닙니다: {p.name}")
        길이, 종류 = struct.unpack("<II", f.read(8))
        if 종류 != 0x4E4F534A:
            raise 요청오류(409, f"동작 모음 GLB의 첫 조각이 JSON이 아닙니다: {p.name}")
        j = json.loads(f.read(길이))
    이름들 = [str(x.get("name") or "") for x in j.get("animations") or [] if x.get("name")]
    _모음캐시[열쇠] = 이름들
    return 이름들


def 모음(a, 이름) -> dict:
    """{이름, glb, fbx, 동작: [...], 오류}. 경로는 상태.json에 적힌 그대로(저장소 밖이어도 됨, 읽기만)."""
    m = 상태값(a, 이름).get("동작모음")
    if not isinstance(m, dict) or not m.get("glb"):
        return {"이름": "", "동작": [], "오류": "상태.json에 \"동작모음\"(이름·glb·fbx 경로)이 없습니다"}
    값 = {"이름": str(m.get("이름") or "동작 모음"), "glb": str(m["glb"]), "fbx": str(m.get("fbx") or ""), "동작": [], "오류": ""}
    g = 경로(a, m["glb"])
    if not g or g.suffix.lower() != ".glb" or not g.is_file():
        return dict(값, 오류=f"동작 모음 GLB가 없습니다: {m['glb']}")
    try:
        값["동작"] = glb동작(g)
    except 요청오류 as e:
        return dict(값, 오류=e.글)
    f = 경로(a, 값["fbx"]) if 값["fbx"] else None
    if not f or f.suffix.lower() != ".fbx" or not f.is_file():
        값["오류"] = f"동작 모음 FBX가 없어 이 캐릭터로 옮길 수 없습니다(원래 인형만 보임): {값['fbx'] or '(안 적힘)'}"
    return 값


def 경로(a, s: str) -> Path | None:
    if not isinstance(s, str) or not s.strip():
        return None
    p = Path(s)
    return (p if p.is_absolute() else a.폴더 / p).resolve()


# ---------------------------------------------------------------- 10단계: 미리 보기(뒤에서 만들기)

_일들: dict[str, dict] = {}
_일잠금 = threading.Lock()


def 미리폴더(a, 이름, 해시: str) -> Path:
    return a.보기폴더(이름, 만들기=True) / "동작미리" / 해시


def _블렌더(blend: Path, 스크립트: Path, 인자: list[str], 로그) -> int:
    bm = 서버.보기만들기
    명령 = [bm.bash찾기(), str(bm.실행도구), str(blend), str(스크립트), "--", *인자]
    로그.write(f"\n$ {' '.join(명령[2:4])} -- …({len(인자)}개)\n")
    로그.flush()
    r = subprocess.run(명령, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=dict(os.environ, PYTHONIOENCODING="utf-8", TAIL="60"),
                       timeout=블렌더제한초, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    로그.write(r.stdout.decode("utf-8", "replace"))
    로그.write(f"[종료 코드 {r.returncode}]\n")
    로그.flush()
    return r.returncode


def _만들기(a, 이름, 해시: str, 작업본: Path, 모: dict, 설정파일: Path, 처리: list[str], 일: dict) -> None:
    d = 미리폴더(a, 이름, 해시)
    d.mkdir(parents=True, exist_ok=True)
    도구 = a.폴더 / "SSOT" / "도구" / "리깅"
    블 = Path(__file__).resolve().parent / "블렌더"
    t1, t2, t3, t4 = d / "_옮김.blend", d / "_정리.blend", d / "_보폭.blend", d / "_팔.blend"
    이름들 = 모["동작"]
    try:
        with open(d / "로그.txt", "w", encoding="utf-8") as 로그:
            로그.write(f"{서버.지금()} 작업본 {작업본}\n")
            def 걸음(글, blend, 스크립트, 인자, 나올):
                일["걸음"] = 글
                rc = _블렌더(blend, 스크립트, 인자, 로그)
                if rc != 0 or not Path(나올).is_file():
                    raise RuntimeError(f"{글} 실패(Blender 종료 코드 {rc}) — 로그: {상대(a, d / '로그.txt')}")
            걸음(f"동작 {len(이름들)}개를 이 캐릭터로 옮기는 중", 작업본, 도구 / "동작옮기기.py",
                [str(설정파일), str(경로(a, 모["fbx"])), str(t1), ",".join(이름들), "-", 미리앞], t1)
            걸음("미리 보기 동작만 남기는 중", t1, 블 / "동작정리.py", [str(t2), 미리앞], t2)
            걸음("미리 보기 GLB(자동 처리 끔)를 만드는 중", t2, 블 / "GLB만들기.py", [str(d / "끈것.glb"), str(d / "끈것.json")], d / "끈것.glb")
            일["끈것"] = True
            앞, 이번 = t2, [미리앞 + n for n in 이름들]
            if "보폭" in 처리:
                걸음("보폭 줄이기", 앞, 도구 / "보폭줄이기.py", [str(설정파일), str(t3), ",".join(이번)], t3)
                비율 = round(float(리깅설정(a, 이름).get("보폭")) * 100)
                앞, 이번 = t3, [f"S{비율}_{n}" for n in 이름들]
            if "팔 벌림" in 처리:
                걸음("팔 벌림", 앞, 도구 / "팔벌림.py", [str(설정파일), str(t4), ",".join(이번)], t4)
                앞 = t4
            if 앞 != t2:
                걸음("미리 보기 GLB(자동 처리 켬)를 만드는 중", 앞, 블 / "GLB만들기.py", [str(d / "켠것.glb"), str(d / "켠것.json")], d / "켠것.glb")
                일["켠것"] = True
        일.update(상태="됨", 걸음="", 끝시각=서버.지금())
    except subprocess.TimeoutExpired:
        일.update(상태="실패", 오류=f"Blender가 {블렌더제한초}초 안에 끝나지 않았습니다.")
    except Exception as e:
        일.update(상태="실패", 오류=str(e)[:400])
    finally:
        for p in (t1, t2, t3, t4):
            try:
                p.unlink()
            except OSError:
                pass
        서버.json_쓰기(d / "상태.json", {k: v for k, v in 일.items() if k != "시작"})
        서버.기록(f"10단계 미리 보기 {일['상태']}: {해시}", a, 이름)


def 미리상태(a, 이름, 시작: bool) -> dict:
    """미리 보기 GLB 상태. 시작=True면 없을 때 뒤에서 만들기를 시작한다(한 해시에 한 번)."""
    h = a._지금작업본해시(이름)
    if not h:
        return {"상태": "작업본 없음"}
    열쇠 = f"{이름}/{h}"
    d = a.보기폴더(이름, 만들기=False) / "동작미리" / h
    with _일잠금:
        일 = _일들.get(열쇠)
        if 일 is None and (d / "상태.json").is_file():
            일 = 읽기(d / "상태.json") or {}
            if 일.get("상태") == "만드는 중":   # 서버가 꺼지며 끊김
                일 = None
            else:
                _일들[열쇠] = 일
        if 일 is None and 시작:
            모 = 모음(a, 이름)
            작업본 = a.작업본파일(이름)
            설정파일 = a.캐릭터폴더(이름) / "04_Blender" / "리깅설정.json"
            if 모["오류"] or not 모["동작"]:
                return {"상태": "못 만듦", "오류": 모["오류"] or "모음에 동작이 없음"}
            if not 작업본 or not 설정파일.is_file():
                return {"상태": "못 만듦", "오류": "작업본이나 04_Blender/리깅설정.json이 없습니다"}
            일 = {"상태": "만드는 중", "걸음": "시작", "시작": time.monotonic(), "시작시각": 서버.지금(), "해시": h,
                 "끈것": False, "켠것": False, "처리": 자동처리(리깅설정(a, 이름))}
            _일들[열쇠] = 일
            threading.Thread(target=_만들기, args=(a, 이름, h, 작업본, 모, 설정파일, [x for x in 일["처리"] if x != "굽기"], 일), daemon=True).start()
    if not 일:
        return {"상태": "아직 안 함", "해시": h}
    값 = {k: v for k, v in 일.items() if k != "시작"}
    if 일.get("상태") == "만드는 중" and "시작" in 일:
        값["경과초"] = round(time.monotonic() - 일["시작"])
    for k in ("끈것", "켠것"):
        if 값.get(k):
            j = 읽기(d / f"{k}.json") or {}
            값[k] = {"주소": f"/api/동작/파일?이름={이름}&종류={k}&해시={h}", "짝": 짝짓기(j.get("동작") or [], k)}
    return 값


def 짝짓기(glb동작들: list, 종류: str) -> dict:
    """모음 동작 이름 → 미리 보기 GLB의 동작 이름. 켠것은 앞붙임이 가장 긴(자동 처리를 가장 많이 거친) 것."""
    짝: dict[str, str] = {}
    for x in glb동작들:
        n = x.get("이름") if isinstance(x, dict) else x
        if not isinstance(n, str):
            continue
        꼬리 = n.split("|")[-1]
        m = 꼬리표.match(꼬리)
        if not m:
            continue
        원 = 꼬리[m.end():]
        if 종류 == "끈것" and m.group(0) != 미리앞:
            continue
        if 원 not in 짝 or len(n) > len(짝[원]):
            짝[원] = n
    return 짝


def 파일(a, 이름, 종류: str, 해시: str | None) -> Path:
    """`/api/동작/파일`: 모음 GLB 또는 미리 보기 GLB."""
    if 종류 == "모음":
        g = 경로(a, (상태값(a, 이름).get("동작모음") or {}).get("glb", ""))
        if not g or g.suffix.lower() != ".glb" or not g.is_file():
            raise 요청오류(404, "동작 모음 GLB가 없습니다.")
        return g
    if 종류 not in ("끈것", "켠것") or not 해시 or not re.fullmatch(r"[0-9a-f]{12}", 해시):
        raise 요청오류(400, "종류는 모음·끈것·켠것, 해시는 12자리.")
    return a.보기폴더(이름, 만들기=False) / "동작미리" / 해시 / f"{종류}.glb"


# ---------------------------------------------------------------- 10단계: 고르기·옮기기(페이지), 옮김·생성 요청(에이전트)

def 고르기(a, 이름, 몸: dict) -> dict:
    a._주인확인(몸.get("탭"), 이름)
    v = 몸.get("고른")
    모 = 모음(a, 이름)
    if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
        raise 요청오류(400, "'고른'은 동작 이름 목록이어야 합니다.")
    없음 = [x for x in v if x not in 모["동작"]]
    if 없음:
        raise 요청오류(409, f"모음에 없는 동작: {', '.join(없음[:5])}")
    순서 = [x for x in 모["동작"] if x in set(v)]
    p = 쓰기(a, 이름, 애니, "고른동작.json", {"모음": 모["이름"], "고른": 순서, "누가": "사용자"})
    return {"됨": True, "파일": 상대(a, p), "고른수": len(순서)}


def 고른것(a, 이름) -> list[str]:
    return list((읽기(폴더(a, 이름, 애니) / "고른동작.json") or {}).get("고른") or [])


def 옮기기요청(a, 이름, 몸: dict) -> dict:
    """페이지 '옮기기': 고른 동작을 에이전트가 옮기도록 요청 파일을 남긴다(옮기기는 에이전트, 7-1)."""
    a._주인확인(몸.get("탭"), 이름)
    고른 = 고른것(a, 이름)
    if not 고른:
        raise 요청오류(409, "고른 동작이 없습니다. 목록에서 체크하세요.")
    모 = 모음(a, 이름)
    if not 모.get("fbx") or "FBX가 없어" in 모["오류"]:
        raise 요청오류(409, 모["오류"] or "동작 모음 FBX가 없습니다.")
    켬 = bool(몸.get("자동처리", True))
    p = 쓰기(a, 이름, 애니, f"옮기기요청_{서버.지금(파일용=True)}.json",
           {"모음": 모["이름"], "fbx": 모["fbx"], "동작": 고른, "자동처리": 자동처리(리깅설정(a, 이름)) if 켬 else [], "누가": "사용자"})
    서버.기록(f"10단계 옮기기 요청: {len(고른)}개", a, 이름)
    a.알림쓰기(이름, 애니, f"동작 {len(고른)}개를 옮겨 달라는 요청을 남겼습니다. Claude 앱에서 '10단계 옮기기 해 줘'라고 알려 주세요.", "안내")
    return {"됨": True, "파일": 상대(a, p), "동작수": len(고른)}


def 마지막옮기기요청(a, 이름) -> dict | None:
    d = 폴더(a, 이름, 애니)
    if not d.is_dir():
        return None
    q = sorted(d.glob("옮기기요청_*.json"))
    return dict(읽기(q[-1]) or {}, 파일=q[-1].name) if q else None


def 옮김쓰기(a, 이름, v: dict) -> dict:
    """에이전트 `동작옮김`: {동작: [{원본, 이름, 성공, 까닭?, 자동처리?, 장수, 교차수, 관통장, 새관통, 장초당?, 시작장?, 찍은그림?}], 확인범위}."""
    목록 = v.get("동작") if isinstance(v, dict) else None
    if not isinstance(목록, list) or not 목록:
        raise 요청오류(400, "'동작'은 동작마다 {원본, 이름, 성공, …} 목록이어야 합니다.")
    for x in 목록:
        if not isinstance(x, dict) or not isinstance(x.get("원본"), str) or not x["원본"]:
            raise 요청오류(400, "동작 한 줄에 '원본'(모음의 동작 이름)이 없습니다.")
        if not isinstance(x.get("성공"), bool):
            raise 요청오류(400, f"{x['원본']}: '성공'은 참/거짓.")
        if not x["성공"]:
            if not str(x.get("까닭") or "").strip():
                raise 요청오류(400, f"{x['원본']}: 옮기지 못했으면 '까닭'(예: 뼈 이름이 대응표에 없음)이 있어야 합니다.")
            continue
        if not isinstance(x.get("이름"), str) or not x["이름"]:
            raise 요청오류(400, f"{x['원본']}: '이름'(작업본 GLB의 동작 이름)이 없습니다.")
        for k in ("장수", "교차수"):
            if not (isinstance(x.get(k), int) and not isinstance(x.get(k), bool) and x[k] >= 0):
                raise 요청오류(400, f"{x['원본']}: '{k}'은 0 이상의 정수여야 합니다(교차 재기 7-3).")
        if not isinstance(x.get("관통장", []), list) or not all(isinstance(i, int) and not isinstance(i, bool) for i in x.get("관통장", [])):
            raise 요청오류(400, f"{x['원본']}: '관통장'은 장 번호 목록.")
        if not isinstance(x.get("새관통", False), bool):
            raise 요청오류(400, f"{x['원본']}: '새관통'은 참/거짓.")
        if not isinstance(x.get("자동처리", []), list) or not all(s in ("보폭", "팔 벌림", "굽기") for s in x.get("자동처리", [])):
            raise 요청오류(400, f"{x['원본']}: '자동처리'는 보폭·팔 벌림·굽기 중에서.")
        if not all(isinstance(g, str) and a.저장소파일(g) for g in x.get("찍은그림", [])):
            raise 요청오류(400, f"{x['원본']}: '찍은그림'은 저장소 안의 그림 경로 목록.")
        for k in ("장초당", "시작장"):
            if k in x and not (isinstance(x[k], (int, float)) and not isinstance(x[k], bool) and x[k] >= 0):
                raise 요청오류(400, f"{x['원본']}: '{k}'은 0 이상의 숫자.")
    p = 쓰기(a, 이름, 애니, "옮김.json", {"동작": 목록, "확인범위": str(v.get("확인범위") or "")[:400]})
    못 = [x["원본"] for x in 목록 if not x["성공"]]
    새 = [x["원본"] for x in 목록 if x["성공"] and x.get("새관통")]
    서버.기록(f"10단계 옮김: {len(목록) - len(못)}개 성공, 실패 {len(못)}, 새 관통 {len(새)}", a, 이름)
    글 = f"동작 {len(목록) - len(못)}개를 옮겼습니다."
    if 못:
        글 += f" 옮기지 못함 {len(못)}개({', '.join(못[:3])}) — 동작 줄에 까닭."
    if 새:
        글 += f" 새 관통 {len(새)}개(빨간 표시, 9단계 보기로 열 수 있음)."
    a.알림쓰기(이름, 애니, 글 + " 재생해 보고 이상한 곳을 리포트해 주세요.", "막힘" if 못 else "결정 필요")
    return {"결과": "씀", "파일": 상대(a, p), "실패": 못, "새관통": 새}


def 생성요청(a, 이름, 프리셋들: list[str]) -> dict:
    """에이전트 `동작생성요청`: TRIPO 동작(retarget) 승인 요청. 8단계를 TRIPO로 리깅한 작업 번호가 있어야 한다."""
    if not 프리셋들 or len(프리셋들) > 5 or not all(프리셋.match(x) for x in 프리셋들):
        raise 요청오류(400, "동작 프리셋을 1~5개 주세요(예: walk,run). tripo-cli는 한 번에 5개까지, 동작마다 크레딧.")
    실행 = 서버.생성단계.마지막실행(a, 이름, 8)
    번호들 = ((실행 or {}).get("결과") or {}).get("작업번호") or []
    if not 실행 or 실행.get("실행") != "실행됨" or not 번호들:
        raise 요청오류(409, "8단계 오토 리깅을 TRIPO로 실행한 작업 번호가 없습니다(tripo anim retarget은 리깅 작업에만 됨).")
    작업 = str(번호들[-1])
    명령 = "tripo anim retarget " + shlex.quote(작업) + " --animation " + " ".join(
        shlex.quote(x if x.startswith("preset:") else "preset:" + x) for x in 프리셋들) + " --out-format glb"
    무엇 = f"TRIPO 동작 생성(retarget {len(프리셋들)}개) — 해 본 적 없음, 값·가격 확인"
    r = 서버.승인.요청만들기(a, 이름, 애니, 무엇, 명령, "모름", len(프리셋들), 만든곳="에이전트 동작생성요청")
    return dict(r, 무엇=무엇, 명령=명령, 크레딧="모름", 횟수=len(프리셋들),
                근거="tripo-cli 0.11.2 안내: retarget은 rig 작업 번호만 받음, 동작마다 크레딧. 가격은 안내에 없어 '모름'")


def 처리쪽검사(결과: list) -> None:
    """10단계 처리 결과 줄마다 '쪽'(동작 / 리깅)이 있어야 한다(2부 22절 리포트)."""
    for r in 결과:
        if r.get("쪽") not in ("동작", "리깅"):
            raise 요청오류(400, f"{r.get('번호')}: 10단계 처리 결과에는 '쪽'(동작 / 리깅)이 있어야 합니다(리깅이면 9단계로 넘어감).")


def 넘어온리포트(a, 이름) -> list[dict]:
    """9단계에 보일 '10단계에서 넘어온 리포트': 10단계 처리 결과에서 쪽이 리깅인 줄과 그 표시."""
    d = 폴더(a, 이름, 애니)
    if not d.is_dir():
        return []
    묶음 = {q.name: v for q, v in a.묶음들(이름, 애니)}
    나옴 = []
    for q in sorted(d.glob("처리_*.json")):
        v = 읽기(q) or {}
        표시 = {x.get("번호"): x for x in (묶음.get(v.get("묶음")) or {}).get("표시") or [] if isinstance(x, dict)}
        for r in v.get("결과") or []:
            if isinstance(r, dict) and r.get("쪽") == "리깅":
                x = 표시.get(r.get("번호")) or {}
                나옴.append({"묶음": v.get("묶음"), "번호": r.get("번호"), "처리": r.get("처리"), "이유": r.get("이유") or r.get("메모") or "",
                           "종류": x.get("종류") or "", "메모": x.get("메모") or "", "동작": (x.get("자리") or {}).get("동작"), "시각": v.get("만든시각")})
    return 나옴[-20:]


# ---------------------------------------------------------------- 11단계: Unity 프로젝트·요청·검사표

def 유니티(a, 이름) -> dict:
    u = 상태값(a, 이름).get("Unity")
    값 = {"경로": "", "넣을이름": "", "버전": "", "SSOT버전": SSOT유니티, "방식": 가져오기방식, "넣을곳": 넣을곳,
         "있음": False, "버전같음": False, "열림": False, "같은이름": [], "잠김": ""}
    if not isinstance(u, dict) or not u.get("경로"):
        return dict(값, 잠김="Unity 프로젝트 경로가 없습니다 — '경로 고르기'")
    값.update(경로=str(u["경로"]), 넣을이름=str(u.get("넣을이름") or ""))
    p = Path(값["경로"])
    v = p / "ProjectSettings" / "ProjectVersion.txt"
    if not p.is_dir() or not v.is_file():
        return dict(값, 잠김="그 경로에 Unity 프로젝트가 없습니다(ProjectSettings/ProjectVersion.txt 없음)")
    m = re.search(r"m_EditorVersion:\s*(\S+)", v.read_text(encoding="utf-8", errors="replace"))
    값.update(있음=True, 버전=m.group(1) if m else "모름")
    값["버전같음"] = 값["버전"] == SSOT유니티
    값["열림"] = (p / "Temp" / "UnityLockfile").exists()
    if 값["넣을이름"]:
        곳 = p / 넣을곳
        값["같은이름"] = sorted(f"{넣을곳}/{x.name}" for x in 곳.glob(f"{값['넣을이름']}.*") if x.suffix != ".meta") if 곳.is_dir() else []
    if not 값["버전같음"]:
        값["잠김"] = f"Unity 버전이 다릅니다({값['버전']} ≠ SSOT {SSOT유니티})"
    elif not 값["넣을이름"]:
        값["잠김"] = "Unity에 넣을 이름이 없습니다"
    return 값


def 경로정하기(a, 이름, 몸: dict) -> dict:
    """페이지 '경로 고르기': 상태.json의 "Unity"에 저장(처음 한 번, 2부 23절). Unity 프로젝트에는 쓰지 않는다."""
    a._주인확인(몸.get("탭"), 이름)
    s, n = str(몸.get("경로") or "").strip().strip('"'), str(몸.get("넣을이름") or "").strip()
    if not s or not Path(s).is_absolute():
        raise 요청오류(400, "Unity 프로젝트 폴더의 전체 경로를 적어 주세요(예: C:\\Users\\…\\MyGame).")
    if not (Path(s) / "ProjectSettings" / "ProjectVersion.txt").is_file():
        raise 요청오류(409, "그 폴더에 Unity 프로젝트가 없습니다(ProjectSettings/ProjectVersion.txt가 없음).")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,40}", n):
        raise 요청오류(400, "Unity에 넣을 이름은 영어 글자로 시작하는 영어·숫자·_ (41자까지)로 적어 주세요(예: OnsenGirl).")
    상태에쓰기(a, 이름, "Unity", {"경로": str(Path(s)), "넣을이름": n, "정한시각": 서버.지금()})
    서버.기록(f"11단계 Unity 경로 정함: {s} ({n})", a, 이름)
    return {"됨": True, "Unity": 유니티(a, 이름)}


def 옮긴동작(a, 이름) -> list[str]:
    v = 읽기(폴더(a, 이름, 애니) / "옮김.json") or {}
    return [x["이름"] for x in v.get("동작") or [] if isinstance(x, dict) and x.get("성공") and x.get("이름")]


def 내보내기요청(a, 이름, 몸: dict) -> dict:
    """페이지 '내보내기': 요청 파일을 남긴다. 같은 이름이 Unity에 있으면 덮어쓰기를 물어야 한다(덮어쓰기 전 사본은 에이전트)."""
    a._주인확인(몸.get("탭"), 이름)
    u = 유니티(a, 이름)
    if u["잠김"]:
        raise 요청오류(409, f"내보내기 잠김: {u['잠김']}")
    동작 = 옮긴동작(a, 이름)
    if not 동작:
        raise 요청오류(409, "옮긴 동작이 없습니다(10단계 '옮기기' 뒤 에이전트 기록이 있어야 함).")
    덮 = bool(몸.get("덮어쓰기"))
    if u["같은이름"] and not 덮:
        raise 요청오류(409, f"같은 이름의 파일이 Unity에 이미 있습니다: {', '.join(u['같은이름'][:4])}. 덮어쓸까요?(덮어쓰기 전 사본을 남김)")
    p = 쓰기(a, 이름, 내보, f"요청_{서버.지금(파일용=True)}.json",
           {"Unity경로": u["경로"], "넣을이름": u["넣을이름"], "넣을곳": 넣을곳, "버전": u["버전"], "방식": 가져오기방식, "동작": 동작,
            "덮어쓰기": 덮, "덮을파일": u["같은이름"] if 덮 else [], "덮기전사본": bool(u["같은이름"]), "Unity열림": u["열림"], "누가": "사용자"})
    서버.기록(f"11단계 내보내기 요청: {u['넣을이름']} → {u['경로']} (동작 {len(동작)}, 덮어쓰기 {덮})", a, 이름)
    a.알림쓰기(이름, 내보, f"내보내기 요청을 남겼습니다(동작 {len(동작)}개{', 덮어쓰기 — 사본을 먼저 남김' if 덮 else ''}). Claude 앱에서 '11단계 내보내기 해 줘'라고 알려 주세요."
              + (" Unity가 열려 있어 창 없는 실행이 막힐 수 있습니다. 닫고 알려 주면 좋습니다." if u["열림"] else ""), "안내")
    return {"됨": True, "파일": 상대(a, p)}


def 마지막요청(a, 이름) -> dict | None:
    d = 폴더(a, 이름, 내보)
    q = sorted(d.glob("요청_*.json")) if d.is_dir() else []
    return dict(읽기(q[-1]) or {}, 파일=q[-1].name) if q else None


def 검사표쓰기(a, 이름, v: dict) -> dict:
    """에이전트 `내보내기결과`: {요청파일, 파일: [{경로, 종류}], 검사: [{항목, 상태, 글}], 표시: {7-5, 7-6, 7-7}, 그림: [...], 사본?: 글}."""
    if not isinstance(v, dict):
        raise 요청오류(400, "검사표 파일은 JSON 객체여야 합니다.")
    r = 마지막요청(a, 이름)
    if not r or v.get("요청파일") != r["파일"]:
        raise 요청오류(409, f"'요청파일'이 가장 최근 내보내기 요청({r['파일'] if r else '없음'})과 다릅니다.")
    파일들, 검사, 표시 = v.get("파일"), v.get("검사"), v.get("표시")
    if not isinstance(파일들, list) or not all(isinstance(x, dict) and isinstance(x.get("경로"), str) and x.get("종류") in ("FBX", "텍스처", "클립", "기타") for x in 파일들):
        raise 요청오류(400, "'파일'은 [{경로, 종류(FBX·텍스처·클립·기타)}] 목록.")
    if not isinstance(검사, list) or not 검사 or not all(isinstance(x, dict) and isinstance(x.get("항목"), str) and x.get("상태") in 검사상태 for x in 검사):
        raise 요청오류(400, f"'검사'는 [{{항목, 상태({'·'.join(검사상태)}), 글}}] 목록.")
    if not isinstance(표시, dict) or set(표시) != set(표시들) or not all(isinstance(표시[k], bool) for k in 표시들):
        raise 요청오류(400, "'표시'는 {\"7-5\": 참/거짓, \"7-6\": …, \"7-7\": …}(SSOT 7_Unity 끝났다는 표시).")
    그림 = v.get("그림", [])
    if not isinstance(그림, list) or not all(isinstance(g, str) and a.저장소파일(g) for g in 그림):
        raise 요청오류(400, "'그림'은 저장소 안의 그림 경로 목록(Play 모드 찍은 것·GIF).")
    if r.get("덮어쓰기") and r.get("덮을파일") and not str(v.get("사본") or "").strip():
        raise 요청오류(400, "덮어쓴 요청이면 '사본'(덮어쓰기 전 사본을 둔 곳)을 적어야 합니다.")
    p = 쓰기(a, 이름, 내보, "검사표.json", {"요청파일": r["파일"], "파일": 파일들, "검사": [dict(x, 글=str(x.get("글") or "")[:300]) for x in 검사],
                                       "표시": 표시, "그림": 그림, "사본": str(v.get("사본") or "")[:400]})
    실패 = sum(1 for x in 검사 if x["상태"] == "실패")
    서버.기록(f"11단계 검사표: 실패 {실패}, 표시 {표시}", a, 이름)
    a.알림쓰기(이름, 내보, f"Unity로 내보냈습니다. 검사표{f' 실패 {실패}개' if 실패 else ''}와 Play 모드 그림을 보고 '봄'을 눌러 주세요.", "막힘" if 실패 else "결정 필요")
    return {"결과": "씀", "파일": 상대(a, p)}


def 봄쓰기(a, 이름, 몸: dict) -> dict:
    a._주인확인(몸.get("탭"), 이름)
    표 = 읽기(폴더(a, 이름, 내보) / "검사표.json")
    if not 표 or not 표.get("그림"):
        raise 요청오류(409, "볼 Play 모드 그림이 없습니다.")
    p = 쓰기(a, 이름, 내보, "봄.json", {"검사표시각": 표.get("만든시각"), "누가": "사용자"})
    return {"됨": True, "파일": 상대(a, p)}


# ---------------------------------------------------------------- 끝나는 조건(2부 22·23절)

def 완료모자람(a, 이름, 번호) -> list[str]:
    모자람 = []
    안된 = [q.name for q, v in a.묶음들(이름, 번호) if v.get("묶음상태") in ("보냄", "처리 중")]
    if 안된:
        모자람.append(f"처리 안 된 묶음 {len(안된)}개")
    지금해시 = a._지금작업본해시(이름)
    if 번호 == 애니:
        고른 = 고른것(a, 이름)
        if not 고른:
            모자람.append("고른 동작이 없음")
        v = 읽기(폴더(a, 이름, 애니) / "옮김.json")
        if not v:
            모자람.append("옮긴 기록이 없음 — '옮기기' 뒤 에이전트 '동작옮김'")
            return 모자람
        if v.get("작업본해시") != 지금해시:
            모자람.append("옮긴 기록이 지금 작업본보다 오래됨 — 다시 재야 함")
        됨 = {x.get("원본"): x for x in v.get("동작") or [] if isinstance(x, dict)}
        빠짐 = [n for n in 고른 if not (됨.get(n) or {}).get("성공")]
        if 빠짐:
            모자람.append(f"고른 동작 중 옮기기 성공이 아닌 것 {len(빠짐)}개({', '.join(빠짐[:3])})")
        return 모자람
    u = 유니티(a, 이름)
    if u["잠김"]:
        모자람.append(u["잠김"])
    표 = 읽기(폴더(a, 이름, 내보) / "검사표.json")
    if not 표:
        모자람.append("검사표가 없음 — '내보내기' 뒤 에이전트 '내보내기결과'")
        return 모자람
    if 표.get("작업본해시") != 지금해시:
        모자람.append("검사표가 지금 작업본보다 오래됨 — 다시 내보내야 함")
    빠진표시 = [k for k in 표시들 if not (표.get("표시") or {}).get(k)]
    if 빠진표시:
        모자람.append(f"7_Unity {', '.join(빠진표시)}의 끝났다는 표시가 없음")
    실패 = [x.get("항목") for x in 표.get("검사") or [] if x.get("상태") == "실패"]
    if 실패:
        모자람.append(f"검사표 실패 {len(실패)}개({', '.join(map(str, 실패[:3]))})")
    봄 = 읽기(폴더(a, 이름, 내보) / "봄.json")
    if not 봄 or 봄.get("검사표시각") != 표.get("만든시각"):
        모자람.append("Play 모드 그림을 사용자가 봄 표시가 없음")
    return 모자람


# ---------------------------------------------------------------- 화면

def 보기(a, 이름, 번호, 미리시작: bool = True) -> dict:
    if 번호 not in 단계들:
        raise 요청오류(400, "10·11단계만 있습니다.")
    값 = {"단계": 번호, "모자람": 완료모자람(a, 이름, 번호), "가짜모드": 서버.승인.모드 != "진짜"}
    if 번호 == 애니:
        모 = 모음(a, 이름)
        설정 = 리깅설정(a, 이름)
        옮 = 읽기(폴더(a, 이름, 애니) / "옮김.json")
        값.update({"모음": {k: 모.get(k) for k in ("이름", "동작", "오류")}, "자동처리": 자동처리(설정), "보폭": 설정.get("보폭"),
                  "고른": 고른것(a, 이름), "옮기기요청": 마지막옮기기요청(a, 이름), "옮김": 옮,
                  "옮김옛것": bool(옮 and 옮.get("작업본해시") != a._지금작업본해시(이름)),
                  "미리": 미리상태(a, 이름, 시작=미리시작 and not 모["오류"].startswith("상태.json")),
                  "생성실행": 서버.생성단계.마지막실행(a, 이름, 애니)})
        return 값
    표 = 읽기(폴더(a, 이름, 내보) / "검사표.json")
    봄 = 읽기(폴더(a, 이름, 내보) / "봄.json")
    값.update({"Unity": 유니티(a, 이름), "동작": 옮긴동작(a, 이름), "요청": 마지막요청(a, 이름), "검사표": 표,
              "검사표옛것": bool(표 and 표.get("작업본해시") != a._지금작업본해시(이름)),
              "봄": bool(봄 and 표 and 봄.get("검사표시각") == 표.get("만든시각"))})
    return 값


def 바뀜(a, 이름, 번호) -> str:
    try:
        d = 폴더(a, 이름, 번호)
    except Exception:
        return ""
    조각 = []
    for p in [d / "고른동작.json", d / "옮김.json", d / "검사표.json", d / "봄.json"] + list(d.glob("*요청_*.json")) + list(d.glob("승인_*.json")) + list(d.glob("보내기_*.json")):
        try:
            조각.append(f"{p.name}:{p.stat().st_mtime_ns}")
        except OSError:
            pass
    if 번호 == 애니:
        h = a._지금작업본해시(이름)
        일 = _일들.get(f"{이름}/{h}") if h else None
        if 일:
            조각.append(f"미리:{일.get('상태')}:{일.get('걸음')}:{일.get('끈것')}:{일.get('켠것')}")
    return "|".join(sorted(조각))
