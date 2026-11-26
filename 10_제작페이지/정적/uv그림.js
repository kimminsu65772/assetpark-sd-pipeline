// 가마우지 제작 페이지 — UV 그림 나란히(W04, 기능명세 1부 5-3절, 2부 6·7단계)
// 3D 보기(보기3d.js) 오른쪽에 지금 파츠의 UV 그림(텍스처 + UV 선)을 둔다.
// - 모델 위 마우스 자리 → UV 그림에 십자. 파츠는 마우스가 올라간 파츠를 따라 바뀌고, "UV 고정"으로 멈춘다("이 파츠만"이면 그 파츠).
// - UV 그림 위 마우스 자리 → 모델의 같은 자리에 점(그 UV 자리를 쓰는 면이 여럿이면 모두).
// - UV 그림 위에서도 붓·지우개로 칠한다. 붓 원에 닿은 UV 삼각형의 면이 표시에 들어간다(칠하기.js의 면칠하기).
// - 칠한 곳은 3D와 같은 색으로 UV에도 보인다. 이음매를 지나는 표시는 양쪽 조각이 모두 보이고, 자리.UV조각에 조각마다 범위가 적힌다.
// UV 좌표는 glTF 그대로(왼쪽 위가 0,0. Blender의 v와는 위아래가 반대). 화소 범위 = UV × 그림 크기.
// 크기·색 숫자는 맨 위 "그림 상수" 한 곳. 색은 디자인 토큰에서 읽는다. 서버(127.0.0.1)에 따로 묻지 않는다(그림은 GLB 안의 텍스처).
import * as THREE from "three";

// ---------------------------------------------------------------- 그림 상수
const 상수 = {
  단계: [6, 7],                 // UV 그림 칸이 있는 단계(2부 18·19절: 3D·UV 위에 칠함)
  그림기본: {6: false, 7: true}, // 처음에 텍스처를 깔지(6단계는 시안대로 UV 선만)
  여백: 0.04,                   // 칸 둘레 여백(칸 크기에 대한 비율)
  칸: 64,                       // UV 찾기 격자(한 변 칸 수)
  십자: 10,                     // 십자 반 길이(화면 화소)
  점크기: 10,                   // 모델 위 점 지름(화면 화소)
  선투명: 0.35, 칠투명: 0.45, 고른투명: 0.7, 후보투명: 0.35,
  확대최대: 32, 휠감도: 0.0015,
  끌기문턱: 4,                  // 이보다 덜 움직이면 "한 번 누름" = 그 자리의 면만
  같은자리: 1e-5,               // UV 꼭짓점이 같은 자리로 볼 거리(조각 나누기)
  점최대: 64,                   // UV 한 자리에 띄울 점 수의 한도
};
const 토큰 = (이름) => getComputedStyle(document.documentElement).getPropertyValue(이름).trim();

// ---------------------------------------------------------------- 화면 요소
const 칸 = document.createElement("div");
칸.className = "view";
칸.id = "uvview";
칸.innerHTML = `<canvas class="uvc" id="uvc" tabindex="-1" aria-label="UV 그림: 휠 확대, 오른쪽 끌기 옮기기, 두 번 눌러 맞춤. 붓을 들면 왼쪽 끌기로 칠하기"></canvas>
<span class="lbl" id="uvlbl">UV 그림</span><span class="lbl2" id="uvst"></span><div class="vmsg" id="uvmsg" hidden></div>`;
const 원 = document.createElement("div");
원.className = "brush";
원.hidden = true;
칸.appendChild(원);
const 도구 = document.createElement("div");
도구.className = "tgrp";
도구.setAttribute("aria-label", "UV 그림");
도구.innerHTML = `<button type="button" class="tb" id="uvlock" title="UV 그림의 파츠를 지금 파츠로 고정(풀면 마우스가 올라간 파츠를 따라감)">UV 고정</button>` +
  `<button type="button" class="tb" id="uvtex" title="UV 그림에 텍스처를 깔기 / UV 선만">UV 텍스처</button>` +
  `<button type="button" class="tb" id="uvfit" title="UV 그림을 칸에 맞춤(UV 그림 위 두 번 누르기와 같음)">UV 맞춤</button>`;
const 캔 = 칸.querySelector("#uvc");
const $ = (id) => (칸.querySelector("#" + id) || 도구.querySelector("#" + id));

// ---------------------------------------------------------------- 상태
const uv = {
  단계: 0, 켜짐: false,
  파츠: null, 고정: false, 그림: true,
  자료: new Map(),        // 파츠 → {삼각(uv 6개씩), 면, 메시번호, 꼭짓점, 메시들, 칸들, 조각, 면삼각, 이미지, 가로, 세로}
  십자: null,             // [u, v] — 모델 위 마우스 자리
  확대: 1, 이동: [0, 0],  // 칸 안의 확대·옮김(화면 화소)
  끌기: null, 붓질: null,
  마지막: null,           // 시험용: 마지막으로 모델에서 맞힌 {파츠, 면, uv}
};
window.uv그림상태 = uv;   // 시험·검사용으로 읽기만

