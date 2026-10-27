const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const root = path.resolve(__dirname, "..");
const business = fs.readFileSync(path.join(root, "content", "procedures", "business-registration.js"), "utf8");
const content = fs.readFileSync(path.join(root, "content.js"), "utf8");

test("Mirror sessionStorage của fill-all không trùng khóa với extension Handfree", () => {
  // sessionStorage thuộc trang, hai extension cùng đọc được → trùng khóa thì bên kia tự chạy tiếp lượt của bên này.
  assert.match(business, /FILLALL_SESSION_MIRROR_KEY = "__af_fillall_state_mirror"/);
  assert.doesNotMatch(business, /FILLALL_KEY \+ "_mirror"/);
  assert.doesNotMatch(business, /autofill_fillall_state_mirror|__tlnd_fillall_state_mirror/);
});

test("Thẻ tiến độ giữ id và nút Dừng ở light DOM để Handfree bấm dừng được", () => {
  assert.match(content, /const FILLALL_BANNER_ID = "af-fillall-progress"/);
  assert.match(content, /const FILLALL_CANCEL_ID = FILLALL_BANNER_ID \+ "-cancel"/);
  assert.match(content, /<slot name="cancel"><\/slot>/);
  assert.match(content, /btn\.slot = "cancel"[\s\S]*?host\.appendChild\(btn\)/);
});

test("Kết quả lượt điền nhiều trang báo ở dòng trạng thái panel, không vẽ dưới panel dựng lại", () => {
  const popup = fs.readFileSync(path.join(root, "popup.js"), "utf8");
  assert.match(content, /const FILLALL_RESULT_KEY_PREFIX = "autofill_fillall_result_"/);
  assert.match(content, /function endFillAllUI\(doneText\)[\s\S]*?reopenPanelWithFillAllResult\(/);
  assert.match(content, /function cancelFillAll\(\)[\s\S]*?reopenPanelWithFillAllResult\(/);
  assert.match(popup, /const FILLALL_RESULT_KEY = "autofill_fillall_result_" \+ \(EMBEDDED_TAB_ID \?\? ""\)/);
  assert.equal((popup.match(/await restoreFillAllResult\(\);/g) || []).length, 2);
});

test("Button header panel chốt inline display/float/margin để CSS thẻ button của cổng không làm méo", () => {
  assert.match(content, /const BUTTON_STYLE_RESET = \{ float: "none", margin: "0", fontFamily: "inherit"/);
  assert.match(content, /function _headerBtn\(txt\)[\s\S]*?Object\.assign\(b\.style, BUTTON_STYLE_RESET/);
  assert.match(content, /Object\.assign\(histBtn\.style, BUTTON_STYLE_RESET/);
  assert.match(content, /Object\.assign\(btns\.style, \{ display: "flex"/);
});
