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

  console.log("signature split bundles: identity only on first dossier and no-identity fallback passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
