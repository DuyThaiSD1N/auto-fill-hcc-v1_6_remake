// Chọn đúng nhân thân người nộp khi hồ sơ có NHIỀU bản của cùng một người (giấy ủy quyền + CCCD) và
// OCR sai họ tên ở một trong hai. Trọng tài là TÊN TÀI KHOẢN đang đăng nhập trên cổng.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ids = new Map();
const warnings = [];
const sandbox = {
  console: { log() {}, warn: (...args) => warnings.push(args.join(" ")), error() {} },
  Event,
  MouseEvent: class {},
  setTimeout,
  clearTimeout,
  CSS: { escape: (value) => String(value) },
  getComputedStyle: () => ({ display: "block", visibility: "visible" }),
  chrome: { storage: { local: { get() {}, set() {}, remove() {} } }, runtime: {} },
  document: {
    getElementById: (id) => ids.get(id) || null,
    querySelector: () => null,
    querySelectorAll: () => [],
    forms: { namedItem: () => null },
  },
};
sandbox.window = {
  location: { pathname: "/HkdOnline/Forms/APP/Registration.aspx" },
  sessionStorage: { getItem: () => null, setItem() {}, removeItem() {} },
  __HCC__: {
    sleep: async () => {},
    norm: (value) => String(value || "").trim().toLowerCase().replace(/\s+/g, " "),
    fieldCandidates: () => [],
    setNativeValue: () => {},
    waitFor: async () => true,
    readAcctContact: () => "",
    fillFormStandard: async () => {},
    findStandardInput: () => null,
    findStandardSelect: () => null,
    isPostbackAddressField: () => false,
  },
  addEventListener() {},
};

vm.runInNewContext(
  fs.readFileSync(path.join(__dirname, "..", "content", "procedures", "business-registration.js"), "utf8"),
  sandbox,
  { filename: "business-registration.js" },
);
const { buildSubmitterOverride, matchSubmitterIdentityCandidate, submitterAddressFields }
  = sandbox.window.__HCC__;

const ID = "040203015844";
const CARD = { hoTen: "Vũ Đình Thiết", soDinhDanh: ID, ngaySinh: "26/04/2003", gioiTinh: "M",
  diaChi: { quocGia: "Việt Nam", tinh: "Nghệ An", xa: "Tam Hợp", diaChi: "Xóm Long Thành" } };
// Bản dựng từ Giấy ủy quyền: OCR sai dấu tên, thiếu ngày sinh/giới tính/địa chỉ.
const LETTER_BAD_NAME = { hoTen: "Vũ Đình Thiếp", soDinhDanh: ID, ngaySinh: "", gioiTinh: "", diaChi: null };

/** Giả lập cổng sau khi bấm "Sao chép thông tin đăng ký tài khoản". */
function withAccount(hoTen, soDinhDanh) {
  ids.clear();
  ids.set("ctl00_C_PERSCtl_FULL_NAMEFld", { value: hoTen });
  ids.set("ctl00_C_PERSCtl_PERS_DOC_NOFld", { value: soDinhDanh });
}
const stWith = (candidates) => ({ pages: { "nguoi-nop-ho-so": [
  { name: "__identityCandidates", value: candidates },
] } });

// 1. Giấy ủy quyền đứng ĐẦU nhưng sai tên; thẻ đúng tên tài khoản → phải chọn bản của THẺ.
withAccount("Vũ Đình Thiết", ID);
let out = buildSubmitterOverride(stWith([LETTER_BAD_NAME, CARD]), []);
assert.equal(out.hoTen, "Vũ Đình Thiết", "phải chọn bản khớp tên tài khoản");
assert.equal(out.ngaySinh, "26/04/2003", "kèm theo ngày sinh của bản đó");
assert.equal(out.diaChi.xa, "Tam Hợp");

// 2. Ngược lại: thẻ sai tên, giấy ủy quyền đúng tên tài khoản → chọn bản của GIẤY.
withAccount("Vũ Đình Thiết", ID);
out = buildSubmitterOverride(stWith([
  { ...CARD, hoTen: "Vũ Đình Thiếp" },
  { ...LETTER_BAD_NAME, hoTen: "Vũ Đình Thiết" },
], []), []);
assert.equal(out.hoTen, "Vũ Đình Thiết");

