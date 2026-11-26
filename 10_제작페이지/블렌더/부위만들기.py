"""작업본(blend) → 부위 목록 (작업 묶음 W05, 기능명세 1부 5-2b·2-1 "부위.json")

실행(창 없이, 저장소 루트에서, Git Bash). 보통은 `10_제작페이지/부위만들기.py`가 부른다:
    SSOT/도구/블렌더실행.sh <작업본.blend> 10_제작페이지/블렌더/부위만들기.py -- <출력.json>

하는 일(작업본은 읽기만, 저장하지 않음):
1. 파츠 = GLB만들기.py와 같은 것(렌더에 보이는 메시). 면 번호 = 작업본의 면 번호(polygon index, GLB의 _FACEID와 같음).
2. 파츠마다 서로 이어진 덩어리(정점을 함께 쓰는 면)로 나눈다.
3. 큰 덩어리(파츠 면의 30% 이상이고 200면 이상)는 UV 조각(같은 모서리를 같은 UV로 나누는 면 묶음,
   `SSOT/도구/텍스처/조각지도.py`와 같은 기준)으로 더 나눈다. 너무 작은 조각(파츠 면의 3% 미만)은
   모서리를 가장 많이 나누는 이웃 조각에 붙인다. 한 덩어리에서 나온 부위가 6개를 넘으면 작은 것부터 붙인다.
4. 이름: [좌우] + [몸 낱말 또는 자리]. 좌우는 화면을 보는 사람 기준(오른쪽 = +x, 1부 규칙).
   몸 낱말은 뼈 가중치(정점 그룹)가 있고 파츠 안에서 두 가지 넘게 갈릴 때만 쓴다(예: 아래팔, 허벅지).
   없으면 파츠 상자 안의 자리(앞/뒤, 위/아래). 같은 이름이 겹치면 뒤에 2, 3.
출력 JSON: {"부위": [{이름, 파츠, 면, 중심, 자동이름, 근거}], "파츠": [{이름, 면수, 크기(상자 대각선)}], "블렌더"}
"""

import json
import os
import sys
from collections import Counter, defaultdict

import bpy

큰덩어리비 = 0.30
큰덩어리면 = 200
작은조각비 = 0.03
덩어리당최대 = 6
가운데비 = 0.15      # 파츠 폭의 절반 × 이 값 안쪽이면 좌우를 붙이지 않음

뼈낱말 = [  # (뼈 이름에 든 낱말, 몸 낱말) — 앞에 있는 것이 먼저
    ("Thumb", "손"), ("Index", "손"), ("Mid", "손"), ("Ring", "손"), ("Pinky", "손"), ("Hand", "손"),
    ("Forearm", "아래팔"), ("Upperarm", "위팔"), ("Clavicle", "어깨"),
    ("ToeBase", "발끝"), ("Toe", "발끝"), ("Foot", "발"), ("Calf", "종아리"), ("Thigh", "허벅지"),
    ("Head", "머리"), ("Neck", "목"), ("Spine", "몸통"), ("Waist", "허리"), ("Pelvis", "골반"),
]


def 인자():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(a) != 1:
        raise SystemExit("인자: -- <출력.json>")
    return os.path.abspath(a[0])


def 렌더에보임(o) -> bool:
    if o.hide_render:
        return False
    return not any(c.hide_render for c in o.users_collection)


class 묶개:
    def __init__(self, n):
        self.p = list(range(n))

    def 뿌리(self, x):
        p = self.p
        while p[x] != x:
            p[x] = p[p[x]]
            x = p[x]
        return x

    def 잇기(self, a, b):
        a, b = self.뿌리(a), self.뿌리(b)
        if a != b:
            self.p[a] = b


def 몸낱말(뼈이름: str) -> str | None:
    for k, w in 뼈낱말:
        if k.lower() in 뼈이름.lower():
            return w
    return None


