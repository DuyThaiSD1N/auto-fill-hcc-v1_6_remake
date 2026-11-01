// Cổng Bắc Ninh (dichvucong.bacninh.gov.vn): luồng 4 tab cùng trang do BE điều phối (chat/bac_ninh, cờ
// supportsBacNinhTabFlow) — chuyển tab bằng hàm Liferay của cổng (MAIN world), báo tab đang mở, điền khối người ủy
// quyền ở tab "Chọn cơ quan tiếp nhận", bổ sung ô ở tab ủy quyền / tab đơn, chọn nơi nhận kết quả, bấm Nộp hồ sơ.
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
const fillCore = read("content/fill-core.js");
const engine = read("content/fill-bacninh.js");
const flow = read("content/bacninh/tab-flow.js");
const review = read("content/bacninh/field-review.js");

test("manifest: phần Bắc Ninh nạp sau engine điền + bộ đọc eForm, hàm chuyển tab chạy trong MAIN world của cổng", () => {
  const manifest = JSON.parse(raw("manifest.json"));
  const js = manifest.content_scripts.find((c) => c.js.includes("content/fill-core.js")).js;
  for (const file of ["content/bacninh/tab-flow.js", "content/bacninh/field-review.js"]) {
    assert.ok(js.indexOf(file) > js.indexOf("content/fill-bacninh.js"), file);
    assert.ok(js.indexOf(file) > js.indexOf("content/field-review.js"), file);
    assert.ok(js.indexOf(file) < js.indexOf("content.js"), file);
  }
  const main = manifest.content_scripts.find((c) => c.js.includes("content/bacninh/tabs-main.js"));
  assert.equal(main.world, "MAIN");
  assert.deepEqual(main.matches, ["https://dichvucong.bacninh.gov.vn/*"]);
});

test("tabs-main gọi Liferay.Portal.Tabs.show đúng namespace + danh sách tab của trang", () => {
  const listeners = {};
  const tabs = ["chondonvitiepnhan", "nhapdondangky", "taithanhphan", "hinhthucnhanketqua"];
  const calls = [];
  const list = {
    getAttribute: () => "_org_bn_hoso_noptructuyen_nhapTab",
    querySelectorAll: () => tabs.map((name) => ({ dataset: { tabName: name } })),
  };
  const window = { Liferay: { Portal: { Tabs: { show: (...args) => calls.push(args) } } } };
  const document = {
    addEventListener: (type, fn) => { listeners[type] = fn; },
    querySelector: (sel) => (sel === 'ul[data-tabs-namespace$="nhapTab"]' ? list : null),
  };
  vm.runInNewContext(raw("content/bacninh/tabs-main.js"), { window, document, console });
  listeners["tlnd-bn-show-tab"]({ detail: "hinhthucnhanketqua" });
  listeners["tlnd-bn-show-tab"]({ detail: "khong-co" });
  assert.equal(JSON.stringify(calls),
    JSON.stringify([["_org_bn_hoso_noptructuyen_nhapTab", tabs, "hinhthucnhanketqua"]]));
});

test("activateBacNinhTab gọi hàm của cổng trước, giữ hai đường dự phòng click / tự đổi class", () => {
  const body = engine.slice(engine.indexOf("async function activateBacNinhTab"));
  const event = body.indexOf('new CustomEvent("tlnd-bn-show-tab", { detail: name })');
  assert.ok(event > 0);
  assert.ok(body.indexOf("link.click()") > event);
  assert.ok(body.indexOf('sec.classList.toggle("hide", !isTarget)') > event);
});

test("lệnh điền mở đúng tab BE gửi (khối ủy quyền ở tab đầu), thiếu thì tab đơn như cũ", () => {
  assert.match(fillCore, /H\.activateBacNinhTab\(String\(msg\.bnTab \|\| ""\) \|\| "nhapdondangky"\)/);
  assert.match(sidebar, /formSnapshot: a\.formSnapshot \|\| null,\s*bnTab: a\.bnTab \|\| "",/);
});

