// 가마우지 제작 페이지 — 3D 보기(W02, 기능명세 1부 5-1·5-2절)
// 서버(127.0.0.1)의 GLB만 띄운다. three.js는 정적/lib/three/의 사본(index.html의 importmap).
// 크기·색 숫자는 여기 "그림 상수" 한 곳에만 둔다(디자인규격 6절). 색은 디자인 토큰에서 읽는다.
// 칠하기(W03)는 정적/칠하기.js, UV 그림(W04)은 정적/uv그림.js가 window.보기3d.내부와 "보기3d모델" 사건으로 붙는다. 하지 않는 것: 부위(W05).
import * as THREE from "three";
import {GLTFLoader} from "three/addons/loaders/GLTFLoader.js";

// ---------------------------------------------------------------- 그림 상수
const 상수 = {
  시야각: 35,            // 원근 보기의 세로 시야(도)
  회전감도: 0.006,       // 끌기 1화소당 회전(라디안)
  휠감도: 0.0015,        // 휠 1단위당 확대 비율(지수)
  다가감: 0.45,          // 두 번 누르면 거리에 곱함
  맞춤여유: 1.15,        // 처음 자리에서 모델 둘레 여유
  아래각: 25,            // "아래"(올려다보기) 각도(도) — SSOT 40 4절 "위·아래 25도"
  옮김시간: 250,         // 카메라가 옮겨 가는 시간(ms)
  최소거리비: 0.02, 최대거리비: 20,   // 모델 크기에 대한 거리 범위
  밝기_하늘: 1.4, 밝기_비춤: 1.6,
  화소배율최대: 2,
  격자칸: 16, 격자그림: 512,          // 격자 텍스처: 칸 수, 그림 한 변(화소)
  형태거칠기: 0.8,
  끌기문턱: 4,           // 이보다 덜 움직이면 누르기로 봄(화소)
  다시묻기: 1000,        // "만드는 중"일 때 다시 묻는 간격(ms)
  블렌더안내초: 10,      // 이보다 오래 걸리면 "Blender 실행 중"
};
const 토큰 = (이름) => getComputedStyle(document.documentElement).getPropertyValue(이름).trim();
const 색 = () => ({
  바탕: new THREE.Color(토큰("--c-canvas")),
  형태: new THREE.Color(토큰("--c-text-2")),
  격자1: 토큰("--c-text-1"), 격자2: 토큰("--c-neutral-btn"), 격자선: 토큰("--c-accent"),
  하늘: new THREE.Color(토큰("--c-text-1")), 땅: new THREE.Color(토큰("--c-neutral-btn")),
});

// ---------------------------------------------------------------- 화면 요소(한 번 만들고 다시 붙인다)
const 뿌리 = document.createElement("div");
뿌리.className = "v3";
뿌리.innerHTML = `
<div class="vrow" data-순서="보기 줄">
  <div class="view" id="v3view">
    <canvas class="v3c" id="v3c" tabindex="-1" aria-label="3D 보기: 왼쪽 끌기 옮기기, 오른쪽 끌기 돌리기, 휠 확대, 두 번 눌러 회전 중심"></canvas>
    <span class="lbl" id="v3lbl">텍스처</span>
    <span class="lbl2" id="v3st"></span>
    <div class="vmsg" id="v3msg" hidden></div>
  </div>
</div>
<div class="tools" data-순서="도구 줄">
  <div class="tgrp" aria-label="칠하기" id="v3paint">
    <button type="button" class="tb" data-칠="보기" title="붓 내려놓기: 왼쪽 끌기가 다시 옮기기 (V)">보기<span class="k">V</span></button>
    <button type="button" class="tb" data-칠="붓" title="붓: 왼쪽 끌기로 칠하기, Shift+휠로 크기 (B)">붓<span class="k">B</span></button>
    <button type="button" class="tb" data-칠="지우개" title="지우개: 칠한 면을 뺀다 (E)">지우개<span class="k">E</span></button>
  </div>
  <div class="tgrp" aria-label="방향">
    <button type="button" class="tb" data-v="앞" title="앞에서 보기 (1)">앞<span class="k">1</span></button>
    <button type="button" class="tb" data-v="옆" title="옆(+x 쪽)에서 보기 (2)">옆<span class="k">2</span></button>
    <button type="button" class="tb" data-v="뒤" title="뒤에서 보기 (3)">뒤<span class="k">3</span></button>
    <button type="button" class="tb" data-v="아래" title="앞 아래에서 올려다보기 (4)">아래 (올려다보기)<span class="k">4</span></button>
    <button type="button" class="tb" id="v3home" title="모델 전체가 보이게 처음 자리로 (F)">처음 자리<span class="k">F</span></button>
    <button type="button" class="tb" id="v3proj" title="원근 보기 / 평행 보기 (5)">원근<span class="k">5</span></button>
  </div>
  <div class="tgrp" aria-label="보이기">
    <button type="button" class="tb" id="v3parts" aria-expanded="false" title="파츠마다 켜고 끄기, 이 파츠만 (H)">파츠 숨김 ▾<span class="k">H</span></button>
    <div class="pop" id="v3pop" hidden></div>
    <button type="button" class="tb" id="v3shape" title="텍스처를 끄고 회색과 음영만">형태만</button>
    <button type="button" class="tb" id="v3grid" title="UV에 격자무늬(늘어남 확인)">격자</button>
    <button type="button" class="tb" id="v3wire" title="면을 선으로(리토폴로지 확인)">와이어</button>
  </div>
  <div class="tgrp" aria-label="비교">
    <button type="button" class="tb" id="v3before" title="누르고 있는 동안 마지막 처리 전 모델 (Space)">전후 비교<span class="k">Space</span></button>
    <button type="button" class="tb" id="v3side" title="전과 지금을 나란히">나란히</button>
  </div>
  <div class="tgrp" aria-label="리깅" id="v3rig" hidden>
    <button type="button" class="tb" id="v3bones" title="뼈대를 선으로 겹쳐 보기">뼈대</button>
    <button type="button" class="tb" id="v3quad" title="앞·옆·뒤·아래(올려다보기)를 한 화면에. 칠하기는 한 방향 보기에서만">네 방향</button>
  </div>
</div>`;
const $ = (id) => 뿌리.querySelector("#" + id);
const 글 = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));

// ---------------------------------------------------------------- three.js 바탕
let 그리개 = null, 씬 = null, 원근 = null, 평행 = null, 비춤 = null, 색값 = null;
let 웹지엘 = true;
try {
  그리개 = new THREE.WebGLRenderer({canvas: $("v3c"), antialias: true});
  그리개.setPixelRatio(Math.min(devicePixelRatio || 1, 상수.화소배율최대));
} catch (e) {
  웹지엘 = false;
}

