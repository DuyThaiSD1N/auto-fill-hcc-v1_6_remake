const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const portal = fs.readFileSync(path.join(root, "content/portal-dvc.js"), "utf8");
const content = fs.readFileSync(path.join(root, "content.js"), "utf8");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");

test("đọc đủ context chủ hồ sơ theo nhãn, không theo class động", () => {
  for (const label of ["Họ và tên", "Số giấy tờ", "Ngày tháng năm sinh", "Giới tính", "Quốc tịch", "Loại giấy tờ", "Địa chỉ chi tiết"]) {
    assert.match(portal, new RegExp(JSON.stringify(label).slice(1, -1)));
  }
  assert.match(portal, /h1,h2,h3,h4,p,label,span,div/);
  assert.match(content, /ownerContext/);
  assert.match(sidebar, /ownerContext: c\.ownerContext \|\| null/);
  assert.match(sidebar, /action: "getOwnerContext"/);
  assert.match(portal, /msg\?\.action !== "getOwnerContext"/);
});

test("backend điều khiển field plan, extension chỉ dùng component generic", () => {
  assert.match(portal, /owner-combobox/);
  assert.match(portal, /msg\?\.action !== "fillOwnerFields"/);
  assert.match(sidebar, /a\.type === "fill_owner_fields"/);
  assert.doesNotMatch(portal, /ket-hon|ket_hon|CccdNam|CccdNu/);
});

test("không ghi đè input đã có và watcher tự theo dõi bước kế tiếp", () => {
  assert.match(portal, /control\.value[\s\S]*field\.overwrite !== true/);
  assert.match(sidebar, /"owner_waiting_next"/);
  assert.match(sidebar, /d\.type === "owner_fields_ready"/);
  assert.match(sidebar, /Không tìm thấy frame chứa các ô Thông tin chủ hồ sơ/);
  assert.match(portal, /fields\.filter\(\(field\) => fieldControl\(field\)\.control\)/);
});

test("selector ổn định cho điện thoại và địa chỉ do backend gửi name", () => {
  assert.match(portal, /field\.name/);
  assert.match(portal, /CSS\.escape/);
  assert.doesNotMatch(portal, /react-select-2-input|self-email-field/);
});

test("ngày cấp và nơi cấp nhận label có span dấu bắt buộc", () => {
  assert.match(portal, /function normalizedOwnerFieldLabel/);
  assert.match(portal, /replace\(\/\\s\*\\\*\+\\s\*\$\/, ""\)/);
  assert.match(portal, /querySelectorAll\("label"\)/);
  assert.match(portal, /matchesOwnerFieldLabel\(element, wanted, section, true\)/);
  assert.match(portal, /querySelectorAll\("p,span,div"\)/);
});

test("field ủy quyền được giới hạn trong đúng section và ưu tiên selector backend", () => {
  assert.match(portal, /field\.sectionLabel/);
  assert.match(portal, /ownerFieldSection\(field\)/);
  assert.match(portal, /isAfterSectionAnchor/);
  assert.match(portal, /field\.dataE2e/);
  assert.match(portal, /data-e2e=/);
  assert.match(portal, /không được fallback ra toàn trang/);
  assert.doesNotMatch(portal, /other-fullName-field|other-relationship-field|other-numberOfDocument-field/);
});

test("owner engine dùng fill-core để React nhận value và tô xanh đỏ", () => {
  assert.match(portal, /H\.setNativeValue/);
  assert.match(portal, /H\.injectAutofillStyles/);
  assert.match(portal, /H\.clearAutofillMarks/);
  assert.match(portal, /H\.markFilled/);
  assert.match(portal, /H\.markUnfilled/);
});

test("đánh dấu wrapper ổn định sau khi React render lại ngày và nơi cấp", () => {
  assert.match(portal, /scope\?\.classList && scope\.isConnected/);
  assert.match(portal, /function markCurrentOwnerField/);
  assert.match(portal, /const current = fieldControl\(field\)/);
  assert.match(portal, /await sleep\(80\)/);
  assert.match(portal, /markCurrentOwnerField\(field, control, scope, true\)/);
});

