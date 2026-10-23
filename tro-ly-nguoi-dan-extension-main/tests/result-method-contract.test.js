// Bước "Thông tin nhận kết quả": trợ lý gạt sẵn công tắc "bản giấy có đóng dấu" trên cổng,
// công dân đổi được sang hai cách kia — nhưng trợ lý CHỈ tick, địa chỉ/người nhận công dân tự điền.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const read = (f) => fs.readFileSync(path.join(root, f), "utf8");
const sidebar = read("sidebar.js");
const portal = read("content/portal-dvc.js");
const css = read("sidebar.css");

const stripComments = (src) => src
  .replace(/\/\*[\s\S]*?\*\//g, "")
  .split("\n").map((line) => line.replace(/\/\/.*$/, "")).join("\n");
const portalCode = stripComments(portal);

test("khai capability để BE biết client gạt được công tắc", () => {
  // Thiếu cờ → BE giữ câu hướng dẫn ba cách; bản trên chợ không khai nên không đổi gì.
  assert.match(sidebar, /supportsResultMethod: true/);
});

test("khớp công tắc theo NHÃN, tuyệt đối không theo id", () => {
  // id Radix kiểu ":r91:-form-item" do React sinh lại mỗi lần render.
  assert.match(portalCode, /querySelectorAll\('button\[role="switch"\]'\)/);
  assert.match(portalCode, /fold\(resultSwitchRow\(sw\)\.textContent\)\.includes\(wanted\)/);
  assert.doesNotMatch(portalCode, /-form-item/, "không được bám id React");
});

test("hàng của công tắc dừng ở tổ tiên còn ĐÚNG MỘT công tắc", () => {
  // Sự cố 24/09/2026: leo theo số cấp cố định thì tới div bọc chung cả ba hàng, text chứa cả
  // ba nhãn → công tắc đầu tiên khớp mọi nhãn, gạt xong bị chính vòng "tắt cái khác" tắt đi.
  assert.match(portalCode, /function resultSwitchRow[\s\S]{0,400}?querySelectorAll\('button\[role="switch"\]'\)\.length > 1\) break;/);
});

test("gạt xong phải xác nhận trạng thái THẬT của công tắc", () => {
  // Bấm được ≠ trang chịu bật. Radix mở bằng pointerdown nên phải clickLikeUser.
  assert.match(portalCode, /clickLikeUser\(sw\)/);
  assert.match(portalCode, /waitFor\(\(\) => resultSwitchOn\(sw\) === on/);
  assert.match(portalCode, /data-state"\) === "checked"/);
});

test("là switch chứ không phải radio nên phải tự tắt cái đang bật", () => {
  assert.match(portalCode, /for \(const khac of \(allLabels \|\| \[\]\)\)[\s\S]{0,220}?setResultSwitch\(sw, false\)/);
});

test("chỉ soi ô trống cho cách thật sự đòi thêm thông tin", () => {
  // Bản giấy / trực tuyến gạt xong là xong (kiểm trên cổng thật). Quét cả trang cho hai cách
  // đó là mời gọi báo nhầm ô bắt buộc của khối khác trên cùng trang.
  assert.match(portalCode, /if \(!needsInput\) return \{ ok: true, missing: \[\] \};/);
  assert.match(sidebar, /needsInput: !!a\.needsInput/);
});

test("ô bắt buộc còn trống đọc dấu * của CHÍNH cổng, không khai cứng", () => {
  assert.match(portalCode, /function missingResultFields/);
  assert.match(portalCode, /\/\\\*\/\.test\(String\(label\.textContent/);
  // Không được khai sẵn tên ô trong extension — mỗi cách mở một bộ ô khác nhau và cổng còn đổi.
  assert.doesNotMatch(portalCode, /đơn vị bưu chính|Nơi nhận kết quả/i);
});

test("báo kết quả chạy NGOÀI runActions", () => {
  // await ask() trong runActions = khoá cứng sidebar.
  assert.match(sidebar, /a\.type === "select_result_method"[\s\S]{0,140}?setTimeout\(\(\) => \{ void runSelectResultMethod\(a\); \}, 0\)/);
  assert.match(sidebar, /__action:result_method_report/);
});

test("card phản chiếu lựa chọn và không để hai bộ thẻ chồng nhau", () => {
  assert.match(sidebar, /card\.kind === "result_methods"\) return renderResultMethods\(card\)/);
  assert.match(sidebar, /querySelectorAll\("\.result-methods"\)\.forEach\(\(el\) => el\.remove\(\)\)/);
  assert.match(sidebar, /opt\.key === card\.selected \? " picked" : ""/);
  // Bấm lại đúng thẻ đang chọn thì thôi, không gạt lại cho rối.
  assert.match(sidebar, /if \(opt\.key === card\.selected\) return;/);
  assert.match(css, /\.result-methods \.opt\.picked/);
});
