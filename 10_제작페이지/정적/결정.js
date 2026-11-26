// 결정 칸(오른쪽) — 작업 묶음 W06 (기능명세 1부 3·4-4)
// 에이전트 알림, 결정 단추 세 개, 되돌리기 목록, 실패한 묶음 다시 보내기. 보내기 단추는 칠하기.js(W03)가 맡는다.
// W07: 유료 단계(2·4·5·6·8, W14부터 10)의 승인 상자와 승인·다시 생성(1부 4-5). 단계 화면의 단추(W09~W14)는 자리만 두고 막아 둔다.
// W09: 1단계 단추(생성·시트 생성·승인·다시 생성)는 그림단계.js가 정한다(`window.그림단계.단추()`, 값이 "그림:"으로 시작하면 그쪽이 처리).
// 서버(127.0.0.1)에만 요청한다.
"use strict";

(() => {
  const $ = (id) => document.getElementById(id);
  const 글 = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const 짧은시각 = (t) => String(t || "").replace("T", " ").slice(5, 16);

  // 디자인 규격 3-5: 앞으로(초록) · 고쳐 줘(파랑) · 물러서기(회색). 값이 null이면 다른 묶음이 만든다(막아 둠).
  const 고쳐 = ["고쳐 줘", "b-fix", "고쳐 줘"];
  const 유료 = [["승인", "b-ok", "승인"], 고쳐, ["다시 생성", "b-re", "다시 생성"]];
  const 수정 = [["이 단계 끝", "b-ok", "이 단계 끝"], 고쳐, ["되돌리기", "b-re", "되돌리기"]];
  const 단추표 = {
    1: [["승인", "b-ok", null, "1단계 화면은 작업 묶음 W09에서 만듭니다"], 고쳐, ["다시 생성", "b-re", null, "다시 생성은 작업 묶음 W07에서 만듭니다"]],
    2: 유료, 3: 수정, 4: 유료, 5: 유료, 6: 유료, 7: 수정, 8: 유료, 9: 수정,
    11: 수정,   // W14: 내보내기·경로 고르기는 옆 기둥(동작단계.js)
  };

  const 결 = {이름: null, 단계: 0, 값: null, 바깥: null, 글: "", 글종류: "", 누르는중: false};
  window.결정상태 = 결;   // 시험·검사용으로 읽기만

  // 칸 안의 자리: 보내기 아래에 결정 단추와 안내 한 줄(디자인 규격 3-4 순서)
  const 뿌리 = document.createElement("div");
  뿌리.className = "decwrap";
  뿌리.dataset.순서 = "결정 단추";
  뿌리.innerHTML = `<div class="btns3" id="decbtns"></div><div class="hint" id="dechint"></div><div class="redo" id="redo" hidden></div>`;
  // 승인 상자(유료 단계만): 보내기와 결정 단추 사이(디자인 규격 3-4의 4번)
  const 상자 = document.createElement("div");
  상자.className = "pay";
  상자.id = "pay";
  상자.dataset.순서 = "승인 상자";
  상자.hidden = true;
  const 보내기칸 = document.querySelector("#side .sendwrap");
  if (보내기칸) { 보내기칸.after(상자); 상자.after(뿌리); }

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

  let 읽기번호 = 0;
  async function 다시읽기() {
    const 이름 = 결.이름, 단계 = 결.단계, 번호 = ++읽기번호;
    if (!이름 || !단계) { 결.값 = null; 그리기(); return; }
    try {
      const v = await 받기(`/api/결정?이름=${encodeURIComponent(이름)}&단계=${단계}`);
      if (번호 !== 읽기번호) return;
      결.값 = v;
    } catch (e) {
      if (번호 !== 읽기번호) return;
      결.값 = null;
      if (!(e instanceof TypeError)) 알리기(`결정 칸을 읽지 못함: ${e.message}`, "ng");
    }
    그리기();
  }

  function 알리기(t, 종류 = "") { 결.글 = t; 결.글종류 = 종류; 그리기(); }

  function 알림그리기() {
    const 칸 = $("alert");
    if (!칸) return;
    const 알림 = 결.값 && 결.값.알림;
    const 제목 = 칸.parentElement.querySelector(".ttl");
    if (!알림) {
      칸.textContent = "아직 알림 없음";
      칸.className = "";
      if (제목) 제목.textContent = "에이전트 알림";
      return;
    }
    칸.className = `alerttext${{"결정 필요": " wa", "막힘": " ng"}[알림.종류] || ""}`;
    칸.textContent = 알림.글;
    if (제목) 제목.innerHTML = `에이전트 알림 · ${글(알림.종류)} · ${글(짧은시각(알림.시각))}${알림.옛것 ? ` · <span class="wa" title="이 알림을 쓴 뒤 작업본이 바뀌었습니다">옛 알림</span>` : ""}`;
  }

  function 막는이유(값) {
    const v = 결.값;
    if (!결.이름 || !v) return "캐릭터를 고르세요";
    if (document.body.dataset.잠금 === "다른 탭") return "다른 탭에서 열려 있습니다";
    if (결.누르는중) return "처리하는 중…";
    if (값 === "이 단계 끝") {
      if (v.밀린묶음.length) return `보내고 처리되지 않은 묶음이 있습니다(${v.밀린묶음.join(", ")})`;
      if (v.상태 === "끝" || v.상태 === "끝(조건 미달)") return "이미 끝난 단계입니다";
    }
    if (값 === "승인") {
      const 승 = v.승인;
      if (!승) return "승인 상자가 없는 단계입니다";
      if (승.막는이유) return 승.막는이유;
    }
    if (값 === "다시 생성") {
      const 승 = v.승인;
      if (!승) return "승인 상자가 없는 단계입니다";
      if (승.다시생성막는이유) return 승.다시생성막는이유;
    }
    if (값 === "되돌리기") {
      if (v.처리중.length) return `에이전트가 처리 중입니다(${v.처리중.join(", ")})`;
      if (!v.되돌리기.length) return "되돌리기 사본이 없습니다(에이전트가 고치기 전에 만듭니다)";
    }
    return "";
  }

  const 수 = (x) => (typeof x === "number" ? String(Math.round(x * 100) / 100) : x == null ? "모름" : String(x));
  function 상자그리기() {
    const 승 = 결.값 && 결.값.승인;
    상자.hidden = !승;
    if (!승 || (결.단계 === 10 && !승.요청)) { 상자.hidden = true; 상자.innerHTML = ""; return; }   // W14: 10단계는 TRIPO로 만들기를 요청했을 때만
    if (승.잔액 && typeof 잔액그리기 === "function") 잔액그리기(승.잔액);
    const 가짜 = 승.모드 === "가짜" ? ` · <span title="TRIPO에 요청하지 않고 받은 값을 그대로 돌려주는 흉내입니다. 크레딧을 쓰지 않습니다.">가짜 실행</span>` : "";
    const 잔액 = 승.잔액 && 승.잔액.잔액 != null ? `${수(승.잔액.잔액)}${승.잔액.가짜 ? "(가짜)" : ""}` : "모름";
    const r = 승.요청;
    if (!r) {
      상자.innerHTML = `<div class="ttl">돈이 드는 실행 — 승인 필요${가짜}</div><span class="hint">아직 승인 요청이 없습니다. 에이전트가 값을 정해 요청을 만들면 여기에 보입니다. 지금 잔액 ${글(잔액)}</span>`;
      return;
    }
    const 제목 = {"실행 중": "실행 중…", "실행됨": "실행됨", "실패": "실행 실패"}[r.실행] || (r.승인 === "거절" ? "무효인 요청" : "돈이 드는 실행 — 승인 필요");
    const 크레딧 = r.크레딧 === "모름" || r.크레딧 == null ? `<b>크레딧 모름</b>` : `<b>${글(수(r.크레딧))}크레딧</b>`;
    const 결과 = r.결과 || {};
    let 아래 = "";
    if (r.실행 === "실행 중") 아래 = `<span class="hint">서버가 실행하는 중입니다. 끝나면 여기와 알림에 결과가 보입니다.</span>`;
    else if (r.실행 === "실행됨" || r.실행 === "실패") {
      const 줄 = [];
      if (결과.작업번호 && 결과.작업번호.length) 줄.push(`작업 ${결과.작업번호.join(", ")}`);
      줄.push(`쓴 크레딧 ${수(결과.쓴크레딧)}`, `잔액 ${수(결과.잔액전)} → ${수(결과.잔액후)}`);
      if (결과.받은파일) 줄.push(`받은 파일 ${결과.받은파일.length}개`);
      아래 = `<span class="hint${r.실행 === "실패" ? " ng" : " ok"}" title="${글(결과.실제값 || "")}">${글(줄.join(" · "))}${결과.실패이유 ? `<br>${글(결과.실패이유)}` : ""}</span>` +
        (결과.실제값 ? `<span class="hint">실제로 쓴 값</span><code>${글(결과.실제값)}</code>` : "");
    } else if (r.승인 === "거절") 아래 = `<span class="hint">${글(r.거절까닭 || "거절")}</span>`;
    else 아래 = `<span class="hint">실행 후: 서버가 실제로 쓴 값, 잔액 변화를 기록${r.해시맞음 ? "" : " · 값해시가 맞지 않아 무효"}</span>`;
    상자.innerHTML = `<div class="ttl">${글(제목)}${가짜}</div>` +
      `<div>${글(r.무엇)} · ${크레딧} · ${글(r.횟수)}번 · 지금 잔액 ${글(잔액)}</div>` +
      `<code title="값해시 ${글(r.값해시)}">${글(r.명령)}</code>${아래}`;
  }

  // W10: 2·4·5·6단계(2부 14·16·17·18절). 앞으로 가는 단추는 승인을 기다리는 요청이 있으면 "승인", 없으면 "이 단계 끝".
  // 5단계에는 "고쳐 줘"가 없다(흠은 7단계에서). 4·6단계는 되돌리기도 둔다.
  const 다시 = ["다시 생성", "b-re", "다시 생성"], 되돌 = ["되돌리기", "b-re", "되돌리기"];
  function 생성단추() {
    const r = 결.값 && 결.값.승인 && 결.값.승인.요청;
    const 앞 = r && r.승인 === "대기" && r.실행 === "안 함" ? ["승인", "b-ok", "승인"] : ["이 단계 끝", "b-ok", "이 단계 끝"];
    return {2: [앞, 고쳐, 다시], 4: [앞, 고쳐, 다시, 되돌], 5: [앞, 다시], 6: [앞, 고쳐, 다시, 되돌], 8: [앞, 다시], 10: [앞, 고쳐, 되돌]}[결.단계];   // 8: W13(리그 체크는 옆 기둥), 10: W14(옮기기는 옆 기둥)
  }
  const 단추들 = () => (결.단계 === 1 && window.그림단계 && window.그림단계.붙음() ? window.그림단계.단추()
    : [2, 4, 5, 6, 8, 10].includes(결.단계) ? 생성단추() : 단추표[결.단계] || []);
  function 그리기() {
    알림그리기();
    상자그리기();
    const 단추 = 단추들();
    $("decbtns").className = 단추.length === 3 ? "btns3" : 단추.length === 1 ? "btns1" : "btns2";
    $("decbtns").innerHTML = 단추.map(([t, c, 값, 막음글], i) => {
      const 이유 = 값 ? 막는이유(값) : 막음글;
      return `<button type="button" class="btn ${c}" data-i="${i}"${이유 ? " disabled" : ""} title="${글(이유 ? `${t} — ${이유}` : t)}">${글(t)}</button>`;
    }).join("");
    const h = $("dechint");
    const 기본 = 결.값 && 결.값.밀린묶음.length && 단추[0]?.[2] === "이 단계 끝" ? "보낸 묶음이 처리되면 '이 단계 끝'을 누를 수 있습니다." : "";
    h.textContent = 결.글 || 기본;
    h.className = `hint${결.글종류 ? ` ${결.글종류}` : ""}`;
    h.title = h.textContent;
    h.hidden = !h.textContent;
    const 실패 = (결.값 && 결.값.실패묶음) || [];
    const r = $("redo");
    r.hidden = !실패.length;
    if (실패.length) {
      const 막음 = 결.값.밀린묶음.length ? "앞 묶음을 아직 처리하지 않았습니다" : document.body.dataset.잠금 === "다른 탭" ? "다른 탭에서 열려 있습니다" : "";
      r.innerHTML = `<span class="hint ng" title="${글(실패.join(", "))}">끝내지 못한 묶음 ${실패.length}개</span>` +
        `<button type="button" class="tb" id="redobtn"${막음 ? " disabled" : ""} title="${글(막음 || `${실패[실패.length - 1]}을 같은 내용으로 다시 보냅니다`)}">다시 보내기</button>`;
    }
  }

  // ---- 묻는 상자(index.html의 ask2를 같이 쓴다)
  function 물어보기(제목, 본문, 단추들) {
    return new Promise((풀기) => {
      const o = $("ask2");
      $("ask2ttl").textContent = 제목;
      $("ask2body").innerHTML = 본문;
      const 줄 = $("ask2btns");
      줄.className = `btns${단추들.length}`;
      줄.innerHTML = 단추들.map(([t, c], i) => `<button class="btn ${c}" type="button" data-i="${i}">${글(t)}</button>`).join("");
      o.hidden = false;
      const 끝 = (값) => {
        const 고른 = o.querySelector("input[name=rbpick]:checked");
        o.hidden = true; o.removeEventListener("keydown", 키); 줄.onclick = null;
        풀기(값 === null ? null : {값, 고른: 고른 ? 고른.value : null});
      };
      const 키 = (ev) => { if (ev.key === "Escape") 끝(null); };
      o.addEventListener("keydown", 키);
      줄.onclick = (ev) => { const b = ev.target.closest("[data-i]"); if (b) 끝(단추들[Number(b.dataset.i)][2]); };
      줄.querySelector("button").focus();
    });
  }

  async function 누름(값) {
    if (!값 || 막는이유(값)) return;
    const 이름 = 결.이름, 단계 = 결.단계, 탭 = window.탭id;
    try {
      if (값 === "이 단계 끝") {
        const 답 = await 물어보기(`${단계}단계를 끝으로 할까요?`, "끝으로 하면 에이전트는 이 단계를 더 고치지 않습니다. 다시 고치려면 '고쳐 줘'를 누릅니다(뒤 단계에 '앞 단계가 바뀜'이 붙음).",
          [["끝으로", "b-ok", "예"], ["취소", "b-re", "아니오"]]);
        if (!답 || 답.값 !== "예") return;
        결.누르는중 = true; 그리기();
        let v = await 보내기("/api/결정", {이름, 단계, 탭, 결정: "이 단계 끝"});
        if (!v.됨 && v.모자람 && v.모자람.length) {
          결.누르는중 = false; 그리기();
          const 또 = await 물어보기("완료 조건이 모자랍니다", `<ul class="lack">${v.모자람.map((x) => `<li>${글(x)}</li>`).join("")}</ul><span class="hint">그래도 끝으로 하면 "끝(조건 미달)"로 기록합니다.</span>`,
            [["그래도 끝으로", "b-ok", "예"], ["취소", "b-re", "아니오"]]);
          if (!또 || 또.값 !== "예") return;
          결.누르는중 = true; 그리기();
          v = await 보내기("/api/결정", {이름, 단계, 탭, 결정: "그래도 끝"});
        }
        알리기(`${단계}단계: ${v.상태}`, "ok");
      } else if (값 === "고쳐 줘") {
        결.누르는중 = true; 그리기();
        const v = await 보내기("/api/결정", {이름, 단계, 탭, 결정: "고쳐 줘"});
        알리기(v.글 || "Claude 앱에서 무엇을 고칠지 말씀해 주세요.", "ac");
      } else if (값 === "승인") {
        const r = 결.값.승인.요청;
        결.누르는중 = true; 그리기();
        // 화면에 보인 값 그대로를 보낸다. 서버는 파일의 값과 값해시가 같을 때만 한 번 실행한다(1부 4-5)
        const v = await 보내기("/api/승인", {이름, 단계, 탭, 파일: r.파일, 명령: r.명령, 크레딧: r.크레딧, 횟수: r.횟수, 값해시: r.값해시});
        알리기(`승인함 — 서버가 실행을 시작했습니다${v.모드 === "가짜" ? "(가짜 실행, 크레딧을 쓰지 않음)" : ""}.`, "ok");
      } else if (값 === "다시 생성") {
        결.누르는중 = true; 그리기();
        await 보내기("/api/다시생성", {이름, 단계, 탭});
        알리기("같은 값으로 새 승인 요청을 만들었습니다. 값을 보고 승인하세요(바로 실행하지 않음).", "ac");
      } else if (값 === "되돌리기") {
        const 목록 = 결.값.되돌리기;
        const 줄들 = 목록.map((x, i) => `<label class="rbrow" title="${글(`${x.파일} · ${x.까닭} · ${x.알림}`)}"><input type="radio" name="rbpick" value="${글(x.파일)}"${i === 0 ? " checked" : ""}>` +
          `<span class="rbt">${글(String(x.시각 || "").replace("T", " ").slice(5, 19))}</span><span class="rbn">${글(x.알림 || x.까닭 || "알림 없음")}</span></label>`).join("");
        const 답 = await 물어보기("어느 때로 되돌릴까요?", `<div class="rblist">${줄들}</div><span class="hint">지금 작업본도 사본으로 남긴 뒤 바꿉니다. 뒤 단계에는 '앞 단계가 바뀜'이 붙습니다.</span>`,
          [["되돌리기", "b-ok", "예"], ["취소", "b-re", "아니오"]]);
        if (!답 || 답.값 !== "예" || !답.고른) return;
        결.누르는중 = true; 그리기();
        const v = await 보내기("/api/되돌리기", {이름, 단계, 탭, 사본: 답.고른});
        알리기(`되돌림: ${답.고른}. 바꾸기 전 작업본은 ${v.남긴사본.split("/").pop()}로 남김${v.지울후보 && v.지울후보.length ? ` · 사본이 10개를 넘음(지울 후보 ${v.지울후보.length}개 — 에이전트에게 정리를 부탁하세요)` : ""}`, "ok");
      }
    } catch (e) {
      알리기(`${값}: ${e instanceof TypeError ? "서버와 연결 끊김" : e.message}`, "ng");
    } finally {
      결.누르는중 = false;
      if (이름 === 결.이름 && 단계 === 결.단계) await 다시읽기();
      if (typeof 맥박 === "function") 맥박();   // 상태.json이 바뀌었으니 단계 목록을 곧바로 다시 읽는다(앱.js)
    }
  }

  async function 다시보내기누름() {
    const 실패 = (결.값 && 결.값.실패묶음) || [];
    if (!실패.length) return;
    const 묶음 = 실패[실패.length - 1];
    try {
      const v = await 보내기("/api/다시보내기", {이름: 결.이름, 단계: 결.단계, 탭: window.탭id, 묶음});
      알리기(`다시 보냄: ${v.파일.split("/").pop()} — Claude 앱에서 '보냈어'라고 알려 주세요.`, "ac");
    } catch (e) {
      알리기(`다시 보내지 못함: ${e.message}`, "ng");
    }
    await 다시읽기();
    if (window.칠하기 && window.칠하기.바깥바뀜) window.칠하기.바깥바뀜(`다시보냄${Date.now()}`);
  }

  $("decbtns").addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-i]");
    if (!b || b.disabled) return;
    const d = 단추들()[Number(b.dataset.i)];
    if (d && String(d[2]).startsWith("그림:")) { if (!막는이유(d[2])) window.그림단계.누름(d[2]); }
    else if (d) 누름(d[2]);
  });
  $("redo").addEventListener("click", (ev) => { if (ev.target.closest("#redobtn")) 다시보내기누름(); });

  // ---- 바깥(앱.js)에 내놓는 것
  function 붙이기(이름, 단계) {
    const 새 = 이름 !== 결.이름 || 단계 !== 결.단계;
    결.이름 = 이름 || null;
    결.단계 = 단계 || 0;
    if (새) { 결.값 = null; 결.글 = ""; 결.글종류 = ""; 결.바깥 = null; 다시읽기(); }
    else 다시읽기();
    그리기();
  }
  // 맥박마다: 서버의 알림·묶음·처리·되돌리기 파일이 바뀌었으면 다시 읽는다(1부 6절 파일 감시)
  let 마지막잠금 = null;
  function 바깥바뀜(값) {
    if (값 !== undefined && 값 !== 결.바깥) {
      const 처음 = 결.바깥 === null;
      결.바깥 = 값;
      if (!처음) 다시읽기();
    }
    if (document.body.dataset.잠금 !== 마지막잠금) { 마지막잠금 = document.body.dataset.잠금; 그리기(); }
  }
  window.결정 = {붙이기, 바깥바뀜, 다시읽기, 그리기, 상태: 결};
  window.dispatchEvent(new Event("결정준비"));
})();
