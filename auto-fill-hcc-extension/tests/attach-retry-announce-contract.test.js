// Cổng dịch vụ công lỗi giữa lượt đính kèm → engine hoãn tệp để thử lại (round-robin 3 lượt).
// Trong lúc chờ, trợ lý phải NÓI cho công dân biết, không thì họ tưởng máy treo.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const attach = fs.readFileSync(path.join(root, "content", "attach-core.js"), "utf8");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
const background = fs.readFileSync(path.join(root, "background.js"), "utf8");

test("engine báo MỘT lần mỗi lượt, chỉ khi tệp còn lượt thử lại", () => {
  assert.match(attach, /if \(retryAnnounced \|\| round >= MAX_ROUNDS\) return;/);
  assert.match(attach, /chrome\.runtime\.sendMessage\(\{ __tlnd: "attachRetrying" \}/);
  // Báo ở hai nhánh hỏng do CỔNG (ví giấy tờ + danh sách tệp khác), không ở nhánh không tìm thấy dòng.
  assert.equal((attach.match(/announceRetry\(round\);\n\s*lastFailAt = Date\.now\(\);\n\s*deferred\.push/g) || []).length, 2);
});

test("sidebar đọc đúng câu, chỉ cho tab của mình (trực tiếp hoặc tab tách qua relay), chặn lặp", () => {
  assert.match(sidebar, /Dạ dịch vụ công đang lỗi, công dân chờ chút em đính kèm lại ạ\./);
  assert.match(sidebar, /msg\?\.__tlnd === "attachRetrying"\) mine = String\(sender\?\.tab\?\.id \|\| ""\) === String\(TAB_ID\)/);
  assert.match(sidebar, /msg\?\.__tlnd === "attachRetryingRelay"\) mine = String\(msg\.originTabId \|\| ""\) === String\(TAB_ID\)/);
  assert.match(sidebar, /Date\.now\(\) - attachRetrySaidAt < 30000/);
});

test("background chuyển tiếp câu báo của tab tách về tab gốc", () => {
  assert.match(background, /msg\?\.__tlnd !== "attachRetrying"/);
  assert.match(background, /\{ __tlnd: "attachRetryingRelay", originTabId \}/);
});

test("thử lại chỉ chờ PHẦN CÒN THIẾU kể từ lần hỏng gần nhất (tệp giữa hỏng → xong tệp cuối thử lại ngay)", () => {
  assert.match(attach, /const minGapMs = round === 2 \? 500 : 1000;/);
  assert.match(attach, /if \(backoffMs\) await sleep\(backoffMs\);/);
  // MỌI nhánh hoãn đều ghi mốc hỏng.
  assert.equal((attach.match(/lastFailAt = Date\.now\(\);\n\s*deferred\.push\(\{ item, index: i \}\);/g) || []).length, 4);
});
