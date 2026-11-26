// 가마우지 제작 페이지 — 칠하기와 표시(W03, 기능명세 1부 2-1·3·4-4·5-4·5-4b·5-5절)
// 3D 보기(보기3d.js)의 장면 위에 붓·지우개로 면을 칠하고, 표시 목록을 보이며, 작성중.json에 자동 저장하고,
// "보내기"로 보내기_<시각>.json을 쓴다. 서버(127.0.0.1)에만 요청한다.
// 면 고르기: 보이는 메시를 "면 번호 색"으로 따로 그린 그림(고르기 그림)에서 붓 원 안의 화소를 읽는다 → 화면에 보이는 면만 칠해진다.
// 크기·색 숫자는 맨 위 "그림 상수" 한 곳. 색은 디자인 토큰에서 읽는다.
// UV 그림 칸(W04, uv그림.js)은 면칠하기·미리보기·겹침모음과 "칠하기겹침" 사건으로 붙는다. 하지 않는 것: 부위(W05), 결정 단추·알림(W06).
import * as THREE from "three";

// ---------------------------------------------------------------- 그림 상수
const 상수 = {
  붓기본: 24, 붓최소: 4, 붓최대: 160,   // 붓 반지름(화면 화소)
  붓휠: 0.004,                          // Shift+휠 1단위당 크기 비율(지수)
  끌기문턱: 4,                          // 이보다 덜 움직이면 "한 번 누름" = 그 면 하나
  칠한곳투명: 0.45, 고른곳투명: 0.7, 후보투명: 0.35,
  깜박횟수: 6, 깜박간격: 180,           // 줄을 누르면 그 표시가 깜박임(ms)
  저장늦춤: 400,                        // 바뀐 뒤 이만큼 조용하면 자동 저장(ms)
  다가감: 3, 최소다가감: 0.35,          // 줄을 누를 때 표시 크기의 몇 배 거리로 다가가나, 모델 크기의 이만큼보다 가까이 가지 않음
  많은표시: 100,                        // 한 묶음 경고(사용자 확정)
};
// 비대칭 예외(SSOT 41_사용자_방침 "비대칭 예외"): 이 낱말이 부위·파츠 이름에 있으면 "반대쪽도"를 켤 수 없다
const 비대칭예외 = ["스카프", "치마 주름", "포니테일", "표정", "반사점", "하이라이트"];
const 판단들 = ["고칠 것", "둘 것", "모름"];

const 토큰 = (이름) => getComputedStyle(document.documentElement).getPropertyValue(이름).trim();
const 글 = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const $ = (id) => document.getElementById(id);

// ①…㊿, 그 뒤는 (51)
function 동그라미(n) {
  if (n >= 1 && n <= 20) return String.fromCodePoint(0x2460 + n - 1);
  if (n >= 21 && n <= 35) return String.fromCodePoint(0x3251 + n - 21);
  if (n >= 36 && n <= 50) return String.fromCodePoint(0x32B1 + n - 36);
  return `(${n})`;
}
function 번호값(s) {
  const c = String(s || "").codePointAt(0);
  if (c >= 0x2460 && c <= 0x2473) return c - 0x2460 + 1;
  if (c >= 0x3251 && c <= 0x325F) return c - 0x3251 + 21;
  if (c >= 0x32B1 && c <= 0x32BF) return c - 0x32B1 + 36;
  const m = /^\((\d+)\)$/.exec(s || "");
  return m ? Number(m[1]) : 0;
}
const 복사 = (v) => JSON.parse(JSON.stringify(v));

// ---------------------------------------------------------------- 상태
const 칠 = {
  이름: null, 단계: 0, 처리목록: [], 메모필수: ["기타"], 취소한도: 50,
  작업본해시: "",             // 지금 작업본(서버가 계산)
  표시: [], 후보판단: [], 다음번호: 1, 묶음번호: 0,
  취소: [], 다시: [],
  묶음: [], 후보: null,       // 서버가 읽은 보낸 묶음, 가장 최근 후보 파일
  고른: null,                 // 고른 표시의 번호(이어 칠하기·메모)
  도구: "보기", 붓: 상수.붓기본, 칠할종류: null,
  미저장: false, 저장중: false, 저장글: "", 저장실패: "",
  읽음: false, 읽는중: false, 보낸글: "", 막힘글: "",
  바깥표시: null,             // 서버의 표시 파일 바뀜 값(다른 곳이 쓴 후보·처리를 알아챔)
};
window.칠하기상태 = 칠;       // 시험·검사용으로 읽기만

// ---------------------------------------------------------------- 표시 목록 칸(한 번 만들고 다시 붙인다)
const 뿌리 = document.createElement("div");
뿌리.className = "marks";
뿌리.dataset.순서 = "표시 목록";
뿌리.innerHTML = `
<div class="mhead">
  <span class="mttl">표시 목록</span>
  <span class="mlab">칠할 처리</span><div class="seg" id="p3kind" role="group" aria-label="칠할 처리"></div>
  <span class="sp"></span>
  <span class="mst" id="p3size" title="붓 크기: Shift+휠로 바꿉니다"></span>
  <button type="button" class="tb" id="p3undo" title="취소 (Ctrl+Z)">취소<span class="k">Ctrl+Z</span></button>
  <button type="button" class="tb" id="p3redo" title="다시 (Ctrl+Y)">다시<span class="k">Ctrl+Y</span></button>
</div>
<div class="mlist" id="p3list"></div>
<div class="note mdetail" id="p3detail" hidden></div>
<div class="mfoot"><span class="mst" id="p3save"></span></div>
<details class="msent" id="p3sent" hidden><summary id="p3sentsum"></summary><div class="msentbody" id="p3sentbody"></div></details>`;
const 안 = (id) => 뿌리.querySelector("#" + id);

// ---------------------------------------------------------------- 3D 쪽(보기3d.js의 안쪽을 함께 씀)
const 보 = () => window.보기3d && window.보기3d.내부;
const 모델 = () => window.보기3d && window.보기3d.상태.지금;
let 면지도 = null;          // 파츠 이름 → [{메시, 면→삼각형[]}]
let 겹침 = [];              // 칠한 곳을 보이는 겹친 메시들
let 재질 = null;
let 깜박 = null;            // {번호|후보키, 남은, 켬}

function 재질만들기() {
  if (재질) return 재질;
  const 기본 = {transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -4, side: THREE.DoubleSide};
  재질 = {
    사용자: new THREE.MeshBasicMaterial({...기본, color: new THREE.Color(토큰("--c-danger")), opacity: 상수.칠한곳투명}),
    고른: new THREE.MeshBasicMaterial({...기본, color: new THREE.Color(토큰("--c-warn")), opacity: 상수.고른곳투명}),
    후보: new THREE.MeshBasicMaterial({...기본, color: new THREE.Color(토큰("--c-accent")), opacity: 상수.후보투명}),
  };
  return 재질;
}

function 보이는해시() {
  const m = 모델();
  const r = m && /([0-9a-f]{12})\.glb$/.exec(decodeURIComponent(m.주소 || ""));
  return r ? r[1] : "";
}

// 면 번호(_faceid, 작업본의 면 번호) → 그 면의 삼각형들. 파츠마다, 메시마다(재질이 여럿이면 메시도 여럿)
function 면지도만들기() {
  면지도 = null;
  for (const o of 겹침) { o.parent && o.parent.remove(o); o.geometry.dispose(); }
  겹침 = [];
  const m = 모델();
  if (!m) return;
  면지도 = new Map();
  let 파츠번호 = 0;
  for (const [이름, 메시들] of m.파츠) {
    const 목록 = [];
    for (const o of 메시들) {
      const g = o.geometry, a = g.attributes._faceid;
      if (!a) continue;
      const 색인 = g.index ? g.index.array : null;
      const 삼각수 = 색인 ? 색인.length / 3 : a.count / 3;
      const 면 = new Map();
      for (let t = 0; t < 삼각수; t++) {
        const v = 색인 ? 색인[t * 3] : t * 3;
        const f = Math.round(a.getX(v));
        let l = 면.get(f);
        if (!l) 면.set(f, (l = []));
        l.push(t);
      }
      목록.push({메시: o, 면, 파츠: 이름, 파츠번호});
    }
    if (목록.length) 면지도.set(이름, 목록);
    파츠번호++;
  }
  for (const 목록 of 면지도.values()) for (const 칸 of 목록) {
    칸.겹침 = {};
    for (const 종류 of ["후보", "사용자", "고른"]) {
      const g = new THREE.BufferGeometry();
      for (const [k, v] of Object.entries(칸.메시.geometry.attributes)) g.setAttribute(k, v);
      g.setIndex(new THREE.BufferAttribute(new Uint32Array(0), 1));
      const o = 칸.메시.isSkinnedMesh ? new THREE.SkinnedMesh(g, 재질만들기()[종류]) : new THREE.Mesh(g, 재질만들기()[종류]);
      if (칸.메시.isSkinnedMesh) o.bind(칸.메시.skeleton, 칸.메시.bindMatrix);
      o.frustumCulled = false;
      o.raycast = () => {};          // 3D 보기의 고르기(두 번 누르기·Alt+클릭)에 걸리지 않게
      o.renderOrder = 종류 === "고른" ? 3 : 종류 === "사용자" ? 2 : 1;
      o.userData.겹침 = true;
      o.visible = false;
      칸.메시.add(o);
      칸.겹침[종류] = o;
      겹침.push(o);
    }
  }
}

