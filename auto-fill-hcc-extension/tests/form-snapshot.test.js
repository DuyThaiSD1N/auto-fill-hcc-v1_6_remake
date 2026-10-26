// Ảnh chụp form (content/form-snapshot): khớp nút rời bước, đọc lại field bằng đúng engine, và
// vòng đời fill → edit → step. Chạy file nguồn trong vm với DOM giả tối thiểu.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const src = (f) => fs.readFileSync(path.join(root, "content/form-snapshot", f), "utf8");

function fakeEl({ tag = "BUTTON", id = "", text = "", value = "", selectors = [], dialog = null } = {}) {
  return {
    tagName: tag, id, textContent: text, value,
    matches: (sel) => selectors.includes(sel),
    closest: (sel) => (sel.includes("dialog") ? dialog : null),
  };
}

function load({ ns = {}, chrome, dom = [] } = {}) {
  const listeners = {};
  const timers = [];
  const store = new Map();
  const sent = [];
  const runtimeListeners = [];
  const ctx = {
    window: { __HCC__: ns, addEventListener: (t, fn) => { listeners["window:" + t] = fn; } },
    document: {
      addEventListener: (t, fn) => { (listeners[t] = listeners[t] || []).push(fn); },
      querySelector: () => null,
      querySelectorAll: (sel) => dom.filter((el) => el.hit(sel)),
    },
    location: { hostname: "dvc.moc.gov.vn", pathname: "/vi/padsvc/apply-online/abc", hash: "" },
    sessionStorage: {
      getItem: (k) => (store.has(k) ? store.get(k) : null),
      setItem: (k, v) => store.set(k, v),
      removeItem: (k) => store.delete(k),
    },
    chrome: chrome || {
      runtime: {
        lastError: null,
        sendMessage: (msg, cb) => { sent.push(msg); if (cb) cb({ ok: true }); },
        getManifest: () => ({ version: "9.9" }),
        onMessage: { addListener: (fn) => runtimeListeners.push(fn) },
      },
    },
    crypto: { randomUUID: () => "id-" + (sent.length + 1) },
    CSS: { escape: (s) => s },
    setTimeout: (fn) => { timers.push(fn); return timers.length; },
    clearTimeout: (n) => { if (n) timers[n - 1] = null; },
    Date, JSON, String, Number, Array, Set, Object, RegExp,
  };
  vm.createContext(ctx);
  for (const f of ["read.js", "labels.js", "rules.js", "tracker.js"]) vm.runInContext(src(f), ctx);
  const runTimers = () => { const due = timers.splice(0); due.forEach((fn) => fn && fn()); };
  return { FS: ns.formSnapshot, listeners, runTimers, sent, store, runtimeListeners, ctx };
}

const RULES = {
  "dvc.moc.gov.vn": [{
    urlPattern: "^/vi/padsvc/apply-online/[0-9a-z]+$",
    buttonSelector: '[id^="cdk-step-content-"][id$="-0"] button.btn_next',
  }],
  "dichvucongnganhtuphap.moj.gov.vn": [
    { urlPattern: "^/nop-ho-so/\\d+$", buttonIds: ["xem-truoc-to-khai"] },
    { urlPattern: "^/nop-ho-so/\\d+$", buttonText: ["xac nhan"], dialogText: "xem to khai" },
  ],
};

test("khớp nút rời bước theo selector, id, nhãn + hộp thoại", () => {
  const { FS } = load();
  const loc = { hostname: "dvc.moc.gov.vn", pathname: "/vi/padsvc/apply-online/abc", hash: "" };
  const next = fakeEl({ text: " Tiếp tục ", selectors: [RULES["dvc.moc.gov.vn"][0].buttonSelector] });
  assert.equal(FS.matchStep(RULES, next, loc), "Tiếp tục");
  assert.equal(FS.matchStep(RULES, fakeEl({ text: "Tiếp tục" }), loc), null, "Tiếp tục ở bước 2 không khớp");
  assert.equal(FS.matchStep(RULES, next, { ...loc, pathname: "/vi/tra-cuu" }), null);

  const moj = { hostname: "dichvucongnganhtuphap.moj.gov.vn", pathname: "/nop-ho-so/144862", hash: "" };
  assert.ok(FS.matchStep(RULES, fakeEl({ id: "xem-truoc-to-khai", text: "Xem trước" }), moj));
  const confirmIn = (title) => fakeEl({ text: "Xác nhận", dialog: { textContent: title } });
  assert.equal(FS.matchStep(RULES, confirmIn("Xem tờ khai điện tử ... Xác nhận"), moj), "Xác nhận");
  assert.equal(FS.matchStep(RULES, confirmIn("Ghi đè thông tin chủ hồ sơ"), moj), null);
  assert.equal(FS.matchStep(RULES, fakeEl({ text: "Đóng" }), { ...moj, hostname: "x.gov.vn" }), null);
});