const 보 = () => window.보기3d && window.보기3d.내부;
const 보기상태 = () => window.보기3d && window.보기3d.상태;
const 칠 = () => window.칠하기;
function 보이는파츠(이름) {
  const b = 보기상태();
  return b ? (b.하나 ? 이름 === b.하나 : !b.숨김.has(이름)) : false;
}

// ---------------------------------------------------------------- 파츠마다 UV 자료 만들기(모델이 바뀔 때 한 번)
function 이미지크기(이미지) {
  if (!이미지) return [0, 0];
  return [이미지.naturalWidth || 이미지.videoWidth || 이미지.width || 0, 이미지.naturalHeight || 이미지.videoHeight || 이미지.height || 0];
}
function 자료만들기() {
  uv.자료 = new Map();
  const m = 보기상태() && 보기상태().지금;
  if (!m) return;
  for (const [이름, 메시들] of m.파츠) {
    const 삼각 = [], 면 = [], 메시번호 = [], 꼭짓점 = [];
    let 이미지 = null;
    메시들.forEach((o, mi) => {
      const g = o.geometry, a = g.attributes.uv, f = g.attributes._faceid;
      if (!a || !f) return;
      const 색인 = g.index ? g.index.array : null, n = 색인 ? 색인.length / 3 : a.count / 3;
      for (let t = 0; t < n; t++) {
        const v0 = 색인 ? 색인[t * 3] : t * 3, v1 = 색인 ? 색인[t * 3 + 1] : t * 3 + 1, v2 = 색인 ? 색인[t * 3 + 2] : t * 3 + 2;
        삼각.push(a.getX(v0), a.getY(v0), a.getX(v1), a.getY(v1), a.getX(v2), a.getY(v2));
        면.push(Math.round(f.getX(v0)));
        메시번호.push(mi);
        꼭짓점.push(v0, v1, v2);
      }
      if (!이미지) for (const 재질 of [].concat(o.userData.원래재질 || [])) if (재질 && 재질.map && 재질.map.image) { 이미지 = 재질.map.image; break; }
    });
    if (!면.length) { uv.자료.set(이름, null); continue; }
    const 삼각수 = 면.length, k = 상수.칸;
    // UV 찾기 격자: 칸마다 걸치는 삼각형
    const 칸들 = Array.from({length: k * k}, () => []);
    for (let t = 0; t < 삼각수; t++) {
      const us = [삼각[t * 6], 삼각[t * 6 + 2], 삼각[t * 6 + 4]], vs = [삼각[t * 6 + 1], 삼각[t * 6 + 3], 삼각[t * 6 + 5]];
      const i0 = 칸번호(Math.min(...us)), i1 = 칸번호(Math.max(...us)), j0 = 칸번호(Math.min(...vs)), j1 = 칸번호(Math.max(...vs));
      for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) 칸들[j * k + i].push(t);
    }
    // 조각(UV에서 이어진 삼각형 묶음): 같은 자리의 UV 꼭짓점을 나눠 쓰면 같은 조각
    const 부모 = Int32Array.from({length: 삼각수}, (_, i) => i);
    const 찾기 = (x) => { while (부모[x] !== x) { 부모[x] = 부모[부모[x]]; x = 부모[x]; } return x; };
    const 자리 = new Map(), q = 1 / 상수.같은자리;
    for (let t = 0; t < 삼각수; t++) for (let c = 0; c < 3; c++) {
      const 열쇠 = `${메시번호[t]}:${Math.round(삼각[t * 6 + c * 2] * q)}:${Math.round(삼각[t * 6 + c * 2 + 1] * q)}`;
      const 앞 = 자리.get(열쇠);
      if (앞 === undefined) 자리.set(열쇠, t); else 부모[찾기(t)] = 찾기(앞);
    }
    const 조각 = Int32Array.from({length: 삼각수}, (_, t) => 찾기(t));
    const 면삼각 = new Map();
    for (let t = 0; t < 삼각수; t++) { let l = 면삼각.get(면[t]); if (!l) 면삼각.set(면[t], (l = [])); l.push(t); }
    const [가로, 세로] = 이미지크기(이미지);
    uv.자료.set(이름, {삼각, 면, 메시번호, 꼭짓점, 메시들, 칸들, 조각, 면삼각, 이미지, 가로, 세로, 바탕: null});
  }
}
function 칸번호(x) { return Math.min(상수.칸 - 1, Math.max(0, Math.floor(x * 상수.칸))); }

