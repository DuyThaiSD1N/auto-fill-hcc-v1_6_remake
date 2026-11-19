// Thông báo lưu trú (Cổng DVC Bộ Công an): danh sách người lưu trú thêm từng người qua modal "Thêm mới người lưu trú".
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const read = (file) => fs.readFileSync(path.join(__dirname, "..", file), "utf8").replace(/^\s*\/\/.*$/gm, "");
const core = read("content/fill-core.js");
const content = read("content.js");
const sidebar = read("sidebar.js");
const FILE_STD = "content/fill-core.js";

test("vòng điền chuẩn giao comp bca-guest-list cho engine modal, không coi là ô thường", () => {
  assert.match(core, /f\.comp === "bca-guest-list"\)\s*\{\s*await fillBcaGuestList\(f, result\);\s*continue;/);
});

test("mỗi người: mở modal bằng nút Thêm mới, điền theo id, Lưu, chỉ tính thành công khi bảng có người đó", () => {
  const fn = core.slice(core.indexOf("async function fillBcaGuest("), core.indexOf("async function fillBcaGuestList("));
  assert.match(fn, /#btnAddPersonLT/);
  assert.match(fn, /btnSaveNLT/);
  assert.match(fn, /!bcaVisible\(modal\) && bcaGuestListed\(guest\)/);
  // Ngày đi qua API datepicker ở MAIN world (gõ chữ làm lịch treo).
  assert.match(fn, /bcaSetPickerDates\(dates\)/);
  assert.match(core, /action: "bcaSetDatepickers"/);
});

test("lỗi ở một người thì dừng, không mở modal chồng; người đã có trong bảng không thêm lại", () => {
  const fn = core.slice(core.indexOf("async function fillBcaGuestList("), core.indexOf("async function retryStandardAreaSelects("));
  assert.match(fn, /if \(bcaGuestListed\(guest\)\)/);
  assert.match(fn, /result\.notFound\.push[\s\S]*return;/);
});

test("người khai là người lưu trú thì tích ô của cổng, ô bị khoá không ghi đè", () => {
  assert.match(core, /chkIS_CHANGED_PERSON/);
  assert.match(core, /txtIDENTIFIER_NUMBER/);
  const fn = core.slice(core.indexOf("async function bcaFillGuestField("), core.indexOf("async function fillBcaGuest("));
  assert.match(fn, /if \(el\.disabled\) return true;/);
});

test("trang lưu trú được nhận là form standard và khối cơ quan nhận cặp id accomStay_*", () => {
  assert.match(core, /document\.getElementById\("btnAddPersonLT"\)\)\)\s*\{\s*return "standard";/);
  assert.match(content, /\["accomStay_cboPROVINCE_ID", "accomStay_cboADDRESS_ID"\]/);
  assert.match(content, /\["cboRECEIVE_ADDR_CITY_CODE", "cboRECEIVE_ADDR_VILLAGE_CODE"\]/);
});

test("sidebar khai cờ supportsBcaGuestList", () => {
  assert.match(sidebar, /supportsBcaGuestList: true/);
});