const 보기 = {
  이름: null, 해시요청: null,      // 붙인 캐릭터, 마지막으로 물은 작업본해시
  지금: null, 전: null,            // {주소, 뿌리(Group), 파츠: Map(이름 → [메시])}
  작업본주소: null, 미리주소: null, // W14: 작업본 GLB 주소, 10단계 미리 보기로 띄운 GLB 주소(없으면 null)
  전주소: null, 전불러오는중: false,
  상태글: "", 갱신중: false,
  평행: false, 형태만: false, 격자: false, 와이어: false, 전보기: false, 나란히: false,
  색: null,                        // W11 3단계: null · "조각" · "파츠" · "노멀"(형태만 대신 칠하는 색)
  숨김: new Set(), 하나: null,     // 숨긴 파츠 이름, "이 파츠만"으로 고른 파츠
  중심: new THREE.Vector3(), 회전: new THREE.Quaternion(), 거리: 1, 크기: 1,
  옮김: null,                      // 카메라 옮김 {시작시각, 전, 후}
  묻기타이머: null, 묻기번호: 0,
  화면수: 0,                       // 그린 화면 수(초당 화면 수 재기용)
  // W13 8·9단계: 동작 재생(GLB의 동작), 뼈대 선, 네 방향 한 화면
  동작: {이름: null, 시각: 0, 재생: false, 마지막: 0},
  뼈대: false, 네방향: false, 리깅단추: false,
};
window.보기3d상태 = 보기;          // 시험·검사용으로 읽기만

if (웹지엘) {
  색값 = 색();
  씬 = new THREE.Scene();
  씬.background = 색값.바탕;
  씬.add(new THREE.HemisphereLight(색값.하늘, 색값.땅, 상수.밝기_하늘));
  비춤 = new THREE.DirectionalLight(0xffffff, 상수.밝기_비춤);
  씬.add(비춤, 비춤.target);
  원근 = new THREE.PerspectiveCamera(상수.시야각, 1, 0.01, 100);
  평행 = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.01, 100);
  new ResizeObserver(() => { 크기맞추기(); 그리기요청(); }).observe($("v3view"));
} else {
  알림(`이 브라우저에서 WebGL을 쓸 수 없어 3D 보기를 띄우지 못합니다.<span class="hint">그래픽 가속이 꺼져 있으면 켜고 다시 열어 주세요.</span>`);
}

function 알림(html) {
  const m = $("v3msg");
  m.innerHTML = html || "";
  m.hidden = !html;
}
function 상태줄() {
  const 파츠수 = 보기.지금 ? 보기.지금.파츠.size : 0;
  const 보이는수 = 보기.지금 ? [...보기.지금.파츠.keys()].filter(보이는파츠).length : 0;
  const 조각 = [보기.평행 ? "평행" : "원근"];
  if (보기.지금) 조각.push(보기.하나 ? `이 파츠만: ${보기.하나}` : `파츠 ${보이는수}/${파츠수}`);
  if (보기.갱신중) 조각.push("갱신 중");
  if (보기.상태글) 조각.push(보기.상태글);
  const 부위글 = window.부위 && window.부위.상태글 && window.부위.상태글();   // W05 부위.js
  if (부위글) 조각.push(부위글);
  $("v3st").textContent = 조각.join(" · ");
  $("v3st").title = $("v3st").textContent;
  const 모양 = 보기.와이어 ? "와이어" : 보기.격자 ? "격자" : 보기.색 ? {조각: "조각 색", 파츠: "파츠 색", 노멀: "노멀 방향"}[보기.색] : 보기.형태만 ? "형태만" : "텍스처";
  $("v3lbl").textContent = 보기.나란히 ? `왼쪽: 전 · 오른쪽: 지금 · ${모양}` : 보기.전보기 ? `전 (마지막 처리 전) · ${모양}`
    : 보기.네방향 ? `네 방향: 앞 · 옆 / 뒤 · 아래 · ${모양}` : 모양;
  $("v3rig").hidden = !보기.리깅단추;   // W13: 8·9단계에서만
  $("v3bones").classList.toggle("on", 보기.뼈대);
  $("v3quad").classList.toggle("on", 보기.네방향);
  // 단추 켜짐 모양
  $("v3proj").firstChild.textContent = 보기.평행 ? "평행" : "원근";
  $("v3proj").classList.toggle("on", 보기.평행);
  $("v3shape").classList.toggle("on", 보기.형태만 && !보기.색);
  $("v3wire").classList.toggle("on", 보기.와이어);
  $("v3grid").classList.toggle("on", 보기.격자);
  $("v3before").classList.toggle("on", 보기.전보기);
  $("v3side").classList.toggle("on", 보기.나란히);
  $("v3parts").classList.toggle("on", 보기.숨김.size > 0 || Boolean(보기.하나));
  const 없음 = !보기.지금;
  for (const b of 뿌리.querySelectorAll(".tools .tb")) {
    if (b.id === "v3before" || b.id === "v3side" || b.dataset.칠 || b.closest("[data-자체단추]")) continue;   // 붓·지우개는 칠하기.js가, 시간 막대는 리깅단계.js(W13)가 정한다
    b.disabled = 없음;
    if (없음) b.title = b.title.split(" — ")[0] + " — 모델이 아직 없습니다";
    else b.title = b.title.split(" — ")[0];
  }
  for (const id of ["v3before", "v3side"]) {
    const b = $(id);
    b.disabled = 없음 || !보기.전주소;
    const 기본 = b.title.split(" — ")[0];
    b.title = b.disabled ? `${기본} — 마지막 처리 전 GLB가 없습니다` : 기본;
  }
}

// ---------------------------------------------------------------- 카메라
function 카메라() { return 보기.평행 ? 평행 : 원근; }
function 크기맞추기() {
  if (!웹지엘) return;
  const v = $("v3view");
  const w = Math.max(1, v.clientWidth), h = Math.max(1, v.clientHeight);
  그리개.setSize(w, h, false);
}
function 카메라놓기(가로, 세로) {
  const 앞 = new THREE.Vector3(0, 0, 1).applyQuaternion(보기.회전);
  const 반높이 = 보기.거리 * Math.tan(THREE.MathUtils.degToRad(상수.시야각) / 2);
  for (const c of [원근, 평행]) {
    c.position.copy(보기.중심).addScaledVector(앞, 보기.거리);
    c.quaternion.copy(보기.회전);
    c.near = 보기.거리 / 100; c.far = 보기.거리 + 보기.크기 * 4;
  }
  원근.aspect = 가로 / 세로;
  평행.left = -반높이 * 가로 / 세로; 평행.right = 반높이 * 가로 / 세로; 평행.top = 반높이; 평행.bottom = -반높이;
  원근.updateProjectionMatrix(); 평행.updateProjectionMatrix();
  비춤.position.copy(원근.position); 비춤.target.position.copy(보기.중심);
}
function 화소당길이() {
  return 2 * 보기.거리 * Math.tan(THREE.MathUtils.degToRad(상수.시야각) / 2) / Math.max(1, $("v3view").clientHeight);
}
function 거리제한(d) { return Math.min(보기.크기 * 상수.최대거리비, Math.max(보기.크기 * 상수.최소거리비, d)); }

