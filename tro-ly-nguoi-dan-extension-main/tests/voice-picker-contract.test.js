// Chọn giọng đọc + tốc độ ở màn Cài đặt.
//
// Ranh giới phải giữ:
//   1. DANH SÁCH giọng do web quản trị cấp (/voice/config → voiceOptions; BE cũ chỉ có voices). Hardcode ở extension là
//      mỗi lần thêm giọng phải phát hành lại bản mới cho tất cả máy quầy.
//   2. Giọng + tốc độ lưu THEO TÀI KHOẢN (account_settings.ttsVoiceVi / ttsVoiceHmong / ttsTempo) và THEO NGÔN NGỮ —
//      lưu một giá trị chung là đổi giọng Việt kéo theo đổi giọng Mông.
//   3. Phát âm thanh theo sample_rate của từng khung (giọng 22050 / 24000 Hz) và báo BE bằng sr=1.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
const html = fs.readFileSync(path.join(root, "sidebar.html"), "utf8");
const tts = fs.readFileSync(path.join(root, "services", "tts.js"), "utf8");
const offscreen = fs.readFileSync(path.join(root, "offscreen.js"), "utf8");
const css = fs.readFileSync(path.join(root, "sidebar.css"), "utf8");

// ── Danh sách đến từ BE, không hardcode ──
assert.match(sidebar, /const table = \(voiceCfg\?\.voiceOptions \|\| \{\}\)\[lang\];/);
assert.match(sidebar, /\(voiceCfg\?\.voices \|\| \{\}\)\[lang\] \|\| \[\]/, "BE cũ chưa có voiceOptions vẫn dùng voices");
assert.ok(!/"phuongnhi-north"|"vuado"|Cô Xi|Anh Dơ/.test(sidebar),
  "tên/id giọng phải lấy từ /voice/config, không nhúng vào extension");
assert.ok(!/phuongnhi|vuado/.test(html), "sidebar.html không được nhúng id giọng");

// ── Một giọng thì ẨN ô chọn (thanh tốc độ vẫn hiện) ──
assert.match(sidebar, /\$voiceSelect\.hidden = list\.length < 2;/);
assert.match(sidebar, /\$voiceCard\.hidden = !voiceCfg\?\.tts;/);
assert.match(html, /id="voice-card"[^>]*hidden/);
assert.match(css, /\.settings-row\[hidden\]\s*\{\s*display:\s*none/);
for (const block of ["lang-bar", "start-screen", "settings-screen"]) {
  assert.match(css, new RegExp(`\\.${block}\\[hidden\\]`), `${block} thiếu rule [hidden]`);
}
// Giọng chưa chọn → ô hiện giọng mặc định.
assert.match(sidebar, /voiceChoice\[voiceLang\] \|\| \(voiceCfg\?\.defaultVoice \|\| \{\}\)\[voiceLang\]/);

// ── Lưu theo TÀI KHOẢN, theo NGÔN NGỮ ──
assert.match(sidebar, /const key = voiceLang === "hmong" \? "ttsVoiceHmong" : "ttsVoiceVi";/);
assert.match(sidebar, /saveAccountSetting\(\{ \[key\]: \$voiceSelect\.value \}, "voice-status"\)/);
assert.match(sidebar, /saveAccountSetting\(\{ ttsTempo: /);
assert.match(sidebar, /applyVoiceSettings\(settings\);/, "cài đặt tài khoản tải về thì đẩy giọng + tốc độ xuống service");
assert.match(sidebar, /applyVoiceSettings\(\{\}\);/, "đăng xuất về giọng mặc định");
assert.doesNotMatch(sidebar, /const VOICE_KEY = "tlnd_voice";/, "không còn lưu giọng theo máy");

// ── Đổi ngôn ngữ phải vẽ lại ô chọn ──
const langBar = sidebar.slice(sidebar.indexOf("function updateLangBar()"));
assert.match(langBar.slice(0, langBar.indexOf("\n  }")), /renderVoiceSettings\(\);/);

// ── Nghe thử: câu tiếng Việt → ẩn ở chế độ tiếng Mông ──
assert.match(sidebar, /\$voiceTryBtn\.hidden = voiceLang === "hmong";/);

// ── tts.js gửi kèm giọng, tốc độ, sr=1; offscreen phát đúng tần số ──
assert.match(tts, /function setVoice\(map\)/);
assert.match(tts, /function setTempo\(value\)/);
assert.match(tts, /if \(voice\) params\.set\("voice", voice\);/);
assert.match(tts, /if \(_tempo != null\) params\.set\("tempo", String\(_tempo\)\);/);
assert.match(tts, /params\.set\("sr", "1"\);/);
assert.match(tts, /window\.__hccTTS = \{ speak, stop, setMuted, setVoice, setTempo, isSpeaking \};/);
assert.match(tts, /function speak\(text, lang = "vi", onDone\)/);
assert.match(offscreen, /ctx\.createBuffer\(1, float32\.length, Number\(data\.sample_rate\) \|\| 16000\)/);

console.log("voice picker: danh sách từ BE, lưu theo tài khoản + theo ngôn ngữ, đúng tần số passed");
