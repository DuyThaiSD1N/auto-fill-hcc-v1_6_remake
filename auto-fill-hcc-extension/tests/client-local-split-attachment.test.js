const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const popup = fs.readFileSync(path.join(root, "popup.js"), "utf8");
const content = fs.readFileSync(path.join(root, "content.js"), "utf8");
const helpersStart = popup.indexOf("function planItemForFile");
const helpersEnd = popup.indexOf("\n// Tách hồ sơ: bundle[0]", helpersStart);
assert.ok(helpersStart >= 0 && helpersEnd > helpersStart, "Không tìm thấy helper local split");

const context = { window: {}, PdfConvert: null };
vm.createContext(context);
vm.runInContext(
  popup.slice(helpersStart, helpersEnd) +
    "\nthis.clientLocalDocumentName = clientLocalDocumentName;" +
    "\nthis.buildClientLocalSplitPlan = buildClientLocalSplitPlan;" +
    "\nthis.buildDefaultSplitBundles = buildDefaultSplitBundles;",
  context
);

function payload(name) {
  return {
    name,
    type: "application/pdf",
    role: "attachment",
    dataUrl: "data:application/pdf;base64,QUJD",
  };
}

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

const decomposed = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM_c.pdf";
const normalized = context.clientLocalDocumentName(decomposed);
assert.equal(normalized, normalized.normalize("NFC"));
assert.ok(normalized.length <= 50);
assert.match(normalized, /^[\p{L}\p{N}_\-\s]+$/u);

const sourceFiles = [
  payload(decomposed),
  payload("CCCD_ban_dich_can_chung_thuc.pdf"),
  payload("Ten rat dai ".repeat(10) + ".pdf"),
];
const built = context.buildClientLocalSplitPlan(sourceFiles, {
  componentName: "Bản dịch và giấy tờ, văn bản cần dịch.",
  componentIndex: 1,
});

assert.equal(built.error, undefined);
assert.equal(built.files.length, 3);
assert.equal(built.attachments.length, 3);
assert.ok(built.attachments.every((item) => item.componentIndex === 1));
assert.ok(built.attachments.every((item) => item.target === "existing"));
assert.ok(built.attachments.every((item) => item.forceFirstRow === true));
assert.ok(built.attachments.every((item) => item.documentName.length <= 50));
// Đa tab (mặc định): appendOnOccupied=false (mỗi tab 1 hồ sơ, ô trống → đính 1 file).
assert.ok(built.attachments.every((item) => item.appendOnOccupied === false),
  "đa tab: appendOnOccupied phải false");

// 1 tab (gộp): tất cả file vào cùng hồ sơ → appendOnOccupied=true để file sau tự thêm thành phần mới.
const mergeBuilt = context.buildClientLocalSplitPlan(sourceFiles, {
  componentName: "Bản dịch và giấy tờ, văn bản cần dịch.",
  componentIndex: 1,
}, { merge: true });
assert.equal(mergeBuilt.error, undefined);
assert.equal(mergeBuilt.attachments.length, 3);
assert.ok(mergeBuilt.attachments.every((item) => item.appendOnOccupied === true),
  "1 tab: appendOnOccupied phải true để gộp vào 1 hồ sơ");
assert.ok(mergeBuilt.attachments.every((item) => item.componentIndex === 1 && item.forceFirstRow === true));

const bundles = context.buildDefaultSplitBundles(built.files, built.attachments);
assert.equal(bundles.length, 3, "N file phải tạo đúng N bundle/tab");
assert.deepEqual(
  plain(bundles.map((bundle) => bundle.files.length)),
  [1, 1, 1],
  "Mỗi tab chỉ được chứa đúng một file"
);
assert.deepEqual(
  plain(bundles.map((bundle) => bundle.planItems.length)),
  [1, 1, 1]
);

