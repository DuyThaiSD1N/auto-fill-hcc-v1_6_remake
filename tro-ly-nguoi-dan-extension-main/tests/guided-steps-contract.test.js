// Luồng dẫn từng bước: trợ lý bấm hộ nút "Bước tiếp theo" / "Gửi hồ sơ" của cổng tư pháp.
//
// Hàng rào then chốt là TƯƠNG THÍCH: backend mới vẫn phải phục vụ bản extension ngoài chợ.
// Cửa duy nhất mở luồng mới là capability supportsGuidedSteps — mất cờ này thì backend tưởng
// mọi client đều hiểu nút mới.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const read = (...p) => fs.readFileSync(path.join(root, ...p), "utf8");
const sidebar = read("sidebar.js");
const guided = read("content", "guided-steps.js");
const portalDvc = read("content", "portal-dvc.js");
const css = read("sidebar.css");
const manifest = JSON.parse(read("manifest.json"));

test("khai capability để backend biết client hiểu luồng mới", () => {
  const block = sidebar.match(/const CLIENT_CAPABILITIES = Object\.freeze\(\{([\s\S]*?)\}\);/);
  assert.ok(block, "không tìm thấy CLIENT_CAPABILITIES");
  assert.match(block[1], /supportsGuidedSteps:\s*true/);
});

test("engine bấm nút được nạp trên mọi cổng cùng các engine content khác", () => {
  const block = manifest.content_scripts.find((c) => c.js.includes("content/guided-steps.js"));
  assert.ok(block, "guided-steps.js chưa được khai trong manifest");
  assert.ok(block.js.includes("content/portal-dvc.js"), "phải nạp cùng engine cổng tư pháp");
});

test("nút chuyển bước đọc giá trị ô chủ hồ sơ TRƯỚC khi gửi backend", () => {
  // Backend gọi tên ô còn thiếu ("ngày cấp", "số điện thoại") nên phải có giá trị thật;
  // gửi rỗng là backend tưởng trang trống và chặn oan.
  assert.match(sidebar, /c\.send === "__action:guided_next"/);
  assert.match(sidebar, /action: "readOwnerFields", fields: c\.fields \|\| \[\]/);
  assert.match(sidebar, /__action:guided_next:\$\{JSON\.stringify\(payload\)\}/);
});

test("đọc ô chủ hồ sơ bỏ qua ô không thấy thay vì trả rỗng", () => {
  const fn = portalDvc.match(/function readOwnerFields\(fields\) \{([\s\S]*?)\n  \}/);
  assert.ok(fn, "thiếu readOwnerFields");
  assert.match(fn[1], /if \(!control\) continue;/);
  // Combobox "Nơi cấp" là react-select: .value của input luôn rỗng, phải đọc nhãn đang hiện.
  assert.match(fn[1], /owner-combobox[\s\S]*comboDisplayedValue/);
});

test("chỉ frame có nút mới trả lời, tránh frame rỗng chiếm lượt", () => {
  assert.match(guided, /if \(!button\) return;/);
  assert.match(portalDvc, /if \(!Object\.keys\(values\)\.length\) return;/);
});

test("không bấm nhầm Gửi hồ sơ khi đang định chuyển bước", () => {
  // data-e2e="btn-next" dùng chung cho cả hai nút ở hai trang khác nhau → phải lọc theo chữ.
  assert.match(guided, /const NEXT_TEXTS = \["buoc tiep theo"\]/);
  assert.match(guided, /const SUBMIT_TEXTS = \["gui ho so", "nop ho so"\]/);
  assert.match(guided, /matchesText/);
  // Bước Thành phần hồ sơ không có data-e2e → phải khai id riêng.
  assert.match(guided, /"#nop-thu-tuc-b-3"/);
  assert.match(guided, /#kt_gui-ho-so/);
});

test("bắt được toast cổng báo thiếu (mount động, tự tắt sau vài giây)", () => {
  assert.match(guided, /role="alert"/);
  assert.match(guided, /form-item-message/, "lỗi từng ô của shadcn/ui");
  // Rình nhiều nhịp chứ không đọc một lần: cổng validate xong mới hiện toast.
  assert.match(guided, /while|for \(let i = 0; i < \d+ && !message/);
  assert.match(guided, /before\.has\(folded\)/, "chỉ lấy thông báo MỚI so với trước khi bấm");
  // Cổng dùng CHUNG khung toast để báo nộp thành công — đọc nhầm là bảo "chưa cho chuyển bước"
  // ngay lúc hồ sơ vừa nộp xong.
  assert.match(guided, /folded\.includes\("thanh cong"\)/);
});

test("xác nhận trang chuyển bước THẬT bằng số bước, không tin mỗi cú bấm", () => {
  const fn = sidebar.match(/async function runGuidedNext\(phase, expect\) \{([\s\S]*?)\n  \}/);
  assert.ok(fn, "thiếu runGuidedNext");
  assert.match(fn[1], /getPageContext/);
  assert.match(fn[1], /wizardStep === expect/);
  assert.match(fn[1], /__action:guided_step_report/);
});

test("báo kết quả chạy NGOÀI runActions, không gọi ask() lồng trong ask()", () => {
  // Sự cố 22/09/2026: await ask() ngay trong runActions → lượt mới nằm lại pendingQueue chờ
  // lượt ngoài, lượt ngoài lại chờ runActions → bấm nút xong bot im luôn, watcher cũng kẹt.
  const block = sidebar.match(/a\.type === "guided_click_next"\) \{([\s\S]*?)a\.type === "fill_owner_fields"/);
  assert.ok(block, "thiếu handler guided_click_next");
  const code = block[1].replace(/\/\/.*/g, ""); // chú thích có nhắc "ask()" để giải thích bẫy
  assert.doesNotMatch(code, /\bask\(/, "runActions không được gọi ask() trực tiếp");
  assert.match(block[1], /setTimeout\(\(\) => \{ void runGuidedNext\(phase, expect\); \}, 0\)/);
  assert.match(block[1], /setTimeout\(\(\) => \{ void runGuidedSubmit\(\); \}, 0\)/);
});

test("không bao giờ có hai nút chuyển bước sống cùng lúc", () => {
  const fn = sidebar.match(/function renderChips\(chips\) \{([\s\S]*?)const wrap = /);
  assert.ok(fn, "thiếu renderChips");
  assert.match(fn[1], /chips\.some\(\(c\) => c\.cta\)/);
  assert.match(fn[1], /querySelectorAll\("\.chip\.cta"\)[\s\S]*\.remove\(\)/);
});

test("nút CTA nổi bật và khi đã bấm thì thành trạng thái xong, không mờ đi", () => {
  assert.match(sidebar, /\(c\.cta \? " cta" : ""\)/);
  assert.match(css, /\.chip\.cta \{/);
  assert.match(css, /\.chip\.cta:disabled/);
  // Người dùng tắt hiệu ứng thì không được nhấp nháy.
  assert.match(css, /prefers-reduced-motion[\s\S]*\.chip\.cta/);
});
