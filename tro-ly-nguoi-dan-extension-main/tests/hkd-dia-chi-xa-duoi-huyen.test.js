const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const src = fs.readFileSync(path.join(__dirname, "../content/procedures/business-registration.js"), "utf8");
const pick = (name) => {
  const start = src.indexOf(`function ${name}(`);
  assert.ok(start >= 0, name);
  let depth = 0;
  for (let i = src.indexOf("{", start); i < src.length; i += 1) {
    if (src[i] === "{") depth += 1;
    else if (src[i] === "}" && --depth === 0) return src.slice(start, i + 1);
  }
  throw new Error(name);
};
const areaIsAt = new Function(`${pick("areaFold")}\n${pick("areaSelectedText")}\n${pick("areaIsAt")}\nreturn areaIsAt;`)();
const sel = (text) => ({ selectedOptions: [{ textContent: text }] });

test("xã trên cổng có đuôi huyện cũ vẫn coi là đã chọn đúng (không chọn lại → không postback xoá số nhà)", () => {
  assert.equal(areaIsAt(sel("Phường Lang Biang - Đà Lạt"), "Lang Biang"), true);
  assert.equal(areaIsAt(sel("Phường Lang Biang - Đà Lạt"), "Phường Lang Biang"), true);
  assert.equal(areaIsAt(sel("Xã Tân Hà"), "Tân Hà"), true);
});

test("xã khác tên vẫn phải chọn lại", () => {
  assert.equal(areaIsAt(sel("Phường Lang Biang - Đà Lạt"), "Lang"), false);
  assert.equal(areaIsAt(sel("Phường Xuân Hương - Đà Lạt"), "Lang Biang"), false);
  assert.equal(areaIsAt(sel(""), "Lang Biang"), false);
  assert.equal(areaIsAt(sel("Phường Lang Biang"), ""), false);
});

test("chọn xã khi có số nhà cần ghi thì chờ ô số nhà dựng lại, không chờ cứng 900ms", () => {
  const body = pick("fillAddressCascade");
  assert.match(body, /if \(settleId\) await waitForPanelSettle\(settleId/);
  assert.match(body, /chooseAndWait\(ward, null, streetBefore && streetBefore\.id\)/);
  assert.ok(body.indexOf("chooseAndWait(ward") < body.indexOf("setNativeValue(el, sf.value"));
});
