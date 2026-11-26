// 부위 (작업 묶음 W05, 기능명세 1부 5-2 "부위 고르기"·5-2b·2-1 "부위.json")
// - 도구 줄 "보이기" 무리의 "파츠 숨김"과 "형태만" 사이에 "부위 ▾". 펼치면 파츠 아래에 부위 목록.
// - 부위를 누르면 그 부위만 밝게, 나머지는 흐리게(또는 숨김), 카메라가 맞춰진다. 다시 누르면 전체. UV 그림에서도 그 부위의 조각만 밝게.
// - 줄마다 보이기(부위 숨김), 이름 바꾸기(다시 만들 때 이어받음). "이 부위 안에서만 칠하기"를 켜면 붓·지우개가 고른 부위 밖을 건드리지 않는다.
// - 칠한 표시의 자리.부위를 부위 이름으로 자동으로 적는다(칠하기.js가 부위이름들()을 부름). 숨긴 부위에는 칠할 수 없다.
// - 부위 목록은 에이전트가 만든다(`10_제작페이지/부위만들기.py`). 작업본해시가 지금 모델과 다르면 회색 + "부위 목록이 옛 것".
// 그리는 법: 면마다 정점이 따로라(GLB의 _faceid가 정점마다 하나) 정점 값 bu_flag(0 보통 · 1 흐림 · 2 숨김)를 넣고 재질 셰이더에서 읽는다.
import * as THREE from "three";

const 상수 = {흐림섞기: 0.72, UV흐림: 0.68, UV숨김: 0.9, 다가감: 1.6, 최소다가감: 0.35};
const 토큰 = (이름) => getComputedStyle(document.documentElement).getPropertyValue(이름).trim();
const 글 = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const 파츠말 = (n) => String(n).replace(/^파츠_/, "");

const 부 = {
  이름: null,           // 캐릭터
  값: null,             // /api/부위 응답
  면부위: new Map(),    // 파츠 → Map(면 → 부위 번호)
  고른: null,           // 부위 번호
  숨김: new Set(),      // 부위 번호
  방식: "흐리게",       // 고르면 나머지를 흐리게 / 숨김
  안에서만: false,
  바꾸는중: null,       // 이름을 바꾸는 부위 번호
  바깥: null,           // 맥박이 알려 준 부위.json 수정 시각
};
window.부위상태 = 부;    // 시험·검사용으로 읽기만

const 보 = () => window.보기3d && window.보기3d.내부;
const 보기 = () => window.보기3d && window.보기3d.상태;
function 보이는해시() {
  const m = 보기() && 보기().지금;
  const r = m && /([0-9a-f]{12})\.glb$/.exec(decodeURIComponent(m.주소 || ""));
  return r ? r[1] : "";
}
function 쓸수있나() { return Boolean(부.값 && 부.값.부위.length && !옛것()); }
function 옛것() { return Boolean(부.값 && 부.값.있음 && (부.값.옛것 || (보이는해시() && 부.값.작업본해시 !== 보이는해시()))); }
function 부위(번호) { return 부.값 && 부.값.부위.find((r) => r.번호 === 번호); }
const 전체이름 = (r) => `${파츠말(r.파츠)} › ${r.이름}`;

// ---------------------------------------------------------------- 단추와 펼침 목록(보기3d.js의 도구 줄에 끼움)
let 단추 = null, 펼침 = null;
function 단추끼우기() {
  const 안쪽 = 보();
  if (!안쪽 || 단추) return Boolean(단추);
  const 형태 = 안쪽.뿌리.querySelector("#v3shape");
  if (!형태) return false;
  단추 = document.createElement("button");
  단추.type = "button"; 단추.className = "tb"; 단추.id = "v3bu";
  단추.setAttribute("aria-expanded", "false");
  단추.title = "부위를 골라 그 부위만 밝게 보기, 부위 숨김, 이름 바꾸기";
  단추.textContent = "부위 ▾";
  펼침 = document.createElement("div");
  펼침.className = "pop bupop"; 펼침.id = "v3bupop"; 펼침.hidden = true;
  형태.before(단추, 펼침);
  단추.addEventListener("click", () => 열기(펼침.hidden));
  펼침.addEventListener("click", 누름);
  펼침.addEventListener("change", 바꿈);
  펼침.addEventListener("keydown", 글쇠);
  document.addEventListener("pointerdown", (ev) => { if (!펼침.hidden && !ev.target.closest("#v3bupop, #v3bu")) 열기(false); });
  return true;
}
function 열기(켬) {
  if (!펼침) return;
  if (켬) { const p = 안("v3pop"); if (p && !p.hidden) p.hidden = true; }   // 파츠 숨김 목록과 겹치지 않게
  펼침.hidden = !켬;
  단추.setAttribute("aria-expanded", String(켬));
  if (켬) 목록그리기();
}
const 안 = (id) => { const 안쪽 = 보(); return 안쪽 && 안쪽.뿌리.querySelector("#" + id); };

