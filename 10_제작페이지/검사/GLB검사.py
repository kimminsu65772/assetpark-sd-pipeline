"""GLB 되읽기 검사 (작업 묶음 W01 완료 조건)

실행(창 없이, 저장소 루트에서, Git Bash):
    SSOT/도구/블렌더실행.sh <작업본.blend> 10_제작페이지/검사/GLB검사.py -- <GLB> [--표본 50] [--씨앗 N] [--자가시험]

보는 것(파츠마다):
1. GLB의 같은 이름 메시가 있다.
2. 삼각형마다 세 정점의 `_FACEID`가 같다(면 번호가 정점 공유로 섞이지 않음).
3. 면 번호 0..면수-1이 모두 나오고 그 밖의 값이 없다. 면마다 삼각형 수 = 꼭짓점 수 - 2.
4. 임의 면 50개: 그 면 번호의 삼각형들의 UV(TEXCOORD_0, v를 1-v로 되돌림)와 위치(Y-up을 되돌림)가
   작업본 그 면의 첫 번째 UV 층·꼭짓점 위치와 같다(오차 1e-4).
`--자가시험`: GLB 값을 일부러 망가뜨린 세 경우(면 번호 하나 바꿈, UV 하나 밀기, 면 하나 빼기)를 잡는지 본다.
위반이 있으면 종료 코드 1.
"""

import json
import random
import struct
import sys

import bpy
import numpy as np

오차 = 1e-4
종류 = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
칸수 = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def 인자():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not a:
        raise SystemExit("인자: -- <GLB> [--표본 50] [--씨앗 N] [--자가시험]")
    값 = {"glb": a[0], "표본": 50, "씨앗": None, "자가시험": "--자가시험" in a}
    if "--표본" in a:
        값["표본"] = int(a[a.index("--표본") + 1])
    if "--씨앗" in a:
        값["씨앗"] = int(a[a.index("--씨앗") + 1])
    return 값


def glb읽기(p):
    b = open(p, "rb").read()
    if b[:4] != b"glTF":
        raise SystemExit("GLB 머리가 아닙니다.")
    n = struct.unpack_from("<I", b, 12)[0]
    j = json.loads(b[20:20 + n].decode("utf-8"))
    bin시작 = 20 + n + 8
    return j, b[bin시작:]


def 접근(j, 바이너리, i):
    ac = j["accessors"][i]
    bv = j["bufferViews"][ac["bufferView"]]
    dt = 종류[ac["componentType"]]
    k = 칸수[ac["type"]]
    시작 = bv.get("byteOffset", 0) + ac.get("byteOffset", 0)
    보폭 = bv.get("byteStride")
    크기 = np.dtype(dt).itemsize * k
    if 보폭 and 보폭 != 크기:
        raw = np.frombuffer(바이너리, np.uint8, count=보폭 * ac["count"], offset=시작).reshape(ac["count"], 보폭)
        a = raw[:, :크기].copy().view(dt).reshape(ac["count"], k)
    else:
        a = np.frombuffer(바이너리, dt, count=ac["count"] * k, offset=시작).reshape(ac["count"], k)
    return a.astype(np.float64) if dt == np.float32 else a.astype(np.int64)


def 파츠자료(j, 바이너리):
    """메시 이름 → 삼각형 목록 {id[T], uv[T,3,2], pos[T,3,3]} (프리미티브를 합침)."""
    결과 = {}
    for m in j["meshes"]:
        ids, uvs, ps, 섞임 = [], [], [], 0
        for p in m["primitives"]:
            if p.get("mode", 4) != 4:
                raise SystemExit(f"{m['name']}: 삼각형이 아닌 프리미티브")
            at = p["attributes"]
            if "_FACEID" not in at or "TEXCOORD_0" not in at:
                결과[m["name"]] = None
                break
            fid = 접근(j, 바이너리, at["_FACEID"])[:, 0]
            uv = 접근(j, 바이너리, at["TEXCOORD_0"])
            pos = 접근(j, 바이너리, at["POSITION"])
            idx = 접근(j, 바이너리, p["indices"])[:, 0] if "indices" in p else np.arange(len(fid))
            t = idx.reshape(-1, 3)
            f3 = fid[t]
            섞임 += int(np.count_nonzero((f3[:, 0] != f3[:, 1]) | (f3[:, 0] != f3[:, 2])))
            ids.append(f3[:, 0])
            uvs.append(uv[t])
            ps.append(pos[t])
        else:
            결과[m["name"]] = {"id": np.concatenate(ids), "uv": np.concatenate(uvs), "pos": np.concatenate(ps), "섞임": 섞임}
    return 결과


def 점집합같음(a, b):
    """두 점 목록이 순서와 중복 없이 같은 점들인가(오차 안)."""
    a = np.unique(np.round(np.asarray(a), 5), axis=0)
    b = np.unique(np.round(np.asarray(b), 5), axis=0)
    if len(a) != len(b):
        return False
    for x in a:
        if np.min(np.max(np.abs(b - x), axis=1)) > 오차:
            return False
    return True


