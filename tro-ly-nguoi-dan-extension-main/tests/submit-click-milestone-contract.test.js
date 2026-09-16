// Mốc "công dân bấm Gửi hồ sơ" — căn cứ phân biệt hồ sơ THẬT với hồ sơ làm dở.
// Chuỗi: content.js (bắt click) → sidebar.js (chuyển tiếp) → BE (__event:submit_clicked).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const content = fs.readFileSync(path.join(root, "content.js"), "utf8");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
const client = fs.readFileSync(path.join(root, "api", "client.js"), "utf8");

test("content.js chỉ tính cú bấm trên ĐÚNG trang nộp hồ sơ", () => {
  // urlPattern là cổng chặn bắt buộc: không khớp pathname thì thoát trước mọi so khớp nút,
  // nếu không nút chữ giống nhau ở trang chủ/tra cứu sẽ bị tính nhầm là đã nộp.
  assert.match(content, /function matchSubmitClick[\s\S]*?rule\.urlPattern[\s\S]*?if \(!m\) return null;/);
  // So khớp theo id VÀ nhãn — id sinh từ nhãn nên cổng đổi tên là hỏng cả hai, cần cả hai lưới.
  assert.match(content, /rule\.buttonIds[\s\S]*?includes\(id\)/);
  assert.match(content, /rule\.buttonText[\s\S]*?label === t/);
  // Capture-phase: cổng có handler riêng có thể stopPropagation.
  assert.match(content, /addEventListener\("click",[\s\S]*?\}, true\)/);
  // Luật đến từ BE, không hardcode tên cổng trong extension.
  assert.match(content, /action === "setSubmitRules"/);
  assert.doesNotMatch(content, /dichvucongnganhtuphap/);
});

test("content.js chống bấm dồn và chỉ chạy ở top frame", () => {
  assert.match(content, /if \(!IS_TOP_FRAME \|\| !submitRules\) return;/);
  assert.match(content, /Date\.now\(\) - lastSubmitClickAt < 3000/);
});

test("sidebar.js chỉ nhận cú bấm của ĐÚNG tab mình", () => {
  // Dùng chrome.runtime (trang web không gửi được) thay vì postMessage → không giả mạo được.
  assert.match(sidebar, /__tlnd !== "submitClicked"/);
  assert.match(sidebar, /sender\?\.tab\?\.id[\s\S]*?TAB_ID/);
  assert.match(sidebar, /__event:submit_clicked/);
});

test("sidebar.js nạp lại luật sau khi chuyển trang", () => {
  // Chuyển trang dựng lại content script → mất luật; boot phải nạp lại từ cache ngay,
  // không chờ tới hồ sơ kế tiếp mới có action arm_submit_watch.
  assert.match(sidebar, /arm_submit_watch/);
  assert.match(sidebar, /function armSubmitWatch[\s\S]*?SUBMIT_RULES_KEY\]: rules/);
  assert.match(sidebar, /async function bootChat\(\)[\s\S]{0,300}?restoreSubmitWatch\(\)/);
});

test("kết thúc phiên báo lý do để BE đóng sổ hồ sơ dở", () => {
  assert.match(client, /async deleteConversation\(reason = ""\)/);
  assert.match(client, /reason=\$\{encodeURIComponent\(reason\)\}/);
  assert.match(sidebar, /await api\.deleteConversation\(reason \|\| "manual"\)/);
  assert.match(sidebar, /await api\.deleteConversation\("dvc-home"\)/);
  assert.match(sidebar, /await api\.deleteConversation\("idle"\)/);
});

test("nói miệng 'làm thủ tục khác' cũng mở phiên mới như bấm chip", () => {
  // Một conversation = một hồ sơ; đường nói-miệng trước đây reset tại chỗ nên hai hồ sơ
  // dùng chung một phiên và mốc thời gian bị trộn.
  assert.match(sidebar, /a\.type === "new_conversation"[\s\S]{0,300}?returnToStart\("manual"\)/);
});
