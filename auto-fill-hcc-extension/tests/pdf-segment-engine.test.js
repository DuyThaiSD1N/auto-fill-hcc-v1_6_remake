const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const PDFLib = require("../vendor/pdf-lib.min.js");

const source = fs.readFileSync(path.join(__dirname, "..", "lib", "imageToPdf.js"), "utf8");
const context = {
  window: { PDFLib },
  atob: (value) => Buffer.from(value, "base64").toString("binary"),
  btoa: (value) => Buffer.from(value, "binary").toString("base64"),
  Uint8Array,
  Array,
  String,
  Number,
  Error,
};
vm.createContext(context);
vm.runInContext(source, context);

function dataUrlToBytes(dataUrl) {
  return Uint8Array.from(Buffer.from(dataUrl.split(",", 2)[1], "base64"));
}

(async () => {
  const input = await PDFLib.PDFDocument.create();
  input.addPage([100, 100]).drawRectangle({ x: 10, y: 10, width: 20, height: 20 });
  input.addPage([200, 200]).drawRectangle({ x: 20, y: 20, width: 30, height: 30 });
  input.addPage([300, 300]).drawRectangle({ x: 30, y: 30, width: 40, height: 40 });
  const bytes = await input.save();
  const file = {
    name: "mixed.pdf",
    type: "application/pdf",
    dataUrl: `data:application/pdf;base64,${Buffer.from(bytes).toString("base64")}`,
  };

  const output = await context.window.PdfConvert.composeSegmentsToPdf(
    [file],
    [{ fileIndex: 0, pageIndexes: [0, 2] }],
    "tach-trang"
  );
  const loaded = await PDFLib.PDFDocument.load(dataUrlToBytes(output.dataUrl));
  assert.equal(loaded.getPageCount(), 2);
  assert.ok(
    loaded.getPages().every((page) => Math.abs(page.getWidth() - 595.28) < 0.01),
    "Trang khác kích thước phải được đặt trên cùng khổ A4"
  );
  assert.ok(
    loaded.getPages().every((page) => Math.abs(page.getHeight() - 841.89) < 0.01),
    "Trang A4 phải có chiều cao thống nhất"
  );

  const uniformInput = await PDFLib.PDFDocument.create();
  uniformInput.addPage([200, 300]).drawRectangle({ x: 10, y: 10, width: 20, height: 20 });
  uniformInput.addPage([201, 299]).drawRectangle({ x: 10, y: 10, width: 20, height: 20 });
  const uniformBytes = await uniformInput.save();
  const uniformFile = {
    name: "uniform.pdf",
    type: "application/pdf",
    dataUrl: `data:application/pdf;base64,${Buffer.from(uniformBytes).toString("base64")}`,
  };
  const uniformOutput = await context.window.PdfConvert.composeSegmentsToPdf(
    [uniformFile],
    [{ fileIndex: 0, pageIndexes: null }],
    "giu-nguyen"
  );
  const uniformLoaded = await PDFLib.PDFDocument.load(dataUrlToBytes(uniformOutput.dataUrl));
  assert.deepEqual(
    uniformLoaded.getPages().map((page) => [page.getWidth(), page.getHeight()]),
    [[200, 300], [201, 299]],
    "Sai số scan nhỏ phải giữ nguyên trang nguồn"
  );

  await assert.rejects(
    context.window.PdfConvert.composeSegmentsToPdf([file], [{ fileIndex: 0, pageIndexes: [3] }], "bad"),
    /không hợp lệ/
  );

  console.log("pdf segment engine: heterogeneous pages normalized to A4, uniform pages preserved");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