def 검사(자료, 표본, rnd):
    위반 = []
    줄 = []
    for o in sorted((o for o in bpy.data.objects if o.type == "MESH"), key=lambda o: o.name):
        if o.name not in 자료:
            continue
        d = 자료[o.name]
        me = o.data
        if d is None:
            위반.append(f"{o.name}: _FACEID 또는 TEXCOORD_0 없음")
            continue
        if d["섞임"]:
            위반.append(f"{o.name}: 세 정점의 면 번호가 다른 삼각형 {d['섞임']}개")
        ids = np.rint(d["id"]).astype(np.int64)
        if np.any(np.abs(d["id"] - ids) > 1e-6):
            위반.append(f"{o.name}: 정수가 아닌 면 번호")
        n = len(me.polygons)
        세기 = np.bincount(ids[(ids >= 0) & (ids < n)], minlength=n)
        밖 = int(np.count_nonzero((ids < 0) | (ids >= n)))
        기대 = np.array([len(p.vertices) - 2 for p in me.polygons])
        빠짐 = int(np.count_nonzero(세기 == 0))
        틀림 = int(np.count_nonzero(세기 != 기대))
        if 밖 or 빠짐 or 틀림:
            위반.append(f"{o.name}: 면 번호 범위 밖 {밖}, 빠진 면 {빠짐}, 삼각형 수가 다른 면 {틀림}")
        uv층 = me.uv_layers[0] if me.uv_layers else None
        고른 = sorted(rnd.sample(range(n), min(표본, n)))
        uv틀림, 위치틀림 = [], []
        for f in 고른:
            p = me.polygons[f]
            t = np.nonzero(ids == f)[0]
            if not len(t):
                uv틀림.append(f)
                continue
            if uv층:
                작업본uv = [(uv층.data[li].uv[0], 1.0 - uv층.data[li].uv[1]) for li in p.loop_indices]
                if not 점집합같음(작업본uv, d["uv"][t].reshape(-1, 2)):
                    uv틀림.append(f)
            작업본위치 = [(me.vertices[v].co.x, me.vertices[v].co.z, -me.vertices[v].co.y) for v in p.vertices]
            if not 점집합같음(작업본위치, d["pos"][t].reshape(-1, 3)):
                위치틀림.append(f)
        if uv틀림:
            위반.append(f"{o.name}: UV가 다른 면 {len(uv틀림)}개 {uv틀림[:10]}")
        if 위치틀림:
            위반.append(f"{o.name}: 위치가 다른 면 {len(위치틀림)}개 {위치틀림[:10]}")
        줄.append(f"{o.name}: 면 {n}, GLB 삼각형 {len(ids)}, 표본 {len(고른)}개(처음 5개 {고른[:5]}) "
                 f"UV 다름 {len(uv틀림)}, 위치 다름 {len(위치틀림)}")
    빠진파츠 = [k for k in 자료 if k not in bpy.data.objects]
    if 빠진파츠:
        위반.append(f"작업본에 없는 GLB 메시: {빠진파츠}")
    if not 줄 and not 위반:
        위반.append("검사한 파츠가 0개")
    return 위반, 줄


def main():
    a = 인자()
    j, 바이너리 = glb읽기(a["glb"])
    씨앗 = a["씨앗"] if a["씨앗"] is not None else random.SystemRandom().randrange(1 << 30)
    자료 = 파츠자료(j, 바이너리)
    # GLB 노드 이름 → 메시: 메시 이름이 객체 이름과 다를 수 있어 노드 이름으로 다시 묶는다
    노드별 = {}
    for nd in j["nodes"]:
        if "mesh" in nd:
            노드별[nd.get("name")] = 자료[j["meshes"][nd["mesh"]]["name"]]
    print(f"씨앗 {씨앗}, 표본 {a['표본']}, GLB 메시 {len(노드별)}개")
    위반, 줄 = 검사(노드별, a["표본"], random.Random(씨앗))
    for s in 줄:
        print("  " + s)
    if a["자가시험"]:
        잡음 = []
        첫 = sorted(노드별)[0]
        for 이름, 망치기 in [
            ("면 번호 하나 바꿈", lambda d: d["id"].__setitem__(0, (d["id"][0] + 1) % max(1, int(d["id"].max())))),
            ("UV 하나 밀기", lambda d: d["uv"].__setitem__((slice(None), 0, 0), d["uv"][:, 0, 0] + 0.01)),
            ("면 하나 빼기", lambda d: d.update(id=d["id"][1:], uv=d["uv"][1:], pos=d["pos"][1:])),
        ]:
            시험 = {k: dict(v, id=v["id"].copy(), uv=v["uv"].copy(), pos=v["pos"].copy()) for k, v in 노드별.items()}
            망치기(시험[첫])
            w, _ = 검사(시험, 10 ** 9, random.Random(씨앗))  # 망친 자리를 놓치지 않게 모든 면
            잡음.append((이름, bool(w)))
        for 이름, 됨 in 잡음:
            print(f"  자가시험 {이름}: {'잡음' if 됨 else '못 잡음'}")
        if not all(됨 for _, 됨 in 잡음):
            위반.append("자가시험에서 못 잡은 경우가 있음")
    if 위반:
        print("위반:")
        for w in 위반:
            print("  " + w)
        sys.exit(1)
    print("위반 0")


main()