// 표시들의 면을 겹친 메시의 삼각형 색인으로
let 마지막모음 = {후보: new Map(), 사용자: new Map(), 고른: new Map()};
function 겹침다시(진행중 = null) {
  if (!면지도) return;
  const h = 보이는해시();
  const 모음 = {후보: new Map(), 사용자: new Map(), 고른: new Map()};
  const 넣기 = (종류, 자리) => {
    for (const [파츠, 면] of Object.entries((자리 && 자리.면) || {})) {
      if (!모음[종류].has(파츠)) 모음[종류].set(파츠, new Set());
      const s = 모음[종류].get(파츠);
      for (const f of 면) s.add(f);
    }
  };
  if (칠.후보 && 칠.후보.작업본해시 === h) for (const x of 보이는후보()) {
    const 깜박임 = 깜박 && 깜박.열쇠 === 후보열쇠(x);
    if (깜박임 && !깜박.켬) continue;
    넣기(깜박임 ? "고른" : "후보", x.자리);
  }
  for (const x of 칠.표시) {
    if (x.작업본해시 !== h) continue;                       // 옛 버전 표시는 바뀐 모델 위에 얹지 않는다(3-3)
    const 깜박임 = 깜박 && 깜박.열쇠 === x.번호;
    if (깜박임 && !깜박.켬) continue;
    넣기(x.번호 === 칠.고른 || 깜박임 ? "고른" : "사용자", x.자리);
  }
  if (진행중) 넣기(진행중.지우개 ? "후보" : "고른", 진행중.자리);   // 칠하는 중(지우개는 지울 곳을 파랑으로)
  마지막모음 = 모음;
  window.dispatchEvent(new Event("칠하기겹침"));   // UV 그림 칸이 같은 색으로 다시 그린다
  for (const [파츠, 목록] of 면지도) for (const 칸 of 목록) {
    for (const 종류 of ["후보", "사용자", "고른"]) {
      const o = 칸.겹침[종류], 면 = 모음[종류].get(파츠);
      const 삼각 = [];
      if (면) for (const f of 면) for (const t of 칸.면.get(f) || []) 삼각.push(t);
      const 원색인 = 칸.메시.geometry.index;
      const 새 = new Uint32Array(삼각.length * 3);
      삼각.forEach((t, i) => {
        for (let k = 0; k < 3; k++) 새[i * 3 + k] = 원색인 ? 원색인.array[t * 3 + k] : t * 3 + k;
      });
      o.geometry.setIndex(new THREE.BufferAttribute(새, 1));
      o.visible = 새.length > 0;
    }
  }
  if (보()) 보().그리기요청();
}

// ---- 고르기 그림: 보이는 메시만 면 번호 색으로 그린다(R·G·B = 면 번호 + 1, A = 파츠 번호 + 1)
let 고르기 = null;   // {대상, 화소, 가로, 세로, 배율}
const 고르기재질들 = new Map();
function 고르기재질(파츠번호, 면) {
  const 열쇠 = `${파츠번호}:${면}`;
  if (고르기재질들.has(열쇠)) return 고르기재질들.get(열쇠);
  const m = new THREE.MeshBasicMaterial({side: 면, blending: THREE.NoBlending, toneMapped: false});
  m.onBeforeCompile = (s) => {
    // bu_flag(부위.js, W05): 2 = 숨긴 부위 → 고르기 그림에서도 빼서 칠할 수 없게
    s.vertexShader = "attribute float _faceid;\nattribute float bu_flag;\nvarying float vFaceId;\nvarying float vBuFlag;\n" + s.vertexShader.replace("#include <begin_vertex>", "#include <begin_vertex>\nvFaceId = _faceid;\nvBuFlag = bu_flag;");
    s.fragmentShader = "varying float vFaceId;\nvarying float vBuFlag;\n" + s.fragmentShader.replace("#include <clipping_planes_fragment>", "if (vBuFlag > 1.5) discard;\n#include <clipping_planes_fragment>").replace("#include <dithering_fragment>",
      `#include <dithering_fragment>
      float fid = floor(vFaceId + 0.5) + 1.0;
      gl_FragColor = vec4(mod(fid, 256.0), mod(floor(fid / 256.0), 256.0), mod(floor(fid / 65536.0), 256.0), ${파츠번호 + 1}.0) / 255.0;`);
  };
  m.customProgramCacheKey = () => 열쇠;
  고르기재질들.set(열쇠, m);
  return m;
}
function 고르기그리기() {
  const 안쪽 = 보(), m = 모델();
  if (!안쪽 || !m || !면지도) return null;
  const 그리개 = 안쪽.그리개(), 씬 = 안쪽.씬(), 캔 = 안쪽.캔버스;
  const 배율 = 그리개.getPixelRatio();
  const 가로 = Math.max(1, Math.round(캔.clientWidth * 배율)), 세로 = Math.max(1, Math.round(캔.clientHeight * 배율));
  if (!고르기 || 고르기.가로 !== 가로 || 고르기.세로 !== 세로) {
    if (고르기) 고르기.대상.dispose();
    고르기 = {대상: new THREE.WebGLRenderTarget(가로, 세로, {depthBuffer: true}), 화소: new Uint8Array(가로 * 세로 * 4), 가로, 세로, 배율, 파츠이름: []};
  }
  안쪽.카메라놓기(캔.clientWidth, 캔.clientHeight);
  const 바꾼 = [], 숨김 = [];
  고르기.파츠이름 = [];
  for (const [이름, 목록] of 면지도) for (const 칸 of 목록) {
    고르기.파츠이름[칸.파츠번호] = 이름;
    const 원 = 칸.메시.material, 면 = (Array.isArray(원) ? 원[0] : 원).side;
    바꾼.push([칸.메시, 원]);
    칸.메시.material = 고르기재질(칸.파츠번호, 면);
  }
  for (const o of 겹침) if (o.visible) { o.visible = false; 숨김.push(o); }
  씬.traverse((o) => { if (o.userData.고르기빼기 && o.visible) { o.visible = false; 숨김.push(o); } });   // UV 그림 칸이 띄운 점
  const 전 = window.보기3d.상태.전;
  const 전보임 = 전 && 전.뿌리.visible;
  if (전) 전.뿌리.visible = false;
  m.뿌리.visible = true;
  const 바탕 = 씬.background;
  씬.background = null;
  const 맑음 = new THREE.Color();
  그리개.getClearColor(맑음);
  const 맑음a = 그리개.getClearAlpha();
  그리개.setClearColor(0x000000, 0);
  그리개.setRenderTarget(고르기.대상);
  그리개.clear();
  그리개.render(씬, 안쪽.카메라());
  그리개.readRenderTargetPixels(고르기.대상, 0, 0, 가로, 세로, 고르기.화소);
  그리개.setRenderTarget(null);
  그리개.setClearColor(맑음, 맑음a);
  씬.background = 바탕;
  for (const [o, 원] of 바꾼) o.material = 원;
  for (const o of 숨김) o.visible = true;
  if (전) 전.뿌리.visible = 전보임;
  고르기.배율 = 배율;
  안쪽.그리기요청();
  return 고르기;
}
// 화면(캔버스 안 CSS 화소) 원 안의 면들 → Map(파츠 → Set(면))
function 원안의면(x, y, 반지름, 담을곳) {
  const g = 고르기;
  if (!g) return;
  const cx = x * g.배율, cy = (g.세로 / g.배율 - y) * g.배율, r = Math.max(0.5, 반지름 * g.배율);
  const x0 = Math.max(0, Math.floor(cx - r)), x1 = Math.min(g.가로 - 1, Math.ceil(cx + r));
  const y0 = Math.max(0, Math.floor(cy - r)), y1 = Math.min(g.세로 - 1, Math.ceil(cy + r));
  for (let py = y0; py <= y1; py++) for (let px = x0; px <= x1; px++) {
    if ((px - cx) ** 2 + (py - cy) ** 2 > r * r) continue;
    한화소(px, py, 담을곳);
  }
}
function 한화소(px, py, 담을곳) {
  const g = 고르기, i = (py * g.가로 + px) * 4, a = g.화소[i + 3];
  if (!a) return false;
  const f = g.화소[i] + g.화소[i + 1] * 256 + g.화소[i + 2] * 65536 - 1, 파츠 = g.파츠이름[a - 1];
  if (f < 0 || !파츠) return false;
  if (window.부위 && !window.부위.칠됨(파츠, f)) return false;   // 숨긴 부위, "이 부위 안에서만 칠하기" 밖(W05)
  if (!담을곳.has(파츠)) 담을곳.set(파츠, new Set());
  담을곳.get(파츠).add(f);
  return true;
}
function 누른면(x, y) {
  const g = 고르기, 담 = new Map();
  if (g) {
    const px = Math.floor(x * g.배율), py = Math.floor((g.세로 / g.배율 - y) * g.배율);
    if (px >= 0 && py >= 0 && px < g.가로 && py < g.세로) 한화소(px, py, 담);
  }
  return 담;
}