// ---------------------------------------------------------------- 칸 안 자리 ↔ UV
function 판() {
  // UV 0~1 사각형이 칸 안에 놓이는 자리(화면 화소): {x, y, w, h}
  const w = Math.max(1, 캔.clientWidth), h = Math.max(1, 캔.clientHeight), d = 지금자료();
  const 비율 = d && d.가로 && d.세로 ? d.가로 / d.세로 : 1;
  const 쓸w = w * (1 - 2 * 상수.여백), 쓸h = h * (1 - 2 * 상수.여백);
  const s = Math.min(쓸w / 비율, 쓸h) * uv.확대;
  const rw = s * 비율, rh = s;
  return {x: (w - rw) / 2 + uv.이동[0], y: (h - rh) / 2 + uv.이동[1], w: rw, h: rh};
}
const UV에서화면 = (p, u, v) => [p.x + u * p.w, p.y + v * p.h];
const 화면에서UV = (p, x, y) => [(x - p.x) / p.w, (y - p.y) / p.h];
function 지금자료() { return uv.파츠 ? uv.자료.get(uv.파츠) : null; }

// 그 UV 자리를 덮는 삼각형들(겹친 UV면 여럿)
function 덮는삼각(d, u, v) {
  const 결과 = [];
  if (!d || u < 0 || v < 0 || u > 1 || v > 1) return 결과;
  for (const t of d.칸들[칸번호(v) * 상수.칸 + 칸번호(u)]) {
    const b = 무게(d.삼각, t, u, v);
    if (b) 결과.push([t, b]);
  }
  return 결과;
}
function 무게(삼각, t, u, v) {
  const ax = 삼각[t * 6], ay = 삼각[t * 6 + 1], bx = 삼각[t * 6 + 2], by = 삼각[t * 6 + 3], cx = 삼각[t * 6 + 4], cy = 삼각[t * 6 + 5];
  const 넓이 = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay);
  if (Math.abs(넓이) < 1e-14) return null;
  const w1 = ((u - ax) * (cy - ay) - (cx - ax) * (v - ay)) / 넓이, w2 = ((bx - ax) * (v - ay) - (u - ax) * (by - ay)) / 넓이, w0 = 1 - w1 - w2;
  const e = -1e-9;
  return w0 >= e && w1 >= e && w2 >= e ? [w0, w1, w2] : null;
}
// 화면 화소의 원(cx, cy, r)에 닿는 삼각형의 면 → 담(파츠 → Set)
function 원에닿는면(d, 파츠, p, cx, cy, r, 담) {
  const [u0, v0] = 화면에서UV(p, cx - r, cy - r), [u1, v1] = 화면에서UV(p, cx + r, cy + r);
  if (u1 < 0 || v1 < 0 || u0 > 1 || v0 > 1) return;
  const k = 상수.칸, 본 = new Set();
  for (let j = 칸번호(v0); j <= 칸번호(v1); j++) for (let i = 칸번호(u0); i <= 칸번호(u1); i++) for (const t of d.칸들[j * k + i]) {
    if (본.has(t)) continue;
    본.add(t);
    if (삼각원닿음(d.삼각, t, p, cx, cy, r)) {
      if (!담.has(파츠)) 담.set(파츠, new Set());
      담.get(파츠).add(d.면[t]);
    }
  }
}
function 삼각원닿음(삼각, t, p, cx, cy, r) {
  const q = [0, 1, 2].map((c) => UV에서화면(p, 삼각[t * 6 + c * 2], 삼각[t * 6 + c * 2 + 1]));
  const [uu, vv] = 화면에서UV(p, cx, cy);
  if (무게(삼각, t, uu, vv)) return true;   // 원 가운데가 삼각형 안
  for (let c = 0; c < 3; c++) {
    const [ax, ay] = q[c], [bx, by] = q[(c + 1) % 3];
    const dx = bx - ax, dy = by - ay, L = dx * dx + dy * dy;
    const s = L ? Math.max(0, Math.min(1, ((cx - ax) * dx + (cy - ay) * dy) / L)) : 0;
    if ((ax + s * dx - cx) ** 2 + (ay + s * dy - cy) ** 2 <= r * r) return true;
  }
  return false;
}