test("đọc lại field bằng engine của từng loại form", () => {
  const ns = {
    readLegacyField: (f) => `legacy:${f.name}`,
    readAngularField: (f) => `ng:${f.name}`,
    readBacNinhField: () => ["Bên thế chấp"],
    readLizField: () => true,
    readSurveyJsValue: () => "Hà Nội",
    findStandardInput: () => ({ type: "text", value: " Nguyễn A " }),
    findStandardSelect: () => null,
  };
  const { FS } = load({ ns });
  const fields = [
    { name: "hoTen", comp: "x-input" },
    { name: "data[hoTen]", comp: "dom-input", occurrence: 1 },
    { name: "NycHoTen", comp: "" },
  ];
  assert.deepEqual(JSON.parse(JSON.stringify(FS.readFields(fields, "angular"))), [
    { name: "hoTen", comp: "x-input", value: "legacy:hoTen" },
    { name: "data[hoTen]", comp: "dom-input", value: "Nguyễn A", occurrence: 1 },
    { name: "NycHoTen", comp: "", value: "ng:NycHoTen" },
  ]);
  assert.deepEqual([...FS.readFields([{ name: "a", comp: "bn-radio" }], "bacninh")[0].value], ["Bên thế chấp"]);
  assert.equal(FS.readFields([{ name: "Tỉnh", section: "Người nộp" }], "liz")[0].section, "Người nộp");
  assert.equal(FS.readFields([{ name: "tinh" }], "surveyjs")[0].value, "Hà Nội");
  ns.readLegacyField = () => { throw new Error("vỡ"); };
  assert.equal(FS.readFields([{ name: "x", comp: "x-date" }], "legacy")[0].value, null, "lỗi đọc → null, không ném");
});

test("vòng đời fill → edit (chỉ khi đổi) → step", () => {
  let value = "A";
  const ns = { readLegacyField: () => value };
  const env = load({ ns });
  const { FS, listeners, runTimers, sent } = env;
  const cfg = { requestId: "req_1", stepRules: RULES };
  FS.arm(cfg);
  FS.track(cfg, [{ name: "hoTen", comp: "x-input" }], "legacy");
  runTimers();
  assert.equal(sent.length, 1);
  assert.equal(sent[0].snapshot.kind, "fill");
  assert.equal(sent[0].snapshot.requestId, "req_1");
  assert.equal(sent[0].snapshot.extVersion, "9.9");

  const user = { isTrusted: true };
  listeners.keyup.forEach((fn) => fn(user));
  runTimers();
  assert.equal(sent.length, 1, "không đổi giá trị thì không gửi edit");

  value = "B";
  listeners.input.forEach((fn) => fn({ isTrusted: false }));
  runTimers();
  assert.equal(sent.length, 1, "sự kiện do script phát không tính");
  listeners.input.forEach((fn) => fn(user));
  runTimers();
  assert.equal(sent[1].snapshot.kind, "edit");
  assert.equal(sent[1].snapshot.fields[0].value, "B");

  const btn = fakeEl({ text: "Tiếp tục", selectors: [RULES["dvc.moc.gov.vn"][0].buttonSelector] });
  listeners.click.forEach((fn) => fn({ isTrusted: true, target: { closest: () => btn } }));
  const step = sent.filter((m) => m.action === "formSnapshot" && m.snapshot.kind === "step");
  assert.equal(step.length, 1);
  assert.equal(step[0].snapshot.trigger, "Tiếp tục");
  assert.ok(sent.some((m) => m.action === "formSnapshotStep"), "báo background để frame khác cũng chụp");
  env.runtimeListeners.forEach((fn) => fn({ action: "formSnapshotCapture", trigger: "x" }));
  assert.equal(sent.filter((m) => m.snapshot?.kind === "step").length, 1, "lệnh phát lại không chụp trùng");
  assert.equal(env.store.size, 0, "background đã nhận thì không giữ trong sessionStorage");
});

