// 페이지 안에서 돌리는 화면 검사(브라우저 쪽 코드). 브라우저 도구가 이 파일을 읽어 page.evaluate로 넣는다.
// - 디자인규격_v001.md 7절 2번(계산된 모양), 3번(칸 안의 순서)
// - 기능명세 1부 9절 12번(칸 밖으로 나간 글, 페이지 가로 스크롤)
// 결과: { 화면, 가로스크롤, 넘침[], 잘림[], 값밖[], 높이밖[], 순서[], 빠짐[], 풀이없음[], 불일치[] } — 배열이 모두 비고 가로스크롤이 거짓이면 통과.
(() => {
  const 간격 = [0, 4, 8, 12, 16, 24, 32];
  const 글자 = [12, 13, 14, 16, 18];
  const 둥글기 = [0, 4, 6, 8, 10, 999];
  const 높이 = [16, 22, 28, 36, 40, 44, 52, 56];
  const 순서표 = {
    "윗줄": ["페이지 이름", "캐릭터 고르기", "지금 단계", "TRIPO 잔액", "주소"],
    "왼쪽": ["칸 제목", "단계 줄", "파일 가져오기"],
    "가운데": ["제목줄", "보기 줄", "도구 줄", "표시 목록", "단계마다 더 있는 것", "사람이 하는 일"],
    "오른쪽": ["칸 제목", "에이전트 알림", "보내기", "승인 상자", "결정 단추", "대화는 Claude 앱에서"],
  };
  const 보임 = (el) => {
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== "hidden";
  };
  const 이름 = (el) => {
    let s = el.tagName.toLowerCase();
    if (el.id) s += "#" + el.id;
    if (el.classList.length) s += "." + [...el.classList].join(".");
    return s;
  };
  const 같음 = (v, 목록) => 목록.some((x) => Math.abs(v - x) < 0.05);
  const 결과 = {화면: `${innerWidth}×${innerHeight}`, 가로스크롤: false, 넘침: [], 잘림: [], 값밖: [], 높이밖: [], 순서: [], 센요소: 0};

  const d = document.documentElement;
  결과.가로스크롤 = d.scrollWidth > d.clientWidth;

  // 우리 화면(.app, 묻는 상자, 알림 띠)만 센다. 브라우저가 그리는 <option> 목록은 빼고 센다.
  const 대상 = [...document.querySelectorAll(".app *, .overlay, .overlay *, .banners, .banners *")]
    .filter((el) => el.tagName !== "OPTION" && 보임(el));
  결과.센요소 = 대상.length;
  for (const el of 대상) {
    const cs = getComputedStyle(el);
    // 2번: 계산된 값
    for (const p of ["paddingTop", "paddingRight", "paddingBottom", "paddingLeft", "marginTop", "marginRight", "marginBottom", "marginLeft"]) {
      const v = parseFloat(cs[p]);
      if (!같음(v, 간격)) 결과.값밖.push({요소: 이름(el), 무엇: p, 값: cs[p]});
    }
    for (const p of ["rowGap", "columnGap"]) {
      if (cs[p] === "normal") continue;
      const v = parseFloat(cs[p]);
      if (!같음(v, 간격)) 결과.값밖.push({요소: 이름(el), 무엇: p, 값: cs[p]});
    }
    const fs = parseFloat(cs.fontSize);
    if (!같음(fs, 글자)) 결과.값밖.push({요소: 이름(el), 무엇: "fontSize", 값: cs.fontSize});
    if (cs.lineHeight !== "normal" && Math.abs(parseFloat(cs.lineHeight) / fs - 1.5) > 0.01)
      결과.값밖.push({요소: 이름(el), 무엇: "lineHeight", 값: cs.lineHeight});
    for (const p of ["borderTopLeftRadius", "borderTopRightRadius", "borderBottomLeftRadius", "borderBottomRightRadius"]) {
      const v = parseFloat(cs[p]);
      if (!같음(v, 둥글기)) 결과.값밖.push({요소: 이름(el), 무엇: p, 값: cs[p]});
    }
    // 12번: 글 넘침. 보이는 채로 넘친 것 = 칸 밖으로 나간 글
    const 말줄임 = cs.textOverflow === "ellipsis";
    const 스크롤칸 = ["auto", "scroll"].includes(cs.overflowY) || ["auto", "scroll"].includes(cs.overflowX);
    const 인라인 = cs.display === "inline";
    if (!인라인) {
      const 가로 = el.scrollWidth > el.clientWidth + 1, 세로 = el.scrollHeight > el.clientHeight + 1;
      if (스크롤칸) {
        if (el.scrollWidth > el.clientWidth + 1) 결과.넘침.push({요소: 이름(el), 무엇: "칸 안 가로 스크롤", 값: `${el.scrollWidth}>${el.clientWidth}`});
      } else if (cs.overflowX === "visible" && 가로) {
        결과.넘침.push({요소: 이름(el), 무엇: "가로로 넘침", 값: `${el.scrollWidth}>${el.clientWidth}`});
      } else if (cs.overflowY === "visible" && 세로 && el.clientHeight > 0) {
        결과.넘침.push({요소: 이름(el), 무엇: "세로로 넘침", 값: `${el.scrollHeight}>${el.clientHeight}`});
      } else if (cs.overflowX === "hidden" && !말줄임 && (가로 || 세로)) {
        // 말줄임 없이 숨겨 잘린 것(이유 없이 글이 잘림)
        결과.잘림.push({요소: 이름(el), 무엇: 가로 ? "가로로 잘림" : "세로로 잘림", 값: 가로 ? `${el.scrollWidth}>${el.clientWidth}` : `${el.scrollHeight}>${el.clientHeight}`});
      }
    }
    // 칸(카드·윗줄) 밖으로 가로로 나간 요소
    const 칸 = el.closest(".card, .top");
    if (칸 && 칸 !== el) {
      const a = el.getBoundingClientRect(), b = 칸.getBoundingClientRect();
      if (a.left < b.left - 0.5 || a.right > b.right + 0.5) 결과.넘침.push({요소: 이름(el), 무엇: "칸 밖으로 나감", 값: `${a.left.toFixed(0)}~${a.right.toFixed(0)} / 칸 ${b.left.toFixed(0)}~${b.right.toFixed(0)}`});
    }
  }

  // 2번: 높이를 정해 둔 요소의 실제 높이(우리 CSS에서 height를 토큰으로 정한 규칙만)
  for (const sheet of document.styleSheets) {
    if (!sheet.href || !sheet.href.includes("앱.css") && !decodeURIComponent(sheet.href).includes("앱.css")) continue;
    for (const rule of sheet.cssRules) {
      if (!rule.style || !rule.style.height || !rule.style.height.includes("var(")) continue;
      for (const el of document.querySelectorAll(rule.selectorText)) {
        if (!보임(el)) continue;
        if (!같음(el.offsetHeight, 높이)) 결과.높이밖.push({요소: 이름(el), 규칙: rule.selectorText, 값: el.offsetHeight});
      }
    }
  }

  // 2번(역할별): 요소마다 정해진 높이(디자인 규격 2절)
  const 역할높이 = {".top": 56, ".step": 40, ".card h3": 44, ".center .head": 52, ".send": 44, ".tb": 28, ".pill": 28, ".btn": 36, ".step .n": 22};
  for (const [sel, 값] of Object.entries(역할높이)) {
    for (const el of document.querySelectorAll(sel)) {
      if (보임(el) && Math.abs(el.offsetHeight - 값) > 0.5) 결과.높이밖.push({요소: 이름(el), 규칙: `${sel} = ${값}`, 값: el.offsetHeight});
    }
  }

  // 반드시 보여야 하는 요소(펼침/접음에 따라)
  const 접음 = document.getElementById("main").classList.contains("folded");
  const 필수 = ["[data-순서='페이지 이름']", "[data-순서='캐릭터 고르기']", "[data-순서='지금 단계']", "[data-순서='TRIPO 잔액']", "[data-순서='주소']",
    "[data-칸='왼쪽'] h3", "[data-순서='파일 가져오기']", "#title", "#src", "#folder"]
    .concat(접음 ? ["#unfold", "#sendtop"] : ["#fold", "[data-순서='에이전트 알림']", "#send", "[data-순서='대화는 Claude 앱에서']"]);
  결과.빠짐 = [];
  for (const sel of 필수) {
    const el = document.querySelector(sel);
    const 뷰 = el && el.getBoundingClientRect();
    if (!el || !보임(el) || 뷰.right > innerWidth + 0.5 || 뷰.bottom > innerHeight + 0.5 || 뷰.left < -0.5) 결과.빠짐.push(sel);
  }
  if (document.querySelectorAll("#steps .step").length !== 11) 결과.빠짐.push("단계 줄 11개");

  // 말줄임으로 잘린 글은 마우스를 올리면 전체를 볼 수 있어야 한다(디자인 규격 5절)
  결과.풀이없음 = [];
  for (const el of 대상) {
    const cs = getComputedStyle(el);
    if (cs.textOverflow !== "ellipsis" || el.scrollWidth <= el.clientWidth + 1) continue;
    const 글 = el.textContent.trim();
    const 풀이 = el.closest("[title]");
    if (!풀이 || !풀이.title.includes(글)) 결과.풀이없음.push({요소: 이름(el), 글: 글.slice(0, 40)});
  }

  // 고른 캐릭터와 보이는 내용이 같은 캐릭터인가(기능명세 1부 9절 3번)
  결과.불일치 = [];
  const 고른 = document.getElementById("char").value, 폴더 = document.getElementById("folder").textContent;
  if (고른 && 폴더 !== `01_캐릭터/${고른}/`) 결과.불일치.push({고른, 폴더});
  if (고른 && document.getElementById("charname").textContent !== 고른) 결과.불일치.push({고른, 윗줄: document.getElementById("charname").textContent});

  // 3번: 칸 안의 순서
  for (const [칸이름, 표] of Object.entries(순서표)) {
    const 칸 = document.querySelector(`[data-칸="${칸이름}"]`);
    if (!칸) { 결과.순서.push({칸: 칸이름, 문제: "칸이 없음"}); continue; }
    const 실제 = [...칸.querySelectorAll("[data-순서]")].filter(보임).map((el) => el.dataset.순서);
    let 앞 = -1;
    for (const x of 실제) {
      const i = 표.indexOf(x);
      if (i < 0) 결과.순서.push({칸: 칸이름, 문제: `표에 없는 요소: ${x}`});
      else if (i <= 앞) 결과.순서.push({칸: 칸이름, 문제: `순서가 다름: ${실제.join(" → ")}`});
      else 앞 = i;
    }
    결과[`순서_${칸이름}`] = 실제.join(" → ");
  }
  const 번호 = [...document.querySelectorAll("#steps .step .n")].map((el) => Number(el.textContent));
  if (번호.join() !== "1,2,3,4,5,6,7,8,9,10,11") 결과.순서.push({칸: "왼쪽", 문제: `단계 번호: ${번호.join()}`});
  const 머리 = [...document.querySelectorAll(".center .head > *")].map((el) => el.id || el.className);
  if (머리.join() !== "title,src,sp,folder") 결과.순서.push({칸: "가운데 제목줄", 문제: 머리.join()});
  if (document.querySelector("#steps .importbtn, .steps .importbtn")) 결과.순서.push({칸: "왼쪽", 문제: "파일 가져오기가 스크롤 안에 있음"});
  return 결과;
})()
