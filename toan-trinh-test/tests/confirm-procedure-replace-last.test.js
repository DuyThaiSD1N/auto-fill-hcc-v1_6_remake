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

test("đăng ký lại khai sinh: QR hướng dẫn hiện trước, câu xác nhận vẽ ngay bên dưới (chưa đọc), đọc sau khi chờ", () => {
  assert.match(sidebar, /"khai-sinh-dang-ky-lai":\s*\{\s*url: "https:\/\/drive\.google\.com\/file\/d\/1ObePKXQq2rS62F72ipMMmXVVS399rMs4\//);
  assert.match(sidebar, /HUONG_DAN_CHO_MS = 15000/);
  const dau = render.slice(0, render.indexOf("lastReplyData = d;", render.indexOf("return;")));
  assert.match(dau, /!opts\?\.noTts && !opts\?\.sauHuongDan && canHuongDanQr\(d\)[\s\S]*hienHuongDanQr\(d\);\s*return;/);
  assert.match(sidebar, /addNode\(el\);[\s\S]{0,400}renderReply\(d, \{ sauHuongDan: true, imLang: true, choHuongDan: true \}\);/);
  assert.match(render, /\} else if \(\(handsfree \|\| listenAfter\) && !opts\?\.choHuongDan\) \{/);
  assert.match(sidebar, /hen\.cho = setTimeout\(docXacNhan, HUONG_DAN_CHO_MS\);/);
  assert.match(sidebar, /if \(daMoHuongDan \|\| !d\.tts_text \|\| !voiceCfg\.tts \|\| ttsMuted\) return;/);
});

test("đọc xong lời giới thiệu thì mở mic; nói/gõ \"bỏ qua\" = bấm nút Bỏ qua, không gửi BE", () => {
  assert.match(sidebar, /speak\?\.\(HUONG_DAN_LOI, "vi", sauLoiGioiThieu\)/);
  assert.match(sidebar, /const sauLoiGioiThieu = \(\) => \{\s*if \(huongDanHen !== hen\) return;\s*demCho\(\);\s*listenWhenQuiet\(\);/);
  assert.match(sidebar, /huongDanHen\?\.boQua && laCauBoQua\(message\)\) \{\s*huongDanHen\.boQua\(\);\s*return;/);
  const fn = sidebar.match(/function laCauBoQua[\s\S]*?\n  \}/)[0];
  const laCauBoQua = new Function(`${fn}; return laCauBoQua;`)();
  for (const t of ["Bỏ qua.", "bỏ qua đi", "Bỏ qua hướng dẫn nhé", "BỎ QUA!"]) assert.equal(laCauBoQua(t), true, t);
  for (const t of ["bỏ", "khai sinh", "không bỏ qua bước này mà làm tiếp thủ tục khai sinh"]) assert.equal(laCauBoQua(t), false, t);
});

test("bấm Mở hướng dẫn: câu xác nhận vẫn hiện nhưng không đọc; bỏ qua / chờ 15s thì đọc như thường", () => {
  assert.match(sidebar, /\.guide-qr-link"\)\?\.addEventListener\("click", \(\) => \{\s*daMoHuongDan = true;/);
  assert.match(render, /else if \(!opts\?\.imLang && !duplicateLogoutChoice && d\.tts_text && voiceCfg\.tts\)/);
  assert.match(render, /const willSpeak = [^;]*!opts\?\.imLang;/);
});

test("QR hướng dẫn có đủ các thủ tục tư pháp, mỗi thủ tục đúng link Drive", () => {
  const bang = {
    "khai-sinh-dang-ky-lai": "1ObePKXQq2rS62F72ipMMmXVVS399rMs4",
    "xac-nhan-tinh-trang-hon-nhan": "1K72MmetiOzQuVywsyest5ZP-GpZGJS6G",
    "khai-sinh-dang-ky": "1GrI9R8FRMUpphFxsIH2QdGR3h1wojwlk",
    "ket-hon": "1yM72x0kkgS0ouLuCjejiTLGYJ0cEyFGR",
    "khai-sinh-dang-ky-thuong": "1_c-8Xx4O9KqTH9KbCG0uqQlPNRH3-2du",
    "chung-thuc-ban-sao": "1rv3_eC98iTnAZX0Bc9cKnWQLsGCPq9Bi",
    "thay-doi-cai-chinh-ho-tich": "1_pns6gVNa2gP0aIWI3FfcyVk1A05FCAB",
  };
  for (const [key, id] of Object.entries(bang)) {
    const re = new RegExp(`"${key}":\\s*\\{\\s*url: "https://drive\\.google\\.com/file/d/${id}/view`);
    assert.match(sidebar, re, key);
  }
});