test("cơ quan thực hiện: một ô bca-agency, chọn Tỉnh rồi chờ danh sách Xã đổi mới chọn Xã, đã chọn thì giữ", () => {
  const src = fs.readFileSync(path.join(__dirname, "..", FILE_STD), "utf8");
  assert.match(src, /f\.comp === "bca-agency"\)\s*\{\s*await fillBcaAgencyField\(f, result\);\s*continue;/);
  const fn = src.slice(src.indexOf("async function fillBcaAgencyField("), src.indexOf("async function fillBcaGuestList("));
  assert.match(fn, /accomStay_cboPROVINCE_ID/);
  assert.match(fn, /accomStay_cboADDRESS_ID/);
  assert.match(fn, /if \(f\.onlyIfEmpty && picked\(city\) && \(provinceOnly \|\| picked\(ward\)\)\) \{/);
  assert.match(fn, /signature\(\) !== before/);
});

test("thường trú: ô cơ quan theo cặp id BE gửi + chờ readySelect; bảng dòng bca-rows bấm Thêm ở dòng cuối", () => {
  const src = fs.readFileSync(path.join(__dirname, "..", FILE_STD), "utf8");
  assert.match(src, /document\.getElementById\(f\.value\?\.cityId \|\| "accomStay_cboPROVINCE_ID"\)/);
  assert.match(src, /f\.value\?\.readySelect/);
  assert.match(src, /f\.comp === "bca-rows"\)\s*\{\s*await fillBcaRows\(f, result\);\s*continue;/);
  const fn = src.slice(src.indexOf("async function fillBcaRows("), src.indexOf("async function fillBcaGuestList("));
  assert.match(fn, /buttons\[buttons\.length - 1\]\?\.click\(\)/);
});

test("cấp đổi căn cước: cặp Công an tỉnh → xã + ô địa chỉ trạm, bỏ tiền tố \"Công an\", cờ supportsBcaCanCuoc", () => {
  assert.match(content, /\["cboORGTinh", "cboORGXa", "cboDiaChiTram"\]/);
  assert.match(content, /const bcaBare = \(s\) => bcaFold\(s\)\.replace\(\/\^cong an\\s\+\/, ""\)/);
  assert.match(content, /if \(options\.length === 1\) bcaSetSelect\(ready, options\[0\]\);/);
  assert.match(sidebar, /supportsBcaCanCuoc: true/);
  const core = read("content/fill-core.js");
  assert.match(core, /document\.getElementById\("txtFULLNAME_NDN"\)/);
  const fn = core.slice(core.indexOf("async function fillBcaAgencyField("), core.indexOf("async function fillBcaRows("));
  assert.match(fn, /const provinceOnly = !wardName;/);
  assert.match(fn, /f\.value\?\.readyPick && options\.length === 1/);
});

test("thường trú: khối cơ quan nhận cặp id _ID, cờ supportsBcaThuongTru, nút Thêm dòng cuối + ô txtNAME_FILE", () => {
  assert.match(content, /\["cboRECEIVE_ADDR_CITY_ID", "cboRECEIVE_ADDR_VILLAGE_ID"\]/);
  assert.match(sidebar, /supportsBcaThuongTru: true/);
  const attach = read("content/attach-core.js");
  assert.match(attach, /a\[title="Thêm"\], #add_gtdk/);
  assert.match(attach, /input\[id\^="txtNAME_FILE"\]/);
});

test("điều chỉnh thông tin cư trú: bcaPlainTable lấy bảng đang hiện, rowFields điền Loại / Số lượng / Ghi chú của dòng", () => {
  const attach = read("content/attach-core.js");
  const fn = attach.slice(attach.indexOf("async function attachFilesByBcaPlan("), attach.indexOf("async function attachFilesByPlan("));
  assert.match(fn, /\(bcaPlainTable && bcaVisibleTable\(\)\) \|\| await bcaOpenGroup\(groupIndex, groupLabel \|\| ""\)/);
  assert.match(fn, /if \(ok\) bcaFillRowFields\(row, item\.rowFields\);/);
  const fill = attach.slice(attach.indexOf("function bcaFillRowFields("), attach.indexOf("function bcaAddRowButton("));
  assert.match(fill, /select\[id\^="cboKIND_OF_FILE"\]/);
  assert.match(fill, /\["txtNUM_OF_DOC", fields\.count\], \["txtNOTE_OF_DOC", fields\.note\]/);
  assert.match(fill, /\(!current \|\| current === "0"\)/);
  const gate = attach.slice(attach.indexOf("function hasAttachmentTarget("), attach.indexOf("function hasAttachmentTarget(") + 600);
  assert.match(gate, /#tblGiayToDinhKem/);
  assert.match(fn, /const checkbox = bcaRowCheckbox\(row\);/);
  assert.match(attach, /input\[type="checkbox"\]\[id\^="chkIS_COMPULSORY"\]/);
  assert.match(attach, /!box\.closest\("td\.bs-checkbox"\)/);
});

const RELATION_SRC = fs.readFileSync(path.join(__dirname, "..", "content/fill-core.js"), "utf8");

// Cấp căn cước dưới 14 tuổi: ô "Mối quan hệ của người kê khai…" chọn theo TÀI KHOẢN đăng nhập (Phần I), không theo giấy.
function runRelation(src, account, value) {
  const fn = src.slice(src.indexOf("async function fillBcaRelationField("), src.indexOf("// Bảng dòng lặp của cổng Bộ Công an"));
  const classes = new Set(["autofill-filled"]);
  const select = { classList: { add: (c) => classes.add(c), remove: (c) => classes.delete(c) } };
  const els = { cboRELATIONSHIP_WITH_NDN: select, txtFULLNAME_NDN: { value: account.name },
    txtIDENTIFY_NUMBER_NDN: { value: account.id } };
  const picked = [];
  const deps = {
    document: { getElementById: (id) => els[id] || null },
    waitFor: async (cond) => cond(),
    bcaGuestFold: (s) => String(s || "").replace(/Đ/g, "D").replace(/đ/g, "d").normalize("NFD")
      .replace(/[̀-ͯ]/g, "").replace(/\s+/g, " ").trim().toLowerCase(),
    fillStandardSelect: (_el, v) => { picked.push(v); return true; },
    standardMarkTarget: (el) => el,
    console: { log() {} },
  };
  const run = new Function(...Object.keys(deps), `${fn}; return fillBcaRelationField;`)(...Object.values(deps));
  const result = { filled: 0, notFound: [] };
  return run({ name: "cboRELATIONSHIP_WITH_NDN", comp: "bca-relation", value }, result)
    .then(() => ({ picked: picked[0], yellow: classes.has("autofill-default"), result }));
}

const RELATION_VALUE = {
  target: "cboRELATIONSHIP_WITH_NDN", fallback: "Người đại diện hợp pháp",
  people: [{ relation: "Mẹ", name: "TRẦN THỊ HOA", id: "012190000002" },
    { relation: "Cha", name: "LÊ VĂN NAM", id: "012088000003" }],
};

test("bca-relation: tài khoản không phải cha/mẹ trên giấy → Người đại diện hợp pháp, không tô vàng", async () => {
  const r = await runRelation(RELATION_SRC, { name: "PHẠM VĂN KHÁCH", id: "001204000001" }, RELATION_VALUE);
  assert.strictEqual(r.picked, "Người đại diện hợp pháp");
  assert.ok(!r.yellow);
});

test("bca-relation: trùng số định danh / họ tên tài khoản → Mẹ / Cha; trùng tên khác số thì không tính", async () => {
  let r = await runRelation(RELATION_SRC, { name: "Ai Đó", id: "012190000002" }, RELATION_VALUE);
  assert.strictEqual(r.picked, "Mẹ");
  assert.ok(!r.yellow);
  r = await runRelation(RELATION_SRC, { name: "Lê Văn Nam", id: "" }, RELATION_VALUE);
  assert.strictEqual(r.picked, "Cha");
  r = await runRelation(RELATION_SRC, { name: "Lê Văn Nam", id: "012088999999" }, RELATION_VALUE);
  assert.strictEqual(r.picked, "Người đại diện hợp pháp");
  // Phần I chưa đổ tài khoản → không chọn bừa.
  r = await runRelation(RELATION_SRC, { name: "", id: "" }, RELATION_VALUE);
  assert.strictEqual(r.picked, undefined);
  assert.strictEqual(r.result.notFound.length, 1);
});

// Cấp căn cước từ đủ 14 tuổi: radio "Đối tượng kê khai" chọn theo TÀI KHOẢN đăng nhập (Phần I), không theo người ký giấy;
// ô khai bcaOtherOnly (khối Phần II) chỉ điền khi tài khoản là người khác.
function runDeclarant(src, account, subject) {
  const fn = src.slice(src.indexOf("async function fillBcaDeclarantField("),
    src.indexOf("// \"Mối quan hệ của người kê khai với người cần cấp căn cước\""));
  const radio = (id) => ({ id, checked: false, disabled: false, click() { this.checked = true; } });
  const els = { txtFULLNAME_NDN: { value: account.name }, txtIDENTIFY_NUMBER_NDN: { value: account.id },
    chkIS_NCC: radio("chkIS_NCC"), chkIS_NOT_NCC: radio("chkIS_NOT_NCC"), divCheck_NDN: {} };
  const deps = {
    document: { getElementById: (id) => els[id] || null },
    waitFor: async (cond) => cond(),
    bcaVisible: (el) => !!el,
    bcaGuestFold: (s) => String(s || "").replace(/Đ/g, "D").replace(/đ/g, "d").normalize("NFD")
      .replace(/[̀-ͯ]/g, "").replace(/\s+/g, " ").trim().toLowerCase(),
    console: { log() {} },
  };
  const run = new Function(...Object.keys(deps), `${fn}; return fillBcaDeclarantField;`)(...Object.values(deps));
  const result = { filled: 0, notFound: [] };
  const value = { selfId: "chkIS_NCC", otherId: "chkIS_NOT_NCC", otherBlock: "divCheck_NDN", subject };
  return run({ name: "radIsNCC", comp: "bca-declarant", value }, result)
    .then((decision) => ({ decision, self: els.chkIS_NCC.checked, other: els.chkIS_NOT_NCC.checked, result }));
}

test("bca-declarant: tài khoản là người cần cấp → radio tự khai; người khác → radio khai thay", async () => {
  const subject = { name: "HOÀNG THỊ LAN", id: "012312000001" };
  let r = await runDeclarant(RELATION_SRC, { name: "Hoàng Thị Lan", id: "012312000001" }, subject);
  assert.deepStrictEqual([r.decision, r.self, r.other], ["self", true, false]);
  r = await runDeclarant(RELATION_SRC, { name: "Hoàng Văn An", id: "012085000002" }, subject);
  assert.deepStrictEqual([r.decision, r.self, r.other], ["other", false, true]);
  // Trùng tên nhưng khác số định danh = người khác.
  r = await runDeclarant(RELATION_SRC, { name: "Hoàng Thị Lan", id: "012312999999" }, subject);
  assert.strictEqual(r.decision, "other");
  // Giấy không có số → so họ tên.
  r = await runDeclarant(RELATION_SRC, { name: "Hoàng Thị Lan", id: "012312000001" }, { name: "HOÀNG THỊ LAN" });
  assert.strictEqual(r.decision, "self");
  // Phần I chưa đổ tài khoản → không chọn bừa, ô Phần II không điền.
  r = await runDeclarant(RELATION_SRC, { name: "", id: "" }, subject);
  assert.strictEqual(r.decision, null);
  assert.strictEqual(r.result.notFound.length, 1);
});

test("vòng điền chuẩn: ô bcaOtherOnly bỏ qua trừ khi bca-declarant chọn khai thay", () => {
  assert.match(RELATION_SRC, /f\.comp === "bca-declarant"\)\s*\{\s*bcaDeclarant = await fillBcaDeclarantField\(f, result\);/);
  assert.match(RELATION_SRC, /if \(f\.bcaOtherOnly && bcaDeclarant !== "other"\) continue;/);
});


// ── Luồng có vòng bổ sung ô + nút Nộp hồ sơ (cờ supportsBcaFlow, content/bca/field-review.js) ──
const bcaReview = read("content/bca/field-review.js");

test("sidebar khai cờ supportsBcaFlow và chuyển lệnh bca_submit xuống trang rồi báo bca_submit_report", () => {
  assert.match(sidebar, /supportsBcaFlow: true/);
  assert.match(sidebar, /a\.type === "bca_submit"\)\s*\{\s*setTimeout\(\(\) => \{ void runBcaSubmit\(a\); \}, 0\);/);
  assert.match(sidebar, /action: "bcaSubmit"/);
  assert.match(sidebar, /__action:bca_submit_report:/);
});

test("manifest nạp bộ đọc ô Bộ Công an sau engine điền và con trỏ dùng chung", () => {
  const manifest = fs.readFileSync(path.join(__dirname, "..", "manifest.json"), "utf8");
  const at = (file) => manifest.indexOf(`"${file}"`);
  assert.ok(at("content/bca/field-review.js") > at("content/fill-core.js"));
  assert.ok(at("content/bca/field-review.js") > at("content/field-review.js"));
});

test("bộ đọc ô Bộ Công an: chỉ trang chính dancuquocgia, cùng giao thức fieldReview*, điền bằng engine chuẩn", () => {
  assert.match(bcaReview, /const HOST = "dichvucong\.dancuquocgia\.gov\.vn"/);
  assert.match(bcaReview, /window\.top === window/);
  for (const action of ["fieldReviewMark", "fieldReviewNext", "fieldReviewStop", "bcaSubmit"]) {
    assert.ok(bcaReview.includes(`"${action}"`), action);
  }
  assert.match(bcaReview, /H\.fillFormStandard\(\[field\]\)/);
  // select2: tô ô công dân thấy, không tô <select> gốc bị ẩn.
  assert.match(bcaReview, /classList\?\.contains\("select2"\)/);
});

test("ô bắt buộc: dấu * vẽ bằng CSS, * đứng sau nhãn, hoặc cổng báo lỗi dưới ô đều tô đỏ (18/11/2026)", () => {
  // Thông báo lưu trú: "Loại hình cơ sở lưu trú *" bị tô cam vì dấu * không nằm trong chữ nhãn → nộp bị cổng chặn.
  assert.match(bcaReview, /getComputedStyle\(el, pseudo\)\.content/);
  assert.match(bcaReview, /\|\| portalFlagged\(group\[0\] \|\| el, box\)/);
  assert.match(bcaReview, /vui long \(chon\|nhap/);
  // Nhãn lỗi jQuery validate không được lấy làm tên ô.
  assert.match(bcaReview, /\.find\(\(l\) => textOf\(l\) && !isErrorNode\(l\)\)/);
});

test("bổ sung ô: nhãn không phải thẻ label vẫn đọc được chữ trước ô; không bao giờ hỏi bằng tên HTML", () => {
  assert.match(bcaReview, /return looseLabel\(anchor, group\) \|\| \{ text: hintOf\(el\), marked: false \};/);
  assert.match(bcaReview, /label: \(text && !htmlName\(text\) \? text : ""\) \|\| sectionOf\(el\) \|\| "Ô còn trống"/);
  assert.doesNotMatch(bcaReview, /label: text \|\| name,/);
});

test("nút nộp: còn ô bắt buộc hoặc chưa tích cam kết thì không bấm; cổng hỏi xác nhận thì để công dân tự bấm", () => {
  const fn = bcaReview.slice(bcaReview.indexOf("async function submit("), bcaReview.indexOf("chrome.runtime.onMessage"));
  assert.match(fn, /if \(stats\.required\) return \{ clicked: false, missing: \["required"\]/);
  assert.match(fn, /!box\.checked\) \{[\s\S]*missing: \["commit"\]/);
  assert.match(fn, /isConfirm\(shownAlert\)\) return \{ clicked: true, stage: pick\.stage, button, confirm: true \}/);
  // Không tự bấm nút trong hộp xác nhận của cổng.
  assert.doesNotMatch(fn, /shownAlert\.el\.querySelector\([^)]*\)\.click/);
});


test("nút tích ô cam đoan chạy cả khi BE chỉ gửi nhãn ô (trang căn cước), trợ lý tích thì đặt cờ để không báo trùng", () => {
  assert.match(sidebar, /a\.type === "tick_commit" && \(a\.id \|\| a\.label\)/);
  const tick = content.slice(content.indexOf('msg?.action !== "tickCommitBox"'), content.indexOf('msg?.action !== "fillBcaAgency"'));
  assert.match(tick, /window\.__TLND_COMMIT_BY_ASSISTANT__ = true;[\s\S]*box\.click\(\)[\s\S]*__TLND_COMMIT_BY_ASSISTANT__ = false/);
  // Đúng trạng thái muốn rồi thì không click (click nữa là đảo ô).
  assert.match(tick, /if \(box\.checked === want\) \{ sendResponse\(\{ ok: true \}\); return; \}/);
});

test("điền / điền lại tờ khai Bộ Công an: bỏ tích ô cam kết trước khi điền để công dân cam đoan lại", () => {
  // 18/11/2026: bấm "Điền lại thông tin" xong ô cam đoan trên trang vẫn tích.
  const tick = content.slice(content.indexOf('msg?.action !== "tickCommitBox"'), content.indexOf('msg?.action !== "fillBcaAgency"'));
  assert.match(tick, /const want = msg\.checked !== false;/);
  const fill = sidebar.slice(sidebar.indexOf('a.type === "fill_fields" && Array.isArray(a.fields)'),
    sidebar.indexOf('action: "fillFields", fields: a.fields'));
  assert.match(fill, /a\.fieldReview\?\.commitId \|\| a\.fieldReview\?\.commitLabel/);
  assert.match(fill, /action: "tickCommitBox",[\s\S]*checked: false/);
});

test("công dân tự tích / bỏ tích ô cam kết trên trang → sidebar báo commit_result source page", () => {
  assert.match(bcaReview, /__tlnd: "bcaCommitChanged"/);
  assert.match(bcaReview, /window\.__TLND_COMMIT_BY_ASSISTANT__/);
  assert.match(sidebar, /msg\?\.__tlnd !== "bcaCommitChanged"/);
  assert.match(sidebar, /__event:commit_result:\$\{JSON\.stringify\(\{ ok: !!msg\.checked, source: "page" \}\)\}/);
});


test("trang căn cước khác bộ id người kê khai vẫn là form standard; câu chọn cơ quan không làm rỗng formKind", () => {
  // 18/11/2026: cấp căn cước từ đủ 14 tuổi — formKind rỗng → trợ lý nói "chưa biết trang đang ở bước nào".
  assert.match(core, /document\.getElementById\("cboORGTinh"\)\s*\|\| document\.querySelectorAll\('input\[id\^="txt"\], select\[id\^="cbo"\]'\)\.length >= 3/);
  assert.match(content, /const agencyBlock = !maeHost && location\.hostname !== "dichvucong\.dancuquocgia\.gov\.vn"/);
  // Lượt bấm "Đã đưa đủ" mang cờ khối cơ quan → BE coi là bước kê khai.
  assert.match(sidebar, /bcaAgencyBlock: !!ctx\?\.bcaAgencyBlock,/);
});


// ── Cấp hộ chiếu 1.001456 (18/11): ô bootstrap-select chọn như người dùng + ô tích iCheck bấm lớp phủ ──
const vm = require("node:vm");
const RAW_SRC = fs.readFileSync(path.join(__dirname, "..", FILE_STD), "utf8");

function fnSrc(name) {
  const m = new RegExp(`\\n( *)(async )?function ${name}\\(`).exec(RAW_SRC);
  assert.ok(m, `thiếu hàm ${name}`);
  const end = RAW_SRC.indexOf(`\n${m[1]}}\n`, m.index + 1);
  return RAW_SRC.slice(m.index + 1, end + m[1].length + 2);
}

function classes(...init) {
  const set = new Set(init);
  return { contains: (c) => set.has(c), add: (c) => set.add(c), remove: (c) => set.delete(c),
    toggle: (c, on) => (on ? set.add(c) : set.delete(c)) };
}

function hoChieuCtx() {
  const ctx = {
    console: { warn() {}, log() {} },
    foldChoiceText: (s) => String(s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/gi, "d")
      .toLowerCase().replace(/\s+/g, " ").trim(),
    sleep: () => Promise.resolve(),
    waitFor: async (fn, timeout) => {
      for (let t = 0; t <= timeout; t += 100) { const v = fn(); if (v) return v; await new Promise((r) => setTimeout(r, 5)); }
      return null;
    },
    markFilled() {},
    standardMarkTarget: (el) => el.formGroup || el,
  };
  vm.runInNewContext(["bootstrapSelectWrapper", "bootstrapItemKey", "pickBootstrapSelectItem", "fillStandardCheckbox"]
    .map(fnSrc).join("\n") + "\nthis.pick = pickBootstrapSelectItem; this.tick = fillStandardCheckbox;", ctx);
  return ctx;
}

// <select> ẩn + div.bootstrap-select đứng sau; danh sách Phường/Xã chỉ có sau khi mở menu (nạp chậm).
function wardSelect(names) {
  const options = [{ value: "", textContent: "-- Chưa chọn --" }];
  const select = { options, selectedIndex: 0, closest: () => null };
  Object.defineProperty(select, "selectedOptions", { get: () => [options[select.selectedIndex]] });
  const items = [];
  const wrap = { classList: classes("btn-group", "bootstrap-select"), querySelectorAll: () => items };
  const button = { disabled: false, click() {
    if (wrap.classList.contains("open")) return wrap.classList.remove("open");
    wrap.classList.add("open");
    if (!items.length) setTimeout(() => names.forEach((name, i) => {
      options.push({ value: String(i + 1), textContent: name });
      items.push({ textContent: name, querySelector: () => null, click() { select.selectedIndex = i + 1; } });
    }), 20);
  } };
  wrap.querySelector = () => button;
  select.nextElementSibling = wrap;
  return { select, wrap };
}

test("hộ chiếu: Phường/Xã bootstrap-select mở menu, chờ danh sách, bấm đúng mục rồi đóng menu", async () => {
  const ctx = hoChieuCtx();
  const { select, wrap } = wardSelect(["Phường Đoàn Kết A", "Phường Đoàn Kết", "Xã Bản Hon"]);
  assert.equal(await ctx.pick(select, "Phường Đoàn Kết", 1000), true);
  assert.equal(select.selectedOptions[0].textContent, "Phường Đoàn Kết");
  assert.equal(wrap.classList.contains("open"), false);
  // Khớp bỏ tiền tố chỉ khi ra đúng một mục; không có mục khớp → false, đóng menu.
  const other = wardSelect(["Phường Kỳ Lừa", "Xã Mai Pha"]);
  assert.equal(await ctx.pick(other.select, "Kỳ Lừa", 1000), true);
  const none = wardSelect(["Xã Mai Pha"]);
  assert.equal(await ctx.pick(none.select, "Phường Đông Kinh", 300), false);
  assert.equal(none.wrap.classList.contains("open"), false);
});

test("hộ chiếu: ô tích iCheck bấm lớp phủ ins.iCheck-helper, không bấm khung form-group", async () => {
  const ctx = hoChieuCtx();
  const wrapper = { classList: classes("icheckbox_minimal") };
  const el = { checked: false, parentElement: wrapper, closest: () => null, dispatchEvent() {},
    formGroup: { click() { throw new Error("không được bấm khung form-group"); } } };
  const helper = { click() { el.checked = !el.checked; wrapper.classList.toggle("checked", el.checked); } };
  wrapper.querySelector = (sel) => (sel.includes("iCheck-helper") ? helper : null);
  assert.equal(await ctx.tick(el, true), true);
  assert.equal(wrapper.classList.contains("checked"), true);
});

test("hộ chiếu: vòng điền chuẩn ở cổng Bộ Công an thử bootstrap-select trước đường cũ", () => {
  const body = RAW_SRC.slice(RAW_SRC.indexOf("const trySelect = async (attempt) => {"));
  assert.match(body.slice(0, 1500), /dichvucong\.bocongan\.gov\.vn[\s\S]*pickBootstrapSelectItem\(el, f\.value/);
});
// ── eForm Nth cổng bocongan (cờ supportsBcaNthReview, user 19/11/2026): cùng bộ đọc ô, gỡ tệp cũ bằng thùng rác ──
test("bộ đọc ô Bộ Công an chạy thêm eForm Nth bocongan: bootstrap-select, chỉ ô của form kê khai", () => {
  assert.match(sidebar, /supportsBcaNthReview: true/);
  assert.match(bcaReview, /const NTH_HOST = "dichvucong\.bocongan\.gov\.vn"/);
  assert.match(bcaReview, /if \(nthPage\(\) && !nthScoped\(el\)\) continue;/);
  assert.match(bcaReview, /el\.closest\("\.bootstrap-select"\)/);
  // Đính xong cùng trang: sidebar đếm lại ô khi BE gửi fieldReview kèm lệnh đính.
  assert.match(sidebar, /if \(a\.fieldReview && res\) \{/);
  // Đính kèm lại: gỡ tệp lượt trước bằng thùng rác của bảng (cổng nhận thêm bản trùng chứ không thay).
  const core = read("content/attach-core.js");
  assert.match(core, /if \(isBcaNthAttachPage\(\)\) return await clearBcaNthAttachedFiles\(\);/);
});