// ---------------------------------------------------------------- 칠할 수 있나(못 하면 이유)
function 칠못함이유() {
  const b = window.보기3d && window.보기3d.상태;
  if (!칠.처리목록.length) return "이 단계에서는 칠하지 않습니다";
  if (!b || !b.지금) return "모델이 아직 없습니다";
  if (document.body.dataset.잠금) return document.body.dataset.잠금 === "다른 탭" ? "다른 탭에서 열려 있어 이 탭에서는 칠할 수 없습니다" : "탭을 확인하는 중입니다";
  if (!칠.읽음) return "표시를 불러오는 중입니다";
  if (b.미리주소) return "미리 보기 중에는 칠할 수 없습니다. 옮긴 동작에서 칠하세요('미리 보기 끝')";   // W14
  if (b.갱신중) return "모델을 새로 만드는 중이라 칠할 수 없습니다(갱신 중)";
  if (보이는해시() !== 칠.작업본해시 && 칠.작업본해시) return "보이는 모델이 지금 작업본과 다릅니다. 새 모델이 뜰 때까지 기다려 주세요";
  if (b.전보기 || b.나란히) return "전후 비교 중에는 칠할 수 없습니다";
  const 리깅 = window.리깅단계 && window.리깅단계.칠못함();   // W13: 9단계는 멈춘 장면에서만, 네 방향 보기에서는 못 칠함
  if (리깅) return 리깅;
  if (칠.묶음.some((x) => x.묶음상태 === "처리 중")) return "에이전트가 처리 중이라 칠하기를 막았습니다";
  return "";
}

// ---------------------------------------------------------------- 붓질
let 붓질 = null;   // {지우개, x, y, 처음x, 처음y, 움직임, 자리: {면: {파츠: [..]}}, 담: Map, 첫면: Map}
const 원 = document.createElement("div");
원.className = "brush";
원.hidden = true;

function 캔버스자리(ev) {
  const r = 보().캔버스.getBoundingClientRect();
  return {x: ev.clientX - r.left, y: ev.clientY - r.top};
}
function 원보이기(ev) {
  const 붓듦 = 칠.도구 !== "보기" && !칠못함이유();
  if (!붓듦 || !ev) { 원.hidden = true; return; }
  const p = 캔버스자리(ev), d = 칠.붓 * 2;
  원.hidden = false;
  원.classList.toggle("erase", 칠.도구 === "지우개");
  원.style.width = 원.style.height = `${d}px`;
  원.style.left = `${p.x - 칠.붓}px`;
  원.style.top = `${p.y - 칠.붓}px`;
}
function 담기를자리로(담) {
  const 면 = {};
  for (const [파츠, s] of 담) 면[파츠] = [...s].sort((a, b) => a - b);
  return {면};
}
function 붓시작(ev) {
  const 안쪽 = 보();
  if (!고르기그리기()) return;
  const p = 캔버스자리(ev);
  붓질 = {지우개: 칠.도구 === "지우개", x: p.x, y: p.y, 처음x: p.x, 처음y: p.y, 움직임: 0, 담: new Map(), 첫면: 누른면(p.x, p.y)};
  원안의면(p.x, p.y, 칠.붓, 붓질.담);
  안쪽.캔버스.setPointerCapture(ev.pointerId);
  붓질.id = ev.pointerId;
  겹침다시({지우개: 붓질.지우개, 자리: 담기를자리로(붓질.담)});
}
function 붓움직임(ev) {
  const p = 캔버스자리(ev);
  const dx = p.x - 붓질.x, dy = p.y - 붓질.y, 길이 = Math.hypot(dx, dy);
  const 걸음 = Math.max(1, 칠.붓 / 2), n = Math.ceil(길이 / 걸음);
  for (let i = 1; i <= n; i++) 원안의면(붓질.x + dx * i / n, 붓질.y + dy * i / n, 칠.붓, 붓질.담);   // 빠르게 끌어도 빈틈 없이
  붓질.x = p.x; 붓질.y = p.y;
  붓질.움직임 = Math.max(붓질.움직임, Math.hypot(p.x - 붓질.처음x, p.y - 붓질.처음y));
  겹침다시({지우개: 붓질.지우개, 자리: 담기를자리로(붓질.담)});
}
function 붓끝() {
  const d = 붓질;
  붓질 = null;
  const 담 = d.움직임 < 상수.끌기문턱 ? d.첫면 : d.담;   // 끌지 않고 한 번 누르면 그 면 하나
  let 수 = 0;
  for (const s of 담.values()) 수 += s.size;
  if (!수) { 겹침다시(); 상태글(window.부위 && window.부위.상태글() ? "모델 밖이거나 칠할 수 없는 부위(숨김·고른 부위 밖)라 칠하지 않았습니다" : "모델 밖이라 칠하지 않았습니다"); return; }
  if (d.지우개) 지우기(담); else 칠하기(담);
}
function 카메라값() {
  const b = window.보기3d.상태;
  return {중심: b.중심.toArray().map((v) => +v.toFixed(5)), 회전: b.회전.toArray().map((v) => +v.toFixed(5)), 거리: +b.거리.toFixed(5)};
}
function 칠하기(담) {
  기록남기기();
  const 고른 = 칠.고른 && 칠.표시.find((x) => x.번호 === 칠.고른 && x.작업본해시 === 보이는해시());
  if (고른) {
    // 이어 칠하기: 목록에서 고른 번호에 더한다
    for (const [파츠, s] of 담) {
      const 있던 = new Set(고른.자리.면[파츠] || []);
      for (const f of s) 있던.add(f);
      고른.자리.면[파츠] = [...있던].sort((a, b) => a - b);
    }
    고른.자리.파츠 = Object.keys(고른.자리.면);
    UV넣기(고른.자리);
    고른.카메라 = 카메라값();
  } else {
    const 자리 = 담기를자리로(담);
    자리.파츠 = Object.keys(자리.면);
    UV넣기(자리);
    동작넣기(자리);
    칠.표시.push({번호: 동그라미(칠.다음번호++), 누가: "사용자", 종류: 칠.칠할종류 || 칠.처리목록.at(-1), 자리,
      반대쪽도: false, 메모: "", 작업본해시: 보이는해시(), 카메라: 카메라값()});
  }
  바뀜();
}
// 자리.UV(2-1: 파츠 → [[x1,y1],[x2,y2]] 화소 범위)와 자리.UV조각(이음매를 지나면 조각마다 범위). UV 그림 칸이 있는 단계만
function UV넣기(자리) {
  부위넣기(자리);
  const u = window.uv그림;
  const v = u && u.켜짐() ? u.UV범위(자리.면) : null;
  delete 자리.UV; delete 자리.UV조각;
  if (!v) return;
  if (Object.keys(v.UV).length) 자리.UV = v.UV;
  if (Object.keys(v.조각).length) 자리.UV조각 = v.조각;
}
// 자리.동작(2-1, W13): 9·10단계에서 멈춘 장면(또는 시간 막대에서 고른 구간)의 동작 이름과 장 번호
function 동작넣기(자리) {
  const d = window.리깅단계 && window.리깅단계.동작자리();
  if (d) 자리.동작 = d; else delete 자리.동작;
}
// 구간 리포트(1부 5-4b, W13): 자리를 칠하지 않고 시간 막대의 구간만 보낸다
function 구간넣기(동작) {
  if (!동작 || !칠.처리목록.length) return false;
  const 못함 = 칠못함이유();
  if (못함) { 상태글(못함); return false; }
  기록남기기();
  칠.표시.push({번호: 동그라미(칠.다음번호++), 누가: "사용자", 종류: 칠.칠할종류 || 칠.처리목록.at(-1), 자리: {파츠: [], 면: {}, 동작, 구간: true},
    반대쪽도: false, 메모: "", 작업본해시: 보이는해시(), 카메라: 카메라값()});
  바뀜();
  return true;
}
// 자리.부위(2-1): 칠한 면이 든 부위 이름(부위.js, W05). 부위 목록이 없거나 옛 것이면 넣지 않는다
function 부위넣기(자리) {
  const l = window.부위 && window.부위.부위이름들(자리.면);
  if (l && l.length) 자리.부위 = l; else delete 자리.부위;
}
function 지우기(담) {
  const h = 보이는해시();
  const 대상 = 칠.표시.filter((x) => x.작업본해시 === h && (!칠.고른 || x.번호 === 칠.고른));
  let 뺌 = 0;
  const 전 = 복사({표시: 칠.표시, 후보판단: 칠.후보판단, 다음번호: 칠.다음번호});
  for (const x of 대상) for (const [파츠, s] of 담) {
    const 면 = x.자리.면[파츠];
    if (!면) continue;
    const 남 = 면.filter((f) => !s.has(f));
    뺌 += 면.length - 남.length;
    if (남.length) x.자리.면[파츠] = 남; else delete x.자리.면[파츠];
    x.자리.파츠 = Object.keys(x.자리.면);
    UV넣기(x.자리);
  }
  if (!뺌) { 겹침다시(); 상태글("지울 칠한 면이 없습니다"); return; }
  칠.취소.push(전); 칠.취소 = 칠.취소.slice(-칠.취소한도); 칠.다시 = [];
  칠.표시 = 칠.표시.filter((x) => x.자리.파츠.length || x.자리.구간);   // 면이 0이 된 표시는 지운다(구간 리포트는 남김, W13)
  if (칠.고른 && !칠.표시.some((x) => x.번호 === 칠.고른)) 칠.고른 = null;
  바뀜();
}

