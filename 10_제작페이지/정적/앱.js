// 가마우지 제작 페이지 — 화면 틀(W00)
// 서버(127.0.0.1)에만 요청한다. 색·크기는 CSS(디자인 토큰)에만 있고 여기에는 숫자 크기를 쓰지 않는다.
"use strict";

const 상태글 = {"끝": "done", "끝(조건 미달)": "done", "결정 대기": "wait", "준비됨": "ready", "입력 없음": "none", "진행 중": "busy", "막힘": "blocked", "알 수 없음": "unknown"};
const 맥박간격 = 3000;   // 서버에 살아 있음을 알리는 간격(ms)
const 탭id = (crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2));
window.탭id = 탭id;   // 칠하기.js가 저장할 때 서버에 알린다(다른 탭은 저장하지 않음)

const 화면 = {
  정보: null,      // /api/정보
  캐릭터: [],      // /api/캐릭터 의 목록
  지금캐릭터: null,
  보기: null,      // /api/상태 결과
  지금단계: 0,     // 0부터
  끊김: false,
  주인: true,
  준비: false,     // 처음 읽기(정보·캐릭터 목록)를 마쳤는가
  바뀜: {},        // 캐릭터마다 마지막으로 반영한 {상태, 작업본} 수정 시각
};

const $ = (id) => document.getElementById(id);
const 글 = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));

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

function 오류띠(메시지) {
  const b = $("b-err");
  b.textContent = 메시지 || "";
  b.hidden = !메시지;
}

// ---------------------------------------------------------------- 그리기

function 윗줄그리기() {
  const 정보 = 화면.정보;
  const a = $("addr");
  const 이PC = ["127.0.0.1", "localhost"].includes(location.hostname) && 정보 && 정보.주소 === "127.0.0.1";
  a.classList.toggle("local", true);
  a.classList.toggle("bad", !이PC);
  a.textContent = 이PC ? `● ${정보.주소}:${정보.포트} (이 PC만)` : `● ${location.host} — 이 PC 밖에서 열려 있음!`;
  a.title = 이PC ? "이 PC에서만 열리는 주소입니다" : "서버가 127.0.0.1이 아닌 주소에 열려 있습니다";

  const 줄 = 화면.보기 && 화면.보기.단계[화면.지금단계];
  $("curstep").textContent = 줄 ? `${줄.번호}단계 ${줄.이름}` : "단계 —";
  $("curstep").title = $("curstep").textContent;
  $("charname").textContent = 화면.지금캐릭터 || "고르세요";
  $("charname").parentElement.title = `캐릭터: ${화면.지금캐릭터 || "없음"}`;
}

function 잔액그리기(잔액) {
  const t = $("tripo");
  if (잔액 && 잔액.잔액 != null) {
    const 시각 = 잔액.시각 ? String(잔액.시각).replace("T", " ").slice(5, 16) : "시각 모름";
    t.textContent = `TRIPO 잔액 ${잔액.잔액}${잔액.가짜 ? "(가짜)" : ""} · ${시각}`;
    t.title = `서버가 마지막으로 기록한 잔액(${잔액.시각 || "시각 모름"}). 바깥에 묻지 않습니다.`;
  } else {
    t.textContent = "TRIPO 잔액 알 수 없음";
    t.title = "서버에 기록된 잔액이 없습니다. 유료 실행 전후에 기록됩니다.";
  }
}

function 캐릭터고르기그리기() {
  const s = $("char");
  s.innerHTML = (화면.지금캐릭터 ? "" : `<option value="" selected>고르세요</option>`) +
    화면.캐릭터.map((c) => `<option value="${글(c.이름)}"${c.이름 === 화면.지금캐릭터 && !화면.입력폼 ? " selected" : ""}>${글(c.이름)}${c.상태파일있음 ? "" : " (기록 없음)"}</option>`).join("") +
    `<option value="__새캐릭터입력__"${화면.입력폼 ? " selected" : ""}>＋ 새 캐릭터 입력…</option>`;   // W09: 1단계 새 캐릭터 입력(2부 13절)
}

