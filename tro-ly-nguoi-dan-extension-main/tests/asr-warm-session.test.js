// Giữ sẵn phiên nhận giọng nói: mic + WS mở một lần, bấm mic chỉ gửi "start" + âm thanh; ngoài lượt không gửi byte nào.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const read = (f) => fs.readFileSync(path.join(root, f), "utf8");

function load() {
  const sockets = [];
  const mics = [];
  class FakeWS {
    constructor(url, protocols) {
      this.url = url; this.protocols = protocols; this.sent = []; this.readyState = 0;
      sockets.push(this);
    }
    send(data) { this.sent.push(data); }
    close() { this.readyState = 3; }
    open() { this.readyState = 1; this.onopen && this.onopen(); }
    msg(obj) { this.onmessage && this.onmessage({ data: JSON.stringify(obj) }); }
    json() { return this.sent.filter((d) => typeof d === "string").map((d) => JSON.parse(d)); }
    bins() { return this.sent.filter((d) => typeof d !== "string").length; }
  }
  FakeWS.OPEN = 1; FakeWS.CONNECTING = 0;
  class FakeMic {
    constructor(opts) { this.opts = opts; this.active = false; this.fail = FakeMic.nextFail; FakeMic.nextFail = null; mics.push(this); }
    async start() {
      if (this.fail) { this.opts.onError({ name: this.fail, message: "x" }); return false; }
      this.active = true; return true;
    }
    async ensureRunning() { return true; }
    stop() { this.active = false; }
    // Mic thật luôn có nhiễu nền (mẫu khác 0); khung toàn 0 = luồng mic đã bị ngắt.
    pcm() { this.opts.onPcm(new Int16Array([120, -80]).buffer); }
    silent() { this.opts.onPcm(new ArrayBuffer(4)); }
    lose() { this.active = false; this.opts.onLost && this.opts.onLost(); }
  }
  const window = { MicCapture: FakeMic, micSupported: () => true, hccWsBase: () => "wss://be" };
  const ctx = { window, WebSocket: FakeWS, console, setTimeout, clearTimeout, setInterval, clearInterval };
  vm.createContext(ctx);
  vm.runInContext(read("services/asr.js"), ctx);
  return { Warm: window.AsrWarmSession, sockets, mics, FakeMic };
}

function session(env, events) {
  return new env.Warm({
    baseUrl: "https://be", accessToken: "tok", lang: "vi",
    onState: (s) => events.push(["state", s]), onPartial: (t) => events.push(["partial", t]),
    onFinal: (t) => events.push(["final", t]), onError: (e) => events.push(["error", e.name]),
  });
}
const tick = () => new Promise((r) => setImmediate(r));

test("giữ sẵn: một WS + một mic; chưa bấm mic thì không gửi byte âm thanh nào", async () => {
  const env = load(); const ev = [];
  const s = session(env, ev);
  await s.warm();
  assert.equal(env.sockets.length, 1); assert.equal(env.mics.length, 1);
  env.sockets[0].open();
  assert.deepEqual(env.sockets[0].json()[0], { type: "warm", lang: "vi" });
  env.mics[0].pcm(); env.mics[0].pcm();
  assert.equal(env.sockets[0].bins(), 0, "ngoài lượt nói âm thanh không rời máy");
  s.cool();
});

test("bấm mic nhiều lượt: chỉ gửi start(turn) trên WS cũ, không mở WS / mic mới", async () => {
  const env = load(); const ev = [];
  const s = session(env, ev);
  await s.warm(); const ws = env.sockets[0]; ws.open();
  for (const turn of [1, 2]) {
    env.mics[0].pcm();
    await s.arm("vi"); await tick();
    const start = ws.json().filter((m) => m.type === "start").pop();
    assert.equal(start.turn, turn);
    assert.ok(ev.some(([k, v]) => k === "state" && v === "listening"));
    env.mics[0].pcm();
    ws.msg({ type: "transcript", data: { transcript: `câu ${turn}`, isFinal: true }, turn });
    assert.deepEqual(ev.filter(([k]) => k === "final").pop(), ["final", `câu ${turn}`]);
    const before = ws.bins(); env.mics[0].pcm();
    assert.equal(ws.bins(), before, "chốt câu xong là thôi gửi âm thanh");
  }
  assert.equal(env.sockets.length, 1); assert.equal(env.mics.length, 1);
  s.cool();
});

test("transcript của lượt cũ trả về muộn không lọt sang lượt mới; dừng giữa chừng gửi cancel, giữ WS", async () => {
  const env = load(); const ev = [];
  const s = session(env, ev);
  await s.warm(); const ws = env.sockets[0]; ws.open();
  env.mics[0].pcm();
  await s.arm("vi"); await tick();
  s.disarm();
  assert.equal(ws.json().pop().type, "cancel");
  assert.deepEqual(ev.pop(), ["state", "stopped"]);
  await s.arm("vi"); await tick();
  ws.msg({ type: "transcript", data: { transcript: "câu cũ", isFinal: true }, turn: 1 });
  assert.ok(!ev.some(([k]) => k === "final"));
  assert.equal(ws.readyState, 1);
  s.cool();
});