def 파츠부위(o):
    me = o.data
    면수 = len(me.polygons)
    wm = o.matrix_world
    중심들 = [wm @ p.center for p in me.polygons]
    # 1) 덩어리: 정점을 함께 쓰는 면
    정점묶음 = 묶개(len(me.vertices))
    for e in me.edges:
        정점묶음.잇기(e.vertices[0], e.vertices[1])
    덩어리 = defaultdict(list)
    for p in me.polygons:
        덩어리[정점묶음.뿌리(p.vertices[0])].append(p.index)
    # 2) UV 조각과 면 이웃(모서리)
    uv = me.uv_layers[0].data if me.uv_layers else None
    조각묶음 = 묶개(면수)
    모서리 = {}
    이웃 = defaultdict(Counter)
    for p in me.polygons:
        ls = list(p.loop_indices)
        for k in range(len(ls)):
            l0, l1 = ls[k], ls[(k + 1) % len(ls)]
            v0, v1 = me.loops[l0].vertex_index, me.loops[l1].vertex_index
            열쇠 = (min(v0, v1), max(v0, v1))
            표 = {v0: tuple(round(c, 6) for c in uv[l0].uv), v1: tuple(round(c, 6) for c in uv[l1].uv)} if uv else None
            if 열쇠 in 모서리:
                q, 표2 = 모서리[열쇠]
                이웃[p.index][q] += 1
                이웃[q][p.index] += 1
                if 표 == 표2:
                    조각묶음.잇기(p.index, q)
            else:
                모서리[열쇠] = (p.index, 표)
    # 3) 뼈 가중치 → 면마다 몸 낱말
    면낱말 = [None] * 면수
    if o.vertex_groups:
        그룹이름 = {g.index: g.name for g in o.vertex_groups}
        정점낱말 = []
        for v in me.vertices:
            합 = Counter()
            for g in v.groups:
                w = 몸낱말(그룹이름.get(g.group, ""))
                if w:
                    합[w] += g.weight
            정점낱말.append(합)
        for p in me.polygons:
            합 = Counter()
            for vi in p.vertices:
                합.update(정점낱말[vi])
            면낱말[p.index] = 합.most_common(1)[0][0] if 합 else None
    낱말세기 = Counter(w for w in 면낱말 if w)
    # 몸 낱말은 파츠 안에서 갈릴 때만(한 낱말이 80% 넘게 차지하면 — 예: 얼굴은 거의 "머리" — 자리로 이름)
    낱말쓰기 = len(낱말세기) >= 2 and 낱말세기.most_common(1)[0][1] < 0.8 * 면수

    부위들 = []
    for 면목록 in 덩어리.values():
        조각 = defaultdict(list)
        if len(면목록) >= 큰덩어리비 * 면수 and len(면목록) >= 큰덩어리면:
            for f in 면목록:
                조각[조각묶음.뿌리(f)].append(f)
        else:
            조각[면목록[0]] = list(면목록)
        조각 = {k: set(v) for k, v in 조각.items()}
        소속 = {f: k for k, v in 조각.items() for f in v}

        def 붙이기(작은):
            세기 = Counter()
            for f in 조각[작은]:
                for q, n in 이웃[f].items():
                    k = 소속.get(q)
                    if k is not None and k != 작은:
                        세기[k] += n
            if not 세기:
                return False
            큰 = 세기.most_common(1)[0][0]
            for f in 조각[작은]:
                소속[f] = 큰
            조각[큰] |= 조각.pop(작은)
            return True

        while len(조각) > 1:
            작은 = min(조각, key=lambda k: len(조각[k]))
            if len(조각[작은]) >= 작은조각비 * 면수 and len(조각) <= 덩어리당최대:
                break
            if not 붙이기(작은):
                break
        for v in 조각.values():
            부위들.append(sorted(v))

    # 4) 이름
    xs = [c.x for c in 중심들]; ys = [c.y for c in 중심들]; zs = [c.z for c in 중심들]
    가운데x = (min(xs) + max(xs)) / 2
    반폭 = max(1e-6, (max(xs) - min(xs)) / 2)
    y0, y1, z0, z1 = min(ys), max(ys), min(zs), max(zs)
    결과 = []
    for 면목록 in 부위들:
        n = len(면목록)
        cx = sum(중심들[f].x for f in 면목록) / n
        cy = sum(중심들[f].y for f in 면목록) / n
        cz = sum(중심들[f].z for f in 면목록) / n
        dx = (cx - 가운데x) / 반폭
        좌우 = "" if abs(dx) < 가운데비 else ("오른쪽" if dx > 0 else "왼쪽")
        낱말 = None
        if 낱말쓰기:
            세기 = Counter(면낱말[f] for f in 면목록 if 면낱말[f])
            낱말 = 세기.most_common(1)[0][0] if 세기 else None
        근거 = "뼈 가중치" if 낱말 else "자리"
        if not 낱말:
            ry = (cy - y0) / max(1e-6, y1 - y0)   # Blender 앞 = -y
            rz = (cz - z0) / max(1e-6, z1 - z0)
            자리 = []
            if rz > 0.66:
                자리.append("위")
            elif rz < 0.33:
                자리.append("아래")
            if ry < 0.4:
                자리.append("앞")
            elif ry > 0.6:
                자리.append("뒤")
            낱말 = " ".join(자리) or "가운데"
        이름 = f"{좌우} {낱말}".strip()
        결과.append({"이름": 이름, "파츠": o.name, "면": 면목록, "중심": [round(cx, 4), round(cy, 4), round(cz, 4)],
                   "근거": 근거})
    # 같은 이름끼리는 서로의 자리(위/아래 또는 앞/뒤, 더 벌어진 쪽)를 붙이고, 그래도 겹치면 2, 3 (면이 많은 것이 먼저)
    무리 = defaultdict(list)
    for r in 결과:
        무리[r["이름"]].append(r)
    for 같은 in 무리.values():
        if len(같은) < 2:
            continue
        zz = [r["중심"][2] for r in 같은]; yy = [r["중심"][1] for r in 같은]
        z축 = max(zz) - min(zz) >= max(yy) - min(yy)
        값 = zz if z축 else yy
        lo, hi = min(값), max(값)
        for r, v in zip(같은, 값):
            t = (v - lo) / max(1e-6, hi - lo)
            if z축:
                붙임 = "위" if t > 0.66 else "아래" if t < 0.33 else "가운데"
            else:
                붙임 = "앞" if t < 0.33 else "뒤" if t > 0.66 else "가운데"   # 앞 = -y
            r["이름"] = f"{r['이름']} {붙임}"
    결과.sort(key=lambda r: (r["이름"], -len(r["면"])))
    세기 = Counter()
    for r in 결과:
        세기[r["이름"]] += 1
        if 세기[r["이름"]] > 1:
            r["이름"] = f"{r['이름']} {세기[r['이름']]}"
        r["자동이름"] = r["이름"]
    결과.sort(key=lambda r: -len(r["면"]))
    return 결과