function 단추모양() {
  if (!단추) return;
  const 없음 = !보기() || !보기().지금;
  단추.disabled = 없음;
  단추.classList.toggle("on", Boolean(쓸수있나() && (부.고른 || 부.숨김.size)));
  const 고른 = 쓸수있나() && 부.고른 && 부위(부.고른);
  단추.textContent = 고른 ? `부위: ${고른.이름} ▾` : "부위 ▾";
  const 기본 = 고른 ? `고른 부위: ${전체이름(고른)} — 다시 누르면 목록` : "부위를 골라 그 부위만 밝게 보기, 부위 숨김, 이름 바꾸기";
  단추.title = 없음 ? `${기본} — 모델이 아직 없습니다` : 기본;
}

function 목록그리기() {
  if (!펼침 || 펼침.hidden) return;
  if (펼침.contains(document.activeElement) && document.activeElement.tagName === "INPUT" && document.activeElement.type === "text") return;   // 이름을 쓰는 중
  const v = 부.값;
  if (!v) { 펼침.innerHTML = `<div class="hint">부위 목록을 읽는 중…</div>`; return; }
  if (v.오류) { 펼침.innerHTML = `<div class="hint wa">${글(v.오류)}</div>`; return; }
  if (!v.있음 || !v.부위.length) {
    펼침.innerHTML = `<div class="hint">부위 목록이 아직 없습니다. Claude 앱에서 "부위 목록 만들어 줘"라고 하면 에이전트가 만듭니다.</div>`;
    return;
  }
  const 옛 = 옛것(), 막음 = 옛 ? " disabled" : "";
  const 줄 = [];
  줄.push(`<div class="prow"><div class="seg" title="부위를 고르면 나머지를 어떻게 보일지">` +
    ["흐리게", "숨김"].map((m) => `<button type="button" class="${부.방식 === m ? "on" : ""}" data-bm="${m}" aria-pressed="${부.방식 === m}"${막음}>나머지 ${m}</button>`).join("") +
    `</div></div><div class="prow"><label class="pchk" title="켜면 붓·지우개가 고른 부위 밖을 건드리지 않습니다"><input type="checkbox" id="bulock"${부.안에서만 ? " checked" : ""}${옛 || !부.고른 ? " disabled" : ""}><span class="pn">이 부위 안에서만 칠하기</span></label></div>`);
  if (옛) 줄.push(`<div class="hint wa">부위 목록이 옛 것입니다(작업본이 바뀜). 에이전트가 다시 만들 때까지 고르기·숨김을 쓰지 않습니다.</div>`);
  let 앞파츠 = null;
  for (const r of v.부위) {
    if (r.파츠 !== 앞파츠) { 앞파츠 = r.파츠; 줄.push(`<div class="bugh">${글(파츠말(r.파츠))}</div>`); }
    const 고름 = 부.고른 === r.번호, 숨 = 부.숨김.has(r.번호);
    const 바뀐 = r.사용자가바꾼이름 ? ` (자동 이름: ${r.자동이름 || ""})` : "";
    if (부.바꾸는중 === r.번호) {
      줄.push(`<div class="prow"><input type="text" class="buin" id="buin" maxlength="40" value="${글(r.이름)}" aria-label="${글(전체이름(r))} 새 이름" placeholder="비우면 자동 이름(${글(r.자동이름 || "")})">` +
        `<button type="button" class="tb" data-bok="${r.번호}">저장</button><button type="button" class="tb" data-bno="${r.번호}">그만</button></div>`);
      continue;
    }
    줄.push(`<div class="prow bur${옛 ? " old" : ""}">` +
      `<label class="pchk buchk" title="${글(전체이름(r))} 보이기(끄면 숨김, 숨긴 부위에는 칠할 수 없음)"><input type="checkbox" data-bh="${r.번호}"${숨 ? "" : " checked"}${막음}></label>` +
      `<button type="button" class="tb bun${고름 ? " on" : ""}" data-bs="${r.번호}" title="${글(`${전체이름(r)}, 면 ${r.면.length}개${바뀐} — ${고름 ? "다시 누르면 전체" : "누르면 이 부위만 밝게, 카메라를 맞춤"}`)}"${막음}>${글(r.이름)}${r.사용자가바꾼이름 ? " ✎" : ""}</button>` +
      `<span class="bucnt">${r.면.length}</span>` +
      `<button type="button" class="tb" data-br="${r.번호}" title="이름 바꾸기(다시 만들어도 같은 자리면 이어받음)"${막음}>이름</button></div>`);
  }
  줄.push(`<div class="hint">이름이 틀리면 "이름"으로 바꿉니다. 묶음 자체가 틀렸으면 Claude 앱에서 말해 주세요.</div>`);
  펼침.innerHTML = 줄.join("");
  const 입력 = 펼침.querySelector("#buin");
  if (입력) { 입력.focus(); 입력.select(); }
}

