// 10·11단계 동작·내보내기 화면 (작업 묶음 W14, 기능명세 2부 22·23절, SSOT 단계/7_Unity)
// 10: 보기 줄 오른쪽 옆 기둥 — 고르기 방식(모음에서 고르기 / TRIPO로 만들기), 모음의 모든 동작 목록(체크·자동 처리 표시·옮김 결과),
//     미리 보기(이름을 누르면 이 캐릭터에 입혀 재생, 준비 전에는 원래 인형), '옮기기', 끝나는 조건.
//     옮긴 동작의 재생·시간 막대·칠하기·구간 리포트는 리깅단계.js(W13)가 9단계와 같게 붙인다. 미리 보기 중에는 그 막대 대신 미리 보기 줄.
// 11: 옆 기둥 — Unity 프로젝트 상자(경로·버전·가져오기 방식), 보낼 파일 검사표, '내보내기', Unity에서 찍은 모습, 끝나는 조건.
(() => {
  const 글 = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const 그림주소 = (x) => `/api/그림/파일?경로=${encodeURIComponent(x)}`;
  const 짧은시각 = (t) => String(t || "").replace("T", " ").slice(5, 16);
  const 상 = {이름: null, 단계: 0, 값: null, 바깥: null, 오류: "", 묻는번호: 0, 누르는중: false, 실패: "", 방식: "모음",
    미리: null, 켬: true, 덮어쓰기: false, 경로글: null, 넣을글: null};
  window.동작단계상태 = 상;   // 시험·검사용으로 읽기만

  const 기둥 = document.createElement("div");
  기둥.className = "g1aside p10aside p14aside";
  기둥.innerHTML = `<div class="g1asidein" id="p14in"></div>`;
  const 미리줄 = document.createElement("div");
  미리줄.className = "tgrp p13bar";
  미리줄.setAttribute("aria-label", "미리 보기");
  미리줄.dataset.자체단추 = "";
  const 사람줄 = document.createElement("div");
  사람줄.className = "human";
  사람줄.dataset.순서 = "사람이 하는 일";

  const 보 = () => window.보기3d;
  const 붙음 = () => Boolean(상.이름 && 기둥.isConnected);
  const 잠금 = () => document.body.dataset.잠금 === "다른 탭";
  function 칸(제목, 안) { return `<div class="note"><div class="ttl">${글(제목)}</div>${안}</div>`; }
  function 섬네일(목록) {
    if (!목록 || !목록.length) return "";
    return `<div class="p10th">${목록.map((x) => `<a href="${그림주소(x)}" target="_blank" rel="noopener" title="${글(x)} — 크게 보기"><img src="${그림주소(x)}" alt="${글(x.split("/").pop())}" loading="lazy"></a>`).join("")}</div>`;
  }
  function 끝칸() {
    const 모 = 상.값.모자람 || [];
    return 칸("끝나는 조건", 모.length ? `<ul class="lack">${모.map((x) => `<li class="ng">${글(x)}</li>`).join("")}</ul>` : `<span class="ok">✓ 모두 채움 — '이 단계 끝'을 누를 수 있습니다</span>`);
  }
  const 실패줄 = () => (상.실패 ? `<span class="hint ng">${글(상.실패)}</span>` : "");

  // ---------------------------------------------------------------- 10단계
  function 옮김줄(n) { return ((상.값.옮김 && 상.값.옮김.동작) || []).find((x) => x.원본 === n) || null; }
  function 미리칸() {
    const m = 상.값.미리 || {};
    let 상태;
    if (m.상태 === "만드는 중") 상태 = `<span class="wa">이 캐릭터로 준비 중… ${글(m.걸음 || "")} · ${글(m.경과초 ?? 0)}초</span><span class="hint">다 되기 전의 동작은 모음의 원래 인형으로 먼저 보입니다. 끝나면 저절로 바뀝니다.</span>`;
    else if (m.상태 === "됨") 상태 = `<span class="ok">✓ 이 캐릭터로 준비됨</span>${m.켠것 ? "" : `<span class="hint">자동 처리를 켠 미리 보기는 없습니다(리깅설정에 보폭·팔 벌림 값이 없음).</span>`}`;
    else if (m.상태 === "실패") 상태 = `<span class="ng">미리 보기를 만들지 못함: ${글(m.오류 || "")}</span><span class="hint">원래 인형으로는 볼 수 있습니다. 서버를 껐다 켜면 다시 만듭니다.</span>`;
    else 상태 = `<span class="hint">${글(m.오류 || (m.상태 === "작업본 없음" ? "작업본이 없어 이 캐릭터로는 미리 볼 수 없습니다" : "아직 시작하지 않음"))}</span>`;
    const 처리 = 상.값.자동처리 || [];
    return `<div class="kv g1kv"><div>미리 보기</div><div>${상태}</div>` +
      `<div>자동 처리</div><div>${처리.length ? 글(처리.join(" · ")) : "없음"}${처리.length ? `<label class="pchk p14chk" title="미리 보기에 보폭·팔 벌림을 켠 것 / 끈 것"><input type="checkbox" id="p14on"${상.켬 ? " checked" : ""}><span>미리 보기에 켬</span></label>` : ""}</div></div>`;
  }
  function 목록칸() {
    const v = 상.값, 모 = v.모음 || {}, 고른 = new Set(v.고른 || []);
    if (!(모.동작 || []).length) return 칸("동작 모음", `<span class="hint ng">${글(모.오류 || "동작 모음이 없습니다")}</span><span class="hint">상태.json에 "동작모음" {이름, glb, fbx}를 적으면 목록이 뜹니다.</span>`);
    const 처리 = v.자동처리 || [];
    const 줄 = 모.동작.map((n) => {
      const o = 옮김줄(n), 지금 = 상.미리 && 상.미리.이름 === n;
      let 결과 = "";
      if (o && !o.성공) 결과 = `<span class="ng">못 옮김: ${글(o.까닭 || "")}</span>`;
      else if (o && o.새관통) 결과 = `<span class="ng">새 관통 · 교차 ${글(o.교차수)}</span><button type="button" class="tb" data-아홉="${글(o.이름)}" title="9단계 보기로 열어 이 동작을 봅니다">9단계 보기로</button>`;
      else if (o) 결과 = `<span class="ok">✓ 옮김 · 교차 ${글(o.교차수)}</span>`;
      const 태그 = (o && o.자동처리 ? o.자동처리 : 처리).join(" · ");
      return `<tr class="${o && (o.새관통 || !o.성공) ? "p14bad" : ""}${지금 ? " on" : ""}"><td><input type="checkbox" data-고름="${글(n)}"${고른.has(n) ? " checked" : ""}${잠금() || 상.누르는중 ? " disabled" : ""} aria-label="${글(n)} 고르기"></td>` +
        `<td><button type="button" class="p14name${지금 ? " on" : ""}" data-미리="${글(n)}" title="이 캐릭터에 입혀 재생">${글(n)}</button>` +
        `<span class="p14sub">${태그 ? `자동 처리: ${글(태그)}` : "자동 처리 없음"}</span>${결과 ? `<span class="p14sub">${결과}</span>` : ""}</td></tr>`;
    }).join("");
    const 요청 = v.옮기기요청;
    const 막음 = 잠금() ? "다른 탭에서 열려 있습니다" : !고른.size ? "옮길 동작을 체크하세요" : (모.오류 || "").includes("FBX") ? 모.오류 : 상.누르는중 ? "보내는 중…" : "";
    return 칸(`${모.이름 || "동작 모음"} · ${모.동작.length}개 · 고름 ${고른.size}`, 미리칸() +
      (모.오류 ? `<span class="hint wa">${글(모.오류)}</span>` : "") +
      `<div class="p14list"><table class="t p14t"><thead><tr><th></th><th>동작(이름을 누르면 미리 보기)</th></tr></thead><tbody>${줄}</tbody></table></div>` +
      `<button type="button" class="tb" id="p14move"${막음 ? ` disabled title="${글(막음)}"` : ` title="고른 동작을 에이전트가 이 캐릭터로 옮기고 자동 처리합니다"`}>옮기기 (${고른.size}개)</button>` +
      (요청 ? `<span class="hint">마지막 옮기기 요청 ${글(짧은시각(요청.만든시각))} · ${글((요청.동작 || []).length)}개${v.옮김 && v.옮김.만든시각 >= 요청.만든시각 ? " · 옮김 받음" : " · 에이전트 기다림"}</span>` : "") +
      (v.옮김옛것 ? `<span class="hint wa">옮긴 기록이 지금 작업본보다 오래됐습니다.</span>` : "") + 실패줄());
  }
  function 트리포칸() {
    const r = 상.값.생성실행;
    return 칸("TRIPO로 만들기", `<span class="hint wa">TRIPO 동작 생성은 아직 해 본 적이 없습니다. 첫 실행 전에 결정 칸 승인 상자에서 값과 가격을 확인하세요(가격은 "모름").</span>` +
      `<span class="hint">Claude 앱에서 "TRIPO로 동작 만들어 줘 (예: walk, run)"라고 하면 에이전트가 요청을 만들고 결정 칸에 승인 상자가 뜹니다. 8단계를 TRIPO로 리깅했어야 합니다. 한 번에 5개까지, 동작마다 크레딧.</span>` +
      (r ? `<div class="kv g1kv"><div>마지막 실행</div><div>${글(r.실행)}${(r.결과 || {}).가짜 ? " · 가짜" : ""} · ${글(짧은시각(r.실행끝시각 || r.만든시각))}</div></div>` : "") +
      (상.값.가짜모드 ? `<span class="hint">가짜 실행 모드: 승인해도 TRIPO에 요청하지 않습니다.</span>` : ""));
  }
  function 십그리기() {
    const 고르기 = `<div class="seg" role="group" aria-label="고르기"><button type="button" data-방식="모음"${상.방식 === "모음" ? ' class="on"' : ""}>모음에서 고르기</button><button type="button" data-방식="트리포"${상.방식 === "트리포" ? ' class="on"' : ""}>TRIPO로 만들기</button></div>`;
    return `<div class="note"><div class="ttl">고르기</div>${고르기}</div>` + (상.방식 === "모음" ? 목록칸() : 트리포칸()) + 끝칸();
  }

  // ---------------------------------------------------------------- 10단계 미리 보기
  function 미리주소(n) {
    const m = 상.값 && 상.값.미리;
    const 쪽 = m && (상.켬 && m.켠것 && m.켠것.짝[n] ? m.켠것 : m.끈것 && m.끈것.짝[n] ? m.끈것 : null);
    if (쪽) return {주소: 쪽.주소, 동작: 쪽.짝[n], 누구: 쪽 === m.켠것 ? "이 캐릭터 · 자동 처리 켬" : "이 캐릭터 · 자동 처리 끔"};
    return {주소: `/api/동작/파일?이름=${encodeURIComponent(상.이름)}&종류=모음`, 동작: n, 누구: "원래 인형 · 이 캐릭터로 준비 중"};
  }
  async function 미리열기(n) {
    if (!보()) return;
    const p = 미리주소(n);
    상.미리 = {이름: n, ...p, 실패: ""};
    미리그리기(); 그리기();
    const 됨 = await 보().미리보기(p.주소);
    if (!상.미리 || 상.미리.이름 !== n) return;
    const c = 보().동작정보().목록.find((x) => x.이름 === p.동작 || x.이름.split("|").pop() === p.동작);
    if (!됨 || !c) { 상.미리.실패 = 됨 ? `이 GLB에 '${n}' 동작이 없습니다` : "미리 보기 GLB를 띄우지 못했습니다"; 미리그리기(); return; }
    보().동작정하기({이름: c.이름, 시각: c.시작, 재생: true});
    미리그리기();
  }
  async function 미리끝() {
    상.미리 = null;
    미리줄.remove();
    if (보()) await 보().미리보기(null);
    if (window.리깅단계 && 상.단계 === 10) window.리깅단계.다시읽기();
    그리기();
  }
  function 미리그리기() {
    if (!상.미리 || 상.단계 !== 10 || !보()) { 미리줄.remove(); return; }
    const 도구 = 보().내부.뿌리.querySelector(".tools");
    if (도구 && !미리줄.isConnected) 도구.appendChild(미리줄);
    const d = 보().동작정보();
    미리줄.innerHTML = `<span class="mst">미리 보기: <b>${글(상.미리.이름)}</b> · ${글(상.미리.누구)}</span>` +
      `<button type="button" class="tb${d.재생 ? " on" : ""}" id="p14play"${d.이름 ? "" : " disabled"}>${d.재생 ? "멈춤" : "재생"}</button>` +
      `<button type="button" class="tb" id="p14stop" title="작업본(옮긴 동작)으로 돌아갑니다. 칠하기는 옮긴 동작에서만">미리 보기 끝</button>` +
      `<span class="hint">미리 보기는 고르기 위한 것이라 관통 검사를 하지 않습니다(옮긴 뒤에 함).</span>` +
      (상.미리.실패 ? `<span class="hint ng">${글(상.미리.실패)}</span>` : "");
  }
  미리줄.addEventListener("click", (ev) => {
    const b = ev.target.closest("button");
    if (!b || b.disabled) return;
    if (b.id === "p14stop") 미리끝();
    if (b.id === "p14play") { 보().동작정하기({재생: !보().동작정보().재생}); 미리그리기(); }
  });
  window.addEventListener("보기3d장", () => { if (상.미리 && 상.단계 === 10) { const b = 미리줄.querySelector("#p14play"), d = 보().동작정보(); if (b && b.textContent !== (d.재생 ? "멈춤" : "재생")) 미리그리기(); } });

  // ---------------------------------------------------------------- 11단계
  function 유니티칸() {
    const u = 상.값.Unity, 경로 = 상.경로글 ?? u.경로, 넣을 = 상.넣을글 ?? u.넣을이름;
    const 버전 = !u.있음 ? "—" : u.버전같음 ? `<span class="ok">${글(u.버전)} ✓</span>` : `<span class="ng">${글(u.버전)} ≠ SSOT ${글(u.SSOT버전)}</span>`;
    return 칸("Unity 프로젝트", `<div class="kv g1kv"><div>경로</div><div>${u.경로 ? `<code>${글(u.경로)}</code>` : "아직 없음"}</div>` +
      `<div>버전</div><div>${버전}</div><div>가져오기 방식</div><div>${글(u.방식)} · 텍스처 꺼내기 · 클립마다 전체 뼈 마스크</div>` +
      `<div>넣을 곳</div><div><code>${글(u.넣을곳)}/${글(u.넣을이름 || "?")}.fbx</code></div></div>` +
      `<label class="p14in">프로젝트 폴더<input type="text" id="p14path" value="${글(경로)}" placeholder="C:\\Users\\…\\MyGame" spellcheck="false"></label>` +
      `<label class="p14in">넣을 이름(영어)<input type="text" id="p14name" value="${글(넣을)}" placeholder="OnsenGirl" spellcheck="false"></label>` +
      `<button type="button" class="tb" id="p14setpath"${잠금() || 상.누르는중 ? " disabled" : ""} title="처음 한 번 정하면 캐릭터 설정(상태.json)에 저장됩니다. Unity 프로젝트에는 쓰지 않습니다">경로 고르기</button>` +
      (u.잠김 ? `<span class="hint ng">${글(u.잠김)} — 내보내기 잠김</span>` : "") +
      (u.열림 ? `<span class="hint wa">Unity가 열려 있습니다(Temp/UnityLockfile). 창 없는 실행이 막힐 수 있으니 내보내기 전에 닫아 주세요.</span>` : "") +
      (u.같은이름.length ? `<span class="hint wa">같은 이름이 이미 있습니다: ${글(u.같은이름.join(", "))}</span>` : ""));
  }
  function 검사칸() {
    const v = 상.값, 표 = v.검사표, u = v.Unity;
    const 막음 = 잠금() ? "다른 탭에서 열려 있습니다" : u.잠김 ? u.잠김 : !v.동작.length ? "옮긴 동작이 없습니다(10단계)" : u.같은이름.length && !상.덮어쓰기 ? "같은 이름이 있습니다 — 덮어쓰기를 체크하세요" : 상.누르는중 ? "보내는 중…" : "";
    let 안 = `<div class="kv g1kv"><div>FBX</div><div><code>${글(u.넣을이름 || "?")}.fbx</code></div><div>동작</div><div title="${글(v.동작.join(", "))}">${글(v.동작.length)}개${v.동작.length ? ` · ${글(v.동작.slice(0, 3).map((x) => x.split("|").pop()).join(", "))}${v.동작.length > 3 ? " …" : ""}` : ""}</div></div>`;
    if (표) {
      const 색 = {통과: "ok", 경고: "wa", 실패: "ng"};
      안 += `<table class="t"><thead><tr><th>항목</th><th>결과</th></tr></thead><tbody>${표.검사.map((x) => `<tr><td>${글(x.항목)}${x.글 ? `<span class="hint">${글(x.글)}</span>` : ""}</td><td><span class="${색[x.상태]}">${글(x.상태)}</span></td></tr>`).join("")}` +
        ["7-5", "7-6", "7-7"].map((k) => `<tr><td>${글({"7-5": "7-5 Unity 설정", "7-6": "7-6 자세·거리", "7-7": "7-7 Play 모드"}[k])}</td><td>${표.표시[k] ? `<span class="ok">✓</span>` : `<span class="ng">✗</span>`}</td></tr>`).join("") + `</tbody></table>` +
        `<div class="kv g1kv"><div>보낸 파일</div><div>${표.파일.map((x) => `<code>${글(x.경로)}</code>`).join(" ") || "—"}</div><div>시각</div><div>${글(짧은시각(표.만든시각))}</div>${표.사본 ? `<div>덮기 전 사본</div><div><code>${글(표.사본)}</code></div>` : ""}</div>` +
        (v.검사표옛것 ? `<span class="hint wa">지금 작업본보다 오래된 검사표입니다. 다시 내보내야 합니다.</span>` : "");
    } else 안 += `<span class="hint">내보낸 뒤 에이전트가 검사표를 채웁니다(경고는 주황, 막지 않음).</span>`;
    return 칸("보낼 파일 검사표", 안 +
      (u.같은이름.length ? `<label class="pchk p14chk"><input type="checkbox" id="p14over"${상.덮어쓰기 ? " checked" : ""}><span>덮어쓰기(덮기 전에 사본을 남김)</span></label>` : "") +
      `<button type="button" class="tb" id="p14export"${막음 ? ` disabled title="${글(막음)}"` : ` title="에이전트가 FBX를 내보내 Unity에 넣고 설정·찍기를 합니다"`}>내보내기</button>` +
      (v.요청 ? `<span class="hint">마지막 요청 ${글(짧은시각(v.요청.만든시각))}${표 && 표.요청파일 === v.요청.파일 ? " · 결과 받음" : " · 에이전트 기다림"}</span>` : "") + 실패줄());
  }
  function 찍은칸() {
    const 표 = 상.값.검사표;
    if (!표 || !(표.그림 || []).length) return 칸("Unity에서 찍은 모습", `<span class="hint">Play 모드에서 찍은 그림(7-7)이 오면 여기에 보입니다.</span>`);
    return 칸("Unity에서 찍은 모습", 섬네일(표.그림) +
      (상.값.봄 ? `<span class="ok">✓ 봄</span>` : `<button type="button" class="tb" id="p14seen"${잠금() || 상.누르는중 ? " disabled" : ""} title="그림을 열어 보고 누르세요">봄</button>`));
  }
  function 십일그리기() { return 유니티칸() + 검사칸() + 찍은칸() + 끝칸(); }

  // ---------------------------------------------------------------- 그리기·단추
  function 그리기() {
    const 안 = 기둥.querySelector("#p14in");
    if (상.오류) 안.innerHTML = `<div class="note ng">${글(상.오류)}</div>`;
    else if (!상.값) 안.innerHTML = `<div class="note"><span class="hint">불러오는 중…</span></div>`;
    else {
      const 스크롤 = 안.scrollTop, 목 = 안.querySelector(".p14list"), 목스크롤 = 목 ? 목.scrollTop : 0;
      const 초점 = document.activeElement && 안.contains(document.activeElement) ? document.activeElement.id : "";
      안.innerHTML = 상.단계 === 10 ? 십그리기() : 십일그리기();
      안.scrollTop = 스크롤;
      const 새목 = 안.querySelector(".p14list");
      if (새목) 새목.scrollTop = 목스크롤;
      if (초점 && document.getElementById(초점)) document.getElementById(초점).focus();
    }
  }
  async function 보내기(경로, 몸) {
    const r = await fetch(경로, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({이름: 상.이름, 탭: window.탭id, ...몸})});
    const v = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(v.오류 || r.status);
    return v;
  }
  async function 누르기(경로, 몸) {
    상.누르는중 = true; 상.실패 = ""; 그리기();
    try { await 보내기(경로, 몸); return true; } catch (e) { 상.실패 = `하지 못함: ${e instanceof TypeError ? "서버와 연결 끊김" : e.message}`; return false; }
    finally { 상.누르는중 = false; await 다시읽기(); if (window.결정 && window.결정.다시읽기) window.결정.다시읽기(); }
  }
  기둥.addEventListener("click", (ev) => {
    const b = ev.target.closest("button");
    if (!b || b.disabled) return;
    if (b.dataset.방식) { 상.방식 = b.dataset.방식; 그리기(); return; }
    if (b.dataset.미리) { 미리열기(b.dataset.미리); return; }
    if (b.dataset.아홉) {   // 새 관통: 9단계 보기로 열기(그 동작을 고른 채)
      if (window.리깅단계) window.리깅단계.아홉단계로(b.dataset.아홉);
      const 단 = document.querySelector('#steps [data-i="8"], [data-i="8"]');
      if (단) 단.click();
      return;
    }
    if (b.id === "p14move") 누르기("/api/동작/옮기기", {자동처리: true});
    if (b.id === "p14setpath") {
      const 경로 = 기둥.querySelector("#p14path").value, 넣을 = 기둥.querySelector("#p14name").value;
      누르기("/api/내보내기/경로", {경로, 넣을이름: 넣을}).then((됨) => { if (됨) { 상.경로글 = null; 상.넣을글 = null; 그리기(); } });
    }
    if (b.id === "p14export") 누르기("/api/내보내기/요청", {덮어쓰기: 상.덮어쓰기}).then((됨) => { if (됨) { 상.덮어쓰기 = false; 그리기(); } });
    if (b.id === "p14seen") 누르기("/api/내보내기/봄", {});
  });
  기둥.addEventListener("change", (ev) => {
    const t = ev.target;
    if (t.dataset && t.dataset.고름 !== undefined) {
      const 고른 = new Set(상.값.고른 || []);
      if (t.checked) 고른.add(t.dataset.고름); else 고른.delete(t.dataset.고름);
      상.값.고른 = [...고른];
      누르기("/api/동작/고르기", {고른: [...고른]});
    }
    if (t.id === "p14on") { 상.켬 = t.checked; if (상.미리) 미리열기(상.미리.이름); else 그리기(); }
    if (t.id === "p14over") { 상.덮어쓰기 = t.checked; 그리기(); }
  });
  기둥.addEventListener("input", (ev) => {
    if (ev.target.id === "p14path") 상.경로글 = ev.target.value;
    if (ev.target.id === "p14name") 상.넣을글 = ev.target.value;
  });

  async function 다시읽기() {
    if (!상.이름) return;
    const 번호 = ++상.묻는번호, 이름 = 상.이름, 단계 = 상.단계;
    try {
      const r = await fetch(`/api/동작?이름=${encodeURIComponent(이름)}&단계=${단계}`, {cache: "no-store"});
      const v = await r.json();
      if (번호 !== 상.묻는번호) return;
      if (!r.ok) throw new Error(v.오류 || r.status);
      const 앞미리 = 상.값 && 상.값.미리;
      상.값 = v; 상.오류 = "";
      // 원래 인형으로 보던 동작이 이 캐릭터로 준비되면 저절로 바꾼다
      if (상.미리 && 상.단계 === 10 && (!앞미리 || 앞미리.상태 !== (v.미리 || {}).상태 || Boolean(앞미리.끈것) !== Boolean((v.미리 || {}).끈것))) {
        const p = 미리주소(상.미리.이름);
        if (p.주소 !== 상.미리.주소) 미리열기(상.미리.이름);
      }
    } catch (e) {
      if (번호 !== 상.묻는번호) return;
      상.오류 = `옆 기둥을 읽지 못함: ${e instanceof TypeError ? "서버와 연결 끊김" : e.message}`;
    }
    그리기();
  }

  function 붙이기(이름, 단계) {
    if ((단계 !== 10 && 단계 !== 11) || !보()) { 떼기(); return; }
    const 뿌리 = 보().내부.뿌리, 줄 = 뿌리.querySelector(".vrow"), 몸 = document.getElementById("body");
    if (!뿌리.isConnected || !줄 || !몸) { 떼기(); return; }
    if (이름 !== 상.이름 || 단계 !== 상.단계) {
      if (상.미리) { 상.미리 = null; 미리줄.remove(); 보().미리보기(null); }
      상.값 = null; 상.오류 = ""; 상.바깥 = null; 상.실패 = ""; 상.덮어쓰기 = false; 상.경로글 = null; 상.넣을글 = null;
    }
    상.이름 = 이름; 상.단계 = 단계;
    줄.appendChild(기둥);
    사람줄.innerHTML = 단계 === 10
      ? `<b>사람이 하는 일</b> · 목록에서 동작 이름을 눌러 이 캐릭터에 입혀 봄(준비 전에는 원래 인형). 쓸 동작을 체크하고 '옮기기'. 옮긴 동작을 재생해 이상한 곳은 멈춘 장면에서 칠하거나 시간 막대를 끌어 '구간 리포트' → 보내기. 새 관통이 뜬 동작은 '9단계 보기로'.`
      : `<b>사람이 하는 일</b> · 처음 한 번 Unity 프로젝트 폴더와 넣을 이름을 정함(버전이 다르면 잠김). '내보내기'를 누르고 Claude 앱에 알림. 검사표(주황은 경고, 막지 않음)와 Unity에서 찍은 Play 모드 그림을 열어 보고 '봄'.`;
    몸.appendChild(사람줄);
    그리기();
    다시읽기();
  }
  function 떼기() {
    if (상.미리 && 보()) 보().미리보기(null);
    상.미리 = null;
    기둥.remove(); 미리줄.remove(); 사람줄.remove();
    상.이름 = null; 상.단계 = 0;
  }
  function 바깥바뀜(값) {
    if (!상.이름) return;
    if (값 !== undefined && 값 !== 상.바깥) { const 처음 = 상.바깥 === null; 상.바깥 = 값; if (!처음) 다시읽기(); }
  }
  window.동작단계 = {붙이기, 떼기, 바깥바뀜, 다시읽기, 미리열기, 미리끝, 상태: 상};
  window.dispatchEvent(new Event("동작단계준비"));
})();
