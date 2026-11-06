// Kết quả đính kèm theo từng tệp (no handfree): popup dựng danh sách tệp đã đính / tệp lỗi (tên gốc, tên đổi, lý do dễ
// hiểu) cho đính 1 tab và đa tab; panel thấp nên chỉ hiện dòng đỏ tóm tắt + tối đa 3 tệp lỗi, danh sách đủ nằm sau
// "Xem chi tiết"; đính 1 tab có nút đính lại riêng tệp lỗi. Engine content.js trả failedFiles theo fileIndex.
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const read = (p) => fs.readFileSync(path.join(root, p), "utf8");
const strip = (src) => src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const popupRaw = read("popup.js");
const popup = strip(popupRaw);
const content = strip(read("content.js"));
const background = strip(read("background.js"));
const html = read("popup.html");

const start = popupRaw.indexOf("const ATTACH_FAIL_REASON_TEXT = {");
const end = popupRaw.indexOf("\n}\n", popupRaw.indexOf("function splitFileOutcome(")) + 3;
const H = new Function(`${popupRaw.slice(start, end)}
  return { attachFailReason, attachFileOutcome, splitDossierFiles, splitFileOutcome };`)();

const FILES = [{ name: "Giay khai sinh.pdf" }, { name: "So ho khau.pdf" }, { name: "x.pdf" }];
const PLAN = [
  { fileIndex: 0, documentName: "Giấy khai sinh", sourceNames: ["IMG_1.jpg"] },
  { fileIndex: 1, documentName: "Sổ hộ khẩu", sourceNames: ["IMG_2.jpg", "IMG_3.jpg"] },
  { fileIndex: 2, documentName: "CCCD", sourceNames: ["cccd.jpg"] },
  { fileIndex: 0, virtualCopy: true, documentName: "Bản sao ảo" },
];

test("lỗi kỹ thuật của engine xếp về nhóm lý do dễ hiểu", () => {
  assert.equal(H.attachFailReason("Tổng dung lượng file không được quá 2.6MB"), "too_large");
  assert.equal(H.attachFailReason("Không thêm được Giấy tờ khác \"A\"."), "portal");
  assert.equal(H.attachFailReason("Không tìm thấy mục Giấy tờ khác."), "no_slot");
  assert.equal(H.attachFailReason("Failed to fetch"), "network");
});

test("1 tab: failedFiles của engine → đúng tệp lỗi, tên gốc + tên đổi, giữ dòng kế hoạch để đính lại; bỏ tệp ảo", () => {
  const out = H.attachFileOutcome(PLAN, FILES, {
    error: "x", fileNames: ["Giấy khai sinh"], failedFiles: [{ fileIndex: 1, error: "Cổng chưa tải xong So ho khau.pdf" }],
  });
  assert.equal(out.failed.length, 1);
  assert.equal(out.failed[0].name, "IMG_2.jpg, IMG_3.jpg");
  assert.equal(out.failed[0].renamed, "Sổ hộ khẩu");
  assert.equal(out.failed[0].reason, "portal");
  assert.equal(out.failed[0].item, PLAN[1], "nút đính lại gửi lại đúng dòng kế hoạch này");
  assert.deepEqual(out.attached.map((f) => f.name), ["IMG_1.jpg", "cccd.jpg"]);
});

test("1 tab: engine khác chỉ trả tên tệp đã lên → đối chiếu theo tên; không lỗi → đủ hết", () => {
  const out = H.attachFileOutcome(PLAN, FILES, { error: "lỗi", fileNames: ["giay-khai-sinh.pdf"], skippedNames: ["CCCD"] });
  assert.deepEqual(out.failed.map((f) => f.renamed), ["Sổ hộ khẩu"]);
  assert.equal(H.attachFileOutcome(PLAN, FILES, { ok: true }).failed.length, 0);
});

