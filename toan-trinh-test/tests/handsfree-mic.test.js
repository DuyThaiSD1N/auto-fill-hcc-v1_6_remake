// Rảnh tay: lúc nào bot đang chờ công dân nói thì mic PHẢI đang nghe; chỉ người dùng mới tắt được rảnh tay.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const sidebar = strip(fs.readFileSync(path.join(root, "sidebar.js"), "utf8"));
const asr = strip(fs.readFileSync(path.join(root, "services", "asr.js"), "utf8"));
const tts = strip(fs.readFileSync(path.join(root, "services", "tts.js"), "utf8"));

test("chốt câu RỖNG vẫn báo stopped (không treo 'Đang nghe')", () => {
  assert.match(asr, /if \(finalText\) this\.onFinal\(finalText\);\s*else this\._setState\("stopped"\);/);
});

test("vòng canh: bot đang chờ (không đọc, không gọi BE, không Cài đặt) thì mở mic", () => {
  assert.match(sidebar, /function micWanted\(\) \{\s*return \(handsfree \|\| pendingListen\) && voiceCfg\.asr && !voiceListening && !busy && !botWorking\(\) && !ratingNoteSink/);
  assert.match(sidebar, /!window\.__hccTTS\?\.isSpeaking\?\.\(\) && Date\.now\(\) >= micRetryAt;/);
  assert.match(sidebar, /setInterval\(ensureMic, 1500\);/);
  // Phiên nghe treo → làm mới.
  assert.match(sidebar, /if \(stuckConnecting \|\| now - micLastEventAt > 45000\) pauseMic\(\);/);
  // TTS báo đang đọc cả câu không có onDone, có hạn chót để không kẹt.
  assert.match(tts, /_active\[id\] = Date\.now\(\);/);
  assert.match(tts, /if \(now - at > ACTIVE_STALE_MS\) delete _active\[id\];/);
});

test("không nghe thấy gì / lỗi mạng KHÔNG tắt rảnh tay; chỉ thiếu quyền micro mới tắt", () => {
  assert.doesNotMatch(sidebar, /emptyTurns/);
  assert.doesNotMatch(sidebar, /Em tạm tắt chế độ rảnh tay/);
  assert.match(sidebar, /micRetryAt = Date\.now\(\) \+ Math\.min\(30000, 1000 \* 2 \*\* \(micErrors - 1\)\);/);
  const errorBlock = sidebar.slice(sidebar.indexOf('if (msg.name === "NotAllowedError"'));
  assert.match(errorBlock.slice(0, 900), /window\.open\(chrome\.runtime\.getURL\("permission\.html"\), "_blank"\);[\s\S]*?if \(handsfree\) setHandsfree\(false\);\s*\} else \{/);
});

test("bot sắp đọc thì tắt mic trước (không thu tiếng loa của bot)", () => {
  assert.match(sidebar, /if \(handsfree \|\| listenAfter\) pauseMic\(\);\s*replyTtsInFlight \+= 1;/);
});

test("nhớ rảnh tay theo tab qua các lần cổng tải lại trang", () => {
  assert.match(sidebar, /const HANDSFREE_KEY = TAB_ID \? `tlnd_handsfree:\$\{TAB_ID\}` : "";/);
  assert.match(sidebar, /function setHandsfree\(on\) \{[\s\S]{0,120}?rememberHandsfree\(on\);/);
  assert.match(sidebar, /get\(\[HANDSFREE_KEY\], \(res\) => \{[\s\S]*?handsfree = true;/);
  // Nộp xong (chờ đăng xuất) thì xoá.
  assert.match(sidebar, /handsfree = false;\s*rememberHandsfree\(false\);/);
});

test("tự mở mic không bao giờ cắt câu bot đang đọc (mở mic = tạo lại offscreen đang phát loa)", () => {
  assert.match(sidebar, /function listenWhenQuiet\(\) \{\s*if \(window\.__hccTTS\?\.isSpeaking\?\.\(\) \|\| busy \|\| botWorking\(\)\) \{[\s\S]*?return;\s*\}\s*startVoice\(\);/);
  // Lượt không có lời đọc (lượt hệ thống im lặng) KHÔNG gọi thẳng startVoice nữa.
  assert.match(sidebar, /\} else if \(handsfree \|\| listenAfter\) \{\s*listenWhenQuiet\(\);\s*\}/);
  assert.match(sidebar, /replyTtsInFlight === 0\) listenWhenQuiet\(\);/);
});

test("bot đang THAO TÁC trên trang (điền, chọn cơ quan, bấm, đính…) hoặc đang đọc giấy tờ thì tắt mic", () => {
  for (const action of ["fillFields", "selectAgency", "guidedClickNext", "attachFilesByPlan", "declarationConfirm"]) {
    assert.match(sidebar, new RegExp(`const PAGE_WORK_ACTIONS = new Set\\(\\[[\\s\\S]*?"${action}"`));
  }
  // Lệnh thao tác vừa gửi xuống trang → tắt mic ngay; xong (hoặc lỗi) mới trừ đếm.
  assert.match(sidebar, /if \(work\) \{\s*pageWorkInFlight \+= 1;\s*pauseMic\(\);\s*\}/);
  assert.match(sidebar, /\}\)\.finally\(\(\) => \{\s*if \(!work\) return;\s*pageWorkInFlight = Math\.max\(0, pageWorkInFlight - 1\);/);
  assert.match(sidebar, /function botWorking\(\) \{\s*return pageWorkInFlight > 0 \|\| Date\.now\(\) - pageWorkEndedAt < 2000 \|\| \(!!\$pipe && !pipeFinished\);/);
  // Mic đang mở mà bot bắt đầu nói / thao tác → vòng canh tắt mic.
  assert.match(sidebar, /if \(handsfree && voiceListening && \(botWorking\(\) \|\| window\.__hccTTS\?\.isSpeaking\?\.\(\)\)\) \{\s*pauseMic\(\);/);
});