// 정해 둔 방향: 모델 앞은 +z(Blender의 -Y), 옆은 +x 쪽(보는 사람 기준 오른쪽)
const 방향 = {
  앞: new THREE.Euler(0, 0, 0),
  옆: new THREE.Euler(0, Math.PI / 2, 0),
  뒤: new THREE.Euler(0, Math.PI, 0),
  아래: new THREE.Euler(THREE.MathUtils.degToRad(상수.아래각), 0, 0, "YXZ"),
};
function 옮기기(후) {
  // 후: {중심?, 회전?, 거리?} — 상수.옮김시간 동안 부드럽게
  const 전 = {중심: 보기.중심.clone(), 회전: 보기.회전.clone(), 거리: 보기.거리};
  보기.옮김 = {시작: performance.now(), 전, 후: {중심: (후.중심 || 전.중심).clone(), 회전: (후.회전 || 전.회전).clone(), 거리: 후.거리 ?? 전.거리}};
  그리기요청();
}
function 옮김진행(지금) {
  const o = 보기.옮김;
  if (!o) return false;
  let t = Math.min(1, (지금 - o.시작) / 상수.옮김시간);
  const s = t * t * (3 - 2 * t);
  보기.중심.lerpVectors(o.전.중심, o.후.중심, s);
  보기.회전.slerpQuaternions(o.전.회전, o.후.회전, s);
  보기.거리 = o.전.거리 + (o.후.거리 - o.전.거리) * s;
  if (t >= 1) 보기.옮김 = null;
  return t < 1;
}
function 방향보기(이름) {
  if (!보기.지금) return;
  옮기기({회전: new THREE.Quaternion().setFromEuler(방향[이름])});
}
function 상자(파츠이름들) {
  const b = new THREE.Box3();
  for (const 이름 of 파츠이름들) for (const m of 보기.지금.파츠.get(이름) || []) b.expandByObject(m, true);
  return b;
}
function 맞춤(파츠이름들, 방향이름 = "앞", 바로 = false) {
  if (!보기.지금) return;
  const b = 상자(파츠이름들);
  if (b.isEmpty()) return;
  const 크기 = b.getSize(new THREE.Vector3()), 가운데 = b.getCenter(new THREE.Vector3());
  const v = $("v3view"), 비율 = Math.max(1, v.clientWidth) / Math.max(1, v.clientHeight);
  const 탄 = Math.tan(THREE.MathUtils.degToRad(상수.시야각) / 2);
  const 회전 = new THREE.Quaternion().setFromEuler(방향[방향이름]);
  const 폭 = Math.max(크기.x, 크기.z);   // 옆에서 보아도 들어오게
  const 거리 = Math.max(크기.y / 2 / 탄, 폭 / 2 / (탄 * 비율)) * 상수.맞춤여유 + 폭 / 2;
  if (바로) { 보기.중심.copy(가운데); 보기.회전.copy(회전); 보기.거리 = 거리; 보기.옮김 = null; 그리기요청(); }
  else 옮기기({중심: 가운데, 회전, 거리});
}
function 처음자리() {
  if (!보기.지금) return;
  맞춤(보이는파츠목록().length ? 보이는파츠목록() : [...보기.지금.파츠.keys()]);
}

// ---------------------------------------------------------------- 그리기(바뀔 때만)
let 요청됨 = false;
function 그리기요청() {
  if (요청됨 || !웹지엘) return;
  요청됨 = true;
  requestAnimationFrame(그리기);
}
function 그리기(지금) {
  요청됨 = false;
  if (!뿌리.isConnected) return;
  const 더 = 옮김진행(지금 ?? performance.now());
  const 재생중 = 재생진행(지금 ?? performance.now());
  const v = $("v3view"), w = Math.max(1, v.clientWidth), h = Math.max(1, v.clientHeight);
  const 보일것 = (전) => {
    if (보기.지금) 보기.지금.뿌리.visible = !전;
    if (보기.전) 보기.전.뿌리.visible = 전;
  };
  if (보기.네방향 && !보기.나란히) {
    // W13: 앞 · 옆 / 뒤 · 아래(올려다보기). 회전 중심과 거리는 지금 보기 그대로
    const 반w = Math.floor(w / 2), 반h = Math.floor(h / 2), 원회전 = 보기.회전.clone();
    그리개.setScissorTest(true);
    for (const [이름, x, y] of [["앞", 0, h - 반h], ["옆", 반w, h - 반h], ["뒤", 0, 0], ["아래", 반w, 0]]) {
      보기.회전.setFromEuler(방향[이름]);
      카메라놓기(반w, 반h);
      그리개.setViewport(x, y, 반w, 반h); 그리개.setScissor(x, y, 반w, 반h);
      보일것(false);
      그리개.render(씬, 카메라());
    }
    보기.회전.copy(원회전);
    그리개.setScissorTest(false);
    그리개.setViewport(0, 0, w, h);
  } else if (보기.나란히 && 보기.전) {
    const 반 = Math.floor(w / 2);
    카메라놓기(반, h);
    그리개.setScissorTest(true);
    for (const [x, 전] of [[0, true], [반, false]]) {
      그리개.setViewport(x, 0, 반, h); 그리개.setScissor(x, 0, 반, h);
      보일것(전);
      그리개.render(씬, 카메라());
    }
    그리개.setScissorTest(false);
    그리개.setViewport(0, 0, w, h);
  } else {
    카메라놓기(w, h);
    보일것(보기.전보기 && Boolean(보기.전));
    그리개.render(씬, 카메라());
  }
  보기.화면수++;
  if (더 || 재는중 || 재생중) 그리기요청();
}

// ---------------------------------------------------------------- 모델 불러오기
const 불러오개 = new GLTFLoader();
let 격자텍스처 = null;
function 격자만들기() {
  if (격자텍스처) return 격자텍스처;
  const c = document.createElement("canvas");
  c.width = c.height = 상수.격자그림;
  const g = c.getContext("2d"), 칸 = 상수.격자그림 / 상수.격자칸;
  for (let i = 0; i < 상수.격자칸; i++) for (let j = 0; j < 상수.격자칸; j++) {
    g.fillStyle = (i + j) % 2 ? 색값.격자1 : 색값.격자2;
    g.fillRect(i * 칸, j * 칸, 칸, 칸);
  }
  g.fillStyle = 색값.격자선;   // 윗변·왼변에 선(UV 방향 확인)
  g.fillRect(0, 0, 상수.격자그림, 칸 / 4); g.fillRect(0, 0, 칸 / 4, 상수.격자그림);
  격자텍스처 = new THREE.CanvasTexture(c);
  격자텍스처.colorSpace = THREE.SRGBColorSpace;
  격자텍스처.flipY = false;    // glTF의 UV와 같은 방향
  return 격자텍스처;
}
const 형태재질 = () => new THREE.MeshStandardMaterial({color: 색값.형태, roughness: 상수.형태거칠기, metalness: 0});
const 와이어재질 = () => new THREE.MeshBasicMaterial({color: 색값.형태, wireframe: true});   // W10: 4단계 기본
const 격자재질 = () => new THREE.MeshStandardMaterial({map: 격자만들기(), roughness: 상수.형태거칠기, metalness: 0});

