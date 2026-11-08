// Trợ lý hộ kinh doanh (thành lập hộ kinh doanh bằng hỏi đáp): khoá các mảnh extension BE cần (capability
// supportsHkdTroLy) — contract regex trên source, dễ bị merge nuốt.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const strip = (src) => src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const sidebar = strip(fs.readFileSync(path.join(__dirname, "..", "sidebar.js"), "utf8"));
const business = strip(fs.readFileSync(
  path.join(__dirname, "..", "content", "procedures", "business-registration.js"), "utf8"));

test("sidebar khai capability supportsHkdTroLy", () => {
  assert.match(sidebar, /supportsHkdTroLy: true/);
});

test("thẻ đồng ý vẽ nút không có tờ khai khi BE gửi no_docs_label và gửi noDocs", () => {
  const card = sidebar.slice(sidebar.indexOf("function renderConsentForm"), sidebar.indexOf("function markConsentVerbal"));
  assert.match(card, /card\.no_docs_label \? `<button type="button" class="chip cnodocs" disabled>/);
  assert.match(card, /\$noDocs\.disabled = \$accept\.disabled/, "cùng điều kiện tích ô như nút Đồng ý");
  assert.match(card, /noDocs \? \{ noDocs: true \} : \{\}/);
  assert.match(card, /finish\(true, card\.no_docs_label, null, true\)/);
});

test("trang chủ hộ chỉ sao chép tài khoản khi có __copyAccount và không xoá ô nhân thân", () => {
  assert.match(business, /function applyOwnerFromDossier\(fields, keepMissing = false\)/);
  assert.match(business, /if \(keepMissing && !source\) continue;/);
});

test("trang thành viên hộ gia đình: tạo lần lượt, bỏ người đã có, có trần đếm", () => {
  assert.match(business, /"thong-tin-ve-thanh-vien": "Thông tin về thành viên"/);
  const handler = business.slice(business.indexOf("async function handleMembersPage"),
    business.indexOf("async function handleAddressCascadePage"));
  assert.match(handler, /st\.memberTries > members\.length \* 4 \+ 4/);
  assert.match(handler, /InformationOfMembers\\\.aspx/);
  assert.match(handler, /\[name="ctl00\$C\$btnNew"\]/);
  assert.match(handler, /existing\.includes\(idOf\(fields\)\)/);
  assert.match(business, /st\.memberTries = 0; st\.memberSkip = \[\]; st\.memberIndex = -1;/);
});

test("khối Thông tin Ủy quyền: bỏ qua khi menu không có, có thì chỉ bấm Lưu", () => {
  assert.match(business, /"thong-tin-uy-quyen": "Thông tin Ủy quyền"/);
  assert.match(business, /targetKey === AUTH_PAGE_KEY && _det\.pageKey !== targetKey\s*&& !findBusinessPageLink/);
  assert.match(business, /if \(targetKey === AUTH_PAGE_KEY\) \{[\s\S]*?clickSaveDetectReload\(authSave\)/);
});

test("đi từng khối: sidebar chuyển hkd_open_block / hkd_focus / hkd_fill xuống trang, báo hkd_arrived", () => {
  assert.match(sidebar, /a\.type === "hkd_open_block" \|\| a\.type === "hkd_focus" \|\| a\.type === "hkd_fill"/);
  assert.match(sidebar, /hkd_open_block: "hkdOpenBlock", hkd_focus: "hkdFocus", hkd_fill: "hkdFill"/);
  assert.match(sidebar, /__event:hkd_arrived:/);
  assert.match(sidebar, /businessPageKey: c\.businessPageKey \|\| ""/);
  assert.match(sidebar, /\$\{ctx\.businessPageKey \|\| ""\}/, "đổi khối phải đổi chữ ký trang để báo BE");
  assert.match(sidebar, /String\(a\.type \|\| ""\)\.startsWith\("hkd_"\)/, "không dựng card chờ khi đi từng khối");
});

test("adapter HkdOnline: mở khối, tô ô đang hỏi, điền ngay (sao chép tài khoản, địa chỉ tỉnh → xã)", () => {
  const adapter = strip(fs.readFileSync(
    path.join(__dirname, "..", "content", "business-registration-adapter.js"), "utf8"));
  assert.match(adapter, /msg\?\.action === "hkdOpenBlock"/);
  assert.match(adapter, /msg\?\.action === "hkdFocus"/);
  assert.match(adapter, /msg\?\.action === "hkdFill"/);
  assert.match(adapter, /menu\.length >= 5 && !H\.findBusinessPageLink/, "chỉ báo thiếu khối khi menu đã dựng");
  assert.match(adapter, /btnIS_SIGNER/);
  assert.match(adapter, /H\.fillAddressCascade\?\.\(address\)/);
  assert.match(business, /H\.goToBusinessPageByKey = goToBusinessPageByKey;/);
  const content = strip(fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8"));
  assert.match(content, /businessPageKey,/);
});

test("mở khối qua menu (trang reload): adapter nhớ khối, tải xong báo sidebar hkdArrived tới khi có xác nhận", () => {
  const adapter = strip(fs.readFileSync(
    path.join(__dirname, "..", "content", "business-registration-adapter.js"), "utf8"));
  assert.match(adapter, /await storageSet\(HKD_OPEN_KEY, \{ page, at: Date\.now\(\) \}\)/,
    "cờ khối ở chrome.storage: jquery.dirrty của cổng xoá sessionStorage mỗi lần postback");
  assert.doesNotMatch(adapter, /sessionStorage\.(set|get)Item\(HKD_OPEN_KEY/);
  assert.match(adapter, /type: "hkdArrived", page: pending/);
  assert.match(adapter, /else if \(tries < 60\) setTimeout\(send, 700\)/);
  assert.match(adapter, /setTimeout\(hkdReportArrival, 400\)/);
  assert.match(sidebar, /msg\?\.type !== "hkdArrived"[\s\S]{0,120}sendResponse\(\{ ok: true \}\)/);
});

test("rảnh tay: không mở mic khi bot đang mở / lưu khối HkdOnline (nhớ qua reload)", () => {
  assert.match(sidebar, /types\.includes\("hkd_open_block"\) \|\| types\.includes\("start_business_registration"\)\) busy = true/);
  assert.match(sidebar, /types\.includes\("hkd_focus"\) \|\| \(d\.chips \|\| \[\]\)\.length \|\| d\.state === "done"\) busy = false/);
  assert.match(sidebar, /\$steps\?\.dataset\.state === "running" \|\| hkdBusy\(\);/);
  assert.match(sidebar, /if \(!opts\?\.noTts\) updateHkdBusy\(d\);/);
});

test("khối người nộp: sao chép tài khoản, so với chủ hộ, báo BE hkd_copied; nơi ở người nộp thay lấy từ câu trả lời", () => {
  const adapter = strip(fs.readFileSync(
    path.join(__dirname, "..", "content", "business-registration-adapter.js"), "utf8"));
  assert.match(adapter, /f\?\.name === "__copySubmitter"/);
  assert.match(adapter, /btn: "ctl00\$C\$btnIS_SIGNER"/);
  // Cùng có số định danh thì chỉ so số — trùng tên khác số là hai người.
  assert.match(adapter, /if \(copied && id && ownerId\) same = id === ownerId;\s*else if \(copied && name && ownerName\) same = name === ownerName;/);
  assert.doesNotMatch(adapter, /\|\| \(!!name && name === ownerName\)/);
  assert.match(sidebar, /a\.type === "hkd_fill" && res && "copied" in res/);
  assert.match(sidebar, /__event:hkd_copied:/);
  const fn = business.slice(business.indexOf("function submitterAddressFields"), business.indexOf("function areaFold"));
  assert.ok(fn.indexOf("applicantAddressFields(plan.other)") < fn.indexOf("identityCard && identityCard.diaChi"),
    "nơi ở công dân khai đứng trước địa chỉ dò từ CCCD");
});

test("sao chép tài khoản reload cả trang: nhớ yêu cầu ở chrome.storage, tải xong so chủ hộ rồi báo hkdCopied", () => {
  const adapter = strip(fs.readFileSync(
    path.join(__dirname, "..", "content", "business-registration-adapter.js"), "utf8"));
  const copy = adapter.slice(adapter.indexOf("async function hkdCopyAccount"), adapter.indexOf("async function hkdReportCopy"));
  assert.ok(copy.indexOf("storageSet(HKD_COPY_KEY") < copy.indexOf("btn.click()"), "ghi cờ TRƯỚC khi bấm");
  assert.match(adapter, /setTimeout\(hkdReportCopy, 450\)/);
  assert.match(adapter, /type: "hkdCopied", page: saved\.page/);
  assert.match(adapter, /btn: "ctl00\$C\$OWN_PCtl\$btnIS_SIGNER"/, "khối chủ hộ cũng reload khi sao chép");
  assert.match(adapter, /ctl00_LV2_LblFullNameValue/, "tên người đăng nhập để hỏi chủ hộ có phải là người đó");
  assert.match(sidebar, /res\.accountName \? \{ accountName: res\.accountName \}/);
  assert.match(sidebar, /msg\?\.type !== "hkdCopied"[\s\S]{0,80}sendResponse\(\{ ok: true \}\)/);
});

test("điền / trỏ ô hộ kinh doanh chạy nối đuôi ở nền, không giữ busy (câu gõ ngay sau câu hỏi không bị bỏ)", () => {
  const branch = sidebar.slice(sidebar.indexOf('a.type === "hkd_open_block" || a.type === "hkd_focus"'),
    sidebar.indexOf('a.type === "prepare_business_registration"'));
  assert.match(branch, /hkdChain = hkdChain\.then\(async \(\) => \{/);
  assert.doesNotMatch(branch.split("hkdChain = hkdChain.then")[0], /await sendToContent/, "không await trong runActions");
  assert.match(sidebar, /a\.type === "start_business_registration" && a\.pages\) \{\s*await hkdChain;/);
});

test("kiểm trùng tên hộ kinh doanh: gọi API của nút Kiểm tra trùng tên, đọc HTML bằng DOMParser, báo hkd_name_checked", () => {
  const adapter = strip(fs.readFileSync(
    path.join(__dirname, "..", "content", "business-registration-adapter.js"), "utf8"));
  assert.match(adapter, /HOUSEHOLDName\.aspx\/\$\{foreign \? "GetExistNameF" : "GetExistName"\}/);
  assert.match(adapter, /new DOMParser\(\)\.parseFromString/);
  assert.doesNotMatch(adapter.slice(adapter.indexOf("async function hkdCheckName")), /\.innerHTML\s*=/);
  assert.match(adapter, /msg\?\.action === "hkdCheckName"/);
  assert.match(sidebar, /supportsHkdCheckName: true/);
  assert.match(sidebar, /a\.type === "hkd_check_name"/);
  assert.match(sidebar, /__event:hkd_name_checked:/);
});

test("trang reload giữa lúc điền: không vẽ lại thẻ danh sách giấy tờ (chỉ cập nhật thẻ đang có)", () => {
  const fn = sidebar.slice(sidebar.indexOf("function renderDocProgress"), sidebar.indexOf("const rows = (p.docs || [])"));
  assert.match(fn, /if \(!wrap && DOCS_DONE_STATES\.has\(lastState\)\) return;/);
  assert.match(sidebar, /const DOCS_DONE_STATES = new Set\(\["filling", "reviewing", "attaching", "choosing_attach_mode", "done"\]\)/);
});

test("bước Chuẩn bị: Khối dữ liệu → Chuẩn bị, nhớ bước qua reload, đọc lỗi notificationPanel; KHÔNG bấm Nộp", () => {
  const adapter = strip(fs.readFileSync(
    path.join(__dirname, "..", "content", "business-registration-adapter.js"), "utf8"));
  const block = adapter.slice(adapter.indexOf("const HKD_PREP_KEY"), adapter.indexOf("async function hkdFill"));
  assert.match(block, /ctl00\$C\$btnAccept/);
  assert.match(block, /\.notificationPanel a\[id\$="_TextLink"\]/);
  assert.ok(block.indexOf('storageSet(HKD_PREP_KEY') < block.indexOf("hkdAcceptBtn().click()"), "ghi bước trước khi bấm");
  assert.doesNotMatch(block, /BtnSave"\]'?\)?\.click|BtnSave[^;]*\.click\(/, "không bao giờ bấm Nộp hồ sơ");
  assert.match(adapter, /setTimeout\(hkdReportPrepare, 500\)/);
  assert.match(sidebar, /supportsHkdPrepare: true/);
  assert.match(sidebar, /msg\?\.type !== "hkdPrepared"/);
  assert.match(sidebar, /a\.type === "hkd_prepare"/);
});

test("khối người đã lưu (chế độ xem): tích Sửa đổi dữ liệu, nhớ ô cần điền qua reload rồi điền tiếp", () => {
  const adapter = strip(fs.readFileSync(
    path.join(__dirname, "..", "content", "business-registration-adapter.js"), "utf8"));
  const fn = adapter.slice(adapter.indexOf("async function hkdEnableEdit"), adapter.indexOf("async function hkdResumeFill"));
  assert.match(fn, /\$\{prefix\}PERSONChange/);
  assert.ok(fn.indexOf("storageSet(HKD_REFILL_KEY") < fn.indexOf("box.click()"), "nhớ ô cần điền TRƯỚC khi bấm");
  assert.match(adapter, /if \(await hkdEnableEdit\(real\)\) return \{ ok: true, reloading: true \};/);
  assert.match(adapter, /setTimeout\(hkdResumeFill, 600\)/);
  assert.match(business, /nameFilled: \(\) => !!readPersonControlRaw\("ctl00_C_PERSCtl_FULL_NAMEFld"\)/,
    "chế độ sửa (tên trong ô nhập) vẫn là đã sao chép");
});

test("nút Nộp hồ sơ: chỉ bấm nút Nộp trên Trang xác nhận khi BE gửi hkd_submit, trả lời trước khi confirm() chặn trang", () => {
  const adapter = strip(fs.readFileSync(
    path.join(__dirname, "..", "content", "business-registration-adapter.js"), "utf8"));
  const handler = adapter.slice(adapter.indexOf('msg?.action === "hkdSubmit"'), adapter.indexOf('msg?.action === "hkdOpenBlock"'));
  assert.ok(handler.indexOf("sendResponse") < handler.indexOf("setTimeout(hkdSubmit"), "trả lời trước khi bấm");
  assert.equal((adapter.match(/BtnSave"\]'\)/g) || []).length, 3, "BtnSave chỉ ở hkdSubmit, handler và đọc kết quả Chuẩn bị");
  assert.match(sidebar, /supportsHkdSubmit: true/);
  assert.match(sidebar, /a\.type === "hkd_submit"/);
});