test("nơi cấp là React Select nên phải mở menu và click option thật", () => {
  assert.match(portal, /openOwnerReactSelect\(input, control\)/);
  assert.match(portal, /new MouseEvent\("mousedown"/);
  assert.match(portal, /matchReactSelectOption/);
  assert.match(portal, /react-select-.*-option-/);
  assert.match(portal, /option\.click\(\)/);
  assert.match(portal, /Danh sách đang có/);
  assert.doesNotMatch(portal, /setNativeValue\(input, wanted/);
});

test("owner fill có trace xuyên sidebar và iframe để chẩn đoán cổng thật", () => {
  assert.match(portal, /\[TLND-OwnerFill\]/);
  assert.match(portal, /react-select:opened/);
  assert.match(portal, /react-select:option-click/);
  assert.match(portal, /message:accepted/);
  assert.match(portal, /message:skip-frame/);
  assert.match(sidebar, /\[TLND-OwnerFill\]\[sidebar\] send/);
  assert.match(sidebar, /traceId/);
});

test("owner fill trả tên trường để backend nói rõ mục đã xong và còn thiếu", () => {
  assert.match(portal, /const filledLabels = \[\]/);
  assert.match(portal, /const keptLabels = \[\]/);
  assert.match(portal, /filledLabels\.push\(label\)/);
  assert.match(portal, /keptLabels\.push\(label\)/);
  assert.match(sidebar, /filledLabels: res\?\.filledLabels \|\| \[\]/);
  assert.match(sidebar, /keptLabels: res\?\.keptLabels \|\| \[\]/);
});

test("pipeline chủ hồ sơ giữ 4 bước, còn kê khai chỉ hiện một dòng", () => {
  assert.match(sidebar, /const PIPE_STAGES = \[/);
  assert.match(sidebar, /showPipelineCard\("Em đang đọc và bóc tách giấy tờ[^\n]+true\)/);
  assert.match(sidebar, /Bóc tách thông tin và điền biểu mẫu/);
  assert.match(sidebar, /showPipelineCard\("Bóc tách thông tin và điền biểu mẫu", false\)/);
  for (const ownerLabel of [
    "Kiểm tra ảnh đã nhận",
    "Đọc chữ trên giấy tờ (OCR)",
    "Bóc tách và đối chiếu thông tin",
    "Chuẩn bị điền biểu mẫu",
  ]) {
    assert.match(sidebar, new RegExp(ownerLabel.replace(/[()]/g, "\\$&")));
  }
});

test("portal engine lấy nodeText từ fill-core, không gọi biến global chưa khai báo", () => {
  assert.match(portal, /const nodeText = typeof H\.nodeText === "function"/);
  assert.match(portal, /\? H\.nodeText/);
});

test("địa chỉ object chỉ lấy phần diaChi và không giữ literal object Object", () => {
  assert.match(portal, /value\.diaChi \|\| value\.dia_chi \|\| value\.diachi/);
  assert.match(portal, /normalized !== "\[object object\]"/);
});

test("date placeholder của khối ủy quyền không được coi là giá trị đã có", () => {
  assert.match(portal, /normalized !== "dd\/mm\/yyyy"/);
});

test("owner-date là input mask React nên phải mô phỏng gõ phím, không gán value", () => {
  // Nhánh riêng cho comp owner-date, KHÔNG dùng setReactValue (bị revert về dd/MM/yyyy).
  assert.match(portal, /field\.comp === "owner-date"[\s\S]*?fillOwnerDate\(control, field\.value\)/);
  assert.match(portal, /async function fillOwnerDate/);
  // Gõ phím thật qua KeyboardEvent, ép keyCode/which vì constructor bỏ qua (thiếu thì mask câm).
  assert.match(portal, /new KeyboardEvent\(type/);
  assert.match(portal, /Object\.defineProperty\(ev, "keyCode"/);
  assert.match(portal, /Object\.defineProperty\(ev, "which"/);
  // Ba điều bắt buộc: xoá sạch (Backspace) → về đầu (Home/ArrowLeft) → gõ ddMMyyyy có delay.
  assert.match(portal, /"Backspace"/);
  assert.match(portal, /"Home"/);
  assert.match(portal, /"ArrowLeft"/);
  // Chấp nhận cả dd/mm/yyyy lẫn ISO yyyy-mm-dd, trả ddMMyyyy 8 số.
  assert.match(portal, /function ownerDateDigits/);
  // Xác thực kết quả đúng dạng dd/mm/yyyy trước khi báo điền thành công.
  assert.match(portal, /\\d\{2\}\\\/\\d\{2\}\\\/\\d\{4\}/);
});
