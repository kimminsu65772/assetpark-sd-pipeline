// 가마우지 제작 페이지 — 파일 가져오기(W08, 기능명세 1부 4-3)
// 고르기·끌어 놓기 → 서버에 그대로 올림 → 서버가 검사(모델은 Blender) → 단계·출처·앞 방향을 고르고 넣기.
// 앱.js의 화면·받기·보내기·글·$·상태불러오기·모두그리기·단계고르기를 쓴다(같은 전역).
"use strict";

window.가져오기 = (() => {
  const 큰모델 = 200 * 1024 * 1024, 큰그림 = 50 * 1024 * 1024;   // 1부 4-3(사용자 확정)
  const 받는형식 = [".png", ".jpg", ".jpeg", ".glb", ".fbx", ".obj", ".blend"];
  const 그림형식 = [".png", ".jpg", ".jpeg"];
  const 출처들 = ["TRIPO 웹", "다른 곳", "이 프로젝트의 다른 파일"];
  const 방향이름 = {"+x": "+x 쪽에서 본 모습", "-x": "-x 쪽에서 본 모습", "+y": "+y 쪽에서 본 모습", "-y": "-y 쪽에서 본 모습"};
  const 일 = {번호: null, 값: null, 단계: 0, 출처: "TRIPO 웹", 작업번호: "", 앞: null, 바꾸기: false, 바쁨: false, 끝: null, 오류: "", 방향만: null};
  let 묻는중 = null;

  const 확장자 = (n) => { const i = n.lastIndexOf("."); return i < 0 ? "" : n.slice(i).toLowerCase(); };
  const MB = (b) => `${(b / 1048576).toFixed(b < 10485760 ? 1 : 0)} MB`;

  function 열기() { $("imp").hidden = false; }
  function 닫기() {
    clearTimeout(묻는중);
    if (일.번호 && !일.끝) 보내기("/api/가져오기/취소", {번호: 일.번호}).catch(() => {});
    Object.assign(일, {번호: null, 값: null, 끝: null, 오류: "", 바쁨: false, 방향만: null, 바꾸기: false, 앞: null, 작업번호: "", 단계설정: false});
    $("imp").hidden = true;
  }

  function 막는이유() {
    if (!화면.지금캐릭터 || !화면.보기) return "먼저 캐릭터를 고르세요.";
    if (!화면.보기.있음) return "이 캐릭터에는 아직 상태.json이 없습니다. 먼저 새 캐릭터로 만드세요.";
    if (document.body.dataset.잠금 === "다른 탭") return "다른 탭에서 열려 있습니다.";
    return "";
  }

  // ---- 1. 고르기·끌어 놓기 → 올리기
  async function 시작(파일) {
    const 이유 = 막는이유();
    if (이유) { 오류띠(`파일 가져오기: ${이유}`); return; }
    if (!$("imp").hidden && (일.바쁨 || 일.번호)) return;
    const 형식 = 확장자(파일.name);
    Object.assign(일, {번호: null, 값: null, 끝: null, 오류: "", 바쁨: true, 방향만: null, 바꾸기: false, 앞: null, 작업번호: "", 출처: "TRIPO 웹", 단계설정: false,
      파일: {이름: 파일.name, 크기: 파일.size}, 캐릭터: 화면.지금캐릭터, 올림: 0});
    열기();
    if (!받는형식.includes(형식)) { 일.바쁨 = false; 일.오류 = `받는 형식이 아닙니다(${형식 || "확장자 없음"}). PNG·JPG(그림), GLB·FBX·OBJ(모델), blend(작업본)만 받습니다.`; return 그리기(); }
    const 한도 = 그림형식.includes(형식) ? 큰그림 : 큰모델;
    let 큰파일 = false;
    if (파일.size > 한도) {
      그리기();
      const 답 = await 묻기("큰 파일입니다", `${글(파일.name)}은 ${MB(파일.size)}입니다(기준 ${MB(한도)}). 받아 두고 검사하는 데 시간이 걸리고, 캐릭터 폴더에 그대로 복사됩니다.`,
        [["그래도 가져오기", "b-fix", true], ["그만두기", "b-re", false]]);
      if (!답) { 일.바쁨 = false; return 닫기(); }
      큰파일 = true;
    }
    그리기();
    try {
      일.값 = await 올리기(파일, 큰파일);
      일.번호 = 일.값.번호;
      일.바쁨 = false;
      기다리기();
    } catch (e) {
      일.바쁨 = false;
      일.오류 = `올리지 못했습니다: ${e.message}`;
    }
    그리기();
  }

  function 올리기(파일, 큰파일) {
    return new Promise((풀기, 막기) => {
      const x = new XMLHttpRequest();
      const 질문 = new URLSearchParams({이름: 일.캐릭터, 파일: 파일.name, 큰파일: 큰파일 ? "1" : ""});
      x.open("POST", `/api/가져오기/올리기?${질문}`);
      x.setRequestHeader("Content-Type", "application/octet-stream");
      x.upload.onprogress = (ev) => { if (ev.lengthComputable) { 일.올림 = Math.round(ev.loaded / ev.total * 100); 그리기(); } };
      x.onload = () => {
        let v = {};
        try { v = JSON.parse(x.responseText); } catch (e) {}
        if (x.status === 200) 풀기(v); else 막기(new Error(v.오류 || `${x.status}`));
      };
      x.onerror = () => 막기(new Error("서버에 닿지 못함"));
      x.send(파일);
    });
  }

  // ---- 2. 검사를 기다림
  async function 기다리기() {
    clearTimeout(묻는중);
    if (!일.번호 || $("imp").hidden) return;
    try {
      const v = await 받기(`/api/가져오기?번호=${일.번호}`);
      if (v.번호 !== 일.번호) return;
      일.값 = v;
      if (v.상태 === "검사됨" && !일.단계설정) {
        일.단계 = v.추정 || 1;
        일.앞 = v.검사 && v.검사.앞 ? v.검사.앞 : null;
        일.단계설정 = true;
      }
    } catch (e) {
      일.오류 = `검사 결과를 받지 못했습니다: ${e.message}`;
      return 그리기();
    }
    그리기();
    if (일.값.상태 === "검사 중") 묻는중 = setTimeout(기다리기, 1000);
  }

  // ---- 3. 넣기
  async function 넣기() {
    if (일.바쁨 || !일.값 || 일.값.상태 !== "검사됨") return;
    일.바쁨 = true; 일.오류 = ""; 그리기();
    try {
      const v = await 보내기("/api/가져오기/넣기", {번호: 일.번호, 이름: 일.캐릭터, 탭: window.탭id, 단계: 일.단계, 출처: 일.출처,
        작업번호: 일.출처 === "TRIPO 웹" ? 일.작업번호 : "", 앞: 일.값.확장자 && 그림형식.includes(일.값.확장자) ? null : 일.앞 || "모름", 바꾸기: 일.바꾸기});
      일.끝 = v;
      if (일.캐릭터 === 화면.지금캐릭터) { 화면.보기 = v.상태보기; 단계고르기(v.단계 - 1); 모두그리기(); }
    } catch (e) {
      일.오류 = e.message;
    }
    일.바쁨 = false;
    그리기();
  }

  // ---- 4. 넣은 뒤 앞 방향 고르기("방향 확인 필요")
  async function 방향열기(단계) {
    const 이유 = 막는이유();
    if (이유) { 오류띠(`앞 방향 고르기: ${이유}`); return; }
    Object.assign(일, {번호: null, 값: null, 끝: null, 오류: "", 바쁨: true, 앞: null, 캐릭터: 화면.지금캐릭터, 방향만: {단계}});
    열기(); 그리기();
    try {
      일.방향만.값 = await 받기(`/api/가져온것?이름=${encodeURIComponent(일.캐릭터)}&단계=${단계}`);
    } catch (e) {
      일.오류 = e.message;
    }
    일.바쁨 = false; 그리기();
  }
  async function 방향넣기() {
    if (일.바쁨 || !일.앞 || !일.방향만) return;
    일.바쁨 = true; 일.오류 = ""; 그리기();
    try {
      const v = await 보내기("/api/가져오기/방향", {이름: 일.캐릭터, 단계: 일.방향만.단계, 앞: 일.앞, 탭: window.탭id});
      일.끝 = v;
      if (일.캐릭터 === 화면.지금캐릭터) { 화면.보기 = v.상태보기; 모두그리기(); }
    } catch (e) {
      일.오류 = e.message;
    }
    일.바쁨 = false; 그리기();
  }

  // ---- 그리기
  function 방향칸(그림, 주소, 추정) {
    if (!그림.length) return "";
    return `<div class="impdirs">${그림.map((n) => `<button type="button" class="${일.앞 === n ? "on" : ""}" data-dir="${n}" title="이 그림이 얼굴 쪽이면 누르세요" aria-pressed="${일.앞 === n}">` +
      `<img src="${주소(n)}" alt="${글(방향이름[n])}"><span>${글(n)}${n === 추정 ? " · 추정" : ""}${n === "-y" ? " · 작업본 앞" : ""}</span></button>`).join("")}</div>`;
  }
  function 앞풀이(앞) {
    if (!앞 || 앞 === "모름") return `<span class="wa">모름 — 넣으면 "방향 확인 필요"로 표시하고, 나중에 그림에서 고릅니다</span>`;
    if (앞 === "-y") return `<span class="ok">-y (작업본 방향 그대로 씀)</span>`;
    return `<span class="wa">${글(앞)} (작업본은 앞이 -y — 원본은 그대로 두고 z축으로 돌린 사본을 만들어 입력으로 씀${앞 === "+x" ? ", TRIPO 원본 방향" : ""})</span>`;
  }

  function 그리기() {
    if ($("imp").hidden) return;
    const 몸 = $("impbody"), 단추 = $("impbtns");
    let html = "", 단추들 = [];
    if (일.방향만) {
      $("impttl").textContent = `${일.방향만.단계}단계 — 가져온 모델의 앞 고르기`;
      const v = 일.방향만.값;
      if (일.끝) {
        html = `<div class="kv"><div>앞</div><div class="ok">${글(일.앞)}</div><div>입력</div><div>${글(일.끝.입력)}</div></div><span class="hint">"방향 확인 필요" 표시를 지웠습니다.</span>`;
        단추들 = [["닫기", "b-re", 닫기]];
      } else if (v) {
        html = `<div>${글(v.원래이름)}의 네 방향 그림입니다. <b>얼굴이 보이는 그림</b>을 누르세요.</div>` +
          방향칸(v.그림, (n) => `/api/가져온것/그림?이름=${encodeURIComponent(일.캐릭터)}&폴더=${encodeURIComponent(v.폴더)}&면=${encodeURIComponent(n)}`, null) +
          `<div class="kv"><div>고른 앞</div><div>${일.앞 ? 앞풀이(일.앞) : "아직 안 고름"}</div></div>`;
        단추들 = [[일.바쁨 ? "만드는 중…" : "이 방향으로", "b-ok", 방향넣기, !일.앞 || 일.바쁨], ["취소", "b-re", 닫기, 일.바쁨]];
      } else {
        html = 일.바쁨 ? "불러오는 중…" : "";
        단추들 = [["닫기", "b-re", 닫기]];
      }
    } else {
      $("impttl").textContent = "파일 가져오기";
      const f = 일.파일 || {};
      const v = 일.값;
      const 머리 = `<div class="kv"><div>파일</div><div>${글(f.이름 || "")} · ${MB(f.크기 || 0)}</div><div>캐릭터</div><div>${글(일.캐릭터 || "")}</div>`;
      if (일.끝) {
        const e = 일.끝;
        html = 머리 + `<div>넣은 곳</div><div>${e.단계}단계 입력</div><div>입력 파일</div><div>${글(e.입력)}</div><div>원본 보존</div><div>${글(e.폴더)}/</div>` +
          (e.이전입력 ? `<div>옛 입력</div><div>${글(e.이전입력)}/ (사본)</div>` : "") +
          (e.방향확인필요 ? `<div>방향</div><div class="wa">방향 확인 필요 — 가운데 칸의 "앞 고르기"로 고릅니다</div>` : "") + `</div>`;
        단추들 = [["닫기", "b-ok", 닫기]];
      } else if (!v) {
        html = 머리 + `<div>상태</div><div>${일.오류 ? "" : 일.바쁨 ? `올리는 중… ${일.올림 || 0}%` : ""}</div></div>`;
        단추들 = [["닫기", "b-re", 닫기, 일.바쁨]];
      } else if (v.상태 === "검사 중") {
        html = 머리 + `<div>상태</div><div>검사 중… ${그림형식.includes(v.확장자) ? "" : "(Blender로 열어 봅니다. 몇 초~1분)"}</div></div>`;
        단추들 = [["닫기", "b-re", 닫기, true]];
      } else if (v.상태 === "열리지 않음") {
        html = 머리 + `<div>열림</div><div class="ng">열리지 않음 — ${글((v.검사 || {}).이유 || "")}</div></div><span class="hint">넣지 않았습니다. 받은 파일은 지웁니다.</span>`;
        단추들 = [["닫기", "b-re", 닫기]];
      } else {
        const g = v.검사 || {};
        const 모델 = !그림형식.includes(v.확장자);
        const 줄 = 화면.보기 && 화면.보기.단계[일.단계 - 1];
        const 있는입력 = 줄 && 줄.입력.length ? 줄.입력 : [];
        html = 머리 + `<div>열림</div><div class="ok">열림</div>` + (모델
          ? `<div>크기(x·y·z)</div><div>${(g.크기 || []).join(" · ")}${g.가장높은축 && g.가장높은축 !== "z" ? ` <span class="wa">— 키가 ${글(g.가장높은축)}축(누워 있음?)</span>` : ""}</div>` +
            `<div>앞 방향</div><div>${앞풀이(일.앞)}</div>` +
            `<div>파츠</div><div>${g.파츠수}개 · 면 ${g.면수}</div>` +
            `<div>UV 층</div><div>${g.UV있는파츠 === g.파츠수 ? `모든 파츠에 있음(가장 많은 파츠 ${g.UV층최대}층)` : `<span class="wa">${g.UV있는파츠}/${g.파츠수} 파츠에만 있음</span>`}</div>` +
            `<div>텍스처</div><div>${g.텍스처수}장${g.텍스처파일없음 ? ` <span class="wa">(그림 파일을 못 찾음 ${g.텍스처파일없음}장)</span>` : ""}</div>` +
            `<div>뼈대</div><div>${g.뼈대수 ? `있음 · 뼈 ${g.뼈수}개${g.동작수 ? ` · 동작 ${g.동작수}개` : ""}` : "없음"}</div>`
          : `<div>그림 크기</div><div>${g.폭} × ${g.높이}</div>`) + `</div>`;
        if (모델) html += 방향칸(v.그림 || [], (n) => `/api/가져오기/그림?번호=${v.번호}&면=${encodeURIComponent(n)}`, g.앞) +
          (v.그림 && v.그림.length ? `<span class="hint">얼굴이 보이는 그림을 누르면 앞을 바꿉니다. 다시 누르면 "모름".</span>` : "");
        else html += `<div class="impdirs one"><img src="/api/가져오기/그림?번호=${v.번호}&면=원본" alt="가져올 그림"></div>`;
        html += `<div class="impf"><label>단계<select id="impstep">${화면.정보.단계목록.map((d) => `<option value="${d.번호}"${d.번호 === 일.단계 ? " selected" : ""}>${d.번호}. ${글(d.이름)}${d.번호 === v.추정 ? " (추정)" : ""}</option>`).join("")}</select></label>` +
          `<span class="hint">${글(v.추정이유)}</span>` +
          `<label>출처<select id="impsrc">${출처들.map((s) => `<option${s === 일.출처 ? " selected" : ""}>${s}</option>`).join("")}</select></label>` +
          (일.출처 === "TRIPO 웹" ? `<label>작업 번호<input type="text" id="impjob" maxlength="80" placeholder="비워도 됨" value="${글(일.작업번호)}"></label>` : "") +
          (일.단계 === 2 && 일.출처 === "TRIPO 웹" ? `<span class="hint">TRIPO 웹에서 받은 모델이면 2단계는 "가져옴"으로 끝이 됩니다.</span>` : "") + `</div>`;
        if (있는입력.length) {
          html += `<div class="impwarn"><div class="wa">${일.단계}단계에 이미 입력이 있습니다. 덮어쓰지 않습니다.</div>` +
            `<div class="inlist">${있는입력.map((x) => `<div>${글(x)}</div>`).join("")}</div>` +
            `<label class="pchk"><input type="checkbox" id="impswap"${일.바꾸기 ? " checked" : ""}>새 입력으로 바꾸기(옛 입력은 03_TRIPO/이전입력_시각/에 사본으로 남김)</label></div>`;
        }
        const 막음 = 일.바쁨 || (있는입력.length && !일.바꾸기);
        단추들 = [[일.바쁨 ? "넣는 중…" : "넣기", "b-ok", 넣기, 막음], ["취소", "b-re", 닫기, 일.바쁨]];
      }
    }
    if (일.오류) html += `<div class="ng">${글(일.오류)}</div>`;
    몸.innerHTML = html;
    단추.className = `btns${단추들.length}`;
    단추.innerHTML = 단추들.map(([t, c, , 흐림], i) => `<button class="btn ${c}" type="button" data-i="${i}"${흐림 ? " disabled" : ""}>${글(t)}</button>`).join("");
    단추.onclick = (ev) => { const b = ev.target.closest("[data-i]"); if (b && !b.disabled) 단추들[Number(b.dataset.i)][2](); };
  }

  function 묻기(제목, 본문, 단추들) {
    return new Promise((풀기) => {
      const o = $("ask2");
      $("ask2ttl").textContent = 제목;
      $("ask2body").innerHTML = 본문;
      const 줄 = $("ask2btns");
      줄.className = `btns${단추들.length}`;
      줄.innerHTML = 단추들.map(([t, c], i) => `<button class="btn ${c}" type="button" data-i="${i}">${글(t)}</button>`).join("");
      o.hidden = false;
      줄.onclick = (ev) => { const b = ev.target.closest("[data-i]"); if (!b) return; o.hidden = true; 줄.onclick = null; 풀기(단추들[Number(b.dataset.i)][2]); };
      줄.querySelector("button").focus();
    });
  }

  // ---- 이벤트
  $("impbody").addEventListener("change", (ev) => {
    const t = ev.target;
    if (t.id === "impstep") 일.단계 = Number(t.value);
    else if (t.id === "impsrc") 일.출처 = t.value;
    else if (t.id === "impswap") 일.바꾸기 = t.checked;
    else return;
    if (t.id !== "impswap") 일.바꾸기 = false;
    그리기();
  });
  $("impbody").addEventListener("input", (ev) => { if (ev.target.id === "impjob") 일.작업번호 = ev.target.value; });
  $("impbody").addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-dir]");
    if (!b || 일.바쁨) return;
    일.앞 = 일.앞 === b.dataset.dir && !일.방향만 ? "모름" : b.dataset.dir;
    그리기();
  });
  $("imp").addEventListener("keydown", (ev) => { if (ev.key === "Escape" && !일.바쁨 && !(일.값 && 일.값.상태 === "검사 중")) 닫기(); });

  const 단추 = document.querySelector(".importbtn");
  단추.disabled = false;
  단추.title = "파일을 골라 가져옵니다. 파일을 이 페이지에 끌어다 놓아도 됩니다.";
  단추.addEventListener("click", () => {
    const 이유 = 막는이유();
    if (이유) { 오류띠(`파일 가져오기: ${이유}`); return; }
    $("impfile").value = "";
    $("impfile").click();
  });
  $("impfile").addEventListener("change", (ev) => { const f = ev.target.files[0]; if (f) 시작(f); });
  // 끌어다 놓기: 페이지 어디에 놓아도 받는다(브라우저가 파일을 열어 버리지 않게)
  let 끌기깊이 = 0;
  const 파일인가 = (ev) => ev.dataTransfer && [...ev.dataTransfer.types].includes("Files");
  window.addEventListener("dragenter", (ev) => { if (!파일인가(ev)) return; ev.preventDefault(); 끌기깊이++; 단추.classList.add("drop"); });
  window.addEventListener("dragleave", (ev) => { if (!파일인가(ev)) return; 끌기깊이 = Math.max(0, 끌기깊이 - 1); if (!끌기깊이) 단추.classList.remove("drop"); });
  window.addEventListener("dragover", (ev) => { if (파일인가(ev)) { ev.preventDefault(); ev.dataTransfer.dropEffect = "copy"; } });
  window.addEventListener("drop", (ev) => {
    if (!파일인가(ev)) return;
    ev.preventDefault(); 끌기깊이 = 0; 단추.classList.remove("drop");
    const 파일들 = [...ev.dataTransfer.files];
    if (파일들.length > 1) 오류띠("파일은 한 번에 하나씩 가져옵니다. 첫 번째 파일만 가져옵니다.");
    if (파일들.length) 시작(파일들[0]);
  });

  return {방향열기};
})();
