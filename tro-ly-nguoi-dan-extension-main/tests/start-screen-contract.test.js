const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(root, "sidebar.html"), "utf8");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
const css = fs.readFileSync(path.join(root, "sidebar.css"), "utf8");
const content = fs.readFileSync(path.join(root, "content.js"), "utf8");

test("màn bắt đầu đứng trước conversation", () => {
  assert.match(html, /id="start-screen"/);
  assert.match(html, /id="start-btn"[^>]*>Bắt đầu làm thủ tục</);
  assert.match(sidebar, /\$startBtn\?\.addEventListener\("click"/);
  assert.match(sidebar, /await ask\("", "system"\);[\s\S]*showProcedurePicker\(\)/);
  // Màn chọn thủ tục cuộn XUỐNG đáy để lộ nút "NÓI" + thanh "Xem tất cả" ở cuối khối.
  assert.match(sidebar, /function showProcedurePicker\(\)[\s\S]*\$messages\.scrollTop = \$messages\.scrollHeight/);
  assert.match(sidebar, /conv\.state === "greet"[\s\S]*showProcedurePicker\(\)/);
  assert.match(sidebar, /async function bootChat\(\)[\s\S]*?showStartScreen\(\);[\s\S]*?finally \{[\s\S]*?chatBootFinished = true/);
});

test("ba bước mở đầu là nhãn hướng dẫn, không mang hình thức nút", () => {
  assert.match(html, /<b aria-hidden="true">01<\/b>/);
  assert.match(css, /\.start-steps li \{[\s\S]*background: transparent; border: 0; border-radius: 0;[\s\S]*box-shadow: none;/);
  assert.match(css, /\.start-steps li \+ li \{ border-top:/);
});

test("cổng báo nộp thành công hỏi giữ phiên và mặc định logout sau 2 phút", () => {
  assert.match(content, /body\.includes\("nop ho so thanh cong"\) \|\| body\.includes\("gui ho so thanh cong"\)/);
  assert.doesNotMatch(content, /body\.includes\("thanh cong"\) && body\.includes\("ma ho so"\)/);
  assert.match(sidebar, /lastState === "done" && ctx\.submitted && !submittedReported/);
  assert.match(sidebar, /submittedReported = true;\s*clearInterval\(watcherTimer\); watcherTimer = null;\s*ask\("__event:submitted"/);
  assert.match(sidebar, /a\.type === "await_logout_choice"/);
  assert.match(sidebar, /Number\(a\.delay_ms\) \|\| 120000/);
  assert.match(sidebar, /a\.type === "logout_citizen"[\s\S]*returnToStart\("completed"\)/);
  assert.match(sidebar, /a\.type === "continue_dossiers"[\s\S]*returnToStart\("continue"\)/);
  assert.match(sidebar, /resetConversation\(\)[\s\S]*completionLogoutState \? "continue" : "manual"/);
  assert.doesNotMatch(sidebar, /a\.type === "return_to_start"/);
  assert.doesNotMatch(sidebar, /function renderPhoneForm/);
  assert.match(sidebar, /chips\.filter\(\(c\) => c\.send !== "__action:finish_procedure"\)/);
});

test("timeout là 20 phút và nhận hoạt động từ cả sidebar lẫn trang cổng", () => {
  // 20 phút: công dân lớn tuổi soạn/chụp giấy tờ tại quầy hay lâu hơn 10 phút, phiên tự kết
  // thúc giữa chừng là mất hồ sơ đang làm dở. Ghim số ở đây CÓ chủ đích — đổi mốc này ảnh
  // hưởng trực tiếp tới công dân đang ngồi trước máy, phải là quyết định cố ý.
  assert.match(sidebar, /IDLE_TIMEOUT_MS = 20 \* 60 \* 1000/);
  assert.match(sidebar, /last_activity_at/);
  assert.match(content, /persistPageActivity/);
  assert.match(content, /\["pointerdown", "keydown", "input", "change", "scroll"\]/);
});