function 파츠모으기(뿌리그룹) {
  // 파츠 = Blender 객체. glTF에서 재질이 여럿인 객체는 Group 아래 메시 여러 개가 된다.
  const 파츠 = new Map();
  뿌리그룹.traverse((o) => {
    if (!o.isMesh) return;
    const p = o.parent;
    const 묶음 = p && p.isGroup && !p.isScene && p.children.length > 1 && p.children.every((c) => c.isMesh);
    const 이름 = (묶음 ? p.name : o.name) || "이름 없음";
    if (!파츠.has(이름)) 파츠.set(이름, []);
    파츠.get(이름).push(o);
    o.userData.파츠 = 이름;
    o.userData.원래재질 = o.material;
    o.frustumCulled = false;   // 스킨 메시가 화면 끝에서 사라지지 않게
  });
  return 파츠;
}
function 버리기(m) {
  if (!m) return;
  씬.remove(m.뿌리);
  m.뿌리.traverse((o) => {
    if (!o.isMesh) return;
    o.geometry.dispose();
    for (const 재질 of [].concat(o.userData.원래재질 || [])) {
      for (const k of Object.keys(재질)) if (재질[k] && 재질[k].isTexture) 재질[k].dispose();
      재질.dispose();
    }
  });
}
async function glb읽기(주소) {
  const g = await 불러오개.loadAsync(주소);
  const 뿌리그룹 = g.scene;
  뿌리그룹.updateMatrixWorld(true);
  const 동작들 = g.animations || [];
  return {주소, 뿌리: 뿌리그룹, 파츠: 파츠모으기(뿌리그룹), 동작들, 섞개: 동작들.length ? new THREE.AnimationMixer(뿌리그룹) : null};
}

// ---------------------------------------------------------------- W13: 동작 재생(8·9단계)
// 시각은 GLB 동작의 초. 장 번호로 바꾸는 것은 리깅단계.js(Blender의 장초당·시작장을 앎)가 한다.
function 클립(m, 이름) { return (m && 이름 && m.동작들.find((c) => c.name === 이름)) || null; }
function 클립시작(c) {
  let t = Infinity;
  for (const tr of c.tracks) if (tr.times.length) t = Math.min(t, tr.times[0]);
  return Number.isFinite(t) ? t : 0;
}
function 자세입히기(m) {
  if (!m || !m.섞개) return;
  const c = 클립(m, 보기.동작.이름);
  m.섞개.stopAllAction();
  if (!c) {
    m.뿌리.traverse((o) => { if (o.isSkinnedMesh) o.skeleton.pose(); });   // 동작 없음 = 기본 자세
  } else {
    const a = m.섞개.clipAction(c);
    a.play();
    a.time = Math.min(Math.max(보기.동작.시각, 클립시작(c)), c.duration);
    m.섞개.update(0);
  }
  m.뿌리.updateMatrixWorld(true);
}
function 자세모두() { 자세입히기(보기.지금); 자세입히기(보기.전); 그리기요청(); window.dispatchEvent(new Event("보기3d장")); }
function 재생진행(지금) {
  const d = 보기.동작, c = 클립(보기.지금, d.이름);
  if (!d.재생 || !c) { d.마지막 = 0; return false; }
  const 초 = d.마지막 ? Math.min(0.1, (지금 - d.마지막) / 1000) : 0;
  d.마지막 = 지금;
  const t0 = 클립시작(c), 길이 = Math.max(1e-6, c.duration - t0);
  d.시각 = t0 + ((d.시각 - t0 + 초) % 길이 + 길이) % 길이;
  자세입히기(보기.지금); 자세입히기(보기.전);
  window.dispatchEvent(new Event("보기3d장"));
  return true;
}
function 동작정하기(v) {
  const d = 보기.동작;
  if ("이름" in v) { d.이름 = v.이름 || null; if (!("시각" in v)) d.시각 = 0; }
  if ("시각" in v) { d.시각 = Number(v.시각) || 0; }
  if ("재생" in v) { d.재생 = Boolean(v.재생) && Boolean(클립(보기.지금, d.이름)); d.마지막 = 0; }
  자세모두();
  상태줄();
}
function 동작정보() {
  const m = 보기.지금;
  return {목록: m ? m.동작들.map((c) => ({이름: c.name, 시작: 클립시작(c), 끝: c.duration})) : [],
    이름: 보기.동작.이름, 시각: 보기.동작.시각, 재생: 보기.동작.재생,
    뼈수: m ? (() => { const s = new Set(); m.뿌리.traverse((o) => { if (o.isSkinnedMesh) for (const b of o.skeleton.bones) s.add(b); }); return s.size; })() : 0,
    뼈이름: m ? (() => { const s = new Set(); m.뿌리.traverse((o) => { if (o.isSkinnedMesh) for (const b of o.skeleton.bones) s.add(b.name); }); return [...s]; })() : []};
}
let 뼈돕개 = null;
function 뼈대그리기() {
  if (뼈돕개) { 씬.remove(뼈돕개); 뼈돕개.dispose(); 뼈돕개 = null; }
  if (!보기.뼈대 || !보기.지금) return;
  뼈돕개 = new THREE.SkeletonHelper(보기.지금.뿌리);
  뼈돕개.material.depthTest = false;
  뼈돕개.material.transparent = true;
  뼈돕개.renderOrder = 10;
  뼈돕개.userData.고르기빼기 = true;   // 칠하기의 고르기 그림에 들어가지 않게
  씬.add(뼈돕개);
}
// W11: 3단계 보기 색. 조각 = 파츠 안에서 서로 이어지지 않은 덩어리(정점 자리로 이음, 가장 큰 덩어리는 회색),
// 파츠 = 파츠마다 다른 색, 노멀 = 면이 향한 방향(뒤집힌 면은 주변과 다른 색으로 보임)
const 색들 = (n) => Array.from({length: n}, (_, i) => new THREE.Color().setHSL((i * 0.618034) % 1, 0.55, 0.55));
function 조각색넣기(메시들) {
  if (메시들[0] && 메시들[0].geometry.attributes.jogak_col) return;
  const 열쇠 = new Map(), 부모 = [];
  const 찾기 = (x) => { while (부모[x] !== x) { 부모[x] = 부모[부모[x]]; x = 부모[x]; } return x; };
  const 잇기 = (x, y) => { x = 찾기(x); y = 찾기(y); if (x !== y) 부모[y] = x; };
  const 번호들 = [];
  for (const o of 메시들) {
    const g = o.geometry, pos = g.attributes.position, 칸 = new Int32Array(pos.count);
    for (let i = 0; i < pos.count; i++) {
      const k = `${Math.round(pos.getX(i) * 1e5)},${Math.round(pos.getY(i) * 1e5)},${Math.round(pos.getZ(i) * 1e5)}`;
      let n = 열쇠.get(k);
      if (n === undefined) { n = 부모.length; 부모.push(n); 열쇠.set(k, n); }
      칸[i] = n;
    }
    const idx = g.index;
    const 삼 = idx ? idx.count / 3 : pos.count / 3;
    for (let t = 0; t < 삼; t++) {
      const a = idx ? idx.getX(t * 3) : t * 3, b = idx ? idx.getX(t * 3 + 1) : t * 3 + 1, c = idx ? idx.getX(t * 3 + 2) : t * 3 + 2;
      잇기(칸[a], 칸[b]); 잇기(칸[a], 칸[c]);
    }
    번호들.push(칸);
  }
  const 수 = new Map();
  for (const 칸 of 번호들) for (const n of 칸) { const r = 찾기(n); 수.set(r, (수.get(r) || 0) + 1); }
  const 차례 = [...수.keys()].sort((x, y) => 수.get(y) - 수.get(x));
  const 팔레트 = 색들(차례.length), 회색 = new THREE.Color(색값.형태), 자리 = new Map(차례.map((r, i) => [r, i]));
  메시들.forEach((o, j) => {
    const 칸 = 번호들[j], 값 = new Float32Array(칸.length * 3);
    for (let i = 0; i < 칸.length; i++) {
      const k = 자리.get(찾기(칸[i])), c = k === 0 ? 회색 : 팔레트[k];
      값[i * 3] = c.r; 값[i * 3 + 1] = c.g; 값[i * 3 + 2] = c.b;
    }
    o.geometry.setAttribute("jogak_col", new THREE.BufferAttribute(값, 3));
    o.userData.조각수 = 차례.length;
  });
}
function 조각재질() {
  const 재질 = new THREE.MeshStandardMaterial({color: 0xffffff, roughness: 상수.형태거칠기, metalness: 0});
  재질.onBeforeCompile = (s) => {
    s.vertexShader = "attribute vec3 jogak_col;\nvarying vec3 vJogak;\n" + s.vertexShader.replace("#include <begin_vertex>", "#include <begin_vertex>\nvJogak = jogak_col;");
    s.fragmentShader = "varying vec3 vJogak;\n" + s.fragmentShader.replace("#include <color_fragment>", "#include <color_fragment>\ndiffuseColor.rgb *= vJogak;");
  };
  재질.customProgramCacheKey = () => "조각색";
  return 재질;
}
function 색재질(m) {
  if (!보기.색) return null;
  const 표 = new Map(), 팔레트 = 색들(m.파츠.size);
  [...m.파츠.keys()].forEach((이름, i) => {
    if (보기.색 === "노멀") 표.set(이름, new THREE.MeshNormalMaterial());
    else if (보기.색 === "파츠") 표.set(이름, new THREE.MeshStandardMaterial({color: 팔레트[i], roughness: 상수.형태거칠기, metalness: 0}));
    else { 조각색넣기(m.파츠.get(이름)); 표.set(이름, 조각재질()); }
  });
  return 표;
}
function 모양입히기(m) {
  if (!m) return;
  const 형태 = 형태재질(), 격자 = 격자재질(), 와이어 = 와이어재질();
  const 색표 = 보기.와이어 || 보기.격자 ? null : 색재질(m);
  for (const [이름, 메시들] of m.파츠) for (const o of 메시들) {
    const 바꿈 = 보기.와이어 ? 와이어 : 보기.격자 ? 격자 : 색표 ? 색표.get(이름) : 보기.형태만 ? 형태 : null;
    o.material = 바꿈 ? (Array.isArray(o.userData.원래재질) ? o.userData.원래재질.map(() => 바꿈) : 바꿈) : o.userData.원래재질;
    o.visible = 보이는파츠(이름);
  }
}
function 보이는파츠(이름) { return 보기.하나 ? 이름 === 보기.하나 : !보기.숨김.has(이름); }
function 보이는파츠목록() { return 보기.지금 ? [...보기.지금.파츠.keys()].filter(보이는파츠) : []; }
function 모두다시() { 모양입히기(보기.지금); 모양입히기(보기.전); window.dispatchEvent(new Event("보기3d모양")); 파츠목록그리기(); 상태줄(); 그리기요청(); }   // 보기3d모양: 부위.js가 새 재질에 부위 흐림·숨김을 입힌다

