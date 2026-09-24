const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

// Hợp đồng BE ↔ FE cho gia hạn CCHN thú y: untickRows (bỏ tick dòng cổng tick sẵn) và
// fallbackComponentName (modal "Thêm giấy tờ" lỗi → đính chung vào dòng dự phòng).
const content = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8").replace(/\r\n/g, "\n");
const popup = fs.readFileSync(path.join(__dirname, "..", "popup.js"), "utf8").replace(/\r\n/g, "\n");

const attpStart = content.indexOf("async function attachFilesByAttpRow");
const attpEnd = content.indexOf("async function attachFilesByPlan", attpStart);
const attp = content.slice(attpStart, attpEnd);
assert.ok(attpStart >= 0 && attpEnd > attpStart, "Không tách được attachFilesByAttpRow");
assert.match(attp, /item\.untickRows/, "Engine attp-row phải đọc untickRows");
assert.match(attp, /if \(row && !planned\) await untickAttpRowCheckbox\(row\)/,
  "Không được bỏ tick dòng mà kế hoạch sắp đính tệp");
assert.ok(attp.indexOf("untickAttpRowCheckbox") < attp.indexOf("for (const items of groups.values())"),
  "Phải bỏ tick TRƯỚC khi đính tệp");

const untickStart = content.indexOf("async function untickAttpRowCheckbox");
const untick = content.slice(untickStart, content.indexOf("async function setAttpRowLoaiBan", untickStart));
assert.match(untick, /attpRowAttachedFingerprints\(row\)\.length/, "Dòng đã có tệp thì không bỏ tick");

const planStart = content.indexOf("async function attachFilesByPlan");
const plan = content.slice(planStart, content.indexOf("\n  async function attachFilesToRequiredCopyCertification", planStart));
const ensure = plan.indexOf("await H.ensureMaeAddDocumentRows(addDocumentItems)");
const fallback = plan.indexOf("addDocumentItems.every((item) => item.fallbackComponentName)", ensure);
const plainError = plan.indexOf("if (ensureResult?.error) {", ensure);
assert.ok(ensure >= 0 && fallback > ensure, "Thiếu nhánh dự phòng sau modal Thêm giấy tờ");
assert.ok(plainError > fallback, "Nhánh dự phòng phải chạy trước khi trả lỗi modal");
assert.match(plan, /componentName: item\.fallbackComponentName/);
assert.match(plan, /notes: \[note\]/);

assert.match(popup, /const attachNotes = \(attachRes\?\.notes \|\| \[\]\)/, "Popup phải hiện notes của engine");
assert.match(popup, /cfg\.key === "gia-han-chung-chi-hanh-nghe-thu-y"/, "Gia hạn phải gửi formContext người nộp");

console.log("attach untickRows + fallbackComponentName contract passed");
