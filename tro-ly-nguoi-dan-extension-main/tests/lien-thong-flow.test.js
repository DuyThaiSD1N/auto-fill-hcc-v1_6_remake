// Cổng liên thông (lienthong.dichvucong.gov.vn): luồng 6 bước do BE điều phối (chat/lien_thong.py, cờ
// supportsLienThongFlow) — báo bước đang mở, bổ sung ô trên form Angular, bấm chuyển bước / quay lại, chọn cách nhận
// kết quả từng giấy tờ, bấm Hoàn thành sau khi soát cam đoan + mã kiểm tra.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const read = (p) => fs.readFileSync(path.join(root, p), "utf8").replace(/^\s*\/\/.*$/gm, "");
const sidebar = read("sidebar.js");
const content = read("content.js");
const portal = read("content/lien-thong.js");
const review = read("content/field-review-angular.js");
const css = read("sidebar.css");

test("manifest nạp bộ bổ sung ô Angular và phần trang liên thông sau engine fill-angular", () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));
  const js = manifest.content_scripts.find((c) => c.js.includes("content/fill-angular.js")).js;
  for (const file of ["content/field-review-angular.js", "content/lien-thong.js"]) {
    assert.ok(js.indexOf(file) > js.indexOf("content/fill-angular.js"), file);
    assert.ok(js.indexOf(file) > js.indexOf("content/field-review.js"), file);
    assert.ok(js.indexOf(file) < js.indexOf("content.js"), file);
  }
});

test("bước liên thông là trường riêng, không đụng wizardStep 4 bước của cổng tư pháp", () => {
  assert.match(content, /lienThongStep: \(window\.__TLND__ && typeof window\.__TLND__\.lienThongStep === "function"\)/);
  assert.match(portal, /items\.forEach\(\(li, i\) => \{ if \(li\.classList\.contains\("active"\)\) step = i \+ 1; \}\);/);
  assert.match(portal, /H\.lienThongStep = currentStep;/);
});