async function 지금바꾸기(주소, 갱신중) {
  if (보기.지금 && 보기.지금.주소 === 주소) { 보기.갱신중 = 갱신중; 상태줄(); return; }
  보기.상태글 = "불러오는 중…"; 상태줄();
  const 이름 = 보기.이름;
  let m;
  try {
    m = await glb읽기(주소);
  } catch (e) {
    if (이름 !== 보기.이름) return;
    보기.상태글 = "";
    알림(`모델을 띄우지 못함<span class="hint">GLB를 읽지 못했습니다: ${글(e.message || e)}</span>`);
    상태줄();
    return;
  }
  if (이름 !== 보기.이름) { 버리기(m); return; }   // 그사이 캐릭터가 바뀜
  const 처음 = !보기.지금;
  버리기(보기.지금);
  보기.지금 = m;
  씬.add(m.뿌리);
  // 이름이 사라진 파츠는 숨김·이 파츠만에서 뺀다
  for (const n of [...보기.숨김]) if (!m.파츠.has(n)) 보기.숨김.delete(n);
  if (보기.하나 && !m.파츠.has(보기.하나)) 보기.하나 = null;
  보기.갱신중 = 갱신중;
  보기.상태글 = "";
  알림("");
  const b = 상자([...m.파츠.keys()]);
  보기.크기 = Math.max(1e-6, b.getSize(new THREE.Vector3()).length());
  모두다시();
  if (보기.동작.이름 && !클립(m, 보기.동작.이름)) { 보기.동작.이름 = null; 보기.동작.재생 = false; }   // W13
  자세입히기(m);
  뼈대그리기();
  if (처음) { 크기맞추기(); 맞춤([...m.파츠.keys()], "앞", true); }
  모델알림();
  window.dispatchEvent(new Event("보기3d장"));
}
function 모델알림() { 뼈대그리기(); window.dispatchEvent(new Event("보기3d모델")); }   // 칠하기.js가 면 지도·칠한 곳 표시를 다시 만든다
async function 전불러오기() {
  if (!보기.전주소 || 보기.전불러오는중) return;
  if (보기.전 && 보기.전.주소 === 보기.전주소) return;
  보기.전불러오는중 = true; 보기.상태글 = "전 불러오는 중…"; 상태줄();
  const 이름 = 보기.이름, 주소 = 보기.전주소;
  try {
    const m = await glb읽기(주소);
    if (이름 !== 보기.이름 || 주소 !== 보기.전주소) { 버리기(m); return; }
    버리기(보기.전);
    보기.전 = m;
    m.뿌리.visible = false;
    씬.add(m.뿌리);
    모양입히기(m);
    자세입히기(m);   // W13: 전도 같은 동작·같은 장으로
  } catch (e) {
    보기.전주소 = null;
  } finally {
    보기.전불러오는중 = false; 보기.상태글 = ""; 상태줄(); 그리기요청();
  }
}

