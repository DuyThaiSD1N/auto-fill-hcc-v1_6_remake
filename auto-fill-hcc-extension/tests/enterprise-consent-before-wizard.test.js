// Cổng ĐKKD qua mạng: một lượt bấm phải chạy MỘT LÈO
//   đồng ý điều khoản -> wizard 3 bước -> vào khối dữ liệu -> quét + điền.
//
// Lỗi cũ: gate consent nằm SAU lệnh mở hồ sơ. Lượt bấm đầu chỉ "lên đạn" wizard rồi return, chưa hỏi
// gì. Wizard đưa tới khối dữ liệu, panel tự bấm lại nút để quét tiếp, và ĐÚNG LÚC ĐÓ màn điều khoản
// mới bật lên rồi chặn luôn lượt tự chạy -> đứt mạch, người dùng phải bấm thêm.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const popup = fs.readFileSync(path.join(__dirname, "..", "popup.js"), "utf8");

function fnBody(name, endMarker) {
  const start = popup.indexOf(`async function ${name}(`);
  assert.ok(start >= 0, `Không thấy hàm ${name}`);
  const end = popup.indexOf(endMarker, start);
  assert.ok(end > start, `Không cắt được thân hàm ${name}`);
  return popup.slice(start, end);
}

// ---- Consent phải nằm TRONG nhánh mở hồ sơ, TRƯỚC khi lên đạn wizard ----
const opener = fnBody("startEnterpriseDossierIfNeeded", "// Chặng 2 của luồng doanh nghiệp");
const iConsent = opener.indexOf("requireConsent(triggerEl)");
const iArm = opener.indexOf("armEnterpriseAutostart(cfg)");
const iPending = opener.indexOf("setEnterprisePendingFill");
assert.ok(iConsent >= 0, "Nhánh mở hồ sơ phải tự hỏi đồng ý, không để dòng sau lo");
assert.ok(iArm >= 0 && iConsent < iArm,
  "Phải hỏi đồng ý TRƯỚC khi lên đạn wizard, nếu không màn điều khoản sẽ bật giữa chừng");
assert.ok(iPending >= 0 && iConsent < iPending,
  "Cờ chờ quét chỉ được đặt sau khi đã đồng ý");
assert.match(opener, /if \(!\(await requireConsent\(triggerEl\)\)\) return true;/,
  "Mở màn điều khoản thì phải trả TRUE — lượt bấm đã tiêu thụ, tránh chạy tiếp nửa vời");

// ---- Hai nút đều phải truyền chính nó làm trigger để bấm lại sau khi đồng ý ----
assert.match(popup, /startEnterpriseDossierIfNeeded\(ocrBtn\)/,
  'Nút "Quét và nhập dữ liệu" phải truyền trigger');
assert.match(popup, /startEnterpriseDossierIfNeeded\(fillAllBtn\)/,
  'Nút "Quét nhập thông tin và đính kèm" phải truyền trigger');
assert.doesNotMatch(popup, /startEnterpriseDossierIfNeeded\(\)/,
  "Không được còn lệnh gọi thiếu trigger — đồng ý xong sẽ không biết bấm lại nút nào");

// ---- Đồng ý xong phải tự bấm lại đúng nút đang chờ ----
assert.match(popup, /const trigger = pendingConsentTrigger;[\s\S]{0,160}trigger\.click\(\)/,
  "Đồng ý xong phải tự bấm lại nút đang chờ để nối mạch, không bắt bấm tay");

// ---- Chặng cuối: vào tới khối dữ liệu thì tự quét, không hỏi lại ----
const resume = fnBody("resumeEnterpriseFillIfPending", "function hasStrongProcedureIdentity");
assert.match(resume, /if \(!stage\.inDossier\) return;/,
  "Chỉ quét khi đã thật sự vào khối dữ liệu");
assert.match(resume, /fillAllBtn\.click\(\)/,
  "Vào tới nơi là tự bấm quét — consent đã được hỏi từ đầu luồng nên lượt này đi thẳng");

console.log("enterprise consent before wizard: single-click end-to-end flow passed");