test("đa tab: hồ sơ có trong failures của background → tệp của hồ sơ đó lỗi, kèm số hồ sơ", () => {
  const bundles = [
    { files: [{ name: "a.pdf" }], planItems: [{ fileIndex: 0, documentName: "Giấy A", sourceNames: ["a.jpg"] }] },
    { files: [{ name: "b.pdf" }], planItems: [{ fileIndex: 0, documentName: "Giấy B", sourceNames: ["b.jpg"] }] },
  ];
  const out = H.splitFileOutcome(H.splitDossierFiles(bundles), [{ ordinal: 2, error: "Không mở được ô đính kèm" }]);
  assert.deepEqual(out.attached, [{ name: "a.jpg", renamed: "Giấy A", dossier: 1 }]);
  assert.deepEqual(out.failed, [{ name: "b.jpg", renamed: "Giấy B", dossier: 2, reason: "no_slot" }]);
});

test("engine content.js trả failedFiles theo fileIndex (bỏ khi nhánh ô cố định lỗi)", () => {
  assert.match(content, /failedFiles\.push\(\{ fileIndex: item\.fileIndex, error: message \|\| "" \}\);/);
  assert.match(content, /const fileReport = fixedFailed \? \{\} : \{ failedFiles \};/);
  assert.equal((content.match(/\.\.\.fileReport,/g) || []).length, 3, "cả 3 nhánh trả về của engine ví giấy tờ");
});

test("background ghi hồ sơ lỗi theo số thứ tự vào tiến độ đa tab", () => {
  assert.match(background, /failures: ok \? \(current\.failures \|\| \[\]\) : \[\.\.\.\(current\.failures \|\| \[\]\), \{/);
});

test("popup: lỗi có danh sách tệp thì không hiện câu lỗi kỹ thuật; tên gốc lưu khi gộp PDF; đa tab lưu tệp theo hồ sơ", () => {
  assert.match(popup, /if \(attachRes\?\.error && attachFiles\?\.failed\.length\) \{/);
  assert.match(popup, /sourceNames: \[\.\.\.new Set\(sourceNames\)\]/);
  assert.match(popup, /\[SPLIT_ATTACH_FILES_KEY\]: \{ runId: splitRunId, dossierFiles \}/);
  assert.match(popup, /if \(progress\.status === "completed"\) void renderSplitAttachFiles\(progress\);/);
  for (const call of ["renderAttachResult(attachRes.attachFiles", "renderAttachResult(res.attachFiles, res.attachRetry, res.details)",
    "renderAttachResult(res.attachFiles, res.attachRetry, details)"]) {
    assert.ok(popup.includes(call), `thiếu ${call}`);
  }
});

test("khối kết quả: tối đa 3 tệp lỗi hiện sẵn, danh sách đủ sau Xem chi tiết, setStatus ẩn khối cũ", () => {
  assert.match(popup, /const ATTACH_FAILED_PREVIEW = 3;/);
  assert.match(popup, /failed\.slice\(0, ATTACH_FAILED_PREVIEW\)/);
  assert.match(popup, /function setStatus\(input, type, details = \[\]\) \{\s*setStatusDetails\(details\);\s*hideAttachResult\(\);/);
  // Biến đọc trong setStatus phải khai trước mọi lời gọi setStatus (tránh lỗi TDZ lúc khởi động).
  assert.ok(popup.indexOf("let attachRetryContext = null;") < popup.indexOf("function setStatus("));
  for (const id of ["attachResult", "attachResultFailed", "attachResultToggle", "attachResultList", "attachRetryBtn"]) {
    assert.ok(html.includes(`id="${id}"`), `popup.html thiếu #${id}`);
  }
});

test("đính lại riêng tệp lỗi: chỉ gửi dòng kế hoạch còn lỗi, không gọi lại BE lập kế hoạch", () => {
  const retry = popup.slice(popup.indexOf('attachRetryBtn.addEventListener("click"'));
  assert.match(retry.slice(0, 1200), /const failedItems = ctx\.outcome\.failed\.map\(\(f\) => f\.item\)/);
  assert.match(retry.slice(0, 1200), /sendAttachPlan\(ctx\.procedure, ctx\.files, failedItems, "merge"\)/);
  assert.doesNotMatch(retry.slice(0, 1200), /attachmentPlan\(/);
});
