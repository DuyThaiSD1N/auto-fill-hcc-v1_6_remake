// Trang "Tên doanh nghiệp" (EnterpriseName.aspx) phải điền XONG TRONG MỘT LƯỢT.
//
// Dropdown tiền tố loại hình (ctl00$C$DROP_NAME_TYPE) có AutoPostBack: WebForms gắn __doPostBack vào
// thuộc tính `onchange`, nên vừa bắn `change` là cổng tải lại trang NGAY -- cuốn theo mấy ô tên vừa
// gõ LẪN lệnh ghi state, buộc lượt sau phải điền lại từ đầu. Đó là vòng "điền mấy lượt mới xong".
// Cách chữa: đặt giá trị dropdown mà KHÔNG bắn `change`; postback của nút Lưu gửi kèm giá trị đó.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.join(__dirname, "..", "content", "procedures", "enterprise-registration.js"), "utf8");

function slice(from, to) {
  const start = source.indexOf(from);
  const end = source.indexOf(to, start);
  assert.ok(start >= 0 && end > start, `Không cắt được đoạn "${from}"`);
  return source.slice(start, end);
}

// ---- Đặc tả trang phải khai đúng ô AutoPostBack ----
assert.match(source, /quietFields:\s*\["ctl00\$C\$DROP_NAME_TYPE"\]/,
  "Trang Tên doanh nghiệp phải khai dropdown tiền tố là ô không được bắn change");
assert.doesNotMatch(slice('"dia-chi": {', '"nganh-nghe-kinh-doanh"'), /quietFields/,
  "Trang Địa chỉ KHÔNG được khai quietFields: dropdown địa bàn cần postback để nạp xã/phường");

// ---- DOM giả: select AutoPostBack như cổng thật ----
const events = [];
let reloaded = false;

function makeSelect(name, optionTexts) {
  const options = optionTexts.map((t) => ({ value: t, textContent: t }));
  const el = {
    tagName: "SELECT", name, options, value: optionTexts[0], parentElement: null,
    getAttribute: (a) => (a === "onchange" ? "javascript:setTimeout('__doPostBack(...)',0)" : null),
    dispatchEvent(ev) {
      events.push(ev.type);
      // Cổng thật: `change` trên control AutoPostBack -> tải lại trang.
      if (ev.type === "change") reloaded = true;
      return true;
    },
  };
  el.parentElement = { el };
  return el;
}

const select = makeSelect("ctl00$C$DROP_NAME_TYPE",
  ["-- Chọn --", "CÔNG TY TNHH", "CÔNG TY TNHH MTV", "CÔNG TY CỔ PHẦN"]);

const filledByStandard = [];
const sandbox = {
  console: { warn() {}, log() {} },
  HTMLSelectElement: { prototype: {} },   // không có descriptor -> gán thẳng el.value
  Event: class { constructor(type) { this.type = type; } },
  document: {
    querySelector: (sel) => (sel.includes("DROP_NAME_TYPE") ? select : null),
  },
};
sandbox.H = {
  markFilled: () => {},
  fillFormStandard: async (fields) => { filledByStandard.push(...fields.map((f) => f.name)); },
};
sandbox.fold = (v) => String(v || "")
  .replace(/đ/g, "d").replace(/Đ/g, "D")
  .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
  .toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();

vm.runInNewContext(
  slice("  function fillSelectWithoutPostback(field)", "  /** Nút Lưu ĐANG BẬT")
  + "globalThis.fillPageFields = fillPageFields;"
  + "globalThis.fillSelectWithoutPostback = fillSelectWithoutPostback;",
  sandbox,
);

(async () => {
  const spec = { quietFields: ["ctl00$C$DROP_NAME_TYPE"] };
  const fields = [
    { name: "ctl00$C$DROP_NAME_TYPE", comp: "dom-select", value: "CÔNG TY TNHH" },
    { name: "ctl00$C$NAMEFld", comp: "dom-input", value: "DỊCH VỤ VẬN TẢI" },
    { name: "ctl00$C$SHORT_NAMEFld", comp: "dom-input", value: "DVVT" },
  ];
  await sandbox.fillPageFields(spec, fields);

  assert.equal(reloaded, false,
    "KHÔNG được bắn `change` lên dropdown AutoPostBack — đó chính là thứ tải lại trang giữa chừng");
  assert.ok(!events.includes("change"), `Sự kiện đã bắn: ${events.join(",")}`);
  assert.ok(events.includes("input"), "Vẫn phải bắn `input` để validator bật nút Lưu");
  assert.equal(select.value, "CÔNG TY TNHH", "Dropdown phải mang đúng giá trị để nút Lưu gửi đi");
  assert.deepEqual(filledByStandard, ["ctl00$C$NAMEFld", "ctl00$C$SHORT_NAMEFld"],
    "Các ô text vẫn đi đường fillFormStandard bình thường, chỉ tách riêng ô AutoPostBack");

  // Chạy lại lượt hai: giá trị đã đúng thì không đụng vào DOM nữa (không có sự kiện mới).
  const before = events.length;
  await sandbox.fillPageFields(spec, fields);
  assert.equal(events.length, before, "Giá trị đã đúng thì không bắn thêm sự kiện nào");

  // Giá trị không có trong danh sách option -> báo trượt, không gán bừa.
  assert.equal(
    sandbox.fillSelectWithoutPostback({ name: "ctl00$C$DROP_NAME_TYPE", value: "HỢP TÁC XÃ" }),
    false, "Không khớp option nào thì phải trả false, không gán bừa");

  console.log("enterprise name single pass: AutoPostBack dropdown set without reload passed");
})();
