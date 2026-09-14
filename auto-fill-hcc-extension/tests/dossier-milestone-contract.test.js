// Vòng đời MỘT hồ sơ ở Auto Fill: dossierId (khóa) — mốc bắt đầu — mốc bấm Gửi hồ sơ.
// Khóa này đi vào traces.dossier_id, CÙNG TRƯỜNG với conversation_id của Trợ lý nhân dân.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const popup = fs.readFileSync(path.join(root, "popup.js"), "utf8");
const content = fs.readFileSync(path.join(root, "content.js"), "utf8");
const background = fs.readFileSync(path.join(root, "background.js"), "utf8");

test("dossierId sinh LƯỜI ở lượt process/đính kèm đầu tiên", () => {
  assert.match(popup, /function ensureDossierId\(\)[\s\S]*?dossierId = newDossierId\(\)/);
  // Cả hai đường đều phải gắn: thủ tục attach-only (chứng thực) KHÔNG gọi /process bao giờ,
  // thiếu đường đính kèm là mất hẳn nhóm nhiều lượt nhất khỏi thống kê.
  assert.match(popup, /async function runAttachmentPlanForCurrentFiles[\s\S]{0,400}?options\.dossierId = ensureDossierId\(\)/);
  assert.match(popup, /options\.dossierId = ensureDossierId\(\);\s*\n\s*const res = await api\.process\(/);
});

test("dossierId phải sống qua reload", () => {
  // Không nằm trong session của tab thì mỗi lần WebForms postback là một hồ sơ mới — đúng cái
  // lỗi đang làm lastProcessSession đứt liên kết fill↔đính kèm.
  assert.match(popup, /const snapshot = \{[\s\S]*?dossierId,[\s\S]*?\}/);
  assert.match(popup, /dossierId = String\(saved\.dossierId \|\| ""\)\.trim\(\)/);
  assert.match(popup, /function ensureDossierId[\s\S]*?void saveSession\(\)/);
});

test("dossierId đóng khi hồ sơ kết thúc", () => {
  assert.match(popup, /function closeDossier\(reason\)[\s\S]*?dossierId = ""/);
  assert.match(popup, /closeDossier\("procedure-change"\)/);          // đổi thủ tục
  assert.match(popup, /async function clearSession\(\)[\s\S]{0,200}?dossierId = ""/); // đăng xuất / Tạo phiên mới
});

test("nộp xong KHÔNG xoá khóa ngay — xoay ở lượt kế tiếp", () => {
  // Chứng thực tách nhiều tab dùng CHUNG một khóa và nộp N lần; xoá ngay là mất các lần sau.
  // Luật này đúng cho MỌI thủ tục nên không cần khai cấu hình riêng cho nhóm đa tab —
  // mà quên khai cấu hình là kiểu lỗi âm thầm, rất lâu sau mới lộ.
  assert.match(popup, /function ensureDossierId\(\)[\s\S]{0,200}?if \(!dossierId \|\| dossierSubmitted\)/);
  assert.match(popup, /msg\?\.action === "dossierSubmitted"[\s\S]{0,200}?dossierSubmitted = true/);
  assert.match(background, /dossierSubmitted: true/);
  assert.doesNotMatch(background, /dossierId: ""/); // background không được tự xoá khóa
  // Cờ phải sống qua reload, nếu không saveSession kế tiếp đè mất và hồ sơ sau bị gộp.
  assert.match(popup, /dossierSubmitted = !!saved\.dossierSubmitted/);
});

test("tab tách được gieo khóa để cú bấm nộp báo về được", () => {
  assert.match(popup, /queueItems = rest\.map[\s\S]{0,600}?dossierId,/);
  assert.match(background, /chrome\.tabs\.create[\s\S]{0,700}?\["autofill_session_" \+ tab\.id\]: \{ dossierId: item\.dossierId \}/);
});

test("content.js chỉ tính cú bấm trên ĐÚNG trang nộp hồ sơ", () => {
  // urlPattern là cổng chặn: sai URL thì thoát trước mọi so khớp nút. Tính nhầm = thổi phồng
  // số hồ sơ, mà sai kiểu đó không ai phát hiện ra.
  assert.match(content, /rule\.urlPattern[\s\S]{0,220}?if \(!m\) return;/);
  assert.match(content, /rule\.buttonIds \|\| \[\]\)\.includes/);
  assert.match(content, /rule\.buttonText \|\| \[\]\)\.some/);
  assert.match(content, /Date\.now\(\) - lastSubmitClickAt < 3000/);
  assert.match(content, /addEventListener\("click",[\s\S]*?\}, true\)/);
  // Luật đến từ BE (portal_submit.py) qua storage — thêm cổng mới khỏi phát hành lại extension.
  assert.match(content, /chrome\.storage\.local\.get\(\[SUBMIT_WATCH_KEY\]/);
  // Popup nạp /procedures SAU khi content script chạy → phải nghe thay đổi, không thì lỡ hồ sơ đầu.
  assert.match(content, /chrome\.storage\.onChanged\.addListener[\s\S]{0,220}?SUBMIT_WATCH_KEY/);
  assert.match(popup, /res\.portalSubmit[\s\S]{0,400}?\[SUBMIT_WATCH_KEY\]: \{ rules: res\.portalSubmit, base \}/);
});

test("bắt click ở content script chứ không ở popup", () => {
  // Panel có thể đã đóng lúc cán bộ bấm Gửi hồ sơ; popup lúc đó không tồn tại.
  assert.match(content, /dossierSubmitClicked/);
  assert.match(background, /msg\?\.action === "dossierSubmitClicked"/);
  assert.doesNotMatch(popup, /addEventListener\("click"[\s\S]{0,120}?kt_gui-ho-so/);
});

test("background chỉ báo hồ sơ mà extension CÓ tham gia", () => {
  // Không có dossierId = chưa từng điền/đính kèm → không chấm. Báo cáo chỉ tính hồ sơ trợ lý làm.
  assert.match(background, /if \(!dossierId\) return;/);
  assert.match(background, /\/api\/v1\/dossiers\/submit-click/);
  assert.match(background, /Authorization: "Bearer " \+ accessToken/);
  // Gọi BE lỗi → GIỮ khóa để lần bấm sau còn ghi được.
  assert.match(background, /console\.warn\("\[BG\] Không báo được mốc nộp hồ sơ[\s\S]{0,120}?return;/);
});
