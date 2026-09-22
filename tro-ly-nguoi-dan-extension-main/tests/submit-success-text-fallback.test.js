// Lưới đỡ dò chữ màn kết quả (successText) — khi cú bấm nút nộp rớt.
//
// Lỗi thật (Phường Vũ Ninh, 21/09): liên thông khai sinh đã nộp, cổng cấp số hồ sơ
// G22.99.08-260921-896048, nhưng hệ thống ghi "chưa nộp". Cú bấm "Hoàn thành" không về tới BE,
// còn câu dò chung "nộp/gửi hồ sơ thành công" thì trượt hẳn vì màn kết quả liên thông chỉ viết
// "Vui lòng ghi nhớ… Số hồ sơ… Ngày hẹn trả dự kiến". Không còn lưới nào đỡ.
//
// Test CHẠY THẬT hàm matchSuccessText (bóc từ content.js) chứ không chỉ khớp chuỗi mã nguồn.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const src = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");
const start = src.indexOf("function matchSuccessText(body)");
assert.ok(start > 0, "thiếu matchSuccessText trong content.js");
const fnSrc = src.slice(start, src.indexOf("\n  }\n", start) + 4);

// Luật y hệt BE đang phát (app/procedures/portal_submit.py).
const RULES = {
  "lienthong.dichvucong.gov.vn": {
    urlPattern: "^/#/ke-khai/([\\d.]+)$",
    buttonText: ["hoan thanh"],
    successText: [["vui long ghi nho cac thong tin ben duoi", "so ho so", "ngay hen tra du kien"]],
  },
  // Cổng không khai successText → lưới này phải im, để câu dò chung tự lo.
  "dichvucong.quangninh.gov.vn": { urlPattern: "^/nop-ho-so/(\\d+)$", buttonIds: ["kt_gui-ho-so"] },
};

function run(body, { host = "lienthong.dichvucong.gov.vn", pathname = "/", hash = "#/ke-khai/2.000987", rules = RULES } = {}) {
  // eslint-disable-next-line no-new-func
  const make = new Function("submitRules", "location", `${fnSrc}; return matchSuccessText;`);
  return make(rules, { hostname: host, pathname, hash })(body);
}

// Chữ màn kết quả thật (ảnh chụp tại quầy), đã qua foldTxt như page_status làm.
const RESULT = "vui long ghi nho cac thong tin ben duoi de theo doi tinh hinh xu ly hoac cap nhap "
  + "thong tin ho so cua ban. so ho so: g22.99.08-260921-896048 ngay hen tra du kien: 25/09/2026. "
  + "khong bao gom thoi gian xin xac nhan tren vneid.";

// ── Bắt được đúng màn kết quả ───────────────────────────────────────────────────────────
assert.equal(run(RESULT), true, "màn kết quả liên thông phải được nhận là ĐÃ NỘP");
assert.equal(run(RESULT, { hash: "#/ke-khai/2.000986" }), true, "cùng cổng, thủ tục liên thông khác");

// ── Phải ĐỦ mọi cụm trong nhóm ──────────────────────────────────────────────────────────
assert.equal(run("vui long ghi nho cac thong tin ben duoi"), false, "thiếu 'ngày hẹn trả' → chưa đủ");
assert.equal(run("ngay hen tra du kien: 25/09/2026"), false, "thiếu câu 'ghi nhớ' → chưa đủ");
assert.equal(
  run("vui long ghi nho cac thong tin ben duoi ngay hen tra du kien: 25/09/2026"),
  false, "thiếu 'số hồ sơ' → chưa đủ",
);

// ── Sai URL thì KHÔNG tính dù chữ khớp ──────────────────────────────────────────────────
// Màn tra cứu/hồ sơ của tôi có thể lặp lại câu chữ — đếm nhầm thì hỏng báo cáo mà không ai biết.
assert.equal(run(RESULT, { hash: "#/tra-cuu" }), false);
assert.equal(run(RESULT, { hash: "#/" }), false);

// ── Cổng khác / không khai successText → im lặng ────────────────────────────────────────
assert.equal(run(RESULT, { host: "dichvucong.quangninh.gov.vn", pathname: "/nop-ho-so/1", hash: "" }), false);
assert.equal(run(RESULT, { host: "vi-du.gov.vn" }), false);
assert.equal(run(RESULT, { rules: null }), false, "chưa nạp luật → không được ném lỗi");
assert.equal(run("", {}), false);

// ── Nối đúng vào tín hiệu `submitted` của page_status ───────────────────────────────────
// sidebar.js phát __event:submitted khi state="done" && ctx.submitted — hồ sơ Vũ Ninh đã ở
// done (đính kèm xong) nên chỉ cần ctx.submitted bật lên là mốc nộp về tới BE.
assert.match(src, /\|\| matchSuccessText\(body\),/);
// Câu dò chung vẫn giữ nguyên cho mọi cổng khác.
assert.match(src, /body\.includes\("nop ho so thanh cong"\) \|\| body\.includes\("gui ho so thanh cong"\)/);

console.log("submit success-text fallback: liên thông nhận được màn kết quả, khóa URL passed");