def main():
    출력 = 인자()
    파츠 = sorted((o for o in bpy.data.objects if o.type == "MESH" and 렌더에보임(o)), key=lambda o: o.name)
    if not 파츠:
        raise SystemExit("부위를 만들 메시 객체가 없습니다(렌더에 보이는 메시 0개).")
    부위 = []
    for o in 파츠:
        부위 += 파츠부위(o)
    def 크기(o):
        cs = [o.matrix_world @ v.co for v in o.data.vertices] or [o.location]
        return round(sum((max(c[i] for c in cs) - min(c[i] for c in cs)) ** 2 for i in range(3)) ** 0.5, 4)
    값 = {"부위": 부위, "파츠": [{"이름": o.name, "면수": len(o.data.polygons), "크기": 크기(o)} for o in 파츠],
          "블렌더": bpy.app.version_string}
    os.makedirs(os.path.dirname(출력), exist_ok=True)
    with open(출력, "w", encoding="utf-8") as f:
        json.dump(값, f, ensure_ascii=False)
    for o in 파츠:
        줄 = [f"{r['이름']}({len(r['면'])})" for r in 부위 if r["파츠"] == o.name]
        print(f"{o.name}: {len(줄)}개 — " + ", ".join(줄))
    print(f"부위 {len(부위)}개")


main()
