const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
const content = fs.readFileSync(path.join(root, "content.js"), "utf8");
const background = fs.readFileSync(path.join(root, "background.js"), "utf8");
const css = fs.readFileSync(path.join(root, "sidebar.css"), "utf8");

test("lựa chọn logout được lưu theo tab và reload nối lại đúng deadline cũ", () => {
  assert.match(sidebar, /COMPLETION_LOGOUT_KEY_PREFIX = "tlnd_completion_logout:"/);
  assert.match(sidebar, /COMPLETION_LOGOUT_STORAGE_KEY = TAB_ID/);
  assert.match(sidebar, /readCompletionLogoutState\(\)/);
  assert.match(sidebar, /storedCompletionLogout \|\| j\.completion_logout/);
  assert.match(sidebar, /Number\(restoredCompletionLogout\.deadline\) - Date\.now\(\)/);
  assert.match(sidebar, /beginCompletionLogoutWait\([\s\S]*deadline[\s\S]*writeCompletionLogoutState\(state\)/);
  assert.match(sidebar, /conversationId: restored\?\.conversationId \|\| api\.conversationId/);
  assert.match(sidebar, /if \(!value\)[\s\S]*delete next\.completion_logout/);
});

test("logout thủ công hoặc đổi công dân hủy timer cũ trước khi có thể logout người mới", () => {
  assert.match(content, /citizenManualLogoutDetected/);
  assert.match(content, /label !== "dang xuat"/);
  assert.match(sidebar, /message\?\.action !== "citizenManualLogoutDetected"/);
  assert.match(background, /function clearCompletionLogoutForTab\(tabId\)/);
  assert.match(background, /msg\?\.action === "citizenManualLogoutDetected"/);
  assert.match(background, /COMPLETION_LOGOUT_KEY_PREFIX/);
  assert.match(background, /delete next\.completion_logout/);
  assert.match(sidebar, /ctx\.loginPage/);
  assert.match(sidebar, /state\.principal !== currentPrincipal/);
  assert.match(sidebar, /resolveCompletionLogout\("manual_logout"/);
  assert.match(sidebar, /completionContextChanged\(ctx, completionLogoutState\)[\s\S]*returnToStart\("completed"\)/);
});

test("Có logout, Không và Trò chuyện mới giữ phiên; nhóm nút có giao diện riêng", () => {
  assert.match(sidebar, /__action:logout_citizen/);
  assert.match(sidebar, /__action:continue_dossiers/);
  assert.match(sidebar, /returnToStart\("completed"\)/);
  assert.match(sidebar, /returnToStart\("continue"\)/);
  assert.match(sidebar, /completionLogoutState \? "continue" : "manual"/);
  assert.match(sidebar, /shouldOpenProcedurePicker = reason === "continue"/);
  assert.match(sidebar, /shouldOpenProcedurePicker[\s\S]*showChatScreen\(Date\.now\(\)\)[\s\S]*await ask\("", "system"\)[\s\S]*showProcedurePickerFromTop\(\)/);
  assert.match(css, /\.chips\.logout-choice \{ flex-wrap: nowrap;/);
  assert.match(css, /\.chips\.logout-choice \.chip/);
});

test("event submitted trùng không render thêm prompt và không gia hạn bộ đếm", () => {
  assert.match(sidebar, /duplicateLogoutChoice = hasLogoutChoice/);
  assert.match(sidebar, /d\.display_md && !duplicateLogoutChoice/);
  assert.match(sidebar, /!duplicateLogoutChoice && d\.chips\?\.length/);
  assert.match(sidebar, /\["pending", "deciding"\]\.includes\(completionLogoutState\?\.phase\)\) continue/);
  assert.match(sidebar, /restoresLogoutChoice[\s\S]*isLegacyLogoutPrompt[\s\S]*return;/);
});

test("ghi và xóa journey được tuần tự để không hồi sinh phiên cũ", () => {
  assert.match(sidebar, /let journeyWriteChain = Promise\.resolve\(\)/);
  assert.match(sidebar, /journeyWriteChain = journeyWriteChain\.then\(run, run\)/);
  assert.match(sidebar, /await saveJourney\(\{ touch: userInitiated \}\)/);
});

test("dừng micro khi hỏi đăng xuất không được đóng offscreen và cắt TTS", () => {
  assert.match(sidebar, /a\.type === "await_logout_choice"[\s\S]*beginCompletionLogoutWait\(delayMs\)/);
  assert.match(sidebar, /beginCompletionLogoutWait[\s\S]*stopVoice\?\.\(\)/);
  const asrStopBranch = background.match(
    /if \(msg\?\.type === "asr-stop"\) \{([\s\S]*?)\n  \}\n  \/\/ Lượt kết thúc/,
  );
  assert.ok(asrStopBranch, "phải có nhánh dừng ASR riêng");
  assert.match(asrStopBranch[1], /target: "offscreen", cmd: "stop"/);
  assert.doesNotMatch(asrStopBranch[1], /closeOffscreen\(/);
  assert.doesNotMatch(background, /msg\.event === "state" && msg\.state === "stopped"[\s\S]*closeOffscreen\(\)/);
});
