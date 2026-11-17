// Laptop page: SO-101 in MuJoCo (WebAssembly) + three.js, driven by a phone over a WebSocket.
// The phone sends velocities for the gripper (turn, reach, height) and the gripper state; this
// page turns them into joint targets with inverse kinematics, steps the physics, and records
// episodes (joint states, joint targets, phone commands, cube pose) at 30 Hz.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import loadMujoco from 'mujoco';

const ARM = ['shoulder_pan', 'shoulder_lift', 'elbow_flex', 'wrist_flex', 'wrist_roll', 'gripper'];
const GRIPPER_OPEN = 1.2, GRIPPER_CLOSED = 0.0;
const PITCH = 1.7;                          // lift + elbow + wrist that points the gripper down
const MAX = { pan: 0.9, r: 0.10, z: 0.10 }; // full-stick speed: rad/s, m/s, m/s
const BOX = { r: [0.14, 0.34], z: [0.01, 0.28] };   // where the gripper may go (reachable, IK tested)
const HOME = { pan: 0, r: 0.22, z: 0.14, open: false };
const SLEW = 3.0;                           // rad/s: smooths the joint targets
const CMD_TIMEOUT = 0.3;                    // s without a phone message: stop moving
const FPS = 30;

const $ = id => document.getElementById(id);
const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));

// ---- room and QR code ----
const params = new URLSearchParams(location.search);
let room = params.get('room');
if (!room) {
  room = Math.random().toString(36).slice(2, 6).toUpperCase();
  history.replaceState(null, '', `?room=${room}`);
}
const phoneUrl = `${location.origin}/phone?room=${room}`;
$('code').textContent = room;
$('url').textContent = phoneUrl;
$('qr').src = `/qr.svg?data=${encodeURIComponent(phoneUrl)}`;
const showQr = on => { $('join').hidden = !on; $('qrbtn').hidden = on; };
$('join').onclick = () => showQr(false);
$('qrbtn').onclick = () => showQr(true);

// a phone used as the screen would dim and lock after a minute without touches: keep it on
async function keepAwake() { try { await navigator.wakeLock?.request('screen'); } catch { /* not supported */ } }
keepAwake();
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') keepAwake(); });
document.addEventListener('pointerdown', keepAwake, { once: true });   // Safari wants a tap first

if (['localhost', '127.0.0.1'].includes(location.hostname))
  $('warn').textContent = 'Phones cannot open a localhost link: open this page through the https tunnel address.';

// ---- state: where the gripper should be, and the latest phone command ----
const target = { ...HOME };
let lift = -0.497, elbow = 0.114;           // IK solution (warm start: gripper 22 cm out, 14 cm up)
let cmd = { vp: 0, vr: 0, vz: 0, at: -1 };
let mj, model, data, ikd, jointIds, actIds, siteId, cubeBody, cubeAdr, targetGeom, ts = 0.002;
let ctrlLo = ARM.map(() => -Infinity), ctrlHi = ARM.map(() => Infinity);

