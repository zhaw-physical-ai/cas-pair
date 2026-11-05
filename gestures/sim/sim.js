// SO-101 arm in MuJoCo (WebAssembly), rendered with three.js, driven by gesture labels.
// Contract: window.sim.command(label), window.sim.qpos(), window.sim.reset().
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import loadMujoco from 'mujoco';

const LABELS = ['left', 'right', 'up', 'down', 'circle', 'idle'];
const ARM = ['shoulder_pan', 'shoulder_lift', 'elbow_flex', 'wrist_flex', 'wrist_roll', 'gripper'];
const PAN_STEP = 20 * Math.PI / 180;   // left/right step
const SLEW = 0.7;                      // rad/s: how fast targets move, for smooth motion
const GRIPPER_OPEN = 1.2, GRIPPER_CLOSED = 0.0;
// up/down walk through these [shoulder_lift, elbow_flex, wrist_flex] poses: the gripper tip stays
// 22 cm in front of the base and points down (as far as the wrist allows), at these heights:
//   2, 6, 10, 14, 18, 22, 26 cm above the table. Solved offline with MuJoCo forward kinematics.
const LEVELS = [
  [+0.045, +0.360, +1.293],
  [-0.031, +0.147, +1.581],
  [-0.261, +0.124, +1.658],
  [-0.497, +0.114, +1.658],
  [-0.640, +0.023, +1.658],
  [-0.695, -0.136, +1.658],
  [-0.671, -0.350, +1.658],
];
const HOME_LEVEL = 3;

// ---- command state: what the arm should do; the controls slew toward it every physics step ----
const state = { pan: 0, level: HOME_LEVEL, open: false };
let mj = null, model = null, data = null;
let ctrlLo = ARM.map(() => -Infinity), ctrlHi = ARM.map(() => Infinity);
const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));

function goal() {
  const [lift, elbow, wrist] = LEVELS[state.level];
  const g = [state.pan, lift, elbow, wrist, 0, state.open ? GRIPPER_OPEN : GRIPPER_CLOSED];
  return g.map((v, i) => clamp(v, ctrlLo[i], ctrlHi[i]));
}

function command(label, p = null, source = 'sim.command') {
  label = String(label ?? '').trim().toLowerCase();
  if (!LABELS.includes(label)) { console.warn('sim.command: unknown label', label); return false; }
  if (label === 'left') state.pan = clamp(state.pan - PAN_STEP, ctrlLo[0], ctrlHi[0]);
  if (label === 'right') state.pan = clamp(state.pan + PAN_STEP, ctrlLo[0], ctrlHi[0]);
  if (label === 'up') state.level = Math.min(LEVELS.length - 1, state.level + 1);
  if (label === 'down') state.level = Math.max(0, state.level - 1);
  if (label === 'circle') state.open = !state.open;
  ui.showLabel(label, p, source);
  return true;
}

function qpos() {
  const out = {};
  if (!model) return out;
  const adr = model.jnt_qposadr, q = data.qpos;
  for (const [name, j] of jointIds) out[name] = q[adr[j]];
  return out;
}

function reset() {
  Object.assign(state, { pan: 0, level: HOME_LEVEL, open: false });
  if (!model) return;
  mj.mj_resetData(model, data);
  const g = goal(), q = data.qpos, c = data.ctrl, adr = model.jnt_qposadr;
  ARM.forEach((name, i) => { q[adr[jointIds.get(name)]] = g[i]; c[actIds[i]] = g[i]; });
  mj.mj_forward(model, data);
}

let readyResolve;
window.sim = { command, qpos, reset, labels: LABELS, ready: new Promise(r => (readyResolve = r)) };   // resolves true once running