function 단계목록그리기() {
  const 단계 = 화면.보기 ? 화면.보기.단계 : 화면.정보.단계목록.map((d, i) => ({번호: i + 1, 이름: d.이름, 상태: 화면.불러오는중 ? "불러오는 중" : "—", 표시: []}));
  $("steps").innerHTML = 단계.map((d, i) => {
    const 상태 = d.상태;
    // 표시 종류마다 번호 동그라미 테두리를 다르게: 앞 단계가 바뀜(주황 실선) · 캐릭터 노트 없음(주황 점선) · 앞 단계 안 거침(회색 점선)
    const 표시칸 = d.표시.includes("앞 단계가 바뀜") ? " fl-changed" : d.표시.includes("캐릭터 노트 없음") ? " fl-note" : d.표시.includes("앞 단계 안 거침") ? " fl-skip" : "";
    const 풀이 = [d.이름, 상태, ...(d.표시 || []), d.이유 || ""].filter(Boolean).join(" · ");
    return `<button type="button" class="step${i === 화면.지금단계 ? " on" : ""}" data-i="${i}" title="${글(풀이)}"${i === 화면.지금단계 ? ' aria-current="step"' : ""}>` +
      `<span class="n${표시칸}">${d.번호}</span><span class="t">${글(d.이름)}</span><span class="s ${상태글[d.상태] || "unknown"}">${글(상태)}</span></button>`;
  }).join("");
}

function 가운데그리기() {
  const 보기 = 화면.보기;
  const 줄 = 보기 && 보기.단계[화면.지금단계];
  const 이름 = 줄 ? 줄.이름 : 화면.정보.단계목록[화면.지금단계].이름;
  $("title").textContent = `${화면.지금단계 + 1}. ${이름}`;
  const 출처 = 줄 && 줄.출처 ? `출처: ${줄.출처}` : "출처 없음";
  $("src").textContent = 출처;
  $("src").title = 출처;
  const 폴더 = 보기 ? 보기.폴더 : 화면.지금캐릭터 ? `01_캐릭터/${화면.지금캐릭터}/` : "";
  $("folder").textContent = 폴더;
  $("folder").title = 폴더;

  let html = "";
  if (!보기 && 화면.불러오는중) {
    html = `<div class="empty">불러오는 중…<span class="hint">${글(화면.지금캐릭터)}</span></div>`;
  } else if (!보기) {
    html = `<div class="empty">캐릭터를 고르세요.<span class="hint">윗줄의 "캐릭터"에서 고릅니다.</span></div>`;
  } else if (!보기.있음) {
    html = `<div class="empty">이 캐릭터에는 아직 제작 페이지 기록(상태.json)이 없습니다.<button type="button" class="tb" id="makenew">새 캐릭터로 만들기</button></div>`;
  } else {
    const 상태 = 줄.상태;
    const 입력 = 줄.입력.length
      ? `<div class="inlist">${줄.입력.map((x) => `<div class="${줄.없는입력.includes(x) ? "missing" : ""}">${글(x)}${줄.없는입력.includes(x) ? " — 파일 없음" : ""}</div>`).join("")}</div>`
      : "없음";
    const 해시 = 보기.작업본
      ? `${글(보기.작업본해시 || "파일 없음")}${보기.작업본해시_파일 && 보기.작업본해시 && 보기.작업본해시_파일 !== 보기.작업본해시 ? ` <span class="wa">(상태.json에는 ${글(보기.작업본해시_파일)} — 작업본이 바뀜)</span>` : ""}`
      : "작업본 없음";
    html = `<div class="note" data-순서="단계마다 더 있는 것"><div class="ttl">단계 상태</div><div class="kv">` +
      `<div>상태</div><div class="${{"끝": "ok", "끝(조건 미달)": "ok", "결정 대기": "wa", "막힘": "ng", "알 수 없음": "ng"}[줄.상태] || ""}">${글(상태)}${줄.이유 ? ` — ${글(줄.이유)}` : ""}</div>` +
      `<div>입력</div><div>${입력}</div>` +
      `<div>출처</div><div>${글(줄.출처 || "없음")}</div>` +
      `<div>바뀐 시각</div><div>${글(줄.바뀐시각 || "—")}</div>` +
      `<div>표시</div><div>${줄.표시.length ? `<span class="wa">${글(줄.표시.join(" · "))}</span>` : "없음"}${줄.표시.includes("방향 확인 필요") ? ` <button type="button" class="tb" id="pickdir" title="가져온 모델의 네 방향 그림에서 얼굴 쪽을 고릅니다">앞 고르기</button>` : ""}</div>` +
      `<div>작업본해시</div><div>${해시}</div>` +
      `</div></div>`;
    // 모델이 생긴 뒤의 단계(2~11)는 3D 보기(W02)를 위에 둔다. 1단계는 그림 화면(W09, 그림단계.js가 상태 상자를 판정표 아래에 넣음)
    if (화면.지금단계 === 0) { 그림상태html = html.replace(' data-순서="단계마다 더 있는 것"', ""); html = `<div id="g1slot"></div>`; }
    else html = 모델단계(화면.지금단계) ? `<div id="v3slot"></div><div id="mkslot"></div>` + html
      : html + `<div class="empty">이 단계의 작업 화면은 아직 만들지 않았습니다.<span class="hint">지금은 단계를 고르고 상태만 봅니다.</span></div>`;
  }
  if (화면.입력폼) { html = `<div id="g1slot"></div>`; $("title").textContent = "새 캐릭터 입력"; $("src").textContent = "SSOT/13_새캐릭터_입력항목.md"; $("folder").textContent = ""; }
  if (보기 && 보기.오류) html = `<div class="note ng">${글(보기.오류)}</div>` + html;
  $("body").innerHTML = html;
  그림붙이기();
  보기붙이기();
  표시붙이기();
  결정붙이기();
  const pd = $("pickdir");   // W08: 가져온 모델의 앞을 모를 때
  if (pd) pd.addEventListener("click", () => window.가져오기 && window.가져오기.방향열기(화면.지금단계 + 1));
  const m = $("makenew");
  if (m) m.addEventListener("click", () => 새캐릭터묻기(화면.지금캐릭터));
}

