// Thẻ "🖨️ Em đã nhận N tệp" ở quầy Lai Châu.
//
// Thẻ này do extension DỰNG (sự kiện máy quét không phải một lượt chat) nên nó nằm ngoài
// đường song ngữ của backend: trước đây thuần tiếng Việt và speak(..., "vi") chốt cứng —
// công dân Mông cứ mỗi tờ scan lại nhận một thẻ tiếng Việt kèm giọng Việt.
//
// Hai ranh giới:
//   1. Lời thoại Mông chỉ có MỘT nguồn: script_mong.py, đẩy xuống qua /voice/config. Nhúng
//      tiếng Mông vào extension là mỗi lần anh Dư sửa bản dịch phải phát hành lại bản mới.
//   2. Thiếu bản Mông thì nói tiếng Việt bằng GIỌNG VIỆT. Đọc chữ Việt bằng giọng Mông là
//      công dân nghe không ra tiếng gì — thà nói ít hơn nói sai.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");

const fn = sidebar.slice(sidebar.indexOf("function renderScanFeedback()"));
const body = fn.slice(0, fn.indexOf("\n  }\n"));

// ── Chữ đến từ BE ───────────────────────────────────────────────────────────────────────
assert.match(body, /voiceCfg\?\.scanFeedback \|\| \{\}/);
assert.match(body, /pack\.vi \|\| SCAN_FEEDBACK_FALLBACK/);

// Bản dự phòng chỉ để sống sót khi BE cũ → CHỈ tiếng Việt, không có chữ Mông nào.
const fb = sidebar.slice(sidebar.indexOf("const SCAN_FEEDBACK_FALLBACK"));
const fbBody = fb.slice(0, fb.indexOf("\n  };"));
for (const hmong of ["pej xeem", "kuv", "ntaub ntawv", "maiv scan", "txaus lawm"]) {
  assert.ok(!fbBody.toLowerCase().includes(hmong),
    `bản dự phòng nhúng tiếng Mông ("${hmong}") — bản dịch phải ở script_mong.py`);
}

// ── Chỉ dùng bản Mông khi ĐANG bật tiếng Mông VÀ BE có gửi ──────────────────────────────
assert.match(body, /voiceLang === "hmong" && _hmongAllowed\(\)\) \? pack\.hmong : null/);

// ── Giọng đi theo NGÔN NGỮ CỦA CHỮ, không theo chế độ ───────────────────────────────────
// hmPack null (BE cũ, hoặc chưa dịch) mà vẫn speak "hmong" là tái hiện đúng lỗi cũ.
assert.match(body, /speak\?\.\(tts, hmPack \? "hmong" : "vi"\)/);
assert.ok(!/speak\?\.\([^)]*,\s*"vi"\s*\)/.test(body.replace(/hmPack \? "hmong" : "vi"/, "")),
  "không được còn lời gọi speak chốt cứng 'vi'");

// ── Khối Mông in nghiêng ở CUỐI, sau toàn bộ tiếng Việt ─────────────────────────────────
assert.match(body, /md \+= `\\n\\n\*\$\{fill\(hmPack\.md\)\}\*`/);
const viLine = body.indexOf("let md = fill(viPack.md)");
assert.ok(viLine >= 0 && viLine < body.indexOf("hmPack?.md"),
  "tiếng Việt phải dựng TRƯỚC rồi mới nối khối Mông");

// ── {count} thay ở cả md lẫn tts ────────────────────────────────────────────────────────
// ttsMore có {count}; quên thay là công dân nghe nguyên chữ "{count}".
assert.match(body, /const fill = \(s\) => String\(s \|\| ""\)\.replace\(\/\\\{count\\\}\/g/);
assert.match(body, /const tts = fill\(n <= 1 \? spoken\.tts : \(spoken\.ttsMore \|\| spoken\.tts\)\)/);

// ── Thẻ hướng dẫn đặt giấy (ảnh + lời) ──────────────────────────────────────────────────
// Cùng loại: extension dựng, nên cũng nằm ngoài đường song ngữ của BE.
const guide = sidebar.slice(sidebar.indexOf("function renderScanGuideCard()"));
const guideBody = guide.slice(0, guide.indexOf("\n  }\n"));

assert.match(guideBody, /voiceCfg\?\.scanGuide \|\| \{\}/);
assert.match(guideBody, /pack\.vi \|\| SCAN_GUIDE_FALLBACK/);
assert.match(guideBody, /voiceLang === "hmong" && _hmongAllowed\(\)\) \? pack\.hmong : null/);
// Chú thích Mông đi kèm heading, body và note — thiếu dòng nào là mất hẳn ý đó.
for (const key of ["heading", "body", "note"]) {
  assert.ok(guideBody.includes(`\${hm("${key}")}`), `thiếu chú thích Mông cho ${key}`);
}
// alt của ảnh: trình đọc màn hình đang ở tiếng Mông thì đọc bản Mông.
assert.match(guideBody, /hmG\?\.alt \|\| viG\.alt/);

// Chữ từ BE đi vào innerHTML → phải escape TRƯỚC khi đổi **…** thành <b>, nếu không là mở
// đường chèn thẻ vào panel.
const bold = sidebar.slice(sidebar.indexOf("function inlineBold("));
assert.match(bold.slice(0, 200),
  /window\.escapeHtml\(String\(s \|\| ""\)\)\.replace\(\/\\\*\\\*\(\[\^\*\]\+\)\\\*\\\*\/g, "<b>\$1<\/b>"\)/);
// Không còn chuỗi tiếng Việt nội suy thẳng vào innerHTML của thẻ.
assert.ok(!/<div class="scan-guide-h">🖨️ Đặt giấy tờ/.test(sidebar),
  "heading vẫn ghi cứng trong markup — phải lấy từ BE");

// Bản dự phòng của thẻ hướng dẫn cũng CHỈ tiếng Việt.
const gfb = sidebar.slice(sidebar.indexOf("const SCAN_GUIDE_FALLBACK"));
const gfbBody = gfb.slice(0, gfb.indexOf("\n  };"));
for (const hmong of ["pej xeem", "kuv", "lub maiv", "daim duab", "txaus lawm"]) {
  assert.ok(!gfbBody.toLowerCase().includes(hmong),
    `bản dự phòng nhúng tiếng Mông ("${hmong}") — bản dịch phải ở script_mong.py`);
}

console.log("scan feedback + hướng dẫn: song ngữ theo BE, giọng theo ngôn ngữ của chữ passed");
