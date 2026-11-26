// Ô mô tả từng dòng ngành nghề hộ kinh doanh: BE quyết chữ ghi (khoá "detail"), extension chỉ ghi. Chạy thật hàm điền
// lấy từ source (bản này + handfree nếu có repo bên cạnh). Dữ liệu giả.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const SOURCES = [
  ["autofill", path.join(__dirname, "..", "content", "procedures", "business-registration.js")],
  ["handfree", path.join(__dirname, "..", "..", "tro-ly-nguoi-dan-extension", "content", "procedures", "business-registration.js")],
].filter(([, p]) => fs.existsSync(p)).map(([label, p]) => [label, fs.readFileSync(p, "utf8")]);

function extract(src, name) {
  const start = src.search(new RegExp(`function ${name}\\(`));
  assert.ok(start >= 0, `thiếu ${name}`);
  let depth = 0;
  for (let i = src.indexOf("{", start); i < src.length; i++) {
    if (src[i] === "{") depth++;
    else if (src[i] === "}" && --depth === 0) return src.slice(start, i + 1);
  }
  throw new Error(`không tách được ${name}`);
}

function load(src, boxes) {
  const ctx = {
    boxes,
    findBusinessRowByCode: (code) => (code in boxes ? { code } : null),
    getBusinessRowDescription: (row) => (row ? boxes[row.code] : null),
    setNativeValue: (el, value) => { el.value = value; },
    foldBusinessLineName: (v) => String(v || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim(),
    console: { log() {} },
  };
  vm.runInNewContext(`${extract(src, "fillBusinessLineDetails")}; this.fill = fillBusinessLineDetails;`, ctx);
  return ctx.fill;
}

for (const [label, src] of SOURCES) {
  test(`${label}: có chữ thì ghi thêm dòng dưới tên chính thức, rỗng thì bỏ qua, detailReplace ghi đè`, () => {
    const boxes = { 5630: { value: "Dịch vụ phục vụ đồ uống" }, 4933: { value: "Vận tải hàng hóa bằng đường bộ" },
      4772: { value: "Bán lẻ dược phẩm" } };
    const fill = load(src, boxes);
    const changed = fill([
      { code: "5630", detail: "Cà phê, nước giải khát", detailReplace: false },
      { code: "4933", detail: "", detailReplace: false },
      { code: "4772", detail: "Thuốc đông y", detailReplace: true },
    ]);
    assert.equal(changed, 2);
    assert.equal(boxes[5630].value, "Dịch vụ phục vụ đồ uống\nCà phê, nước giải khát");
    assert.equal(boxes[4933].value, "Vận tải hàng hóa bằng đường bộ");
    assert.equal(boxes[4772].value, "Thuốc đông y");
    assert.equal(fill([{ code: "5630", detail: "Cà phê, nước giải khát" }]), 0, "chạy lại không ghi lặp");
  });

  test(`${label}: dòng có khoá detail thì không tự so tên nữa`, () => {
    const body = extract(src, "fillBusinessLineDescriptions");
    assert.match(body, /if \(rows\.some\(\(row\) => row && Object\.prototype\.hasOwnProperty\.call\(row, "detail"\)\)\) \{\s*return fillBusinessLineDetails\(rows\);/);
  });
}

test("popup không còn tự quyết ô mô tả ngành theo tài khoản (đã chuyển sang BE)", () => {
  const popup = fs.readFileSync(path.join(__dirname, "..", "popup.js"), "utf8");
  assert.doesNotMatch(popup, /skipBusinessLineDescription|businessLineDescriptionParenOnly/);
});

test("giấy không ghi mã ngành: tài khoản có câu cố định thì bỏ tên ngành OCR khỏi ô chưa khớp mã", () => {
  const src = fs.readFileSync(path.join(__dirname, "..", "content", "procedures", "business-registration.js"), "utf8");
  const ctx = { norm: (s) => String(s || "").trim() };
  vm.runInNewContext(`${extract(src, "withoutOcrBusinessAct")}; this.drop = withoutOcrBusinessAct;`, ctx);
  const fields = [
    { name: "ctl00$C$BUSINESS_ACT_TEXTFld", comp: "dom-input", value: "Sản xuất sữa chua" },
    { name: "ctl00$C$khac", comp: "dom-input", value: "x" },
  ];
  assert.deepEqual(ctx.drop(fields, { businessActText: "Hộ kinh doanh phải thực hiện đúng ..." }).map((f) => f.name),
    ["ctl00$C$khac"]);
  assert.equal(ctx.drop(fields, null), fields, "tài khoản không có câu cố định giữ tên ngành OCR");
  assert.equal(ctx.drop(fields, { businessActText: "  " }), fields);

  const nganh = extract(src, "handleNganhNghePage");
  assert.match(nganh, /withoutOcrBusinessAct\(\s*\(\(st\.pages/, "luồng điền tất cả phải lọc trước fillFormStandard");
  const content = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");
  assert.match(content, /endsWith\("BUSINESS_ACT_TEXTFld"\) \? \{ \.\.\.f, value: businessActText \}/,
    "điền lẻ trang ngành nghề thay tên OCR bằng câu cố định");
});
