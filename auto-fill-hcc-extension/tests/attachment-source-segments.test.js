const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const popup = fs.readFileSync(path.join(root, "popup.js"), "utf8");
const start = popup.indexOf("async function applyMergeGroups");
const end = popup.indexOf("\n// Đăng ký hộ kinh doanh", start);
assert.ok(start >= 0 && end > start, "Không tìm thấy applyMergeGroups");

const calls = [];
const PdfConvert = {
  async composeSegmentsToPdf(files, segments, name) {
    calls.push({ kind: "segments", files, segments, name });
    return {
      name: `${name}.pdf`,
      type: "application/pdf",
      dataUrl: `data:application/pdf;base64,${segments.map((item) => (item.pageIndexes || ["all"]).join("-")).join("_")}`,
    };
  },
  async mergeToPdf(files, name) {
    calls.push({ kind: "merge", files, name });
    return { name: `${name}.pdf`, type: "application/pdf", dataUrl: "data:application/pdf;base64,MERGED" };
  },
};
const context = { window: { PdfConvert }, PdfConvert, console };
vm.createContext(context);
vm.runInContext(popup.slice(start, end) + "\nthis.applyMergeGroups = applyMergeGroups;", context);

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

(async () => {
  const files = [{
    name: "mixed.pdf",
    type: "application/pdf",
    dataUrl: "data:application/pdf;base64,MIXED",
  }];
  const plan = [
    {
      fileIndex: 0,
      documentName: "Căn cước công dân",
      sourceSegments: [{ fileIndex: 0, pageIndexes: [0] }],
    },
    {
      fileIndex: 0,
      documentName: "Giấy khai sinh",
      sourceSegments: [{ fileIndex: 0, pageIndexes: [1, 2] }],
    },
  ];

  const result = await context.applyMergeGroups(files, plan);
  assert.equal(result.files.length, 2, "Một PDF hỗn hợp phải sinh hai file đích");
  assert.deepEqual(plain(result.attachments.map((item) => item.fileIndex)), [0, 1]);
  assert.ok(result.attachments.every((item) => !Object.hasOwn(item, "sourceSegments")));
  assert.deepEqual(plain(calls.map((call) => call.segments?.[0]?.pageIndexes)), [[0], [1, 2]]);

  calls.length = 0;
  const legacy = await context.applyMergeGroups(
    [files[0], { ...files[0], name: "back.pdf" }],
    [{ fileIndex: 0, documentName: "CCCD", sourceFileIndexes: [0, 1] }]
  );
  assert.equal(legacy.files.length, 1);
  assert.equal(calls[0].kind, "merge", "Contract sourceFileIndexes cũ vẫn phải dùng mergeToPdf");

  calls.length = 0;
  const fullFileSegments = await context.applyMergeGroups(
    [files[0], { ...files[0], name: "hoc-ba-2.pdf" }, { ...files[0], name: "hoc-ba-3.pdf" }],
    [{
      fileIndex: 0,
      documentName: "Học bạ Nguyễn Quốc Việt",
      sourceSegments: [
        { fileIndex: 0, pageIndexes: null },
        { fileIndex: 1, pageIndexes: null },
        { fileIndex: 2, pageIndexes: null },
      ],
    }]
  );
  assert.equal(fullFileSegments.files.length, 1, "Ba phần học bạ phải thành một PDF logic");
  assert.equal(calls[0].kind, "segments");
  assert.deepEqual(plain(calls[0].segments.map((item) => item.fileIndex)), [0, 1, 2]);

  console.log("attachment source segments: split mixed PDF, merge full files, preserve legacy merge passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
