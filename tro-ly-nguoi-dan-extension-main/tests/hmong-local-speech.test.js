// Chế độ tiếng Mông: hai câu sidebar TỰ ĐỌC ngoài lượt chat (cổng lỗi giữa lúc đính kèm, vừa nhận thêm tệp) phải đọc bản
// Mông BE gửi qua /voice/config localSpeech bằng giọng Mông; BE cũ chưa có bản Mông thì im — không đọc câu tiếng Việt.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const sidebar = fs.readFileSync(path.join(__dirname, "..", "sidebar.js"), "utf8").replace(/\/\/[^\n]*/g, "");

const retry = sidebar.slice(sidebar.indexOf("attachRetrySaidAt = Date.now();"), sidebar.indexOf("Công dân tự gõ trên form SurveyJS") > 0
  ? sidebar.indexOf("attachRetrySaidAt = Date.now();") + 900 : undefined);
assert.match(retry, /localSpeech\?\.\[hm \? "hmong" : "vi"\]\?\.attachRetry \|\| \(hm \? "" : ATTACH_RETRY_TEXT\)/,
  "Mông không có bản dịch thì rỗng, không rơi về câu Việt");
assert.match(retry, /speak\?\.\(speech, hm \? "hmong" : "vi"/);
assert.doesNotMatch(retry, /speak\?\.\(ATTACH_RETRY_TEXT, "vi"/);

const files = sidebar.slice(sidebar.indexOf("filesAnnounceTtsTimer = setTimeout"), sidebar.indexOf("filesAnnounceTtsTimer = setTimeout") + 900);
assert.match(files, /const lang = voiceLang === "hmong" && _hmongAllowed\(\) \? "hmong" : "vi";/);
assert.match(files, /localSpeech\?\.\[lang\]\?\.filesReceived/);
assert.match(files, /lang === "vi" \? "Tôi đã nhận \{count\} tệp mà công dân gửi lên nhé\." : ""/);
assert.match(files, /if \(tpl\) window\.__hccTTS\?\.speak\?\./);

console.log("hmong local speech passed");