// 3. CẢ HAI bản đều sai tên → không bản nào khớp; ghi TÊN TÀI KHOẢN, vẫn lấy phần còn lại từ hồ sơ.
warnings.length = 0;
withAccount("Vũ Đình Thiết", ID);
out = buildSubmitterOverride(stWith([LETTER_BAD_NAME, { ...CARD, hoTen: "Trần Văn X" }]), []);
assert.equal(out.hoTen, "Vũ Đình Thiết", "không ghi tên OCR sai vào khối người nộp");
assert.equal(out.soDinhDanh, ID);
assert.equal(out.ngaySinh, "26/04/2003", "vẫn giữ ngày sinh đọc được từ hồ sơ");
assert.ok(warnings.some((w) => w.includes("LỆCH TÊN")), "phải cảnh báo lệch tên khi chọn bản");
assert.ok(warnings.some((w) => w.includes("ghi theo tài khoản")), "phải báo đã ghi theo tài khoản");

// 3b. Sai DẤU thôi (phép so tên bỏ dấu nên vẫn coi là khớp) → vẫn phải ghi đúng dấu của tài khoản.
warnings.length = 0;
withAccount("Vũ Đình Thiết", ID);
out = buildSubmitterOverride(stWith([{ ...CARD, hoTen: "Vũ Đình Thiệt" }]), []);
assert.equal(out.hoTen, "Vũ Đình Thiết", "sai dấu cũng không được ghi vào form");
assert.equal(warnings.length, 0, "sai dấu không coi là lệch tên nên không cảnh báo");

// 4. Chỉ một bản, tên khớp → giữ nguyên, không cảnh báo thừa.
warnings.length = 0;
withAccount("Vũ Đình Thiết", ID);
out = buildSubmitterOverride(stWith([CARD]), []);
assert.equal(out.hoTen, "Vũ Đình Thiết");
assert.equal(warnings.length, 0, "khớp sạch thì không cảnh báo");

// 5. Số định danh KHÔNG khớp tài khoản → không lấy bừa ai (hành vi cũ phải giữ).
withAccount("Trần Thị B", "099999999999");
assert.equal(buildSubmitterOverride(stWith([CARD, LETTER_BAD_NAME]), []), null);

// 6. Tài khoản chưa sao chép (form trống) → không đoán.
ids.clear();
assert.equal(buildSubmitterOverride(stWith([CARD]), []), null);

// 7. Khớp theo TÊN khi tài khoản không có số định danh trên form.
withAccount("Vũ Đình Thiết", "");
out = buildSubmitterOverride(stWith([LETTER_BAD_NAME, CARD]), []);
assert.equal(out.soDinhDanh, ID);
assert.equal(out.ngaySinh, "26/04/2003");

// === Ngoại lệ Đà Nẵng ===
// Nhánh Đà Nẵng ép tick "Người có thẩm quyền ký" và KHÔNG gọi buildSubmitterOverride (submitterOverride
// để null) → nhân thân giữ nguyên dữ liệu nút "Sao chép tài khoản", tên tài khoản không bao giờ bị OCR
// đè. Nó chỉ dùng matchSubmitterIdentityCandidate để lấy ĐỊA CHỈ của chính người đăng nhập.

// 8. Giấy ủy quyền sai tên + không có địa chỉ, thẻ đúng tên + có địa chỉ → phải lấy địa chỉ của THẺ.
withAccount("Vũ Đình Thiết", ID);
const stDaNang = { pages: { "nguoi-nop-ho-so": [
  { name: "__identityCandidates", value: [LETTER_BAD_NAME, CARD] },
  { name: "__applicantAddress", value: { role: "authorized", self: null } },
] } };
const card = matchSubmitterIdentityCandidate(stDaNang, []);
assert.equal(card.hoTen, "Vũ Đình Thiết", "chọn bản khớp tên tài khoản");
const addr = submitterAddressFields(stDaNang, stDaNang.pages["nguoi-nop-ho-so"], [], card, false);
const addrValue = (suffix) => (addr.find((f) => f.name.endsWith(suffix)) || {}).value;
assert.equal(addrValue("WARD_IDFld"), "Tam Hợp", "địa chỉ phải lấy trên CCCD của người đăng nhập");
assert.equal(addrValue("STREET_NUMBERFld"), "Xóm Long Thành");

// 9. Cả hai bản sai tên → gộp, vẫn còn địa chỉ để điền (trước đây lấy bản đầu là mất trắng).
withAccount("Vũ Đình Thiết", ID);
const merged = matchSubmitterIdentityCandidate({ pages: { "nguoi-nop-ho-so": [
  { name: "__identityCandidates", value: [LETTER_BAD_NAME, { ...CARD, hoTen: "Trần Văn X" }] },
] } }, []);
assert.equal(merged.soDinhDanh, ID);
assert.equal(merged.diaChi.xa, "Tam Hợp", "gộp nên không mất địa chỉ");

console.log("business-submitter-name-match: OK");
