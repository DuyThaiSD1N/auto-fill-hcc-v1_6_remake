// Cổng Lai Châu (dichvucong.laichau.gov.vn, eForm Nth, mỗi bước một trang "Bước N - …"): bước "Lệ phí hồ sơ" do BE
// điều phối (chat/lai_chau.py, cờ supportsLaiChauFeeStep) — báo bước trang, bấm "Đồng ý và tiếp tục", đọc / chọn hình
// thức nhận kết quả + mức lệ phí, lấy địa chỉ người nộp.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const raw = (p) => fs.readFileSync(path.join(root, p), "utf8");
const read = (p) => raw(p).replace(/^\s*\/\/.*$/gm, "");
const sidebar = read("sidebar.js");
const content = read("content.js");
const portal = read("content/laichau/portal.js");

test("manifest nạp content/laichau/portal.js sau engine điền và trước content.js", () => {
  const manifest = JSON.parse(raw("manifest.json"));
  const js = manifest.content_scripts.find((c) => c.js.includes("content/fill-core.js")).js;
  const at = js.indexOf("content/laichau/portal.js");
  assert.ok(at > js.indexOf("content/fill-core.js"));
  assert.ok(at < js.indexOf("content.js"));
});

test("sidebar khai cờ, gửi lcStep, watcher báo đổi bước khi BE bật lai_chau, chạy lệnh lc_* ngoài lượt ask()", () => {
  assert.match(sidebar, /supportsLaiChauFeeStep: true,/);
  assert.match(sidebar, /lcStep: Number\(c\.lcStep\) \|\| 0,/);
  assert.match(sidebar, /lcStep: Number\(ctx\?\.lcStep\) \|\| 0,/);
  assert.match(sidebar, /: lastReplyData\?\.lai_chau \? Number\(ctx\.lcStep\) \|\| 0\s*:/);
  assert.match(sidebar, /a\.type === "lc_result_scan" \|\| a\.type === "lc_result_set"\) \{\s*setTimeout\(\(\) => \{ void runLcResult\(a\); \}, 0\);/);
  assert.match(sidebar, /a\.type === "lc_next"\) \{\s*setTimeout\(\(\) => \{ void runLcNext\(\); \}, 0\);/);
  // Bấm hợp lệ thì cổng tải trang mới: chỉ báo BE khi bị chặn.
  assert.match(sidebar, /if \(res\?\.clicked && !res\?\.message\) return;/);
  assert.match(sidebar, /__action:lc_result_report:/);
});

test("content.js đưa lcStep vào ngữ cảnh trang", () => {
  assert.match(content, /lcStep: \(window\.__TLND__ && typeof window\.__TLND__\.laiChauStep === "function"\)/);
});

test("portal: chỉ trang tiếp nhận online của cổng Lai Châu, ô theo name cổng, nút lấy địa chỉ + nút đi tiếp", () => {
  assert.match(portal, /const HOST = "dichvucong\.laichau\.gov\.vn";/);
  assert.match(portal, /location\.pathname\.includes\("\/tiep-nhan-online\/"\)/);
  assert.match(portal, /select\[name\^="\$\{FEE\}_"\]/);
  assert.match(portal, /button\[data-action="get-address-from-user"\]/);
  assert.match(portal, /document\.getElementById\("btn-next"\)/);
  // "Đến cơ quan giải quyết" (value 0) không có khối địa chỉ → không bấm lấy địa chỉ.
  assert.match(portal, /result\.value !== "0" && addressShown\(\) && addressEmpty\(\)/);
  // Ô chọn chỉ một lựa chọn thì chọn luôn; bị chặn thì đọc cả hộp thoại lẫn lời dưới ô (p.form-error).
  assert.match(portal, /options\.length === 1 && setSelect\(select, textOf\(options\[0\]\)\)\) prepared\.push\(`auto:\$\{group\.name\}`\)/);
  assert.match(portal, /document\.querySelectorAll\("p\.form-error"\)/);
});

function runPortal({ title, hostname = "dichvucong.laichau.gov.vn", pathname = "/dich-vu-cong/tiep-nhan-online/nhap-le-phi-ho-so" }) {
  const window = {};
  const context = {
    window,
    document: { title, querySelectorAll: () => [], querySelector: () => null, getElementById: () => null },
    location: { hostname, pathname },
    chrome: { runtime: { onMessage: { addListener() {} } } },
    getComputedStyle: () => ({ visibility: "visible" }),
    CSS: { escape: (s) => s },
    Event: class {},
    setTimeout,
    console,
  };
  vm.runInNewContext(raw("content/laichau/portal.js"), context);
  return window.__TLND__.laiChauStep();
}

test("portal: số bước đọc từ tiêu đề \"Bước N - …\" của trang nộp hồ sơ", () => {
  assert.equal(runPortal({ title: "Bước 4 - Lệ phí hồ sơ" }), 4);
  assert.equal(runPortal({ title: "Bước 2 - Thông tin người nộp hồ sơ" }), 2);
  assert.equal(runPortal({ title: "Dịch vụ công trực tuyến" }), 0);
  assert.equal(runPortal({ title: "Bước 4 - Lệ phí hồ sơ", hostname: "dichvucong.gov.vn" }), 0);
  assert.equal(runPortal({ title: "Bước 4 - Lệ phí hồ sơ", pathname: "/dichvucong/tracuu" }), 0);
  // Trang chọn trường hợp không ghi "Bước N" trên tiêu đề → nhận theo đường dẫn, là bước 1.
  assert.equal(runPortal({ title: "Trường hợp nộp hồ sơ",
    pathname: "/dich-vu-cong/tiep-nhan-online/chon-truong-hop-ho-so" }), 1);
});
