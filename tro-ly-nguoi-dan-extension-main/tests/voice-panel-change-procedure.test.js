// (1) Micro mở → khung "Đang nghe… công dân hãy nói" (mic nhịp + sóng + ✕) thay cho dòng trạng thái.
// (2) "Chọn/Làm thủ tục khác" → phiên mới + mở thẳng danh sách thủ tục, KHÔNG về màn giới thiệu và
//     KHÔNG đưa trang cổng về trang chủ (công dân vẫn ở quầy, chỉ đổi thủ tục).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const read = (f) => fs.readFileSync(path.join(root, f), "utf8");
const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const html = read("sidebar.html");
const js = strip(read("sidebar.js"));

test("khung nghe nằm ngay trên ô nhập, có trạng thái + chữ đang nhận dạng + nút tắt", () => {
  const panel = html.indexOf('id="voice-panel"');
  assert.ok(panel > 0 && panel < html.indexOf('<footer class="bot-f">'));
  for (const id of ["vp-status", "vp-interim", "vp-close"]) assert.match(html, new RegExp(`id="${id}"`));
  assert.match(html, /class="vp-wave"[^>]*>(<i><\/i>){7}/);
});

test("setMicUI: đang nghe thì hiện khung, tắt thì ẩn khung và trả về dòng trạng thái", () => {
  const fn = js.slice(js.indexOf("function setMicUI("), js.indexOf('document.getElementById("vp-close")'));
  assert.match(fn, /if \(listening && \$voicePanel\) \{[\s\S]*\$voicePanel\.hidden = false;[\s\S]*return;/);
  assert.match(fn, /\$voicePanel\.hidden = true;/);
  assert.match(js, /setMicUI\(true, "Đang nghe… công dân hãy nói"\)/);
  assert.match(js, /if \(\$vpInterim\) \$vpInterim\.textContent = msg\.text/);
});

test("nút ✕ tắt micro (đang rảnh tay thì tắt cả rảnh tay)", () => {
  assert.match(js, /getElementById\("vp-close"\)\?\.addEventListener\("click", \(\) => \{\s*if \(handsfree\) setHandsfree\(false\); else stopVoice\(\);/);
});

test("chip Chọn/Làm thủ tục khác + câu nói tương đương → mở danh sách thủ tục, không về trang chủ", () => {
  assert.match(js, /if \(c\.send === "__action:new_procedure"\) \{ changeProcedure\(\); return; \}/);
  assert.match(js, /a\.type === "new_conversation"[\s\S]{0,80}await returnToStart\("new_procedure"\);/);
  assert.match(js, /const shouldOpenProcedurePicker = reason === "continue" \|\| reason === "new_procedure";/);
  // Chỉ "Trò chuyện mới" thủ công mới đưa trang cổng về trang chủ DVC.
  assert.match(js, /if \(reason === "manual" && !alreadyOnDvcHome\)/);
});