async function 모델묻기(다시 = false) {
  clearTimeout(보기.묻기타이머);
  const 이름 = 보기.이름, 번호 = ++보기.묻기번호;
  if (!이름 || !웹지엘) return;
  let v;
  try {
    const r = await fetch(`/api/모델?이름=${encodeURIComponent(이름)}${다시 ? "&다시=1" : ""}`, {cache: "no-store"});
    v = await r.json();
    if (!r.ok) throw new Error(v.오류 || r.status);
  } catch (e) {
    if (번호 !== 보기.묻기번호) return;
    보기.상태글 = "서버에 묻지 못함";
    if (!보기.지금) 알림(`모델을 불러오지 못했습니다.<span class="hint">서버 응답: ${글(String(e.message || e))} — 서버가 옛 버전이면 껐다 켜 주세요. 잠시 뒤 다시 시도합니다.</span>`);
    상태줄();
    보기.묻기타이머 = setTimeout(모델묻기, 상수.다시묻기 * 3);
    return;
  }
  if (번호 !== 보기.묻기번호 || 이름 !== 보기.이름) return;
  if (보기.전주소 !== v.전) { 버리기(보기.전); 보기.전 = null; 보기.전주소 = v.전 || null; 보기.전보기 = false; if (!보기.전주소) 보기.나란히 = false; }
  if (v.상태 === "됨") {
    보기.작업본주소 = v.주소;
    if (!보기.미리주소) await 지금바꾸기(v.주소, false);   // W14: 10단계 미리 보기 중이면 작업본 GLB는 기억만
  } else if (v.상태 === "만드는 중" && 보기.미리주소) {
    보기.묻기타이머 = setTimeout(모델묻기, 상수.다시묻기);
  } else if (v.상태 === "만드는 중") {
    const 초 = Math.round(v.경과초 || 0);
    if (v.마지막) {
      // 작업본이 바뀌는 중: 마지막으로 만든 GLB를 보여 주고 "갱신 중"
      await 지금바꾸기(v.마지막, true);
      보기.갱신중 = true;
      보기.상태글 = 초 >= 상수.블렌더안내초 ? `Blender 실행 중 ${초}초` : `${초}초`;
      상태줄();
    } else {
      알림(`모델을 만드는 중… ${초}초${초 >= 상수.블렌더안내초 ? `<span class="hint">Blender 실행 중 (작업본에서 GLB를 만들고 있습니다)</span>` : ""}`);
    }
    보기.묻기타이머 = setTimeout(모델묻기, 상수.다시묻기);
  } else if (v.상태 === "작업본 없음") {
    버리기(보기.지금); 보기.지금 = null; 모델알림();
    알림(`작업본이 없습니다.<span class="hint">상태.json의 "작업본"에 blend 경로가 적히면 여기에 3D로 뜹니다.${v.작업본 ? ` (적힌 경로: ${글(v.작업본)} — 파일 없음)` : ""}</span>`);
    상태줄();
  } else {
    버리기(보기.지금); 보기.지금 = null; 모델알림();
    알림(`모델을 띄우지 못함<span class="hint">${글(v.오류 || "알 수 없는 오류")}${v.로그 ? `<br>Blender 기록: ${글(v.로그)}` : ""}</span>` +
      `<button type="button" class="tb" id="v3retry">다시 만들기</button>`);
    상태줄();
    const r = $("v3retry");
    if (r) r.addEventListener("click", () => 모델묻기(true));
  }
}

// ---------------------------------------------------------------- 파츠 숨김 목록
function 파츠목록그리기() {
  const p = $("v3pop");
  if (!보기.지금) { p.innerHTML = ""; return; }
  p.innerHTML = [...보기.지금.파츠.keys()].map((n) =>
    `<div class="prow"><label class="pchk" title="${글(n)} 보이기"><input type="checkbox" data-p="${글(n)}"${보기.숨김.has(n) ? "" : " checked"}${보기.하나 ? " disabled" : ""}><span class="pn">${글(n)}</span></label>` +
    `<button type="button" class="tb${보기.하나 === n ? " on" : ""}" data-only="${글(n)}" title="${보기.하나 === n ? "다시 누르면 전체" : `${글(n)}만 보이고 카메라를 맞춤`}">이 파츠만</button></div>`).join("") +
    `<div class="hint">모델 위 Alt+클릭: 그 파츠만 / 다시 하면 전체</div>`;
}
function 이파츠만(이름) {
  보기.하나 = 보기.하나 === 이름 ? null : 이름;
  모두다시();
  if (보기.하나) 맞춤([보기.하나], "앞"); else 처음자리();
}
function 목록열기(열기 = $("v3pop").hidden) {
  if (!보기.지금) return;
  $("v3pop").hidden = !열기;
  $("v3parts").setAttribute("aria-expanded", String(열기));
}
$("v3parts").addEventListener("click", () => 목록열기());
$("v3pop").addEventListener("change", (ev) => {
  const n = ev.target.dataset.p;
  if (n == null) return;
  if (ev.target.checked) 보기.숨김.delete(n); else 보기.숨김.add(n);
  모두다시();
});
$("v3pop").addEventListener("click", (ev) => {
  const b = ev.target.closest("[data-only]");
  if (b) 이파츠만(b.dataset.only);
});
document.addEventListener("pointerdown", (ev) => {
  if (!$("v3pop").hidden && !ev.target.closest("#v3pop, #v3parts")) 목록열기(false);
});