// ---- inverse kinematics: (reach r, height z) of the gripper tip -> shoulder_lift, elbow_flex ----
function wristFor(a, b) { return clamp(PITCH - a - b, ctrlLo[3], ctrlHi[3]); }
function tip(a, b) {
  const q = ikd.qpos, adr = model.jnt_qposadr;
  q[adr[jointIds[0]]] = 0; q[adr[jointIds[1]]] = a; q[adr[jointIds[2]]] = b;
  q[adr[jointIds[3]]] = wristFor(a, b); q[adr[jointIds[4]]] = 0;
  mj.mj_kinematics(model, ikd);
  return [ikd.site_xpos[3 * siteId], ikd.site_xpos[3 * siteId + 2]];
}
function ik(r, z, a, b) {                   // damped least squares, warm-started at (a, b)
  for (let k = 0; k < 20; k++) {
    const [x, y] = tip(a, b), ex = r - x, ey = z - y;
    if (Math.hypot(ex, ey) < 1e-4) break;
    const h = 1e-4, [xa, ya] = tip(a + h, b), [xb, yb] = tip(a, b + h);
    const j11 = (xa - x) / h, j21 = (ya - y) / h, j12 = (xb - x) / h, j22 = (yb - y) / h;
    const A = j11 * j11 + j21 * j21 + 1e-4, B = j11 * j12 + j21 * j22, C = j12 * j12 + j22 * j22 + 1e-4;
    const g1 = j11 * ex + j21 * ey, g2 = j12 * ex + j22 * ey, det = A * C - B * B;
    a = clamp(a + (C * g1 - B * g2) / det, ctrlLo[1], ctrlHi[1]);
    b = clamp(b + (A * g2 - B * g1) / det, ctrlLo[2], ctrlHi[2]);
  }
  const [x, y] = tip(a, b);
  return { a, b, err: Math.hypot(r - x, z - y) };
}

function goal() {
  return [target.pan, lift, elbow, wristFor(lift, elbow), 0, target.open ? GRIPPER_OPEN : GRIPPER_CLOSED]
    .map((v, i) => clamp(v, ctrlLo[i], ctrlHi[i]));
}

// move the target by the phone's velocities; keep the move only if the arm can reach it
function integrate(dt, now) {
  if (now - cmd.at > CMD_TIMEOUT) return;
  target.pan = clamp(target.pan + cmd.vp * MAX.pan * dt, ctrlLo[0], ctrlHi[0]);
  const r = clamp(target.r + cmd.vr * MAX.r * dt, ...BOX.r), z = clamp(target.z + cmd.vz * MAX.z * dt, ...BOX.z);
  if (r === target.r && z === target.z) return;
  const s = ik(r, z, lift, elbow);
  if (s.err < 0.003) { target.r = r; target.z = z; lift = s.a; elbow = s.b; }
}

function reset(randomCube = false) {
  Object.assign(target, HOME);
  const s = ik(HOME.r, HOME.z, -0.497, 0.114); lift = s.a; elbow = s.b;
  mj.mj_resetData(model, data);
  const g = goal(), q = data.qpos, c = data.ctrl, adr = model.jnt_qposadr;
  ARM.forEach((_, i) => { q[adr[jointIds[i]]] = g[i]; c[actIds[i]] = g[i]; });
  if (randomCube) { q[cubeAdr] += (Math.random() - 0.5) * 0.04; q[cubeAdr + 1] += (Math.random() - 0.5) * 0.04; }
  mj.mj_forward(model, data);
}

// ---- recording ----
let rec = null, episodes = 0, lastSample = 0;
function startRecording(name) {
  reset(true);
  rec = { name: name || 'anon', started: new Date().toISOString(), t0: performance.now() / 1000,
          frames: { t: [], state: [], action: [], command: [], gripper_target: [], cube: [] } };
  lastSample = rec.t0 - 1 / FPS;
}
function sample(now) {
  const f = rec.frames, adr = model.jnt_qposadr, q = data.qpos, b = cubeBody;
  f.t.push(+(now - rec.t0).toFixed(3));
  f.state.push(jointIds.map(j => +q[adr[j]].toFixed(4)));
  f.action.push(goal().map(v => +v.toFixed(4)));
  f.command.push(now - cmd.at > CMD_TIMEOUT ? [0, 0, 0] : [cmd.vp, cmd.vr, cmd.vz].map(v => +v.toFixed(3)));
  f.gripper_target.push([target.pan, target.r, target.z, target.open ? 1 : 0].map(v => +v.toFixed(4)));
  f.cube.push([...data.xpos.slice(3 * b, 3 * b + 3), ...data.xquat.slice(4 * b, 4 * b + 4)].map(v => +v.toFixed(4)));
}
async function stopRecording(save) {
  const ep = rec; rec = null;
  if (!save || ep.frames.t.length < FPS) { status(save ? 'too short, not saved' : 'discarded'); return; }
  const body = {
    room, name: ep.name, started: ep.started, fps: FPS, success: cubeInTarget(),
    task: 'move the red cube onto the green square',
    joint_names: ARM, units: 'radians; gripper_target = [pan rad, reach m, height m, open]; cube = [x y z m, quat w x y z]',
    frames: ep.frames,
  };
  try {
    const r = await fetch('/api/episodes', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!r.ok) throw new Error(r.status);
    episodes += 1;
    status(`saved (${body.success ? 'cube on target' : 'cube not on target'})`);
  } catch (e) { status(`saving failed: ${e.message}`); }
}

