const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../content/procedures/business-registration.js"), "utf8");

function slice(start, end) {
  const from = source.indexOf(start);
  const to = source.indexOf(end, from);
  assert.ok(from >= 0 && to > from, `không tìm thấy ${start}`);
  return source.slice(from, to);
}

// Chạy thật các hàm đối chiếu chủ hộ ↔ tài khoản trên DOM giả.
function load(dom) {
  const code = [
    slice("function foldBusinessPageText", "const BUSINESS_PAGE_LABELS"),
    slice("const ownerFieldValue", "/**\n   * Chủ hộ là người đang đăng nhập"),
    "function readPersonControlRaw(id) { return (dom[id] || {}).value || ''; }",
    "({ ownerMatchesAccount, ownerCopiedFromAccount, copiedOwnerConflicts })",
  ].join("\n");
  const norm = (v) => String(v || "").normalize("NFC").replace(/\s+/g, " ").trim().toLowerCase();
  return vm.runInNewContext(code, {
    norm, dom, document: { getElementById: (id) => dom[id] || null },
  });
}

const HEADER = "ctl00_LV2_LblFullNameValue";
const NAME = "ctl00_C_OWN_PCtl_PERSCtl_FULL_NAMEFld";
const DOB = "ctl00_C_OWN_PCtl_PERSCtl_DATE_OF_BIRTHFld";
const ID = "ctl00_C_OWN_PCtl_PERSCtl_PERS_DOC_NOFld";
const P = "ctl00$C$OWN_PCtl$PERSCtl$";

function dossier({ name = "Nguyễn Văn A", dob = "01/02/1990", id = "" } = {}) {
  return [
    { name: `${P}FULL_NAMEFld`, value: name },
    { name: `${P}DATE_OF_BIRTHFld`, value: dob },
    { name: `${P}PERS_DOC_NOFld`, value: id },
  ];
}

test("chủ hộ trùng tên tài khoản trên header (bỏ dấu, hoa thường) thì sao chép", () => {
  const f = load({ [HEADER]: { textContent: "  NGUYỄN VĂN A " } });
  assert.equal(f.ownerMatchesAccount(dossier()), true);
  assert.equal(f.ownerMatchesAccount(dossier({ name: "Nguyễn Văn B" })), false);
  assert.equal(load({}).ownerMatchesAccount(dossier()), false, "không có header thì giữ luồng cũ");
});

test("chỉ coi là đã sao chép khi ô họ tên = tài khoản và có số định danh", () => {
  const dom = { [HEADER]: { textContent: "NGUYỄN VĂN A" }, [NAME]: { value: "NGUYỄN VĂN A" }, [ID]: { value: "" } };
  const f = load(dom);
  assert.equal(f.ownerCopiedFromAccount(), false);
  dom[ID].value = "001090000001";
  assert.equal(f.ownerCopiedFromAccount(), true);
});

test("trùng tên khác người: ngày sinh hoặc số định danh đủ 12 số khác dữ liệu sao chép", () => {
  const f = load({ [DOB]: { value: "01/02/1990" }, [ID]: { value: "001090000001" } });
  assert.equal(f.copiedOwnerConflicts(dossier()), false);
  assert.equal(f.copiedOwnerConflicts(dossier({ dob: "03/04/1991" })), true);
  assert.equal(f.copiedOwnerConflicts(dossier({ id: "001090000002" })), true);
  // Đơn viết thừa/thiếu số → không dùng để so, vẫn lấy số của tài khoản.
  assert.equal(f.copiedOwnerConflicts(dossier({ id: "0010900000012" })), false);
  assert.equal(f.copiedOwnerConflicts(dossier({ dob: "", id: "" })), false);
});

test("trang chủ hộ: sao chép xong không ghi đè nhân thân, chỉ liên hệ đơn có ghi", () => {
  const handler = slice("async function handleOwnerPage", "async function handleCopyPersonPage");
  assert.match(handler, /const fromAccount = await copyOwnerFromAccount\(st, fields\)/);
  assert.match(handler, /if \(fromAccount === "wait"\) return;/);
  assert.equal((handler.match(/applyOwnerFromDossier\(fields, fromAccount\)/g) || []).length, 2);
  assert.match(source, /if \(fromAccount && OWNER_IDENTITY_RE\.test\(id \|\| radioName\)\) continue;/);
  assert.match(source, /if \(fromAccount && !value\.trim\(\)\) continue;/);
  const copy = slice("async function copyOwnerFromAccount", "/**\n   * Trang \"Thông tin về chủ hộ kinh doanh\"");
  assert.match(copy, /\$C\$OWN_PCtl\$btnIS_SIGNER/);
  assert.match(copy, /st\.ownerCopyTries \|\| 0\) >= 3/);
});