// 1단계 그림 화면(정적/그림단계.js, W09)과 새 캐릭터 입력 칸
let 그림상태html = "";
function 그림붙이기() {
  if (!window.그림단계) return;
  const 자리 = $("g1slot");
  if (!자리) { window.그림단계.떼기(); return; }
  if (화면.입력폼) window.그림단계.입력붙이기(자리, 새캐릭터항목, 새캐릭터필수);
  else window.그림단계.붙이기(자리, 화면.보기.이름, 그림상태html);
}
window.addEventListener("그림단계준비", 그림붙이기);
// SSOT/13_새캐릭터_입력항목.md "항목" 표(서버 그림단계.py와 같은 목록)
const 새캐릭터항목 = ["이름", "컨셉", "헤어", "의상", "양말·신발", "체형·인상", "표정", "뺄 것", "참고 그림", "기타"];
const 새캐릭터필수 = ["이름", "컨셉", "헤어", "의상"];
function 새캐릭터입력열기() {
  화면.입력폼 = true;
  캐릭터고르기그리기();
  가운데그리기();
}
window.새캐릭터입력닫기 = async (새이름) => {
  화면.입력폼 = false;
  if (새이름) {
    try { 화면.캐릭터 = (await 받기("/api/캐릭터")).캐릭터; } catch (e) {}
    화면.지금단계 = 0;
    await 캐릭터바꾸기(새이름);
  } else 모두그리기();
};

