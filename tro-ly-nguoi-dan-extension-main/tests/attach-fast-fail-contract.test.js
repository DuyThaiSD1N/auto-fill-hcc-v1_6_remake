// NGUYÊN LÝ: chỉ BẰNG CHỨNG DƯƠNG gắn với chính tệp đó mới được quyền kết luận.
//
//   Xong  = tên tệp hiện thật trên đúng dòng.
//   Hỏng  = hết giờ chờ mà tên chưa hiện → hoãn lại, đính tệp khác, lượt sau quay lại.
//
// Toast của cổng KHÔNG được quyền phán quyết. Nó là trạng thái của CẢ TRANG, không của một tệp:
//   - toast của tệp trước còn trên màn → tệp sau bị khai hỏng oan;
//   - gỡ toast đi thì React dựng lại → lại thành "toast mới" → vẫn khai hỏng oan;
//   - bộ lọc chữ bắt cả thông báo vô hại ("Lời nhắn…", "Quyền lợi…", "1.500.000 đồng").
// Ba lần sửa liên tiếp đều vấp cùng chỗ này. Toast chỉ được dùng để GIẢI THÍCH sau khi đã kết
// luận bằng bằng chứng dương.
//
// Bỏ phán quyết bằng toast KHÔNG làm mất khả năng nào: vòng round-robin (3 lượt, backoff tăng
// dần) vốn đã lo việc thử lại. Đổi lại phải rút NGẮN các mốc chờ — bỏ cuộc sớm giờ rất rẻ vì
// còn lượt sau, trong khi chờ lâu thì tệp nào hỏng cũng bắt các tệp còn lại xếp hàng.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const attach = fs.readFileSync(path.join(root, "content", "attach-core.js"), "utf8");
const wallet = attach.slice(attach.indexOf("async function attachOneFileViaDocumentWallet"));
const walletBody = wallet.slice(0, wallet.indexOf("\nasync function ", 10));

// ── ① Toast KHÔNG được phán quyết ────────────────────────────────────────────────────────
assert.ok(!attach.includes("waitUnlessPortalError"),
  "vòng chờ có-điều-kiện-theo-toast phải biến mất: toast không quyết định thành/bại");
assert.ok(!attach.includes("dismissPortalUploadErrors"),
  "không xoá/bấm vào DOM thông báo của cổng — gỡ xong React dựng lại thành 'toast mới'");
// Toast chỉ được đọc ở nhánh BÁO LỖI, sau khi đã kết luận hỏng bằng bằng chứng dương.
assert.equal((walletBody.match(/newPortalUploadError\(errorsBefore\)/g) || []).length, 2,
  "toast chỉ được đọc ở hai nhánh BÁO LỖI, không phải để quyết định");
assert.match(walletBody, /\/\/ Mốc toast chỉ để SOẠN CÂU BÁO LỖI/);

// ── ② Bộ lọc chữ không được bắt thông báo vô hại ─────────────────────────────────────────
// fold dấu là hỏng: "lỗi", "lời", "lợi" đều thành "loi".
assert.match(attach, /if \(!\/lỗi\|thất bại\|không thành công\|failed\|error\/\.test\(text\.toLowerCase\(\)\)\) return null;/);
const errFn = attach.slice(attach.indexOf("function portalUploadErrorNodes"));
const errFnBody = errFn.slice(0, errFn.indexOf("\n}"));
assert.ok(!/foldChoiceText/.test(errFnBody), "không được fold dấu khi nhận diện chữ 'lỗi'");
assert.ok(!/50\[0-9\]/.test(errFnBody), "không dò mã HTTP trần: '500' khớp cả 1.500.000 đồng");

// ── ③ Bằng chứng DƯƠNG vẫn là thứ duy nhất kết luận THÀNH CÔNG ───────────────────────────
assert.match(attach, /const persisted = await waitForPersistedAttachment\(row, planItem, existingName\)/);
assert.match(attach, /code: "wallet-file-not-persisted"/);
assert.match(attach, /return await probe\(\); \/\/ lần cuối/);
// Trong vòng chờ bằng chứng dương KHÔNG được xen tín hiệu toàn trang.
const persistFn = attach.slice(attach.indexOf("async function waitForPersistedAttachment"));
assert.ok(!/PortalUploadError/.test(persistFn.slice(0, persistFn.indexOf("\n}"))),
  "vòng chờ tên tệp trên dòng phải sạch mọi tín hiệu toàn trang");

// ── ④ Các mốc chờ đã rút ngắn ────────────────────────────────────────────────────────────
// Bỏ cuộc sớm là RẺ (còn lượt sau); chờ lâu thì tệp hỏng bắt tệp lành xếp hàng.
const LIMITS = [
  [/findNewWalletDialog\(dialogsBefore\), 2500, 120/, "mở modal: 6s → 2,5s"],
  [/dialog\.querySelector\("input\[type='file'\]"\),\n {4}2500,/, "input tải tệp: 6s → 2,5s"],
  [/dialog\.querySelector\('input\[name="documentName"\]'\), 4000, 100/, "ô Tên tài liệu: 8s → 4s"],
  [/\}, 6000, 100\);/, "nút Thêm vào ví hết disabled: 10s → 6s"],
  [/\}, 6000, 150\);/, "tải xong: 10s → 6s"],
  [/timeout = 8000\)/, "dòng nhận file: 15s → 8s (hụt thì lượt sau dedup nhận ra, không đính trùng)"],
];
for (const [pattern, why] of LIMITS) assert.match(attach, pattern, why);
for (const tooLong of ["12000", "15000", "20000", "25000"]) {
  assert.ok(!attach.includes(tooLong), `không còn mốc chờ ${tooLong}ms nào`);
}

// ── ⑤ Hoãn rồi đi tiếp — không chặn các tệp còn lại ──────────────────────────────────────
const loop = attach.slice(attach.indexOf("const MAX_ROUNDS = 3"));
const loopBody = loop.slice(0, loop.indexOf("\n    if (errors.length)"));
assert.match(loopBody, /const backoffMs = \(round - 1\) \* 3000 \+ \(queue\.length <= 1 \? 2500 : 0\)/);
assert.equal((loopBody.match(/deferred\.push\(\{ item, index: i \}\);\s*\n\s*continue;/g) || []).length, 4,
  "MỌI nhánh hỏng đều phải hoãn-rồi-đi-tiếp, không nhánh nào được dừng cả lượt");

// ── ⑥ Lớp đỡ cuối: đã đính được thì không báo lỗi ────────────────────────────────────────
// Rút ngắn chờ làm tăng khả năng kết luận hỏng oan → lớp này càng quan trọng.
assert.match(loopBody, /await sleep\(1500\); \/\/ ân hạn/);
assert.match(loopBody, /const landedRow = payloadFile \? findExistingAttachedRowForPlanItem\(item, payloadFile\) : null;/);
assert.match(loopBody, /markAttachmentResult\(landedRow, true\);[\s\S]{0,220}?lastErrorByIndex\.delete\(index\);/);
assert.match(loopBody, /queue = stillMissing;/);
assert.match(attach, /lastErrorByIndex\.delete\(i\);\s*\n\s*markAttachmentResult\(existingRow, true\);/);

console.log("Handfree attach: chỉ bằng chứng dương kết luận, toast chỉ giải thích, hỏng thì hoãn nhanh passed");
