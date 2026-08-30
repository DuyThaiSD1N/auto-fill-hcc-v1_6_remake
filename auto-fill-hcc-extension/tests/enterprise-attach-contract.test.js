// Engine đính kèm được DÙNG CHUNG cho hai cổng: HkdOnline (ClientID "ctl00_C_X") và cổng ĐKKD qua
// mạng (ClientID ngắn "C_X"). Hai lỗi đã thực sự xảy ra và test này chặn tái diễn:
//
// 1. Tra control bằng id CỨNG "ctl00_C_..." -> trên cổng doanh nghiệp trả null, engine THOÁT IM LẶNG
//    (đúng ca nút "Tải lên" ctl00_C_BtnSaveNoTyple làm luồng kẹt mãi ở pha khai loại).
// 2. Nhãn loại tài liệu lệch giữa backend và extension -> chooseOption() khớp theo NHÃN nên lệch một
//    ký tự là không khai được loại nào, cũng không có lỗi nào hiện ra.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const source = fs.readFileSync(
  path.join(root, "content", "procedures", "business-registration.js"),
  "utf8",
);

// ---- 1. Vùng đính kèm không được tra control bằng ClientID cứng ----
const attachStart = source.indexOf('const ATTACH_KEY = "autofill_attachall_state"');
const attachEnd = source.indexOf("H.detectBusinessPageKey =", attachStart);
assert.ok(attachStart > 0 && attachEnd > attachStart, "Không tách được vùng engine đính kèm");
const attachRegion = source.slice(attachStart, attachEnd);

// Chỉ bắt id VIẾT CỨNG; chính helper attachElById dùng template `ctl00_C_${suffix}` nên phải loại
// trừ bằng cách yêu cầu phần sau tiền tố chỉ gồm ký tự định danh (không có "${").
const hardcoded = [...attachRegion.matchAll(/getElementById\(\s*["'`]ctl00_C_[A-Za-z0-9_]+["'`]/g)]
  .map((m) => m[0]);
assert.deepEqual(
  hardcoded, [],
  "Engine đính kèm phải tra control qua attachElById() để chạy được trên CẢ HAI cổng "
  + `(id cứng còn sót: ${hardcoded.join(", ")})`,
);
assert.ok(
  attachRegion.includes("function attachElById"),
  "Thiếu helper attachElById — engine sẽ chỉ chạy được trên HkdOnline",
);

// ---- 2. Nhãn loại tài liệu phải khớp ĐÚNG backend ----
const plannerSource = fs.readFileSync(
  path.join(root, "..", "auto-fill-hcc-backend", "app", "pipelines", "thanh_lap_ctcp",
    "attach", "planner.py"),
  "utf8",
);
const labelBlock = plannerSource.slice(
  plannerSource.indexOf("_LABEL_BY_CAT = {"),
  plannerSource.indexOf("_LLM_TO_CAT = {"),
);
const backendLabels = Object.fromEntries(
  [...labelBlock.matchAll(/_CAT_(\w+):\s*"([^"]+)"/g)].map((m) => [m[1], m[2]]),
);

// Tên hằng ở backend (_CAT_BUSREG...) khác key category, nên đối chiếu qua chính giá trị category.
const catValues = Object.fromEntries(
  [...plannerSource.matchAll(/_CAT_(\w+)\s*=\s*"([^"]+)"/g)].map((m) => [m[1], m[2]]),
);
const backendByCategory = Object.fromEntries(
  Object.entries(backendLabels).map(([constName, label]) => [catValues[constName], label]),
);

const feTypeBlock = attachRegion.slice(
  attachRegion.indexOf("const ATTACH_TYPE = {"),
  attachRegion.indexOf("async function getAttachAllState"),
);
const feLabels = Object.fromEntries(
  [...feTypeBlock.matchAll(/(\w+):\s*\{[^}]*label:\s*"([^"]+)"/g)].map((m) => [m[1], m[2]]),
);

for (const [category, label] of Object.entries(backendByCategory)) {
  assert.ok(
    feLabels[category],
    `Category "${category}" backend trả về nhưng ATTACH_TYPE của extension chưa khai -> không khai được loại`,
  );
  assert.equal(
    feLabels[category], label,
    `Nhãn loại "${category}" lệch giữa backend và extension — chooseOption() khớp theo nhãn nên sẽ trượt`,
  );
}

console.log(`enterprise-attach-contract: ${Object.keys(backendByCategory).length} nhãn khớp backend, `
  + "không còn ClientID cứng passed");
