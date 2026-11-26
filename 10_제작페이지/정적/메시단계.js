// 3단계 메시 정리 화면 (작업 묶음 W11, 기능명세 2부 15절, 1부 3-1b)
// 보기 줄 오른쪽 옆 기둥: 보기 색(형태만·조각·파츠·노멀) · 정리 순서 체크 · 멈춤 칸 · 끝나는 조건. 아래에 "사람이 하는 일".
// 두 번만 멈춘다: 멈춤 1 계획 확인(지울 조각 후보 + 대칭 기준), 멈춤 2 결과 확인(남은 흠 후보 + 고친 것).
// 후보의 판단(고칠 것·둘 것·모름)과 칠하기는 표시 목록(칠하기.js)이 하고, 이 파일은 멈춤 1의 대칭 답을 보내기에 붙인다.
(() => {
  const 글 = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const 수 = (n) => (typeof n === "number" ? n.toLocaleString("ko-KR") : "—");
  const 그림주소 = (x) => `/api/그림/파일?경로=${encodeURIComponent(x)}`;
  const 쪽글 = (k) => ({"+x": "+x (화면 오른쪽)", "-x": "-x (화면 왼쪽)"}[k] || "—");
  const 상 = {이름: null, 값: null, 바깥: null, 오류: "", 묻는번호: 0, 답: {}, 보내려함: false, 보낸글: ""};
  window.메시단계상태 = 상;   // 시험·검사용으로 읽기만

  const 기둥 = document.createElement("div");
  기둥.className = "g1aside p10aside";
  기둥.innerHTML = `<div class="g1asidein" id="p11in"></div>`;
  const 사람줄 = document.createElement("div");
  사람줄.className = "human";
  사람줄.dataset.순서 = "사람이 하는 일";

  function 칸(제목, 안) { return `<div class="note"><div class="ttl">${글(제목)}</div>${안}</div>`; }

  function 색칸() {
    const b = window.보기3d && window.보기3d.상태, 지금 = b ? (b.색 || (b.형태만 ? "형태만" : "")) : "";
    const 단 = (k, t, 뜻) => `<button type="button" data-mc="${k}" class="${지금 === k ? "on" : ""}" aria-pressed="${지금 === k}" title="${글(뜻)}">${글(t)}</button>`;
    return 칸("보기 색", `<div class="seg">${단("형태만", "형태만", "회색과 음영만")}${단("조각", "조각 색", "파츠 안에서 서로 이어지지 않은 덩어리마다 다른 색(가장 큰 덩어리는 회색)")}` +
      `${단("파츠", "파츠 색", "파츠마다 다른 색")}${단("노멀", "노멀 방향", "면이 향한 방향을 색으로(뒤집힌 면은 주변과 다른 색)")}</div>`);
  }
  function 순서칸() {
    const v = 상.값, 줄 = [];
    for (const x of v.순서) {
      줄.push(`<tr><td>${x.번호}</td><td title="${글(x.메모 || x.글)}">${글(x.글)}${x.메모 ? `<span class="hint">${글(x.메모)}</span>` : ""}</td><td>${x.끝 ? `<span class="ok">✓</span>` : "—"}</td></tr>`);
      if (x.번호 === 5 || x.번호 === 10) {
        const k = x.번호 === 5 ? "멈춤 1 · 계획 확인" : "멈춤 2 · 결과 확인";
        줄.push(`<tr><td></td><td colspan="2"><b class="wa">${글(k)}</b></td></tr>`);
      }
    }
    return 칸("정리 순서(SSOT 단계/3_메시)", `<table class="t"><tbody>${줄.join("")}</tbody></table>`);
  }
  function 섬네일(목록) {
    if (!목록 || !목록.length) return "";
    return `<div class="p10th">${목록.map((x) => `<a href="${그림주소(x)}" target="_blank" rel="noopener" title="${글(x)} — 크게 보기"><img src="${그림주소(x)}" alt="${글(x.split("/").pop())}" loading="lazy"></a>`).join("")}</div>`;
  }
  function 계획칸(m) {
    const 확 = 상.값.확정, 계 = m.계획 || {파츠: [], 대칭: []};
    const 파츠 = `<table class="t"><thead><tr><th>파츠</th><th>면</th><th>조각</th></tr></thead><tbody>` +
      계.파츠.map((p) => `<tr><td>${글(p.이름)}</td><td>${수(p.면)}</td><td>${(window.보기3d && window.보기3d.조각수(p.이름)) ?? "—"}</td></tr>`).join("") + `</tbody></table>`;
    let 대칭;
    if (확) {
      대칭 = `<table class="t"><thead><tr><th>파츠</th><th>정함</th></tr></thead><tbody>` +
        확.대칭.map((x) => `<tr><td>${글(x.파츠)}</td><td>${x.대칭 ? `대칭 · 기준 ${글(쪽글(x.기준쪽))}` : "대칭 안 함"}${x.답 === "에이전트 쪽" ? "" : ` <span class="wa">(${글(x.답)})</span>`}</td></tr>`).join("") +
        `</tbody></table><span class="hint ok">✓ 정함 ${글(String(확.만든시각 || "").replace("T", " ").slice(5, 16))} — 정한 대칭 기준은 뒤에서 바꾸지 않습니다.</span>`;
    } else {
      대칭 = 계.대칭.map((x) => {
        const 답 = 상.답[x.파츠] || {답: x.대칭 ? "에이전트 쪽" : "대칭 안 함", 기준쪽: x.기준쪽 || "+x"};
        const 고름 = x.대칭
          ? `<select class="g1sel" data-sym="${글(x.파츠)}" aria-label="${글(x.파츠)} 대칭 답">${["에이전트 쪽", "반대쪽", "대칭 안 함"].map((k) => `<option${k === 답.답 ? " selected" : ""}>${글(k)}</option>`).join("")}</select>`
          : `<select class="g1sel" data-sym="${글(x.파츠)}" aria-label="${글(x.파츠)} 대칭 답"><option${답.답 === "대칭 안 함" ? " selected" : ""}>대칭 안 함</option>` +
            `<option value="+x"${답.답 !== "대칭 안 함" && 답.기준쪽 === "+x" ? " selected" : ""}>대칭 · +x 기준</option><option value="-x"${답.답 !== "대칭 안 함" && 답.기준쪽 === "-x" ? " selected" : ""}>대칭 · -x 기준</option></select>`;
        return `<div class="note"><div class="kv g1kv"><div>파츠</div><div>${글(x.파츠)}</div>` +
          `<div>에이전트</div><div>${x.대칭 ? `대칭 · 기준 ${글(쪽글(x.기준쪽))}` : "비대칭으로 둠"}</div>` +
          `<div>이유</div><div title="${글(x.이유)}">${글(x.이유 || "—")}</div><div>고르기</div><div>${고름}</div></div>` +
          `${섬네일(x.그림)}${x.그림 && x.그림.length ? `<span class="hint">좌우 절반 나란히(누르면 크게)</span>` : ""}</div>`;
      }).join("") || `<span class="hint">대칭으로 만들 파츠가 없습니다.</span>`;
    }
    const 단추 = 확 ? "" : `<button type="button" class="btn b-ok" id="p11send"${m.보냄 ? " disabled" : ""}>계획 정하고 보내기</button>` +
      `<span class="hint">지울 조각 후보 ${m.후보수}개는 아래 표시 목록에서 판단(고칠 것 = 지움 · 둘 것 · 모름). 대칭 답과 함께 한 번에 보냅니다.</span>` +
      (상.보낸글 ? `<span class="hint ng">${글(상.보낸글)}</span>` : "");
    return 칸("멈춤 1 · 계획 확인", `<div class="hint">파츠 나눈 결과</div>${파츠}<div class="hint">대칭으로 만들 조각과 기준 쪽(화면 오른쪽 = +x)</div>${대칭}${단추}`);
  }
  function 결과칸(m) {
    const r = m.결과 || {};
    const 판 = (r.접합부판정 || []).map((x) => `<tr><td>${글(x.접합부)}</td><td class="${x.판정 === "통과" ? "ok" : "wa"}">${글(x.판정)}</td><td title="${글(x.근거)}">${글(x.근거 || "")}</td></tr>`).join("");
    return 칸("멈춤 2 · 결과 확인", `<div class="kv g1kv"><div>남은 흠 후보</div><div>${m.후보수}개${m.보냄 ? ` <span class="ok">✓ 보냄</span>` : ""}</div><div>묻지 않고 고친 것</div><div>${m.고친것수}개(표시 목록의 ✓, 누르면 전후)</div></div>` +
      `<div class="hint">접합부별 판정</div><table class="t"><tbody>${판 || `<tr><td>없음</td></tr>`}</tbody></table>` +
      `<div class="hint">여러 방향 그림</div>${섬네일(r.다각도그림)}` +
      `<span class="hint">여기서 고르는 것은 뒤의 작업에 영향이 없습니다. 후보를 판단해 보내거나, 모두 괜찮으면 '이 단계 끝'.</span>`);
  }
  function 멈춤칸() {
    const m = 상.값.멈춤;
    if (!m) {
      const 끝 = 상.값.순서.filter((x) => x.끝).length;
      return 칸("멈춤", `<span class="hint">${상.값.확정 ? "계획을 정했습니다. 에이전트가 6~10을 하고 멈춤 2(결과 확인)를 냅니다." : `에이전트가 순서 1~5를 하는 중입니다(${끝}/10 끝). 끝나면 멈춤 1(계획 확인)이 여기에 보입니다.`}</span>` +
        `<span class="hint">Claude 앱에서 "3단계 메시 정리 시작해 줘"라고 하면 에이전트가 시작합니다.</span>`);
    }
    return m.멈춤 === "계획 확인" ? 계획칸(m) : 결과칸(m);
  }
  function 끝칸() {
    const 모 = 상.값.모자람 || [];
    return 칸("끝나는 조건", 모.length ? `<ul class="lack">${모.map((x) => `<li class="ng">${글(x)}</li>`).join("")}</ul>` : `<span class="ok">✓ 모두 채움 — '이 단계 끝'을 누를 수 있습니다</span>`);
  }
  function 그리기() {
    const 안 = 기둥.querySelector("#p11in");
    if (상.오류) { 안.innerHTML = `<div class="note ng">${글(상.오류)}</div>`; return; }
    if (!상.값) { 안.innerHTML = `<div class="note"><span class="hint">불러오는 중…</span></div>`; return; }
    const 스크롤 = 안.scrollTop;
    안.innerHTML = 색칸() + 멈춤칸() + 순서칸() + 끝칸();
    안.scrollTop = 스크롤;
  }
  기둥.addEventListener("click", (ev) => {
    const c = ev.target.closest("[data-mc]");
    if (c && window.보기3d) {
      window.보기3d.모양정하기(c.dataset.mc === "형태만" ? {형태만: true, 격자: false, 와이어: false, 색: null} : {격자: false, 와이어: false, 색: c.dataset.mc});
      그리기();
      return;
    }
    if (ev.target.closest("#p11send")) 계획보내기();
  });
  기둥.addEventListener("change", (ev) => {
    const s = ev.target.closest("[data-sym]");
    if (!s) return;
    const v = s.value;
    상.답[s.dataset.sym] = v === "+x" || v === "-x" ? {답: "에이전트 쪽", 기준쪽: v} : {답: v};
  });
  window.addEventListener("보기3d모양", () => { if (상.이름) 그리기(); });

  // 칠하기.js의 보내기가 부른다: 멈춤 1이면 '계획 정하고 보내기'를 누른 때만 대칭 답을 붙인다(아니면 서버가 막고 이유를 보임)
  function 멈춤답() {
    const m = 상.값 && 상.값.멈춤;
    if (!m || m.보냄) return undefined;
    if (m.멈춤 === "결과 확인") return {멈춤: "결과 확인", 후보파일: m.파일};
    if (상.값.확정 || !상.보내려함) return undefined;
    return {멈춤: "계획 확인", 후보파일: m.파일, 대칭: (m.계획.대칭 || []).map((x) => {
      const 답 = 상.답[x.파츠] || {답: x.대칭 ? "에이전트 쪽" : "대칭 안 함"};
      return x.대칭 ? {파츠: x.파츠, 답: 답.답} : 답.답 === "대칭 안 함" ? {파츠: x.파츠, 답: "대칭 안 함"} : {파츠: x.파츠, 답: "에이전트 쪽", 기준쪽: 답.기준쪽};
    })};
  }
  async function 계획보내기() {
    if (!window.칠하기 || !window.칠하기.보내기) return;
    상.보내려함 = true; 상.보낸글 = "";
    try {
      await window.칠하기.보내기();
      const 글들 = window.칠하기.상태.보낸글 || "";
      if (글들.startsWith("보내지 못함")) 상.보낸글 = 글들;
    } finally {
      상.보내려함 = false;
      await 다시읽기();
    }
  }

  async function 다시읽기() {
    if (!상.이름) return;
    const 번호 = ++상.묻는번호, 이름 = 상.이름;
    try {
      const r = await fetch(`/api/메시?이름=${encodeURIComponent(이름)}`, {cache: "no-store"});
      const v = await r.json();
      if (번호 !== 상.묻는번호) return;
      if (!r.ok) throw new Error(v.오류 || r.status);
      상.값 = v; 상.오류 = "";
    } catch (e) {
      if (번호 !== 상.묻는번호) return;
      상.오류 = `옆 기둥을 읽지 못함: ${e instanceof TypeError ? "서버와 연결 끊김" : e.message}`;
    }
    그리기();
  }

  function 붙이기(이름, 단계) {
    if (단계 !== 3 || !window.보기3d) { 떼기(); return; }
    const 뿌리 = window.보기3d.내부.뿌리, 줄 = 뿌리.querySelector(".vrow"), 몸 = document.getElementById("body");
    if (!뿌리.isConnected || !줄 || !몸) { 떼기(); return; }
    const 새 = 이름 !== 상.이름;
    if (!상.이름) window.보기3d.모양정하기({형태만: true, 격자: false, 와이어: false, 색: null});   // 2부 15절: 형태만이 기본
    상.이름 = 이름;
    if (새) { 상.값 = null; 상.오류 = ""; 상.바깥 = null; 상.답 = {}; 상.보낸글 = ""; }
    줄.appendChild(기둥);
    사람줄.innerHTML = `<b>사람이 하는 일</b> · 두 번만 정합니다. 멈춤 1: 지울 조각 후보를 판단하고 대칭 기준 쪽을 고름(뒤에서 바꾸지 않음). 멈춤 2: 남은 흠 후보를 판단하고 고친 것의 전후를 봄. 그 밖에 이상한 곳은 붓으로 칠해 보내기.`;
    몸.appendChild(사람줄);
    그리기();
    다시읽기();
  }
  function 떼기() {
    if (상.이름 && window.보기3d && window.보기3d.상태.색) window.보기3d.모양정하기({색: null});
    기둥.remove(); 사람줄.remove();
    상.이름 = null;
  }
  function 바깥바뀜(값) {
    if (!상.이름) return;
    if (값 !== undefined && 값 !== 상.바깥) { const 처음 = 상.바깥 === null; 상.바깥 = 값; if (!처음) 다시읽기(); }
  }
  window.메시단계 = {붙이기, 떼기, 바깥바뀜, 다시읽기, 멈춤답, 상태: 상};
  window.dispatchEvent(new Event("메시단계준비"));
})();
