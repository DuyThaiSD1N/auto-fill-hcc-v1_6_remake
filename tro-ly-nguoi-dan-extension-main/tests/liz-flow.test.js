// Contract luồng trang nộp một trang của cổng Bộ VHTTDL (dichvucong.bvhttdl.gov.vn, form liz): bổ sung ô
// (content/liz/field-review.js), tích cam kết + gạt VNPost + điền người nhận + bấm nộp (content/liz/one-page.js).
// BE (chat/tu_phap_moi.py, registry lizFlow) chỉ bật khi sidebar khai supportsLizFlow.
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const read = (p) => fs.readFileSync(path.join(root, p), "utf8");
const strip = (src) => src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const manifest = JSON.parse(read("manifest.json"));
const sidebar = strip(read("sidebar.js"));
const review = strip(read("content/liz/field-review.js"));
const onePage = strip(read("content/liz/one-page.js"));
const fillLiz = strip(read("content/fill-liz.js"));
const guided = strip(read("content/guided-steps.js"));
const attachCore = strip(read("content/attach-core.js"));

test("manifest nạp 2 file liz sau fill-core / fill-liz / field-review (con trỏ dùng chung)", () => {
  const js = manifest.content_scripts[0].js;
  for (const file of ["content/liz/field-review.js", "content/liz/one-page.js"]) {
    assert.ok(js.includes(file), `${file} chưa được inject`);
    for (const dep of ["content/fill-core.js", "content/fill-liz.js", "content/field-review.js"]) {
      assert.ok(js.indexOf(file) > js.indexOf(dep), `${file} phải nạp SAU ${dep}`);
    }
  }
  assert.ok(manifest.content_scripts[0].matches.includes("https://dichvucong.bvhttdl.gov.vn/*"));
});

test("sidebar khai supportsLizFlow, chuyển nhãn cam kết + trạng thái VNPost xuống trang, báo lại kết quả tích", () => {
  assert.match(sidebar, /supportsLizFlow: true/);
  assert.match(sidebar, /action: "guidedSubmit", commitLabel: a\?\.commitLabel \|\| ""/);
  assert.match(sidebar, /a\.type === "guided_submit"\) \{\s*setTimeout\(\(\) => \{ void runGuidedSubmit\(a\); \}, 0\);/);
  assert.match(sidebar, /commitLabel: a\.commitLabel \|\| "",\s*\.\.\.\(typeof a\.postOffice === "boolean" \? \{ postOffice: a\.postOffice \} : \{\}\)/);
  assert.match(sidebar, /\.\.\.\(typeof res\?\.commit === "boolean" \? \{ commit: res\.commit \} : \{\}\)/);
});

test("fill-liz.js export hàm đọc ô cho ảnh chụp form và hàm điền MỘT ô cho bộ bổ sung", () => {
  assert.match(fillLiz, /H\.readLizField = readLizField;/);
  assert.match(fillLiz, /H\.fillLizFieldElement = fillLizFieldElement;/);
  assert.match(fillLiz, /if \(matField\.querySelector\("mat-select"\)\) return fillLizSelect\(matField, value\);/);
});

test("bộ bổ sung ô liz chỉ trả lời trên trang liz của cổng Bộ VHTTDL, cùng giao thức fieldReview*", () => {
  assert.match(review, /const ourPage = \(\) => location\.hostname === HOST && H\.detectFormKind\?\.\(\) === "liz";/);
  assert.match(review, /if \(!action\.startsWith\("fieldReview"\)\) return;\s*if \(!ourPage\(\)\) return;/);
  for (const action of ["fieldReviewMark", "fieldReviewStop", "fieldReviewNext"]) {
    assert.ok(review.includes(`action === "${action}"`), `thiếu ${action}`);
  }
  assert.match(review, /H\.fillLizFieldElement\(slot\.mf, value\)/);
  assert.match(review, /H\.fieldReviewPointer\?\.focus\(slot\.mf\)/);
  // Ô có ô lọc (danh sách xã) hỏi như ô gõ tự do — danh sách chỉ nạp một phần.
  assert.match(review, /search \? \{ free: true, options: \[\] \}/);
});

