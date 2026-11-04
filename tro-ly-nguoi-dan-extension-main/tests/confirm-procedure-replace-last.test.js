// Chỉnh nơi làm / đối tượng trên card xác nhận thủ tục → câu hỏi đổi TẠI CHỖ trong bong bóng cũ,
// không vẽ thêm bong bóng + card mới (lỗi cũ: mỗi lần đổi tỉnh/xã là một khối mới rơi xuống).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const sidebar = strip(fs.readFileSync(path.join(__dirname, "..", "sidebar.js"), "utf8"));
const render = sidebar.slice(sidebar.indexOf("function renderReply(d, opts)"));

test("sidebar khai capability supportsReplaceLast", () => {
  assert.match(sidebar, /supportsReplaceLast:\s*true/);
});

test("replace_last sửa chữ trong bong bóng xác nhận cũ rồi DỪNG — không vẽ bong bóng/card mới", () => {
  const i = render.indexOf("if (d.replace_last && d.display_md)");
  const vẽMới = render.indexOf("const $botBubble = (d.display_md && !duplicateLogoutChoice) ? addBotMd(");
  assert.ok(i > 0 && vẽMới > i, "nhánh sửa tại chỗ phải chạy TRƯỚC khi addBotMd vẽ bong bóng mới");
  const nhanh = render.slice(i, vẽMới);
  assert.match(nhanh, /\.msg\.bot\[data-ask="confirm-procedure"\]/);
  assert.match(nhanh, /cu\.innerHTML = window\.renderMarkdown\(d\.display_md\)/);
  assert.match(nhanh, /return;/, "sửa xong phải dừng, không rơi xuống vẽ card/chip/đọc TTS");
});

test("câu xác nhận đi kèm card chọn nơi được đánh dấu để lượt sau tìm đúng nó", () => {
  const sau = render.slice(render.indexOf("const $botBubble = (d.display_md"));
  assert.match(sau.slice(0, 600),
    /d\.state === "confirm_procedure"[\s\S]*c\.kind === "location_picker"[\s\S]*dataset\.ask = "confirm-procedure"/);
});

test("QR hướng dẫn hiện trước, lời giới thiệu chỉ hiển thị không đọc; câu xác nhận vẽ và đọc ngay bên dưới", () => {
  const dau = render.slice(0, render.indexOf("lastReplyData = d;", render.indexOf("return;")));
  assert.match(dau, /!opts\?\.noTts && !opts\?\.sauHuongDan && canHuongDanQr\(d\)[\s\S]*hienHuongDanQr\(d\);\s*return;/);
  const qr = sidebar.match(/function hienHuongDanQr\(d\) \{[\s\S]*?\n  \}/)[0];
  assert.match(qr, /addNode\(el\);[\s\S]{0,400}renderReply\(d, \{ sauHuongDan: true \}\);/);
  assert.doesNotMatch(sidebar, /speak\?\.\(HUONG_DAN_LOI/);
  assert.doesNotMatch(sidebar, /HUONG_DAN_CHO_MS|guide-qr-skip|laCauBoQua/);
});

test("bấm Mở hướng dẫn thì cắt câu đang đọc, kẻo đè tiếng video", () => {
  assert.match(sidebar, /\.guide-qr-link"\)\?\.addEventListener\("click", \(\) => \{\s*markActivity\(\);\s*stopReplyTts\(\);/);
});

test("QR hướng dẫn lấy từ action procedure_guide của BE — FE không còn bảng link/QR vẽ sẵn", () => {
  assert.doesNotMatch(sidebar, /HUONG_DAN_THU_TUC|qrPath|qrSize|drive\.google\.com/);
  const lay = sidebar.match(/function huongDanAction\(d\) \{[\s\S]*?\n  \}/)[0];
  assert.match(lay, /a\.type === "procedure_guide" && a\.url && a\.qr_png_base64/);
  const can = sidebar.match(/function canHuongDanQr\(d\) \{[\s\S]*?\n  \}/)[0];
  assert.match(can, /!!huongDanAction\(d\)/);
  const qr = sidebar.match(/function hienHuongDanQr\(d\) \{[\s\S]*?\n  \}/)[0];
  assert.match(qr, /src="data:image\/png;base64,\$\{window\.escapeHtml\(String\(hd\.qr_png_base64\)\)\}"/);
  assert.match(qr, /href="\$\{window\.escapeHtml\(hd\.url\)\}"/);
  // runActions không báo "action chưa hỗ trợ" cho thẻ đã vẽ ở renderReply.
  assert.match(sidebar, /a\.type === "procedure_guide"\) \{/);
});

test("ô tìm thủ tục (Xem tất cả): gõ vài từ không liền nhau trong tên vẫn ra — đủ mọi từ là khớp", () => {
  // Chạy đúng đoạn lọc của renderServiceSheetList (foldVi + điều kiện subset), mã TTHC tắt để chỉ thử phần chữ.
  const fold = sidebar.slice(sidebar.indexOf("function foldVi(s) {"), sidebar.indexOf("function pickProcedure(it)"));
  const start = sidebar.indexOf("const ql = foldVi(query).trim();");
  const end = sidebar.indexOf("list.innerHTML", start);
  assert.ok(start > 0 && end > start);
  const filter = new Function("serviceSheetItems", "query",
    `${fold}\nconst codeMatches = () => false;\n${sidebar.slice(start, end)}\nreturn subset.map((it) => it.key);`);
  const items = [
    { key: "tq", title: "Đăng ký đất đai, cấp Giấy chứng nhận quyền sử dụng đất lần đầu",
      subtitle: "Kê khai đăng ký đất đai tại Tuyên Quang",
      label: "Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận … lần đầu đối với hộ gia đình, cá nhân" },
    { key: "ks", title: "Đăng ký khai sinh", subtitle: "", label: "" },
  ];
  assert.deepEqual(filter(items, "đăng ký đất đai lần đầu"), ["tq"]);
  assert.deepEqual(filter(items, "Tuyên Quang"), ["tq"]);
  assert.deepEqual(filter(items, "đăng ký"), ["tq", "ks"]);
  assert.deepEqual(filter(items, "khai sinh lần đầu"), []);
  assert.deepEqual(filter(items, ""), ["tq", "ks"]);
});
