// Trang nộp hồ sơ mới của Cổng DVC quốc gia (SurveyJS): form + Thành phần hồ sơ cùng một trang →
// nút "Điền biểu mẫu và đính kèm hồ sơ" điền xong đính kèm luôn. Chỉ hiện khi CHÍNH trang đang mở
// là form mới (cùng mã thủ tục còn chạy trên cổng cũ dạng nhiều bước).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const popup = fs.readFileSync(path.join(root, "popup.js"), "utf8");
const html = fs.readFileSync(path.join(root, "popup.html"), "utf8");
const content = fs.readFileSync(path.join(root, "content.js"), "utf8");

const fn = popup.slice(popup.indexOf("function fillAttachAvailable()"), popup.indexOf("// Hỏi THẲNG một lần"));

function available({ kind, cfg = {}, attachMode = false, business = false }) {
  const ctx = vm.createContext({
    pageFormKind: kind,
    currentConfig: () => ({ hasAttachmentStep: true, ...cfg }),
    isAttachMode: () => attachMode,
    currentBusinessPages: () => (business ? [{}] : []),
  });
  vm.runInContext(`${fn}\nthis.ok = fillAttachAvailable();`, ctx);
  return ctx.ok;
}

test("chỉ hiện ở trang form mới, thủ tục có bước đính kèm", () => {
  assert.equal(available({ kind: "surveyjs" }), true);
  assert.equal(available({ kind: "legacy" }), false, "cổng cũ nhiều bước: đính kèm ở trang sau");
  assert.equal(available({ kind: "" }), false);
  assert.equal(available({ kind: "surveyjs", cfg: { hasAttachmentStep: false } }), false);
  assert.equal(available({ kind: "surveyjs", cfg: { fillWithAttach: true } }), false, "nút quét đã tự đính");
  assert.equal(available({ kind: "surveyjs", attachMode: true }), false);
  assert.equal(available({ kind: "surveyjs", business: true }), false);
});

test("có nút trên panel, ẩn mặc định, nằm CUỐI nhóm nút và nổi hơn", () => {
  assert.match(html, /<button id="fillAttachBtn" class="fill-attach-btn" hidden/);
  assert.match(html, /Điền\s+biểu mẫu và đính kèm hồ sơ<\/button>/);
  assert.ok(html.indexOf('id="fillAttachBtn"') > html.indexOf('id="attachStepBtn"'), "phải nằm dưới nút Đính kèm giấy tờ");
  const css = fs.readFileSync(path.join(root, "popup.css"), "utf8");
  assert.match(css, /\.fill-attach-btn \{[^}]*font-weight: 700;[^}]*background: #e8590c;/);
});

test("trang trả loại form (chỉ khung trên cùng); panel hỏi thẳng, không tiêm lại script", () => {
  assert.match(content, /msg\?\.action === "getFormKind"\) \{\s*if \(window\.top !== window\) return;\s*sendResponse\(\{ ok: true, formKind: detectFormKind\(\) \|\| "" \}\);/);
  const probe = popup.slice(popup.indexOf("async function probeFormKind()"), popup.indexOf("setInterval(() => { void probeFormKind(); }"));
  assert.match(probe, /chrome\.tabs\.sendMessage\(tabId, \{ action: "getFormKind" \}/);
  assert.ok(!/sendToContent\(/.test(probe));
});

test("bấm nút: hỏi đồng ý trước, rồi đi chung đường quét–điền và đính kèm sau khi điền", () => {
  const click = popup.slice(popup.indexOf('fillAttachBtn.addEventListener("click"'), popup.indexOf("ocrBtn.addEventListener(\"click\""));
  assert.match(click, /if \(!\(await requireConsent\(fillAttachBtn\)\)\) return;\s*fillAttachRequested = true;\s*ocrBtn\.click\(\);/);
  assert.match(popup, /ocrBtn\.addEventListener\("click", async \(\) => \{\s*if \(window\.__AUTOFILL_HCC_POPUP_BUSY__\) return;[\s\S]{0,200}const attachAfter = fillAttachRequested;\s*fillAttachRequested = false;/);
  assert.match(popup, /if \(cfg\.fillWithAttach \|\| attachAfter\) await attachAfterFill\(fillOutcome, res\.sessionId\);/);
});