test("form đã rời trang (đọc ra toàn null) thì không gửi ảnh edit/step rỗng", () => {
  let value = "A";
  const env = load({ ns: { readLegacyField: () => value } });
  const cfg = { requestId: "req_1", stepRules: RULES };
  env.FS.track(cfg, [{ name: "hoTen", comp: "x-input" }], "legacy");
  env.runTimers();
  value = null;
  env.listeners.pointerup.forEach((fn) => fn({ isTrusted: true }));
  env.runTimers();
  env.runtimeListeners.forEach((fn) => fn({ action: "formSnapshotCapture", trigger: "x" }));
  assert.deepEqual(env.sent.map((m) => m.snapshot?.kind), ["fill"]);
});

test("background chưa nhận thì giữ trong sessionStorage và gửi lại khi trang nạp lại", () => {
  const pending = [];
  const chrome = {
    runtime: {
      lastError: null,
      sendMessage: (msg, cb) => { pending.push(msg); },
      onMessage: { addListener: () => {} },
    },
  };
  const env = load({ ns: { readLegacyField: () => "A" }, chrome });
  env.FS.track({ requestId: "req_1", stepRules: {} }, [{ name: "a", comp: "x-input" }], "legacy");
  env.runTimers();
  const kept = JSON.parse(env.store.get("__form_snapshot_pending"));
  assert.equal(kept.length, 1);
  assert.equal(kept[0].kind, "fill");
});

function domEl({ tag, name, type = "", value = "", checked = false, parent = null }) {
  return {
    tagName: tag.toUpperCase(), type, value, checked, parentElement: parent, selectedOptions: [],
    getAttribute: (k) => (k === "name" ? name : null),
    closest: () => null,
    // Đủ cho các selector module dùng: "x-input-number[name]", "input[name]", '[name="..."]'.
    hit: (sel) => sel.split(",").some((one) => {
      one = one.trim();
      const byName = one.match(/^\[name="(.+)"\]$/);
      if (byName) return byName[1] === name;
      return one === `${tag}[name]`;
    }),
  };
}

test("ô BE không trả mà người dùng tự điền vẫn có trong ảnh chụp", () => {
  const xComp = domEl({ tag: "x-input-number", name: "DeNghiCapBanSao" });
  const inner = domEl({ tag: "input", name: "DeNghiCapBanSao-inner", type: "text", value: "9", parent: xComp });
  const lan = domEl({ tag: "input", name: "LoaiDangKy", type: "checkbox", checked: false });
  const daCo = domEl({ tag: "x-input", name: "HoTen" });
  const hauTo = domEl({ tag: "x-input", name: "HoTen__1761724625529" });
  const values = { DeNghiCapBanSao: "", HoTen: "A" };
  const ns = { readLegacyField: (f) => values[f.name], fieldCandidates: (f) => [f.name] };
  const env = load({ ns, dom: [xComp, inner, lan, daCo, hauTo] });
  env.FS.track({ requestId: "req_1", stepRules: {} }, [{ name: "HoTen", comp: "x-input" }], "legacy");
  env.runTimers();
  const fill = JSON.parse(JSON.stringify(env.sent[0].snapshot.fields));
  assert.deepEqual(fill.map((f) => [f.name, f.comp, f.value]), [
    ["HoTen", "x-input", "A"], ["DeNghiCapBanSao", "x-input-number", ""], ["LoaiDangKy", "", false],
  ], "ô con trong x-* không tính riêng; ô BE đã trả (kể cả tên có hậu tố __<số>) không lặp");

  values.DeNghiCapBanSao = "5";
  lan.checked = true;
  env.listeners.input.forEach((fn) => fn({ isTrusted: true }));
  env.runTimers();
  const edit = JSON.parse(JSON.stringify(env.sent[1].snapshot.fields));
  assert.deepEqual(edit.map((f) => f.value), ["A", "5", true]);
});

test("nối vào luồng điền và manifest", () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));
  const js = manifest.content_scripts[0].js;
  const idx = (f) => js.indexOf(f);
  assert.ok(idx("content/form-snapshot/read.js") > -1);
  assert.ok(idx("content/form-snapshot/read.js") < idx("content/form-snapshot/rules.js"));
  assert.ok(idx("content/form-snapshot/rules.js") < idx("content/form-snapshot/tracker.js"));
  const dispatcher = fs.existsSync(path.join(root, "content/fill-core.js"))
    ? fs.readFileSync(path.join(root, "content/fill-core.js"), "utf8")
    : fs.readFileSync(path.join(root, "content.js"), "utf8");
  assert.match(dispatcher, /msg\.action !== "fillFields"\) return;\s*\n\s*H\.formSnapshot\?\.arm\?\.\(msg\.formSnapshot\);/);
  assert.match(dispatcher, /H\.formSnapshot\?\.track\?\.\(msg\.formSnapshot, fields, formKind\)/);
});
