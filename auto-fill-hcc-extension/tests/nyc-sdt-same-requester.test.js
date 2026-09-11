const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "content", "fill-angular.js"), "utf8");

const start = source.indexOf("// Bỏ dấu + gộp khoảng trắng để so tên");
const end = source.indexOf("// mat-select (Angular Material)", start);
assert.ok(start >= 0 && end > start, "Không tách được helper điền SĐT người yêu cầu");

function run({ tenTrenForm, tenTrenToKhai, sdt, coOSdt = true }) {
  const filled = [];
  const sandbox = {
    console: { log() {}, warn() {} },
    readRequesterIdentity: () => ({ cccd: "", ten: tenTrenForm }),
    fieldCandidates: (field) => [field.name],
    findFormControl: (names) => (coOSdt && names.includes("NycSdt") ? { tag: "NycSdt" } : null),
    fillNgText: (el, value) => { filled.push(value); return true; },
  };
  vm.runInNewContext(`
    ${source.slice(start, end)}
    globalThis.fill = fillNycSdtIfSameRequester;
  `, sandbox);
  return sandbox.fill({ name: "NycSdt", comp: "sdt-nguoiyeucau", value: { sdt, ten: tenTrenToKhai } })
    .then((ok) => ({ ok, filled }));
}

(async () => {
  // Trùng tên (khác cách viết hoa/dấu do OCR) → điền số điện thoại.
  let r = await run({
    tenTrenForm: "Nguyễn Trần Đăng Vinh",
    tenTrenToKhai: "NGUYỄN TRẦN ĐĂNG VINH",
    sdt: "0981828309",
  });
  assert.equal(r.ok, true, "Cùng người yêu cầu thì phải điền SĐT");
  assert.deepEqual(r.filled, ["0981828309"]);

  // Khác người → tuyệt đối không điền số của người khác.
  r = await run({
    tenTrenForm: "Trần Vũ Đan Thanh",
    tenTrenToKhai: "NGUYỄN TRẦN ĐĂNG VINH",
    sdt: "0981828309",
  });
  assert.equal(r.ok, false, "Khác người yêu cầu thì phải bỏ qua");
  assert.deepEqual(r.filled, [], "Không được điền SĐT cho người khác");

  // Cổng chưa đổ tên người yêu cầu → không đủ căn cứ, bỏ qua.
  r = await run({ tenTrenForm: "", tenTrenToKhai: "NGUYỄN TRẦN ĐĂNG VINH", sdt: "0981828309" });
  assert.equal(r.ok, false, "Form chưa có tên người yêu cầu thì không điền");
  assert.deepEqual(r.filled, []);

  // Trùng tên nhưng form không có ô SĐT → báo không điền được, không ném lỗi.
  r = await run({
    tenTrenForm: "NGUYỄN TRẦN ĐĂNG VINH",
    tenTrenToKhai: "Nguyễn Trần Đăng Vinh",
    sdt: "0981828309",
    coOSdt: false,
  });
  assert.equal(r.ok, false, "Không thấy ô SĐT thì trả false");

  console.log("nyc-sdt-same-requester: OK");
})();