// 3D 보기(정적/보기3d.js, 모듈이라 늦게 뜰 수 있음). 화면을 다시 그려도 같은 보기(WebGL)를 다시 붙인다.
const 모델단계 = (i) => i >= 1;   // 2단계(모델 생성)부터 3D 보기(W10: 받은 모델을 형태만으로)
function 보기붙이기() {
  const 자리 = $("v3slot");
  if (자리 && window.보기3d && 화면.보기) window.보기3d.붙이기(자리, 화면.보기.이름, 화면.보기.작업본해시 || "");
  uv붙이기();
  부위붙이기();
  생성붙이기();
  메시붙이기();
  텍스처붙이기();
  리깅붙이기();
  동작붙이기();
}
// 2·4·5·6단계 옆 기둥(정적/생성단계.js, W10). 3D 보기의 보기 줄 오른쪽 끝(UV 그림 다음)에 붙는다
function 생성붙이기() {
  if (!window.생성단계) return;
  const 붙음 = Boolean(window.보기3d && window.보기3d.내부.뿌리.isConnected && 화면.보기 && 화면.보기.있음);
  if (!붙음) { window.생성단계.떼기(); return; }
  window.생성단계.붙이기(화면.보기.이름, 화면.지금단계 + 1);
}
window.addEventListener("생성단계준비", 생성붙이기);
// 3단계 옆 기둥(정적/메시단계.js, W11). 붙는 자리는 2·4·5·6단계와 같다
function 메시붙이기() {
  if (!window.메시단계) return;
  const 붙음 = Boolean(window.보기3d && window.보기3d.내부.뿌리.isConnected && 화면.보기 && 화면.보기.있음);
  if (!붙음) { window.메시단계.떼기(); return; }
  window.메시단계.붙이기(화면.보기.이름, 화면.지금단계 + 1);
}
window.addEventListener("메시단계준비", 메시붙이기);
// 7단계 옆 기둥(정적/텍스처단계.js, W12). UV 그림 다음에 붙는다
function 텍스처붙이기() {
  if (!window.텍스처단계) return;
  const 붙음 = Boolean(window.보기3d && window.보기3d.내부.뿌리.isConnected && 화면.보기 && 화면.보기.있음);
  if (!붙음) { window.텍스처단계.떼기(); return; }
  window.텍스처단계.붙이기(화면.보기.이름, 화면.지금단계 + 1);
}
window.addEventListener("텍스처단계준비", 텍스처붙이기);
// 8·9단계(정적/리깅단계.js, W13): 옆 기둥, 9단계는 도구 줄 끝에 시간 막대와 표시 목록 아래 후보 비교
function 리깅붙이기() {
  if (!window.리깅단계) return;
  const 붙음 = Boolean(window.보기3d && window.보기3d.내부.뿌리.isConnected && 화면.보기 && 화면.보기.있음);
  if (!붙음) { window.리깅단계.떼기(); return; }
  window.리깅단계.붙이기(화면.보기.이름, 화면.지금단계 + 1);
}
window.addEventListener("리깅단계준비", 리깅붙이기);
// 10·11단계 옆 기둥(정적/동작단계.js, W14). 10단계의 시간 막대·칠하기는 리깅단계.js가 같이 붙인다
function 동작붙이기() {
  if (!window.동작단계) return;
  const 붙음 = Boolean(window.보기3d && window.보기3d.내부.뿌리.isConnected && 화면.보기 && 화면.보기.있음);
  if (!붙음) { window.동작단계.떼기(); return; }
  window.동작단계.붙이기(화면.보기.이름, 화면.지금단계 + 1);
}
window.addEventListener("동작단계준비", 동작붙이기);
// 부위(정적/부위.js, W05). 3D 보기가 붙은 단계에서 도구 줄에 "부위 ▾"를 끼우고 캐릭터의 부위.json을 읽는다.
function 부위붙이기() {
  if (!window.부위 || !window.보기3d) return;
  window.부위.붙이기(화면.보기 && 화면.보기.있음 ? 화면.보기.이름 : null);
}
window.addEventListener("부위준비", 부위붙이기);
window.addEventListener("보기3d준비", 보기붙이기);

// UV 그림 나란히(정적/uv그림.js, W04). 6·7단계에서 3D 보기 오른쪽에 붙는다(어느 단계인지는 uv그림.js가 정함).
function uv붙이기() {
  if (!window.uv그림) return;
  const 붙음 = Boolean(window.보기3d && window.보기3d.내부.뿌리.isConnected && 화면.보기);
  const d = 화면.정보 && 화면.정보.단계목록 && 화면.정보.단계목록[화면.지금단계];
  window.uv그림.붙이기(붙음 && d ? d.번호 : 0);
}
window.addEventListener("uv그림준비", () => { uv붙이기(); 생성붙이기(); 텍스처붙이기(); });