test("chặng cuối liz: tích cam kết trước, gạt VNPost theo postOffice, điền người nhận, soát ô rồi mới bấm nộp", () => {
  assert.match(onePage, /if \(!\["selectResultMethod", "guidedSubmit", "lizCommitWatch", "lizCommitTick"\]\.includes\(action\) \|\| !ourPage\(\)\) \{\s*return;/);
  assert.match(onePage, /const commit = msg\.commitLabel \? await tickCommit\(msg\.commitLabel\)/);
  assert.match(onePage, /if \(typeof msg\.postOffice !== "boolean"\) return/);
  assert.match(onePage, /input\[type="checkbox"\]\[name="post_office"\]/);
  for (const name of ["recipient_name", "recipient_phone", "recipient_address", "recipient_commune_id"]) {
    assert.ok(onePage.includes(`name="${name}"`), `thiếu ô người nhận ${name}`);
  }
  // Nộp: tích lại cam kết → ô bắt buộc trống thì KHÔNG bấm → chờ nút hết khoá → bấm.
  const submit = onePage.slice(onePage.indexOf("async function submit("));
  const order = ["tickCommit(", "requiredEmpty()", "clicked: false, missing", "!b.disabled", "button.click()"]
    .map((s) => submit.indexOf(s));
  assert.ok(order.every((i, k) => i >= 0 && (k === 0 || i > order[k - 1])), `thứ tự bước nộp sai: ${order}`);
});

test("guided-steps.js không bấm thẳng nút nộp trên trang liz (one-page.js soát trước)", () => {
  assert.match(guided, /if \(submit && window\.__TLND__\?\.isLizOnePage\?\.\(\)\) return;/);
});

test("trang liz có bảng thành phần hồ sơ (input file trong app-upload-flie-multi) → nhận là trang đính kèm", () => {
  const gate = attachCore.slice(attachCore.indexOf("function hasAttachmentTarget()"));
  assert.match(gate.slice(0, 1500), /app-upload-flie-multi input\[type="file"\]/);
});

// Đính kèm lại trên trang liz: chạy THẬT clearPreviousAttachments của attach-core.js trên bảng giả. Mỗi tệp đã đính là
// <span><span class="file_name">…</span><div>…<button class="warn"><i class="fas fa-trash-alt"></i></button></div></span>.
function lizClearPage({ rows, confirm = false, stuck = [] }) {
  const src = read("content/attach-core.js");
  const from = src.indexOf("const LIZ_DIALOGS");
  const to = src.indexOf("\n// ===== Cổng DVC Bộ Công an", from);
  assert.ok(from >= 0 && to > from, "không cắt được đoạn gỡ tệp liz");
  const clicks = [];
  const dialogs = [];
  const trs = rows.map(({ upload = true, files = [] }) => {
    const row = { upload, names: [] };
    row.querySelector = (sel) => (sel === "app-upload-flie-multi" && row.upload ? {} : null);
    row.querySelectorAll = (sel) => (sel === ".file_name" ? [...row.names] : []);
    for (const file of files) {
      const name = { file };
      const remove = () => { row.names = row.names.filter((n) => n !== name); };
      const button = {
        disabled: false,
        click() {
          clicks.push(file);
          if (stuck.includes(file)) return;
          if (confirm) dialogs.push({ yes: { click() { dialogs.length = 0; remove(); } } });
          else remove();
        },
      };
      const icon = { closest: (sel) => (sel === "button" ? button : null) };
      name.parentElement = { querySelector: (sel) => (sel === "i.fa-trash-alt, i.fa-trash" ? icon : null) };
      row.names.push(name);
    }
    return row;
  });
  const ctx = {
    console: { log() {} },
    document: {
      querySelector: (sel) => (sel === "app-upload-flie-multi" && trs.some((r) => r.upload) ? {} : null),
      querySelectorAll: (sel) => (sel === "tr" ? trs : [...dialogs]),
    },
    isVisible: () => true,
    sleep: async () => {},
    waitFor: async (fn) => {
      for (let i = 0; i < 5; i++) {
        const value = fn();
        if (value) return value;
        await null;
      }
      return fn();
    },
    findButtonByText: (dialog, labels) => (labels.includes("Đồng ý") ? dialog.yes : null),
  };
  vm.createContext(ctx);
  vm.runInContext(`${src.slice(from, to)}\nthis.clearPreviousAttachments = clearPreviousAttachments;`, ctx);
  const left = () => trs.map((row) => row.names.map((n) => n.file));
  return { clear: ctx.clearPreviousAttachments, left, clicks, dialogs };
}

test("đính kèm lại liz: bấm thùng rác gỡ mọi tệp trong bảng thành phần, bảng khác không đụng", async () => {
  const page = lizClearPage({ rows: [
    { files: ["Ma-ket.pdf", "Ma-ket 2.pdf"] },
    { files: ["Ban phoi canh.pdf"] },
    { upload: false, files: ["Tep ngoai bang.pdf"] },
  ] });
  const res = await page.clear();
  assert.equal(res.removedFiles, 3);
  assert.deepEqual(page.left(), [[], [], ["Tep ngoai bang.pdf"]]);
  assert.ok(!page.clicks.includes("Tep ngoai bang.pdf"));
});

test("đính kèm lại liz: cổng hỏi lại trước khi xoá → bấm Đồng ý trên hộp mới mọc", async () => {
  const page = lizClearPage({ confirm: true, rows: [{ files: ["Thong bao.pdf", "Thong bao 2.pdf"] }] });
  const res = await page.clear();
  assert.equal(res.removedFiles, 2);
  assert.deepEqual(page.left(), [[]]);
  assert.equal(page.dialogs.length, 0);
});

test("đính kèm lại liz: tệp cổng không cho xoá thì bỏ qua, không lặp, vẫn gỡ tệp còn lại", async () => {
  const page = lizClearPage({ stuck: ["Khoa.pdf"], rows: [{ files: ["Khoa.pdf", "Gỡ được.pdf"] }] });
  const res = await page.clear();
  assert.equal(res.removedFiles, 1);
  assert.deepEqual(page.left(), [["Khoa.pdf"]]);
  assert.equal(page.clicks.filter((f) => f === "Khoa.pdf").length, 1);
});

// ── Chặng ô cam kết (sidebar khai supportsLizCommitSelf): BE dặn cần tích + nút cam "Tích ô cam kết" → trợ lý tích ô
// (lizCommitTick); công dân tự tích thì trang báo lizCommitChanged; nút nộp gửi commitSelf thì không tích hộ. Không con
// trỏ, không dòng gợi ý trên trang (user 10/11 bỏ chữ nền xanh). ──
test("sidebar khai supportsLizCommitSelf, chạy lệnh liz_commit_watch / liz_commit_check / liz_commit_tick, báo về BE", () => {
  assert.match(sidebar, /supportsLizCommitSelf: true/);
  assert.match(sidebar, /a\.type === "liz_commit_watch" \|\| a\.type === "liz_commit_check"/);
  assert.match(sidebar, /a\.type === "liz_commit_tick"\) \{\s*setTimeout\(\(\) => \{ void runLizCommitTick\(a\); \}, 0\);/);
  assert.match(sidebar, /action: "lizCommitWatch", commitLabel: a\.commitLabel \|\| "" \}/);
  assert.match(sidebar, /action: "lizCommitTick", commitLabel: a\.commitLabel \|\| "" \}/);
  assert.match(sidebar, /source: "tick", checked: !!res\?\.checked, found: !!res\?\.found/);
  assert.match(sidebar, /if \(source === "watch" && !res\?\.checked\) return;/);
  assert.match(sidebar, /msg\?\.__tlnd !== "lizCommitChanged" \|\| String\(sender\?\.tab\?\.id \|\| ""\) !== String\(TAB_ID\)/);
  const submit = sidebar.slice(sidebar.indexOf("async function runGuidedSubmit("));
  assert.match(submit.slice(0, 1500), /commitSelf: !!a\?\.commitSelf/);
  assert.match(submit.slice(0, 1500), /\.\.\.\(typeof res\?\.commit === "boolean" \? \{ commit: res\.commit \} : \{\}\)/);
});

