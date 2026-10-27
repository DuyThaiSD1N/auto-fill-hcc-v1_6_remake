// Bước "Thông tin chủ hồ sơ" nhánh ỦY QUYỀN có MỘT bảng đính kèm riêng cho văn bản ủy quyền:
// header "Tên hồ sơ | Đính kèm | Hành động", đúng một dòng, nút cũng ghi "Chọn tệp đính kèm".
//
// Lỗi CÓ THẬT trước khi có file này: hasAttachmentTarget() chỉ cần thấy một nút "Chọn tệp
// đính kèm" ở bất kỳ đâu là báo đang ở bước đính kèm → bot bỏ qua cả bước chủ hồ sơ, và
// findAttachmentCandidateRows() (quét MỌI <tr> trong trang) coi dòng ủy quyền là thành phần
// hồ sơ, tức có thể đính giấy tờ cần chứng thực vào đúng ô giấy ủy quyền.
//
// Đối chiếu HTML thật: "mẫu toàn trình/chứng thực bs/trường hợp uỷ quyền.html" (bước 1) và
// "…/đính kèm.html" (bước 3).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const read = (...p) => fs.readFileSync(path.join(root, ...p), "utf8");
const attachCore = read("content", "attach-core.js");
const content = read("content.js");
const portalDvc = read("content", "portal-dvc.js");
const guided = read("content", "guided-steps.js");
const sidebar = read("sidebar.js");

test("dòng đính kèm văn bản ủy quyền bị loại khỏi danh sách thành phần hồ sơ", () => {
  const fn = attachCore.match(/function findAttachmentCandidateRows\(\)[\s\S]*?\n\}/);
  assert.ok(fn, "thiếu findAttachmentCandidateRows");
  assert.match(fn[0], /isAuthorizationAttachmentRow\(row\)/);
});

test("một nút 'Chọn tệp đính kèm' lạc không còn đủ để kết luận đang ở bước đính kèm", () => {
  const fn = attachCore.match(/function hasAttachmentTarget\(\)[\s\S]*?\n\}/);
  assert.ok(fn, "thiếu hasAttachmentTarget");
  assert.match(fn[0], /isAuthorizationAttachmentRow\(button\.closest\?\.\("tr"\)\)/);
});

test("nhận diện bảng ủy quyền bằng chữ của chính dòng, không dựa vào việc có <table>", () => {
  // Cả hai trang đều có <table> và đều có chữ "Đính kèm" → chỉ hai thứ đó là nhận nhầm.
  assert.match(attachCore, /const AUTHORIZATION_ROW_MARKERS = \[[^\]]*"tai lieu uy quyen"/);
  const fn = attachCore.match(/function isAuthorizationAttachmentRow\(row\)[\s\S]*?\n\}/);
  assert.ok(fn, "thiếu isAuthorizationAttachmentRow");
  // Lớp dự phòng theo header: bảng ủy quyền là "Tên hồ sơ/Hành động", bảng thành phần hồ sơ
  // là "Tên thành phần hồ sơ/Thao Tác" — chỉ loại khi CHẮC CHẮN không phải bảng kia.
  assert.match(fn[0], /head\.includes\("ten ho so"\)/);
  assert.match(fn[0], /!head\.includes\("thanh phan ho so"\)/);
});

test("dòng ủy quyền cũng không được nhận là dòng chứng thực bản sao", () => {
  const fn = attachCore.match(/function findCopyCertificationAttachmentRow\(\)[\s\S]*?\n\}/);
  assert.ok(fn, "thiếu findCopyCertificationAttachmentRow");
  assert.match(fn[0], /isAuthorizationAttachmentRow\(row\) \? null : row/);
});