// Kể cả tên có chữ CCCD, cờ forceFirstRow vẫn đi qua bundle để content không đẩy sang STT2.
assert.equal(bundles[1].planItems[0].forceFirstRow, true);
assert.equal(bundles[1].planItems[0].componentIndex, 1);
assert.match(
  content,
  /!item\?\.forceFirstRow &&\s*isIdentityAttachmentItem\(item\)/,
  "Content phải ưu tiên forceFirstRow trước heuristic CCCD"
);

const localBranchStart = popup.indexOf("if (isClientLocalSplitProcedure(cfg))");
const serverPlanCall = popup.indexOf("api.attachmentPlan", localBranchStart);
const localBranch = popup.slice(localBranchStart, serverPlanCall);
assert.match(localBranch, /api\.clientAttachmentTrace/);
assert.doesNotMatch(localBranch, /dataUrl/);
assert.match(localBranch, /attachSplitAcrossTabs/);
// CTV phải có 2 nhánh theo ô tick: đa tab (attachSplitMode) vs 1 tab (gộp vào hồ sơ hiện tại).
assert.match(localBranch, /attachSplitMode/, "CTV phải nhánh theo ô tick tách/gộp");
assert.match(localBranch, /buildLocalMergeAttachMessage/, "thiếu nhánh đính 1 tab (gộp)");
assert.match(localBranch, /merge: !splitOn/, "buildClientLocalSplitPlan phải nhận cờ merge khi 1 tab");

// Ô tick "tách hồ sơ" phải HIỆN cho case local (CTV) — trước đây bị ẩn cứng.
const splitRowLine = popup.slice(popup.indexOf("if (splitModeRow) {"), popup.indexOf("if (splitModeRow) {") + 200);
assert.doesNotMatch(splitRowLine, /!isClientLocalSplitProcedure\(\)/,
  "splitModeRow không được ẩn cứng với case local nữa");

// Gộp 1 tab: các thành phần thêm mới KHÔNG được trùng tên → engine đánh số " 2"/" 3"…
// Bao cả 2 đường: hàng trống form tự thêm (rowForPlanItem) và nút "Thêm thành phần" (addAttachmentComponent).
assert.match(content, /function uniqueComponentName\(/,
  "thiếu helper đánh số tên thành phần trùng");
assert.match(content, /function ensureUniqueEmptyRowName\(/,
  "thiếu đánh số cho hàng trống form tự thêm (đường chính của CTV gộp)");
assert.match(content, /await ensureUniqueEmptyRowName\(emptyExistingRow, componentName\)/,
  "rowForPlanItem phải đánh số hàng trống trước khi đính");
assert.match(content, /const uniqueName = uniqueComponentName\(componentName\)/,
  "addAttachmentComponent phải dùng tên duy nhất");
// Lượt CHỐT sau khi đính: đánh số vào ô <input> tên của các dòng thêm mới trùng tên (bản dịch CTV).
assert.match(content, /function renumberDuplicateComponentNameInputs\(/,
  "thiếu lượt chốt đánh số ô tên input trùng");
assert.match(content, /await renumberDuplicateComponentNameInputs\(\)/,
  "attachFilesByPlan phải gọi lượt chốt đánh số sau vòng đính");
assert.match(content, /await sleep\(650\)/,
  "phải chờ qua debounce ~500ms để cổng commit tên, tránh React revert");

const consentStart = popup.indexOf("async function requireConsent(triggerEl)");
const consentEnd = popup.indexOf("\nfunction escapeConsent", consentStart);
const consentBranch = popup.slice(consentStart, consentEnd);
assert.ok(consentStart >= 0 && consentEnd > consentStart, "Không tìm thấy chốt consent");
assert.match(consentBranch, /currentConfig\(\)\?\.skipConsent === true/);
assert.ok(
  consentBranch.indexOf("skipConsent") < consentBranch.indexOf("resolveConsentContext"),
  "Phải miễn consent trước khi đọc danh tính trên cổng"
);

console.log("client local split attachment: no consent, Unicode-safe name and N files = N tabs passed");