test("one-page.js không dùng con trỏ / dòng gợi ý cho ô cam kết", () => {
  assert.doesNotMatch(onePage, /fieldReviewPointer/);
  assert.match(onePage, /"lizCommitWatch", "lizCommitTick"\]\.includes\(action\)/);
});

const COMMIT = "Tôi cam kết chịu trách nhiệm trước pháp luật về tính hợp pháp, chính xác của các giấy tờ có trong hồ sơ"
  + " và cung cấp đầy đủ thông tin có liên quan";

// Chạy THẬT content/liz/one-page.js trên trang giả: mỗi ô cam kết là <label> bọc <input type="checkbox">; bấm ô thì
// trang phát sự kiện change như trình duyệt.
function lizCommitPage(boxes) {
  const listeners = {};
  const sent = [];
  const pointed = [];
  const scrolled = [];
  let onMessage = null;
  const change = (input) => (listeners.change || []).forEach((fn) => fn({ target: input }));
  const inputs = boxes.map(({ checked = false, hidden = false, text = COMMIT }) => {
    const label = { textContent: ` ${text} `, scrollIntoView: () => { scrolled.push(label); } };
    let clicks = 0;
    const input = {
      type: "checkbox", checked, disabled: false,
      getClientRects: () => (hidden ? [] : [{}]),
      closest: (sel) => (sel === "label" ? label : null),
      click() { clicks += 1; this.checked = !this.checked; change(this); },
      get clicks() { return clicks; },
    };
    input.label = label;
    return input;
  });
  const ctx = {
    console, setTimeout, Promise,
    window: {},
    location: { hostname: "dichvucong.bvhttdl.gov.vn" },
    document: {
      querySelectorAll: (sel) => (sel === 'input[type="checkbox"]' ? inputs : []),
      querySelector: () => null,
      addEventListener: (type, fn) => { (listeners[type] = listeners[type] || []).push(fn); },
    },
    chrome: {
      runtime: {
        onMessage: { addListener: (fn) => { onMessage = fn; } },
        sendMessage: (msg, cb) => { sent.push(msg); if (cb) cb(); },
        lastError: undefined,
      },
    },
  };
  ctx.window.__TLND__ = {
    detectFormKind: () => "liz",
    fieldReviewPointer: {
      focus: async (el, hint) => { pointed.push({ el, hint }); },
      unfocus: () => { pointed.push("unfocus"); },
    },
  };
  vm.createContext(ctx);
  vm.runInContext(read("content/liz/one-page.js"), ctx);
  const call = (msg) => new Promise((resolve) => { onMessage(msg, {}, resolve); });
  return { inputs, sent, pointed, scrolled, call, change };
}

