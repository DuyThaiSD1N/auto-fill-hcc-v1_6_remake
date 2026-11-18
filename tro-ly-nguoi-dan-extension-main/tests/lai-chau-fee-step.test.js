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
  assert.match(portal, /const HOSTS = \["dichvucong\.laichau\.gov\.vn", "dichvucong\.bocongan\.gov\.vn"\];/);
  assert.match(portal, /location\.pathname\.includes\("\/tiep-nhan-online\/"\)/);
  assert.match(portal, /select\[name\^="\$\{FEE\}_"\]/);
  assert.match(portal, /button\[data-action="get-address-from-user"\]/);
  assert.match(portal, /document\.getElementById\("btn-next"\)/);
  // "Đến cơ quan giải quyết" (value 0) không có khối địa chỉ → không bấm lấy địa chỉ.
  assert.match(portal, /result\.value !== "0" && addressShown\(\) && addressEmpty\(\)/);
  // Ô chọn chỉ một lựa chọn thì chọn luôn; bị chặn thì đọc cả hộp thoại lẫn lời dưới ô (p.form-error).
  assert.match(portal, /options\.length === 1 && await setControl\(group\.name, textOf\(options\[0\]\)\)\) prepared\.push\(`auto:\$\{group\.name\}`\)/);
  assert.match(portal, /document\.querySelectorAll\("p\.form-error"\)/);
});

test("portal (Bộ Công an, hộ chiếu 1.001456): bootstrap-select đứng cạnh <select>, chọn bằng bấm mục, preset cơ quan theo tỉnh", () => {
  // Khung div.bootstrap-select là anh em ngay sau thẻ <select> ẩn → vẫn tính là ô đang hiện.
  assert.match(portal, /const controlShown = \(el\) => shown\(el\) \|\| shown\(bootstrapOf\(el\)\)/);
  assert.match(portal, /for \(let sib = select\?\.nextElementSibling; sib; sib = sib\.nextElementSibling\)/);
  // Chọn như người dùng (bootstrap-select tự bắn change + changed.bs.select), không được thì đặt value như cũ.
  assert.match(portal, /bootstrapOf\(el\) && await pickBootstrap\(el, text\)\) return true;\s*if \(setSelect\(el, text\)\) return true;/);
  // Lượt đọc đầu: chọn ô cơ quan theo preset BE gửi, chờ cổng hiện ô Trường hợp giải quyết rồi mới đọc.
  assert.match(portal, /await prepare\(msg\.groups, msg\.presets\)/);
  assert.match(portal, /const preset = await applyPresets\(groups, presets\);\s*[\s\S]{0,120}if \(preset\.length\) await settle\(\);/);
  assert.match(portal, /options\.length === 1 && await setControl\(group\.name, options\[0\]\)\) prepared\.push\(`preset:\$\{group\.name\}`\)/);
  assert.match(read("sidebar.js"), /presets: a\.presets/);
  // Ảnh 18/11: ô cơ quan nạp chậm → khung dò bắt nhầm ô ngôn ngữ đầu trang (cbx_MA_NGON_NGU) → bỏ ô ngôn ngữ.
  assert.match(portal, /\/ngon_\?ngu\|language\/i\.test\(name\)\) continue;/);
  // Chờ ô cơ quan + lựa chọn của tỉnh nạp xong (tối đa 6 giây) rồi mới chọn; đọc lại (prepare:false) vẫn chọn bù.
  assert.match(portal, /waited < 6000 && !target\?\.options\.length/);
  assert.match(portal, /msg\.prepare === false && Array\.isArray\(msg\.presets\)[\s\S]{0,40}\s*prepared = await applyPresets/);
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
  // Cổng DVC Bộ Công an cùng nền eForm Nth (đăng ký xe): trang chọn trường hợp cũng là bước 1.
  assert.equal(runPortal({ title: "Bộ công an", hostname: "dichvucong.bocongan.gov.vn",
    pathname: "/bo-cong-an/tiep-nhan-online/chon-truong-hop-ho-so" }), 1);
});

test("portal: nhóm ô \"*\" = tự dò mọi ô chọn đang hiện trong khung có nút Đồng ý và tiếp tục (nhãn #_lbl_<name>)", () => {
  assert.match(portal, /const AUTO = "\*";/);
  assert.match(portal, /const resolve = \(groups\) => \(\(groups \|\| \[\]\)\.some\(\(g\) => g\?\.name === AUTO\) \? discover\(\)/);
  assert.match(portal, /document\.getElementById\(`_lbl_\$\{name\}`\)/);
  assert.match(portal, /\.querySelector\("\.mandatory"\)/);
  // Ô bị bootstrap-select / select2 che vẫn tính là đang hiện.
  assert.match(portal, /closest\?\.\("\.bootstrap-select"\)/);
  assert.match(sidebar, /supportsBcaCaseStep: true/);
});


test("portal (Bộ Công an): dò cả nhóm radio, chờ khung chọn trường hợp đứng yên, select2 nạp khi mở, lưới đỡ đọc lại", () => {
  // Ô "Cơ quan giải quyết hồ sơ" (đăng ký mẫu con dấu) có thể chỉ mang id → dò cả select[id]; bỏ ô ngôn ngữ đầu trang;
  // lượt đọc tự dò đầu tiên chờ ô nạp (AJAX) tối đa 4 giây.
  assert.match(portal, /const CASE_CONTROLS = "select\[name\], select\[id\], input\[type='radio'\]\[name\]";/);
  assert.match(portal, /querySelectorAll\(CASE_CONTROLS\)/);
  assert.match(portal, /el\.closest\("header, nav, \.dvc-header, #dvc-header-home"\)/);
  assert.match(portal, /waited < 4000 && !discover\(\)\.length/);
  assert.match(portal, /document\.getElementById\(name\)/);
  // Chọn xong chờ DOM khung chọn trường hợp đứng yên (cổng tải thêm ô qua AJAX), không chờ mốc cố định.
  assert.match(portal, /new MutationObserver\(\(\) => \{ lastChange = Date\.now\(\); \}\)/);
  assert.match(portal, /if \(ok\) await settle\(\);/);
  assert.match(portal, /async function loadLazy\(/);
  assert.match(portal, /\.select2-container--open \.select2-results__option/);
  // Bị chặn mà cổng không nói gì → báo đúng ô bắt buộc còn trống.
  assert.match(portal, /message: `Còn trống: \$\{missing\.join\(", "\)\}`/);
  assert.match(portal, /__tlnd: "lcCaseChanged"/);
  assert.match(sidebar, /ask\("__action:lc_case_changed", "system"\)/);
});


test("portal (Bộ Công an): radio iCheck — bấm lớp phủ ins.iCheck-helper, nhãn lựa chọn ở khối riêng, nhãn nhóm phía trước", () => {
  assert.match(portal, /radio\.parentElement\?\.querySelector\("ins\.iCheck-helper"\)/);
  assert.match(portal, /for \(const target of \[helper, label, radio\]\)/);
  assert.match(portal, /function optionBox\(radio\)/);
  assert.match(portal, /function radioGroupLabel\(radio\)/);
  const core = read("content/fill-core.js");
  assert.match(core, /const iCheckHelper = target\.parentElement\?\.querySelector\("ins\.iCheck-helper"\);/);
  assert.match(core, /\(iCheckHelper \|\| label \|\| target\)\.click\(\);/);
});
