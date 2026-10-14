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