// 칠하기와 표시(정적/칠하기.js, W03). 칠하는 단계(처리 목록이 있는 단계)에서 표시 목록을 보기 아래에 붙인다.
function 표시붙이기() {
  if (!window.칠하기) return;
  const 자리 = $("mkslot");
  if (!자리 || !화면.보기 || !화면.보기.있음) { window.칠하기.떼기(); return; }
  const d = 화면.정보.단계목록[화면.지금단계];
  window.칠하기.작업본바뀜(화면.보기.작업본해시 || "");
  window.칠하기.붙이기(자리, 화면.보기.이름, d.번호, d.처리 || [], 화면.정보.메모필수, 화면.정보.취소한도);
}
window.addEventListener("칠하기준비", 표시붙이기);

// 결정 칸(정적/결정.js, W06). 에이전트 알림·결정 단추·되돌리기. 상태.json이 있는 캐릭터에서만.
function 결정붙이기() {
  if (!window.결정) return;
  const 있음 = 화면.보기 && 화면.보기.있음;
  window.결정.붙이기(있음 ? 화면.보기.이름 : null, 있음 ? 화면.지금단계 + 1 : 0);
}
window.addEventListener("결정준비", 결정붙이기);

function 모두그리기() {
  윗줄그리기();
  캐릭터고르기그리기();
  단계목록그리기();
  가운데그리기();
}

// ---------------------------------------------------------------- 동작

// 캐릭터를 빨리 바꿀 때 늦게 도착한 옛 응답이 화면을 덮지 않도록, 요청마다 번호를 붙이고 마지막 번호의 응답만 쓴다.
let 요청번호 = 0;
async function 상태불러오기() {
  const 이름 = 화면.지금캐릭터;
  const 번호 = ++요청번호;
  if (!이름) { 화면.보기 = null; return true; }
  try {
    const v = await 받기(`/api/상태?이름=${encodeURIComponent(이름)}`);
    if (번호 !== 요청번호 || 이름 !== 화면.지금캐릭터) return false;
    화면.보기 = v;
    화면.바뀜[이름] = {상태: v.수정시각 || 0, 작업본: (화면.바뀜[이름] || {}).작업본};
    오류띠("");
  } catch (e) {
    if (번호 !== 요청번호 || 이름 !== 화면.지금캐릭터) return false;
    // 읽지 못하면 빈 "입력 없음" 대신 모든 단계를 "알 수 없음"과 이유로 보인다
    const 이유 = `상태를 읽지 못함: ${e.message}`;
    화면.보기 = {이름, 폴더: `01_캐릭터/${이름}/`, 있음: true, 노트있음: true, 오류: 이유, 작업본: "", 작업본해시: "", 작업본해시_파일: "",
      단계: 화면.정보.단계목록.map((d) => ({번호: d.번호, 이름: d.이름, 상태: "알 수 없음", 이유, 입력: [], 없는입력: [], 출처: null, 바뀐시각: null, 표시: []}))};
    오류띠(이유);
  }
  return true;
}

async function 캐릭터바꾸기(이름, 사용자가고름 = true) {
  화면.지금캐릭터 = 이름 || null;
  $("ask").hidden = true;
  // 응답을 기다리는 동안 앞 캐릭터의 내용을 새 이름 아래 남기지 않는다
  화면.보기 = null;
  화면.불러오는중 = Boolean(이름);
  모두그리기();
  const 최신 = await 상태불러오기();
  if (!최신) return;   // 그사이 다른 캐릭터를 골랐음
  화면.불러오는중 = false;
  모두그리기();
  if (사용자가고름) 기억하기();
  맥박();
  if (사용자가고름 && 화면.보기 && !화면.보기.있음) 새캐릭터묻기(이름);
}

function 기억하기() {
  보내기("/api/기억", {캐릭터: 화면.지금캐릭터, 단계: 화면.지금단계}).catch(() => {});
}

let 묻는캐릭터 = null;   // 묻는 상자를 연 때의 캐릭터(승인할 때 다시 읽지 않음)
function 새캐릭터묻기(이름) {
  묻는캐릭터 = 이름;
  $("askbody").innerHTML = `"${글(이름)}"에는 아직 제작 페이지 기록(<code>제작페이지/상태.json</code>)이 없습니다. 새 캐릭터로 만들면 빈 상태 파일을 만듭니다(다른 파일은 건드리지 않음).`;
  $("ask").hidden = false;
  $("askyes").focus();
}
function 묻기닫기() {
  $("ask").hidden = true;
  $("char").focus();
}