// ---------------------------------------------------------------- 취소·다시(5-4: 칠하기·지우개·표시 지우기·종류·판단·메모·반대쪽도)
function 지금값() { return 복사({표시: 칠.표시, 후보판단: 칠.후보판단, 다음번호: 칠.다음번호}); }
function 기록남기기() {
  칠.취소.push(지금값());
  if (칠.취소.length > 칠.취소한도) 칠.취소 = 칠.취소.slice(-칠.취소한도);
  칠.다시 = [];
}
function 되돌림(앞으로) {
  const 꺼낼 = 앞으로 ? 칠.다시 : 칠.취소, 넣을 = 앞으로 ? 칠.취소 : 칠.다시;
  if (!꺼낼.length) { 상태글(앞으로 ? "다시 할 것이 없습니다" : "취소할 것이 없습니다(보낸 뒤에는 보내기 전까지 거슬러 취소하지 않습니다)"); return; }
  if (document.body.dataset.잠금 === "다른 탭") { 상태글("다른 탭에서 열려 있어 이 탭에서는 바꿀 수 없습니다"); return; }
  if (칠.묶음.some((x) => x.묶음상태 === "처리 중")) { 상태글("에이전트가 처리 중이라 바꿀 수 없습니다"); return; }
  넣을.push(지금값());
  const v = 꺼낼.pop();
  칠.표시 = v.표시; 칠.후보판단 = v.후보판단; 칠.다음번호 = v.다음번호;
  if (칠.고른 && !칠.표시.some((x) => x.번호 === 칠.고른)) 칠.고른 = null;
  바뀜();
}

// ---------------------------------------------------------------- 저장(작성중.json)
let 저장타이머 = null;
function 바뀜() {
  칠.미저장 = true;
  그리기();
  겹침다시();
  clearTimeout(저장타이머);
  저장타이머 = setTimeout(저장하기, 상수.저장늦춤);
}
function 저장몸() {
  const 표시 = 칠.표시.map((x) => { const y = {...x}; return y; });
  return {이름: 칠.이름, 단계: 칠.단계, 탭: window.탭id || "", 표시, 후보판단: 칠.후보판단, 다음번호: 칠.다음번호, 묶음번호: 칠.묶음번호,
    기록: {취소: 칠.취소, 다시: 칠.다시}};
}
async function 저장하기() {
  clearTimeout(저장타이머);
  if (!칠.미저장 || !칠.이름 || 칠.저장중) return;
  if (document.body.dataset.잠금 === "다른 탭") { 칠.저장실패 = "다른 탭에서 열려 있어 저장하지 않았습니다"; 그리기(); return; }
  칠.저장중 = true;
  const 몸 = 저장몸(), 열쇠 = `${칠.이름}|${칠.단계}`;
  칠.미저장 = false;
  try {
    const r = await fetch("/api/작성중", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(몸)});
    const v = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(v.오류 || r.status);
    if (열쇠 === `${칠.이름}|${칠.단계}`) { 칠.저장실패 = ""; 칠.저장글 = `자동 저장됨 ${String(v.만든시각 || "").slice(11, 19)}`; }
  } catch (e) {
    if (열쇠 === `${칠.이름}|${칠.단계}`) {
      칠.미저장 = true;   // 브라우저에 들고 있다가 다음 바뀜·다시 연결 때 또 저장한다(8절)
      칠.저장실패 = `자동 저장 실패: ${e instanceof TypeError ? "서버와 연결 끊김" : e.message} — 칠한 것은 이 창에 남아 있고, 다시 연결되면 저장합니다`;
      if (String(e.message).includes("그사이")) 다시읽기(true);
    }
  } finally {
    칠.저장중 = false;
    if (칠.미저장 && !칠.저장실패) 저장타이머 = setTimeout(저장하기, 상수.저장늦춤);
    그리기();
  }
}

// ---------------------------------------------------------------- 서버에서 읽기
async function 다시읽기(강제 = false) {
  if (!칠.이름 || !칠.처리목록.length) return;
  if (칠.미저장 && !강제) { 저장하기(); return; }
  const 열쇠 = `${칠.이름}|${칠.단계}`;
  칠.읽는중 = true;
  try {
    const r = await fetch(`/api/표시?이름=${encodeURIComponent(칠.이름)}&단계=${칠.단계}`, {cache: "no-store"});
    const v = await r.json();
    if (!r.ok) throw new Error(v.오류 || r.status);
    if (열쇠 !== `${칠.이름}|${칠.단계}`) return;
    칠.작업본해시 = v.작업본해시 || "";
    칠.묶음 = v.묶음 || [];
    칠.후보 = v.후보;
    const 작성 = v.작성중 || {};
    if (!칠.미저장 || 강제) {
      칠.표시 = Array.isArray(작성.표시) ? 작성.표시 : [];
      칠.후보판단 = Array.isArray(작성.후보판단) ? 작성.후보판단 : [];
      칠.묶음번호 = Number.isInteger(작성.묶음번호) ? 작성.묶음번호 : 0;
      const 쓴번호 = [...칠.표시, ...칠.묶음.flatMap((b) => b.표시)].map((x) => 번호값(x && x.번호));
      칠.다음번호 = Math.max(Number.isInteger(작성.다음번호) ? 작성.다음번호 : 1, 1 + Math.max(0, ...쓴번호));
      칠.취소 = (v.기록 && v.기록.취소) || [];
      칠.다시 = (v.기록 && v.기록.다시) || [];
      칠.미저장 = false;
    }
    if (칠.고른 && !칠.표시.some((x) => x.번호 === 칠.고른)) 칠.고른 = null;
    칠.읽음 = true;
    칠.저장실패 = (v.오류 || []).join(" · ");
  } catch (e) {
    if (열쇠 === `${칠.이름}|${칠.단계}`) 칠.저장실패 = `표시를 읽지 못함: ${e instanceof TypeError ? "서버와 연결 끊김" : e.message}`;
  } finally {
    칠.읽는중 = false;
  }
  그리기();
  겹침다시();
}

// ---------------------------------------------------------------- 후보
const 후보열쇠 = (x) => `후보:${x.번호}`;
function 보낸판단() {
  const s = new Set();
  for (const b of 칠.묶음) for (const p of b.후보판단 || []) s.add(`${p.후보파일}|${p.번호}`);
  return s;
}
function 보이는후보() {
  if (!칠.후보) return [];
  const 보낸 = 보낸판단();
  return (칠.후보.후보 || []).filter((x) => x && x.번호 && !보낸.has(`${칠.후보.파일}|${x.번호}`));
}
function 판단(번호) {
  const p = 칠.후보 && 칠.후보판단.find((x) => x.후보파일 === 칠.후보.파일 && x.번호 === 번호);
  return p ? p.판단 : "";
}