const wait = (ms) => new Promise((r) => setTimeout(r, ms));

test("ô cam kết: theo dõi không chỉ / không cuộn; công dân tự tích thì báo một lần, bỏ tích thì báo lại", async () => {
  const page = lizCommitPage([{ checked: false }]);
  const res = await page.call({ action: "lizCommitWatch", commitLabel: COMMIT });
  assert.deepEqual({ ...res }, { ok: true, found: true, checked: false });
  assert.equal(page.pointed.length, 0, "không con trỏ, không dòng gợi ý");
  assert.equal(page.scrolled.length, 0);
  assert.equal(page.inputs[0].clicks, 0, "theo dõi không tích");

  page.inputs[0].checked = true;
  page.change(page.inputs[0]);
  page.change(page.inputs[0]);
  await wait(350);
  assert.deepEqual(page.sent.map((m) => ({ ...m })), [{ __tlnd: "lizCommitChanged", checked: true }]);

  page.inputs[0].checked = false;
  page.change(page.inputs[0]);
  await wait(350);
  assert.deepEqual({ ...page.sent[1] }, { __tlnd: "lizCommitChanged", checked: false });
});

test("nút cam Tích ô cam kết: trợ lý cuộn tới ô rồi tích, trả checked=true, không báo trùng lizCommitChanged", async () => {
  const page = lizCommitPage([{ checked: false }]);
  const res = await page.call({ action: "lizCommitTick", commitLabel: COMMIT });
  assert.deepEqual({ ...res }, { ok: true, found: true, checked: true });
  assert.equal(page.inputs[0].clicks, 1);
  assert.equal(page.scrolled[0], page.inputs[0].label, "cuộn cho công dân thấy ô vừa tích");
  assert.equal(page.pointed.length, 0);
  await wait(350);
  assert.equal(page.sent.length, 0, "cú tích của trợ lý đã báo qua kết quả lệnh, không báo lần hai");
  // Đã tích sẵn thì không bấm lại (bấm lại là BỎ tích).
  const again = await page.call({ action: "lizCommitTick", commitLabel: COMMIT });
  assert.equal(again.checked, true);
  assert.equal(page.inputs[0].clicks, 1);
});

