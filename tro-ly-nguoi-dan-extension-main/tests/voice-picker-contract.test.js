// Chọn giọng đọc ở màn Cài đặt — thay cho giọng chốt cứng bằng env cho MỌI phường.
//
// Hai ranh giới phải giữ:
//   1. DANH MỤC giọng do BE cấp (/voice/config → voices). Hardcode danh sách ở extension là
//      mỗi lần thêm giọng phải phát hành lại bản mới cho tất cả máy quầy.
//   2. Lựa chọn lưu THEO MÁY và THEO NGÔN NGỮ. Tiếng Việt và tiếng Mông có danh mục khác
//      nhau; lưu một giá trị chung là đổi giọng Việt kéo theo đổi giọng Mông.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
const html = fs.readFileSync(path.join(root, "sidebar.html"), "utf8");
const tts = fs.readFileSync(path.join(root, "services", "tts.js"), "utf8");
const css = fs.readFileSync(path.join(root, "sidebar.css"), "utf8");

// ── Danh mục đến từ BE, không hardcode ──────────────────────────────────────────────────
assert.match(sidebar, /const list = \(voiceCfg\?\.voices \|\| \{\}\)\[voiceLang\] \|\| \[\];/);
assert.ok(!/"phuongnhi-north"|"vuado"|Cô Xi|Anh Dơ/.test(sidebar),
  "tên/id giọng phải lấy từ /voice/config, không nhúng vào extension");
assert.ok(!/phuongnhi|vuado/.test(html), "sidebar.html không được nhúng id giọng");

// ── Một giọng thì ẨN cả thẻ ─────────────────────────────────────────────────────────────
// Bày một ô chọn duy nhất, bấm vào không đổi gì → cán bộ tưởng hỏng.
assert.match(sidebar, /\$voiceCard\.hidden = list\.length < 2;/);
assert.match(html, /id="voice-card"[^>]*hidden/);
// `hidden` của trình duyệt là display:none ở tầng USER-AGENT nên THUA mọi rule display của
// tác giả: .settings-card đặt display:flex → thẻ có hidden vẫn hiện ra RỖNG. Đã gặp thật.
assert.match(css, /\.settings-card\[hidden\]\s*\{\s*display:\s*none/);
// Mọi khối ẩn/hiện khác trong file cũng phải khai lại, nếu không lặp lại đúng lỗi này.
for (const block of ["lang-bar", "start-screen", "settings-screen"]) {
  assert.match(css, new RegExp(`\\.${block}\\[hidden\\]`), `${block} thiếu rule [hidden]`);
}

// ── Ô đang chọn phải NHÌN THẤY ĐƯỢC ─────────────────────────────────────────────────────
// aria-checked chỉ trình đọc màn hình nghe được. Thiếu .on là hai ô giọng hiện y hệt nhau,
// bấm xong không biết đã đổi chưa — đã gặp thật.
assert.match(sidebar, /btn\.classList\.toggle\("on", v\.id === current\);/);
assert.match(css, /\.settings-seg button\.on\s*\{/);
// Hover đổi mỗi màu chữ thì hai ô cùng nền trong suốt vẫn khó phân biệt con trỏ đang ở đâu.
assert.match(css, /\.settings-seg button:not\(\.on\)[^{]*:hover\s*\{[^}]*background:/);
// Mọi giọng đều nằm trong danh mục BE nên luôn có đúng một ô sáng: current rơi về defaultVoice.
assert.match(sidebar, /voiceChoice\[voiceLang\] \|\| \(voiceCfg\?\.defaultVoice \|\| \{\}\)\[voiceLang\]/);

// ── Lưu theo MÁY và theo NGÔN NGỮ ───────────────────────────────────────────────────────
assert.match(sidebar, /const VOICE_KEY = "tlnd_voice";/);
assert.match(sidebar, /voiceChoice = \{ \.\.\.voiceChoice, \[voiceLang\]: id \};/,
  "phải lưu theo từng ngôn ngữ, không ghi đè lẫn nhau");
assert.match(sidebar, /chrome\.storage\?\.local\.set\(\{ \[VOICE_KEY\]: voiceChoice \}/);
// Khôi phục lúc mở panel — phiên mới/reload vẫn giữ giọng cán bộ quen nghe.
assert.match(sidebar, /chrome\.storage\?\.local\.get\(\[VOICE_KEY\]/);

// ── Đổi ngôn ngữ phải vẽ lại ô chọn ─────────────────────────────────────────────────────
// Danh mục tiếng Việt và tiếng Mông khác nhau; không vẽ lại là hiện giọng của ngôn ngữ cũ.
const langBar = sidebar.slice(sidebar.indexOf("function updateLangBar()"));
assert.match(langBar.slice(0, langBar.indexOf("\n  }")), /renderVoiceSettings\(\);/);

// ── tts.js gửi kèm giọng ────────────────────────────────────────────────────────────────
assert.match(tts, /function setVoice\(map\)/);
assert.match(tts, /if \(voice\) params\.set\("voice", voice\);/);
assert.match(tts, /window\.__hccTTS = \{ speak, stop, setMuted, setVoice \};/);
// Giọng giữ trong service, KHÔNG thêm tham số vào speak(): các chỗ gọi speak rải rác trong
// sidebar, thêm tham số là dễ sót một chỗ rồi đọc lẫn giọng giữa chừng.
assert.match(tts, /function speak\(text, lang = "vi", onDone\)/);
assert.equal((sidebar.match(/__hccTTS\?\.setVoice\?\.\(voiceChoice\)/g) || []).length, 2,
  "phải đẩy giọng xuống service cả lúc khôi phục lẫn lúc đổi");

console.log("voice picker: danh mục từ BE, lưu theo máy + theo ngôn ngữ passed");