// ---------------------------------------------------------------- 그리기(표시 목록·결정 칸의 보내기)
function 자리설명(x) {
  const 면 = (x.자리 && x.자리.면) || {};
  const 수 = Object.values(면).reduce((a, l) => a + l.length, 0);
  const 부위 = (x.자리 && x.자리.부위) || [];   // W05: "상체 › 왼쪽 아래팔" — 셋 넘으면 앞의 둘 + "외 N곳"
  const 파츠 = 부위.length ? (부위.length > 3 ? `${부위.slice(0, 2).join(" · ")} 외 ${부위.length - 2}곳` : 부위.join(" · ")) : Object.keys(면).join("·");
  const d = x.자리 && x.자리.동작, 동작이름 = d ? (window.리깅단계 ? window.리깅단계.짧은이름(d.이름) : d.이름) : "";   // W13
  const 동작 = d ? ` · ${동작이름} ${d.시작장 === d.끝장 ? `${d.시작장}장` : `${d.시작장}~${d.끝장}장`}` : "";
  const 조각수 = Object.values((x.자리 && x.자리.UV조각) || {}).reduce((a, l) => a + l.length, 0);
  const 이음매 = 조각수 > 1 ? ` · UV 조각 ${조각수}개(이음매를 지남)` : "";
  return `${파츠 || (x.자리 && x.자리.구간 ? "구간 리포트" : "자리 없음")}${수 ? `, 면 ${수}개` : ""}${이음매}${동작}`;
}
function 반대쪽잠금(x) {
  const 이름들 = [...((x.자리 && x.자리.부위) || []), ...((x.자리 && x.자리.파츠) || [])];
  const 걸림 = 비대칭예외.find((k) => 이름들.some((n) => String(n).includes(k)));
  return 걸림 ? `비대칭 예외(${걸림})라 반대쪽을 뒤집어 고치지 않습니다(SSOT 41 "비대칭 예외")` : "";
}
// 7단계(2부 19절 예외): "반대쪽도"는 기본 꺼짐. 잠기지 않은 사용자 표시에는 그 줄에 "반대쪽도 고칠까요?"를 띄운다.
// 대칭 부위인지는 페이지가 모르므로 잠기지 않은 표시 모두에 묻고, 대칭이 아닌 곳이면 에이전트가 그 쪽만 고친다.
function 반대쪽물음(x) {
  return 칠.단계 === 7 && !x.반대쪽도 && !반대쪽잠금(x);
}
// 눈(반사점 말고): 뒤집을 때 반사점은 원래 자리에 둔다(사용자, 2026-11-24)
function 눈안내(x) {
  const 이름들 = [...((x.자리 && x.자리.부위) || []), ...((x.자리 && x.자리.파츠) || [])];
  return 칠.단계 === 7 && 이름들.some((n) => /눈(?!썹)/.test(String(n))) ? "눈은 반사점을 뺀 나머지만 뒤집어 쓰고, 반사점은 원래 자리에 둡니다" : "";
}
function seg(값들, 고른값, 속성) {
  return 값들.map((v) => `<button type="button" class="${v === 고른값 ? "on" : ""}" ${속성}="${글(v)}" aria-pressed="${v === 고른값}">${글(v)}</button>`).join("");
}
function 그리기() {
  const 칠됨 = 칠.처리목록.length > 0;
  뿌리.hidden = !칠됨 || !칠.이름;
  도구그리기();
  보내기그리기();
  if (뿌리.hidden) return;
  const 지금h = 칠.작업본해시;
  if (!칠.칠할종류 || !칠.처리목록.includes(칠.칠할종류)) 칠.칠할종류 = 칠.처리목록.at(-1);
  안("p3kind").innerHTML = seg(칠.처리목록, 칠.칠할종류, "data-kind");
  안("p3kind").title = `새로 칠할 표시의 처리. 고르지 않으면 "${칠.처리목록.at(-1)}"`;
  안("p3size").textContent = `붓 ${Math.round(칠.붓)}`;
  안("p3undo").disabled = !칠.취소.length;
  안("p3redo").disabled = !칠.다시.length;
  안("p3undo").title = 칠.취소.length ? `취소 (Ctrl+Z) — ${칠.취소.length}번 남음` : "취소할 것이 없습니다";
  안("p3redo").title = 칠.다시.length ? `다시 (Ctrl+Y) — ${칠.다시.length}번 남음` : "다시 할 것이 없습니다";

  const 줄들 = [];
  for (const x of 보이는후보()) {
    const 옛 = 칠.후보.작업본해시 !== 지금h;
    const 설명 = `${x.메모 || x.종류 || "후보"} — ${자리설명(x)}`;
    줄들.push(`<div class="mrow cand${옛 ? " old" : ""}" data-cand="${글(x.번호)}" title="${글(`${x.번호} · ${칠.후보.만든이 || x.누가 || ""} · ${설명}${옛 ? " · 옛 버전(작업본이 바뀜)" : ""}`)}">` +
      `<span class="mk ac">${글(x.번호)}</span><span class="who">${글(x.누가 || 칠.후보.만든이 || "후보")}</span><span class="desc">${글(설명)}</span>` +
      `<span class="seg">${seg(판단들, 판단(x.번호), "data-judge")}</span></div>`);
  }
  for (const x of (칠.후보 && 칠.후보.고친것) || []) {
    const 설명 = `${x.메모 || "묻지 않고 고침"} — ${자리설명(x)}`;
    줄들.push(`<div class="mrow fixed" data-fixed="${글(x.번호)}" title="${글(`${x.번호} · 고친 것 · ${설명} · 누르면 전후 보기`)}">` +
      `<span class="mk ok">${글(x.번호 || "✓")}</span><span class="who">고친 것</span><span class="desc">${글(설명)}</span><span class="mtag">전후 보기</span></div>`);
  }
  for (const x of 칠.표시) {
    const 옛 = x.작업본해시 !== 지금h;
    const 물음 = 반대쪽물음(x);
    const 설명 = `${자리설명(x)}${x.메모 ? ` · ${x.메모}` : ""}${x.반대쪽도 ? " · 반대쪽도" : 물음 ? " · 반대쪽도 고칠까요?" : ""}`;
    const 메모없음 = 칠.메모필수.includes(x.종류) && !String(x.메모 || "").trim();
    줄들.push(`<div class="mrow user${옛 ? " old" : ""}${x.번호 === 칠.고른 ? " on" : ""}" data-mark="${글(x.번호)}" title="${글(`${x.번호} · 사용자 · ${x.종류} · ${설명}${옛 ? " · 옛 버전: 칠할 때의 작업본과 지금 작업본이 다릅니다. 그대로 보내면 에이전트가 자리를 다시 찾습니다" : ""}`)}">` +
      `<span class="mk ng">${글(x.번호)}</span><span class="who">사용자</span><span class="desc">${글(설명)}</span>` +
      `<span class="mtag${메모없음 ? " ng" : ""}">${옛 ? "옛 버전 · " : ""}${글(x.종류)}${메모없음 ? " · 메모 필요" : ""}</span></div>`);
  }
  안("p3list").innerHTML = 줄들.length ? 줄들.join("") :
    `<div class="mempty">아직 표시가 없습니다. 도구 줄의 "붓"(B)을 들고 모델 위를 왼쪽 끌기로 칠하면 표시가 생깁니다.</div>`;

  // 고른 표시의 자세히(처리 종류·메모·반대쪽도·지우기)
  const 고른 = 칠.표시.find((x) => x.번호 === 칠.고른);
  const d = 안("p3detail");
  d.hidden = !고른;
  if (고른) {
    const 잠금 = 반대쪽잠금(고른);
    const 옛 = 고른.작업본해시 !== 지금h;
    const 메모필요 = 칠.메모필수.includes(고른.종류);
    if (!d.contains(document.activeElement)) {
      d.innerHTML = `<div class="ttl">${글(고른.번호)} 자세히${옛 ? " — 옛 버전(새 모델에는 보이지 않음. 다시 칠하거나 그대로 보낼 수 있음)" : " — 붓으로 칠하면 이 번호에 이어 칠해집니다"}</div>` +
        `<div class="drow"><span class="mlab">처리</span><div class="seg">${seg(칠.처리목록, 고른.종류, "data-dkind")}</div></div>` +
        `<label class="dmemo"><span class="mlab">메모${메모필요 ? " (기타는 꼭 적기)" : " (선택)"}</span><textarea id="p3memo" rows="2" placeholder="${메모필요 ? "무엇이 이상한지 적어 주세요" : "적지 않아도 됩니다"}">${글(고른.메모 || "")}</textarea></label>` +
        `<div class="drow"><label class="pchk" title="${글(잠금 || "켜면 에이전트가 좌우 대칭 자리도 같이 고칩니다(한쪽만 고치고 뒤집기)")}"><input type="checkbox" id="p3mirror"${고른.반대쪽도 ? " checked" : ""}${잠금 ? " disabled" : ""}><span class="pn">반대쪽도</span></label>` +
        `<span class="hint${반대쪽물음(고른) ? " wa" : ""}">${글(잠금 || [반대쪽물음(고른) ? "반대쪽도 고칠까요? 대칭 부위면 켜 주세요(한쪽을 고쳐 뒤집어 씀)" : "", 눈안내(고른), 고른.자리.부위 ? "" : "부위 목록이 없거나 옛 것이라 비대칭 예외인지는 에이전트가 다시 확인합니다"].filter(Boolean).join(" · "))}</span><span class="sp"></span>` +
        `<button type="button" class="tb" id="p3del" title="이 표시를 지웁니다(Ctrl+Z로 되살림)">표시 지우기</button>` +
        `<button type="button" class="tb" id="p3unsel" title="고르기를 풀면 붓이 새 번호로 칠합니다">고르기 풀기</button></div>`;
    }
  }

  // 저장 상태
  const s = 안("p3save");
  s.textContent = 칠.저장실패 || 칠.막힘글 || (칠.미저장 ? "저장 대기…" : 칠.저장글) || "";
  s.className = `mst${칠.저장실패 ? " ng" : ""}`;
  s.title = s.textContent;
  오류띠알림(칠.저장실패);

  // 보낸 묶음(처리됨이면 항목마다 고침/안 고침 + 이유)
  const 묶음 = 칠.묶음.slice().reverse();
  const 보낸 = 안("p3sent");
  보낸.hidden = !묶음.length;
  if (묶음.length) {
    const 마지막 = 묶음[0];
    안("p3sentsum").textContent = `보낸 묶음 ${묶음.length}개 · 가장 최근: ${마지막.묶음상태 || "알 수 없음"}`;
    안("p3sentbody").innerHTML = 묶음.map((b) => {
      const 결과 = new Map(((b.처리 && b.처리.결과) || []).map((r) => [r.번호, r]));
      const 항목 = [...b.표시.map((x) => [x.번호, `${x.종류} · ${자리설명(x)}`]), ...b.후보판단.map((p) => [p.번호, `후보 판단: ${p.판단}`])];
      return `<div class="sb"><div class="sbt">${글(b.파일)} — <span class="${{"처리됨": "ok", "실패": "ng", "처리 중": "wa"}[b.묶음상태] || "ac"}">${글(b.묶음상태 || "알 수 없음")}</span>${b.합친묶음.length ? ` · 합침: ${글(b.합친묶음.join(", "))}` : ""}</div>` +
        항목.map(([n, 설명]) => {
          const r = 결과.get(n);
          return `<div class="sbi" title="${글(`${n} ${설명}${r ? ` — ${r.처리}${r.이유 ? `: ${r.이유}` : ""}` : ""}`)}">${글(n)} ${글(설명)}${r ? ` — <span class="${r.처리 === "고침" ? "ok" : "wa"}">${글(r.처리)}</span>${r.이유 ? `: ${글(r.이유)}` : ""}` : ""}</div>`;
        }).join("") + `</div>`;
    }).join("");
  }
}
function 도구그리기() {
  const 안쪽 = 보();
  if (!안쪽) return;
  const 이유 = 칠못함이유();
  for (const b of 안쪽.뿌리.querySelectorAll("[data-칠]")) {
    const 도구 = b.dataset.칠;
    b.classList.toggle("on", 칠.도구 === 도구);
    b.setAttribute("aria-pressed", String(칠.도구 === 도구));
    const 기본 = b.title.split(" — ")[0];
    const 막음 = 도구 !== "보기" && 이유;
    b.disabled = Boolean(막음);
    b.title = 막음 ? `${기본} — ${이유}` : 기본;
  }
  const v = 안쪽.뿌리.querySelector(".view");
  if (v) v.classList.toggle("painting", 칠.도구 !== "보기" && !이유);
}
function 보낼수() { return 칠.표시.length + 보이는후보().length; }
function 보내기그리기() {
  if (!칠.이름 && window.그림단계 && window.그림단계.붙음()) return window.그림단계.보내기그리기();   // W09: 1단계는 그림단계.js가 보내기를 맡음
  const n = 칠.이름 && 칠.처리목록.length ? 보낼수() : 0;
  const 처리중 = 칠.묶음.some((x) => x.묶음상태 === "처리 중");
  const 보냄 = 칠.묶음.some((x) => x.묶음상태 === "보냄");
  const 막음 = !n ? "보낼 표시가 없습니다" : document.body.dataset.잠금 === "다른 탭" ? "다른 탭에서 열려 있습니다" : 보내는중 ? "보내는 중…" : "";
  for (const b of [$("send"), $("sendtop")]) {
    if (!b) continue;
    b.textContent = 보내는중 ? "보내는 중…" : `표시 ${n}개 보내기`;
    b.disabled = Boolean(막음);
    b.title = 막음 || `사용자 표시 ${칠.표시.length}개와 후보 판단 ${보이는후보().length}개를 보내기 파일로 씁니다`;
  }
  const h = document.querySelector(".sendwrap .hint");
  if (h) {
    const 글들 = !칠.처리목록.length || !칠.이름 ? "이 단계에서는 칠하지 않습니다. 보낼 표시가 생기는 단계에서 누를 수 있습니다."
      : 칠.보낸글.startsWith("보내지 못함") ? 칠.보낸글
      : 처리중 ? "처리 중 — 에이전트가 앞 묶음을 고치는 중이라 칠하기를 막았습니다."
      : 보냄 ? `보냄 — Claude 앱에서 '보냈어'라고 알려 주세요. (${칠.묶음.filter((x) => x.묶음상태 === "보냄").map((x) => x.파일).join(", ")})`
      : n ? "보내면 Claude 앱에서 '보냈어'라고 알려 주세요." : "칠하거나 후보를 판단하면 누를 수 있습니다.";
    h.textContent = 글들;
    h.classList.toggle("ng", 칠.보낸글.startsWith("보내지 못함"));
  }
}
function 오류띠알림(메시지) {
  const b = $("b-save");
  if (!b) return;
  b.textContent = 메시지 || "";
  b.hidden = !메시지;
}
let 상태글타이머 = null;
function 상태글(t) {
  칠.막힘글 = t;
  그리기();
  clearTimeout(상태글타이머);
  상태글타이머 = setTimeout(() => { 칠.막힘글 = ""; 그리기(); }, 4000);
}