function 누름(ev) {
  const b = ev.target.closest("button");
  if (!b || b.disabled) return;
  if (b.dataset.bm) { 부.방식 = b.dataset.bm; 다시칠하기(); 목록그리기(); return; }
  if (b.dataset.bs) { 고르기(+b.dataset.bs); return; }
  if (b.dataset.br) { 부.바꾸는중 = +b.dataset.br; 목록그리기(); return; }
  if (b.dataset.bno) { 부.바꾸는중 = null; 목록그리기(); return; }
  if (b.dataset.bok) { 이름저장(+b.dataset.bok); return; }
}
function 바꿈(ev) {
  const t = ev.target;
  if (t.id === "bulock") { 부.안에서만 = t.checked; 상태알림(); return; }
  if (t.dataset.bh) {
    const n = +t.dataset.bh;
    if (t.checked) 부.숨김.delete(n); else { 부.숨김.add(n); if (부.고른 === n) 부.고른 = null; }
    다시칠하기(); 목록그리기();
  }
}
function 글쇠(ev) {
  if (ev.target.id !== "buin") return;
  if (ev.key === "Enter") { ev.preventDefault(); 이름저장(부.바꾸는중); }
  if (ev.key === "Escape") { ev.preventDefault(); ev.stopPropagation(); 부.바꾸는중 = null; 목록그리기(); }
}
async function 이름저장(번호) {
  const 입력 = 펼침.querySelector("#buin");
  if (!입력) return;
  const 새이름 = 입력.value;
  try {
    const r = await fetch("/api/부위이름", {method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({이름: 부.이름, 탭: window.탭id || "", 번호, 새이름, 작업본해시: 부.값.작업본해시 || ""})});
    const v = await r.json();
    if (!r.ok) throw new Error(v.오류 || r.status);
    const x = 부위(번호);
    if (x) { x.이름 = v.이름; x.사용자가바꾼이름 = v.사용자가바꾼이름; }
    부.바꾸는중 = null;
    입력.blur();
    목록그리기(); 단추모양();
    if (window.칠하기) window.칠하기.상태글(`이름을 "${v.이름}"(으)로 바꿨습니다`);
  } catch (e) {
    if (window.칠하기) window.칠하기.상태글(`이름을 바꾸지 못함: ${e.message || e}`);
    await 읽기();
  }
}