// ---------------------------------------------------------------- 마우스
function 맞힌곳(ev) {
  if (!보기.지금) return null;
  const c = $("v3c"), r = c.getBoundingClientRect();
  const ndc = new THREE.Vector2(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
  if (보기.나란히) return null;   // 나란히 볼 때는 고르지 않음
  카메라놓기(r.width, r.height);
  const 광선 = new THREE.Raycaster();
  광선.setFromCamera(ndc, 카메라());
  const 대상 = 보기.전보기 && 보기.전 ? 보기.전 : 보기.지금;
  const 맞음 = 광선.intersectObject(대상.뿌리, true);
  return 맞음.find((h) => { for (let o = h.object; o; o = o.parent) if (!o.visible) return false; return true; }) || null;
}
let 끌기 = null;
const 캔버스 = $("v3c");
캔버스.addEventListener("contextmenu", (ev) => ev.preventDefault());
캔버스.addEventListener("pointerdown", (ev) => {
  if (!보기.지금) return;
  // 왼쪽: 옮기기(가운데 버튼·Shift+왼쪽도 옮기기), 오른쪽: 돌리기. 칠하기(W03)가 붙으면 붓을 든 동안 왼쪽은 칠하기.
  const 종류 = ev.button === 2 ? "돌리기" : (ev.button === 0 || ev.button === 1) ? "옮기기" : null;
  if (!종류) return;
  ev.preventDefault();
  캔버스.setPointerCapture(ev.pointerId);
  끌기 = {종류, x: ev.clientX, y: ev.clientY, 처음x: ev.clientX, 처음y: ev.clientY, id: ev.pointerId, alt: ev.altKey && ev.button === 0, 움직임: 0};
  보기.옮김 = null;
});
캔버스.addEventListener("pointermove", (ev) => {
  if (!끌기 || ev.pointerId !== 끌기.id) return;
  const dx = ev.clientX - 끌기.x, dy = ev.clientY - 끌기.y;
  끌기.x = ev.clientX; 끌기.y = ev.clientY;
  끌기.움직임 = Math.max(끌기.움직임, Math.hypot(ev.clientX - 끌기.처음x, ev.clientY - 끌기.처음y));
  if (끌기.종류 === "돌리기") {
    // 가로 끌기는 세상의 위쪽 축, 세로 끌기는 카메라의 가로축으로 돌린다. 각도 제한이 없어 어느 각도로든 볼 수 있다.
    const 가로 = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), -dx * 상수.회전감도);
    const 세로 = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), -dy * 상수.회전감도);
    보기.회전.premultiply(가로).multiply(세로).normalize();
  } else {
    const k = 화소당길이();
    const 오른 = new THREE.Vector3(1, 0, 0).applyQuaternion(보기.회전), 위 = new THREE.Vector3(0, 1, 0).applyQuaternion(보기.회전);
    보기.중심.addScaledVector(오른, -dx * k).addScaledVector(위, dy * k);
  }
  그리기요청();
});
function 끌기끝(ev) {
  if (!끌기 || ev.pointerId !== 끌기.id) return;
  const d = 끌기;
  끌기 = null;
  if (d.alt && d.움직임 < 상수.끌기문턱) {
    const h = 맞힌곳(ev);
    if (h) 이파츠만(h.object.userData.파츠);
    else if (보기.하나) 이파츠만(보기.하나);   // 빈 곳 Alt+클릭: 전체로
  }
}
캔버스.addEventListener("pointerup", 끌기끝);
캔버스.addEventListener("pointercancel", 끌기끝);
캔버스.addEventListener("dblclick", (ev) => {
  if (ev.altKey) return;
  const h = 맞힌곳(ev);
  if (!h) return;
  // 그 자리가 회전 중심이 되고 그쪽으로 다가간다
  옮기기({중심: h.point, 거리: 거리제한(보기.거리 * 상수.다가감)});
});
캔버스.addEventListener("wheel", (ev) => {
  if (!보기.지금) return;
  ev.preventDefault();
  const 단위 = ev.deltaMode === 1 ? 16 : ev.deltaMode === 2 ? 400 : 1;   // 줄·쪽 단위를 화소 단위로
  const f = Math.exp(ev.deltaY * 단위 * 상수.휠감도);
  const 새거리 = 거리제한(보기.거리 * f), 실제 = 새거리 / 보기.거리;
  // 마우스 아래 자리(회전 중심 깊이의 평면 위)가 제자리에 남도록 확대
  const r = 캔버스.getBoundingClientRect(), k = 화소당길이();
  const 오른 = new THREE.Vector3(1, 0, 0).applyQuaternion(보기.회전), 위 = new THREE.Vector3(0, 1, 0).applyQuaternion(보기.회전);
  const 점 = 보기.중심.clone().addScaledVector(오른, (ev.clientX - r.left - r.width / 2) * k).addScaledVector(위, -(ev.clientY - r.top - r.height / 2) * k);
  보기.중심.sub(점).multiplyScalar(실제).add(점);
  보기.거리 = 새거리;
  보기.옮김 = null;
  그리기요청();
}, {passive: false});

// ---------------------------------------------------------------- 단추와 단축키
for (const b of 뿌리.querySelectorAll("[data-v]")) b.addEventListener("click", () => 방향보기(b.dataset.v));
$("v3home").addEventListener("click", 처음자리);
function 시야바꾸기() { if (!보기.지금) return; 보기.평행 = !보기.평행; 상태줄(); 그리기요청(); }
$("v3proj").addEventListener("click", 시야바꾸기);
function 형태만바꾸기() { if (!보기.지금) return; if (보기.색) { 보기.색 = null; 보기.형태만 = true; } else 보기.형태만 = !보기.형태만; 모두다시(); }   // W11: 3단계 색을 켠 채 누르면 형태만으로
function 격자바꾸기() { if (!보기.지금) return; 보기.격자 = !보기.격자; 모두다시(); }
function 와이어바꾸기() { if (!보기.지금) return; 보기.와이어 = !보기.와이어; 모두다시(); }
// W10: 단계에 들어올 때의 기본 모양(2단계 형태만, 4단계 와이어, 6단계 격자). 모델이 아직 없어도 값만 정해 둔다
function 모양정하기(v) {
  for (const k of ["형태만", "격자", "와이어"]) if (k in v) 보기[k] = Boolean(v[k]);
  if ("색" in v) 보기.색 = v.색 || null;   // W11
  if (보기.지금) 모두다시(); else 상태줄();
}
$("v3shape").addEventListener("click", 형태만바꾸기);
$("v3grid").addEventListener("click", 격자바꾸기);
$("v3wire").addEventListener("click", 와이어바꾸기);
$("v3bones").addEventListener("click", () => { if (!보기.지금) return; 보기.뼈대 = !보기.뼈대; 뼈대그리기(); 상태줄(); 그리기요청(); });   // W13
$("v3quad").addEventListener("click", () => { if (!보기.지금) return; 보기.네방향 = !보기.네방향; 상태줄(); 그리기요청(); window.dispatchEvent(new Event("보기3d장")); });
// W14: 10단계 미리 보기 — 작업본 GLB 대신 다른 GLB(모음의 원래 인형, 이 캐릭터에 옮긴 미리 보기)를 잠시 띄운다. null이면 작업본으로 돌아감.
// 미리 보기 중에는 칠하지 못한다(칠하기.js가 상태.미리주소를 봄). 동작은 동작정하기로 고른다.
async function 미리보기(주소) {
  주소 = 주소 || null;
  if (주소 === 보기.미리주소) return true;
  const 앞크기 = 보기.크기;
  보기.미리주소 = 주소;
  보기.동작.재생 = false; 보기.동작.이름 = null;
  const 갈곳 = 주소 || 보기.작업본주소;
  if (!갈곳) { 상태줄(); return false; }
  await 지금바꾸기(갈곳, false);
  if (보기.지금 && 보기.지금.주소 === 갈곳 && Math.abs(보기.크기 - 앞크기) > 앞크기 * 0.05) { 크기맞추기(); 맞춤([...보기.지금.파츠.keys()], "앞", true); }
  상태줄();
  return Boolean(보기.지금 && 보기.지금.주소 === 갈곳);
}
function 리깅단추(켬, 뼈대기본) {   // W13: 리깅단계.js가 8·9단계에서 켠다. 끌 때 뼈대·네 방향·재생도 끔
  if (켬 === 보기.리깅단추 && (!켬 || Boolean(뼈대기본) === 보기.리깅뼈대기본)) return;
  보기.리깅단추 = 켬; 보기.리깅뼈대기본 = Boolean(뼈대기본);
  if (켬) 보기.뼈대 = Boolean(뼈대기본);   // 8단계는 켬, 9단계는 끔으로 시작
  else { 보기.뼈대 = false; 보기.네방향 = false; 보기.동작.재생 = false; 보기.동작.이름 = null; 자세모두(); }
  뼈대그리기(); 상태줄(); 그리기요청();
}
async function 전보기(켬) {
  if (켬 && (!보기.전주소 || 보기.나란히)) return;
  보기.전보기 = 켬;
  상태줄();
  if (켬) await 전불러오기();
  그리기요청();
}
const 전단추 = $("v3before");
전단추.addEventListener("pointerdown", (ev) => { if (ev.button === 0) { 전단추.setPointerCapture(ev.pointerId); 전보기(true); } });
전단추.addEventListener("pointerup", () => 전보기(false));
전단추.addEventListener("pointercancel", () => 전보기(false));
전단추.addEventListener("keydown", (ev) => { if ((ev.key === "Enter") && !ev.repeat) 전보기(true); });
전단추.addEventListener("keyup", (ev) => { if (ev.key === "Enter") 전보기(false); });
$("v3side").addEventListener("click", async () => {
  if (!보기.전주소) return;
  보기.나란히 = !보기.나란히;
  보기.전보기 = false;
  상태줄();
  if (보기.나란히) await 전불러오기();
  그리기요청();
});