// ---------------------------------------------------------------- 줄 누르기 → 카메라가 그 자리로, 깜박임
function 면상자(자리) {
  const b = new THREE.Box3(), v = new THREE.Vector3();
  if (!면지도 || !자리) return b;
  for (const [파츠, 면] of Object.entries(자리.면 || {})) for (const 칸 of 면지도.get(파츠) || []) {
    const g = 칸.메시.geometry, 위치 = g.attributes.position, 색인 = g.index;
    칸.메시.updateWorldMatrix(true, false);
    for (const f of 면) for (const t of 칸.면.get(f) || []) for (let k = 0; k < 3; k++) {
      v.fromBufferAttribute(위치, 색인 ? 색인.array[t * 3 + k] : t * 3 + k).applyMatrix4(칸.메시.matrixWorld);
      b.expandByPoint(v);
    }
  }
  return b;
}
function 그자리로(x, 열쇠) {
  const 안쪽 = 보(), b = window.보기3d && window.보기3d.상태;
  if (!안쪽 || !b || !b.지금) return;
  if (x.자리 && x.자리.동작 && window.리깅단계) window.리깅단계.장으로(x.자리.동작);   // W13: 그 동작의 그 장으로
  const 지금모델 = (x.작업본해시 || (칠.후보 && 칠.후보.작업본해시)) === 보이는해시();
  const 상 = 지금모델 ? 면상자(x.자리) : new THREE.Box3();
  if (!상.isEmpty()) {
    const 크기 = 상.getSize(new THREE.Vector3()).length();
    const 회전 = x.카메라 ? new THREE.Quaternion().fromArray(x.카메라.회전) : undefined;
    안쪽.옮기기({중심: 상.getCenter(new THREE.Vector3()), 회전, 거리: 안쪽.거리제한(Math.max(크기 * 상수.다가감, b.크기 * 상수.최소다가감))});
  } else if (x.카메라) {
    // 옛 버전: 칠할 때의 카메라 자리로(면은 새 모델에 얹지 않음)
    안쪽.옮기기({중심: new THREE.Vector3().fromArray(x.카메라.중심), 회전: new THREE.Quaternion().fromArray(x.카메라.회전), 거리: x.카메라.거리});
  }
  if (지금모델 && 열쇠) 깜박이기(열쇠);
}
function 깜박이기(열쇠) {
  if (깜박) clearTimeout(깜박.타이머);
  깜박 = {열쇠, 남은: 상수.깜박횟수, 켬: true};
  const 한번 = () => {
    if (!깜박) return;
    깜박.켬 = !깜박.켬;
    if (--깜박.남은 <= 0) { 깜박 = null; 겹침다시(); return; }
    겹침다시();
    깜박.타이머 = setTimeout(한번, 상수.깜박간격);
  };
  겹침다시();
  깜박.타이머 = setTimeout(한번, 상수.깜박간격);
}