test("nút cam Tích ô cam kết: ô hiện hai lần thì tích cả hai; không có ô thì found=false", async () => {
  const twice = lizCommitPage([{ checked: false }, { checked: false }]);
  const res = await twice.call({ action: "lizCommitTick", commitLabel: COMMIT });
  assert.equal(res.checked, true);
  assert.deepEqual(twice.inputs.map((i) => i.checked), [true, true]);
  const none = lizCommitPage([{ checked: false, text: "Đề nghị nhận kết quả bản giấy tại nhà" }]);
  const empty = await none.call({ action: "lizCommitTick", commitLabel: COMMIT });
  assert.deepEqual({ ...empty }, { ok: true, found: false, checked: false });
  assert.equal(none.inputs[0].clicks, 0, "ô VNPost không phải ô cam kết");
});

test("ô cam kết: chưa được BE dặn thì không theo dõi; ô khác trên trang không tính", async () => {
  const page = lizCommitPage([{ checked: false }, { checked: false, text: "Đề nghị nhận kết quả bản giấy tại nhà" }]);
  page.inputs[0].checked = true;
  page.change(page.inputs[0]);
  await wait(350);
  assert.equal(page.sent.length, 0);
  await page.call({ action: "lizCommitWatch", commitLabel: COMMIT });
  page.inputs[1].checked = true;
  page.change(page.inputs[1]);
  await wait(350);
  assert.equal(page.sent.length, 0, "ô VNPost không phải ô cam kết");
});

test("ô cam kết hiện hai lần: chỉ xét ô đang hiện; không có ô thì báo found=false", async () => {
  const twice = lizCommitPage([{ checked: false, hidden: true }, { checked: true }]);
  const res = await twice.call({ action: "lizCommitWatch", commitLabel: COMMIT });
  assert.equal(res.checked, true);
  const none = lizCommitPage([{ checked: false, text: "Ô khác" }]);
  const empty = await none.call({ action: "lizCommitWatch", commitLabel: COMMIT });
  assert.deepEqual({ ...empty }, { ok: true, found: false, checked: false });
});

test("nút nộp commitSelf: ô cam kết chưa tích thì không tích hộ, không bấm, trả commit=false, cuộn tới ô", async () => {
  const page = lizCommitPage([{ checked: false }]);
  const res = await page.call({ action: "guidedSubmit", commitLabel: COMMIT, commitSelf: true });
  assert.deepEqual({ ...res, missing: [...res.missing] }, { ok: false, clicked: false, commit: false, missing: [] });
  assert.equal(page.inputs[0].checked, false);
  assert.equal(page.inputs[0].clicks, 0);
  assert.equal(page.scrolled[0], page.inputs[0].label);
  assert.equal(page.pointed.length, 0);
});

test("nút xoá tệp liz nhận theo icon thùng rác, không phải class warn (nút mdc-button cạnh nó cũng là warn)", () => {
  const fn = attachCore.slice(attachCore.indexOf("function lizAttachedFiles()"));
  assert.match(fn.slice(0, 600), /querySelector\("i\.fa-trash-alt, i\.fa-trash"\)\?\.closest\("button"\)/);
  assert.match(attachCore, /async function clearPreviousAttachments\(\) \{\s*if \(isLizAttachPage\(\)\) return await clearLizAttachedFiles\(\);/);
});