test("sidebar khai cờ, chạy lệnh liên thông ngoài lượt ask() và vẽ thẻ cách nhận từng giấy", () => {
  assert.match(sidebar, /supportsLienThongFlow: true,/);
  assert.match(sidebar, /a\.type === "lien_thong_next"\) \{\s*setTimeout\(\(\) => \{ void runLienThongMove\(a\); \}, 0\);/);
  assert.match(sidebar, /a\.type === "lien_thong_result_scan" \|\| a\.type === "lien_thong_result_set"\) \{\s*setTimeout/);
  assert.match(sidebar, /a\.type === "lien_thong_submit"\) \{\s*setTimeout\(\(\) => \{ void runLienThongSubmit\(\); \}, 0\);/);
  assert.match(sidebar, /if \(card\.kind === "lt_result_groups"\) return renderLtResultGroups\(card\);/);
  assert.match(css, /\.ltr-opt\.picked \{/);
});

test("bấm chuyển bước: đối chiếu lienThongStep, bị chặn ở Kê khai thì tô lại ô để BE mời bổ sung", () => {
  assert.match(sidebar, /step = Number\(ctx\?\.lienThongStep\) \|\| 0;\s*moved = !!expect && step === expect;/);
  assert.match(sidebar, /if \(!moved && a\.fieldReview\) \{\s*const marked = await sendToContent\(\{ \.\.\.a\.fieldReview, action: "fieldReviewMark" \}\);/);
  assert.match(sidebar, /__action:lt_step_report:/);
});

test("watcher báo đổi bước liên thông ở mọi state đang theo dõi, kể cả sau đính kèm", () => {
  assert.match(sidebar, /const ltMoved = !!lastReplyData\?\.lien_thong && !!ctx\.lienThongStep && ctx\.lienThongStep !== lastLtStep;/);
  assert.match(sidebar, /\$\{ctx\.lienThongStep \|\| 0\}/);
});

test("nộp: soát cam đoan + mã kiểm tra trước, chỉ bấm nút Hoàn thành, đọc toast lỗi của cổng", () => {
  assert.match(portal, /if \(camDoan && !camDoanTicked\(camDoan\)\) missing\.push\("camDoan"\);/);
  assert.match(portal, /if \(captchaInput && !String\(captchaInput\.value \|\| ""\)\.trim\(\)\) missing\.push\("captcha"\);/);
  assert.match(portal, /if \(missing\.length\) return \{ clicked: false, missing \};/);
  assert.match(portal, /fold\(el\.textContent\) === "hoan thanh"/);
  assert.match(portal, /if \(fresh\.classList\.contains\("toast-success"\)\) return "";/);
});

test("chỉ trang liên thông trả lời lệnh; bộ đọc ô Angular không cướp lượt của eForm / SurveyJS", () => {
  assert.match(portal, /if \(!action\.startsWith\("lienThong"\) \|\| !onPortal\(\) \|\| !currentStep\(\)\) return;/);
  assert.match(review, /const ourPage = \(\) => location\.hostname === HOST && H\.detectFormKind\?\.\(\) === "angular"/);
  assert.match(review, /if \(!ourPage\(\)\) return;/);
});

test("ô khoá (người yêu cầu từ VNeID) và ô tích không hỏi; ghi chú đỏ tĩnh không bị tính là lỗi", () => {
  assert.match(review, /input\?\.disabled \|\| input\?\.readOnly \|\| host\.hasAttribute\("disabled"\)/);
  assert.match(review, /if \(type === "checkbox"\) continue;/);
  assert.match(review, /const ERROR_TEXT = \/khong duoc de trong\|bat buoc\|khong hop le\|vui long\/;/);
  assert.match(review, /ng-select\.required/);
});

test("điền câu trả lời bằng engine fill-angular, địa chỉ chọn đúng ô Tỉnh / Xã đang hỏi", () => {
  assert.match(review, /await H\.fillFormAngular\(\[\{ name: slot\.name, comp: slot\.comp, value \}\]\);/);
  assert.match(review, /if \(slot\.role === "tinh" \|\| slot\.role === "xa"\) return pickArea\(input, value\);/);
  assert.match(review, /H\.fieldReviewPointer\?\.focus\(slot\.box\)/);
});

test("đổi cách nhận kết quả: chỉ nhắc các ô vừa mọc ra (địa chỉ bưu điện), tính từng ô con của khối địa chỉ", () => {
  assert.match(portal, /const before = missingFields\(msg\.groups\);/);
  assert.match(portal, /\.filter\(\(\[key\]\) => !before\.has\(key\)\)/);
  assert.match(portal, /const boxes = Array\.from\(host\.querySelectorAll\("mat-form-field"\)\);/);
});

// ── Khối "Thông tin người yêu cầu": chọn đúng người trong giấy tờ trùng người đăng nhập ──
// fill-angular.js là IIFE gắn hàm vào window.__TLND__; nạp với window giả, chỉ cần hàm thuần.
function napEngine() {
  const src = fs.readFileSync(path.join(root, "content", "fill-angular.js"), "utf8");
  const window = { __TLND__: {} };
  const chrome = { runtime: { onMessage: { addListener() {} } } };
  new Function("window", "document", "chrome", src)(window, { querySelectorAll: () => [] }, chrome);
  return window.__TLND__;
}

test("người yêu cầu là cha / mẹ / người thứ ba → chọn theo số định danh; cùng tên khác số thì không chọn", () => {
  const { chonNguoiYeuCau } = napEngine();
  const nguoi = [
    { vaiTro: "cha", ten: "TRẦN VĂN BỐ", cccd: "001090000011" },
    { vaiTro: "me", ten: "LÊ THỊ MẸ", cccd: "001190000022" },
    { vaiTro: "khac", ten: "PHẠM VĂN ÔNG", cccd: "001060000033" },
  ];
  assert.equal(chonNguoiYeuCau(nguoi, { cccd: "001090000011", ten: "Trần Văn Bố" }).vaiTro, "cha");
  assert.equal(chonNguoiYeuCau(nguoi, { cccd: "001190000022", ten: "LÊ THỊ MẸ" }).vaiTro, "me");
  assert.equal(chonNguoiYeuCau(nguoi, { cccd: "001060000033", ten: "" }).vaiTro, "khac");
  assert.equal(chonNguoiYeuCau(nguoi, { cccd: "001090000099", ten: "TRẦN VĂN BỐ" }), null);
  assert.equal(chonNguoiYeuCau([{ vaiTro: "toKhai", ten: "ĐỖ THỊ BÀ" }], { cccd: "001150000044", ten: "Do Thi Ba" }).vaiTro, "toKhai");
});