// ---------------------------------------------------------------- 보내기(4-4)
let 보내는중 = false;
const 묻기 = {상자: null};
function 물어보기(제목, 본문, 단추들) {
  // 단추들: [[글, 색(b-ok/b-fix/b-re), 값]] — 누른 단추의 값을 돌려준다(Esc는 null)
  return new Promise((풀기) => {
    const o = $("ask2");
    $("ask2ttl").textContent = 제목;
    $("ask2body").innerHTML = 본문;
    const 줄 = $("ask2btns");
    줄.className = `btns${단추들.length}`;
    줄.innerHTML = 단추들.map(([t, c], i) => `<button class="btn ${c}" type="button" data-i="${i}">${글(t)}</button>`).join("");
    o.hidden = false;
    const 끝 = (값) => { o.hidden = true; o.removeEventListener("keydown", 키); 줄.onclick = null; 풀기(값); };
    const 키 = (ev) => { if (ev.key === "Escape") 끝(null); };
    o.addEventListener("keydown", 키);
    줄.onclick = (ev) => { const b = ev.target.closest("[data-i]"); if (b) 끝(단추들[Number(b.dataset.i)][2]); };
    줄.querySelector("button").focus();
  });
}
async function 보내기() {
  if (보내는중 || (!보낼수() && !(칠.단계 === 3 && window.메시단계 && window.메시단계.멈춤답()))) return;   // W11: 멈춤 1은 후보가 없어도 대칭 답만 보냄
  await 저장하기();
  // 옛 버전 표시(칠할 때의 작업본이 지금과 다름)는 보내지 않는다. 면 번호가 지금 모델의 면을 가리킨다는 보장이 없다.
  const 옛표시 = 칠.표시.filter((x) => 칠.작업본해시 && x.작업본해시 !== 칠.작업본해시);
  const 보낼표시 = 칠.표시.filter((x) => !옛표시.includes(x));
  if (옛표시.length) {
    const 남는것 = 보낼표시.length || 보이는후보().length || (칠.단계 === 3 && window.메시단계 && window.메시단계.멈춤답());
    if (!남는것) {
      칠.보낸글 = `보내지 못함: 옛 버전 표시만 있습니다(${옛표시.map((x) => x.번호).join(" ")}). 지금 모델에 다시 칠해 주세요.`;
      그리기();
      return;
    }
    const 답 = await 물어보기("옛 버전 표시는 빼고 보냅니다",
      `작업본이 바뀌기 전에 칠한 표시 ${옛표시.length}개는 보내지 않고 목록에서 정리합니다.<span class="hint">${글(옛표시.map((x) => x.번호).join(" "))}</span>`,
      [["빼고 보내기", "b-ok", true], ["취소", "b-re", false]]);
    if (!답) return;
  }
  const 빈메모 = 보낼표시.filter((x) => 칠.메모필수.includes(x.종류) && !String(x.메모 || "").trim());
  if (빈메모.length) {
    칠.고른 = 빈메모[0].번호;
    칠.보낸글 = `보내지 못함: "기타"는 메모가 있어야 합니다(${빈메모.map((x) => x.번호).join(" ")}). 표시 목록에서 메모를 적어 주세요.`;
    그리기();
    return;
  }
  const 안판단 = 보이는후보().filter((x) => !판단(x.번호));
  if (안판단.length) {
    const 답 = await 물어보기("판단 안 한 후보가 있습니다", `판단 안 한 후보 ${안판단.length}개 — '모름'으로 보낼까요?<span class="hint">${글(안판단.map((x) => x.번호).join(" "))}</span>`,
      [["모름으로 보내기", "b-ok", true], ["취소", "b-re", false]]);
    if (!답) return;
  }
  const 수 = 보낼표시.length + 보이는후보().length;
  if (수 > 상수.많은표시) {
    const 답 = await 물어보기("표시가 많습니다", `한 묶음에 ${수}개입니다(${상수.많은표시}개 넘음). 그래도 보낼까요?`, [["그래도 보내기", "b-ok", true], ["취소", "b-re", false]]);
    if (!답) return;
  }
  let 합치기;
  const 남은 = 칠.묶음.filter((x) => x.묶음상태 === "보냄");
  if (남은.length) {
    합치기 = await 물어보기("앞 묶음을 아직 처리하지 않았습니다", `앞 묶음을 아직 처리하지 않았습니다. 합쳐 보낼까요, 따로 보낼까요?<span class="hint">${글(남은.map((x) => x.파일).join(", "))}</span>`,
      [["합쳐 보내기", "b-ok", true], ["따로 보내기", "b-fix", false], ["취소", "b-re", null]]);
    if (합치기 === null) return;
  }
  const 판단목록 = [...칠.후보판단.filter((p) => 칠.후보 && p.후보파일 === 칠.후보.파일 && 보이는후보().some((x) => x.번호 === p.번호))];
  for (const x of 안판단) 판단목록.push({후보파일: 칠.후보.파일, 번호: x.번호, 판단: "모름"});
  보내는중 = true; 그리기();
  try {
    const r = await fetch("/api/보내기", {method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({이름: 칠.이름, 단계: 칠.단계, 탭: window.탭id || "", 표시: 보낼표시, 후보판단: 판단목록, 다음번호: 칠.다음번호, 묶음번호: 칠.묶음번호, 합치기,
        멈춤답: 칠.단계 === 3 && window.메시단계 ? window.메시단계.멈춤답() : undefined})});   // W11: 3단계 멈춤 답(대칭 기준)
    const v = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(v.오류 || r.status);
    칠.보낸글 = "";
    칠.표시 = []; 칠.후보판단 = []; 칠.취소 = []; 칠.다시 = []; 칠.고른 = null; 칠.미저장 = false;   // 취소 기록은 보내기에서 끊긴다
    await 다시읽기(true);
  } catch (e) {
    칠.보낸글 = `보내지 못함: ${e instanceof TypeError ? "서버와 연결 끊김" : e.message}`;
    if (String(e.message).includes("그사이")) await 다시읽기(true);
  } finally {
    보내는중 = false;
    그리기();
  }
}

// ---------------------------------------------------------------- 이벤트
안("p3kind").addEventListener("click", (ev) => {
  const b = ev.target.closest("[data-kind]");
  if (!b) return;
  칠.칠할종류 = b.dataset.kind;
  그리기();
});
안("p3undo").addEventListener("click", () => 되돌림(false));
안("p3redo").addEventListener("click", () => 되돌림(true));
안("p3list").addEventListener("click", (ev) => {
  const j = ev.target.closest("[data-judge]");
  const 줄 = ev.target.closest(".mrow");
  if (!줄) return;
  if (j) {
    if (document.body.dataset.잠금 === "다른 탭") { 상태글("다른 탭에서 열려 있어 바꿀 수 없습니다"); return; }
    const 번호 = 줄.dataset.cand, 값 = j.dataset.judge;
    기록남기기();
    칠.후보판단 = 칠.후보판단.filter((p) => !(p.후보파일 === 칠.후보.파일 && p.번호 === 번호));
    if (판단(번호) !== 값) 칠.후보판단.push({후보파일: 칠.후보.파일, 번호, 판단: 값});
    바뀜();
    return;
  }
  if (줄.dataset.mark) {
    const x = 칠.표시.find((y) => y.번호 === 줄.dataset.mark);
    칠.고른 = 칠.고른 === x.번호 ? null : x.번호;
    그리기(); 겹침다시();
    if (칠.고른) 그자리로(x, x.번호);
  } else if (줄.dataset.cand) {
    const x = 보이는후보().find((y) => y.번호 === 줄.dataset.cand);
    if (x) 그자리로(x, 후보열쇠(x));
  } else if (줄.dataset.fixed) {
    const x = ((칠.후보 && 칠.후보.고친것) || []).find((y) => y.번호 === 줄.dataset.fixed);
    if (x) 그자리로(x, null);
    const 나란히 = document.getElementById("v3side");
    if (나란히 && !나란히.disabled && !window.보기3d.상태.나란히) 나란히.click();   // 전후 보기(W02의 나란히)
  }
});
안("p3detail").addEventListener("click", (ev) => {
  const 고른 = 칠.표시.find((x) => x.번호 === 칠.고른);
  if (!고른) return;
  const k = ev.target.closest("[data-dkind]");
  if (k && k.dataset.dkind !== 고른.종류) { 기록남기기(); 고른.종류 = k.dataset.dkind; 안("p3detail").innerHTML = ""; 바뀜(); return; }
  if (ev.target.closest("#p3del")) { 기록남기기(); 칠.표시 = 칠.표시.filter((x) => x !== 고른); 칠.고른 = null; 바뀜(); return; }
  if (ev.target.closest("#p3unsel")) { 칠.고른 = null; 그리기(); 겹침다시(); }
});
let 메모기록함 = false;
안("p3detail").addEventListener("focusin", (ev) => { if (ev.target.id === "p3memo") 메모기록함 = false; });
안("p3detail").addEventListener("input", (ev) => {
  if (ev.target.id !== "p3memo") return;
  const 고른 = 칠.표시.find((x) => x.번호 === 칠.고른);
  if (!고른) return;
  if (!메모기록함) { 기록남기기(); 메모기록함 = true; }   // 한 번 고쳐 쓰는 동안은 취소 한 번
  고른.메모 = ev.target.value;
  칠.보낸글 = "";
  바뀜();
});
안("p3detail").addEventListener("focusout", (ev) => { if (ev.target.id === "p3memo") { 메모기록함 = false; setTimeout(그리기, 0); } });
안("p3detail").addEventListener("change", (ev) => {
  if (ev.target.id !== "p3mirror") return;
  const 고른 = 칠.표시.find((x) => x.번호 === 칠.고른);
  if (!고른 || 반대쪽잠금(고른)) return;
  기록남기기();
  고른.반대쪽도 = ev.target.checked;
  바뀜();
});
for (const b of [$("send"), $("sendtop")]) if (b) b.addEventListener("click", 보내기);

