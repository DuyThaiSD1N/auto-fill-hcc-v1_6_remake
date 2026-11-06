// Cỡ chữ theo tài khoản (Cài đặt → Cỡ chữ): thanh trượt 90–130% bước 5% + chữ mẫu; lưu ở BE account_settings.fontScale;
// phóng cả khung bằng zoom, chiều cao khung chia lại theo tỉ lệ để ô nhập không rơi khỏi đáy.
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const read = (p) => fs.readFileSync(path.join(root, p), "utf8");
const strip = (src) => src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const raw = read("sidebar.js");
const js = strip(raw);
const css = strip(read("sidebar.css"));
const html = read("sidebar.html");

// Chạy thật hàm làm tròn/chặn khoảng.
const clampSrc = raw.slice(raw.indexOf("  const FONT_SCALE_MIN"), raw.indexOf("  // Khung phải cao đúng cửa sổ"));
const clamp = new Function(`${clampSrc.replace("let fontScale = 1;", "").replace(/let fontScalePending[^\n]*\n/, "")}
  return clampFontScale;`)();

test("khoảng 90–130%, bước 5%; giá trị lạ về 100%", () => {
  assert.equal(clamp(0.5), 0.9);
  assert.equal(clamp(2), 1.3);
  assert.equal(clamp(1.12), 1.1);
  assert.equal(clamp(1.13), 1.15);
  assert.equal(clamp("abc"), 1);
  assert.match(html, /id="font-scale-range" class="font-scale-range" type="range" min="90" max="130" step="5" value="100"/);
  assert.match(html, /id="font-scale-sample"/);
});

test("thả tay mới lưu theo tài khoản; kéo chỉ đổi chữ mẫu", () => {
  assert.match(js, /\$fontScaleRange\?\.addEventListener\("input", \(\) => showFontScalePreview\(/);
  assert.match(js, /saveAccountSetting\(\{ fontScale: next \}, "font-scale-status"\)/);
  assert.match(js, /applyFontScale\(settings\?\.fontScale \?\? 1\);/);
  assert.match(js, /const ACCOUNT_STATUS_IDS = \[[^\]]*"font-scale-status"/, "trạng thái tải/lỗi cài đặt tài khoản có cả dòng cỡ chữ");
});

test("đăng xuất về 100%; khởi động áp bản sao lần trước để không nháy", () => {
  const forget = js.slice(js.indexOf("function forgetAccountSettings()"));
  assert.match(forget.slice(0, 400), /applyFontScale\(1\);/);
  assert.match(js, /res\?\.\[ACCOUNT_SETTINGS_KEY\]\?\.fontScale != null/);
});

test("CSS: zoom cả khung, chiều cao khung theo --app-h (JS chia tỉ lệ), cỡ lớn gọn thanh nút", () => {
  assert.match(css, /body \{ zoom: var\(--ui-scale, 1\); \}/);
  assert.match(css, /\.tlnd-app \{[^}]*height: var\(--app-h, 100dvh\);/);
  assert.match(js, /root\.style\.setProperty\("--app-h", `\$\{window\.innerHeight \/ fontScale\}px`\)/);
  assert.match(css, /html\[data-ui-scale="lg"\] \.bot-h \.tb \.tbi \{ display: none; \}/);
});