test("page_status / lệnh nói mang bnTab; watcher báo khi tab đổi", () => {
  assert.match(content, /bnTab: \(window\.__TLND__ && typeof window\.__TLND__\.bacNinhTab === "function"\)/);
  assert.match(sidebar, /bnTab: Number\(c\.bnTab\) \|\| 0,/);
  assert.match(sidebar, /bnTab: Number\(ctx\?\.bnTab\) \|\| 0,/);
  assert.match(sidebar, /: lastReplyData\?\.bac_ninh \? Number\(ctx\.bnTab\) \|\| 0 : 0;/);
});

test("sidebar khai cờ, chạy lệnh bn_* ngoài lượt ask(), đối chiếu bnTab sau khi chuyển", () => {
  assert.match(sidebar, /supportsBacNinhTabFlow: true,/);
  assert.match(sidebar, /a\.type === "bn_tab"\) \{\s*setTimeout\(\(\) => \{ void runBnTab\(a\); \}, 0\);/);
  assert.match(sidebar, /a\.type === "bn_result"\) \{\s*setTimeout\(\(\) => \{ void runBnResult\(a\); \}, 0\);/);
  assert.match(sidebar, /a\.type === "bn_submit"\) \{\s*setTimeout\(\(\) => \{ void runBnSubmit\(\); \}, 0\);/);
  assert.match(sidebar, /tab = Number\(ctx\?\.bnTab\) \|\| 0;/);
  assert.match(sidebar, /__action:bn_tab_report:/);
});

test("tab-flow: chỉ trang 4 tab Bắc Ninh trả lời; nơi nhận theo value radio; nộp ở tab cuối rồi đọc #validateHoSo", () => {
  assert.match(flow, /location\.hostname === "dichvucong\.bacninh\.gov\.vn"/);
  assert.match(flow, /input\[type="radio"\]\[name="\$\{PFX\}noiNhanKetQua"\]/);
  // Đọc nơi nhận trước khi đổi tab; nút Nộp ở tab cuối của trang (4 tab: nhận kết quả; 2 tab: đính kèm).
  assert.ok(flow.indexOf("const state = resultState();") < flow.indexOf("for (const name of [TABS[3], TABS[2]])"));
  assert.match(flow, /document\.getElementById\(`\$\{PFX\}nopTrucTuyen`\)/);
  assert.match(flow, /#\$\{PFX\}validateHoSo li/);
});

test("bộ đọc ô Bắc Ninh: chỉ tab khối ủy quyền / tab đơn, bỏ ô tích, khoá eform-element làm tên, select2 điền bằng engine", () => {
  assert.match(review, /const ourPage = \(\) => tab\(\) === 1 \|\| tab\(\) === 2 \|\| !!accountRoot\(\);/);
  assert.match(review, /thongTinChuHoSoDoiTuongKhacDv/);
  assert.match(review, /dvNhapDonDangKy/);
  assert.match(review, /\["hidden", "file", "checkbox", "radio", "button"\]\.includes\(type\)/);
  assert.match(review, /await H\.fillFormBacNinh\(\[\{ name: slot\.fillName, comp: "bn-select", value \}\]\);/);
  assert.match(review, /return !t \|\| t\.startsWith\("chon "\) \|\| t === "chua co thong tin";/);
});

test("cơ quan tiếp nhận: đọc / chọn select2 donViTiepNhanId bằng engine Bắc Ninh; chọn tay trên trang thì watcher báo", () => {
  assert.match(flow, /document\.getElementById\(`\$\{PFX\}donViTiepNhanId`\)/);
  assert.match(flow, /await H\.fillFormBacNinh\(\[\{ name: "donViTiepNhanId", comp: "bn-select", value \}\]\);/);
  assert.match(content, /bnAgency: \(window\.__TLND__ && typeof window\.__TLND__\.bacNinhAgency === "function"\)/);
  assert.match(sidebar, /bnAgency: String\(c\.bnAgency \|\| ""\),/);
  assert.match(sidebar, /const sig = `[^`]*\|\$\{ctx\.bnAgency \|\| ""\}\|/);
  assert.match(sidebar, /a\.type === "bn_agency"\) \{\s*setTimeout\(\(\) => \{ void runBnAgency\(a\); \}, 0\);/);
  assert.match(sidebar, /__action:bn_agency_report:/);
});