// ---- UI ----
const $ = id => document.getElementById(id);
const ui = {
  lastAt: 0,
  showLabel(label, p, source) {
    $('label').textContent = label;
    $('prob').textContent = p == null ? '' : `p = ${Number(p).toFixed(2)}`;
    $('source').textContent = source;
    this.lastAt = performance.now();
    const b = document.querySelector(`button[data-label="${label}"]`);
    if (b) { b.classList.add('hit'); setTimeout(() => b.classList.remove('hit'), 250); }
  },
  status(text, kind = '') { const s = $('status'); s.textContent = text; s.className = kind; },
  tick(now, inTarget) {
    $('age').textContent = this.lastAt ? `${((now - this.lastAt) / 1000).toFixed(1)} s ago` : '';
    $('goal').classList.toggle('done', inTarget);
    $('goal').textContent = inTarget ? 'cube in target' : 'goal: push the red cube onto the green square';
  },
};

for (const b of document.querySelectorAll('button[data-label]')) b.onclick = () => command(b.dataset.label, null, 'button');
$('reset').onclick = () => reset();
const KEYS = { ArrowLeft: 'left', ArrowRight: 'right', ArrowUp: 'up', ArrowDown: 'down', c: 'circle', C: 'circle' };
window.addEventListener('keydown', e => {
  if (e.repeat || e.ctrlKey || e.metaKey || e.altKey) return;
  if (KEYS[e.key]) { e.preventDefault(); command(KEYS[e.key], null, 'keyboard'); }
  else if (e.key === 'r' || e.key === 'R') reset();
});

// from a parent page when iframed: postMessage({type: 'gesture', label, p})
window.addEventListener('message', e => {
  const m = e.data;
  if (m && m.type === 'gesture') command(m.label, m.p, 'postMessage');
});

// live: ?channel=<name> -> long-poll /api/live/<name>/next?after=<seq>, events {"seq","label","p","t"}
// (long-polling, not EventSource: tunnels and proxies such as Cloudflare buffer event streams)
const channel = new URLSearchParams(location.search).get('channel');
if (channel) {
  ui.status(`live "${channel}": connecting`, 'wait');
  const url = `/api/live/${encodeURIComponent(channel)}/next`;
  (async function poll(after = -1) {
    for (;;) {
      try {
        const r = await fetch(`${url}?after=${after}`, { cache: 'no-store' });
        if (!r.ok) throw new Error(r.status);
        const j = await r.json();
        ui.status(`live "${channel}": connected`, 'ok');
        for (const m of j.events) command(m.label, m.p, `live "${channel}"`);
        after = j.seq;
      } catch (e) {
        ui.status(`live "${channel}": reconnecting`, 'bad');
        await new Promise(res => setTimeout(res, 2000));
      }
    }
  })();
} else {
  ui.status('keyboard / buttons (add ?channel=NAME for live)', '');
}

// ---- three.js scene ----
// without WebGL the physics and window.sim still run, there is just nothing to see
let renderer = null, glError = null;
try {
  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  $('view').appendChild(renderer.domElement);
} catch (err) {
  glError = 'WebGL is not available in this browser, so the 3D view is off (the simulation still runs).';
}

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xdde4ec);
const camera = new THREE.PerspectiveCamera(45, 1, 0.01, 20);
camera.up.set(0, 0, 1);                      // MuJoCo is z-up
camera.position.set(-0.5, 0.2, 0.42);       // behind the arm: screen left = arm's left
const controls = new OrbitControls(camera, renderer ? renderer.domElement : document.body);
controls.target.set(0.1, -0.03, 0.12);
controls.enableDamping = true;
controls.update();

scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8070, 1.6));
const sun = new THREE.DirectionalLight(0xffffff, 2.0);
sun.position.set(0.5, 0.6, 1.5);
sun.target.position.set(0.12, 0, 0);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -0.6, right: 0.6, top: 0.6, bottom: -0.6, near: 0.1, far: 4 });
sun.shadow.bias = -0.0005;
scene.add(sun, sun.target);

