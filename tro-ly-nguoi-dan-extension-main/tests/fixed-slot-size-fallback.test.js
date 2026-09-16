// Khai sinh liên thông: cổng chặn TỔNG dung lượng mỗi loại giấy tờ ("không được quá 2.6MB").
// Mọi giấy tờ khác đều dồn vào STT1 (giấy chứng sinh) nên hồ sơ nhiều tệp là vỡ hạn mức — trước
// đây input vẫn nhận file, cổng từ chối bằng toast, còn ta thì tô xanh và báo đã đính xong.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const attach = fs.readFileSync(path.join(__dirname, "..", "content", "attach-core.js"), "utf8");

test("đọc được lời cổng báo quá dung lượng", () => {
  // Câu này KHÔNG chứa "lỗi/thất bại/500" nên bộ lọc lỗi chung không bắt được → phải có hàm riêng.
  assert.match(attach, /function sizeLimitToastNodes\(\)/);
  assert.match(attach, /folded\.includes\("dung luong"\)/);
  assert.match(attach, /khong duoc qua\|vuot qua\|toi da\|khong vuot\|gioi han/);
});

test("thành công = tên tệp hiện thật (landed), KHÔNG phải vắng toast", () => {
  // Trước đây coi "không bắt được toast" là thành công → toast lỡ nhịp thành "thành công giả":
  // tệp không vào mà cũng không dời ô. Giờ tiêu chí là BẰNG CHỨNG DƯƠNG (landed).
  const fn = attach.slice(attach.indexOf("const tryMenuSlot = async"));
  const body = fn.slice(0, fn.indexOf("\n    };"));
  assert.match(body, /let landed = false, sizeError = "";/);
  assert.match(body, /const deadline = Date\.now\(\) \+ 7000;/);
  assert.match(body, /if \(!ok \|\| !landed\)[\s\S]{0,220}?markAttachmentResult\(markTarget, false\)/);
  // Chỉ tô xanh ở nhánh CUỐI, sau khi đã có bằng chứng dương.
  assert.match(body, /markAttachmentResult\(markTarget, true\);\s*\n\s*return \{ found: true, ok: true \}/);
  // Không còn coi "vắng toast" là đủ để kết luận thành công.
  assert.doesNotMatch(body, /const sizeError = \(ok && !landed\) \? await waitPortalSizeLimitError/);
});

test("landed = tên tệp hiện trong dòng, dò bằng POLL (không chờ chết)", () => {
  // Bằng chứng dương: cổng đã liệt kê tệp trong dòng = đã nhận. Poll tới hạn; toast size MỚI cắt sớm.
  const fn = attach.slice(attach.indexOf("const tryMenuSlot = async"));
  const body = fn.slice(0, fn.indexOf("\n    };"));
  assert.match(body, /menuSlotRowText\(trigger\)\.includes\(foldChoiceText\(name\)\)\)\) \{ landed = true; break; \}/);
  assert.match(body, /const t = newSizeLimitError\(toastsBefore\);/);
});

test("KHÔNG được đọc nhầm toast của lần thử trước", () => {
  // Lỗi thật đã gặp: tệp VÀO ĐƯỢC ô dự phòng nhưng toast của lần thử ô chính còn trên màn hình
  // → báo hỏng oan, và câu lỗi lặp y hệt hai lần.
  assert.match(attach, /function snapshotSizeLimitToasts\(\)/);
  assert.match(attach, /const toastsBefore = snapshotSizeLimitToasts\(\);/);
  assert.match(attach, /async function waitPortalSizeLimitError\(before = \[\], ms = 1200\)/);
  // "Mới" so theo NỘI DUNG, không theo node: thư viện toast React dựng lại node cho cùng một
  // lời than, so node là lại tưởng toast mới (đã làm hỏng đường toast lỗi tải tệp một lần rồi).
  assert.match(attach, /function newSizeLimitError\(before = \[\]\)/);
  assert.match(attach, /if \(!seen\.has\(foldChoiceText\(hit\.text\)\)\) return hit\.text;/);
});

test("ô chính KHÔNG nhận (size/đầy/…) thì DỜI sang ô dự phòng BE chỉ định", () => {
  // Trước chỉ dời khi bắt được toast size; giờ dời khi ô chính HỎNG bất kể lý do (miễn có fallback),
  // vì tệp đằng nào cũng không vào được ô chính — dời còn hơn bỏ sót. Thử lại chính ô cũ là vô nghĩa.
  assert.match(attach, /if \(item\.fallbackSlotKey \|\| Number\.isInteger\(item\.fallbackSlotIndex\)\)/);
  assert.match(attach, /slotKey: item\.fallbackSlotKey[\s\S]{0,120}?slotIndex: item\.fallbackSlotIndex/);
  // KHÔNG còn khoá theo riêng sizeError nữa.
  assert.doesNotMatch(attach, /if \(first\.sizeError && \(item\.fallbackSlotKey/);
});

test("ô dự phòng cũng không nhận thì báo RÕ tệp nào, kèm lý do cổng", () => {
  assert.match(attach, /Không đính được \$\{fileNames\.join\(", "\)\}/);
  assert.match(attach, /const reason = second\.sizeError \|\| first\.sizeError \|\| second\.error \|\| first\.error \|\| "cổng từ chối";/);
  assert.match(attach, /không nhận thêm — \$\{reason\}/);
});

test("ô chính hỏng mà KHÔNG có ô dự phòng → báo lỗi luôn, không lén dời", () => {
  assert.match(attach, /errors\.push\(first\.error\);\s*\n\s*continue;/);
});
