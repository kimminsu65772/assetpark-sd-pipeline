"""화면 자동 검사(기능명세 27절 "맡는 모델과 검사", 디자인 규격 7절 1~3번, 1부 9절 12번).

켜 둔 제작 페이지를 ego-browser로 열어, 세 화면 크기(1920×1080, 1536×864, 1280×720)와 1280×720 접음에서
모든 캐릭터 × 모든 단계 화면을 검사한다. 페이지 안의 검사는 같은 폴더의 `화면검사.js`가 한다:
규격 밖 간격·글자 크기·높이, 칸 밖으로 넘친 글, 말줄임 없이 잘린 글, 가로 스크롤, 칸 안의 순서,
필수 요소, 말줄임 글의 풀이, 고른 캐릭터와 내용의 일치. 토큰 밖 숫자·색은 `숫자검사.py`로 센다.
단계마다 화면 그림을 남긴다(그림 캐릭터 하나에 대해, 크기마다). 위반이 0이 아니면 종료 코드 1.

    python 검사/화면검사.py --주소 http://127.0.0.1:8765/ --그림 <폴더>
    python 검사/화면검사.py --주소 http://127.0.0.1:8765/ --자가시험     # 일부러 망가뜨린 화면을 잡는지

- 서버는 먼저 켜 둔다(만드는 동안에는 가짜 저장소를 `--폴더`로). 이 스크립트는 파일을 쓰지 않는다(그림·결과.json만).
- `--캐릭터 <이름> ...`으로 캐릭터를 고를 수 있다. 기본은 목록의 모든 캐릭터.
- 상태 파일이 없는 캐릭터를 고르면 페이지가 "새 캐릭터로 만들까요?"를 묻는다. 검사는 그 상자를 닫고(만들지 않음) 지나간다.
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

여기 = Path(__file__).resolve().parent
크기 = [(1920, 1080, False), (1536, 864, False), (1280, 720, False), (1280, 720, True)]
항목 = ["넘침", "잘림", "값밖", "높이밖", "순서", "빠짐", "풀이없음", "불일치"]

브라우저코드 = r"""
const fs = await import("node:fs/promises");
const 설정 = __설정__;
const chk = await fs.readFile(설정.검사파일, "utf8");
const task = await taskSpace("가마우지 화면검사 " + Date.now());
const page = task.page("p1");
const 결과 = {화면수: 0, 위반: [], 그림: [], 자가시험: null};
const 나쁨 = (r) => r.가로스크롤 || 설정.항목.some(k => (r[k] || []).length);
try {
  await page.cdp("Emulation.setDeviceMetricsOverride", {width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false});
  await page.goto(설정.주소);
  await page.waitForFunction(() => typeof 화면 !== "undefined" && 화면.준비 && document.querySelectorAll("#steps .step").length === 11, undefined, {timeout: 15000});
  const 모두 = await page.evaluate(() => [...document.getElementById("char").options].map(o => o.value).filter(Boolean));
  const 캐릭터 = 설정.캐릭터.length ? 설정.캐릭터.filter(c => 모두.includes(c)) : 모두;
  const 그림캐릭터 = 설정.그림캐릭터 && 모두.includes(설정.그림캐릭터) ? 설정.그림캐릭터 : 캐릭터[0];
  async function 고르기(c, 접음) {
    await page.evaluate(async ({c, 접음}) => {
      if (document.getElementById("main").classList.contains("folded") !== 접음) document.getElementById(접음 ? "fold" : "unfold").click();
      const s = document.getElementById("char");
      if (s.value !== c) { s.value = c; s.dispatchEvent(new Event("change")); }
      for (let k = 0; k < 200 && (화면.불러오는중 || !화면.보기); k++) await new Promise(r => setTimeout(r, 50));
      if (!document.getElementById("ask").hidden) document.getElementById("askno").click();
    }, {c, 접음});
  }
  if (설정.자가시험) {
    // 일부러 망가뜨린 화면 다섯 가지를 각각 잡는지 본다
    const 망가뜨림 = {
      "잔액 숨김": () => { document.getElementById("tripo").style.display = "none"; },
      "단계 줄 36": () => { document.querySelector("#steps .step").style.height = "36px"; },
      "말줄임 풀이 지움": () => { const e = document.getElementById("src"); e.textContent = "아주 긴 출처 ".repeat(40); e.removeAttribute("title"); },
      "순서 바꿈": () => { document.querySelector(".center .head").appendChild(document.getElementById("title")); },
      "간격 10": () => { document.querySelector(".center .body").style.gap = "10px"; },
      "글 넘침": () => { const e = document.querySelector("#steps .step .t"); e.style.overflow = "visible"; e.textContent = "넘치는글".repeat(30); },
      "캐릭터 어긋남": () => { document.getElementById("folder").textContent = "01_캐릭터/다른캐릭터/"; },
    };
    결과.자가시험 = {};
    await page.cdp("Emulation.setDeviceMetricsOverride", {width: 1280, height: 720, deviceScaleFactor: 1, mobile: false});
    for (const [이름, 함수] of Object.entries(망가뜨림)) {
      await page.reload();
      await page.waitForFunction(() => typeof 화면 !== "undefined" && 화면.준비 && document.querySelectorAll("#steps .step").length === 11, undefined, {timeout: 15000});
      await 고르기(그림캐릭터, false);
      const 전 = await page.evaluate(chk);
      await page.evaluate(`(${함수.toString()})()`);
      const 후 = await page.evaluate(chk);
      결과.자가시험[이름] = {망가뜨리기전_통과: !나쁨(전), 잡음: 나쁨(후)};
    }
    await page.reload();
  } else {
    for (const [w, h, 접음] of 설정.크기) {
      await page.cdp("Emulation.setDeviceMetricsOverride", {width: w, height: h, deviceScaleFactor: 1, mobile: false});
      for (const c of 캐릭터) {
        await 고르기(c, 접음);
        for (let i = 0; i < 11; i++) {
          await page.evaluate((i) => document.querySelectorAll("#steps .step")[i].click(), i);
          const r = await page.evaluate(chk);
          결과.화면수++;
          if (나쁨(r)) 결과.위반.push({크기: `${w}x${h}`, 접음, 캐릭터: c, 단계: i + 1,
            내용: Object.fromEntries(Object.entries(r).filter(([k, v]) => (Array.isArray(v) && v.length) || (k === "가로스크롤" && v)))});
          if (설정.그림 && c === 그림캐릭터) {
            const p = `${설정.그림}/${w}x${h}${접음 ? "_접음" : ""}_${String(i + 1).padStart(2, "0")}단계.png`;
            await page.screenshot({path: p});
            결과.그림.push(p);
          }
        }
      }
    }
    // 바깥으로 나간 요청이 있었는지(1부 9절 2번)
    결과.요청한곳 = await page.evaluate(() => [...new Set([location.host, ...performance.getEntriesByType("resource").map(e => new URL(e.name).host)])]);
    await page.evaluate(() => { if (document.getElementById("main").classList.contains("folded")) document.getElementById("unfold").click(); });
  }
} finally {
  console.log("@@결과@@" + JSON.stringify(결과));
  await task.finish({keep: []});
}
"""


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="제작 페이지 화면 자동 검사(ego-browser)")
    p.add_argument("--주소", default="http://127.0.0.1:8765/")
    p.add_argument("--그림", help="단계마다 화면 그림을 남길 폴더")
    p.add_argument("--캐릭터", nargs="*", default=[])
    p.add_argument("--그림캐릭터", help="그림을 남길 캐릭터(기본: 검사하는 첫 캐릭터)")
    p.add_argument("--자가시험", action="store_true")
    인자 = p.parse_args()

    sys.path.insert(0, str(여기))
    import 숫자검사  # noqa: E402
    숫자위반 = []
    for f in sorted((여기.parent / "정적").rglob("*")):
        if f.suffix in (".css", ".html", ".js") and "lib" not in f.relative_to(여기.parent / "정적").parts:
            숫자위반 += 숫자검사.검사(f.read_text(encoding="utf-8"), f.name)

    그림 = None
    if 인자.그림:
        그림 = Path(인자.그림).resolve()
        그림.mkdir(parents=True, exist_ok=True)
    설정 = {
        "주소": 인자.주소, "검사파일": (여기 / "화면검사.js").as_posix(), "그림": 그림.as_posix() if 그림 else None,
        "캐릭터": 인자.캐릭터, "그림캐릭터": 인자.그림캐릭터, "자가시험": 인자.자가시험,
        "크기": [list(k) for k in 크기], "항목": 항목,
    }
    코드 = 브라우저코드.replace("__설정__", json.dumps(설정, ensure_ascii=False))
    with tempfile.TemporaryDirectory(prefix="화면검사_") as d:
        파일 = Path(d) / "검사.mjs"
        파일.write_text(코드, encoding="utf-8")
        r = subprocess.run(["ego-browser", "nodejs", "-e", f"await import('{파일.as_uri()}')"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
    줄 = next((l[l.index("@@결과@@"):] for l in (r.stdout + chr(10) + r.stderr).splitlines() if "@@결과@@" in l), None)
    if 줄 is None:
        print("브라우저 검사를 돌리지 못했습니다.\n" + r.stdout[-2000:] + r.stderr[-2000:])
        return 2
    결과 = json.loads(줄[len("@@결과@@"):])
    결과["숫자위반"] = [list(x) for x in 숫자위반]

    if 인자.자가시험:
        못잡음 = [k for k, v in 결과["자가시험"].items() if not (v["잡음"] and v["망가뜨리기전_통과"])]
        for k, v in 결과["자가시험"].items():
            print(f"{'통과' if k not in 못잡음 else '실패'} {k}: 망가뜨리기 전 통과={v['망가뜨리기전_통과']}, 잡음={v['잡음']}")
        print(f"화면 검사 자가시험: {len(결과['자가시험'])}가지 중 못 잡음 {len(못잡음)}")
        return 1 if 못잡음 else 0

    바깥 = [h for h in 결과.get("요청한곳", []) if not h.startswith(("127.0.0.1", "localhost"))]
    for v in 결과["위반"][:20]:
        print(f"위반 {v['크기']}{' 접음' if v['접음'] else ''} {v['캐릭터']} {v['단계']}단계: {json.dumps(v['내용'], ensure_ascii=False)[:300]}")
    for x in 숫자위반:
        print(f"숫자 위반 {x[0]}:{x[1]} {x[2]}")
    print(f"화면 검사: 화면 {결과['화면수']}개, 위반 화면 {len(결과['위반'])}개, 토큰 밖 숫자·색 {len(숫자위반)}개, "
          f"바깥 요청 {len(바깥)}곳{바깥 if 바깥 else ''}, 그림 {len(결과['그림'])}장" + (f" → {그림}" if 그림 else ""))
    if 그림:
        (그림 / "결과.json").write_text(json.dumps(결과, ensure_ascii=False, indent=1), encoding="utf-8")
    return 1 if (결과["위반"] or 숫자위반 or 바깥 or 결과["화면수"] == 0) else 0


if __name__ == "__main__":
    sys.exit(main())
