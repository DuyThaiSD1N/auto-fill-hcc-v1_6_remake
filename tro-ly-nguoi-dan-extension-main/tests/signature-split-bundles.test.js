const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
const helpersStart = sidebar.indexOf("function planItemForSplitFile");
const helpersEnd = sidebar.indexOf("\n  function splitQueueReport", helpersStart);
assert.ok(helpersStart >= 0 && helpersEnd > helpersStart, "Không tìm thấy helpers tách hồ sơ chữ ký");

const context = { window: {} };
vm.createContext(context);
vm.runInContext(
  sidebar.slice(helpersStart, helpersEnd)
    + "\nthis.buildSignatureSplitBundles = buildSignatureSplitBundles;",
  context
);

function file(name) {
  return { name, type: "application/pdf", dataUrl: `data:application/pdf;base64,${name}` };
}

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

(async () => {
  const documentA = file("van-ban-a.pdf");
  const documentB = file("van-ban-b.pdf");
  const identity = file("can-cuoc.pdf");
  const built = await context.buildSignatureSplitBundles(
    [documentA, documentB, identity],
    [
      { fileIndex: 0, documentName: "Văn bản A", componentIndex: 1, target: "existing" },
      { fileIndex: 1, documentName: "Văn bản B", componentIndex: null, target: "new" },
      { fileIndex: 2, documentName: "Căn cước", componentIndex: 9, target: "existing" },
    ]
  );

  assert.equal(built.error, undefined);
  assert.equal(built.bundles.length, 2, "Số hồ sơ phải bằng số văn bản STT1");
  assert.deepEqual(
    plain(built.bundles.map((bundle) => bundle.files.map((item) => item.name))),
    [["van-ban-a.pdf", "can-cuoc.pdf"], ["van-ban-b.pdf"]]
  );
  assert.deepEqual(
    plain(built.bundles.map((bundle) => bundle.attachments.map((item) => item.componentIndex))),
    [[1, 2], [null]]
  );
  assert.equal(built.bundles[0].files[1], identity,
    "Giấy tờ tùy thân chỉ được đính STT2 ở hồ sơ đầu tiên");
  assert.equal(built.bundles[1].files.length, 1,
    "Hồ sơ tiếp theo không được đính lặp giấy tờ tùy thân");

  const matched = await context.buildSignatureSplitBundles(
    [
      file("uy-quyen-zhou.pdf"),
      file("cccd-ho-chieu-zhou.pdf"),
      file("uy-quyen-hsieh.pdf"),
      file("cccd-ho-chieu-hsieh.pdf"),
      file("uy-quyen-yi.pdf"),
      file("cccd-ho-chieu-yi.pdf"),
    ],
    [
      { fileIndex: 0, bundleId: "signature-1", bundleRole: "signature_document", documentName: "Văn bản ủy quyền Zhou" },
      { fileIndex: 1, bundleId: "signature-1", bundleRole: "identity", identityScope: "matched", documentName: "Hộ chiếu Zhou Yang" },
      { fileIndex: 2, bundleId: "signature-2", bundleRole: "signature_document", documentName: "Văn bản ủy quyền Hsieh" },
      { fileIndex: 3, bundleId: "signature-2", bundleRole: "identity", identityScope: "matched", documentName: "Hộ chiếu Hsieh Tse-Yu" },
      { fileIndex: 4, bundleId: "signature-3", bundleRole: "signature_document", documentName: "Văn bản ủy quyền Yi" },
      { fileIndex: 5, bundleId: "signature-3", bundleRole: "identity", identityScope: "matched", documentName: "Hộ chiếu Yi Tingkun" },
    ]
  );

  assert.equal(matched.error, undefined);
  assert.deepEqual(
    plain(matched.bundles.map((bundle) => bundle.files.map((item) => item.name))),
    [
      ["uy-quyen-zhou.pdf", "cccd-ho-chieu-zhou.pdf"],
      ["uy-quyen-hsieh.pdf", "cccd-ho-chieu-hsieh.pdf"],
      ["uy-quyen-yi.pdf", "cccd-ho-chieu-yi.pdf"],
    ]
  );
  assert.deepEqual(
    plain(matched.bundles.map((bundle) => bundle.attachments.map((item) => item.componentIndex))),
    [[1, 2], [1, 2], [1, 2]]
  );

  const shared = await context.buildSignatureSplitBundles(
    [file("giay-to-1.pdf"), file("giay-to-2.pdf"), file("cccd-dung-chung.pdf")],
    [
      { fileIndex: 0, bundleId: "signature-1", bundleRole: "signature_document", documentName: "Giấy tờ 1" },
      { fileIndex: 1, bundleId: "signature-2", bundleRole: "signature_document", documentName: "Giấy tờ 2" },
      { fileIndex: 2, bundleId: "signature-1", bundleRole: "identity", identityScope: "shared", documentName: "CCCD dùng chung" },
    ]
  );

  assert.equal(shared.error, undefined);
  assert.deepEqual(
    plain(shared.bundles.map((bundle) => bundle.files.map((item) => item.name))),
    [["giay-to-1.pdf", "cccd-dung-chung.pdf"], ["giay-to-2.pdf"]]
  );

  const unsafeLegacy = await context.buildSignatureSplitBundles(
    [file("giay-to.pdf"), file("cccd-a.pdf"), file("cccd-b.pdf")],
    [
      { fileIndex: 0, documentName: "Giấy tờ", componentIndex: 1 },
      { fileIndex: 1, documentName: "CCCD A", componentIndex: 2 },
      { fileIndex: 2, documentName: "CCCD B", componentIndex: 2 },
    ]
  );
  assert.match(unsafeLegacy.error, /bundle|quan hệ/i);

  const identityOnly = await context.buildSignatureSplitBundles(
    [identity],
    [{ fileIndex: 0, documentName: "Căn cước", componentIndex: 2, target: "existing" }]
  );
  assert.match(identityOnly.error, /STT1/);
  // Sự cố Nghĩa Hưng 21/09/2026: BE bản cũ vẫn gửi tệp KHÔNG có bundleId (giấy tùy thân không
  // khớp người ký nào). Bỏ RIÊNG tệp đó rồi đính tiếp, thay vì hủy cả lượt làm mất sạch tệp lành.
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

  // Bỏ hết tệp lạc mà không còn văn bản STT1 nào thì vẫn phải dừng — không có gì để đính.
  const chiToanTepLac = await context.buildSignatureSplitBundles(
    [file("cccd-a.pdf"), file("cccd-b.pdf")],
    [
      { fileIndex: 0, documentName: "CCCD A", componentIndex: 2, bundleRole: "identity" },
      { fileIndex: 1, documentName: "CCCD B", componentIndex: 2, bundleId: "signature-1",
        bundleRole: "identity" },
    ]
  );
  assert.match(chiToanTepLac.error, /chứng thực chữ ký|STT1/i);

  console.log("TLND signature split bundles passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
