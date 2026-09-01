const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const sidebar = fs.readFileSync(path.join(__dirname, "..", "sidebar.js"), "utf8");
const start = sidebar.indexOf("async function preparePdfPayload");
const end = sidebar.indexOf("\n  const SPLIT_ATTACH_PROCEDURES", start);
assert.ok(start >= 0 && end > start, "Không tìm thấy preparePdfPayload");

const calls = [];
const PdfConvert = {
  async composeSegmentsToPdf(files, segments, name) {
    calls.push({ kind: "segments", files, segments, name });
    return { name: `${name}.pdf`, type: "application/pdf", dataUrl: "data:application/pdf;base64,SPLIT" };
  },
  async mergeToPdf(files, name) {
    calls.push({ kind: "merge", files, name });
    return { name: `${name}.pdf`, type: "application/pdf", dataUrl: "data:application/pdf;base64,MERGED" };
  },
  isImage() { return false; },
};
const context = { window: { PdfConvert, PDFLib: {} }, PdfConvert, console, Array, Number };
vm.createContext(context);
vm.runInContext(sidebar.slice(start, end) + "\nthis.preparePdfPayload = preparePdfPayload;", context);

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

(async () => {
  const files = [{ name: "mixed.pdf", type: "application/pdf", dataUrl: "data:application/pdf;base64,MIXED" }];
  const result = await context.preparePdfPayload(files, [
    { fileIndex: 0, documentName: "CCCD", sourceSegments: [{ fileIndex: 0, pageIndexes: [0] }] },
    { fileIndex: 0, documentName: "Giấy khai sinh", sourceSegments: [{ fileIndex: 0, pageIndexes: [1, 2] }] },
  ]);

  assert.equal(result.files.length, 2);
  assert.deepEqual(plain(result.attachments.map((item) => item.fileIndex)), [0, 1]);
  assert.ok(result.attachments.every((item) => !Object.hasOwn(item, "sourceSegments")));
  assert.deepEqual(plain(calls.map((call) => call.segments?.[0]?.pageIndexes)), [[0], [1, 2]]);

  calls.length = 0;
  await context.preparePdfPayload(
    [files[0], { ...files[0], name: "back.pdf" }],
    [{ fileIndex: 0, documentName: "CCCD", sourceFileIndexes: [0, 1] }]
  );
  assert.equal(calls[0].kind, "merge", "Contract sourceFileIndexes cũ phải tiếp tục dùng mergeToPdf");

  const brokenPdfConvert = context.PdfConvert.composeSegmentsToPdf;
  context.PdfConvert.composeSegmentsToPdf = async () => { throw new Error("bad range"); };
  await assert.rejects(
    context.preparePdfPayload(files, [{ fileIndex: 0, sourceSegments: [{ fileIndex: 0, pageIndexes: [9] }] }]),
    /bad range/,
    "Lỗi tách trang phải dừng, không được đính nguyên PDF hỗn hợp"
  );
  context.PdfConvert.composeSegmentsToPdf = brokenPdfConvert;

  const noPdfContext = { window: {}, console, Array, Number };
  vm.createContext(noPdfContext);
  vm.runInContext(sidebar.slice(start, end) + "\nthis.preparePdfPayload = preparePdfPayload;", noPdfContext);
  await assert.rejects(
    noPdfContext.preparePdfPayload(files, [{ fileIndex: 0, sourceSegments: [{ fileIndex: 0, pageIndexes: [0] }] }]),
    /Thiếu bộ xử lý PDF/,
    "Không có pdf-lib phải báo lỗi, không được đính nguyên file hỗn hợp"
  );
})();