function resize() {
  const w = window.innerWidth, h = window.innerHeight;
  renderer?.setSize(w, h); camera.aspect = w / h;
  // portrait (phones): widen the vertical fov so the arm still fits horizontally
  camera.fov = camera.aspect >= 1.2 ? 45 : 2 * Math.atan(Math.tan(Math.PI / 8) * 1.2 / camera.aspect) * 180 / Math.PI;
  camera.updateProjectionMatrix();
}
window.addEventListener('resize', resize); resize();

// ---- MuJoCo model ----
let jointIds, actIds, targetGeom = -1, cubeBody = -1, ts = 0.005;
const meshes = [];   // [geomId, THREE.Mesh]

async function fetchBytes(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  return new Uint8Array(await r.arrayBuffer());
}

async function loadModel() {
  const base = new URL('model/', import.meta.url);
  const arm = await (await fetch(new URL('so101.xml', base))).text();
  const meshFiles = [...arm.matchAll(/file="([^"]+\.stl)"/g)].map(m => m[1]);
  const meshdir = (arm.match(/meshdir="([^"]+)"/) || [, ''])[1];
  const files = ['scene.xml', 'so101.xml', ...meshFiles.map(f => `${meshdir}/${f}`)];
  const bytes = await Promise.all(files.map(f => fetchBytes(new URL(f, base))));
  const vfs = new mj.MjVFS();
  files.forEach((f, i) => vfs.addBuffer(f, bytes[i]));
  try { model = mj.MjModel.from_xml_path('scene.xml', vfs); } finally { vfs.delete(); }
  data = new mj.MjData(model);
  ts = model.opt.timestep;
}

function buildScene() {
  const O = mj.mjtObj;
  const id = (type, name) => mj.mj_name2id(model, O[type].value, name);
  jointIds = new Map(ARM.map(n => [n, id('mjOBJ_JOINT', n)]));
  actIds = ARM.map(n => id('mjOBJ_ACTUATOR', n));
  const cr = model.actuator_ctrlrange;
  ctrlLo = actIds.map(a => cr[2 * a]); ctrlHi = actIds.map(a => cr[2 * a + 1]);
  targetGeom = id('mjOBJ_GEOM', 'target'); cubeBody = id('mjOBJ_BODY', 'cube');

  const T = mj.mjtGeom;
  const type = model.geom_type, size = model.geom_size, group = model.geom_group;
  const dataid = model.geom_dataid, matid = model.geom_matid, rgbaG = model.geom_rgba, rgbaM = model.mat_rgba;
  const meshCache = new Map();
  for (let g = 0; g < model.ngeom; g++) {
    if (group[g] > 2) continue;                       // groups 3, 4: collision geoms
    const s = [size[3 * g], size[3 * g + 1], size[3 * g + 2]];
    let geo;
    switch (type[g]) {
      case T.mjGEOM_PLANE.value: geo = new THREE.PlaneGeometry(s[0] ? 2 * s[0] : 20, s[1] ? 2 * s[1] : 20); break;
      case T.mjGEOM_BOX.value: geo = new THREE.BoxGeometry(2 * s[0], 2 * s[1], 2 * s[2]); break;
      case T.mjGEOM_SPHERE.value: geo = new THREE.SphereGeometry(s[0], 24, 16); break;
      case T.mjGEOM_ELLIPSOID.value: geo = new THREE.SphereGeometry(1, 24, 16).scale(s[0], s[1], s[2]); break;
      case T.mjGEOM_CAPSULE.value: geo = new THREE.CapsuleGeometry(s[0], 2 * s[1], 6, 16).rotateX(Math.PI / 2); break;
      case T.mjGEOM_CYLINDER.value: geo = new THREE.CylinderGeometry(s[0], s[0], 2 * s[1], 24).rotateX(Math.PI / 2); break;
      case T.mjGEOM_MESH.value: {
        const k = dataid[g];
        if (!meshCache.has(k)) meshCache.set(k, meshGeometry(k));
        geo = meshCache.get(k);
        break;
      }
      default: continue;
    }
    const m = matid[g], src = m >= 0 ? rgbaM : rgbaG, o = 4 * (m >= 0 ? m : g);
    const mat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(src[o], src[o + 1], src[o + 2]), opacity: src[o + 3], transparent: src[o + 3] < 1,
      roughness: 0.75, metalness: 0.05, flatShading: type[g] === T.mjGEOM_MESH.value,
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.matrixAutoUpdate = false;
    mesh.castShadow = type[g] !== T.mjGEOM_PLANE.value && src[o + 3] === 1;
    mesh.receiveShadow = true;
    scene.add(mesh);
    meshes.push([g, mesh]);
  }
}