// ---------------------------------------------------------------- 고르기·숨김을 3D와 UV에 반영
function 고르기(번호) {
  부.고른 = 부.고른 === 번호 ? null : 번호;
  if (!부.고른) 부.안에서만 = false;
  부.숨김.delete(부.고른);
  다시칠하기();
  목록그리기();
  const 안쪽 = 보(), b = 보기();
  if (!안쪽 || !b) return;
  if (!부.고른) { window.보기3d.처음자리(); return; }
  const r = 부위(부.고른);
  const 상 = 면상자(r.파츠, new Set(r.면));
  if (상.isEmpty()) return;
  const 크기 = 상.getSize(new THREE.Vector3()).length();
  안쪽.옮기기({중심: 상.getCenter(new THREE.Vector3()), 거리: 안쪽.거리제한(Math.max(크기 * 상수.다가감, b.크기 * 상수.최소다가감))});
  // 숨긴 파츠·"이 파츠만"에 가려 안 보이면 알림
  if (b.하나 ? b.하나 !== r.파츠 : b.숨김.has(r.파츠)) window.칠하기 && window.칠하기.상태글(`${파츠말(r.파츠)} 파츠가 숨겨져 있어 보이지 않습니다(파츠 숨김)`);
}
function 면상자(파츠, 면) {
  const b = new THREE.Box3(), v = new THREE.Vector3();
  const m = 보기() && 보기().지금;
  for (const o of (m && m.파츠.get(파츠)) || []) {
    const g = o.geometry, f = g.attributes._faceid, p = g.attributes.position;
    if (!f) continue;
    o.updateWorldMatrix(true, false);
    for (let i = 0; i < f.count; i++) if (면.has(Math.round(f.getX(i)))) b.expandByPoint(v.fromBufferAttribute(p, i).applyMatrix4(o.matrixWorld));
  }
  return b;
}
// 면 → 0 보통 · 1 흐림 · 2 숨김
function 면값(파츠, f) {
  if (!쓸수있나()) return 0;
  const n = (부.면부위.get(파츠) || new Map()).get(f);
  if (n !== undefined && 부.숨김.has(n)) return 2;
  if (부.고른 && n !== 부.고른) return 부.방식 === "숨김" ? 2 : 1;
  return 0;
}
function 패치(재질) {
  if (!재질 || 재질.userData.부위패치) return;
  재질.userData.부위패치 = true;
  const 원래 = 재질.onBeforeCompile;
  const 원래열쇠 = 재질.customProgramCacheKey;
  재질.onBeforeCompile = (s, r) => {
    if (원래) 원래.call(재질, s, r);
    s.uniforms.buDim = {value: new THREE.Color(토큰("--c-canvas"))};
    s.vertexShader = "attribute float bu_flag;\nvarying float vBuFlag;\n" + s.vertexShader.replace("#include <begin_vertex>", "#include <begin_vertex>\nvBuFlag = bu_flag;");
    s.fragmentShader = "varying float vBuFlag;\nuniform vec3 buDim;\n" + s.fragmentShader
      .replace("#include <clipping_planes_fragment>", "if (vBuFlag > 1.5) discard;\n#include <clipping_planes_fragment>")
      .replace("#include <dithering_fragment>", `#include <dithering_fragment>\nif (vBuFlag > 0.5) gl_FragColor.rgb = mix(gl_FragColor.rgb, buDim, ${상수.흐림섞기});`);
  };
  재질.customProgramCacheKey = () => `${원래열쇠 ? 원래열쇠.call(재질) : ""}|부위`;
  재질.needsUpdate = true;
}
function 다시칠하기() {
  const m = 보기() && 보기().지금;
  if (m) for (const [이름, 메시들] of m.파츠) for (const o of 메시들) {
    const g = o.geometry, f = g.attributes._faceid;
    if (!f) continue;
    let a = g.attributes.bu_flag;
    if (!a || a.count !== f.count) { a = new THREE.BufferAttribute(new Float32Array(f.count), 1); g.setAttribute("bu_flag", a); }
    const 배열 = a.array;
    let 바뀜 = false;
    for (let i = 0; i < f.count; i++) {
      const v = 면값(이름, Math.round(f.getX(i)));
      if (배열[i] !== v) { 배열[i] = v; 바뀜 = true; }
    }
    if (바뀜) a.needsUpdate = true;
    for (const 재질 of [].concat(o.material || [])) 패치(재질);
    // 칠하기.js의 겹친 메시(칠한 곳)도 같은 값을 써서 숨긴 곳에 칠이 떠 보이지 않게
    for (const c of o.children) if (c.userData.겹침) {
      if (c.geometry.attributes.bu_flag !== a) c.geometry.setAttribute("bu_flag", a);
      for (const 재질 of [].concat(c.material || [])) 패치(재질);
    }
  }
  단추모양();
  상태알림();
  if (보()) 보().그리기요청();
  window.dispatchEvent(new Event("부위바뀜"));   // UV 그림 칸이 다시 그린다
}
function 상태알림() { if (보()) 보().상태줄(); }
// 3D 보기 왼쪽 아래 상태 글에 붙는 것(보기3d.js 상태줄이 부름)
function 상태글() {
  if (!쓸수있나()) return 옛것() ? "부위 목록이 옛 것" : "";
  const r = 부.고른 && 부위(부.고른), 조각 = [];
  if (r) 조각.push(`부위: ${전체이름(r)}${부.안에서만 ? " (안에서만 칠하기)" : ""}`);
  if (부.숨김.size) 조각.push(`숨긴 부위 ${부.숨김.size}개`);
  return 조각.join(" · ");
}

