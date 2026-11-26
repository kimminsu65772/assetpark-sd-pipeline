// 2·4·5·6단계(TRIPO 생성 계열) 화면 (작업 묶음 W10, 기능명세 2부 14·16·17·18절)
// 가운데: 보기 줄(3D 보기 · [6단계 UV 그림] · 옆 기둥) → 도구 줄 → 표시 목록(6단계) → 단계 상태 → 사람이 하는 일.
// 옆 기둥: 보낼 값(SSOT 기본값) · 단계마다의 표(입력 네 장 / 면 수 / 받은 그림 / UV 수치) · 받은 뒤 확인 · 끝나는 조건.
// 실행은 결정 칸의 승인 상자(W07)가 한다. 이 파일은 읽어서 보이기만 한다.
(() => {
  const 단계들 = [2, 4, 5, 6];
  const 글 = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const 수 = (n) => (typeof n === "number" ? n.toLocaleString("ko-KR") : "—");
  const 그림주소 = (x) => `/api/그림/파일?경로=${encodeURIComponent(x)}`;
  const 사람 = {
    2: "입력 네 장과 보낼 값을 보고 승인. 받은 모델이 입력 그림과 크게 다르면 다시 생성. 에이전트가 받은 파일을 확인하면 '이 단계 끝'.",
    4: "전후를 나란히(와이어) 보고 모양이 같은지 판단. 면 수가 예산 안이고 파츠 수·대칭·접합부 점검이 끝나면 '이 단계 끝'.",
    5: "받은 텍스처를 입력 그림과 나란히 보고, 크게 다르면 다시 생성. 흠은 여기서 고치지 않음(7단계).",
    6: "격자로 늘어난 곳을 보고 붓으로 칠해 보내기. 수치표가 모두 통과하면 '이 단계 끝'.",
  };
  const 기본모양 = {2: {형태만: true, 격자: false, 와이어: false}, 4: {형태만: false, 격자: false, 와이어: true},
    5: {형태만: false, 격자: false, 와이어: false}, 6: {형태만: false, 격자: true, 와이어: false}};

  const 상 = {이름: null, 단계: 0, 값: null, 바깥: null, 오류: "", 묻는번호: 0};
  window.생성단계상태 = 상;   // 시험·검사용으로 읽기만

  const 기둥 = document.createElement("div");
  기둥.className = "g1aside p10aside";
  기둥.innerHTML = `<div class="g1asidein" id="p10in"></div>`;
  const 사람줄 = document.createElement("div");
  사람줄.className = "human";
  사람줄.dataset.순서 = "사람이 하는 일";

  function 칸(제목, 안) { return `<div class="note"><div class="ttl">${글(제목)}</div>${안}</div>`; }
  function kv(줄들) { return `<div class="kv g1kv">${줄들.map(([k, v]) => `<div>${글(k)}</div><div title="${글(String(v).replace(/<[^>]*>/g, ""))}">${v}</div>`).join("")}</div>`; }
  const 판 = (참, 글참 = "통과", 글거짓 = "안 됨") => (참 === true ? `<span class="ok">✓ ${글참}</span>` : 참 === false ? `<span class="ng">${글거짓}</span>` : "—");

  function 보낼값() {
    const v = 상.값, 기 = v.기본;
    const 결 = window.결정 && window.결정.상태 && window.결정.상태.값;
    const r = 결 && 결.승인 && 결.승인.요청;
    const 상태 = r ? `${글(r.파일)} · 승인 ${글(r.승인)} · 실행 ${글(r.실행)}${r.가짜 ? " (가짜)" : ""}` : `<span class="wa">아직 요청 없음</span>`;
    const 안내 = r ? "" : `<span class="hint">Claude 앱에서 "${v.단계}단계 승인 요청 만들어 줘"라고 하면 에이전트가 아래 값으로 요청을 만듭니다(명령 '생성요청').</span>`;
    return 칸("보낼 값", kv([["무엇", 글(기.무엇)], ["명령 틀", `<code>${글(기.틀)}</code>`],
      ["크레딧", 기.크레딧 === "모름" ? "<b>모름</b>" : 글(기.크레딧)], ["지금 요청", 상태]]) +
      `<span class="hint">근거: ${글(기.근거)}</span>${안내}`);
  }
  function 섬네일(목록, 빈글) {
    if (!목록 || !목록.length) return `<span class="hint">${글(빈글)}</span>`;
    return `<div class="p10th">${목록.map((x) => `<img src="${그림주소(x)}" alt="${글(x.split("/").pop())}" title="${글(x)}" loading="lazy">`).join("")}</div>`;
  }
  function 단계표() {
    const v = 상.값, c = v.확인 || {};
    if (v.단계 === 2) {
      const 검 = v.입력검사 || {};
      return 칸("입력 네 장", 섬네일(v.입력그림, "2단계 입력이 없습니다(1단계에서 시트를 승인하면 생깁니다).") +
        `<div class="hint ${검.통과 ? "ok" : "ng"}">입력 검사: ${검.통과 ? "통과" : "실패 — 승인 단추가 잠깁니다"}${검.출력 && 검.출력.length ? ` · ${글(검.출력.join(" "))}` : ""}</div>`);
    }
    if (v.단계 === 5) {
      return 칸("받은 그림 · 입력 그림과 나란히", `<div class="hint">받은 그림(파츠마다 한 장)</div>${섬네일(c.받은그림, "아직 받은 그림이 없습니다.")}` +
        `<div class="hint">입력 그림(1단계 네 장)</div>${섬네일(v.입력그림, "입력 그림이 없습니다.")}`);
    }
    const m = v.면수 || {};
    if (v.단계 === 4) {
      const 후 = c.면수후 ?? m.지금, 전 = c.면수전 ?? m.전;
      const 안 = typeof 후 === "number" ? (후 <= v.예산삼각형 ? `<span class="ok">✓ ${수(후)}</span>` : `<span class="ng">${수(후)}</span>`) : "—";
      return 칸("면 수(삼각형)", `<table class="t"><thead><tr><th></th><th>전</th><th>후</th><th>예산</th></tr></thead><tbody>` +
        `<tr><td>삼각형</td><td>${수(전)}</td><td>${안}</td><td>${수(v.예산삼각형)}</td></tr>` +
        `<tr><td>파츠</td><td>${수(c.파츠수전 ?? m.파츠전)}</td><td>${수(c.파츠수후 ?? m.파츠지금)}</td><td>그대로</td></tr></tbody></table>` +
        `<span class="hint">${c.면수후 !== undefined ? "에이전트 확인 값" : "3D 보기 GLB에서 센 값(전 = 마지막 처리 전)"}</span>`);
    }
    // 6단계: 4_UV 합격 수치
    const 줄 = (이름, 값, 기준, 참) => `<tr><td>${글(이름)}</td><td>${값 === undefined ? "—" : 글(값)}</td><td>${글(기준)}</td><td>${참 === undefined ? "—" : 판(참, "통과", "불합격")}</td></tr>`;
    const 입력 = m.지금;
    return 칸("점검 수치(4_UV)", `<table class="t"><thead><tr><th>항목</th><th>값</th><th>기준</th><th>판정</th></tr></thead><tbody>` +
      줄("겹침", c.겹침, "0", c.겹침 === undefined ? undefined : c.겹침 === 0) +
      줄("최소 간격", c.최소간격, `${v.UV간격}칸 이상`, c.최소간격 === undefined ? undefined : c.최소간격 >= v.UV간격) +
      줄("UV 0~1", c.UV범위안 === undefined ? undefined : c.UV범위안 ? "안" : "밖", "안", c.UV범위안) +
      줄("뒤집힌 삼각형", c.뒤집힌삼각형, "0", c.뒤집힌삼각형 === undefined ? undefined : c.뒤집힌삼각형 === 0) +
      줄("옮긴 그림 비교", c.그림비교통과 === undefined ? undefined : c.그림비교통과 ? "같음" : "다름", "같음", c.그림비교통과) +
      줄("격자 직접 봄", c.격자직접봄 === undefined ? undefined : c.격자직접봄 ? "봄" : "안 봄", "봄", c.격자직접봄) +
      줄("입력 삼각형", 입력 === null || 입력 === undefined ? undefined : 수(입력), `${수(v.UV한도삼각형)} 이하`, 입력 === null || 입력 === undefined ? undefined : 입력 <= v.UV한도삼각형) +
      `</tbody></table>`);
  }
  function 확인칸() {
    const v = 상.값, c = v.확인, 실 = v.실행;
    const 실행 = 실 ? `${글(실.실행)}${실.가짜 ? " (가짜 실행)" : ""} · 받은 파일 ${실.받은파일.length}개${실.끝시각 ? ` · ${글(실.끝시각.replace("T", " ").slice(5, 16))}` : ""}` : "아직 없음";
    const 줄들 = [["마지막 실행", 실행]];
    if (c) {
      const 뺄것 = new Set(["만든시각", "작업본해시", "만든곳", "받은그림", "겹침", "최소간격", "UV범위안", "뒤집힌삼각형", "그림비교통과", "격자직접봄", "면수전", "면수후", "파츠수전", "파츠수후"]);
      for (const [k, x] of Object.entries(c)) {
        if (뺄것.has(k)) continue;
        줄들.push([k, typeof x === "boolean" ? 판(x, "예", "아니오") : Array.isArray(x) ? 글(x.length ? x.join(", ") : "없음") : 글(x)]);
      }
      줄들.push(["확인한 때", 글(String(c.만든시각 || "").replace("T", " ").slice(5, 16))]);
    } else 줄들.push(["확인", `<span class="wa">아직 없음 — 에이전트가 받은 뒤 '생성확인'</span>`]);
    return 칸("받은 뒤 확인", kv(줄들));
  }
  function 끝칸() {
    const 모 = 상.값.모자람 || [];
    return 칸("끝나는 조건", 모.length ? `<ul class="lack">${모.map((x) => `<li class="ng">${글(x)}</li>`).join("")}</ul>` : `<span class="ok">✓ 모두 채움 — '이 단계 끝'을 누를 수 있습니다</span>`);
  }
  function 그리기() {
    const 안 = 기둥.querySelector("#p10in");
    if (상.오류) { 안.innerHTML = `<div class="note ng">${글(상.오류)}</div>`; return; }
    if (!상.값) { 안.innerHTML = `<div class="note"><span class="hint">불러오는 중…</span></div>`; return; }
    안.innerHTML = 보낼값() + 단계표() + 확인칸() + 끝칸();
  }

  async function 다시읽기() {
    if (!상.이름 || !상.단계) return;
    const 번호 = ++상.묻는번호, 이름 = 상.이름, 단계 = 상.단계;
    try {
      const r = await fetch(`/api/생성단계?이름=${encodeURIComponent(이름)}&단계=${단계}`, {cache: "no-store"});
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

  // ---- 바깥(앱.js)에 내놓는 것
  function 붙이기(이름, 단계) {
    if (!단계들.includes(단계) || !window.보기3d) { 떼기(); return; }
    const 뿌리 = window.보기3d.내부.뿌리, 줄 = 뿌리.querySelector(".vrow"), 몸 = document.getElementById("body");
    if (!뿌리.isConnected || !줄 || !몸) { 떼기(); return; }
    const 새 = 이름 !== 상.이름 || 단계 !== 상.단계;
    if (단계 !== 상.단계) window.보기3d.모양정하기(기본모양[단계]);
    상.이름 = 이름; 상.단계 = 단계;
    if (새) { 상.값 = null; 상.오류 = ""; 상.바깥 = null; }
    줄.appendChild(기둥);   // 보기가 왼쪽, 옆 기둥이 오른쪽(디자인 규격 3-3). 6단계는 UV 그림 다음
    사람줄.innerHTML = `<b>사람이 하는 일</b> · ${글(사람[단계])}`;
    몸.appendChild(사람줄);
    그리기();
    다시읽기();
  }
  function 떼기() {
    기둥.remove(); 사람줄.remove();
    상.단계 = 0;
  }
  // 맥박마다: 확인.json·승인 파일·입력 검사가 바뀌면 다시 읽는다. 결정 칸의 승인 상태도 보낼 값에 보이므로 함께
  function 바깥바뀜(값) {
    if (!상.단계) return;
    if (값 !== undefined && 값 !== 상.바깥) { const 처음 = 상.바깥 === null; 상.바깥 = 값; if (!처음) 다시읽기(); }
  }
  window.생성단계 = {붙이기, 떼기, 바깥바뀜, 다시읽기, 그리기, 상태: 상};
  window.dispatchEvent(new Event("생성단계준비"));
})();