test("nơi nhận kết quả: đọc / chọn điểm tiếp nhận; chưa chọn điểm thì không bấm Nộp hồ sơ", () => {
  assert.match(flow, /name="\$\{PFX\}noiNhanKetQuadiemTiepNhanId"/);
  assert.match(flow, /if \(state\.points\.length && !state\.point\) return \{ clicked: false, missing: "point", \.\.\.state \};/);
  assert.match(sidebar, /action: "bnResult", value: a\.value \|\| "", point: a\.point \|\| ""/);
  assert.match(sidebar, /missing: res\?\.missing \|\| "",/);
});

test("đính kèm Bắc Ninh: chờ cổng hiện tên tệp tối đa 15 giây rồi mới tô xanh / báo lỗi tô đỏ", () => {
  const engineRaw = read("content/fill-bacninh.js");
  assert.match(engineRaw, /const LANDED_WAIT_MS = 15000;/);
  assert.match(engineRaw, /await waitLanded\(pending\);/);
  assert.match(engineRaw, /H\.markFilled && H\.markFilled\(p\.cell\);/);
  assert.match(engineRaw, /H\.markUnfilled && H\.markUnfilled\(p\.cell\);/);
  assert.match(engineRaw, /querySelectorAll\("li\.list-group-item"\)/);
  // Lượt đính lại không bỏ qua dòng chỉ còn input.files của lần gán hỏng.
  assert.doesNotMatch(engineRaw, /if \(input && input\.files && input\.files\.length\) return true;/);
});

test("bộ đọc ô Bắc Ninh: tiêu đề mục lấy cả đoạn <p>, trả lời ô dưới thì ghi kèm ô tiêu đề (MIRROR)", () => {
  assert.match(review, /root\.querySelectorAll\("label, p"\)/);
  assert.match(review, /\(rules\?\.mirror \|\| \[\]\)/);
});

test("bưu chính: đọc / tích hai ô gửi hồ sơ / nhận kết quả qua bưu điện, chưa tích ô nào thì không bấm Nộp", () => {
  assert.match(flow, /input\.chkNhanKetQua\[type=\\"checkbox\\"\]/);
  assert.match(flow, /const want = msg\.postal\.includes\(postalName\(box\)\);/);
  assert.match(flow, /return \{ clicked: false, missing: "postal", \.\.\.state \};/);
  assert.match(sidebar, /postal: Array\.isArray\(a\.postal\) \? a\.postal : null,/);
});

test("điền xong đơn Bắc Ninh thì đưa trang về đầu", () => {
  assert.match(fillCore, /if \(formKind === "bacninh"\) window\.scrollTo\(\{ top: 0, behavior: "smooth" \}\);/);
});

test("trang hoàn thiện tài khoản: nhận ra trang, bấm Lưu đọc lỗi; bộ đọc ô chỉ tab Thông tin chung, ô * bắt buộc", () => {
  assert.match(flow, /form\[id\$="_frmCongDanAction"\]\[id\*="_taikhoan_sso_vneid_"\]/);
  assert.match(flow, /if \(action === "bnAccountSave"\) \{/);
  assert.match(content, /bnAccountForm: !!\(window\.__TLND__ && typeof window\.__TLND__\.bacNinhAccountForm === "function"/);
  assert.match(sidebar, /bnAccountForm: !!c\.bnAccountForm,/);
  assert.match(sidebar, /a\.type === "bn_account_save"\) \{\s*setTimeout\(\(\) => \{ void runBnAccountSave\(\); \}, 0\);/);
  assert.match(sidebar, /clicked: res \? !!res\.clicked : true, message: res\?\.message \|\| "", gone: !res,/);
  assert.match(review, /li\[data-tab-name="thongtinchung"\]/);
  assert.match(review, /marker: rawLabel\(el\)\.includes\("\*"\),/);
  assert.match(review, /if \(!shown\(box\) \|\| el\.disabled \|\| el\.readOnly\) continue;/);
  assert.match(review, /slot\.required = need\.has\(slot\.name\) \|\| !!slot\.marker;/);
});