// ---------------------------------------------------------------- 읽기
async function 읽기() {
  const 이름 = 부.이름;
  if (!이름) return;
  try {
    const r = await fetch(`/api/부위?이름=${encodeURIComponent(이름)}`, {cache: "no-store"});
    const v = await r.json();
    if (이름 !== 부.이름) return;
    if (!r.ok) throw new Error(v.오류 || r.status);
    // 목록을 다시 만들었으면(작업본해시가 바뀜) 번호가 다른 부위를 가리킬 수 있어 고르기·숨김을 푼다
    if (부.값 && 부.값.작업본해시 !== v.작업본해시) { 부.고른 = null; 부.숨김.clear(); 부.안에서만 = false; 부.바꾸는중 = null; }
    부.값 = v;
  } catch (e) {
    if (이름 !== 부.이름) return;
    부.값 = {있음: false, 오류: `부위 목록을 읽지 못함: ${e.message || e} (서버가 옛 버전이면 껐다 켜 주세요)`, 부위: []};
  }
  부.면부위 = new Map();
  for (const r of 부.값.부위) {
    if (!부.면부위.has(r.파츠)) 부.면부위.set(r.파츠, new Map());
    const m = 부.면부위.get(r.파츠);
    for (const f of r.면) m.set(f, r.번호);
  }
  const 번호들 = new Set(부.값.부위.map((r) => r.번호));
  if (부.고른 && !번호들.has(부.고른)) 부.고른 = null;
  for (const n of [...부.숨김]) if (!번호들.has(n)) 부.숨김.delete(n);
  if (!부.고른) 부.안에서만 = false;
  다시칠하기();
  목록그리기();
}

// ---------------------------------------------------------------- 칠하기.js·uv그림.js가 쓰는 것
// 붓이 담은 면(Map 파츠 → Set 면)에서 숨긴 부위와(안에서만 칠하기면) 고른 부위 밖을 뺀다
function 칠됨(파츠, f) {
  if (!쓸수있나()) return true;
  const n = (부.면부위.get(파츠) || new Map()).get(f);
  if (n !== undefined && 부.숨김.has(n)) return false;
  if (부.고른 && n !== 부.고른 && (부.안에서만 || 부.방식 === "숨김")) return false;
  return true;
}
function 거르기(담) {
  if (!쓸수있나()) return 담;
  const 새 = new Map();
  for (const [파츠, s] of 담) {
    const 남 = new Set([...s].filter((f) => 칠됨(파츠, f)));
    if (남.size) 새.set(파츠, 남);
  }
  return 새;
}
// 자리.면 → 부위 이름 목록("상체 › 왼쪽 아래팔"), 면이 많이 든 부위부터. 목록이 없거나 옛 것이면 null
function 부위이름들(면) {
  if (!쓸수있나()) return null;
  const 세기 = new Map();
  for (const [파츠, l] of Object.entries(면 || {})) {
    const m = 부.면부위.get(파츠);
    if (!m) continue;
    for (const f of l) { const n = m.get(f); if (n !== undefined) 세기.set(n, (세기.get(n) || 0) + 1); }
  }
  return [...세기].sort((a, b) => b[1] - a[1]).map(([n]) => 전체이름(부위(n)));
}
// UV 그림 칸: 파츠의 면 → 0/1/2 (고르기·숨김이 없으면 null)
function 면모양(파츠) {
  if (!쓸수있나() || (!부.고른 && !부.숨김.size)) return null;
  return (f) => 면값(파츠, f);
}

function 붙이기(이름) {
  단추끼우기();
  if (이름 !== 부.이름) {
    부.이름 = 이름; 부.값 = null; 부.면부위 = new Map(); 부.고른 = null; 부.숨김.clear(); 부.안에서만 = false; 부.바꾸는중 = null; 부.바깥 = null;
    if (펼침) 펼침.hidden = true;
    if (이름) 읽기();
  }
  단추모양();
}
function 바깥바뀜(시각) {
  if (시각 === undefined || 시각 === 부.바깥) return;
  const 처음 = 부.바깥 === null;
  부.바깥 = 시각;
  if (!처음) 읽기();
}

window.addEventListener("보기3d모델", () => { 다시칠하기(); 목록그리기(); });
window.addEventListener("보기3d모양", 다시칠하기);   // 형태만·격자·파츠 숨김으로 재질이 바뀜
window.부위 = {붙이기, 바깥바뀜, 거르기, 칠됨, 부위이름들, 면모양, 상태글, 다시읽기: 읽기, 상태: 부,
  UV흐림: 상수.UV흐림, UV숨김: 상수.UV숨김};
window.dispatchEvent(new Event("부위준비"));
