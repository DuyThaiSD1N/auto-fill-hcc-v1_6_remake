// Ô "Đi đến thủ tục" tra được bằng MÃ TTHC in trên giấy, không chỉ bằng tên dài.
// Mã do backend khai ở app/procedures/data/ke_khai_links.json, popup gắn vào <option data-code>.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "popup.js"), "utf8");

const normStart = source.indexOf("function normalizeProcedureSearch(value)");
const normEnd = source.indexOf("\nconst XUAN_HUONG_BUSINESS_ACT_TEXT", normStart);
const listStart = source.indexOf("  function renderList(query) {");
const listEnd = source.indexOf("\n  function open() {", listStart);
assert.ok(normStart >= 0 && normEnd > normStart, "Không tách được normalizeProcedureSearch");
assert.ok(listStart >= 0 && listEnd > listStart, "Không tách được renderList");

// <option> giả lập: đúng hai thứ renderList đọc — textContent và dataset.code.
const OPTIONS = [
  { value: "", textContent: "-- Chọn thủ tục --", dataset: {} },
  { value: "chung-thuc-ban-sao", textContent: "Chứng thực bản sao từ bản chính giấy tờ, văn bản", dataset: { code: "2.000815" } },
  { value: "khai-sinh-dang-ky", textContent: "Liên thông đăng ký khai sinh, thường trú, BHYT cho trẻ dưới 6 tuổi", dataset: { code: "2.000986" } },
  { value: "xet-tuyen-cong-chuc", textContent: "Thủ tục xét tuyển Công chức", dataset: { code: "1.014113" } },
  { value: "thi-tuyen-cong-chuc", textContent: "Thủ tục thi tuyển Công chức", dataset: { code: "1.014111" } },
  // Chưa tra được mã — phải tìm được bằng tên và KHÔNG bị bịa mã.
  { value: "ket-hon-nuoc-ngoai", textContent: "Thủ tục đăng ký kết hôn có yếu tố nước ngoài", dataset: {} },
];

// DOM tối thiểu cho renderList: list.innerHTML, createElement, appendChild.
function fakeEl() {
  return {
    className: "", type: "", textContent: "", dataset: {}, children: [],
    setAttribute() {}, addEventListener() {},
    appendChild(c) { this.children.push(c); return c; },
  };
}
const rendered = [];
const sandbox = {
  document: {
    createElement: () => fakeEl(),
    createTextNode: (t) => ({ nodeValue: t }),
  },
  list: {
    set innerHTML(_v) { rendered.length = 0; },
    appendChild(node) { rendered.push(node); return node; },
  },
  options: () => OPTIONS.filter((o) => o.value !== ""),
  select: { value: "" },
};

vm.runInNewContext(`
  ${source.slice(normStart, normEnd)}
  ${source.slice(listStart, listEnd)}
  globalThis.run = (q) => { renderList(q); return null; };
`, sandbox);

// Mã KHÔNG hiện thành dòng riêng nữa (chỉ nằm ở data-code + tooltip), nên nhận diện kết quả
// bằng chính tên thủ tục hiển thị.
const find = (q) => {
  rendered.length = 0;
  sandbox.run(q);
  // renderList append 1 phần tử "Không tìm thấy" khi rỗng → nhận ra bằng className.
  if (rendered.length === 1 && rendered[0].className === "combo-empty") return [];
  return rendered.map((item) => item.textContent);
};

// Tra bằng mã đầy đủ đúng như in trên giấy.
assert.deepEqual(find("2.000815"), ["Chứng thực bản sao từ bản chính giấy tờ, văn bản"], "Mã đầy đủ");
assert.deepEqual(find("1.014113"), ["Thủ tục xét tuyển Công chức"], "Mã xét tuyển công chức");

// Gõ thiếu/thừa dấu chấm — cán bộ nhập nhanh trên bàn phím số.
assert.deepEqual(find("2000815"), ["Chứng thực bản sao từ bản chính giấy tờ, văn bản"], "Mã không dấu chấm");
assert.deepEqual(find("2.000.815"), ["Chứng thực bản sao từ bản chính giấy tờ, văn bản"], "Mã thừa dấu chấm");

// Hai mã chỉ khác chữ số cuối phải ra đúng một kết quả.
assert.deepEqual(find("1014111"), ["Thủ tục thi tuyển Công chức"], "1.014111 không lẫn với 1.014113");

// Tìm theo tên vẫn nguyên như cũ, kể cả thủ tục chưa có mã.
assert.equal(find("khai sinh").length, 1, "Tìm theo tên không dấu");
assert.deepEqual(find("yếu tố nước ngoài"), ["Thủ tục đăng ký kết hôn có yếu tố nước ngoài"], "Thủ tục chưa có mã vẫn tìm được bằng tên");

// Một chữ số lẻ trong tên KHÔNG được kéo cả rổ thủ tục về theo đường khớp mã.
// "Công chức"/"công chức" không chứa "2" nên chỉ các mã chứa 2 mới dính nếu luật sai.
assert.deepEqual(find("2"), [], "Một chữ số không đủ để coi là mã");
assert.deepEqual(find("999999"), [], "Mã không tồn tại");

// Không gõ gì → hiện toàn bộ danh sách.
assert.equal(find("").length, OPTIONS.length - 1, "Chưa gõ thì liệt kê hết");

// Mã không hiện thành dòng riêng, nhưng vẫn phải tra được qua tooltip khi rê chuột.
rendered.length = 0;
sandbox.run("2.000815");
assert.equal(rendered[0].title, "2.000815 — Chứng thực bản sao từ bản chính giấy tờ, văn bản",
  "Tooltip giữ lại mã để đối chiếu");
assert.equal(rendered[0].children.length, 0, "Không còn phần tử con nào chứa mã");

rendered.length = 0;
sandbox.run("yếu tố nước ngoài");
assert.equal(rendered[0].title, undefined, "Thủ tục chưa có mã thì không gán tooltip mã");

console.log("ke khai search by code: passed");
