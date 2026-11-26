# -*- coding: utf-8 -*-
"""4방향 시트 한 장을 TRIPO 입력용 네 장으로 자른다(재생성·리사이즈 없이).

쓰는 법(저장소 루트에서):
    PYTHONIOENCODING=utf-8 python SSOT/도구/시트_자르기.py <시트.png> <출력 폴더>

- 배경색은 네 모서리의 중앙값으로 정한다. 세로 한 줄 전체가 배경색이면 빈 간격으로 본다.
- 캐릭터가 차지한 구간이 정확히 네 개일 때만 자른다. 아니면 종료 코드 1로 멈춘다.
- 자르는 경계는 이웃한 두 캐릭터 사이 빈 간격의 가운데다. 위아래는 자르지 않는다.
- 결과: 01_front.png, 02_profile_facing_left.png, 03_back.png, 04_profile_facing_right.png,
  자르기기록.json(시트와 결과의 SHA256, 자른 영역, 캐릭터 구간).
- 순서는 시트의 왼쪽부터 정면, 캐릭터의 왼쪽 면, 후면, 캐릭터의 오른쪽 면이라는 요청문의 배치를 따른다.
  그림이 그 순서로 그려졌는지는 사람이(에이전트가) 그림을 열어 확인한다.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

이름들 = ["01_front.png", "02_profile_facing_left.png", "03_back.png", "04_profile_facing_right.png"]
색차_문턱 = 30      # 배경과 이 값보다 다르면 캐릭터로 본다(RGB 차이의 합)
최소_간격 = 8       # 이보다 좁은 빈 틈은 캐릭터 안의 틈으로 보고 합친다(픽셀)
최소_폭 = 40        # 이보다 좁은 구간은 잡티로 보고 버린다(픽셀)


def 해시(경로):
    return hashlib.sha256(Path(경로).read_bytes()).hexdigest()


def main():
    if len(sys.argv) != 3:
        raise SystemExit("쓰는 법: python SSOT/도구/시트_자르기.py <시트.png> <출력 폴더>")
    시트, 출력 = Path(sys.argv[1]), Path(sys.argv[2])
    im = Image.open(시트)
    a = np.asarray(im.convert("RGB")).astype(int)
    h, w, _ = a.shape
    모서리 = np.array([a[2, 2], a[2, w - 3], a[h - 3, 2], a[h - 3, w - 3]])
    배경 = np.median(모서리, axis=0)
    전경 = np.abs(a - 배경).sum(axis=2) > 색차_문턱
    열 = 전경.any(axis=0)

    구간 = []
    x = 0
    while x < w:
        if 열[x]:
            s = x
            while x < w and 열[x]:
                x += 1
            구간.append([s, x])
        else:
            x += 1
    합친 = []
    for s, e in 구간:
        if 합친 and s - 합친[-1][1] < 최소_간격:
            합친[-1][1] = e
        else:
            합친.append([s, e])
    합친 = [g for g in 합친 if g[1] - g[0] >= 최소_폭]
    print(f"시트 {w}x{h}, 배경 {배경.tolist()}, 캐릭터 구간 {합친}")
    if len(합친) != 4:
        print(f"오류: 캐릭터 구간이 {len(합친)}개다(4개여야 한다). 자르지 않았다.")
        raise SystemExit(1)

    경계 = [0] + [(합친[i][1] + 합친[i + 1][0]) // 2 for i in range(3)] + [w]
    출력.mkdir(parents=True, exist_ok=True)
    기록 = {"sheet": str(시트), "sheet_sha256": 해시(시트), "sheet_size": [w, h],
          "background": 배경.tolist(), "figure_columns": 합친, "crops": []}
    for i, 이름 in enumerate(이름들):
        상자 = (경계[i], 0, 경계[i + 1], h)
        경로 = 출력 / 이름
        im.crop(상자).save(경로)
        기록["crops"].append({"file": 이름, "box": list(상자), "sha256": 해시(경로)})
        print(f"{이름}: 상자 {상자}")
    (출력 / "자르기기록.json").write_text(json.dumps(기록, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("자르기 완료 4장")


if __name__ == "__main__":
    main()
