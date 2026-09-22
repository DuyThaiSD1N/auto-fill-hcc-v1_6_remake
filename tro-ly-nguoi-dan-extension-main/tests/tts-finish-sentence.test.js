// Chuyển bước: cắt câu đang đọc hay đọc cho hết?
//
// Mặc định CẮT — bot không được đọc hướng dẫn của bước đã qua. Ở quầy Lai Châu thì ngược
// lại: công dân nghe qua lời dịch tiếng Mông, mất nửa câu là mất hẳn ý. BE bật cờ
// finishSentenceBeforeNext theo tỉnh của tài khoản.
//
// Ba ranh giới:
//   1. Chính sách do BE quyết. Dò tỉnh ngay trong extension là thêm tỉnh phải phát hành lại
//      bản mới cho tất cả máy quầy.
//   2. Cờ bật thì XẾP HÀNG, không phải bỏ đọc câu mới.
//   3. Ngắt lời bằng micro (barge-in) VẪN cắt — người nói luôn được ưu tiên.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
const offscreen = fs.readFileSync(path.join(root, "offscreen.js"), "utf8");

// ── Chính sách đến từ BE ────────────────────────────────────────────────────────────────
assert.match(sidebar, /voiceCfg\?\.finishSentenceBeforeNext === true/);
// So sánh === true: cờ vắng mặt (server cũ) phải là "cắt như cũ", không phải undefined-truthy.
assert.ok(!/finishSentenceBeforeNext\s*\)/.test(sidebar),
  "phải so sánh === true, không dùng trực tiếp làm điều kiện");
// Tên tỉnh KHÔNG được xuất hiện trong LOGIC (chú thích thì được — nó giải thích cờ của BE).
const reply = sidebar.slice(sidebar.indexOf("function renderReply("));
const replyBody = reply.slice(0, reply.indexOf("\n  function "));
const replyCode = replyBody.replace(/\/\/.*/g, "");
assert.ok(!/lai chau|Lai Châu/i.test(replyCode),
  "dò tỉnh trong extension = thêm tỉnh phải phát hành lại bản mới");
assert.ok(!/tlndAuth\?\.user\?\.tinh/.test(replyCode),
  "đừng đọc tỉnh từ token: chính sách do BE quyết, FE chỉ nhận cờ");

// ── Bật cờ = xếp hàng, không phải bỏ đọc ────────────────────────────────────────────────
assert.match(replyBody, /if \(!queueThisReply\) stopReplyTts\(\);/);
// speak() vẫn được gọi trong cả hai nhánh — chỉ khác có stop trước hay không.
assert.match(replyBody, /window\.__hccTTS\?\.speak\?\.\(d\.tts_text, d\.tts_lang \|\| "vi"/);
// Bộ đếm phải tăng ở CẢ hai nhánh, nếu không micro mở giữa chừng cắt mất câu đang xếp hàng.
const incAfterStop = replyBody.indexOf("replyTtsInFlight += 1");
assert.ok(incAfterStop > replyBody.indexOf("if (!queueThisReply)"),
  "replyTtsInFlight phải tăng sau nhánh rẽ, tức là tăng cho MỌI lượt");
assert.match(replyBody, /replyTtsInFlight === 0\) startVoice\(\)/,
  "chỉ mở mic khi hàng đợi đã cạn");

// ── Trường hợp fill_report cũ vẫn giữ ───────────────────────────────────────────────────
// Đây là lý do cơ chế xếp hàng tồn tại từ đầu; gộp điều kiện không được làm mất nó.
assert.match(replyBody, /prevState === "filling" && d\.state === "reviewing"/);

// ── Barge-in vẫn cắt ────────────────────────────────────────────────────────────────────
const startVoice = sidebar.slice(sidebar.indexOf("async function startVoice()"));
assert.match(startVoice.slice(0, 600), /stopReplyTts\(\); \/\/ đang đọc mà mở mic/);

// ── Hàng đợi thật nằm ở offscreen ───────────────────────────────────────────────────────
// Không có hàng đợi ở tầng phát thì "không stop" chỉ là hai câu chồng lên nhau.
assert.match(offscreen, /ttsEnqueue\(\{/);
assert.match(offscreen, /const ttsQueue = \[\]/);
assert.match(offscreen, /ttsQueue\.push\(item\)/);

console.log("tts: quầy Lai Châu đọc trọn câu, barge-in vẫn cắt passed");