// ---------------------------------------------------------------- 그리기
let 요청 = false;
function 그리기요청() { if (!요청 && uv.켜짐) { 요청 = true; requestAnimationFrame(그리기); } }
function 크기맞추기() {
  const 배율 = Math.min(devicePixelRatio || 1, 2);
  const w = Math.max(1, Math.round(캔.clientWidth * 배율)), h = Math.max(1, Math.round(캔.clientHeight * 배율));
  if (캔.width !== w || 캔.height !== h) { 캔.width = w; 캔.height = h; for (const d of uv.자료.values()) if (d) d.바탕 = null; }
  return 배율;
}
function 바탕그리기(d, p, 배율) {
  // 텍스처 + UV 선(바뀔 때만 다시 그림)
  const 열쇠 = `${캔.width}x${캔.height}|${p.x}|${p.y}|${p.w}|${uv.그림}`;
  if (d.바탕 && d.바탕.열쇠 === 열쇠) return d.바탕.캔;
  const c = (d.바탕 && d.바탕.캔) || document.createElement("canvas");
  c.width = 캔.width; c.height = 캔.height;
  const g = c.getContext("2d");
  g.setTransform(배율, 0, 0, 배율, 0, 0);
  g.clearRect(0, 0, c.width, c.height);
  g.fillStyle = 토큰("--c-surface-1");
  g.fillRect(p.x, p.y, p.w, p.h);
  if (uv.그림 && d.이미지) { g.imageSmoothingEnabled = uv.확대 < 4; g.drawImage(d.이미지, p.x, p.y, p.w, p.h); }
  g.strokeStyle = 토큰("--c-text-2");
  g.globalAlpha = uv.그림 && d.이미지 ? 상수.선투명 : 1;
  g.lineWidth = 1;
  g.beginPath();
  for (let t = 0; t < d.면.length; t++) {
    const [ax, ay] = UV에서화면(p, d.삼각[t * 6], d.삼각[t * 6 + 1]);
    g.moveTo(ax, ay);
    g.lineTo(...UV에서화면(p, d.삼각[t * 6 + 2], d.삼각[t * 6 + 3]));
    g.lineTo(...UV에서화면(p, d.삼각[t * 6 + 4], d.삼각[t * 6 + 5]));
    g.closePath();
  }
  g.stroke();
  g.globalAlpha = 1;
  g.strokeStyle = 토큰("--c-line");
  g.strokeRect(p.x, p.y, p.w, p.h);
  d.바탕 = {캔: c, 열쇠};
  return c;
}
// 부위(W05): 고른 부위가 있으면 그 조각만 밝게, 나머지와 숨긴 부위는 바탕색으로 덮는다
let 가리개 = null;
function 부위가리개(g, d, p) {
  const 값 = window.부위 && window.부위.면모양(uv.파츠);
  if (!값) return;
  if (!가리개) 가리개 = document.createElement("canvas");
  가리개.width = 캔.width; 가리개.height = 캔.height;
  const h = 가리개.getContext("2d"), 배율 = 캔.width / Math.max(1, 캔.clientWidth);
  h.setTransform(배율, 0, 0, 배율, 0, 0);
  const 바탕 = 토큰("--c-canvas");
  const 칠 = (같은값, 투명, 지우기) => {
    h.globalCompositeOperation = 지우기 ? "destination-out" : "source-over";
    h.globalAlpha = 투명; h.fillStyle = 바탕;
    h.beginPath();
    for (let t = 0; t < d.면.length; t++) {
      if (!같은값(값(d.면[t]))) continue;
      h.moveTo(...UV에서화면(p, d.삼각[t * 6], d.삼각[t * 6 + 1]));
      h.lineTo(...UV에서화면(p, d.삼각[t * 6 + 2], d.삼각[t * 6 + 3]));
      h.lineTo(...UV에서화면(p, d.삼각[t * 6 + 4], d.삼각[t * 6 + 5]));
      h.closePath();
    }
    h.fill();
  };
  h.clearRect(0, 0, 캔.clientWidth, 캔.clientHeight);
  h.globalAlpha = window.부위.UV흐림; h.fillStyle = 바탕;
  h.fillRect(p.x, p.y, p.w, p.h);                 // 판 전체를 흐리게
  칠((v) => v === 0, 1, true);                    // 밝을 조각은 뚫고(UV가 겹친 곳도 밝게)
  칠((v) => v === 2, window.부위.UV숨김, false);  // 숨긴 부위는 더 짙게
  h.globalCompositeOperation = "source-over"; h.globalAlpha = 1;
  g.save(); g.setTransform(1, 0, 0, 1, 0, 0); g.drawImage(가리개, 0, 0); g.restore();
}
function 그리기() {
  요청 = false;
  if (!uv.켜짐 || !칸.isConnected) return;
  const 배율 = 크기맞추기(), g = 캔.getContext("2d"), d = 지금자료(), p = 판();
  g.setTransform(1, 0, 0, 1, 0, 0);
  g.fillStyle = 토큰("--c-canvas");
  g.fillRect(0, 0, 캔.width, 캔.height);
  상태줄();
  if (!d) return;
  g.drawImage(바탕그리기(d, p, 배율), 0, 0);
  g.setTransform(배율, 0, 0, 배율, 0, 0);
  부위가리개(g, d, p);
  // 칠한 곳(칠하기.js의 겹침과 같은 모음·같은 색)
  const 모음 = 칠() && 칠().겹침모음 ? 칠().겹침모음() : null;
  if (모음) for (const [종류, 색이름, 투명] of [["후보", "--c-accent", 상수.후보투명], ["사용자", "--c-danger", 상수.칠투명], ["고른", "--c-warn", 상수.고른투명]]) {
    const 면 = 모음[종류] && 모음[종류].get(uv.파츠);
    if (!면 || !면.size) continue;
    g.fillStyle = 토큰(색이름);
    g.globalAlpha = 투명;
    g.beginPath();
    for (const f of 면) for (const t of d.면삼각.get(f) || []) {
      g.moveTo(...UV에서화면(p, d.삼각[t * 6], d.삼각[t * 6 + 1]));
      g.lineTo(...UV에서화면(p, d.삼각[t * 6 + 2], d.삼각[t * 6 + 3]));
      g.lineTo(...UV에서화면(p, d.삼각[t * 6 + 4], d.삼각[t * 6 + 5]));
      g.closePath();
    }
    g.fill();
  }
  g.globalAlpha = 1;
  // 십자(모델 위 마우스 자리)
  if (uv.십자) {
    const [x, y] = UV에서화면(p, uv.십자[0], uv.십자[1]), r = 상수.십자;
    g.lineWidth = 3; g.strokeStyle = 토큰("--c-canvas");
    g.beginPath(); g.moveTo(x - r, y); g.lineTo(x + r, y); g.moveTo(x, y - r); g.lineTo(x, y + r); g.stroke();
    g.lineWidth = 1.5; g.strokeStyle = 토큰("--c-accent");
    g.beginPath(); g.moveTo(x - r, y); g.lineTo(x + r, y); g.moveTo(x, y - r); g.lineTo(x, y + r); g.stroke();
  }
}
function 상태줄() {
  const d = 지금자료(), b = 보기상태();
  let 글 = "";
  if (!b || !b.지금) 글 = "";
  else if (!uv.파츠) 글 = "모델 위에 마우스를 올리면 그 파츠의 UV";
  else {
    const 크기 = d && d.가로 ? `${d.가로}×${d.세로}` : d ? "텍스처 없음" : "UV 없음";
    글 = `${uv.파츠} · ${크기}${b.하나 ? " · 이 파츠만" : uv.고정 ? " · 고정" : ""}${보이는파츠(uv.파츠) ? "" : " · 숨김(칠할 수 없음)"}${uv.확대 > 1.001 ? ` · ${uv.확대.toFixed(1)}배` : ""}`;
  }
  $("uvst").textContent = 글;
  $("uvst").title = 글;
  $("uvlbl").textContent = uv.그림 ? "UV 그림 (텍스처 입힘)" : "UV (선만)";
  const 메시지 = !b || !b.지금 ? "" : uv.파츠 && !d ? `${uv.파츠}에는 UV가 없습니다.` : "";
  $("uvmsg").textContent = 메시지;
  $("uvmsg").hidden = !메시지;
  $("uvlock").classList.toggle("on", uv.고정 || Boolean(b && b.하나));
  $("uvlock").setAttribute("aria-pressed", String(uv.고정));
  $("uvtex").classList.toggle("on", uv.그림);
  $("uvtex").setAttribute("aria-pressed", String(uv.그림));
  for (const id of ["uvlock", "uvtex", "uvfit"]) $(id).disabled = !b || !b.지금;
  const 이유 = 칠못함이유();
  칸.classList.toggle("painting", 칠() && 칠().상태.도구 !== "보기" && !이유);
}
function 파츠바꾸기(이름) {
  if (이름 === uv.파츠) return;
  uv.파츠 = 이름; uv.확대 = 1; uv.이동 = [0, 0];
  그리기요청();
}
function 처음파츠() {
  const b = 보기상태();
  if (!b || !b.지금) { uv.파츠 = null; return; }
  if (b.하나) { 파츠바꾸기(b.하나); return; }
  if (uv.파츠 && uv.자료.has(uv.파츠)) return;
  const 첫 = [...uv.자료.keys()].find((n) => uv.자료.get(n) && 보이는파츠(n)) || [...uv.자료.keys()][0] || null;
  uv.파츠 = null;
  파츠바꾸기(첫);
}

