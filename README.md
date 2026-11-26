# AssetPark

SD 캐릭터 3D 에셋을 그림 → TRIPO 모델 → 메시 정리 → UV·텍스처 → 리깅 → Unity까지 만드는 동안, 사람이 화면에서 고칠 곳을 칠해 AI 에이전트(Claude Code)에게 보내고 결과를 확인하는 로컬 웹 페이지입니다.

- 서버는 이 PC(`127.0.0.1`)에서만 열립니다. 페이지는 바깥 주소로 요청하지 않습니다.
- 유료 TRIPO 실행은 기본이 **가짜 실행**입니다. 진짜 실행은 서버를 `--진짜실행`으로 켠 뒤 화면의 승인 상자에서 승인할 때만 하고, 승인 한 번에 한 번만 실행합니다.

## 필요한 것

| 무엇 | 왜 | 확인한 판 |
| --- | --- | --- |
| Windows 10/11 | 켜기 파일(`.bat`)과 경로 처리 | Windows 10 |
| Python 3.12 이상 | 서버(표준 라이브러리만, 따로 설치할 패키지 없음) | 3.12 |
| Blender | 작업본(blend)을 3D 보기용 GLB로 내보내기, 메시·리깅 도구 | 5.3 |
| Git for Windows(Git Bash) | Blender를 부르는 `SSOT/도구/블렌더실행.sh` | — |
| Claude Code | 칠해 보낸 표시를 처리하는 에이전트(스킬 `.claude/skills/jejak-page/`) | — |
| Node.js 20 이상 + tripo-cli 0.11.2 | 진짜 TRIPO 실행만 | 0.11.2 |
| TRIPO API 키 | 진짜 TRIPO 실행만 | — |
| Codex 명령줄 | 1단계 그림을 진짜로 생성할 때만 | — |
| Unity 6000.3.7f1 | 11단계 내보내기만 | 6000.3.7f1 |

## 설치

1. 이 저장소를 받습니다.

   ```powershell
   git clone https://github.com/kimminsu65772/assetpark-sd-pipeline.git AssetPark
   ```

2. Blender가 `C:\Program Files\Blender Foundation\Blender 5.3\blender.exe`가 아니면 사용자 환경 변수 `BLENDER`에 blender.exe의 전체 경로를 적습니다.
3. Git Bash가 `C:\Program Files\Git\bin\bash.exe`가 아니면 사용자 환경 변수 `가마우지_BASH`에 bash.exe 경로를 적습니다(WSL의 bash는 쓰지 않습니다).
4. (진짜 TRIPO 실행을 할 때만) tripo-cli를 이 폴더 안에 설치하고, API 키를 사용자 환경 변수 `TRIPO_API_KEY`에 둡니다. 키는 파일에 적지 않습니다.

   ```powershell
   npm install --no-audit --no-fund --prefix 10_제작페이지/로컬/tripo-cli tripo-cli@0.11.2
   ```

   다른 곳에 설치했다면 환경 변수 `가마우지_TRIPO`에 그 `dist/cli.js` 경로를 적습니다.

## 켜기와 끄기

- `10_제작페이지/제작페이지_켜기.bat`을 두 번 누릅니다. 기본 브라우저에 `http://127.0.0.1:8765/`가 열립니다(쓰이는 중이면 다음 빈 포트). 창을 닫으면 꺼집니다.
- 명령으로 켜기:

  ```powershell
  python 10_제작페이지/제작페이지.py --폴더 .
  ```

- Claude Code에서 이 폴더를 열고 "제작 페이지 열어 줘" / "제작 페이지 꺼 줘"라고 해도 됩니다.

## 쓰는 흐름

1. 캐릭터 고르기의 "＋ 새 캐릭터 입력…"으로 캐릭터를 만듭니다(`01_캐릭터/<이름>/`, 캐릭터 노트는 `SSOT/캐릭터/_새캐릭터_틀.md`를 복사해 `SSOT/캐릭터/<이름>.md`로).
2. 단계 화면에서 고칠 곳을 붓으로 칠하고 "보내기"를 누릅니다.
3. Claude Code에 "보냈어"라고 합니다. 에이전트가 `10_제작페이지/에이전트_안내.md`대로 받아 고치고, 페이지의 결정 칸에 알림을 남깁니다.
4. 결과를 3D로 확인하고 "이 단계 끝" / "고쳐 줘" / "되돌리기"를 고릅니다.

## 폴더

| 폴더 | 내용 |
| --- | --- |
| `10_제작페이지/` | 서버·화면(`정적/`, three.js 사본 포함)·Blender 스크립트·에이전트 명령·검사. 자세한 설명은 그 폴더의 `README.md` |
| `SSOT/` | 에이전트가 읽는 단계별 규칙·규격(`00_시작.md`부터)과 공통 도구(`도구/`) |
| `00_공통문서/제작페이지_설계/` | 기능명세(에이전트가 지킬 약속), 화면 디자인 토큰 |
| `01_캐릭터/` | 만든 캐릭터가 들어가는 곳(처음에는 비어 있음) |
| `.claude/skills/jejak-page/` | Claude Code 스킬 |

## 시험

```powershell
python 10_제작페이지/검사/서버시험.py
```

`--원본`을 받는 다른 시험(`승인시험.py`, `메시시험.py` 등)은 예시 캐릭터 자료가 있어야 돕니다.

## 라이선스

- MIT(`LICENSE`).
- three.js 사본: MIT(`10_제작페이지/정적/lib/three/LICENSE`).
