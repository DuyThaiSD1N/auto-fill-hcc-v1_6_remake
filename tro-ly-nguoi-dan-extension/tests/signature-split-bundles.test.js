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
      { fileIndex: 2, documentName: "Căn cước", componentIndex: 2, target: "existing" },
    ]
  );

  assert.equal(built.error, undefined);
  assert.equal(built.bundles.length, 2, "Số hồ sơ phải bằng số văn bản STT1");
  assert.deepEqual(
    plain(built.bundles.map((bundle) => bundle.files.map((item) => item.name))),
    [["van-ban-a.pdf", "can-cuoc.pdf"], ["van-ban-b.pdf", "can-cuoc.pdf"]]
  );
  assert.deepEqual(
    plain(built.bundles.map((bundle) => bundle.attachments.map((item) => item.componentIndex))),
    [[1, 2], [null, 2]]
  );
  assert.ok(built.bundles.every((bundle) => bundle.files[1] === identity),
    "Mọi hồ sơ phải dùng chung giấy tờ tùy thân ở STT2");

  const identityOnly = await context.buildSignatureSplitBundles(
    [identity],
    [{ fileIndex: 0, documentName: "Căn cước", componentIndex: 2, target: "existing" }]
  );
  assert.match(identityOnly.error, /STT1/);
  console.log("TLND signature split bundles passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
