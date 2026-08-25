// Trang "Thông tin về chủ hộ kinh doanh": KHÔNG bấm "Sao chép thông tin đăng ký tài khoản",
// nhân thân + liên hệ chủ hộ điền thẳng từ giấy đề nghị (dữ liệu backend).
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

// core.autocrlf=true nên working tree là CRLF; chuẩn hóa để mốc cắt nhiều dòng khớp ổn định.
const source = fs.readFileSync(
  path.join(__dirname, "..", "content", "procedures", "business-registration.js"), "utf8"
).replace(/\r\n/g, "\n");

// --- 1. Không còn dấu vết bước sao chép cho trang chủ hộ ---
assert.doesNotMatch(
  source,
  /OWN_PCtl\$btnIS_SIGNER|OWN_PCtl_btnIS_SIGNER/,
  "Không được còn tham chiếu nút Sao chép tài khoản của trang chủ hộ",
);
const cfgStart = source.indexOf("const COPY_PERSON_CFG = {");
const cfgEnd = source.indexOf("\n  };", cfgStart);
assert.ok(cfgStart >= 0 && cfgEnd > cfgStart, "Không tách được COPY_PERSON_CFG");
assert.doesNotMatch(
  source.slice(cfgStart, cfgEnd),
  /"chu-ho-kinh-doanh"/,
  "Trang chủ hộ không còn thuộc nhóm trang dùng nút sao chép",
);
assert.match(
  source,
  /if \(targetKey === "chu-ho-kinh-doanh"\) \{\s*\n\s*return void handleOwnerPage\(st\);/,
  "stepFillAll phải định tuyến trang chủ hộ sang handleOwnerPage",
);
// Trang người nộp VẪN phải copy: khối đó mang nhân thân của chính tài khoản đang đăng nhập.
assert.match(source, /copyBtn: 'input\[name="ctl00\$C\$btnIS_SIGNER"\]/);
assert.match(source, /if \(targetKey === "nguoi-nop-ho-so"\) \{\s*\n\s*return void handleCopyPersonPage\(st, targetKey\);/);

// --- 2. applyOwnerFromDossier: điền/xóa/mở khóa đúng ---
const start = source.indexOf("  const OWNER_PERSON_FIELDS = [");
const end = source.indexOf("\n  /**\n   * Trang \"Thông tin về chủ hộ kinh doanh\"", start);
assert.ok(start >= 0 && end > start, "Không tách được applyOwnerFromDossier");

const elements = new Map();
function makeInput(id, { value = "", disabled = false, readOnly = false } = {}) {
  const el = { id, value, disabled, readOnly };
  elements.set(id, el);
  return el;
}

const genderCalls = [];
const sandbox = {
  document: { getElementById: (id) => elements.get(id) || null },
  norm: (v) => String(v == null ? "" : v).trim().toLowerCase(),
  setNativeValue: (el, value) => { el.value = String(value ?? ""); },
  setGenderRadio: (name, value) => { genderCalls.push([name, value]); },
};
vm.runInNewContext(`${source.slice(start, end)}\nglobalThis.applyOwner = applyOwnerFromDossier;`, sandbox);

const P = "ctl00_C_OWN_PCtl_PERSCtl_";
const name = makeInput(P + "FULL_NAMEFld", { disabled: true });       // cổng khóa ô này trước khi copy
const dob = makeInput(P + "DATE_OF_BIRTHFld");
const doc = makeInput(P + "PERS_DOC_NOFld", { readOnly: true });
const phone = makeInput(P + "PHONEFld");
const fax = makeInput(P + "FAXFld", { value: "RÁC CŨ" });             // đơn không kê khai → phải xóa
const email = makeInput(P + "EMAILFld");
const url = makeInput(P + "URLFld");

const N = "ctl00$C$OWN_PCtl$PERSCtl$";
sandbox.applyOwner([
  { name: N + "FULL_NAMEFld", value: "Nguyễn Văn An" },
  { name: N + "GENDER_IDFld", value: "M" },
  { name: N + "DATE_OF_BIRTHFld", value: "05/03/1990" },
  { name: N + "PERS_DOC_NOFld", value: "024090001234" },
  { name: N + "PHONEFld", value: "0912345678" },
  { name: N + "EMAILFld", value: "an@example.com" },
  { name: N + "URLFld", value: "example.com" },
]);

assert.equal(name.value, "Nguyễn Văn An");
assert.equal(dob.value, "05/03/1990");
assert.equal(doc.value, "024090001234");
assert.equal(phone.value, "0912345678");
assert.equal(email.value, "an@example.com");
assert.equal(url.value, "example.com", "Website phải được điền (trước đây rơi giữa hai bước)");
assert.equal(fax.value, "", "Ô đơn không kê khai phải được xóa, không giữ giá trị lạ");

// Input disabled/readonly không được trình duyệt submit → phải mở khóa trước khi ghi.
assert.equal(name.disabled, false, "Phải bỏ disabled trước khi ghi họ tên");
assert.equal(doc.readOnly, false, "Phải bỏ readonly trước khi ghi số định danh");

assert.deepEqual(genderCalls, [["ctl00$C$OWN_PCtl$PERSCtl$GENDER_IDFld", "M"]]);

// --- 3. Đơn không có giới tính → gọi với chuỗi rỗng (setGenderRadio tự bỏ qua), không đoán bừa ---
genderCalls.length = 0;
sandbox.applyOwner([{ name: N + "FULL_NAMEFld", value: "Trần Thị Bình" }]);
assert.deepEqual(genderCalls, [["ctl00$C$OWN_PCtl$PERSCtl$GENDER_IDFld", ""]]);
assert.equal(name.value, "Trần Thị Bình");

console.log("business owner page: no account-copy, fill from dossier only — passed");