test("lỗi mic lúc giữ sẵn thì im (không tự mở trang cấp quyền); bấm mic mới báo lỗi", async () => {
  const env = load(); const ev = [];
  env.FakeMic.nextFail = "NotAllowedError";
  const s = session(env, ev);
  await s.warm();
  assert.ok(!ev.some(([k]) => k === "error"));
  env.FakeMic.nextFail = "NotAllowedError";
  env.sockets[0].open();
  await s.arm("vi"); await tick();
  assert.ok(ev.some(([k, v]) => k === "error" && v === "NotAllowedError"));
  s.cool();
});

test("service worker không đóng offscreen sau final của phiên giữ sẵn; sidebar báo sống và gửi warm khi BE hỗ trợ", () => {
  const bg = read("background.js"); const sb = read("sidebar.js"); const off = read("offscreen.js");
  assert.match(bg, /\(msg\.event === "final" \|\| msg\.event === "error"\) && !msg\.warm/);
  assert.match(bg, /msg\?\.type === "asr-warm" \|\| \(msg\?\.type === "asr-start" && msg\.warm === true\)/);
  assert.match(sb, /warm: voiceCfg\.asrWarm === true,/);
  assert.match(sb, /setInterval\(\(\) => \{ void warmVoice\(\); \}, ASR_WARM_BEAT_MS\)/);
  assert.match(off, /const WARM_LEASE_MS = \d+;/);
  assert.match(off, /if \(warm\) warm\.disarm\(\);/);
});

const wait = (ms) => new Promise((r) => setTimeout(r, ms));

test("mic giữ sẵn chỉ ra khung im lặng (luồng bị ngắt ngầm): bấm mic tự xin mic mới, âm thanh lúc chờ được gửi bù", async () => {
  const env = load(); const ev = [];
  const s = session(env, ev);
  await s.warm(); const ws = env.sockets[0]; ws.open();
  env.mics[0].silent(); env.mics[0].silent();
  await wait(5);
  const arming = s.arm("vi"); await tick();
  assert.equal(env.mics.length, 2, "mic chết phải được thay bằng mic mới");
  assert.ok(!ev.some(([k, v]) => k === "state" && v === "listening"), "chưa thấy tiếng thật thì chưa báo Đang nghe");
  env.mics[1].pcm();
  await arming;
  const sent = ws.sent.slice(ws.sent.findIndex((d) => typeof d === "string" && JSON.parse(d).type === "start"));
  assert.equal(JSON.parse(sent[0]).type, "start");
  assert.equal(typeof sent[1], "object", "khung thu trong lúc kiểm mic được gửi ngay sau start");
  assert.ok(ev.some(([k, v]) => k === "state" && v === "listening"));
  s.cool();
});

test("luồng mic bị ngắt lúc rảnh (track ended/muted): tự xin mic mới, không báo lỗi", async () => {
  const env = load(); const ev = [];
  const s = session(env, ev);
  await s.warm(); env.sockets[0].open();
  env.mics[0].lose(); await tick();
  assert.equal(env.mics.length, 2);
  assert.equal(env.mics[1].active, true);
  assert.ok(!ev.some(([k]) => k === "error"));
  s.cool();
});

test("mic không thu được tiếng nào: dựng lại một lần rồi báo lỗi rõ, không bao giờ hiện Đang nghe", async () => {
  const env = load(); const ev = [];
  const s = session(env, ev);
  await s.warm(); env.sockets[0].open();
  await s.arm("vi");
  assert.equal(env.mics.length, 2, "dựng lại mic đúng một lần");
  assert.ok(ev.some(([k, v]) => k === "error" && v === "MicSilentError"));
  assert.ok(!ev.some(([k, v]) => k === "state" && v === "listening"));
  assert.ok(!env.sockets[0].json().some((m) => m.type === "start"), "không mở lượt khi mic không có tiếng");
  s.cool();
});

test("WS nối lại xong trước khi mic xác nhận: chưa gửi start; mic có tiếng mới mở lượt, đúng một lần", async () => {
  const env = load(); const ev = [];
  const s = session(env, ev);
  await s.warm(); const ws = env.sockets[0];
  const arming = s.arm("vi"); await tick();
  ws.open();
  assert.ok(!ws.json().some((m) => m.type === "start"));
  env.mics[0].pcm();
  await arming;
  assert.equal(ws.json().filter((m) => m.type === "start").length, 1);
  s.cool();
});

test("đang nghe mà mic chỉ còn khung im lặng: tự dựng lại mic, lượt nói giữ nguyên", async () => {
  const env = load(); const ev = [];
  const s = session(env, ev);
  await s.warm(); const ws = env.sockets[0]; ws.open();
  env.mics[0].pcm();
  await s.arm("vi"); await tick();
  assert.ok(ev.some(([k, v]) => k === "state" && v === "listening"));
  for (let i = 0; i < 4; i++) { env.mics[0].silent(); await wait(450); }
  assert.equal(env.mics.length, 2, "mic chết giữa lượt được thay");
  assert.ok(!ev.some(([k]) => k === "error"));
  env.mics[1].pcm();
  assert.ok(ws.bins() > 0);
  s.cool();
});