// ---------------------------------------------------------------- 모델 위 점(UV 그림 위 마우스 자리)
let 점들 = null;
function 점만들기() {
  if (점들 || !보()) return 점들;
  const 동그라미 = document.createElement("canvas");
  동그라미.width = 동그라미.height = 64;
  const g = 동그라미.getContext("2d");
  g.fillStyle = 토큰("--c-canvas"); g.beginPath(); g.arc(32, 32, 30, 0, Math.PI * 2); g.fill();
  g.fillStyle = 토큰("--c-accent"); g.beginPath(); g.arc(32, 32, 22, 0, Math.PI * 2); g.fill();
  const 기하 = new THREE.BufferGeometry();
  기하.setAttribute("position", new THREE.BufferAttribute(new Float32Array(상수.점최대 * 3), 3));
  기하.setDrawRange(0, 0);
  const 재질 = new THREE.PointsMaterial({size: 상수.점크기 * Math.min(devicePixelRatio || 1, 2), sizeAttenuation: false, map: new THREE.CanvasTexture(동그라미),
    transparent: true, alphaTest: 0.1, depthTest: false, depthWrite: false});
  점들 = new THREE.Points(기하, 재질);
  점들.name = "UV점";
  점들.frustumCulled = false;
  점들.renderOrder = 10;
  점들.raycast = () => {};
  점들.userData.고르기빼기 = true;   // 칠하기.js의 고르기 그림에 들어가지 않게
  점들.visible = false;
  보().씬().add(점들);
  return 점들;
}
function 점보이기(자리들) {
  const p = 점만들기();
  if (!p) return;
  const a = p.geometry.attributes.position, n = Math.min(자리들.length, 상수.점최대);
  for (let i = 0; i < n; i++) a.setXYZ(i, 자리들[i].x, 자리들[i].y, 자리들[i].z);
  a.needsUpdate = true;
  p.geometry.setDrawRange(0, n);
  p.visible = n > 0;
  보().그리기요청();
}
// UV 자리 → 그 자리를 쓰는 면마다 모델 위 자리(스킨 반영, 세상 좌표)
function UV자리의점(u, v) {
  const d = 지금자료(), 결과 = [];
  if (!d) return 결과;
  const a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3();
  for (const [t, w] of 덮는삼각(d, u, v)) {
    const o = d.메시들[d.메시번호[t]];
    o.getVertexPosition(d.꼭짓점[t * 3], a); o.getVertexPosition(d.꼭짓점[t * 3 + 1], b); o.getVertexPosition(d.꼭짓점[t * 3 + 2], c);
    o.updateWorldMatrix(true, false);
    const 점 = a.multiplyScalar(w[0]).addScaledVector(b, w[1]).addScaledVector(c, w[2]).applyMatrix4(o.matrixWorld);
    결과.push({파츠: uv.파츠, 면: d.면[t], 점: 점.clone()});
  }
  return 결과;
}

