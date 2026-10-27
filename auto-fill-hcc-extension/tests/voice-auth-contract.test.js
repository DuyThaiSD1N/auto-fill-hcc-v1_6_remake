const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const root = path.resolve(__dirname, "..");
const auth = fs.readFileSync(path.join(root, "api", "auth.js"), "utf8");
const asr = fs.readFileSync(path.join(root, "services", "asr.js"), "utf8");
const tts = fs.readFileSync(path.join(root, "services", "tts.js"), "utf8");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
const background = fs.readFileSync(path.join(root, "background.js"), "utf8");
const offscreen = fs.readFileSync(path.join(root, "offscreen.js"), "utf8");

test("ASR và TTS lấy JWT còn hạn trước khi mở WebSocket", () => {
  assert.match(auth, /async function getAccessToken\(minValiditySeconds = 30\)/);
  assert.match(auth, /_accessNeedsRefresh\(state\?\.access, minValiditySeconds\)/);
  assert.match(auth, /load, login, logout, refresh, authFetch, getAccessToken/);
  assert.match(sidebar, /const accessToken = await window\.tlndAuth\?\.getAccessToken\?\.\(\)/);
  assert.match(tts, /await window\.tlndAuth\?\.getAccessToken\?\.\(\)/);
});

test("JWT voice đi bằng subprotocol và được chuyển nguyên vẹn qua offscreen", () => {
  assert.match(asr, /new WebSocket\(wsUrl, \["tlnd-voice", `tlnd-auth\.\$\{this\.accessToken\}`\]\)/);
  assert.match(tts, /protocols: \["tlnd-voice", `tlnd-auth\.\$\{accessToken\}`\]/);
  assert.match(background, /accessToken: msg\.accessToken \|\| ""/);
  assert.match(background, /protocols: msg\.protocols \|\| \[\]/);
  assert.match(offscreen, /accessToken: msg\.accessToken \|\| ""/);
  assert.match(offscreen, /new WebSocket\(item\.url, item\.protocols \|\| \[\]\)/);
  assert.doesNotMatch(asr, /[?&](?:token|access_token)=/);
  assert.doesNotMatch(tts, /[?&](?:token|access_token)=/);
});

test("TTS đã bị dừng trong lúc refresh không phát lại câu cũ", () => {
  assert.match(tts, /let _generation = 0/);
  assert.match(tts, /if \(generation !== _generation\) return/);
  assert.match(tts, /function stop\(\)[\s\S]*?_generation\+\+/);
});