// ---- connection to the phone ----
let ws = null, lastStatus = '', steering = false;
function status(text) { lastStatus = text; }
function send(msg) { if (ws?.readyState === 1) ws.send(JSON.stringify(msg)); }
function connect() {
  ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/${room}/view`);
  ws.onmessage = e => {
    const m = JSON.parse(e.data), now = performance.now() / 1000;
    if (m.type === 'presence') {
      if (m.controller && !steering) showQr(false);       // someone steers: fold the QR code away
      if (!m.phones && steering) showQr(true);             // the phone left: show it again
      steering = !!m.controller;
      $('phone').textContent = !m.phones ? 'no phone connected'
        : m.controller ? `${m.controller} is steering` : 'phone connected, nobody steering';
      $('phone').className = m.phones ? 'ok' : 'bad';
    } else if (m.type === 'cmd') {
      cmd = { vp: clamp(+m.vp || 0, -1, 1), vr: clamp(+m.vr || 0, -1, 1), vz: clamp(+m.vz || 0, -1, 1), at: now };
    } else if (m.type === 'gripper') {
      target.open = !!m.open;
    } else if (m.type === 'record') {
      if (m.action === 'start' && !rec) startRecording(m.name);
      if (m.action === 'save' && rec) stopRecording(true);
      if (m.action === 'discard' && rec) stopRecording(false);
    } else if (m.type === 'reset' && !rec) {
      reset();
    }
  };
  ws.onclose = () => setTimeout(connect, 1500);
}
setInterval(() => send({ type: 'status', recording: !!rec, open: target.open, episodes, message: lastStatus,
  seconds: rec ? +(performance.now() / 1000 - rec.t0).toFixed(1) : 0, success: model ? cubeInTarget() : false }), 250);

// ---- three.js scene (as in gestures/sim) ----
let renderer = null, glError = null;
try {
  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  $('view').appendChild(renderer.domElement);
} catch (err) { glError = 'WebGL is not available in this browser.'; }
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xdde4ec);
const camera = new THREE.PerspectiveCamera(45, 1, 0.01, 20);
camera.up.set(0, 0, 1);
camera.position.set(-0.5, 0.2, 0.42);       // behind the arm: screen left = arm's left
const controls = new OrbitControls(camera, renderer ? renderer.domElement : document.body);
controls.target.set(0.1, -0.03, 0.12);
controls.enableDamping = true;
controls.update();
scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8070, 1.6));
const sun = new THREE.DirectionalLight(0xffffff, 2.0);
sun.position.set(0.5, 0.6, 1.5); sun.target.position.set(0.12, 0, 0); sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -0.6, right: 0.6, top: 0.6, bottom: -0.6, near: 0.1, far: 4 });
sun.shadow.bias = -0.0005;
scene.add(sun, sun.target);
function resize() {
  const w = window.innerWidth, h = window.innerHeight;
  renderer?.setSize(w, h); camera.aspect = w / h;
  // portrait (a phone): widen the vertical field of view so the arm still fits horizontally
  camera.fov = camera.aspect >= 1.2 ? 45 : 2 * Math.atan(Math.tan(Math.PI / 8) * 1.2 / camera.aspect) * 180 / Math.PI;
  camera.updateProjectionMatrix();
}
window.addEventListener('resize', resize); resize();

const meshes = [];
async function loadModel() {
  const base = new URL('/model/', location.origin);
  const arm = await (await fetch(new URL('so101.xml', base))).text();
  const meshdir = (arm.match(/meshdir="([^"]+)"/) || [, ''])[1];
  const files = ['scene.xml', 'so101.xml', ...[...arm.matchAll(/file="([^"]+\.stl)"/g)].map(m => `${meshdir}/${m[1]}`)];
  const bytes = await Promise.all(files.map(async f => new Uint8Array(await (await fetch(new URL(f, base))).arrayBuffer())));
  const vfs = new mj.MjVFS();
  files.forEach((f, i) => vfs.addBuffer(f, bytes[i]));
  try { model = mj.MjModel.from_xml_path('scene.xml', vfs); } finally { vfs.delete(); }
  data = new mj.MjData(model); ikd = new mj.MjData(model);
  ts = model.opt.timestep;
  const O = mj.mjtObj, id = (type, name) => mj.mj_name2id(model, O[type].value, name);
  jointIds = ARM.map(n => id('mjOBJ_JOINT', n));
  actIds = ARM.map(n => id('mjOBJ_ACTUATOR', n));
  const cr = model.actuator_ctrlrange;
  ctrlLo = actIds.map(a => cr[2 * a]); ctrlHi = actIds.map(a => cr[2 * a + 1]);
  siteId = id('mjOBJ_SITE', 'gripperframe');
  targetGeom = id('mjOBJ_GEOM', 'target'); cubeBody = id('mjOBJ_BODY', 'cube');
  cubeAdr = model.jnt_qposadr[id('mjOBJ_JOINT', 'cube')];
}

function buildScene() {
  const T = mj.mjtGeom, type = model.geom_type, size = model.geom_size, group = model.geom_group;
  const dataid = model.geom_dataid, matid = model.geom_matid, rgbaG = model.geom_rgba, rgbaM = model.mat_rgba;
  const cache = new Map();
  for (let g = 0; g < model.ngeom; g++) {
    if (group[g] > 2) continue;
    const s = [size[3 * g], size[3 * g + 1], size[3 * g + 2]];
    let geo;
    switch (type[g]) {
      case T.mjGEOM_PLANE.value: geo = new THREE.PlaneGeometry(s[0] ? 2 * s[0] : 20, s[1] ? 2 * s[1] : 20); break;
      case T.mjGEOM_BOX.value: geo = new THREE.BoxGeometry(2 * s[0], 2 * s[1], 2 * s[2]); break;
      case T.mjGEOM_SPHERE.value: geo = new THREE.SphereGeometry(s[0], 24, 16); break;
      case T.mjGEOM_CAPSULE.value: geo = new THREE.CapsuleGeometry(s[0], 2 * s[1], 6, 16).rotateX(Math.PI / 2); break;
      case T.mjGEOM_CYLINDER.value: geo = new THREE.CylinderGeometry(s[0], s[0], 2 * s[1], 24).rotateX(Math.PI / 2); break;
      case T.mjGEOM_MESH.value: {
        const k = dataid[g];
        if (!cache.has(k)) {
          const va = model.mesh_vertadr[k], vn = model.mesh_vertnum[k], fa = model.mesh_faceadr[k], fn = model.mesh_facenum[k];
          const m = new THREE.BufferGeometry();
          m.setAttribute('position', new THREE.BufferAttribute(Float32Array.from(model.mesh_vert.subarray(3 * va, 3 * (va + vn))), 3));
          m.setIndex(new THREE.BufferAttribute(Uint32Array.from(model.mesh_face.subarray(3 * fa, 3 * (fa + fn))), 1));
          m.computeVertexNormals();
          cache.set(k, m);
        }
        geo = cache.get(k);
        break;
      }
      default: continue;
    }
    const m = matid[g], src = m >= 0 ? rgbaM : rgbaG, o = 4 * (m >= 0 ? m : g);
    const mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({
      color: new THREE.Color(src[o], src[o + 1], src[o + 2]), opacity: src[o + 3], transparent: src[o + 3] < 1,
      roughness: 0.75, metalness: 0.05, flatShading: type[g] === T.mjGEOM_MESH.value }));
    mesh.matrixAutoUpdate = false;
    mesh.castShadow = type[g] !== T.mjGEOM_PLANE.value && src[o + 3] === 1;
    mesh.receiveShadow = true;
    scene.add(mesh);
    meshes.push([g, mesh]);
  }
}

function syncMeshes() {
  const p = data.geom_xpos, R = data.geom_xmat;
  for (const [g, mesh] of meshes) {
    const a = 9 * g, b = 3 * g;
    mesh.matrix.set(R[a], R[a + 1], R[a + 2], p[b], R[a + 3], R[a + 4], R[a + 5], p[b + 1],
                    R[a + 6], R[a + 7], R[a + 8], p[b + 2], 0, 0, 0, 1);
  }
}

function cubeInTarget() {
  const c = data.xpos, p = data.geom_xpos, R = data.geom_xmat, s = model.geom_size, g = targetGeom;
  const dx = c[3 * cubeBody] - p[3 * g], dy = c[3 * cubeBody + 1] - p[3 * g + 1], a = 9 * g;
  const lx = dx * R[a] + dy * R[a + 3], ly = dx * R[a + 1] + dy * R[a + 4];
  return Math.abs(lx) < s[3 * g] && Math.abs(ly) < s[3 * g + 1] && c[3 * cubeBody + 2] < 0.05;
}

// ---- main loop ----
let lastT = null, simDebt = 0;
function frame(nowMs) {
  requestAnimationFrame(frame);
  const now = nowMs / 1000, dt = lastT == null ? 0 : Math.min(now - lastT, 0.1);
  lastT = now; simDebt += dt;
  integrate(dt, performance.now() / 1000);
  const g = goal(), maxStep = SLEW * ts;
  while (simDebt >= ts) {
    const c = data.ctrl;
    for (let i = 0; i < ARM.length; i++) c[actIds[i]] += clamp(g[i] - c[actIds[i]], -maxStep, maxStep);
    mj.mj_step(model, data);
    simDebt -= ts;
  }
  const t = performance.now() / 1000;
  if (rec && t - lastSample >= 1 / FPS) {   // keep 30 Hz on average, whatever the screen's frame rate
    lastSample = Math.max(lastSample + 1 / FPS, t - 1 / FPS); sample(t);
  }
  syncMeshes(); controls.update(); renderer?.render(scene, camera);
  const done = cubeInTarget();
  $('goal').className = done ? 'done' : '';
  $('goal').textContent = done ? 'cube on the green square!' : 'goal: move the red cube onto the green square';
  $('rec').className = rec ? 'on' : '';
  $('rec').textContent = rec ? `● REC ${(t - rec.t0).toFixed(1)} s` : (lastStatus || 'not recording');
  $('count').textContent = `episodes saved on this screen: ${episodes}`;
}

try {
  $('loading').textContent = 'loading MuJoCo ...';
  mj = await loadMujoco();
  $('loading').textContent = 'loading SO-101 model ...';
  await loadModel();
  buildScene();
  reset();
  if (glError) { $('loading').textContent = glError; $('loading').classList.add('error'); } else $('loading').remove();
  window.teleop = { target, reset, cubeInTarget, get cmd() { return cmd; } };   // for debugging
  connect();
  requestAnimationFrame(frame);
} catch (err) {
  console.error(err);
  $('loading').textContent = `failed to start: ${err.message || err}`;
  $('loading').classList.add('error');
}