// ---------------------------------------------------------------- 모델 위 마우스 → 십자
const 광선 = new THREE.Raycaster();
function 모델에서맞힘(x, y) {
  // x, y: 3D 캔버스 안 CSS 화소
  const 안쪽 = 보(), b = 보기상태();
  if (!안쪽 || !b || !b.지금 || b.나란히 || b.전보기) return null;
  const r = 안쪽.캔버스.getBoundingClientRect();
  안쪽.카메라놓기(r.width, r.height);
  광선.setFromCamera(new THREE.Vector2((x / r.width) * 2 - 1, -(y / r.height) * 2 + 1), 안쪽.카메라());
  const 대상 = [];
  for (const [이름, 메시들] of b.지금.파츠) if (보이는파츠(이름)) for (const o of 메시들) if (o.visible) 대상.push(o);
  const h = 광선.intersectObjects(대상, false)[0];
  if (!h || !h.uv) return null;
  const 파츠 = h.object.userData.파츠, f = h.object.geometry.attributes._faceid;
  return {파츠, 면: f ? Math.round(f.getX(h.face.a)) : -1, uv: [h.uv.x, h.uv.y], 점: h.point.toArray()};
}
let 모델마우스 = null, 모델요청 = false;
function 모델마우스처리() {
  모델요청 = false;
  const ev = 모델마우스;
  if (!ev || !uv.켜짐) return;
  const r = 보().캔버스.getBoundingClientRect();
  const h = 모델에서맞힘(ev.clientX - r.left, ev.clientY - r.top);
  uv.마지막 = h;
  const b = 보기상태();
  if (h && !uv.고정 && !b.하나) 파츠바꾸기(h.파츠);
  uv.십자 = h && h.파츠 === uv.파츠 ? h.uv : null;
  그리기요청();
}