function 도구고르기(도구) {
  if (도구 !== "보기" && 칠못함이유()) { 상태글(칠못함이유()); return; }
  칠.도구 = 도구;
  원.hidden = true;
  그리기();
}
function 캔버스잇기() {
  const 안쪽 = 보();
  if (!안쪽 || 캔버스잇기.됨) return;
  캔버스잇기.됨 = true;
  for (const b of 안쪽.뿌리.querySelectorAll("[data-칠]")) b.addEventListener("click", () => 도구고르기(b.dataset.칠));
  안쪽.뿌리.querySelector(".view").appendChild(원);
  const c = 안쪽.캔버스;
  // 붓을 든 동안 왼쪽 끌기는 칠하기. 보기3d.js보다 먼저 받아(capture) 옮기기를 막는다. Shift+왼쪽·가운데·오른쪽은 그대로 보기3d.js로
  c.addEventListener("pointerdown", (ev) => {
    if (칠.도구 === "보기" || ev.button !== 0 || ev.shiftKey || ev.altKey) return;
    ev.stopImmediatePropagation();
    ev.preventDefault();
    const 이유 = 칠못함이유();
    if (이유) { 상태글(이유); return; }
    붓시작(ev);
  }, true);
  c.addEventListener("pointermove", (ev) => {
    원보이기(ev);
    if (붓질 && ev.pointerId === 붓질.id) { ev.stopImmediatePropagation(); 붓움직임(ev); }
  }, true);
  const 끝 = (ev) => { if (붓질 && ev.pointerId === 붓질.id) { ev.stopImmediatePropagation(); 붓끝(); } };
  c.addEventListener("pointerup", 끝, true);
  c.addEventListener("pointercancel", 끝, true);
  c.addEventListener("pointerleave", () => { 원.hidden = true; });
  c.addEventListener("dblclick", (ev) => { if (칠.도구 !== "보기") ev.stopImmediatePropagation(); }, true);   // 붓을 든 동안 두 번 누르기는 칠하기(회전 중심 아님)
  c.addEventListener("wheel", (ev) => {
    if (!ev.shiftKey || 칠.도구 === "보기") return;
    ev.stopImmediatePropagation();
    ev.preventDefault();
    const d = ev.deltaY || ev.deltaX;   // Shift를 누르면 가로 휠로 오는 브라우저가 있다
    칠.붓 = Math.min(상수.붓최대, Math.max(상수.붓최소, 칠.붓 * Math.exp(-d * 상수.붓휠)));
    원보이기(ev);
    그리기();
  }, {capture: true, passive: false});
}
document.addEventListener("keydown", (ev) => {
  if (!뿌리.isConnected || 뿌리.hidden) return;
  const t = ev.target;
  if (t && t.closest && t.closest("input, select, textarea, [contenteditable]")) return;
  if (document.querySelector(".overlay:not([hidden])")) return;
  const 키 = ev.key.length === 1 ? ev.key.toLowerCase() : ev.key;
  if ((ev.ctrlKey || ev.metaKey) && !ev.altKey) {
    if (키 === "z" && !ev.shiftKey) { ev.preventDefault(); 되돌림(false); }
    else if (키 === "y" || (키 === "z" && ev.shiftKey)) { ev.preventDefault(); 되돌림(true); }
    return;
  }
  if (ev.altKey || ev.repeat) return;
  const 도구 = {b: "붓", e: "지우개", v: "보기"}[키];
  if (도구) { ev.preventDefault(); 도구고르기(도구); }
});
window.addEventListener("보기3d모델", () => { 면지도만들기(); 겹침다시(); 그리기(); });
window.addEventListener("pagehide", () => {
  if (!칠.미저장 || !칠.이름) return;
  try { navigator.sendBeacon("/api/작성중", new Blob([JSON.stringify(저장몸())], {type: "application/json"})); } catch (e) {}
});

// ---------------------------------------------------------------- 바깥(앱.js)에 내놓는 것
async function 붙이기(자리, 이름, 단계, 처리목록, 메모필수, 취소한도) {
  캔버스잇기();
  const 새 = 이름 !== 칠.이름 || 단계 !== 칠.단계;
  if (새) {
    if (칠.미저장) await 저장하기();
    Object.assign(칠, {이름, 단계, 처리목록: 처리목록 || [], 메모필수: 메모필수 || ["기타"], 취소한도: 취소한도 || 50,
      표시: [], 후보판단: [], 취소: [], 다시: [], 묶음: [], 후보: null, 고른: null, 읽음: false, 저장실패: "", 저장글: "", 보낸글: "", 막힘글: "", 칠할종류: null, 미저장: false});
    if (!칠.처리목록.length) 칠.도구 = "보기";
  }
  if (자리) 자리.replaceWith(뿌리);
  그리기();
  if (새) { await 다시읽기(true); 겹침다시(); }
}
function 떼기() {
  if (칠.미저장) 저장하기();
  if (뿌리.isConnected) 뿌리.remove();
  Object.assign(칠, {이름: null, 단계: 0, 처리목록: [], 표시: [], 후보판단: [], 묶음: [], 후보: null, 고른: null, 도구: "보기", 보낸글: ""});
  겹침다시();
  그리기();
}
// 맥박(앱.js)이 알려 주는 것: 서버의 표시 파일이 바뀜, 작업본해시가 바뀜, 다시 연결됨, 잠금이 바뀜
let 마지막잠금 = null;
function 바깥바뀜(표시값) {
  if (표시값 !== undefined && 표시값 !== 칠.바깥표시) {
    const 처음 = 칠.바깥표시 === null;
    칠.바깥표시 = 표시값;
    if (!처음) 다시읽기();
  }
  if (칠.미저장 && !칠.저장중) 저장하기();
  if (document.body.dataset.잠금 !== 마지막잠금) { 마지막잠금 = document.body.dataset.잠금; 그리기(); }   // 잠금이 바뀔 때만 다시 그린다
}
function 작업본바뀜(해시) {
  if (해시 === 칠.작업본해시) return;
  칠.작업본해시 = 해시 || "";
  그리기(); 겹침다시();
}
// UV 그림 칸(uv그림.js)이 쓰는 것: 담 = Map(파츠 → Set(면))
function 면칠하기(담, 지우개) {
  if (window.부위) 담 = window.부위.거르기(담);
  let 수 = 0;
  for (const s of 담.values()) 수 += s.size;
  if (!수) { 겹침다시(); 상태글(window.부위 && window.부위.상태글() ? "UV 조각 밖이거나 칠할 수 없는 부위라 칠하지 않았습니다" : "UV 조각 밖이라 칠하지 않았습니다"); return 0; }
  if (지우개) 지우기(담); else 칠하기(담);
  return 수;
}
function 미리보기(지우개, 담) { 겹침다시(담 ? {지우개, 자리: 담기를자리로(window.부위 ? window.부위.거르기(담) : 담)} : null); }
function 붓바꾸기(d) { 칠.붓 = Math.min(상수.붓최대, Math.max(상수.붓최소, 칠.붓 * Math.exp(-d * 상수.붓휠))); 그리기(); }
window.칠하기 = {붙이기, 떼기, 바깥바뀜, 작업본바뀜, 저장하기, 보내기, 상태: 칠,
  면칠하기, 미리보기, 붓바꾸기, 칠못함이유, 상태글, 구간넣기, 겹침모음: () => 마지막모음,
  // 시험용(검사에서 칠한 자리를 재현): 화면 좌표의 원 안 면들
  시험_면: (x, y, r) => { 고르기그리기(); const m = new Map(); 원안의면(x, y, r, m); return 담기를자리로(m); },
  시험_고르기: () => { const g = 고르기그리기(); let n = 0; if (g) for (let i = 3; i < g.화소.length; i += 4) if (g.화소[i]) n++; return {면지도: 면지도 ? 면지도.size : null, 가로: g && g.가로, 세로: g && g.세로, 칠해진화소: n}; }};
window.dispatchEvent(new Event("칠하기준비"));