async function 새캐릭터만들기() {
  const 이름 = 묻는캐릭터;
  묻기닫기();
  if (!이름) return;
  try {
    const v = await 보내기("/api/새캐릭터", {이름});
    const c = 화면.캐릭터.find((x) => x.이름 === 이름);
    if (c) c.상태파일있음 = true;
    if (이름 === 화면.지금캐릭터) { 화면.보기 = v; 화면.바뀜[이름] = {상태: v.수정시각 || 0}; }
    오류띠("");
  } catch (e) {
    오류띠(`새 캐릭터를 만들지 못했습니다: ${e.message}`);
  }
  모두그리기();
}

function 단계고르기(i) {
  화면.지금단계 = Math.max(0, Math.min(10, i));
  if (화면.입력폼) { 화면.입력폼 = false; 캐릭터고르기그리기(); }
  단계목록그리기();
  가운데그리기();
  윗줄그리기();
  기억하기();
}

function 접기(접음) {
  $("main").classList.toggle("folded", 접음);
  $("app").classList.toggle("folded", 접음);
  $("fold").setAttribute("aria-expanded", String(!접음));
  // 접어도 "보내기"는 윗줄에 남는다(기능명세 1부 4-6)
  $("sendtop").hidden = !접음;
  try { localStorage.setItem("결정칸접힘", 접음 ? "1" : ""); } catch (e) {}
  (접음 ? $("unfold") : $("fold")).focus();
}

// ---- 서버와 이어져 있는지, 같은 캐릭터를 다른 탭이 열었는지 (1부 6절, 8절)

let 맥박중 = false;
async function 맥박() {
  if (맥박중) return;
  맥박중 = true;
  try {
    if (!화면.준비) { await 처음읽기(); return; }   // 처음 읽기에 실패했으면 서버가 돌아올 때 처음부터 다시
    const 이름 = 화면.지금캐릭터;
    let v;
    try {
      v = await 보내기("/api/탭", {탭: 탭id, 캐릭터: 이름, 단계: 화면.지금단계 + 1});
    } catch (e) {
      if (e instanceof TypeError) { 끊김(true); return; }   // 서버에 닿지 못함
      throw e;
    }
    if (화면.끊김) {
      끊김(false);
      const 목록 = await 받기("/api/캐릭터");
      화면.캐릭터 = 목록.캐릭터;
      잔액그리기(목록.잔액);
      if (await 상태불러오기()) 모두그리기();
      return;
    }
    화면.주인 = v.주인;
    $("b-tab").hidden = v.주인;
    document.body.dataset.잠금 = v.주인 ? "" : "다른 탭";   // 칠하기(W03)는 이 값이 있으면 막는다
    if (window.칠하기 && 이름 === 화면.지금캐릭터) window.칠하기.바깥바뀜(v.바뀜 && v.바뀜.표시);
    if (window.결정 && 이름 === 화면.지금캐릭터) window.결정.바깥바뀜(v.바뀜 && v.바뀜.결정);   // 에이전트가 쓴 알림·처리·사본
    if (window.부위 && 이름 === 화면.지금캐릭터) window.부위.바깥바뀜(v.바뀜 && v.바뀜.부위);
    if (window.생성단계 && 이름 === 화면.지금캐릭터) window.생성단계.바깥바뀜(v.바뀜 && v.바뀜.생성);   // W10
    if (window.메시단계 && 이름 === 화면.지금캐릭터) window.메시단계.바깥바뀜(v.바뀜 && v.바뀜.메시);   // W11
    if (window.텍스처단계 && 이름 === 화면.지금캐릭터) window.텍스처단계.바깥바뀜(v.바뀜 && v.바뀜.텍스처);   // W12
    if (window.리깅단계 && 이름 === 화면.지금캐릭터) window.리깅단계.바깥바뀜(v.바뀜 && v.바뀜.리깅);   // W13
    if (window.동작단계 && 이름 === 화면.지금캐릭터) window.동작단계.바깥바뀜(v.바뀜 && v.바뀜.동작);   // W14
    if (window.그림단계 && 이름 === 화면.지금캐릭터) window.그림단계.바깥바뀜(v.바뀜 && v.바뀜.그림, v.바뀜 && v.바뀜.표시);   // W09   // 에이전트가 부위 목록을 다시 만듦
    // 캐릭터를 막 바꿔 불러오는 중이면 다시 읽지 않는다(그 읽기가 "새 캐릭터로 만들까요?"를 묻는다)
    if (이름 && 이름 === 화면.지금캐릭터 && v.바뀜 && !화면.불러오는중) {
      const 전 = 화면.바뀜[이름] || {};
      const 다름 = v.바뀜.상태 !== 전.상태 || (전.작업본 !== undefined && v.바뀜.작업본 !== 전.작업본);
      if (다름 && await 상태불러오기()) {
        const c = 화면.캐릭터.find((x) => x.이름 === 이름);
        if (c) c.상태파일있음 = Boolean(화면.보기 && 화면.보기.있음);
        모두그리기();
      }
      if (이름 === 화면.지금캐릭터) 화면.바뀜[이름] = {상태: (화면.보기 && 화면.보기.수정시각) || 0, 작업본: v.바뀜.작업본};
    }
  } catch (e) {
    오류띠(`서버 응답 오류: ${e.message}`);
  } finally {
    맥박중 = false;
  }
}