// ---------------------------------------------------------------- UV 그림 위 마우스: 점, 붓, 옮기기, 확대
function 칠못함이유() {
  const c = 칠();
  if (!c) return "칠하기를 불러오는 중입니다";
  const 이유 = c.칠못함이유();
  if (이유) return 이유;
  if (!uv.파츠 || !지금자료()) return "이 파츠에는 UV가 없습니다";
  if (!보이는파츠(uv.파츠)) return "숨긴 파츠에는 칠할 수 없습니다";
  return "";
}
function 캔자리(ev) { const r = 캔.getBoundingClientRect(); return [ev.clientX - r.left, ev.clientY - r.top]; }
function 원보이기(ev) {
  const c = 칠();
  if (!ev || !c || c.상태.도구 === "보기" || 칠못함이유()) { 원.hidden = true; return; }
  const [x, y] = 캔자리(ev), r = c.상태.붓;
  원.hidden = false;
  원.classList.toggle("erase", c.상태.도구 === "지우개");
  원.style.width = 원.style.height = `${r * 2}px`;
  원.style.left = `${x - r}px`;
  원.style.top = `${y - r}px`;
}
function UV점갱신(ev) {
  const [x, y] = 캔자리(ev), [u, v] = 화면에서UV(판(), x, y);
  점보이기(UV자리의점(u, v).map((x) => x.점));
}
function 붓찍기(x, y) {
  const d = 지금자료();
  if (d) 원에닿는면(d, uv.파츠, 판(), x, y, 칠().상태.붓, uv.붓질.담);
}
캔.addEventListener("contextmenu", (ev) => ev.preventDefault());
캔.addEventListener("pointerdown", (ev) => {
  const c = 칠(), [x, y] = 캔자리(ev);
  const 붓듦 = c && c.상태.도구 !== "보기" && ev.button === 0 && !ev.shiftKey;
  if (붓듦) {
    ev.preventDefault();
    const 이유 = 칠못함이유();
    if (이유) { c.상태글(이유); return; }
    캔.setPointerCapture(ev.pointerId);
    uv.붓질 = {id: ev.pointerId, 지우개: c.상태.도구 === "지우개", x, y, 처음x: x, 처음y: y, 움직임: 0, 담: new Map()};
    붓찍기(x, y);
    c.미리보기(uv.붓질.지우개, uv.붓질.담);
    return;
  }
  if (ev.button > 2) return;
  ev.preventDefault();
  캔.setPointerCapture(ev.pointerId);
  uv.끌기 = {id: ev.pointerId, x: ev.clientX, y: ev.clientY};
});
캔.addEventListener("pointermove", (ev) => {
  원보이기(ev);
  if (uv.붓질 && ev.pointerId === uv.붓질.id) {
    const [x, y] = 캔자리(ev), s = uv.붓질, dx = x - s.x, dy = y - s.y;
    const 걸음 = Math.max(1, 칠().상태.붓 / 2), n = Math.ceil(Math.hypot(dx, dy) / 걸음);
    for (let i = 1; i <= n; i++) 붓찍기(s.x + dx * i / n, s.y + dy * i / n);   // 빠르게 끌어도 빈틈 없이
    s.x = x; s.y = y;
    s.움직임 = Math.max(s.움직임, Math.hypot(x - s.처음x, y - s.처음y));
    칠().미리보기(s.지우개, s.담);
  } else if (uv.끌기 && ev.pointerId === uv.끌기.id) {
    uv.이동[0] += ev.clientX - uv.끌기.x; uv.이동[1] += ev.clientY - uv.끌기.y;
    uv.끌기.x = ev.clientX; uv.끌기.y = ev.clientY;
    그리기요청();
  }
  if (!uv.끌기) UV점갱신(ev);
});
function 끝(ev) {
  if (uv.붓질 && ev.pointerId === uv.붓질.id) {
    const s = uv.붓질;
    uv.붓질 = null;
    let 담 = s.담;
    if (s.움직임 < 상수.끌기문턱) {
      // 한 번 누름: 그 자리를 쓰는 면만(UV가 겹쳐 여럿이면 모두)
      const [u, v] = 화면에서UV(판(), s.처음x, s.처음y);
      담 = new Map();
      for (const x of UV자리의점(u, v)) { if (!담.has(x.파츠)) 담.set(x.파츠, new Set()); 담.get(x.파츠).add(x.면); }
    }
    칠().미리보기(s.지우개, null);
    칠().면칠하기(담, s.지우개);
  }
  if (uv.끌기 && ev.pointerId === uv.끌기.id) uv.끌기 = null;
}
캔.addEventListener("pointerup", 끝);
캔.addEventListener("pointercancel", 끝);
캔.addEventListener("pointerleave", () => { 원.hidden = true; if (!uv.붓질) 점보이기([]); });
캔.addEventListener("dblclick", (ev) => { if (!칠() || 칠().상태.도구 === "보기") 맞춤(); });
캔.addEventListener("wheel", (ev) => {
  ev.preventDefault();
  const c = 칠();
  if (ev.shiftKey && c && c.상태.도구 !== "보기") { c.붓바꾸기(ev.deltaY || ev.deltaX); 원보이기(ev); return; }
  const 단위 = ev.deltaMode === 1 ? 16 : ev.deltaMode === 2 ? 400 : 1;
  const 새 = Math.min(상수.확대최대, Math.max(1, uv.확대 * Math.exp(-ev.deltaY * 단위 * 상수.휠감도)));
  // 마우스 아래 UV 자리가 제자리에 남도록
  const [x, y] = 캔자리(ev), 전 = 판(), [u, v] = 화면에서UV(전, x, y);
  uv.확대 = 새;
  const 후 = 판();
  uv.이동[0] += x - (후.x + u * 후.w); uv.이동[1] += y - (후.y + v * 후.h);
  if (새 === 1) uv.이동 = [0, 0];
  그리기요청();
}, {passive: false});
function 맞춤() { uv.확대 = 1; uv.이동 = [0, 0]; 그리기요청(); }

$("uvlock").addEventListener("click", () => { uv.고정 = !uv.고정; 그리기요청(); });
$("uvtex").addEventListener("click", () => { uv.그림 = !uv.그림; 그리기요청(); });
$("uvfit").addEventListener("click", 맞춤);

