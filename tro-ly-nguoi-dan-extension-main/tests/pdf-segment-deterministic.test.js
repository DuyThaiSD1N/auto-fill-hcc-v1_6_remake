const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const PDFLib = require(path.join(root, "vendor/pdf-lib.min.js"));

function loadPdfConvert() {
  const window = { PDFLib };
  const context = vm.createContext({ window, atob, btoa, Uint8Array, Array, Number, String, Error, Math, console });
  vm.runInContext(fs.readFileSync(path.join(root, "lib/imageToPdf.js"), "utf8"), context);
  return window.PdfConvert;
}

test("cắt cùng các trang hai lần ra đúng cùng một PDF (lượt đính lại nhận ra tệp đã có)", async () => {
  const doc = await PDFLib.PDFDocument.create();
  for (let i = 0; i < 3; i++) doc.addPage([200, 300]).drawText(`trang ${i + 1}`, { x: 20, y: 150 });
  const dataUrl = "data:application/pdf;base64," + Buffer.from(await doc.save()).toString("base64");
  const PdfConvert = loadPdfConvert();
  const source = [{ name: "hoso.pdf", type: "application/pdf", dataUrl }];
  const first = await PdfConvert.composeSegmentsToPdf(source, [{ fileIndex: 0, pageIndexes: [1, 2] }], "Giấy tờ");
  await new Promise((resolve) => setTimeout(resolve, 1100));
  const second = await PdfConvert.composeSegmentsToPdf(source, [{ fileIndex: 0, pageIndexes: [1, 2] }], "Giấy tờ");
  assert.equal(first.dataUrl, second.dataUrl);
});
