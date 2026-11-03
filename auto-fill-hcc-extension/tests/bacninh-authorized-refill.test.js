// Khối "Thông tin trong trường hợp được ủy quyền" (Bắc Ninh): mỗi change của ô loại đối tượng làm cổng nạp lại khối
// bằng AJAX, đè form trống lên ô cũ. Chạy THẬT fill-bacninh.js trong vm với DOM giả (cùng kịch bản với
// tro-ly-nguoi-dan-extension/tests/bacninh-same-page-contract.test.js).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const engine = fs.readFileSync(path.join(__dirname, "..", "content", "fill-bacninh.js"), "utf8");
const PFX = "_org_bn_hoso_noptructuyen_";
const OPTION = "Cá nhân khác là Công dân Việt Nam";

function loadEngine({ selected = "" } = {}) {
  const order = [];
  let blockOpen = selected !== "";
  const inputs = new Map();
  const input = (name) => {
    if (!inputs.has(name)) {
      inputs.set(name, {
        tagName: "INPUT", value: "",
        getAttribute: (a) => (a === "type" ? "text" : a === "name" ? name : null),
        dispatchEvent() {},
      });
    }
    return inputs.get(name);
  };
  const checkbox = { checked: blockOpen, click() { this.checked = true; order.push("tick"); }, dispatchEvent() {} };
  const typeSelect = {
    tagName: "SELECT", value: selected, getAttribute: () => null,
    options: [{ textContent: "-- Chọn --", value: "" }, { textContent: OPTION, value: "2" },
      { textContent: "Người cao tuổi", value: "5" }],
    dispatchEvent() {
      if (blockOpen) {
        setTimeout(() => {
          for (const k of [...inputs.keys()]) if (k.startsWith(`${PFX}doiTuongKhac`)) inputs.delete(k);
          order.push("nap-lai");
        }, 50);
      }
      if (this.value === "2") { blockOpen = true; order.push("chon-loai"); }
    },
  };
  const document = {
    querySelectorAll: () => [],
    querySelector(sel) {
      if (sel === `input[type="checkbox"][name="${PFX}boSungDoituongKhac"]`) return checkbox;
      if (sel === `select[name="${PFX}loaiDoiTuongKhac"]`) return typeSelect;
      const m = /^\[name="([^"]+)"\]$/.exec(sel);
      if (m && m[1].startsWith(`${PFX}doiTuongKhac`)) return blockOpen ? input(m[1]) : null;
      return null;
    },
  };
  const H = {
    setNativeValue(el, value) { el.value = value; order.push(el.getAttribute("name").replace(PFX, "")); },
    markFilled() {},
    injectAutofillStyles() {},
  };
  const ctx = {
    document, console, setTimeout, __HCC__: H,
    CSS: { escape: (s) => s },
    Event: class { constructor(type) { this.type = type; } },
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(engine, ctx);
  return { H, order, inputs };
}

const FIELDS = [{ name: "doiTuongKhachoTen", comp: "bn-input", value: "Họ tên mẫu" }];
const settle = () => new Promise((r) => setTimeout(r, 120));

test("lần đầu: tick ô bổ sung, chọn loại đối tượng rồi mới điền", async () => {
  const { H, order, inputs } = loadEngine();
  const res = await H.fillAuthorizedPersonBacNinh(FIELDS, OPTION);
  await settle();
  assert.deepEqual(order, ["tick", "chon-loai", "doiTuongKhachoTen"]);
  assert.equal(inputs.get(`${PFX}doiTuongKhachoTen`).value, "Họ tên mẫu");
  assert.equal(res.filled, 1);
});

test("điền lại khi khối đã mở đúng loại: không chọn lại để cổng khỏi nạp đè form trống", async () => {
  const { H, order, inputs } = loadEngine({ selected: "2" });
  await H.fillAuthorizedPersonBacNinh(FIELDS, OPTION);
  await settle();
  assert.deepEqual(order, ["doiTuongKhachoTen"]);
  assert.equal(inputs.get(`${PFX}doiTuongKhachoTen`).value, "Họ tên mẫu");
});

test("khối đang mở loại khác: chọn lại rồi chờ khối MỚI thay khối cũ mới điền", async () => {
  const { H, order, inputs } = loadEngine({ selected: "5" });
  await H.fillAuthorizedPersonBacNinh(FIELDS, OPTION);
  await settle();
  assert.deepEqual(order, ["chon-loai", "nap-lai", "doiTuongKhachoTen"]);
  assert.equal(inputs.get(`${PFX}doiTuongKhachoTen`).value, "Họ tên mẫu");
});
