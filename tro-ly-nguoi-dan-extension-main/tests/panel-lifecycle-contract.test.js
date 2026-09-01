const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const content = fs.readFileSync(path.join(root, "content.js"), "utf8");
const html = fs.readFileSync(path.join(root, "sidebar.html"), "utf8");

test("nút đóng chỉ thu panel về launcher và giữ phiên sống", () => {
  assert.match(content, /function closePanel\(\) \{[\s\S]*?minimizePanel\(\);[\s\S]*?\n  \}/);
  assert.match(content, /if \(host && !host\.classList\.contains\("open"\)\) host\.style\.display = "none"/);
  assert.doesNotMatch(content, /function setGlobalDismissed/);
  assert.doesNotMatch(content, /function persistDismissed/);
  assert.match(html, /id="close-btn"[^>]*title="Thu về biểu tượng"/);
  assert.match(html, /id="login-close-btn"[^>]*title="Thu về biểu tượng"/);
});

test("launcher dùng logo HCC lớn và nằm phía trên", () => {
  assert.match(content, /assets\/icons\/icon-128\.png/);
  assert.match(content, /right: "18px", top: "22px"/);
  assert.match(content, /width: "80px", height: "80px"/);
  assert.match(content, /createElement\("button"\)/);
  assert.match(content, /aria-label", "Mở Trợ lý người dân"/);
});

test("header và màn hình bắt đầu dùng chung logo mới của extension", () => {
  const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
  const css = fs.readFileSync(path.join(root, "sidebar.css"), "utf8");
  assert.match(sidebar, /BRAND_ICON_URL = chrome\.runtime\.getURL\("assets\/icons\/icon-128\.png"\)/);
  assert.match(sidebar, /getElementById\("bot-avatar"\)\.innerHTML = BRAND_ICON\(30, "brand-icon-header"\)/);
  assert.match(sidebar, /getElementById\("start-avatar"\)\.innerHTML = BRAND_ICON\(68, "brand-icon-start"\)/);
  assert.match(css, /\.brand-icon-header/);
  assert.match(css, /\.brand-icon-start/);
});

test("chỉ trang chủ DVC quốc gia tự mở và không dựng lại panel đang mở", () => {
  assert.match(content, /IS_DVC_HOST = location\.origin === "https:\/\/dichvucong\.gov\.vn"/);
  assert.match(content, /IS_DVC_HOME = IS_DVC_HOST && location\.pathname === "\/"/);
  assert.match(content, /if \(IS_DVC_HOME\) \{ ensurePanelOpen\(\); return; \}/);
  assert.match(content, /if \(IS_DVC_HOST\) \{ showDvcChildInitial\(\); return; \}/);
  assert.match(content, /sessionStorage\.setItem\(SS_OPEN_KEY, open \? "1" : "0"\)/);
  assert.match(content, /function showDvcChildInitial\(\)[\s\S]*?state === "1"[\s\S]*?ensurePanelOpen\(\)[\s\S]*?state === "0"[\s\S]*?showLauncher\(\)[\s\S]*?showInitial\(\);/);
  assert.match(content, /function ensurePanelOpen\(\)[\s\S]*?if \(host\)[\s\S]*?return;/);
  assert.match(content, /clearLegacyDismissedState\(\)/);
});

test("về đúng trang chủ DVC tạo lượt trò chuyện mới", () => {
  const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
  assert.match(content, /if \(IS_DVC_HOME\) sidebarQuery\.set\("fresh", "dvc-home"\)/);
  assert.match(content, /sidebar\.html\?\$\{sidebarQuery\.toString\(\)\}/);
  assert.match(sidebar, /START_FRESH_ON_DVC_HOME = params\.get\("fresh"\) === "dvc-home"/);
  assert.match(sidebar, /if \(START_FRESH_ON_DVC_HOME\)[\s\S]*await api\.deleteConversation\(\)/);
  assert.match(sidebar, /if \(START_FRESH_ON_DVC_HOME\)[\s\S]*await clearJourney\(\)/);
  assert.match(sidebar, /if \(START_FRESH_ON_DVC_HOME\)[\s\S]*showStartScreen\(\)/);
  assert.doesNotMatch(sidebar, /START_FRESH_ON_DVC_HOME[\s\S]{0,800}clearCitizenDvcCookies/);
});

test("lần điều hướng đầu phải ghi xong journey trước khi hủy iframe", () => {
  const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
  assert.match(sidebar, /function saveJourney\([\s\S]*?return new Promise/);
  assert.match(sidebar, /if \(a\.type === "navigate" && a\.url\)[\s\S]*?await saveJourney\(\);[\s\S]*?action: "navigate"/);
});

test("launcher kéo thả được và khôi phục vị trí sau reload", () => {
  assert.match(content, /LAUNCHER_POSITION_KEY = "tlnd_launcher_position_v1"/);
  assert.match(content, /function clampLauncherPosition\(/);
  assert.match(content, /addEventListener\("pointerdown"/);
  assert.match(content, /addEventListener\("pointermove"/);
  assert.match(content, /addEventListener\("pointerup"/);
  assert.match(content, /chrome\.storage\.local\.set\(\{ \[LAUNCHER_POSITION_KEY\]: position \}/);
  assert.match(content, /chrome\.storage\.local\.get\(\[LAUNCHER_POSITION_KEY\]/);
  assert.match(content, /suppressClick = drag\.moved/);
  assert.match(content, /dataset\.launcherXRatio/);
  assert.match(content, /dataset\.launcherYRatio/);
  assert.match(content, /function reflowLauncherPosition\(/);
  assert.match(content, /launcher && launcher\.style\.display !== "none"\) reflowLauncherPosition\(launcher\)/);
});
