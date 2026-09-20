// NGUYÊN LÝ: bằng chứng cho tệp X phải là thứ XUẤT HIỆN SAU KHI bắt đầu làm tệp X.
//
// Bản Handfree đã vấp bốn lần liên tiếp vì cùng một bệnh — lấy trạng thái chung của cả trang
// làm bằng chứng cho một tệp cụ thể, trong khi trang còn tàn dư của tệp trước. File này khoá
// cùng nguyên lý cho bản no-handfree, để hai bên không trôi ra khỏi nhau.
//
// Toast của cổng: readPortalUploadError (lỏng) CHỈ để giải thích khi đã kết luận hỏng. Handfree
// từng nâng toast chung lên vai phán quyết và hỏng ba lần. NGOẠI LỆ HẸP (19/09/2026, đồng bộ
// Handfree theo yêu cầu): đúng câu "…thất bại" của cổng, MỚI so với mốc trước tệp, được HOÃN tệp
// sớm + đóng toast đó trước khi sang tệp kế. Không nới ra "lỗi"/mã HTTP chung.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const content = fs.readFileSync(path.join(root, "content.js"), "utf8");

// ── Modal ví tài liệu: phải là modal MỚI ─────────────────────────────────────────────────
// "Có modal mang tiêu đề đó" KHÔNG chứng minh cú click của ta đã mở được nó. Cổng vừa lỗi thì
// modal của tệp trước chưa kịp đóng → tệp này thao tác trên đúng cái modal hỏng đó: nút "Thêm
// vào ví" còn disabled, ô Tên tài liệu còn tên cũ → chờ hết hạn rồi báo hỏng oan.
assert.match(content, /function visibleWalletDialogs\(\)/);
assert.match(content, /function findNewWalletDialog\(before\)/);
assert.match(content, /if \(!before\.has\(dialogs\[index\]\)\) return dialogs\[index\];/);

const openStart = content.indexOf("async function openDocumentWalletForRow");
const openWallet = content.slice(openStart, content.indexOf("\n  function findRemoveAttachmentButton", openStart));
assert.match(openWallet, /if \(visibleWalletDialogs\(\)\.length\) await closeDocumentWalletDialogs\(\);/,
  "phải dọn modal cũ TRƯỚC khi chụp mốc");
assert.match(openWallet, /const dialogsBefore = new Set\(visibleWalletDialogs\(\)\);/);
assert.match(openWallet, /await waitFor\(\(\) => findNewWalletDialog\(dialogsBefore\), 2500, 120\)/);
assert.ok(!/findLatestDialogByText\("Danh sách tài liệu điện tử"\)/.test(openWallet),
  '"có modal mang tiêu đề đó" KHÔNG chứng minh cú click của ta đã mở được modal');

// Thứ tự bắt buộc: dọn → chụp mốc → click.
const closeAt = openWallet.indexOf("await closeDocumentWalletDialogs();");
const snapAt = openWallet.indexOf("const dialogsBefore =");
const clickAt = openWallet.indexOf("button.click();");
assert.ok(closeAt > 0 && closeAt < snapAt && snapAt < clickAt, "dọn → chụp mốc → click");

// Hai ca modal hỏng phải phân biệt được: modal cũ treo thì reload chữa được, màn sạch thì không.
assert.match(openWallet, /code: stuckDialog \? "wallet-stale-modal" : "wallet-modal-not-opened"/);
const popup = fs.readFileSync(path.join(root, "popup.js"), "utf8");
assert.ok(popup.includes("wallet-stale-modal") || content.includes("SPLIT_RELOADABLE_WALLET_CODES"),
  "wallet-stale-modal phải nằm trong nhóm reload chữa được");

// ── Tên tệp: so BẰNG NHAU, không chứa nhau ───────────────────────────────────────────────
// "Bảng điểm Đại học Duy Tân 2" không được nuốt "Bảng điểm Đại học Duy Tân".
assert.ok(!content.includes("attachmentKeyMatches"), "so kiểu chứa nhau đã bị gỡ, đừng đưa lại");
assert.match(content, /return labels\.some\(\(label\) => attachmentKeyEquals\(attachedName, label\)\);/);

// ── Đã đính được thì KHÔNG báo lỗi ───────────────────────────────────────────────────────
// Cổng ghi nhận chậm: tệp ta đã bỏ cuộc vẫn có thể nằm sẵn trên dòng vài giây sau.
// Càng cần từ khi các mốc chờ rút ngắn.
const loop = content.slice(content.indexOf("const MAX_ROUNDS = 3"));
const loopBody = loop.slice(0, loop.indexOf("// Lượt chốt: đánh số các dòng"));
assert.match(loopBody, /await sleep\(1500\); \/\/ ân hạn/);
assert.match(loopBody, /const landedRow = payloadFile \? findExistingAttachedRowForPlanItem\(item, payloadFile\) : null;/);
assert.match(loopBody, /markAttachmentResult\(landedRow, true\);[\s\S]{0,220}?lastErrorByIndex\.delete\(index\);/);
assert.match(loopBody, /queue = stillMissing;/);
assert.match(content, /lastErrorByIndex\.delete\(i\);\s*\n\s*markAttachmentResult\(existingRow, true\);/);

// ── Mốc chờ đã rút ngắn ──────────────────────────────────────────────────────────────────
// Bỏ cuộc sớm là RẺ (round-robin còn lượt sau); chờ lâu thì tệp hỏng bắt tệp lành xếp hàng.
for (const tooLong of ["12000", "15000", "20000", "25000"]) {
  assert.ok(!content.includes(tooLong), `không còn mốc chờ ${tooLong}ms nào`);
}
assert.match(content, /async function waitForPersistedAttachment\(row, planItem = \{\}, previousName = "", timeout = 8000,\n\s*uploadFailed = null\)/);

// ── Toast giữ ĐÚNG VAI: chỉ giải thích ───────────────────────────────────────────────────
assert.ok(!content.includes("waitUnlessPortalError"),
  "toast không được quyền quyết định thành/bại — Handfree đã hỏng ba lần vì điều này");
assert.ok(!content.includes("dismissPortalUploadErrors"),
  "không xoá/bấm mọi thông báo của cổng — chỉ đóng đúng toast upload-thất-bại");
// Bộ dò hoãn-sớm KHÔNG được dùng readPortalUploadError (lỏng: khớp cả "lỗi", "500").
const failFn = content.slice(content.indexOf("function newPortalUploadFailure"));
assert.ok(!/readPortalUploadError/.test(failFn.slice(0, failFn.indexOf("\n  }\n"))));
// Mốc chụp TRƯỚC khi đưa tệp vào ô tải, so theo nội dung.
assert.match(content, /const failuresBefore = snapshotUploadFailures\(\);\n[\s\S]{0,700}?setFilesOnInput\(uploadInput/);
assert.match(content, /portalError \? ` — cổng báo: \$\{portalError\}` : "\."/,
  "toast chỉ để làm rõ câu báo lỗi");

console.log("no-handfree attach: modal phải mới, đã đính thì không báo lỗi, chờ đã rút passed");
