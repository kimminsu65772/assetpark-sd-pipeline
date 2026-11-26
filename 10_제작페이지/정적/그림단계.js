// 1단계 그림 생성 화면 — 작업 묶음 W09 (기능명세 2부 13절, 1부 4-4·5-4·5-4b·5-5)
// 가운데: 보기 줄(그림 칸 + 옆 기둥: 캐릭터 노트·요청문·고르기) → 도구 줄 → 표시 목록 → 판정표 → 사람이 하는 일.
// 그림 위에 붓·지우개로 칠한다(2D). 표시는 작성중.json(2-1, 자리.그림)으로 자동 저장, 보내기는 보내기_<시각>.json.
// 결정 칸의 1단계 단추(생성·승인·다시 생성)는 결정.js가 이 모듈에 묻는다. 새 캐릭터 입력 칸도 여기서 그린다.
// 서버(127.0.0.1)에만 요청한다. 화면 크기 숫자는 CSS(토큰)에만 있고, 그림 칸 안의 그림 상수는 아래 한 곳에 모았다(디자인 규격 6절).
"use strict";

(() => {
  const $ = (id) => document.getElementById(id);
  const 글 = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const 상수 = {세계높이: 1000, 판사이: 40, 여백: 24, 붓기본: 16, 붓최소: 3, 붓최대: 120, 붓휠: 0.0015, 점간격: 0.35,
    확대최소: 0.05, 확대최대: 40, 손띠: [0.40, 0.70], 발띠: [0.80, 1.0], 저장늦춤: 400, 취소한도: 50, 많은표시: 100};
  const 보기이름 = {기준: "기준 그림", 시트: "4방향 시트", 네장: "자른 네 장"};
  const 원번호 = (n) => (n >= 1 && n <= 20 ? String.fromCharCode(0x2460 + n - 1) : `(${n})`);
  const 색 = (k) => getComputedStyle(document.documentElement).getPropertyValue(k).trim();

  const 그 = {이름: null, 값: null, 보는것: "기준", 판: {기준: 0, 시트: 0}, 나란히: "", 도구: "보기", 붓: 상수.붓기본,
    표시: [], 다음번호: 1, 묶음번호: 0, 취소: [], 다시: [], 묶음: [], 고른: null, 칠할종류: "", 바깥: null, 바깥표시: null,
    보내는중: false, 상태글: "", 상태종류: "", 저장틀: null, 미저장: false, 카메라: null, 띠: "", 입력폼: false};
  window.그림상태 = 그;   // 시험·검사용으로 읽기만

  const 그림창고 = new Map();   // 경로 → Image
  function 그림(경로) {
    if (!그림창고.has(경로)) {
      const im = new Image();
      im.onload = () => 그리기캔버스();
      im.onerror = () => { im.실패 = true; 그리기캔버스(); };
      im.src = `/api/그림/파일?경로=${encodeURIComponent(경로)}`;
      그림창고.set(경로, im);
    }
    return 그림창고.get(경로);
  }

  async function 받기(경로) {
    const r = await fetch(경로, {cache: "no-store"});
    const v = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(v.오류 || `${r.status}`);
    return v;
  }
  async function 보내기(경로, 몸) {
    const r = await fetch(경로, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(몸)});
    const v = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(v.오류 || `${r.status}`);
    return v;
  }

  // ---------------------------------------------------------------- 뿌리(한 번 만들고 다시 붙인다)
  const 뿌리 = document.createElement("div");
  뿌리.className = "g1";
  뿌리.innerHTML = `
    <div class="vrow" data-순서="보기 줄">
      <div class="view g1v"><canvas class="g1c" tabindex="0" aria-label="그림 칸"></canvas><span class="lbl" id="g1lbl"></span><span class="lbl2" id="g1lbl2"></span>
        <div class="vmsg" id="g1msg" hidden></div><div class="brush" id="g1brush" hidden></div></div>
      <div class="g1aside"><div class="g1asidein">
        <div class="note"><div class="ttl" id="g1notettl">캐릭터 노트</div><div id="g1note"></div></div>
        <div class="note"><div class="ttl">요청문 (조립됨)</div><div id="g1req"></div></div>
        <div class="seg" id="g1seg" role="group" aria-label="볼 그림 고르기"></div>
        <div class="g1ver" id="g1ver"></div>
      </div></div>
    </div>
    <div class="tools" data-순서="도구 줄" id="g1tools"></div>
    <div class="marks" data-순서="표시 목록">
      <div class="mhead"><span class="mttl">표시</span><span class="mlab">칠할 종류</span><select class="g1sel" id="g1kind" aria-label="칠할 종류"></select><span class="mst" id="g1st"></span></div>
      <div class="mlist" id="g1list"></div>
      <div class="note mdetail" id="g1detail" hidden></div>
    </div>
    <div class="g1more" data-순서="단계마다 더 있는 것" id="g1more"></div>
    <div class="human" data-순서="사람이 하는 일"><b>사람이 하는 일</b> · 그림을 보고 승인하거나, 이상한 곳을 그림 위에 칠해 보내고 "고쳐 줘". 탈락한 그림은 다음 단계로 넘어가지 않음.</div>`;
  const 캔버스 = 뿌리.querySelector(".g1c");
  const 원 = 뿌리.querySelector("#g1brush");
  const 칸 = 뿌리.querySelector(".g1v");

  // 입력 칸(새 캐릭터)
  const 입력뿌리 = document.createElement("div");
  입력뿌리.className = "g1";

  // ---------------------------------------------------------------- 지금 보는 것
  function 같은종류(종류) { return ((그.값 && 그.값.그림) || []).filter((g) => g.종류 === 종류); }
  function 지금그림() {
    const 종류 = 그.보는것 === "기준" ? "기준" : "시트";
    const 목록 = 같은종류(종류);
    if (!목록.length) return null;
    const i = Math.max(0, Math.min(목록.length - 1, 목록.length - 1 - (그.판[종류] || 0)));
    return 목록[i];
  }
  function 승인된기준() { return 같은종류("기준").filter((g) => g.승인 === "승인").pop() || null; }

  function 판들() {   // 그림 칸에 놓을 판: {경로, 참고(칠하지 않음), 이름}
    const g = 지금그림();
    let 판 = [];
    if (g) {
      if (그.보는것 === "네장") 판 = (g.자른것 || []).map((x) => ({경로: x, 이름: x.split("/").pop()}));
      else 판 = (g.파일 || []).map((x) => ({경로: x, 이름: `${g.번호}`}));
    }
    if (그.나란히 === "기준") {
      const b = 승인된기준() || 같은종류("기준").slice(-1)[0];
      if (b && b.파일[0] && !판.some((x) => x.경로 === b.파일[0])) 판.push({경로: b.파일[0], 이름: `기준 ${b.번호}`, 참고: true});
    } else if (그.나란히.startsWith("캐릭터:")) {
      const n = 그.나란히.slice(4);
      const c = ((그.값 && 그.값.다른캐릭터) || []).find((x) => x.이름 === n);
      if (c) 판.push({경로: c.그림, 이름: n, 참고: true});
    }
    // 세계 좌표에 놓기: 높이를 같게(발바닥 높이를 맞춤)
    let x = 0;
    for (const p of 판) {
      const im = 그림(p.경로);
      const w = im.naturalWidth || 1, h = im.naturalHeight || 1;
      p.k = 상수.세계높이 / h; p.x = x; p.y = 0; p.w = w * p.k; p.h = 상수.세계높이; p.im = im;
      x += p.w + 상수.판사이;
    }
    return 판;
  }

  // ---------------------------------------------------------------- 그림 칸(캔버스)
  let 마지막판 = [];
  function 카메라맞춤(띠) {
    const 판 = 마지막판;
    const r = 캔버스.getBoundingClientRect();
    if (!판.length || !r.width) { 그.카메라 = null; return; }
    const W = 판[판.length - 1].x + 판[판.length - 1].w;
    const y0 = 띠 ? 상수[띠][0] * 상수.세계높이 : 0, y1 = 띠 ? 상수[띠][1] * 상수.세계높이 : 상수.세계높이;
    const s = Math.min((r.width - 2 * 상수.여백) / W, (r.height - 2 * 상수.여백) / (y1 - y0));
    그.카메라 = {s, ox: (r.width - W * s) / 2, oy: (r.height - (y1 - y0) * s) / 2 - y0 * s};
  }
  const 화면에서 = (x, y) => ({x: (x - 그.카메라.ox) / 그.카메라.s, y: (y - 그.카메라.oy) / 그.카메라.s});

  function 그리기캔버스() {
    if (!뿌리.isConnected) return;
    const r = 캔버스.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    if (캔버스.width !== Math.round(r.width * dpr) || 캔버스.height !== Math.round(r.height * dpr)) {
      캔버스.width = Math.round(r.width * dpr); 캔버스.height = Math.round(r.height * dpr);
    }
    const 판 = 판들();
    const 바뀜 = 판.map((p) => `${p.경로}:${p.im.naturalWidth}`).join("|") !== 마지막판.map((p) => `${p.경로}:${p.im.naturalWidth}`).join("|");
    마지막판 = 판;
    if (바뀜 || !그.카메라) 카메라맞춤(그.띠);
    const c = 캔버스.getContext("2d");
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    c.clearRect(0, 0, r.width, r.height);
    const 메시지 = $("g1msg");
    const g = 지금그림();
    let 글들 = "";
    if (!그.값) 글들 = "불러오는 중…";
    else if (그.값.실행중) 글들 = `생성하는 중…${그.값.모드 === "가짜" ? " (가짜 실행)" : " (Codex)"}`;
    else if (!g) 글들 = 그.보는것 === "기준" ? "아직 기준 그림이 없습니다. 오른쪽 결정 칸의 '생성'을 누르세요." : "아직 4방향 시트가 없습니다. 기준 그림을 승인한 뒤 '시트 생성'을 누르세요.";
    else if (g.실패이유) 글들 = `생성 실패: ${g.실패이유}`;
    else if (그.보는것 === "네장" && !(g.자른것 || []).length) 글들 = g.자르기오류 || "자른 네 장이 없습니다.";
    메시지.hidden = !글들 || (판.some((p) => !p.참고) && !(그.값 && 그.값.실행중));
    메시지.textContent = 글들;
    $("g1lbl").textContent = g ? `${보기이름[그.보는것]} ${g.번호}${g.승인 === "승인" ? " · 승인" : g.탈락 ? " · 탈락" : g.승인 === "대체됨" ? " · 대체됨" : ""}` : 보기이름[그.보는것];
    const 크기 = 판.filter((p) => !p.참고 && p.im.naturalWidth).map((p) => `${p.im.naturalWidth}×${p.im.naturalHeight}`);
    $("g1lbl2").textContent = 크기.length === 1 ? 크기[0] : 크기.length ? `${크기.length}장` : "";
    $("g1lbl2").title = 판.map((p) => p.경로).join("\n");
    if (!그.카메라) return;
    const {s, ox, oy} = 그.카메라;
    c.save();
    c.translate(ox, oy); c.scale(s, s);
    c.imageSmoothingQuality = "high";
    for (const p of 판) {
      if (p.im.complete && p.im.naturalWidth) c.drawImage(p.im, p.x, p.y, p.w, p.h);
      c.lineWidth = 1 / s;
      c.strokeStyle = p.참고 ? 색("--c-text-3") : 색("--c-line");
      c.setLineDash(p.참고 ? [6 / s, 4 / s] : []);
      c.strokeRect(p.x, p.y, p.w, p.h);
    }
    c.setLineDash([]);
    // 표시: 빨강(사용자), 고른 것은 굵게
    const 빨강 = 색("--c-danger");
    for (const m of 그.표시) {
      const 그자리 = m.자리.그림;
      const p = 판.find((x) => x.경로 === 그자리.파일 && !x.참고);
      if (!p) continue;
      c.globalAlpha = m.번호 === 그.고른 ? 0.55 : 0.35;
      c.fillStyle = 빨강;
      for (const 획 of 그자리.획 || []) for (const [x, y] of 획.점) {
        c.beginPath(); c.arc(p.x + x * p.k, p.y + y * p.k, 획.붓 * p.k, 0, Math.PI * 2); c.fill();
      }
      c.globalAlpha = 1;
      const [[x1, y1]] = 그자리.범위;
      c.font = `${18 / s}px ${색("--font") || "sans-serif"}`;
      c.fillStyle = 빨강;
      c.fillText(m.번호, p.x + x1 * p.k, p.y + y1 * p.k - 4 / s);
    }
    c.restore();
  }

  // ---------------------------------------------------------------- 칠하기(2D)
  let 끌기 = null;
  function 칠못함이유() {
    if (!그.이름) return "캐릭터를 고르세요";
    if (document.body.dataset.잠금) return document.body.dataset.잠금 === "다른 탭" ? "다른 탭에서 열려 있습니다" : "확인 중";
    if (그.묶음.some((x) => x.묶음상태 === "처리 중")) return "에이전트가 앞 묶음을 처리하는 중입니다";
    if (!마지막판.some((p) => !p.참고)) return "칠할 그림이 없습니다";
    return "";
  }
  function 판찾기(w) { return 마지막판.find((p) => !p.참고 && w.x >= p.x && w.x <= p.x + p.w && w.y >= p.y && w.y <= p.y + p.h); }
  function 기록남기기() {
    그.취소.push(JSON.stringify({표시: 그.표시, 다음번호: 그.다음번호}));
    if (그.취소.length > 상수.취소한도) 그.취소.shift();
    그.다시 = [];
  }
  function 범위다시(m) {
    let x1 = Infinity, y1 = Infinity, x2 = -Infinity, y2 = -Infinity;
    for (const 획 of m.자리.그림.획) for (const [x, y] of 획.점) {
      x1 = Math.min(x1, x - 획.붓); y1 = Math.min(y1, y - 획.붓); x2 = Math.max(x2, x + 획.붓); y2 = Math.max(y2, y + 획.붓);
    }
    const im = 그림(m.자리.그림.파일);
    const W = im.naturalWidth || x2, H = im.naturalHeight || y2;
    m.자리.그림.범위 = [[Math.max(0, Math.round(x1)), Math.max(0, Math.round(y1))], [Math.min(W, Math.round(x2)), Math.min(H, Math.round(y2))]];
  }
  function 칠시작(ev) {
    const w = 화면에서(ev.offsetX, ev.offsetY);
    const p = 판찾기(w);
    if (!p) { 상태알림("그림 밖이거나 참고 그림이라 칠하지 않았습니다"); return null; }
    const 점 = [(w.x - p.x) / p.k, (w.y - p.y) / p.k];
    const 붓 = 그.붓 / (그.카메라.s * p.k);
    기록남기기();
    if (그.도구 === "지우개") return {판: p, 지우개: true};
    let m = 그.고른 && 그.표시.find((x) => x.번호 === 그.고른 && x.자리.그림.파일 === p.경로);
    if (!m) {
      m = {번호: 원번호(그.다음번호), 누가: "사용자", 종류: 그.칠할종류 || 그.값.처리종류.slice(-1)[0],
        자리: {파츠: [], 면: {}, 그림: {파일: p.경로, 범위: [점, 점], 획: []}}, 반대쪽도: false, 메모: "", 작업본해시: ""};
      그.다음번호 += 1;
      그.표시.push(m);
      그.고른 = m.번호;
    }
    m.자리.그림.획.push({붓: Math.round(붓 * 10) / 10, 점: [점.map((v) => Math.round(v))]});
    범위다시(m);
    return {판: p, 표시: m};
  }
  function 칠이어(ev) {
    const w = 화면에서(ev.offsetX, ev.offsetY);
    const p = 끌기.판;
    const 점 = [Math.round((w.x - p.x) / p.k), Math.round((w.y - p.y) / p.k)];
    if (끌기.지우개) { 지우기(p, 점, 그.붓 / (그.카메라.s * p.k)); return; }
    const 획 = 끌기.표시.자리.그림.획.slice(-1)[0];
    const [px, py] = 획.점[획.점.length - 1];
    if (Math.hypot(점[0] - px, 점[1] - py) < 획.붓 * 상수.점간격) return;
    if (획.점.length > 2000) return;
    획.점.push(점);
    범위다시(끌기.표시);
  }
  function 지우기(p, [x, y], r) {
    for (const m of 그.표시) {
      if (m.자리.그림.파일 !== p.경로) continue;
      for (const 획 of m.자리.그림.획) 획.점 = 획.점.filter(([a, b]) => Math.hypot(a - x, b - y) > r + 획.붓);
      m.자리.그림.획 = m.자리.그림.획.filter((획) => 획.점.length);
      if (m.자리.그림.획.length) 범위다시(m);
    }
    const 전 = 그.표시.length;
    그.표시 = 그.표시.filter((m) => m.자리.그림.획.length);
    if (그.표시.length !== 전 && !그.표시.some((m) => m.번호 === 그.고른)) 그.고른 = null;
  }

  캔버스.addEventListener("contextmenu", (ev) => ev.preventDefault());
  캔버스.addEventListener("pointerdown", (ev) => {
    if (!그.카메라) return;
    캔버스.focus();
    캔버스.setPointerCapture(ev.pointerId);
    const 칠 = ev.button === 0 && !ev.shiftKey && 그.도구 !== "보기";
    if (칠) {
      const 이유 = 칠못함이유();
      if (이유) { 상태알림(이유); return; }
      const 시작 = 칠시작(ev);
      if (!시작) return;
      끌기 = {칠: true, ...시작};
      if (끌기.지우개) 칠이어(ev);
      그리기캔버스();
    } else 끌기 = {옮김: true, x: ev.clientX, y: ev.clientY};
  });
  캔버스.addEventListener("pointermove", (ev) => {
    붓원(ev);
    if (!끌기) return;
    if (끌기.옮김) {
      그.카메라.ox += ev.clientX - 끌기.x; 그.카메라.oy += ev.clientY - 끌기.y;
      끌기.x = ev.clientX; 끌기.y = ev.clientY;
    } else 칠이어(ev);
    그리기캔버스();
  });
  const 끌기끝 = () => {
    if (끌기 && 끌기.칠) 바뀜();
    끌기 = null;
  };
  캔버스.addEventListener("pointerup", 끌기끝);
  캔버스.addEventListener("pointercancel", 끌기끝);
  캔버스.addEventListener("pointerleave", () => { 원.hidden = true; });
  캔버스.addEventListener("wheel", (ev) => {
    ev.preventDefault();
    if (ev.shiftKey) { 그.붓 = Math.min(상수.붓최대, Math.max(상수.붓최소, 그.붓 * Math.exp(-(ev.deltaY || ev.deltaX) * 상수.붓휠 * 10))); 붓원(ev); return; }
    if (!그.카메라) return;
    const k = Math.exp(-ev.deltaY * 상수.붓휠);
    const s = Math.min(상수.확대최대, Math.max(상수.확대최소, 그.카메라.s * k));
    const w = 화면에서(ev.offsetX, ev.offsetY);
    그.카메라 = {s, ox: ev.offsetX - w.x * s, oy: ev.offsetY - w.y * s};
    그리기캔버스();
  }, {passive: false});
  캔버스.addEventListener("dblclick", () => { 그.띠 = ""; 카메라맞춤(""); 그리기캔버스(); 도구그리기(); });
  function 붓원(ev) {
    if (그.도구 === "보기" || 칠못함이유()) { 원.hidden = true; return; }
    원.hidden = false;
    원.classList.toggle("erase", 그.도구 === "지우개");
    원.style.width = 원.style.height = `${그.붓 * 2}px`;
    원.style.left = `${ev.offsetX - 그.붓}px`;
    원.style.top = `${ev.offsetY - 그.붓}px`;
  }
  new ResizeObserver(() => { if (뿌리.isConnected) { 카메라맞춤(그.띠); 그리기캔버스(); } }).observe(칸);

  // ---------------------------------------------------------------- 저장·보내기
  function 저장몸() {
    return {이름: 그.이름, 단계: 1, 탭: window.탭id || "", 표시: 그.표시, 후보판단: [], 다음번호: 그.다음번호, 묶음번호: 그.묶음번호,
      기록: {취소: 그.취소, 다시: 그.다시}};
  }
  function 바뀜() {
    그.미저장 = true;
    clearTimeout(그.저장틀);
    그.저장틀 = setTimeout(저장하기, 상수.저장늦춤);
    목록그리기(); 그리기캔버스(); 보내기그리기();
  }
  async function 저장하기() {
    if (!그.이름 || !그.미저장) return;
    그.미저장 = false;
    try {
      await 보내기("/api/작성중", 저장몸());
      $("b-save").hidden = true;
    } catch (e) {
      if (String(e.message).includes("그사이")) { await 표시읽기(); return; }
      그.미저장 = true;
      const b = $("b-save");
      b.textContent = `표시를 저장하지 못함: ${e instanceof TypeError ? "서버와 연결 끊김(다시 이어지면 저장)" : e.message}`;
      b.hidden = false;
    }
  }
  async function 표시읽기() {
    if (!그.이름) return;
    const 이름 = 그.이름;
    try {
      const v = await 받기(`/api/표시?이름=${encodeURIComponent(이름)}&단계=1`);
      if (이름 !== 그.이름) return;
      const 작 = v.작성중 || {};
      if (!그.미저장) {
        그.표시 = (작.표시 || []).filter((m) => m && m.자리 && m.자리.그림);
        그.다음번호 = 작.다음번호 || 그.표시.length + 1;
        그.묶음번호 = 작.묶음번호 || 0;
        그.취소 = (v.기록 && v.기록.취소) || []; 그.다시 = (v.기록 && v.기록.다시) || [];
      }
      그.묶음 = v.묶음 || [];
    } catch (e) { /* 연결 끊김은 앱.js 띠가 알림 */ }
    목록그리기(); 그리기캔버스(); 보내기그리기();
  }

  function 보낼수() { return 그.표시.length; }
  function 보내기그리기() {
    if (!붙음()) return;
    const n = 보낼수();
    const 처리중 = 그.묶음.some((x) => x.묶음상태 === "처리 중");
    const 보냄 = 그.묶음.filter((x) => x.묶음상태 === "보냄");
    const 막음 = !n ? "보낼 표시가 없습니다" : document.body.dataset.잠금 === "다른 탭" ? "다른 탭에서 열려 있습니다" : 그.보내는중 ? "보내는 중…" : "";
    for (const b of [$("send"), $("sendtop")]) {
      if (!b) continue;
      b.textContent = 그.보내는중 ? "보내는 중…" : `표시 ${n}개 보내기`;
      b.disabled = Boolean(막음);
      b.title = 막음 || `그림 위 표시 ${n}개를 보내기 파일로 씁니다`;
    }
    const h = document.querySelector(".sendwrap .hint");
    if (h) {
      h.textContent = 그.상태종류 === "보냄실패" ? 그.상태글
        : 처리중 ? "처리 중 — 에이전트가 앞 묶음을 고치는 중이라 칠하기를 막았습니다."
        : 보냄.length ? `보냄 — Claude 앱에서 '보냈어'라고 알려 주세요. (${보냄.map((x) => x.파일).join(", ")})`
        : n ? "보내면 Claude 앱에서 '보냈어'라고 알려 주세요." : "그림 위에 칠하면 누를 수 있습니다.";
      h.classList.toggle("ng", 그.상태종류 === "보냄실패");
    }
  }
  async function 보내기누름() {
    if (!붙음() || 그.보내는중 || !보낼수()) return;
    clearTimeout(그.저장틀);
    await 저장하기();
    const 빈메모 = 그.표시.filter((m) => ((typeof 화면 !== "undefined" && 화면.정보 && 화면.정보.메모필수) || ["기타"]).includes(m.종류) && !String(m.메모 || "").trim());
    if (빈메모.length) {
      그.고른 = 빈메모[0].번호;
      그.상태종류 = "보냄실패";
      그.상태글 = `보내지 못함: "기타"는 메모가 있어야 합니다(${빈메모.map((m) => m.번호).join(" ")}). 표시 목록에서 메모를 적어 주세요.`;
      목록그리기(); 보내기그리기();
      return;
    }
    if (그.표시.length > 상수.많은표시) {
      const 답 = await 물어보기("표시가 많습니다", `한 묶음에 ${그.표시.length}개입니다(${상수.많은표시}개 넘음). 그래도 보낼까요?`, [["그래도 보내기", "b-ok", true], ["취소", "b-re", false]]);
      if (!답) return;
    }
    let 합치기;
    const 남은 = 그.묶음.filter((x) => x.묶음상태 === "보냄");
    if (남은.length) {
      합치기 = await 물어보기("앞 묶음을 아직 처리하지 않았습니다", `앞 묶음을 아직 처리하지 않았습니다. 합쳐 보낼까요, 따로 보낼까요?<span class="hint">${글(남은.map((x) => x.파일).join(", "))}</span>`,
        [["합쳐 보내기", "b-ok", true], ["따로 보내기", "b-fix", false], ["취소", "b-re", null]]);
      if (합치기 === null) return;
    }
    그.보내는중 = true; 보내기그리기();
    try {
      await 보내기("/api/보내기", {이름: 그.이름, 단계: 1, 탭: window.탭id || "", 표시: 그.표시, 후보판단: [], 다음번호: 그.다음번호, 묶음번호: 그.묶음번호, 합치기});
      그.상태글 = ""; 그.상태종류 = "";
      그.표시 = []; 그.취소 = []; 그.다시 = []; 그.고른 = null; 그.미저장 = false;
      await 표시읽기();
    } catch (e) {
      그.상태종류 = "보냄실패";
      그.상태글 = `보내지 못함: ${e instanceof TypeError ? "서버와 연결 끊김" : e.message}`;
      if (String(e.message).includes("그사이")) await 표시읽기();
    } finally {
      그.보내는중 = false;
      보내기그리기();
      if (window.결정) window.결정.다시읽기();
    }
  }
  for (const b of [$("send"), $("sendtop")]) if (b) b.addEventListener("click", 보내기누름);

  // ---- 묻는 상자(index.html의 ask2)
  function 물어보기(제목, 본문, 단추들) {
    return new Promise((풀기) => {
      const o = $("ask2");
      $("ask2ttl").textContent = 제목;
      $("ask2body").innerHTML = 본문;
      const 줄 = $("ask2btns");
      줄.className = `btns${단추들.length}`;
      줄.innerHTML = 단추들.map(([t, c], i) => `<button class="btn ${c}" type="button" data-i="${i}">${글(t)}</button>`).join("");
      o.hidden = false;
      const 끝 = (값) => { o.hidden = true; o.removeEventListener("keydown", 키); 줄.onclick = null; 풀기(값); };
      const 키 = (ev) => { if (ev.key === "Escape") 끝(단추들[단추들.length - 1][2]); };
      o.addEventListener("keydown", 키);
      줄.onclick = (ev) => { const b = ev.target.closest("[data-i]"); if (b) 끝(단추들[Number(b.dataset.i)][2]); };
      줄.querySelector("button").focus();
    });
  }
  function 상태알림(t, 종류 = "") { 그.상태글 = t; 그.상태종류 = 종류; const s = $("g1st"); if (s) { s.textContent = t; s.title = t; s.className = `mst${종류 === "ng" || 종류 === "보냄실패" ? " ng" : ""}`; } }

  // ---------------------------------------------------------------- 그리기(옆 기둥·도구·목록·판정표)
  function 옆그리기() {
    const v = 그.값;
    const 노트 = v ? v.노트 : null;
    $("g1notettl").textContent = 노트 && 노트.있음 ? `캐릭터 노트 · ${노트.확인됨 ? "설정 확인함" : "설정 확인 전"}` : "캐릭터 노트";
    $("g1notettl").title = 노트 ? 노트.경로 : "";
    if (!노트) $("g1note").innerHTML = `<span class="hint">불러오는 중…</span>`;
    else if (!노트.있음) $("g1note").innerHTML = `<span class="wa">캐릭터 노트 없음</span><span class="hint">Claude 앱에서 컨셉·헤어·의상을 알려 주세요(또는 캐릭터 고르기의 "새 캐릭터 입력"). ${글(노트.경로)}</span>`;
    else {
      const 줄 = 노트.설정.filter((x) => x.항목 !== "비율").slice(0, 8);
      $("g1note").innerHTML = `<div class="kv g1kv">${줄.map((x) => `<div title="${글(x.항목)}">${글(x.항목)}</div><div title="${글(`${x.조건} — ${x.상태}`)}">${글(x.조건)}<span class="hint">${글(x.상태)}</span></div>`).join("")}</div>` +
        (노트.설정.length > 줄.length + 1 ? `<span class="hint">그 밖 ${노트.설정.length - 줄.length - 1}줄 — ${글(노트.경로)}</span>` : "");
    }
    const 요 = v && v.요청문 && v.요청문[그.보는것 === "기준" ? "기준" : "시트"];
    $("g1req").innerHTML = !v ? "" : !요 ? `<span class="hint">아직 조립하지 않았습니다. '생성'을 누르면 서버가 조립합니다(사람이 직접 쓰지 않음).</span>`
      : `<details class="g1det"><summary>${글(그.보는것 === "기준" ? "기준 그림" : "4방향 시트")} 요청문 — 한국어·영어 나란히 펼쳐 보기</summary>` +
        `<div class="g1two"><div><div class="ttl">한국어</div><pre>${글(요.한국어)}</pre></div><div><div class="ttl">영어 (Codex에 넘김)</div><pre>${글(요.영어)}</pre></div></div></details>` +
        `<span class="hint" title="${글(요.경로)}">사람이 직접 쓰지 않음 · ${글(요.경로)}</span>`;
    $("g1seg").innerHTML = ["기준", "시트", "네장"].map((k) => `<button type="button" data-k="${k}" class="${그.보는것 === k ? "on" : ""}" aria-pressed="${그.보는것 === k}">${보기이름[k]}</button>`).join("");
    const 종류 = 그.보는것 === "기준" ? "기준" : "시트";
    const 목록 = 같은종류(종류);
    const g = 지금그림();
    $("g1ver").innerHTML = 목록.length > 1
      ? `<button type="button" class="tb" data-ver="1"${(그.판[종류] || 0) >= 목록.length - 1 ? " disabled title=\"가장 오래된 판입니다\"" : ' title="앞 판"'}>‹ 앞 판</button><span class="hint">${글(g ? g.번호 : "")} (${목록.length - (그.판[종류] || 0)}/${목록.length})</span><button type="button" class="tb" data-ver="-1"${!(그.판[종류] || 0) ? " disabled title=\"가장 최근 판입니다\"" : ' title="뒤 판"'}>뒤 판 ›</button>`
      : "";
  }

  function 도구그리기() {
    const 이유 = 칠못함이유();
    const 다른 = ((그.값 && 그.값.다른캐릭터) || []);
    const 단 = (k, t, 키, 켜짐, 막음 = "") => `<button type="button" class="tb${켜짐 ? " on" : ""}" data-t="${k}" aria-pressed="${Boolean(켜짐)}"${막음 ? " disabled" : ""} title="${글(막음 ? `${t} — ${막음}` : t)}">${글(t)}${키 ? `<span class="k">${키}</span>` : ""}</button>`;
    $("g1tools").innerHTML =
      `<div class="tgrp">${단("보기", "보기", "V", 그.도구 === "보기")}${단("붓", "붓", "B", 그.도구 === "붓", 이유)}${단("지우개", "지우개", "E", 그.도구 === "지우개", 이유)}</div>` +
      `<div class="tgrp">${단("손", "손 확대", "", 그.띠 === "손띠")}${단("발", "발 확대", "", 그.띠 === "발띠")}${단("맞춤", "처음 자리", "F", false)}</div>` +
      `<div class="tgrp">${단("기준나란히", "기준 그림과 나란히", "", 그.나란히 === "기준", 그.보는것 === "기준" ? "기준 그림을 보는 중입니다" : 같은종류("기준").length ? "" : "기준 그림이 없습니다")}` +
      `<label class="g1pick${그.나란히.startsWith("캐릭터:") ? " on" : ""}" title="다른 캐릭터와 나란히(같은 게임으로 보이는가)"><select id="g1other" aria-label="다른 캐릭터와 나란히"${다른.length ? "" : " disabled"}>` +
      `<option value="">다른 캐릭터와 나란히${다른.length ? "" : " (기준 그림 있는 캐릭터 없음)"}</option>${다른.map((c) => `<option value="캐릭터:${글(c.이름)}"${그.나란히 === `캐릭터:${c.이름}` ? " selected" : ""}>${글(c.이름)}와 나란히</option>`).join("")}</select></label></div>`;
    $("g1kind").innerHTML = ((그.값 && 그.값.처리종류) || []).map((k) => `<option${k === 그.칠할종류 ? " selected" : ""}>${글(k)}</option>`).join("");
    칸.classList.toggle("painting", 그.도구 !== "보기" && !이유);
  }

  function 목록그리기() {
    if (!뿌리.isConnected) return;
    const 목 = $("g1list");
    목.innerHTML = 그.표시.length ? 그.표시.map((m) => {
      const g = m.자리.그림;
      const 설명 = `${g.파일.split("/").pop()} · 범위 ${g.범위[0].join(",")}–${g.범위[1].join(",")}${m.메모 ? ` · ${m.메모}` : ""}`;
      return `<div class="mrow${m.번호 === 그.고른 ? " on" : ""}" data-n="${글(m.번호)}" role="button" tabindex="0" title="${글(`${m.번호} ${m.종류} · ${g.파일} · ${설명}`)}">` +
        `<span class="mk">${글(m.번호)}</span><span class="who">사용자</span><span class="desc">${글(설명)}</span><span class="mtag${m.종류 === "기타" && !m.메모 ? " ng" : ""}">${글(m.종류)}</span></div>`;
    }).join("") : `<div class="mempty">아직 표시가 없습니다. 붓(B)을 들고 그림 위 이상한 곳을 칠하세요. 칠할 종류를 먼저 고르면 그 종류로 적힙니다(고르지 않으면 "기타" — 메모 필요).</div>`;
    const 고른 = 그.표시.find((m) => m.번호 === 그.고른);
    const d = $("g1detail");
    d.hidden = !고른;
    if (고른) {
      d.innerHTML = `<div class="ttl">${글(고른.번호)} 고친 것 적기</div><div class="drow"><span class="mlab">종류</span><select class="g1sel" id="g1mkind">${그.값.처리종류.map((k) => `<option${k === 고른.종류 ? " selected" : ""}>${글(k)}</option>`).join("")}</select>` +
        `<button type="button" class="tb" id="g1del">표시 지우기</button><span class="hint">이 번호를 고른 채 칠하면 같은 번호에 더해집니다.</span></div>` +
        `<label class="dmemo"><span class="mlab">메모${고른.종류 === "기타" ? " (기타는 꼭)" : " (선택)"}</span><textarea id="g1memo" rows="2" maxlength="4000">${글(고른.메모)}</textarea></label>`;
    }
    const 보냄 = 그.묶음.length ? `보낸 묶음 ${그.묶음.length}개 · 마지막 ${그.묶음[그.묶음.length - 1].묶음상태}` : "";
    if (그.상태종류 !== "보냄실패" && 그.상태종류 !== "ng" && !그.상태글) 상태알림(보냄);
    else 상태알림(그.상태글, 그.상태종류);
  }

  function 판정그리기(상태노트) {
    const v = 그.값;
    const g = 지금그림();
    let html = "";
    if (v) {
      const 판정 = g && g.판정;
      const 줄 = v.범주.map((k) => {
        const x = 판정 && 판정[k];
        const 칸 = !x ? `<td class="hint">에이전트 검수 전</td><td></td>` : `<td class="${{"충족": "ok", "보완 필요": "ng", "사람 확인": "wa"}[x.판정] || ""}">${글(x.판정)}</td><td title="${글(x.근거)}">${글(x.근거)}</td>`;
        return `<tr><td title="${글(k)}">${글(k)}</td>${칸}</tr>`;
      }).join("");
      const 범위 = v.등신범위;
      const 등신 = g && g.등신 != null ? g.등신 : null;
      const 밖 = 등신 == null || 등신 < 범위[0] || 등신 > 범위[1];
      const 등신줄 = g && g.종류 === "기준" ? `<tr><td>등신</td><td class="${!판정 ? "hint" : 밖 ? "ng" : "ok"}">${!판정 ? "에이전트 검수 전" : 등신 == null ? "재지 않음" : `${글(등신)}${밖 ? " — 범위 밖" : ""}`}</td><td title="${글(g.등신근거 || "")}">${글(g.등신근거 || `범위 ${범위[0]}~${범위[1]}(결과에 맞춰 넓히지 않음)`)}</td></tr>` : "";
      const 머리 = g ? `${보기이름[그.보는것 === "기준" ? "기준" : "시트"]} ${g.번호}의 자가 검수${g.탈락 ? " · <span class=\"ng\">탈락</span>" : ""}${g.조건미달승인 && g.조건미달승인.length ? " · <span class=\"wa\">조건 미달로 승인</span>" : ""}` : "자가 검수";
      html = `<table class="t"><caption>${머리}</caption><tr><th>검사 범주</th><th>판정</th><th>근거</th></tr>${줄}${등신줄}</table>`;
      if (g && g.TRIPO폴더) html += `<div class="hint ok" title="${글(g.검사 || "")}">TRIPO 입력: ${글(g.TRIPO폴더)} · ${g.검사통과 ? "검사 통과" : "검사 실패"}</div>`;
      if (v.모자람 && v.모자람.length) html += `<div class="hint" title="${글(v.모자람.join("\n"))}">이 단계가 끝나려면: ${글(v.모자람.join(" · "))}</div>`;
    }
    $("g1more").innerHTML = html + (상태노트 || "");
  }

  let 상태노트html = "";
  function 그리기() {
    if (!뿌리.isConnected) return;
    옆그리기(); 도구그리기(); 목록그리기(); 판정그리기(상태노트html); 그리기캔버스(); 보내기그리기();
    if (window.결정 && window.결정.그리기) window.결정.그리기();
  }

  // ---------------------------------------------------------------- 이벤트(그림 칸 밖)
  뿌리.addEventListener("click", (ev) => {
    const s = ev.target.closest("#g1seg [data-k]");
    if (s) { 그.보는것 = s.dataset.k; if (그.나란히 === "기준" && 그.보는것 === "기준") 그.나란히 = ""; 그.카메라 = null; 그리기(); return; }
    const vv = ev.target.closest("[data-ver]");
    if (vv && !vv.disabled) { const 종류 = 그.보는것 === "기준" ? "기준" : "시트"; 그.판[종류] = (그.판[종류] || 0) + Number(vv.dataset.ver); 그.카메라 = null; 그리기(); return; }
    const t = ev.target.closest("[data-t]");
    if (t && !t.disabled) { 도구누름(t.dataset.t); return; }
    const r = ev.target.closest(".mrow[data-n]");
    if (r) { 그.고른 = 그.고른 === r.dataset.n ? null : r.dataset.n; 목록그리기(); 그리기캔버스(); return; }
    if (ev.target.closest("#g1del")) {
      기록남기기();
      그.표시 = 그.표시.filter((m) => m.번호 !== 그.고른); 그.고른 = null; 바뀜();
    }
  });
  뿌리.addEventListener("change", (ev) => {
    if (ev.target.id === "g1kind") 그.칠할종류 = ev.target.value;
    else if (ev.target.id === "g1other") { 그.나란히 = ev.target.value; 그.카메라 = null; 그리기(); }
    else if (ev.target.id === "g1mkind") { const m = 그.표시.find((x) => x.번호 === 그.고른); if (m) { 기록남기기(); m.종류 = ev.target.value; 바뀜(); } }
    else if (ev.target.id === "g1memo") { const m = 그.표시.find((x) => x.번호 === 그.고른); if (m && m.메모 !== ev.target.value) { 기록남기기(); m.메모 = ev.target.value; 바뀜(); } }
  });
  뿌리.addEventListener("keydown", (ev) => {
    const r = ev.target.closest(".mrow[data-n]");
    if (r && (ev.key === "Enter" || ev.key === " ")) { ev.preventDefault(); r.click(); }
  });
  function 도구누름(k) {
    if (k === "보기" || k === "붓" || k === "지우개") { 그.도구 = k; 원.hidden = true; }
    else if (k === "손" || k === "발") { 그.띠 = 그.띠 === `${k}띠` ? "" : `${k}띠`; 카메라맞춤(그.띠); }
    else if (k === "맞춤") { 그.띠 = ""; 카메라맞춤(""); }
    else if (k === "기준나란히") { 그.나란히 = 그.나란히 === "기준" ? "" : "기준"; 그.카메라 = null; }
    도구그리기(); 그리기캔버스();
  }
  document.addEventListener("keydown", (ev) => {
    if (!뿌리.isConnected || ev.target.closest("input, textarea, select") || !$("ask2").hidden) return;
    const 키 = ev.key.toLowerCase();
    if ((ev.ctrlKey || ev.metaKey) && (키 === "z" || 키 === "y")) {
      ev.preventDefault();
      const 다시 = 키 === "y" || ev.shiftKey;
      const 에서 = 다시 ? 그.다시 : 그.취소, 로 = 다시 ? 그.취소 : 그.다시;
      if (!에서.length || 칠못함이유() === "다른 탭에서 열려 있습니다") return;
      로.push(JSON.stringify({표시: 그.표시, 다음번호: 그.다음번호}));
      const v = JSON.parse(에서.pop());
      그.표시 = v.표시; 그.다음번호 = v.다음번호;
      if (!그.표시.some((m) => m.번호 === 그.고른)) 그.고른 = null;
      바뀜();
      return;
    }
    if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
    if (키 === "b" && !칠못함이유()) 도구누름("붓");
    else if (키 === "e" && !칠못함이유()) 도구누름("지우개");
    else if (키 === "v") 도구누름("보기");
    else if (키 === "f") 도구누름("맞춤");
  });

  // ---------------------------------------------------------------- 결정 칸 단추(결정.js가 묻는다)
  function 승인막음(g) {
    const v = 그.값;
    if (!v) return "불러오는 중";
    if (v.실행중) return "생성하는 중입니다";
    if (!g) return "볼 그림이 없습니다";
    if (g.실패이유) return "생성에 실패한 판입니다";
    if (g.탈락) return "탈락한 그림입니다";
    if (g.승인 === "승인") return "이미 승인했습니다";
    if (g.승인 === "대체됨") return "다른 판을 승인해 대체된 그림입니다";
    if (!g.판정) return "에이전트 자가 검수(다섯 범주 판정표)가 아직 없습니다";
    if (g.종류 === "시트" && (g.자른것 || []).length !== 4) return "네 장으로 자르지 못했습니다 — 다시 생성하세요";
    if ((g.없는파일 || []).length) return "그림 파일이 없습니다";
    return "";
  }
  function 생성막음(종류) {
    const v = 그.값;
    if (!v) return "불러오는 중";
    if (v.실행중) return "생성하는 중입니다";
    if (!v.노트.있음) return "캐릭터 노트가 없습니다 — Claude 앱에서 컨셉·헤어·의상을 알려 주세요";
    if (종류 === "시트" && !승인된기준()) return "기준 그림을 먼저 승인하세요";
    return "";
  }
  function 단추() {
    const 종류 = 그.보는것 === "기준" ? "기준" : "시트";
    const g = 지금그림();
    const 고쳐 = ["고쳐 줘", "b-fix", "고쳐 줘"];
    if (!g) {
      const 이유 = 생성막음(종류);
      return [[종류 === "기준" ? "생성" : "시트 생성", "b-ok", 이유 ? null : "그림:생성", 이유], 고쳐, ["다시 생성", "b-re", null, "아직 생성한 그림이 없습니다"]];
    }
    const 승이유 = 승인막음(g), 다이유 = 생성막음(종류);
    return [["승인", "b-ok", 승이유 ? null : "그림:승인", 승이유], 고쳐, ["다시 생성", "b-re", 다이유 ? null : "그림:다시", 다이유]];
  }
  async function 누름(값) {
    const 이름 = 그.이름, 종류 = 그.보는것 === "기준" ? "기준" : "시트";
    try {
      if (값 === "그림:생성" || 값 === "그림:다시") {
        const 노트 = 그.값.노트;
        let 설정확인 = 노트.확인됨;
        if (!설정확인) {
          const 표 = `<table class="t"><tr><th>항목</th><th>조건</th><th>상태</th></tr>${노트.설정.map((x) => `<tr><td>${글(x.항목)}</td><td>${글(x.조건)}</td><td class="${/미정/.test(x.상태) ? "wa" : /제안/.test(x.상태) ? "ac" : ""}">${글(x.상태)}</td></tr>`).join("")}</table>`;
          const 답 = await 물어보기("설정 표를 확인해 주세요", `${표}<span class="hint">"에이전트 제안"과 "미정"이 맞는지 보고 생성합니다. 바꿀 것이 있으면 취소하고 Claude 앱에서 말씀해 주세요.</span>`,
            [["확인하고 생성", "b-ok", true], ["취소", "b-re", false]]);
          if (!답) return;
          설정확인 = true;
        }
        const v = await 보내기("/api/그림/생성", {이름, 탭: window.탭id, 종류, 다시: 값 === "그림:다시", 설정확인});
        그.판[종류] = 0;
        상태알림(`생성을 시작했습니다${v.모드 === "가짜" ? "(가짜 실행 — Codex를 부르지 않고 흉내 그림을 만듦)" : "(Codex)"}. 끝나면 알림에 보입니다.`);
      } else if (값 === "그림:승인") {
        const g = 지금그림();
        let v = await 보내기("/api/그림/승인", {이름, 탭: window.탭id, 번호: g.번호});
        if (!v.됨 && v.경고) {
          const 답 = await 물어보기(g.종류 === "기준" && v.경고.some((x) => x.startsWith("등신")) ? "범위 밖입니다. 그래도 승인할까요?" : "보완 필요 판정이 있습니다. 그래도 승인할까요?",
            `<ul class="lack">${v.경고.map((x) => `<li>${글(x)}</li>`).join("")}</ul><span class="hint">결과에 맞춰 범위를 넓히지 않는다는 규칙(SSOT 단계/1_이미지 1-4)이 있습니다. 그래도 승인하면 "조건 미달로 승인"으로 기록하고, 이 단계 끝은 "끝(조건 미달)"이 됩니다.</span>`,
            [["그래도 승인", "b-ok", true], ["취소", "b-re", false]]);
          if (!답) return;
          v = await 보내기("/api/그림/승인", {이름, 탭: window.탭id, 번호: g.번호, 그래도: true});
        }
        상태알림(v.TRIPO폴더 ? `승인함 — 네 장을 ${v.TRIPO폴더}에 두었습니다(TRIPO 입력 검사 통과).` : `${g.번호} 승인함.${g.종류 === "기준" ? " 이제 '4방향 시트'에서 시트 생성을 누를 수 있습니다." : ""}`);
      }
    } catch (e) {
      상태알림(`${e instanceof TypeError ? "서버와 연결 끊김" : e.message}`, "ng");
    } finally {
      if (이름 === 그.이름) await 다시읽기();
      if (window.결정) window.결정.다시읽기();
      if (typeof 맥박 === "function") 맥박();
    }
  }

  // ---------------------------------------------------------------- 새 캐릭터 입력
  function 입력그리기(항목, 필수) {
    입력뿌리.innerHTML = `<div class="note g1form" data-순서="단계마다 더 있는 것"><div class="ttl">새 캐릭터 입력 — SSOT/13_새캐릭터_입력항목.md의 목록</div>` +
      항목.map((n) => {
        const 큰 = !["이름"].includes(n);
        const 도움 = {"이름": "폴더 이름으로 씀(한글·영문·숫자·밑줄)", "참고 그림": "가진 그림 파일 경로(줄마다 하나). 파일은 '파일 가져오기'로도 넣을 수 있음", "기타": "위에 없는 요청 전부 — 빠짐없이 요청문에 들어감", "체형·인상": "말로 묘사(숫자를 강요하지 않음)"}[n] || (필수.includes(n) ? "" : "비우면 에이전트가 컨셉에 맞게 제안");
        return `<label class="g1f"><span class="mlab">${글(n)}${필수.includes(n) ? ' <b class="ng">*</b>' : ""}</span>` +
          (큰 ? `<textarea rows="2" data-f="${글(n)}" maxlength="4000"></textarea>` : `<input data-f="${글(n)}" maxlength="40">`) +
          (도움 ? `<span class="hint">${글(도움)}</span>` : "") + `</label>`;
      }).join("") +
      `<div class="btns2"><button type="button" class="btn b-ok" id="g1fsend" disabled>보내기</button><button type="button" class="btn b-re" id="g1fcancel">취소</button></div><span class="hint" id="g1fhint">* 표시 칸(이름·컨셉·헤어·의상)을 채우면 보내기를 누를 수 있습니다. 비율은 게임 공통이라 묻지 않습니다.</span></div>` +
      `<div class="human" data-순서="사람이 하는 일"><b>사람이 하는 일</b> · 컨셉·헤어·의상을 적고 보내기. 그다음 Claude 앱에서 "보냈어" — 에이전트가 캐릭터 노트를 만들고 설정 표를 띄웁니다.</div>`;
    const 확인 = () => {
      const 빈 = 필수.filter((n) => !입력뿌리.querySelector(`[data-f="${n}"]`).value.trim());
      const b = $("g1fsend");
      b.disabled = Boolean(빈.length);
      b.title = 빈.length ? `비어 있는 칸: ${빈.join(", ")}` : "입력을 파일로 저장합니다";
    };
    입력뿌리.oninput = 확인;
    입력뿌리.onclick = async (ev) => {
      if (ev.target.id === "g1fcancel") { window.새캐릭터입력닫기 && window.새캐릭터입력닫기(null); return; }
      if (ev.target.id !== "g1fsend" || ev.target.disabled) return;
      const 항목들 = {};
      for (const el of 입력뿌리.querySelectorAll("[data-f]")) 항목들[el.dataset.f] = el.value;
      ev.target.disabled = true;
      try {
        const v = await 보내기("/api/그림/새캐릭터", {항목들});
        window.새캐릭터입력닫기 && window.새캐릭터입력닫기(v.이름);
      } catch (e) {
        const h = $("g1fhint"); h.textContent = `보내지 못함: ${e.message}`; h.className = "hint ng";
        ev.target.disabled = false;
      }
    };
    확인();
  }

  // ---------------------------------------------------------------- 바깥(앱.js·결정.js)에 내놓는 것
  let 읽기번호 = 0;
  async function 다시읽기() {
    const 이름 = 그.이름, 번호 = ++읽기번호;
    if (!이름) return;
    try {
      const v = await 받기(`/api/그림?이름=${encodeURIComponent(이름)}`);
      if (번호 !== 읽기번호 || 이름 !== 그.이름) return;
      그.값 = v;
      if (!그.칠할종류 || !v.처리종류.includes(그.칠할종류)) 그.칠할종류 = v.처리종류[v.처리종류.length - 1];
    } catch (e) {
      if (번호 !== 읽기번호) return;
      if (!(e instanceof TypeError)) 상태알림(`1단계를 읽지 못함: ${e.message}`, "ng");
    }
    그리기();
  }
  function 붙이기(자리, 이름, 상태노트) {
    상태노트html = 상태노트 || "";
    if (입력뿌리.isConnected) 입력뿌리.remove();
    const 새 = 이름 !== 그.이름;
    if (새) {
      if (그.미저장) 저장하기();
      Object.assign(그, {이름, 값: null, 판: {기준: 0, 시트: 0}, 나란히: "", 표시: [], 묶음: [], 고른: null, 취소: [], 다시: [],
        상태글: "", 상태종류: "", 바깥: null, 카메라: null, 띠: "", 미저장: false});
    }
    자리.replaceWith(뿌리);
    그리기();
    if (새) { 다시읽기(); 표시읽기(); }
  }
  function 떼기() {
    if (그.미저장) 저장하기();
    if (뿌리.isConnected) 뿌리.remove();
    if (입력뿌리.isConnected) 입력뿌리.remove();
  }
  function 입력붙이기(자리, 항목, 필수) {
    떼기();
    자리.replaceWith(입력뿌리);
    입력그리기(항목, 필수);
  }
  function 붙음() { return 뿌리.isConnected; }
  let 마지막잠금 = null;
  function 바깥바뀜(값, 표시값) {
    if (!붙음()) return;
    if (값 !== undefined && 값 !== 그.바깥) { const 처음 = 그.바깥 === null; 그.바깥 = 값; if (!처음) 다시읽기(); }
    if (표시값 !== undefined && 표시값 !== 그.바깥표시) { const 처음 = 그.바깥표시 === null; 그.바깥표시 = 표시값; if (!처음) 표시읽기(); }
    if (그.미저장) 저장하기();
    if (document.body.dataset.잠금 !== 마지막잠금) { 마지막잠금 = document.body.dataset.잠금; 도구그리기(); 보내기그리기(); }
  }
  window.그림단계 = {붙이기, 떼기, 입력붙이기, 붙음, 단추, 누름, 바깥바뀜, 보내기그리기, 다시읽기, 상태: 그,
    // 시험용: 그림 화소 좌표(파일 x, y)에 반지름 r(화소)로 한 번 칠한다
    시험_칠: (파일, x, y, r) => {
      const p = 마지막판.find((q) => q.경로 === 파일 && !q.참고);
      if (!p || !그.카메라) return null;
      const 화면 = {offsetX: (p.x + x * p.k) * 그.카메라.s + 그.카메라.ox, offsetY: (p.y + y * p.k) * 그.카메라.s + 그.카메라.oy};
      const 전붓 = 그.붓; 그.붓 = r * p.k * 그.카메라.s;
      const 전도구 = 그.도구; 그.도구 = "붓";
      const 시작 = 칠시작(화면);
      그.붓 = 전붓; 그.도구 = 전도구;
      바뀜();
      return 시작 && 시작.표시 ? 시작.표시.번호 : null;
    }};
  window.dispatchEvent(new Event("그림단계준비"));
})();
