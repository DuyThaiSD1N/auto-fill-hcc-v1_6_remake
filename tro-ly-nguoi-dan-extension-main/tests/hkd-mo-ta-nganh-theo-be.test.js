// Ô mô tả từng dòng ngành nghề hộ kinh doanh: BE quyết chữ ghi (khoá "detail"), extension chỉ ghi. Chạy thật hàm điền
// lấy từ source (bản này + Auto Fill nếu có repo bên cạnh). Dữ liệu giả.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const SOURCES = [
  ["handfree", path.join(__dirname, "..", "content", "procedures", "business-registration.js")],
  ["autofill", path.join(__dirname, "..", "..", "auto-fill-hcc-extension", "content", "procedures", "business-registration.js")],
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
