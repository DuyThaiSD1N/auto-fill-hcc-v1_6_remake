// Mốc "công dân bấm Gửi hồ sơ" — căn cứ phân biệt hồ sơ THẬT với hồ sơ làm dở.
// Chuỗi: content.js (bắt click) → sidebar.js (chuyển tiếp) → BE (__event:submit_clicked).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const content = fs.readFileSync(path.join(root, "content.js"), "utf8");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
const background = fs.readFileSync(path.join(root, "background.js"), "utf8");
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

test("sidebar.js chỉ nhận cú bấm của ĐÚNG hồ sơ mình (tab mình hoặc tab tách của mình)", () => {
  // Dùng chrome.runtime (trang web không gửi được) thay vì postMessage → không giả mạo được.
  assert.match(sidebar, /__tlnd === "submitClicked"/);
  // Cửa 1: cú bấm trực tiếp — phải đúng tab của sidebar này.
  assert.match(sidebar, /sender\?\.tab\?\.id[\s\S]*?TAB_ID/);
  // Cửa 2: chuyển tiếp từ tab tách — phải đúng tab GỐC là tab này, không nhận của sidebar khác.
  assert.match(sidebar, /__tlnd === "submitClickedRelay"/);
  assert.match(sidebar, /msg\.originTabId[\s\S]*?TAB_ID/);
  // Không thuộc hồ sơ mình → bỏ (vẫn chặn tab lạ như trước).
  assert.match(sidebar, /if \(!fromThisDossier\) return;/);
  assert.match(sidebar, /__event:submit_clicked/);
});

// Chứng thực tách N hồ sơ = N tab. Trước đây chỉ tab gốc được đếm (4 hồ sơ ghi 1) vì tab tách
// vừa không có luật nhận nút, vừa bị sidebar bỏ do khác tab.
test("tab tách tự nạp luật nhận nút Nộp (không chờ sidebar gửi)", () => {
  assert.match(content, /tlnd_submit_rules/);
  assert.match(content, /chrome\.storage\.local\.get\(\[SUBMIT_RULES_KEY\]/);
  assert.match(content, /chrome\.storage\.onChanged\.addListener[\s\S]{0,200}?SUBMIT_RULES_KEY/);
});

test("background nhớ tab tách → tab gốc và CHỈ chuyển tiếp tab tách (không đếm đôi)", () => {
  assert.match(background, /tlnd_split_tab_origin/);
  // Ghi bản đồ lúc mở tab tách, từ originTabId của hàng đợi.
  assert.match(background, /rememberSplitTabOrigin\(tab\.id, state\.originTabId\)/);
  assert.match(background, /originTabId: Number\(msg\.originTabId\)/);
  // Chỉ chuyển tiếp khi tab CÓ trong bản đồ — tab gốc không có nên không bị đếm hai lần.
  assert.match(background, /const originTabId = \(await getSplitTabOrigins\(\)\)\[tabId\];\s*if \(!originTabId\) return;/);
  assert.match(background, /__tlnd: "submitClickedRelay"/);
  // Dọn bản đồ khi đóng tab.
  assert.match(background, /chrome\.tabs\.onRemoved\.addListener[\s\S]{0,80}?forgetSplitTabOrigin/);
  // Tab gốc không bao giờ tự trỏ về chính nó.
  assert.match(background, /splitTabId === originTabId\) return;/);
});

test("sidebar báo tab gốc khi bắt đầu lượt tách", () => {
  assert.match(sidebar, /action: "startSplitAttachQueue"[\s\S]{0,300}?originTabId: Number\(TAB_ID\)/);
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
