// Phiên tải ảnh QR phải sống qua các lần panel dựng lại (trang cổng chuyển bước/tải lại). Trước đây
// mã phiên chỉ nằm trong bộ nhớ panel → dựng lại là ngừng kéo, điện thoại vẫn báo "đã gửi" (đo prod:
// 98/2541 phiên, 214 tệp không về panel). Chạy THẬT đoạn code của popup.js trong vm.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const popup = fs.readFileSync(path.join(root, "popup.js"), "utf8");
const bg = fs.readFileSync(path.join(root, "background.js"), "utf8");

const start = popup.indexOf("const PHONE_UPLOAD_KEY");
const end = popup.indexOf("function setQrStatus(", start);
const snippet = popup.slice(start, end);

function panel(store, { files = [], user = { username: "u" } } = {}) {
  const calls = { qr: [], ws: [], reconcile: 0, intervals: 0, status: [] };
  const ctx = vm.createContext({
    EMBEDDED_TAB_ID: 5, currentUser: user, files, Date, Number,
    pulledFids: new Set(),
    phoneUploadSid: null, phoneUploadQr: "", phoneReconcile: null, phone404: 0, qrCard: null,
    chrome: { storage: { local: {
      set: (o) => { Object.assign(store, JSON.parse(JSON.stringify(o))); },
      get: async (k) => ({ [k]: store[k] }),
      remove: (k) => { delete store[k]; },
    } } },
    renderQrCard: (s) => calls.qr.push(s.qr_png_base64),
    setQrStatus: (t) => calls.status.push(t),
    subscribePhoneUpload: (sid) => calls.ws.push(sid),
    reconcilePhoneOnce: async () => { calls.reconcile++; },
    setInterval: () => { calls.intervals++; return 1; },
    stopPhoneUploadChannel: () => {},
  });
  vm.runInContext(`${snippet}
    this.api = { savePhoneUpload, restorePhoneUpload, closePhoneUpload,
      open: (sid, qr) => { phoneUploadSid = sid; phoneUploadQr = qr; savePhoneUpload(); },
      pull: (fid) => { pulledFids.add(fid); savePhoneUpload(); },
      state: () => ({ sid: phoneUploadSid, pulled: [...pulledFids] }) };`, ctx);
  return { api: ctx.api, calls };
}

test("mở QR → panel dựng lại → nối lại đúng phiên, hiện lại QR, kéo nốt ngay", async () => {
  const store = {};
  const p1 = panel(store);
  p1.api.open("HS-1", "QRPNG");
  p1.api.pull("f1");
  const p2 = panel(store, { files: [{ fromPhone: true, phoneFid: "f1" }] });
  await p2.api.restorePhoneUpload();
  assert.equal(p2.api.state().sid, "HS-1");
  assert.deepEqual(p2.calls.qr, ["QRPNG"]);
  assert.deepEqual(p2.calls.ws, ["HS-1"]);
  assert.equal(p2.calls.intervals, 1);
  assert.equal(p2.calls.reconcile, 1, "kéo ngay tệp gửi trong lúc panel dựng lại");
});

test("tệp cán bộ đã bấm × không bị kéo lại; tệp đã vào hồ sơ mà chưa kịp ghi `pulled` cũng không kéo trùng", async () => {
  const store = {};
  const p1 = panel(store);
  p1.api.open("HS-2", "Q");
  p1.api.pull("da-xoa"); // đã kéo rồi cán bộ xoá khỏi danh sách
  const p2 = panel(store, { files: [{ fromPhone: true, phoneFid: "chua-ghi" }] });
  await p2.api.restorePhoneUpload();
  assert.deepEqual([...p2.api.state().pulled].sort(), ["chua-ghi", "da-xoa"]);
});

test("đóng QR / Phiên mới / đăng xuất → không nối lại nữa; bản lưu quá 24 giờ bị bỏ", async () => {
  const store = {};
  const p1 = panel(store);
  p1.api.open("HS-3", "Q");
  p1.api.closePhoneUpload();
  assert.equal(store.autofill_phone_upload_5, undefined);
  const p2 = panel(store);
  await p2.api.restorePhoneUpload();
  assert.equal(p2.api.state().sid, null);

  store.autofill_phone_upload_5 = { sid: "HS-OLD", qr: "", pulled: [], at: Date.now() - 25 * 3600 * 1000 };
  const p3 = panel(store);
  await p3.api.restorePhoneUpload();
  assert.equal(p3.api.state().sid, null);
  assert.equal(store.autofill_phone_upload_5, undefined);
});

test("chưa đăng nhập thì không nối lại", async () => {
  const store = { autofill_phone_upload_5: { sid: "HS-4", qr: "", pulled: [], at: Date.now() } };
  const p = panel(store, { user: null });
  await p.api.restorePhoneUpload();
  assert.equal(p.api.state().sid, null);
});

test("nối dây: khôi phục sau tự nhận diện thủ tục, lưu khi mở QR, mã tệp đi cùng hồ sơ, dọn khi đóng tab", () => {
  assert.equal((popup.match(/await autoDetectProcedure\(\);\s*await restorePhoneUpload\(\);/g) || []).length, 2);
  assert.match(popup, /phoneUploadQr = s\.qr_png_base64 \|\| "";\s*savePhoneUpload\(\);/);
  assert.match(popup, /fromPhone: true, phoneFid: r\.f\.fid,/);
  assert.match(popup, /await saveSession\(\);\s*if \(phoneUploadSid !== sid\) return added;\s*savePhoneUpload\(\);/);
  assert.match(popup, /fromPhone: it\.fromPhone \|\| false,\s*phoneFid: it\.phoneFid \|\| null,/);
  assert.match(popup, /fromPhone: !!f\.fromPhone,\s*phoneFid: f\.phoneFid \|\| null,/);
  assert.match(bg, /"autofill_phone_upload_" \+ tabId,/);
});
