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
  /if \(!item\?\.forceFirstRow && isIdentityAttachmentItem\(item\)\)/,
  "Content phải ưu tiên forceFirstRow trước heuristic CCCD"
);

const localBranchStart = popup.indexOf("if (isClientLocalSplitProcedure(cfg))");
const serverPlanCall = popup.indexOf("api.attachmentPlan", localBranchStart);
const localBranch = popup.slice(localBranchStart, serverPlanCall);
assert.match(localBranch, /api\.clientAttachmentTrace/);
assert.doesNotMatch(localBranch, /dataUrl/);
assert.match(localBranch, /attachSplitAcrossTabs/);

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
