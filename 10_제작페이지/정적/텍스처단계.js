// 7단계 텍스처 수정 화면 (작업 묶음 W12, 기능명세 2부 19절, SSOT 단계/5_텍스처 5-5~5-7)
// 보기 줄 오른쪽 옆 기둥(UV 그림 다음): 정리 차례 · 후보(에이전트·독립 검수) · 자동 검사기 후보(아직 비어 있음) · 독립 검수 · 끝나는 조건.
// 아래에 "사람이 하는 일". 칠하기·후보 판단·고친 것(✓) 전후는 표시 목록(칠하기.js)이 한다.
(() => {
  const 글 = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const 그림주소 = (x) => `/api/그림/파일?경로=${encodeURIComponent(x)}`;
  const 짧은시각 = (t) => String(t || "").replace("T", " ").slice(5, 16);
  const 상 = {이름: null, 값: null, 바깥: null, 오류: "", 묻는번호: 0, 안받음열림: false, 적는중: false, 글: "", 실패: ""};
  window.텍스처단계상태 = 상;   // 시험·검사용으로 읽기만

  const 기둥 = document.createElement("div");
  기둥.className = "g1aside p10aside";
  기둥.innerHTML = `<div class="g1asidein" id="p12in"></div>`;
  const 사람줄 = document.createElement("div");
  사람줄.className = "human";
  사람줄.dataset.순서 = "사람이 하는 일";

  function 칸(제목, 안) { return `<div class="note"><div class="ttl">${글(제목)}</div>${안}</div>`; }
  function 섬네일(목록) {
    if (!목록 || !목록.length) return "";
    return `<div class="p10th">${목록.map((x) => `<a href="${그림주소(x)}" target="_blank" rel="noopener" title="${글(x)} — 크게 보기"><img src="${그림주소(x)}" alt="${글(x.split("/").pop())}" loading="lazy"></a>`).join("")}</div>`;
  }

  function 순서칸() {
    const v = 상.값, 검 = v.검수;
    const 줄 = v.순서.map((x) => `<tr><td>${x.번호}</td><td title="${글(x.메모 || x.글)}">${글(x.글)}${x.메모 ? `<span class="hint">${글(x.메모)}</span>` : ""}</td><td>${x.끝 ? `<span class="ok">✓</span>` : "—"}</td></tr>`);
    줄.push(`<tr><td>4</td><td>독립 검수(5-7, Codex Astra)</td><td>${검 ? `<span class="${검.상태 === "받음" ? "ok" : "wa"}">${검.상태 === "받음" ? "✓" : "받지 않음"}</span>` : "—"}</td></tr>`);
    return 칸("정리 차례(SSOT 단계/5_텍스처)", `<table class="t"><tbody>${줄.join("")}</tbody></table>`);
  }
  function 후보칸() {
    const h = 상.값.후보;
    if (!h) return 칸("후보와 고친 것", `<span class="hint">아직 없습니다. 에이전트가 정리 뒤 후보와 묻지 않고 고친 것(✓)을 냅니다.</span>`);
    const 누가 = Object.entries(h.누가 || {}).map(([k, n]) => `<div>${글(k)}</div><div>${n}개</div>`).join("");
    return 칸("후보와 고친 것", `<div class="kv g1kv">${누가 || "<div>후보</div><div>0개</div>"}` +
      `<div>판단 안 함</div><div class="${h.안판단 ? "wa" : "ok"}">${h.안판단}개</div><div>묻지 않고 고친 것</div><div>${h.고친것수}개(표시 목록의 ✓, 누르면 전후)</div></div>` +
      `<span class="hint">후보는 아래 표시 목록에서 고칠 것 / 둘 것 / 모름.</span>`);
  }
  function 검사기칸() {
    return 칸("자동 검사기 후보", `<span class="hint">아직 붙이지 않았습니다. 텍스처 자동 검사기 시험 결과를 본 뒤에 붙입니다(기능명세 28절).</span>`);
  }
  function 검수칸() {
    const 검 = 상.값.검수;
    let 안;
    if (!검) 안 = `<span class="hint">아직 받지 않았습니다. 에이전트가 끝나기 전에 Codex Astra에게 맡기고, 지적은 후보로 같은 목록에 들어옵니다.</span>`;
    else if (검.상태 === "받음") {
      안 = `<div class="kv g1kv"><div>회차</div><div>${검.차}차 · ${글(짧은시각(검.시각))}</div><div>검수자</div><div>${글(검.검수자)}</div>` +
        `<div>지적</div><div>${검.지적수}개${검.지적수 ? "(후보로 넣음)" : ""}</div>` +
        `${검.보고 ? `<div>보고</div><div><code>${글(검.보고)}</code></div>` : ""}</div>` +
        (검.넓은그림 && 검.넓은그림.length ? `<div class="hint">넓게 본 그림(누르면 크게)</div>${섬네일(검.넓은그림)}<span class="hint">확대 지적을 끝없이 쫓지 않습니다. 넓게 보고 멈출 곳을 정해 주세요.</span>` : "");
    } else {
      안 = `<div class="kv g1kv"><div>회차</div><div>${검.차}차 · ${글(짧은시각(검.시각))}</div><div>받지 않음</div><div class="wa">${글(검.이유)}</div><div>적은 이</div><div>${글(검.누가)}</div></div>`;
    }
    const 단추 = 상.안받음열림
      ? `<label class="dmemo"><span class="mlab">받지 않는 이유</span><textarea id="p12why" rows="2" placeholder="예: Codex 사용량 한도">${글(상.글)}</textarea></label>` +
        `<div class="btns2"><button type="button" class="btn b-re" id="p12no"${상.적는중 ? " disabled" : ""}>받지 않음으로 적기</button><button type="button" class="btn b-re" id="p12cancel">취소</button></div>`
      : (!검 || 검.상태 !== "받지 않음" ? `<button type="button" class="tb" id="p12open" title="끝나는 조건: 독립 검수를 받았거나 '받지 않음'이 기록됨">독립 검수 받지 않음…</button>` : "");
    return 칸("독립 검수", 안 + 단추 + (상.실패 ? `<span class="hint ng">${글(상.실패)}</span>` : ""));
  }
  function 끝칸() {
    const 모 = 상.값.모자람 || [];
    return 칸("끝나는 조건", 모.length ? `<ul class="lack">${모.map((x) => `<li class="ng">${글(x)}</li>`).join("")}</ul>` : `<span class="ok">✓ 모두 채움 — '이 단계 끝'을 누를 수 있습니다</span>`);
  }
  function 그리기() {
    const 안 = 기둥.querySelector("#p12in");
    if (상.오류) { 안.innerHTML = `<div class="note ng">${글(상.오류)}</div>`; return; }
    if (!상.값) { 안.innerHTML = `<div class="note"><span class="hint">불러오는 중…</span></div>`; return; }
    if (안.contains(document.activeElement) && document.activeElement.id === "p12why") return;   // 이유를 적는 동안은 다시 그리지 않음
    const 스크롤 = 안.scrollTop;
    안.innerHTML = 후보칸() + 검수칸() + 순서칸() + 검사기칸() + 끝칸();
    안.scrollTop = 스크롤;
  }

  기둥.addEventListener("click", async (ev) => {
    if (ev.target.closest("#p12open")) { 상.안받음열림 = true; 그리기(); 기둥.querySelector("#p12why")?.focus(); return; }
    if (ev.target.closest("#p12cancel")) { 상.안받음열림 = false; 상.글 = ""; 그리기(); return; }
    if (ev.target.closest("#p12no")) {
      상.적는중 = true; 상.실패 = ""; 그리기();
      try {
        const r = await fetch("/api/텍스처/검수안받음", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({이름: 상.이름, 탭: window.탭id, 이유: 상.글})});
        const v = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(v.오류 || r.status);
        상.안받음열림 = false; 상.글 = "";
      } catch (e) {
        상.실패 = `적지 못함: ${e instanceof TypeError ? "서버와 연결 끊김" : e.message}`;
      } finally {
        상.적는중 = false;
        await 다시읽기();
      }
    }
  });
  기둥.addEventListener("input", (ev) => { if (ev.target.id === "p12why") 상.글 = ev.target.value; });

  async function 다시읽기() {
    if (!상.이름) return;
    const 번호 = ++상.묻는번호, 이름 = 상.이름;
    try {
      const r = await fetch(`/api/텍스처?이름=${encodeURIComponent(이름)}`, {cache: "no-store"});
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
    if (단계 !== 7 || !window.보기3d) { 떼기(); return; }
    const 뿌리 = window.보기3d.내부.뿌리, 줄 = 뿌리.querySelector(".vrow"), 몸 = document.getElementById("body");
    if (!뿌리.isConnected || !줄 || !몸) { 떼기(); return; }
    if (이름 !== 상.이름) { 상.값 = null; 상.오류 = ""; 상.바깥 = null; 상.안받음열림 = false; 상.글 = ""; }
    상.이름 = 이름;
    줄.appendChild(기둥);
    사람줄.innerHTML = `<b>사람이 하는 일</b> · 후보(에이전트·독립 검수)를 판단하고, 고친 것(✓)의 전후를 봄. 그 밖에 이상한 곳은 3D나 UV 그림 위에 칠해 처리를 고르고 보내기. 대칭 부위는 "반대쪽도"를 켜면 한쪽을 고쳐 뒤집어 씀(기본 꺼짐). 독립 검수의 확대 지적은 넓게 본 그림으로 멈출 곳을 정함.`;
    몸.appendChild(사람줄);
    그리기();
    다시읽기();
  }
  function 떼기() {
    기둥.remove(); 사람줄.remove();
    상.이름 = null;
  }
  function 바깥바뀜(값) {
    if (!상.이름) return;
    if (값 !== undefined && 값 !== 상.바깥) { const 처음 = 상.바깥 === null; 상.바깥 = 값; if (!처음) 다시읽기(); }
  }
  window.텍스처단계 = {붙이기, 떼기, 바깥바뀜, 다시읽기, 상태: 상};
  window.dispatchEvent(new Event("텍스처단계준비"));
})();
