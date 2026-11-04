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
  assert.match(onePage, /if \(!\["selectResultMethod", "guidedSubmit"\]\.includes\(action\) \|\| !ourPage\(\)\) return;/);
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

test("nút xoá tệp liz nhận theo icon thùng rác, không phải class warn (nút mdc-button cạnh nó cũng là warn)", () => {
  const fn = attachCore.slice(attachCore.indexOf("function lizAttachedFiles()"));
  assert.match(fn.slice(0, 600), /querySelector\("i\.fa-trash-alt, i\.fa-trash"\)\?\.closest\("button"\)/);
  assert.match(attachCore, /async function clearPreviousAttachments\(\) \{\s*if \(isLizAttachPage\(\)\) return await clearLizAttachedFiles\(\);/);
});
