// Đính kèm (no-handfree): một tệp hỏng KHÔNG được chặn các tệp còn lại, và KHÔNG được báo
// thành công khi cổng chưa thật sự ghi nhận.
//
// Bối cảnh: cổng moj trả 500 xen kẽ — lô 4 tệp chỉ vào được 2-3. Vòng cũ `break` ngay ở tệp
// đầu hỏng nên các tệp sau không được thử lần nào; vòng thử-lại-tại-chỗ thì ngồi sleep 2s+4s
// rồi vẫn hỏng (cổng vừa 500 thì thử ngay cũng 500). Khuôn này đã áp cho handfree trước.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const content = fs.readFileSync(path.join(root, "content.js"), "utf8");

test("hỏng một tệp thì HOÃN rồi đi tiếp, không chặn các tệp sau", () => {
  assert.match(content, /const MAX_ROUNDS = 3/);
  assert.match(content, /for \(let round = 1; round <= MAX_ROUNDS && queue\.length/);
  // Backoff TĂNG DẦN trước retry: cổng 500/đơ cần thời gian hồi; tệp cuối/duy nhất chờ lâu hơn.
  assert.match(content, /const backoffMs = \(round - 1\) \* 3000 \+ \(queue\.length <= 1 \? 2500 : 0\)/);
  assert.match(content, /deferred\.push\(\{ item, index: i \}\);\s*\n\s*continue;/);
  assert.match(content, /queue = deferred;/);
});

test("vòng thử-lại-tại-chỗ cũ phải biến mất", () => {
  // Nó chờ chết 2s+4s rồi vẫn `break`, bỏ luôn các tệp phía sau.
  assert.doesNotMatch(content, /MAX_ATTACH_ATTEMPTS/);
  assert.doesNotMatch(content, /sleep\(2000 \* attempt\)/);
});

test("báo lỗi theo TỪNG tệp, không nuốt phần còn lại", () => {
  assert.match(content, /for \(const \{ index \} of queue\)[\s\S]{0,220}?errors\.push\(message\)/);
});

test("chế độ tách hồ sơ vẫn dừng ngay khi ví React treo", () => {
  // Ví treo không chữa được bằng click lại; state machine cần nhận ngay để áp giới hạn reload.
  assert.match(content, /if \(splitMode && isSplitReloadableWalletError\(result\.code\)\)[\s\S]{0,90}?splitAbort = true/);
  assert.match(content, /queue\.length && !splitAbort/);
});

test("tạo được DÒNG chưa phải là đính xong", () => {
  // Tô xanh ngay lúc thêm dòng trống → bước đính sau hỏng mà dòng vẫn xanh, cán bộ tưởng đã xong.
  const addFn = content.slice(content.indexOf("async function addAttachmentComponent"));
  const body = addFn.slice(0, addFn.indexOf("\n  }\n"));
  assert.doesNotMatch(body, /markAttachmentResult\([^)]*true\)/);
});

test("chỉ tô xanh khi TÊN TỆP hiện thật trên dòng", () => {
  assert.match(content, /async function waitForPersistedAttachment/);
  assert.match(content, /const persisted = await waitForPersistedAttachment\(row, planItem, existingName\)/);
  assert.match(content, /if \(!persisted\)[\s\S]{0,360}?markAttachmentResult\(liveRow \|\| dialog, false\)/);
  assert.match(content, /markAttachmentResult\(persisted\.row, true\)/);
});

test("lý do thật của cổng phải lọt vào thông báo lỗi", () => {
  assert.match(content, /function readPortalUploadError\(\)/);
  assert.match(content, /that bai\|failed\|loi\|error\|500\|502\|503\|504/);
  assert.match(content, /portalError \? ` — cổng báo: \$\{portalError\}` : "\."/);
});