function 키를받나(ev) {
  if (!뿌리.isConnected || ev.ctrlKey || ev.metaKey || ev.altKey) return false;
  const t = ev.target;
  if (t && (t.closest("input, select, textarea, [contenteditable]") || t.closest(".overlay:not([hidden])"))) return false;
  const 상자 = document.querySelector(".overlay:not([hidden])");
  return !상자;
}
document.addEventListener("keydown", (ev) => {
  if (!키를받나(ev)) return;
  const 키 = ev.key.length === 1 ? ev.key.toLowerCase() : ev.key;
  if (ev.code === "Space" || 키 === " ") {
    ev.preventDefault();               // 스크롤·단추 누름 대신 전 보기
    if (!ev.repeat) 전보기(true);
    return;
  }
  const 일 = {"1": () => 방향보기("앞"), "2": () => 방향보기("옆"), "3": () => 방향보기("뒤"), "4": () => 방향보기("아래"),
    "5": 시야바꾸기, "f": 처음자리, "h": () => 목록열기(), "Escape": () => 목록열기(false)}[키];
  if (!일 || ev.repeat) return;
  ev.preventDefault();
  일();
});
document.addEventListener("keyup", (ev) => {
  if (ev.code === "Space" || ev.key === " ") { if (보기.전보기) { ev.preventDefault(); 전보기(false); } }
});
window.addEventListener("blur", () => { if (보기.전보기) 전보기(false); });

// ---------------------------------------------------------------- 초당 화면 수 재기(검사용)
let 재는중 = false;
async function 재기(밀리초 = 5000) {
  if (!보기.지금) return null;
  재는중 = true;
  const 시작회전 = 보기.회전.clone(), 시작화면 = 보기.화면수, t0 = performance.now();
  const 돌기 = () => {
    if (!재는중) return;
    const t = performance.now() - t0;
    보기.회전.copy(시작회전).premultiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), t / 1000));
    requestAnimationFrame(돌기);
  };
  돌기();
  그리기요청();
  await new Promise((r) => setTimeout(r, 밀리초));
  재는중 = false;
  const 초 = (performance.now() - t0) / 1000;
  // 한 장을 그리는 데 드는 시간(GPU가 끝날 때까지 기다림): 브라우저가 화면 수를 묶어 두어도 그리기 자체가 빠른지 본다
  const 화소 = new Uint8Array(4), gl = 그리개.getContext(), 횟수 = 30;
  const t1 = performance.now();
  for (let i = 0; i < 횟수; i++) {
    보기.회전.premultiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), 0.05));
    그리기(performance.now());
    gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, 화소);
  }
  const 한장 = (performance.now() - t1) / 횟수;
  보기.회전.copy(시작회전);
  그리기요청();
  let 빈화면 = 0;   // 아무것도 그리지 않을 때 브라우저가 주는 초당 화면 수
  await new Promise((r) => { const t = performance.now(); const f = () => { 빈화면++; if (performance.now() - t < 2000) requestAnimationFrame(f); else r(); }; requestAnimationFrame(f); });
  return {초당화면: Math.round((보기.화면수 - 시작화면) / 초 * 10) / 10, 초: Math.round(초 * 10) / 10,
    한장ms: Math.round(한장 * 10) / 10, 빈화면초당: Math.round(빈화면 / 2 * 10) / 10,
    그림크기: `${그리개.domElement.width}×${그리개.domElement.height}`, 화소배율: 그리개.getPixelRatio()};
}

// ---------------------------------------------------------------- 바깥(앱.js)에 내놓는 것
function 붙이기(자리, 이름, 작업본해시) {
  자리.replaceWith(뿌리);
  상태줄();
  if (!웹지엘) return;
  크기맞추기();
  if (이름 !== 보기.이름) {
    보기.이름 = 이름;
    버리기(보기.지금); 버리기(보기.전);
    보기.지금 = null; 보기.전 = null; 보기.전주소 = null; 모델알림();
    보기.숨김.clear(); 보기.하나 = null; 보기.전보기 = false; 보기.나란히 = false; 보기.갱신중 = false; 보기.상태글 = "";
    보기.동작 = {이름: null, 시각: 0, 재생: false, 마지막: 0}; 보기.네방향 = false; 뼈대그리기();   // W13
    $("v3pop").hidden = true;
    알림("불러오는 중…");
    상태줄();
    보기.해시요청 = 작업본해시;
    모델묻기();
  } else if (작업본해시 !== 보기.해시요청) {
    보기.해시요청 = 작업본해시;   // 작업본이 바뀜: 다시 묻는다(만드는 동안은 마지막 것을 "갱신 중"으로)
    모델묻기();
  }
  그리기요청();
}
window.보기3d = {붙이기, 재기, 방향보기, 처음자리, 이파츠만, 모양정하기, 상태: 보기,
  동작정하기, 동작정보, 리깅단추,   // W13
  미리보기,   // W14
  조각수: (이름) => { const m = 보기.지금 && 보기.지금.파츠.get(이름); if (!m || !m[0]) return null; 조각색넣기(m); return m[0].userData.조각수 ?? null; },   // W11
  // 칠하기.js가 쓰는 안쪽(같은 장면·카메라를 함께 씀)
  내부: {THREE, 뿌리, 캔버스, 씬: () => 씬, 그리개: () => 그리개, 카메라, 카메라놓기, 그리기요청, 옮기기, 거리제한, 상태줄, 웹지엘}};
window.dispatchEvent(new Event("보기3d준비"));