function 끊김(예) {
  화면.끊김 = 예;
  $("b-off").hidden = !예;
}

async function 처음읽기() {
  try {
    화면.정보 = await 받기("/api/정보");
    const 목록 = await 받기("/api/캐릭터");
    화면.캐릭터 = 목록.캐릭터;
    잔액그리기(목록.잔액);
    const 기억 = 목록.기억 || {};
    if (Number.isInteger(기억.단계)) 화면.지금단계 = Math.max(0, Math.min(10, 기억.단계));
    const 이름 = 화면.캐릭터.some((c) => c.이름 === 기억.캐릭터) ? 기억.캐릭터
      : (화면.캐릭터.find((c) => c.상태파일있음) || {}).이름 || null;
    화면.준비 = true;
    끊김(false);
    await 캐릭터바꾸기(이름, false);
  } catch (e) {
    끊김(true);
  }
}

async function 시작() {
  let 접음 = false;
  try { 접음 = localStorage.getItem("결정칸접힘") === "1"; } catch (e) {}
  if (접음) { $("main").classList.add("folded"); $("app").classList.add("folded"); $("sendtop").hidden = false; $("fold").setAttribute("aria-expanded", "false"); }
  await 처음읽기();
  setInterval(맥박, 맥박간격);
}

// ---------------------------------------------------------------- 이벤트

$("steps").addEventListener("click", (ev) => {
  const b = ev.target.closest(".step");
  if (b) 단계고르기(Number(b.dataset.i));
});
$("steps").addEventListener("keydown", (ev) => {
  const b = ev.target.closest(".step");
  if (!b || !["ArrowDown", "ArrowUp"].includes(ev.key)) return;
  ev.preventDefault();
  단계고르기(Number(b.dataset.i) + (ev.key === "ArrowDown" ? 1 : -1));
  const 다음 = $("steps").querySelector(".step.on");
  if (다음) 다음.focus();
});
$("char").addEventListener("change", (ev) => {
  // 작성 중인 표시는 칠할 때마다 자동 저장되므로(W03) 그대로 넘어간다.
  if (ev.target.value === "__새캐릭터입력__") { 새캐릭터입력열기(); return; }
  화면.입력폼 = false;
  캐릭터바꾸기(ev.target.value || null);
});
$("askyes").addEventListener("click", 새캐릭터만들기);
$("askno").addEventListener("click", 묻기닫기);
$("ask").addEventListener("keydown", (ev) => { if (ev.key === "Escape") 묻기닫기(); });
$("fold").addEventListener("click", () => 접기(true));
$("unfold").addEventListener("click", () => 접기(false));
// 숨었던(잠들었던) 탭이 돌아오면 곧바로 주인인지 다시 확인한다. 그동안은 칠하기를 막는다.
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState !== "visible" || !화면.준비) return;
  document.body.dataset.잠금 = "확인 중";
  맥박();
});
window.addEventListener("pagehide", () => {
  try {
    navigator.sendBeacon("/api/탭", new Blob([JSON.stringify({탭: 탭id, 캐릭터: 화면.지금캐릭터, 놓기: true})], {type: "application/json"}));
  } catch (e) {}
});

시작();
