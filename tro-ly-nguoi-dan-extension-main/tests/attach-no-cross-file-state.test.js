// NGUYÊN TẮC: bằng chứng cho tệp X phải là thứ XUẤT HIỆN SAU KHI bắt đầu làm tệp X.
//
// Bốn lỗi thật liên tiếp của cùng một hồ sơ chứng thực đều là MỘT bệnh — lấy trạng thái chung
// của cả trang làm bằng chứng cho một tệp cụ thể, trong khi trang còn tàn dư của tệp trước:
//
//   1. tên tệp   — so kiểu chứa nhau  → "…Duy Tân 2" nuốt "…Duy Tân"
//   2. toast lỗi — đọc lời than của tệp trước
//   3. toast lỗi — so theo node, mà thư viện toast dựng lại node
//   4. modal ví  — dùng lại modal của tệp trước còn treo
//
// File này KHÔNG chặn từng ca. Nó chặn CÁCH VIẾT sinh ra ca mới: mọi hàm đọc trạng thái chung
// chỉ được tiêu thụ qua đúng cặp "chụp mốc trước / so cái mới sau". Thêm tín hiệu mới mà quên
// mốc so sánh là test này đỏ ngay.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const attach = fs.readFileSync(path.join(root, "content", "attach-core.js"), "utf8");

/** Cắt thân một hàm để soi riêng. */
function bodyOf(name) {
  const start = attach.indexOf(`function ${name}(`);
  assert.ok(start > 0, `không tìm thấy hàm ${name}`);
  const end = attach.indexOf("\nfunction ", start + 10);
  const endAsync = attach.indexOf("\nasync function ", start + 10);
  const stop = Math.min(...[end, endAsync].filter((value) => value > 0));
  return attach.slice(start, stop > 0 ? stop : undefined);
}

/** Đếm số lần gọi `fn(` ngoài phần khai báo chính nó. */
function callSites(fn) {
  return (attach.match(new RegExp(`(?<!function )\\b${fn}\\(`, "g")) || []).length;
}

// ── Danh mục các hàm ĐỌC TRẠNG THÁI CHUNG và nơi DUY NHẤT được phép tiêu thụ chúng ───────
// Thêm một hàm đọc trạng thái chung mới → phải khai vào đây kèm cặp mốc của nó.
const GUARDED = [
  {
    reader: "portalUploadErrorNodes",
    consumers: ["snapshotPortalUploadErrors", "newPortalUploadError"],
    why: "toast lỗi của cổng sống rất lâu — đọc trần là câu báo lỗi của tệp này thành lời than của tệp trước",
  },
  {
    reader: "sizeLimitToastNodes",
    consumers: ["snapshotSizeLimitToasts", "newSizeLimitError"],
    why: "toast quá dung lượng cũng còn trên màn khi sang ô kế tiếp",
  },
  {
    reader: "visibleWalletDialogs",
    consumers: ["openDocumentWalletForRow", "findNewWalletDialog"],
    why: "modal ví của tệp trước chưa đóng thì cú click của tệp này thành vô nghĩa",
  },
];

for (const { reader, consumers, why } of GUARDED) {
  const allowed = consumers.map((name) => bodyOf(name)).join("\n");
  const allowedCalls = (allowed.match(new RegExp(`\\b${reader}\\(`, "g")) || []).length;
  assert.equal(
    callSites(reader), allowedCalls,
    `${reader}() bị gọi ngoài ${consumers.join(" / ")} — ${why}`,
  );
}

// ── Mỗi tín hiệu phải có đủ cặp "mốc trước / cái mới sau" ────────────────────────────────
// Toast: chụp mốc theo NỘI DUNG → câu báo lỗi chỉ lấy lời than chưa từng thấy.
// (Toast KHÔNG còn quyền phán quyết — xem tests/attach-fast-fail-contract.test.js.)
assert.match(attach, /return portalUploadErrorNodes\(\)\.map\(\(hit\) => foldChoiceText\(hit\.text\)\);/);
// Cả HAI đường toast (lỗi tải tệp và quá dung lượng) phải dùng chung một cách so.
assert.equal(
  (attach.match(/if \(!seen\.has\(foldChoiceText\(hit\.text\)\)\) return hit\.text;/g) || []).length, 2,
  "cả newPortalUploadError lẫn newSizeLimitError đều phải so theo NỘI DUNG",
);
assert.ok(!/prev\.text !== hit\.text/.test(attach), "không còn chỗ nào so toast theo node");

// Modal: chụp mốc các modal ĐANG HIỆN → chỉ nhận modal không nằm trong mốc đó.
assert.match(attach, /function findNewWalletDialog\(before\)/);
assert.match(attach, /if \(!before\.has\(dialogs\[index\]\)\) return dialogs\[index\];/);
const openWallet = bodyOf("openDocumentWalletForRow");
assert.match(openWallet, /if \(visibleWalletDialogs\(\)\.length\) await closeDocumentWalletDialogs\(\);/,
  "phải dọn modal cũ TRƯỚC khi chụp mốc");
assert.match(openWallet, /const dialogsBefore = new Set\(visibleWalletDialogs\(\)\);/);
assert.match(openWallet, /await waitFor\(\(\) => findNewWalletDialog\(dialogsBefore\), 2500, 120\)/);
assert.ok(!/findLatestDialogByText\("Danh sách tài liệu điện tử"\)/.test(openWallet),
  '"có modal mang tiêu đề đó" KHÔNG chứng minh cú click của ta đã mở được modal');

// Thứ tự bắt buộc: dọn → chụp mốc → click.
const closeAt = openWallet.indexOf("await closeDocumentWalletDialogs();");
const snapAt = openWallet.indexOf("const dialogsBefore =");
const clickAt = openWallet.indexOf("clickLikeUser(button)");
assert.ok(closeAt > 0 && closeAt < snapAt && snapAt < clickAt, "dọn → chụp mốc → click");

// Tên tệp: so BẰNG NHAU, không chứa nhau.
assert.ok(!attach.includes("attachmentKeyMatches"), "so kiểu chứa nhau đã bị gỡ, đừng đưa lại");

// ── Hai ca modal hỏng phải phân biệt được ────────────────────────────────────────────────
// Modal cũ treo → tải lại trang mới gỡ (mã nằm trong nhóm reloadable). Màn sạch mà click
// không ra modal → reload vô ích. Gộp một mã là hoặc bỏ lỡ cách chữa, hoặc reload vô ích.
assert.match(openWallet, /code: stuckDialog \? "wallet-stale-modal" : "wallet-modal-not-opened"/);
const splitAttach = fs.readFileSync(path.join(root, "content", "split-attach.js"), "utf8");
assert.ok(splitAttach.includes('"wallet-stale-modal"'), "wallet-stale-modal phải reload được");

// ── Lớp đỡ cuối: đã đính được thì không được báo lỗi ─────────────────────────────────────
// Dù mọi lớp trên trượt, bước soi lại bảng vẫn phải cứu.
assert.match(attach, /const landedRow = payloadFile \? findExistingAttachedRowForPlanItem\(item, payloadFile\) : null;/);

console.log("Handfree attach: không tín hiệu nào của tệp trước rơi sang tệp sau passed");
