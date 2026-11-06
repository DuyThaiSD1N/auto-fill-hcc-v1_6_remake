// Báo kết quả đính kèm theo từng tệp (supportsAttachFileReport): sidebar dựng attach_report.files (tên gốc, tên đổi,
// hồ sơ số mấy, nhóm lý do) cho cả đính 1 tab lẫn đa tab; engine ví giấy tờ trả failedFiles; thẻ attach_files vẽ nút
// xem tệp đã đính + khung tệp lỗi ngay sau bong bóng chính. BE: chat/attach_files.py.
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const read = (p) => fs.readFileSync(path.join(root, p), "utf8");
const strip = (src) => src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const sidebarRaw = read("sidebar.js");
const sidebar = strip(sidebarRaw);
const attachCore = strip(read("content/attach-core.js"));

// Chạy thật các hàm dựng báo cáo (thuần, không đụng DOM) — cắt từ sidebar.js.
const start = sidebarRaw.indexOf("  function attachFailReason(");
const end = sidebarRaw.indexOf("  function splitQueueReport(");
const H = new Function(`${sidebarRaw.slice(start, end)}
  return { attachFailReason, planFileEntry, attachFileOutcome, splitDossierFiles, splitFileOutcome };`)();

test("sidebar khai supportsAttachFileReport", () => {
  assert.match(sidebar, /supportsAttachFileReport: true/);
});

test("lỗi kỹ thuật xếp về nhóm lý do — BE ghi câu cho người dân", () => {
  assert.equal(H.attachFailReason("Tổng dung lượng file của 1 loại giấy tờ không được quá 2.6MB"), "too_large");
  assert.equal(H.attachFailReason("Không đọc được tệp \"a.jpg\"."), "corrupt");
  assert.equal(H.attachFailReason("Failed to fetch"), "network");
  assert.equal(H.attachFailReason("Không tìm thấy dòng hồ sơ \"Giấy khai sinh\"."), "no_slot");
  assert.equal(H.attachFailReason("Cổng chưa ghi nhận a.pdf vào dòng hồ sơ."), "portal");
  assert.equal(H.attachFailReason("???"), "other");
});

const FILES = [{ name: "Giay khai sinh.pdf" }, { name: "So ho khau.pdf" }, { name: "x.pdf" }];
const PLAN = [
  { fileIndex: 0, documentName: "Giấy khai sinh", sourceNames: ["IMG_1.jpg"] },
  { fileIndex: 1, documentName: "Sổ hộ khẩu", sourceNames: ["IMG_2.jpg", "IMG_3.jpg"] },
  { fileIndex: 2, documentName: "CCCD", sourceNames: ["cccd.jpg"] },
  { fileIndex: 0, virtualCopy: true, documentName: "Bản sao ảo" },
];

test("1 tab: engine ví giấy tờ báo failedFiles → đúng tệp lỗi, tên gốc + tên đổi; bỏ tệp ảo", () => {
  const out = H.attachFileOutcome(PLAN, FILES, {
    error: "x", fileNames: ["Giấy khai sinh"], failedFiles: [{ fileIndex: 1, error: "Cổng chưa tải xong So ho khau.pdf" }],
  });
  assert.deepEqual(out.failed, [{ name: "IMG_2.jpg, IMG_3.jpg", renamed: "Sổ hộ khẩu", reason: "portal" }]);
  assert.deepEqual(out.attached.map((f) => f.name), ["IMG_1.jpg", "cccd.jpg"]);
});

test("1 tab: engine khác chỉ trả tên tệp đã lên → đối chiếu theo tên", () => {
  const out = H.attachFileOutcome(PLAN, FILES, {
    error: "Không gắn được file vào Giấy tờ khác", fileNames: ["giay-khai-sinh.pdf"], skippedNames: ["CCCD"],
  });
  assert.deepEqual(out.failed.map((f) => f.renamed), ["Sổ hộ khẩu"]);
  assert.equal(out.attached.length, 2);
});

test("1 tab: không lỗi → mọi tệp đã đính; trang không trả lời → mọi tệp lỗi", () => {
  assert.equal(H.attachFileOutcome(PLAN, FILES, { ok: true, attached: 3 }).failed.length, 0);
  const none = H.attachFileOutcome(PLAN, FILES, null);
  assert.equal(none.attached.length, 0);
  assert.ok(none.failed.every((f) => f.reason === "no_slot"));
});

test("đa tab: tệp của hồ sơ hỏng vào danh sách lỗi kèm số hồ sơ", () => {
  const bundles = [
    { files: [{ name: "a.pdf" }], attachments: [{ fileIndex: 0, documentName: "Giấy A", sourceNames: ["a.jpg"] }] },
    { files: [{ name: "b.pdf" }], attachments: [{ fileIndex: 0, documentName: "Giấy B", sourceNames: ["b.jpg"] }] },
  ];
  const out = H.splitFileOutcome(H.splitDossierFiles(bundles), [
    { ordinal: 1, ok: true }, { ordinal: 2, ok: false, error: "Không mở được ô đính kèm" },
  ]);
  assert.deepEqual(out.attached, [{ name: "a.jpg", renamed: "Giấy A", dossier: 1 }]);
  assert.deepEqual(out.failed, [{ name: "b.jpg", renamed: "Giấy B", dossier: 2, reason: "no_slot" }]);
});

test("báo cáo 1 tab và đa tab đều kèm files; đa tab giữ danh sách theo hồ sơ qua reload (activeSplit)", () => {
  assert.match(sidebar, /const fileOutcome = attachFileOutcome\(sendAttachments, files, res\);/);
  assert.match(sidebar, /\.\.\.\(fileOutcome \? \{ files: fileOutcome \} : \{\}\)/);
  assert.match(sidebar, /dispatch_id: a\.dispatch_id \|\| "", dossierFiles,/);
  assert.match(sidebar, /splitQueueReport\(status, monitor\.dispatchId, dossierFiles\)/);
  assert.match(sidebar, /sourceNames: \[\.\.\.new Set\(sourceNames\)\]/);
});

test("engine ví giấy tờ trả failedFiles theo fileIndex (bỏ khi nhánh ô cố định lỗi)", () => {
  assert.match(attachCore, /failedFiles\.push\(\{ fileIndex: item\.fileIndex, error: message \|\| "" \}\);/);
  assert.match(attachCore, /\.\.\.\(fixedFailed \? \{\} : \{ failedFiles \}\)/);
});

test("thẻ attach_files vẽ ngay sau bong bóng chính, tên tệp qua textContent, tối đa maxLines dòng", () => {
  const reply = sidebar.slice(sidebar.indexOf("function renderReply("));
  const bubble = reply.indexOf("const $botBubble =");
  const card = reply.indexOf('c.kind === "attach_files"');
  const trail = reply.indexOf('a.type === "trail_message"', bubble);
  assert.ok(bubble > 0 && card > bubble && trail > card, "thẻ phải đứng giữa câu chính và câu bước tiếp theo");
  assert.match(sidebar, /if \(card\.kind === "attach_files"\) return;/);
  const render = sidebar.slice(sidebar.indexOf("function renderAttachFiles("));
  assert.match(render, /failed\.slice\(0, max\)/);
  assert.match(render, /li\.textContent = attachFileLine\(card, f\)/);
  assert.match(render, /msg bot err attach-files-failed/);
});