function meshGeometry(k) {
  const va = model.mesh_vertadr[k], vn = model.mesh_vertnum[k];
  const fa = model.mesh_faceadr[k], fn = model.mesh_facenum[k];
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(Float32Array.from(model.mesh_vert.subarray(3 * va, 3 * (va + vn))), 3));
  geo.setIndex(new THREE.BufferAttribute(Uint32Array.from(model.mesh_face.subarray(3 * fa, 3 * (fa + fn))), 1));
  geo.computeVertexNormals();
  return geo;
}

function syncMeshes() {
  const p = data.geom_xpos, R = data.geom_xmat;
  for (const [g, mesh] of meshes) {
    const a = 9 * g, b = 3 * g;
    mesh.matrix.set(R[a], R[a + 1], R[a + 2], p[b],
                    R[a + 3], R[a + 4], R[a + 5], p[b + 1],
                    R[a + 6], R[a + 7], R[a + 8], p[b + 2],
                    0, 0, 0, 1);
  }
}

function cubeInTarget() {
  if (targetGeom < 0 || cubeBody < 0) return false;
  const c = data.xpos, p = data.geom_xpos, R = data.geom_xmat, s = model.geom_size;
  const dx = c[3 * cubeBody] - p[3 * targetGeom], dy = c[3 * cubeBody + 1] - p[3 * targetGeom + 1];
  const a = 9 * targetGeom;   // project onto the target's x/y axes (columns of xmat)
  const lx = dx * R[a] + dy * R[a + 3], ly = dx * R[a + 1] + dy * R[a + 4];
  return Math.abs(lx) < s[3 * targetGeom] && Math.abs(ly) < s[3 * targetGeom + 1] && c[3 * cubeBody + 2] < 0.05;
}

// ---- main loop: step physics in real time, slew controls toward the goal ----
let lastT = null, simDebt = 0;
function frame(now) {
  requestAnimationFrame(frame);
  const t = now / 1000;
  const dt = lastT == null ? 0 : Math.min(t - lastT, 0.1);
  lastT = t;
  simDebt += dt;
  const g = goal(), maxStep = SLEW * ts;
  while (simDebt >= ts) {
    const c = data.ctrl;
    for (let i = 0; i < ARM.length; i++) c[actIds[i]] += clamp(g[i] - c[actIds[i]], -maxStep, maxStep);
    mj.mj_step(model, data);
    simDebt -= ts;
  }
  syncMeshes();
  controls.update();
  renderer?.render(scene, camera);
  ui.tick(now, cubeInTarget());
}

try {
  $('loading').textContent = 'loading MuJoCo (WebAssembly) ...';
  mj = await loadMujoco();
  $('loading').textContent = 'loading SO-101 model ...';
  await loadModel();
  buildScene();
  reset();
  if (glError) { $('loading').textContent = glError; $('loading').classList.add('error'); }
  else $('loading').remove();
  readyResolve(true);
  requestAnimationFrame(frame);
} catch (err) {
  console.error(err);
  $('loading').textContent = `failed to start: ${err.message || err}`;
  $('loading').classList.add('error');
  readyResolve(false);
}
