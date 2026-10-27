const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const popup = fs.readFileSync(path.join(root, "popup.js"), "utf8");
const helpersStart = popup.indexOf("function planItemForFile");
const helpersEnd = popup.indexOf("\n// Tách hồ sơ: bundle[0]", helpersStart);
assert.ok(helpersStart >= 0 && helpersEnd > helpersStart, "Không tìm thấy helpers tách hồ sơ chữ ký");

const context = {
  window: {},
  PdfConvert: null,
};
vm.createContext(context);
vm.runInContext(
  popup.slice(helpersStart, helpersEnd) +
    "\nthis.buildSignatureSplitBundles = buildSignatureSplitBundles;",
  context
);

function file(name) {
  return { name, type: "application/pdf", dataUrl: `data:application/pdf;base64,${name}` };
}

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

(async () => {
  const tla = file("TLA.pdf");
  const tlb = file("TLB.pdf");
  const cccd = file("CCCD.pdf");
  const withIdentity = await context.buildSignatureSplitBundles(
    [tla, tlb, cccd],
    [
      { fileIndex: 0, documentName: "TLA", componentIndex: 1, target: "existing" },
      { fileIndex: 2, documentName: "CCCD", componentIndex: 2, target: "existing" },
      { fileIndex: 1, documentName: "TLB", componentIndex: null, target: "new" },
    ]
  );
  assert.equal(withIdentity.error, undefined);
  assert.equal(withIdentity.bundles.length, 2, "Số tab phải bằng số tài liệu STT1");
  assert.deepEqual(
    plain(withIdentity.bundles.map((bundle) => bundle.files.map((item) => item.name))),
    [["TLA.pdf", "CCCD.pdf"], ["TLB.pdf"]]
  );
  assert.deepEqual(
    plain(withIdentity.bundles.map((bundle) => bundle.planItems.map((item) => item.componentIndex))),
    [[1, 2], [null]]
  );
  assert.equal(withIdentity.bundles[0].files[1], cccd, "CCCD chỉ dùng ở STT2 của tab đầu tiên");
  assert.equal(withIdentity.bundles[1].files.length, 1, "Tab tiếp theo không được đính lặp CCCD");

  const uqZhou = file("UQ-Zhou.pdf");
  const idZhou = file("ID-Zhou.pdf");
  const uqHsieh = file("UQ-Hsieh.pdf");
  const idHsieh = file("ID-Hsieh.pdf");
  const uqYi = file("UQ-Yi.pdf");
  const idYi = file("ID-Yi.pdf");
  const matched = await context.buildSignatureSplitBundles(
    [uqZhou, idZhou, uqHsieh, idHsieh, uqYi, idYi],
    [
      { fileIndex: 0, bundleId: "signature-1", bundleRole: "signature_document", componentIndex: 1 },
      { fileIndex: 1, bundleId: "signature-1", bundleRole: "identity", identityScope: "matched", componentIndex: 2 },
      { fileIndex: 2, bundleId: "signature-2", bundleRole: "signature_document", componentIndex: 1 },
      { fileIndex: 3, bundleId: "signature-2", bundleRole: "identity", identityScope: "matched", componentIndex: 2 },
      { fileIndex: 4, bundleId: "signature-3", bundleRole: "signature_document", componentIndex: 1 },
      { fileIndex: 5, bundleId: "signature-3", bundleRole: "identity", identityScope: "matched", componentIndex: 2 },
    ]
  );
  assert.equal(matched.error, undefined);
  assert.deepEqual(
    plain(matched.bundles.map((bundle) => bundle.files.map((item) => item.name))),
    [["UQ-Zhou.pdf", "ID-Zhou.pdf"], ["UQ-Hsieh.pdf", "ID-Hsieh.pdf"], ["UQ-Yi.pdf", "ID-Yi.pdf"]]
  );
  assert.deepEqual(
    plain(matched.bundles.map((bundle) => bundle.planItems.map((item) => item.componentIndex))),
    [[1, 2], [1, 2], [1, 2]]
  );

  const shared = await context.buildSignatureSplitBundles(
    [tla, cccd, tlb],
    [
      { fileIndex: 0, bundleId: "signature-1", bundleRole: "signature_document", componentIndex: 1 },
      { fileIndex: 1, bundleId: "signature-1", bundleRole: "identity", identityScope: "shared", componentIndex: 2 },
      { fileIndex: 2, bundleId: "signature-2", bundleRole: "signature_document", componentIndex: 1 },
    ]
  );
  assert.deepEqual(
    plain(shared.bundles.map((bundle) => bundle.files.map((item) => item.name))),
    [["TLA.pdf", "CCCD.pdf"], ["TLB.pdf"]]
  );

  const unsafeLegacy = await context.buildSignatureSplitBundles(
    [tla, tlb, idZhou, idHsieh],
    [
      { fileIndex: 0, componentIndex: 1 },
      { fileIndex: 1, componentIndex: null },
      { fileIndex: 2, componentIndex: 2 },
      { fileIndex: 3, componentIndex: 2 },
    ]
  );
  assert.match(unsafeLegacy.error, /chưa trả quan hệ ghép hồ sơ/i);

  const withoutIdentity = await context.buildSignatureSplitBundles(
    [tla, tlb],
    [
      { fileIndex: 0, documentName: "TLA", componentIndex: 1, target: "existing" },
      { fileIndex: 1, documentName: "TLB", componentIndex: null, target: "new" },
    ]
  );
  assert.equal(withoutIdentity.bundles.length, 2);
  assert.deepEqual(
    plain(withoutIdentity.bundles.map((bundle) => bundle.files.map((item) => item.name))),
    [["TLA.pdf"], ["TLB.pdf"]]
  );

  const identityOnly = await context.buildSignatureSplitBundles(
    [cccd],
    [{ fileIndex: 0, documentName: "CCCD", componentIndex: 2, target: "existing" }]
  );
  assert.match(identityOnly.error, /STT1/);

  // Sự cố Nghĩa Hưng 21/09/2026 (gặp ở bản Handfree, cùng máy đính kèm): kế hoạch có tệp KHÔNG
  // mang bundleId → trước đây hủy cả lượt, mất luôn các tệp lành, mà thử lại thì hỏng y hệt.
  const lac = await context.buildSignatureSplitBundles(
    [file("van-ban-1.pdf"), file("van-ban-2.pdf"), file("cccd-ban.pdf"), file("cccd-nguoi-la.pdf")],
    [
      { fileIndex: 0, documentName: "Trích lục", componentIndex: 1, target: "existing",
        bundleId: "signature-1", bundleRole: "signature_document" },
      { fileIndex: 1, documentName: "Bảo lãnh", componentIndex: 1, target: "existing",
        bundleId: "signature-2", bundleRole: "signature_document" },
      { fileIndex: 2, documentName: "Căn cước Ban", componentIndex: 2, target: "existing",
        bundleId: "signature-2", bundleRole: "identity", identityScope: "matched" },
      { fileIndex: 3, documentName: "Giấy tờ tùy thân 2", componentIndex: null, target: "new",
        bundleRole: "identity" },
    ]
  );
  assert.equal(lac.error, undefined, "một tệp lạc không được làm hỏng cả lượt");
  assert.deepEqual(
    plain(lac.bundles.map((bundle) => bundle.files.map((item) => item.name))),
    [["van-ban-1.pdf"], ["van-ban-2.pdf", "cccd-ban.pdf"]]
  );
  assert.deepEqual(lac.skippedNames, ["cccd-nguoi-la.pdf"], "phải nêu tên tệp bị bỏ");

  const chiToanTepLac = await context.buildSignatureSplitBundles(
    [file("cccd-a.pdf"), file("cccd-b.pdf")],
    [
      { fileIndex: 0, documentName: "CCCD A", componentIndex: 2, bundleRole: "identity" },
      { fileIndex: 1, documentName: "CCCD B", componentIndex: 2, bundleId: "signature-1",
        bundleRole: "identity" },
    ]
  );
  assert.match(chiToanTepLac.error, /chứng thực chữ ký|STT1/i);

  console.log("signature split bundles: shared, matched and safe legacy fallback passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