// ---------------------------------------------------------------- 3D 보기에 잇기
function 잇기() {
  const 안쪽 = 보();
  if (!안쪽 || 잇기.됨) return;
  잇기.됨 = true;
  안쪽.캔버스.addEventListener("pointermove", (ev) => {
    if (ev.buttons & 6) return;   // 돌리기·옮기기 중에는 묻지 않는다
    모델마우스 = ev;
    if (!모델요청) { 모델요청 = true; requestAnimationFrame(모델마우스처리); }
  });
  안쪽.캔버스.addEventListener("pointerleave", () => { 모델마우스 = null; if (uv.십자) { uv.십자 = null; 그리기요청(); } });
  new ResizeObserver(그리기요청).observe(칸);
}
window.addEventListener("보기3d모델", () => { 자료만들기(); 처음파츠(); 점보이기([]); uv.십자 = null; 그리기요청(); });
window.addEventListener("칠하기겹침", 그리기요청);
window.addEventListener("부위바뀜", 그리기요청);
// 파츠 숨김·이 파츠만·도구가 바뀌면 다시 그린다(단추를 누른 뒤)
document.addEventListener("click", () => { if (uv.켜짐) { const b = 보기상태(); if (b && b.하나 && b.하나 !== uv.파츠) 파츠바꾸기(b.하나); 그리기요청(); } });
document.addEventListener("keyup", () => { if (uv.켜짐) 그리기요청(); });

// ---------------------------------------------------------------- 바깥(앱.js·칠하기.js)에 내놓는 것
function 붙이기(단계) {
  잇기();
  const 안쪽 = 보();
  const 켬 = Boolean(안쪽) && 상수.단계.includes(단계);
  if (단계 !== uv.단계) { uv.그림 = 상수.그림기본[단계] ?? true; uv.고정 = false; }
  uv.단계 = 단계;
  uv.켜짐 = 켬;
  if (!켬) { 칸.remove(); 도구.remove(); 점보이기([]); return; }
  const 줄 = 안쪽.뿌리.querySelector(".vrow"), 도구줄 = 안쪽.뿌리.querySelector(".tools");
  if (칸.parentNode !== 줄) 줄.appendChild(칸);
  if (도구.parentNode !== 도구줄) 도구줄.appendChild(도구);
  if (!uv.자료.size) 자료만들기();
  처음파츠();
  그리기요청();
}
// 표시의 면 → 자리.UV(파츠 → [[x1,y1],[x2,y2]] 화소 범위, 2-1)와 조각마다 범위(이음매를 지나면 2개 이상)
function UV범위(면모음) {
  const UV = {}, 조각 = {};
  for (const [파츠, 면] of Object.entries(면모음 || {})) {
    const d = uv.자료.get(파츠);
    if (!d || !d.가로) continue;
    const 묶음 = new Map();
    for (const f of 면) for (const t of d.면삼각.get(f) || []) {
      const k = d.조각[t];
      let b = 묶음.get(k);
      if (!b) 묶음.set(k, (b = [Infinity, Infinity, -Infinity, -Infinity]));
      for (let c = 0; c < 3; c++) {
        const x = d.삼각[t * 6 + c * 2] * d.가로, y = d.삼각[t * 6 + c * 2 + 1] * d.세로;
        b[0] = Math.min(b[0], x); b[1] = Math.min(b[1], y); b[2] = Math.max(b[2], x); b[3] = Math.max(b[3], y);
      }
    }
    if (!묶음.size) continue;
    const 정수 = (b) => [[Math.max(0, Math.floor(b[0])), Math.max(0, Math.floor(b[1]))], [Math.min(d.가로 - 1, Math.ceil(b[2])), Math.min(d.세로 - 1, Math.ceil(b[3]))]];
    const 모두 = [...묶음.values()];
    UV[파츠] = 정수([Math.min(...모두.map((b) => b[0])), Math.min(...모두.map((b) => b[1])), Math.max(...모두.map((b) => b[2])), Math.max(...모두.map((b) => b[3]))]);
    if (모두.length > 1) 조각[파츠] = 모두.map(정수);
  }
  return {UV, 조각};
}
window.uv그림 = {붙이기, 켜짐: () => uv.켜짐, UV범위, 상태: uv,
  // 시험용: 3D 캔버스 자리에서 맞힌 {파츠, 면, uv}, UV 자리를 쓰는 면과 모델 위 점, UV 자리의 화면(UV 캔버스 안) 자리
  시험_모델에서: (x, y) => 모델에서맞힘(x, y),
  시험_UV에서: (u, v) => UV자리의점(u, v).map((x) => ({파츠: x.파츠, 면: x.면, 점: x.점.toArray()})),
  시험_화면자리: (u, v) => UV에서화면(판(), u, v),
  시험_파츠: (이름) => { uv.고정 = true; 파츠바꾸기(이름); }};
window.dispatchEvent(new Event("uv그림준비"));
