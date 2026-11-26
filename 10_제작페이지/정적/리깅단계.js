// 8·9단계 리깅 화면 (작업 묶음 W13, 기능명세 2부 20·21절, SSOT 단계/6_리깅)
// 8: 보기 줄 오른쪽 옆 기둥(리그 체크 · 확인 표 · 뼈대 · 끝나는 조건), 3D 보기에 뼈대 선(기본 켬).
// 9: 도구 줄 끝에 동작 고르기 · 재생 단추 · 시간 막대(관통이 남은 장은 빨간 눈금, 끌어서 구간 고르기 → 구간 리포트),
//    옆 기둥(시험 동작 · 교차 · 끝나는 조건), 표시 목록 아래 후보 비교(있을 때만). 붓은 멈춘 장면에서만(칠하기.js가 칠못함()을 봄).
// 동작 재생 자체는 보기3d.js(동작정하기·동작정보). 장 번호 = 시작장 + (초 − 동작 첫 초) × 장초당(Blender 장 번호와 같게).
(() => {
  const 글 = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const 그림주소 = (x) => `/api/그림/파일?경로=${encodeURIComponent(x)}`;
  const 짧은시각 = (t) => String(t || "").replace("T", " ").slice(5, 16);
  const 기본장초당 = 30;    // GLB 정보·교차 기록 모두에 장초당이 없을 때(어림으로 표시)
  const 끌기문턱 = 4;       // 시간 막대에서 이보다 덜 끌면 그 장으로 옮기기만(화면 화소)
  const 상 = {이름: null, 단계: 0, 값: null, 바깥: null, 오류: "", 묻는번호: 0, 구간: null, 끌기: null, 고르는중: false, 실패: "", 글: "", 처음동작: true, 다음동작: null};
  window.리깅단계상태 = 상;   // 시험·검사용으로 읽기만

  const 기둥 = document.createElement("div");
  기둥.className = "g1aside p10aside";
  기둥.innerHTML = `<div class="g1asidein" id="p13in"></div>`;
  const 막대 = document.createElement("div");
  막대.className = "tgrp p13bar";
  막대.setAttribute("aria-label", "동작");
  막대.dataset.자체단추 = "";   // 보기3d.js 상태줄이 이 안의 단추를 켜고 끄지 않게
  const 비교칸 = document.createElement("div");
  비교칸.className = "note p13cmp";
  비교칸.dataset.순서 = "단계마다 더 있는 것";
  const 사람줄 = document.createElement("div");
  사람줄.className = "human";
  사람줄.dataset.순서 = "사람이 하는 일";

  const 보 = () => window.보기3d;
  const 붙음 = () => Boolean(상.이름 && (기둥.isConnected || 막대.isConnected));   // W14: 10단계는 막대만 붙음
  function 칸(제목, 안) { return `<div class="note"><div class="ttl">${글(제목)}</div>${안}</div>`; }
  function 섬네일(목록) {
    if (!목록 || !목록.length) return "";
    return `<div class="p10th">${목록.map((x) => `<a href="${그림주소(x)}" target="_blank" rel="noopener" title="${글(x)} — 크게 보기"><img src="${그림주소(x)}" alt="${글(x.split("/").pop())}" loading="lazy"></a>`).join("")}</div>`;
  }
  const 표시 = (v) => v === true ? `<span class="ok">✓</span>` : v === false ? `<span class="ng">✗</span>` : "—";

  // ---------------------------------------------------------------- 장 번호
  function 교차동작(이름) { return ((상.값 && 상.값.교차 && 상.값.교차.동작) || []).find((x) => x.이름 === 이름) || null; }
  function 틀(이름) {
    const 목 = 보() && 보().동작정보().목록.find((c) => c.이름 === 이름);
    if (!목 || !상.값) return null;
    const 교 = 교차동작(이름) || {};
    const 장초당 = 교.장초당 || 상.값.장초당 || 기본장초당;
    const 시작장 = 교.시작장 ?? ((상.값.동작장 || {})[이름] || [0])[0];
    const 장수 = Math.max(1, Math.round((목.끝 - 목.시작) * 장초당) + 1);
    return {장초당, 시작장, 끝장: 시작장 + 장수 - 1, 장수, t0: 목.시작, 어림: !교.장초당 && !상.값.장초당};
  }
  function 장(f, 초) { return Math.min(f.끝장, Math.max(f.시작장, f.시작장 + Math.round((초 - f.t0) * f.장초당))); }
  function 초(f, n) { return f.t0 + (n - f.시작장) / f.장초당; }
  function 짧은이름(n) {
    const 보임 = 상.값 && 상.값.동작보임 && 상.값.동작보임[n];
    return 보임 || String(n || "").split("|").pop();
  }

  // ---------------------------------------------------------------- 칠하기.js가 묻는 것
  function 칠못함() {
    if (!붙음()) return "";
    const b = 보() && 보().상태;
    if (b && b.네방향) return "네 방향 보기에서는 칠할 수 없습니다. '네 방향'을 끄고 한 방향에서 칠하세요";
    if ((상.단계 === 9 || 상.단계 === 10) && b && b.동작.재생) return "재생 중에는 칠할 수 없습니다. 멈춘 장면에서 칠하세요";
    return "";
  }
  function 동작자리() {
    if (!붙음() || (상.단계 !== 9 && 상.단계 !== 10)) return null;
    const d = 보().동작정보(), f = d.이름 && 틀(d.이름);
    if (!f) return null;
    if (상.구간) return {이름: d.이름, 시작장: 상.구간[0], 끝장: 상.구간[1]};
    const n = 장(f, d.시각);
    return {이름: d.이름, 시작장: n, 끝장: n};
  }
  function 장으로(동작) {
    if (!붙음() || (상.단계 !== 9 && 상.단계 !== 10) || !동작) return;
    const f = 틀(동작.이름);
    if (!f) { 상.글 = `이 모델에 '${짧은이름(동작.이름)}' 동작이 없습니다(작업본이 바뀌었을 수 있음)`; 막대그리기(); return; }
    상.구간 = 동작.끝장 > 동작.시작장 ? [동작.시작장, 동작.끝장] : null;
    보().동작정하기({이름: 동작.이름, 시각: 초(f, 동작.시작장), 재생: false});
  }

  // ---------------------------------------------------------------- 8단계 옆 기둥
  function 체크칸() {
    const v = 상.값, c = v.체크, r = v.요청;
    const 결과 = !c ? `<span class="hint">아직 하지 않음</span>` : c.riggable === true ? `<span class="ok">✓ riggable true</span>` : `<span class="ng">✗ riggable false</span>`;
    const 잠금 = document.body.dataset.잠금 === "다른 탭";
    const 막음 = !r ? "에이전트가 아직 입력을 내고 '리깅요청'을 하지 않았습니다" : 잠금 ? "다른 탭에서 열려 있습니다" : 상.고르는중 ? "리그 체크 중…" : "";
    return 칸("리그 체크(무료, 승인 필요 없음)",
      `<div class="kv g1kv"><div>입력</div><div>${r ? `<code>${글(r.입력)}</code>` : "—"}</div><div>결과</div><div>${결과}${c && c.가짜 ? " · 가짜" : ""}</div>` +
      `${c ? `<div>몸 유형</div><div>${글(c.rig_type || "모름")} · 요청 ${글(r ? r.몸 : "—")}</div><div>시각</div><div>${글(짧은시각(c.만든시각))}</div>` : ""}</div>` +
      `<button type="button" class="tb" id="p13check"${막음 ? ` disabled title="${글(막음)}"` : ` title="TRIPO에 riggable인지 묻습니다(크레딧을 쓰지 않음)"`}>${상.고르는중 ? "리그 체크 중…" : "리그 체크"}</button>` +
      (v.체크까닭 ? `<span class="hint wa">${글(v.체크까닭)}</span>` : r ? `<span class="hint ok">승인할 수 있습니다(결정 칸의 승인 상자).</span>` : "") +
      (v.가짜모드 ? `<span class="hint">가짜 실행 모드: 리그 체크도 흉내만 냅니다(서버를 --가짜결과 실패로 켜면 false).</span>` : "") +
      (상.실패 ? `<span class="hint ng">${글(상.실패)}</span>` : ""));
  }
  function 확인표칸() {
    const v = 상.값, c = v.확인, k = v.체크;
    const 줄 = [["리그 체크", k ? k.riggable === true : null], ["방향", c ? c.방향 : null], ["되돌리기", c ? c.되돌림 : null],
      ["정점 자리 같음(차 0)", c ? c.정점자리차 === 0 : null], ["UV 같음", c ? c.UV같음 : null], ["가중치 없는 정점 0", c ? c.가중치없는정점 === 0 : null]];
    const 실행 = v.실행 ? `${글(v.실행.실행)}${v.실행.가짜 ? " · 가짜" : ""}${v.실행.끝시각 ? ` · ${글(짧은시각(v.실행.끝시각))}` : ""}` : "아직 없음";
    return 칸("확인 표(6-0)", `<table class="t"><tbody>${줄.map(([t, x]) => `<tr><td>${글(t)}</td><td>${표시(x)}</td></tr>`).join("")}</tbody></table>` +
      `<div class="kv g1kv"><div>오토 리깅</div><div>${실행}</div>${c && c.정점자리차 ? `<div>정점 자리 차</div><div class="ng">${글(c.정점자리차)} mm</div>` : ""}` +
      `${c && c.정점수전 != null ? `<div>정점 수</div><div>${글(c.정점수전)} → ${글(c.정점수후)}${c.정점수다름 ? `<span class="hint">${글(c.정점수다름)}</span>` : ""}</div>` : ""}</div>` +
      (c ? 섬네일(c.그림) : `<span class="hint">받은 뒤 에이전트가 되돌리고 확인합니다('리깅확인').</span>`));
  }
  function 뼈칸() {
    const v = 상.값, c = v.확인, d = 보() ? 보().동작정보() : {뼈수: 0, 뼈이름: []};
    const 수 = c ? c.뼈수 : d.뼈수, 이름들 = (c && c.뼈이름 && c.뼈이름.length ? c.뼈이름 : d.뼈이름);
    if (!수) return 칸("뼈대", `<span class="hint">아직 뼈대가 없습니다(오토 리깅 전).</span>`);
    const 다름 = 수 !== v.SSOT뼈수;
    return 칸("뼈대", `<div class="kv g1kv"><div>뼈 수</div><div>${글(수)}개${c ? "" : "(3D 보기에서 셈)"}</div>` +
      `<div>이름 꼴</div><div title="${글(이름들.join(", "))}">${글(이름들.slice(0, 5).join(", "))}${이름들.length > 5 ? " …" : ""}</div></div>` +
      (다름 ? `<span class="hint wa">SSOT 6_리깅의 TRIPO 뼈대 ${v.SSOT뼈수}개와 다릅니다. 막지 않습니다(뼈 이름 규격은 50_미정과_초안 2절, 사용자 결정 전).</span>` : "") +
      `<span class="hint">도구 줄 '뼈대'로 선을 켜고 끕니다.</span>`);
  }

  // ---------------------------------------------------------------- 9단계 옆 기둥·후보 비교
  function 시험칸() {
    const v = 상.값, d = 보() ? 보().동작정보() : {목록: []};
    const 줄 = v.시험동작.map((x) => `<tr><td>${글(x.이름)}</td><td>${x.있음 ? `<span class="ok">✓</span>` : `<span class="wa">없음</span>`}</td></tr>`).join("");
    return 칸("시험 동작(걷기·달리기·잽·크로스)", `<table class="t"><tbody>${줄}</tbody></table>` +
      `<span class="hint">이 모델의 동작 ${d.목록.length}개. ${v.시험동작.some((x) => !x.있음) ? "없는 시험 동작은 에이전트가 동작옮기기.py로 옮깁니다." : ""}</span>`);
  }
  function 교차칸() {
    const v = 상.값, 교 = v.교차;
    if (!교) return 칸("교차", `<span class="hint">아직 기록이 없습니다. 에이전트가 시험 동작의 교차를 잽니다('리깅교차').</span>`);
    const 줄 = 교.동작.map((x) => `<tr><td title="${글(x.이름)}">${글(짧은이름(x.이름))}</td><td>${글(x.교차수)}</td><td>${(x.관통장 || []).length ? `<span class="ng">${(x.관통장 || []).length}장</span>` : `<span class="ok">0</span>`}</td></tr>`).join("");
    const 그림 = 교.동작.flatMap((x) => x.찍은그림 || []);
    const 없음 = !(보() && 보().상태.지금);
    return 칸("교차", `<table class="t"><thead><tr><th>동작</th><th>교차</th><th>관통 남은 장</th></tr></thead><tbody>${줄}</tbody></table>` +
      `<div class="kv g1kv"><div>잰 시각</div><div>${글(짧은시각(교.만든시각))}</div>${교.확인범위 ? `<div>확인 범위</div><div>${글(교.확인범위)}</div>` : ""}</div>` +
      (v.교차옛것 ? `<span class="hint wa">지금 작업본보다 오래된 기록입니다. 에이전트가 다시 잽니다.</span>` : "") +
      (그림.length ? `<div class="hint">${없음 ? "3D로 재생하지 못해 미리 찍은 그림(동작찍기.py)을 보입니다" : "미리 찍은 그림(누르면 크게)"}</div>${섬네일(그림)}` : ""));
  }
  function 넘어온칸() {   // W14: 10단계에서 리깅 쪽으로 넘어온 리포트
    const 목 = (상.값 && 상.값.넘어온) || [];
    if (!목.length) return "";
    return 칸(`10단계에서 넘어온 리포트 ${목.length}개`, `<table class="t"><tbody>${목.map((x) => `<tr><td>${글(x.종류 || x.번호)}${x.동작 ? ` · ${글(짧은이름(x.동작.이름))} ${글(x.동작.시작장)}${x.동작.끝장 > x.동작.시작장 ? `~${글(x.동작.끝장)}` : ""}장` : ""}</td><td>${x.처리 === "고침" ? `<span class="ok">고침</span>` : `<span class="wa">${글(x.처리 || "")}</span>`}</td></tr>` +
      (x.메모 || x.이유 ? `<tr><td colspan="2"><span class="hint">${글(x.메모 || x.이유)}</span></td></tr>` : "")).join("")}</tbody></table>` +
      `<span class="hint">10단계 에이전트가 "리깅 쪽(가중치·옷 뼈)"으로 정한 것입니다.</span>`);
  }
  function 끝칸() {
    const 모 = 상.값.모자람 || [];
    return 칸("끝나는 조건", 모.length ? `<ul class="lack">${모.map((x) => `<li class="ng">${글(x)}</li>`).join("")}</ul>` : `<span class="ok">✓ 모두 채움 — '이 단계 끝'을 누를 수 있습니다</span>`);
  }
  function 비교그리기() {
    const 비 = 상.값 && 상.단계 === 9 ? 상.값.비교 : null, 몸 = document.getElementById("body");
    if (!비 || !몸 || !붙음()) { 비교칸.remove(); return; }
    if (!비교칸.isConnected) 몸.insertBefore(비교칸, 사람줄.isConnected ? 사람줄 : null);
    const 고른 = 상.값.고른후보, 잠금 = document.body.dataset.잠금 === "다른 탭";
    비교칸.innerHTML = `<div class="ttl">후보 비교 · ${글(짧은시각(비.만든시각))}</div>${비.설명 ? `<span class="hint">${글(비.설명)}</span>` : ""}` +
      `<div class="p13rows">${비.후보.map((x) => {
        const 골랐음 = 고른 && 고른.번호 === x.번호;
        return `<div class="p13row"><div class="kv g1kv"><div>${글(x.번호)}</div><div><b>${글(x.이름)}</b></div><div>도구</div><div>${글(x.도구)}${x.값 ? ` · ${글(x.값)}` : ""}</div>` +
          `${x.교차수 != null ? `<div>교차</div><div>${글(x.교차수)}</div>` : ""}${x.새흠 ? `<div>새 흠</div><div class="ng">${글(x.새흠)}</div>` : ""}</div>${섬네일(x.그림)}` +
          `<button type="button" class="tb${골랐음 ? " on" : ""}" data-고르기="${글(x.번호)}"${잠금 || 상.고르는중 ? " disabled" : ""} title="${골랐음 ? "고른 후보입니다" : "이 후보를 고릅니다(에이전트가 작업본에 넣음)"}">${골랐음 ? "고름 ✓" : "이 후보 고르기"}</button></div>`;
      }).join("")}</div>` +
      (고른 ? `<span class="hint ok">${글(고른.번호)} ${글(고른.이름)}을 골랐습니다 — Claude 앱에서 알려 주세요.</span>` : `<span class="hint">새 흠이 있는 후보도 고를 수 있습니다(그림을 보고 정함).</span>`) +
      (상.실패 ? `<span class="hint ng">${글(상.실패)}</span>` : "");
  }
  function 그리기() {
    const 안 = 기둥.querySelector("#p13in");
    if (상.오류) 안.innerHTML = `<div class="note ng">${글(상.오류)}</div>`;
    else if (!상.값) 안.innerHTML = `<div class="note"><span class="hint">불러오는 중…</span></div>`;
    else {
      const 스크롤 = 안.scrollTop;
      안.innerHTML = 상.단계 === 8 ? 체크칸() + 확인표칸() + 뼈칸() + 끝칸() : 시험칸() + 넘어온칸() + 교차칸() + 끝칸();
      안.scrollTop = 스크롤;
    }
    비교그리기();
    막대그리기();
  }

  // ---------------------------------------------------------------- 9단계 시간 막대
  function 막대그리기() {
    if ((상.단계 !== 9 && 상.단계 !== 10) || !보()) { 막대.innerHTML = ""; return; }
    막대.hidden = Boolean(보().상태.미리주소);   // W14: 10단계 미리 보기 중에는 동작단계.js의 미리 보기 줄이 대신
    if (막대.hidden) return;
    const d = 보().동작정보(), f = d.이름 ? 틀(d.이름) : null;
    if (!d.목록.length) {
      막대.innerHTML = `<span class="hint">${상.단계 === 10 ? "작업본에 옮긴 동작이 없습니다. 옆 기둥에서 동작을 고르고 '옮기기'를 누르면 에이전트가 옮깁니다(미리 보기는 동작 이름을 누름)." : "이 모델에는 동작이 없습니다. 에이전트가 시험 동작을 옮기면 재생할 수 있습니다."}</span>`;
      return;
    }
    const 고르기 = [`<button type="button" data-동작=""${d.이름 ? "" : ' class="on"'} title="기본 자세">자세 없음</button>`]
      .concat(d.목록.map((c) => `<button type="button" data-동작="${글(c.이름)}"${c.이름 === d.이름 ? ' class="on"' : ""} title="${글(c.이름)}">${글(짧은이름(c.이름))}</button>`)).join("");
    const 지금 = f ? 장(f, d.시각) : 0;
    const 자리 = (n) => f ? (f.장수 > 1 ? (n - f.시작장) / (f.장수 - 1) * 100 : 0) : 0;
    const 관통 = f ? ((교차동작(d.이름) || {}).관통장 || []).filter((n) => n >= f.시작장 && n <= f.끝장) : [];
    const 구간 = 상.구간 && f ? `<span class="p13rng" style="left:${자리(상.구간[0])}%;width:${자리(상.구간[1]) - 자리(상.구간[0])}%"></span>` : "";
    // 사용자 표시(붓·구간 리포트)도 이 동작의 장이면 빨간 눈금으로. 구간이면 그 폭만큼 빨간 띠
    const 사용자 = f ? ((window.칠하기 && window.칠하기.상태.표시) || []).filter((x) => x.자리 && x.자리.동작 && x.자리.동작.이름 === d.이름) : [];
    const 사용자눈금 = 사용자.map((x) => {
      const a = Math.max(f.시작장, x.자리.동작.시작장), b = Math.min(f.끝장, x.자리.동작.끝장);
      if (b < a) return "";
      const 글귀 = `${x.번호} 사용자 표시 · ${a === b ? `${a}장` : `${a}~${b}장`}`;
      return a === b ? `<span class="p13tick" style="left:${자리(a)}%" title="${글(글귀)}"></span>`
        : `<span class="p13urng" style="left:${자리(a)}%;width:${자리(b) - 자리(a)}%" title="${글(글귀)}"></span>`;
    }).join("");
    const 못함 = !f ? "동작을 먼저 고르세요" : "";
    막대.innerHTML = `<div class="seg" id="p13clip" role="group" aria-label="동작 고르기">${고르기}</div>` +
      `<button type="button" class="tb" id="p13prev"${못함 ? ` disabled title="${못함}"` : ' title="한 장 뒤"'}>◀ 한 장</button>` +
      `<button type="button" class="tb${d.재생 ? " on" : ""}" id="p13play"${못함 ? ` disabled title="${못함}"` : ` title="${d.재생 ? "멈춤(붓은 멈춘 장면에서만)" : "재생"}"`}>${d.재생 ? "멈춤" : "재생"}</button>` +
      `<button type="button" class="tb" id="p13next"${못함 ? ` disabled title="${못함}"` : ' title="한 장 앞"'}>한 장 ▶</button>` +
      `<div class="p13track" id="p13track" title="누르면 그 장으로, 끌면 구간 고르기. 빨간 눈금: 관통이 남은 장(에이전트 교차 기록)과 사용자가 표시한 장">` +
      `${관통.map((n) => `<span class="p13tick" style="left:${자리(n)}%" title="${n}장 관통"></span>`).join("")}${사용자눈금}${구간}` +
      `${f ? `<span class="p13head" style="left:${자리(지금)}%"></span>` : ""}</div>` +
      `<span class="mst" id="p13fr" title="${f && f.어림 ? `장초당을 몰라 ${기본장초당}장/초로 셈(어림)` : "Blender 장 번호"}">${f ? `${지금}장 / ${f.시작장}~${f.끝장}${f.어림 ? " (어림)" : ""}` : "—"}</span>` +
      `<button type="button" class="tb" id="p13range"${!상.구간 || d.재생 ? ` disabled title="${d.재생 ? "멈춘 뒤 구간 리포트" : "시간 막대를 끌어 구간을 고르세요"}"` : ` title="고른 구간을 칠할 처리 종류로 표시에 넣습니다(자리를 칠하지 않아도 됨)"`}>구간 리포트${상.구간 ? ` ${상.구간[0]}~${상.구간[1]}장` : ""}</button>` +
      (상.글 ? `<span class="hint wa">${글(상.글)}</span>` : "");
  }
  function 장머리만() {   // 재생 중에는 막대 전체를 다시 그리지 않고 머리와 글만
    const d = 보().동작정보(), f = d.이름 ? 틀(d.이름) : null, h = 막대.querySelector(".p13head"), t = 막대.querySelector("#p13fr");
    if (!f || !h || !t) { 막대그리기(); return; }
    const n = 장(f, d.시각);
    h.style.left = `${f.장수 > 1 ? (n - f.시작장) / (f.장수 - 1) * 100 : 0}%`;
    t.textContent = `${n}장 / ${f.시작장}~${f.끝장}${f.어림 ? " (어림)" : ""}`;
  }
  function 막대장(ev) {
    const d = 보().동작정보(), f = d.이름 ? 틀(d.이름) : null, r = 막대.querySelector("#p13track").getBoundingClientRect();
    if (!f) return null;
    const x = Math.min(1, Math.max(0, (ev.clientX - r.left) / Math.max(1, r.width)));
    return f.시작장 + Math.round(x * (f.장수 - 1));
  }
  막대.addEventListener("pointerdown", (ev) => {
    const t = ev.target.closest("#p13track");
    if (!t || ev.button !== 0) return;
    const n = 막대장(ev);
    if (n == null) return;
    상.끌기 = {x: ev.clientX, 처음: n, 움직임: 0};
    t.setPointerCapture(ev.pointerId);
    const f = 틀(보().동작정보().이름);
    상.구간 = null; 상.글 = "";
    보().동작정하기({시각: 초(f, n), 재생: false});
  });
  막대.addEventListener("pointermove", (ev) => {
    if (!상.끌기) return;
    상.끌기.움직임 = Math.max(상.끌기.움직임, Math.abs(ev.clientX - 상.끌기.x));
    if (상.끌기.움직임 < 끌기문턱) return;
    const n = 막대장(ev), f = 틀(보().동작정보().이름);
    if (n == null || !f) return;
    상.구간 = [Math.min(상.끌기.처음, n), Math.max(상.끌기.처음, n)];
    if (상.구간[0] === 상.구간[1]) 상.구간 = null;
    보().동작정하기({시각: 초(f, n), 재생: false});
  });
  const 끌기끝 = () => { if (상.끌기) { 상.끌기 = null; 막대그리기(); } };
  막대.addEventListener("pointerup", 끌기끝);
  막대.addEventListener("pointercancel", 끌기끝);
  막대.addEventListener("click", (ev) => {
    const b = ev.target.closest("button");
    if (!b || b.disabled) return;
    const d = 보().동작정보();
    if (b.dataset.동작 !== undefined) {
      상.구간 = null; 상.글 = "";
      const f = b.dataset.동작 ? 틀(b.dataset.동작) : null;
      보().동작정하기({이름: b.dataset.동작 || null, 시각: f ? f.t0 : 0, 재생: false});
      return;
    }
    const f = d.이름 ? 틀(d.이름) : null;
    if (!f) return;
    if (b.id === "p13play") 보().동작정하기({재생: !d.재생});
    if (b.id === "p13prev" || b.id === "p13next") {
      const n = 장(f, d.시각) + (b.id === "p13next" ? 1 : -1);
      보().동작정하기({시각: 초(f, n > f.끝장 ? f.시작장 : n < f.시작장 ? f.끝장 : n), 재생: false});
    }
    if (b.id === "p13range" && 상.구간 && window.칠하기) {
      if (window.칠하기.구간넣기({이름: d.이름, 시작장: 상.구간[0], 끝장: 상.구간[1]})) { 상.구간 = null; 막대그리기(); }
    }
  });
  window.addEventListener("보기3d장", () => {
    if ((상.단계 !== 9 && 상.단계 !== 10) || !붙음()) return;
    if (보().상태.동작.재생 && !상.끌기 && !막대.hidden) 장머리만(); else 막대그리기();
  });
  window.addEventListener("칠하기겹침", () => {   // 표시가 늘거나 줄면 사용자 눈금을 다시 그림
    if ((상.단계 !== 9 && 상.단계 !== 10) || !붙음() || !보() || 보().상태.동작.재생) return;
    막대그리기();
  });
  window.addEventListener("보기3d모델", () => {
    if (!붙음()) return;
    처음동작고르기();
    그리기();
  });
  function 처음동작고르기() {   // 9단계를 처음 열면 첫 시험 동작을 멈춘 채로 고른다
    if (상.단계 !== 9 || !상.처음동작 || !상.값 || !보() || !보().상태.지금) return;
    const d = 보().동작정보();
    상.처음동작 = false;
    const 다음 = 상.다음동작 && d.목록.find((c) => c.이름 === 상.다음동작);   // W14: 10단계 "9단계 보기로 열기"
    상.다음동작 = null;
    if (다음) { 보().동작정하기({이름: 다음.이름, 시각: 다음.시작, 재생: false}); return; }
    if (d.이름 || !d.목록.length) return;
    const 순서 = ["걷기", "달리기", "잽", "크로스"], 보임 = (c) => (상.값.동작보임 || {})[c.이름] || "";
    const 첫 = 순서.map((n) => d.목록.find((c) => 보임(c) === n)).find(Boolean) || d.목록[0];
    보().동작정하기({이름: 첫.이름, 시각: 첫.시작, 재생: false});
  }

  // ---------------------------------------------------------------- 단추(리그 체크·후보 고르기)
  async function 보내기(경로, 몸) {
    const r = await fetch(경로, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(몸)});
    const v = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(v.오류 || r.status);
    return v;
  }
  async function 누르기(경로, 몸) {
    상.고르는중 = true; 상.실패 = ""; 그리기();
    try { await 보내기(경로, 몸); } catch (e) { 상.실패 = `하지 못함: ${e instanceof TypeError ? "서버와 연결 끊김" : e.message}`; }
    finally { 상.고르는중 = false; await 다시읽기(); if (window.결정 && window.결정.다시읽기) window.결정.다시읽기(); }
  }
  기둥.addEventListener("click", (ev) => {
    if (ev.target.closest("#p13check")) 누르기("/api/리깅/리그체크", {이름: 상.이름, 탭: window.탭id});
  });
  비교칸.addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-고르기]");
    if (b && !b.disabled) 누르기("/api/리깅/후보고르기", {이름: 상.이름, 탭: window.탭id, 번호: b.dataset.고르기});
  });

  async function 다시읽기() {
    if (!상.이름) return;
    const 번호 = ++상.묻는번호, 이름 = 상.이름, 단계 = 상.단계;
    try {
      const r = await fetch(`/api/리깅?이름=${encodeURIComponent(이름)}&단계=${단계}`, {cache: "no-store"});
      const v = await r.json();
      if (번호 !== 상.묻는번호) return;
      if (!r.ok) throw new Error(v.오류 || r.status);
      상.값 = v; 상.오류 = "";
    } catch (e) {
      if (번호 !== 상.묻는번호) return;
      상.오류 = `옆 기둥을 읽지 못함: ${e instanceof TypeError ? "서버와 연결 끊김" : e.message}`;
    }
    처음동작고르기();
    그리기();
  }

  function 붙이기(이름, 단계) {
    if ((단계 !== 8 && 단계 !== 9 && 단계 !== 10) || !보()) { 떼기(); return; }
    const 뿌리 = 보().내부.뿌리, 줄 = 뿌리.querySelector(".vrow"), 도구 = 뿌리.querySelector(".tools"), 몸 = document.getElementById("body");
    if (!뿌리.isConnected || !줄 || !도구 || !몸) { 떼기(); return; }
    if (이름 !== 상.이름 || 단계 !== 상.단계) { 상.값 = null; 상.오류 = ""; 상.바깥 = null; 상.구간 = null; 상.글 = ""; 상.실패 = ""; 상.처음동작 = true; }
    상.이름 = 이름; 상.단계 = 단계;
    if (단계 === 10) {   // W14: 10단계는 시간 막대·칠하기만(옆 기둥과 사람이 하는 일은 동작단계.js)
      기둥.remove(); 비교칸.remove(); 사람줄.remove();
      도구.appendChild(막대);
      보().리깅단추(true, false);
      그리기(); 다시읽기();
      return;
    }
    줄.appendChild(기둥);
    if (단계 === 9) 도구.appendChild(막대); else 막대.remove();
    보().리깅단추(true, 단계 === 8);
    사람줄.innerHTML = 단계 === 8
      ? `<b>사람이 하는 일</b> · 에이전트가 입력을 내면 '리그 체크'(무료)를 누름 → true면 결정 칸에서 값·가격을 보고 승인. 받은 뒤 확인 표와 뼈대(도구 줄 '뼈대')를 봄. 뼈 수가 앞 캐릭터와 달라도 막지 않음.`
      : `<b>사람이 하는 일</b> · 시험 동작을 재생해 봄(도구 줄 '네 방향'으로 앞·옆·뒤·아래를 한 번에). 이상한 곳은 멈춘 장면에서 칠하거나, 시간 막대를 끌어 '구간 리포트'. 처리를 고르고 보내기. 후보 비교가 뜨면 그림을 보고 하나를 고름. 모든 장의 무관통은 요구하지 않음.`;
    몸.appendChild(사람줄);
    그리기();
    다시읽기();
  }
  function 떼기() {
    기둥.remove(); 막대.remove(); 비교칸.remove(); 사람줄.remove();
    if (상.이름 && 보()) 보().리깅단추(false);
    상.이름 = null; 상.단계 = 0;
  }
  function 바깥바뀜(값) {
    if (!상.이름) return;
    if (값 !== undefined && 값 !== 상.바깥) { const 처음 = 상.바깥 === null; 상.바깥 = 값; if (!처음) 다시읽기(); }
  }
  function 아홉단계로(동작이름) { 상.다음동작 = 동작이름 || null; }   // W14: 9단계를 열 때 이 동작을 고름
  window.리깅단계 = {붙이기, 떼기, 바깥바뀜, 다시읽기, 칠못함, 동작자리, 장으로, 짧은이름, 아홉단계로, 상태: 상};
  window.dispatchEvent(new Event("리깅단계준비"));
})();