test("báo cờ trang ủy quyền lên backend", () => {
  assert.match(attachCore, /hasAuthorizationAttachmentBlock/);
  assert.match(content, /authorizationBlock: !!\(/);
  assert.match(sidebar, /authorizationBlock: !!c\.authorizationBlock/);
});

test("nút Bước tiếp theo của trang ủy quyền có id riêng, phải khai tường minh", () => {
  // Trang ủy quyền MẤT data-e2e="btn-next" và đổi id thành nop-thu-tuc-b-3-uy-quyen.
  assert.match(guided, /nop-thu-tuc-b-3-uy-quyen/);
});

test("đếm ô bắt buộc còn trống để backend quyết định có quét giấy tờ ngay không", () => {
  const fn = portalDvc.match(/function ownerFormRequiredState\(\)[\s\S]*?\n  \}/);
  assert.ok(fn, "thiếu ownerFormRequiredState");
  // Dấu * đọc từ CHÍNH trang: ô "Địa chỉ chi tiết" có * ở nhánh tự làm nhưng KHÔNG có ở
  // nhánh ủy quyền — khai cứng ở backend là đòi sai ô.
  assert.match(fn[0], /\/\\\*\/\.test/);
  // react-select chỉ dựng singleValue khi đã chọn; input của nó luôn rỗng.
  assert.match(fn[0], /singleValue/);
  assert.match(content, /ownerFormRequiredState/);
  assert.match(sidebar, /ownerForm: c\.ownerForm \|\| null/);
});

test("đọc ô chủ hồ sơ trả kèm việc ô đó có bắt buộc hay không", () => {
  const fn = portalDvc.match(/function readOwnerFields\(fields\)[\s\S]*?\n  \}/);
  assert.ok(fn, "thiếu readOwnerFields");
  assert.match(fn[0], /required: fieldMarkedRequired\(field\)/);
});

test("khai capability để backend biết client hiểu luồng quét sớm", () => {
  const block = sidebar.match(/const CLIENT_CAPABILITIES = Object\.freeze\(\{([\s\S]*?)\}\);/);
  assert.ok(block, "không tìm thấy CLIENT_CAPABILITIES");
  assert.match(block[1], /supportsOwnerScan:\s*true/);
});

test("đọc tên tệp đã đính theo ĐÚNG cột của từng bảng", () => {
  // Sự cố 22/09/2026: đính xong, trang đã hiện tên tệp, nhưng bot vẫn báo "cổng chưa ghi
  // nhận". Bảng thành phần hồ sơ có 5 cột (tệp ở cột 3), bảng giấy ủy quyền chỉ có 3 cột
  // (tệp ở cột 2) — đọc cứng cột 3 là trúng cột Hành động, bỏ nút view/delete đi thì còn rỗng.
  const fn = attachCore.match(/function attachmentFileCell\(row\)[\s\S]*?\n\}/);
  assert.ok(fn, "thiếu attachmentFileCell");
  assert.match(fn[0], /isAuthorizationAttachmentRow\(row\)/);
  assert.match(fn[0], /cells\[1\]/);
  // Bộ đọc tên tệp phải đi qua hàm trên, không được tự chỉ định cột.
  const reader = attachCore.match(/function rowAttachedFileName\(row\)[\s\S]*?\n\}/);
  assert.match(reader[0], /attachmentFileCell\(row\)/);
  assert.doesNotMatch(reader[0], /cells\[\d\]/);
});

test("dòng giấy ủy quyền đã có tệp thì không đính đè", () => {
  // Cổng đổi tên tệp khi lưu (bỏ dấu) nên so tên để quyết định đính lại là dễ ra hai bản.
  const fn = attachCore.match(/async function attachAuthorizationFile\(payloadFile\)[\s\S]*?\n\}/);
  assert.ok(fn, "thiếu attachAuthorizationFile");
  assert.match(fn[0], /const existing = rowAttachedFileName\(row\)/);
  assert.match(fn[0], /skipped: true/);
  // KHÔNG truyền componentName: dòng này cố tình không có trong danh sách thành phần hồ sơ,
  // nên bộ dò theo tên sẽ không tìm ra nếu dòng bị dựng lại.
  const code = fn[0].replace(/\/\/.*/g, ""); // chú thích có nhắc componentName để giải thích
  assert.doesNotMatch(code, /componentName/);
});
