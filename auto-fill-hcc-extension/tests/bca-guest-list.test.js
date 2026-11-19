// Thông báo lưu trú (Cổng DVC Bộ Công an): danh sách người lưu trú thêm từng người qua modal "Thêm mới người lưu trú".
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const read = (file) => fs.readFileSync(path.join(root, file), "utf8").replace(/^\s*\/\/.*$/gm, "");
const content = read("content.js");
const main = read("content/bca-datepicker-main.js");
const FILE_STD = "content.js";
const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));

test("trang Bộ Công an được nhận là form standard", () => {
  assert.match(content, /document\.getElementById\("btnAddPersonLT"\)\)\)\s*\{\s*return "standard";/);
  // Trang cấp đổi căn cước: ô họ tên người kê khai là txtFULLNAME_NDN.
  assert.match(content, /document\.getElementById\("txtFULLNAME_NDN"\)/);
});

test("vòng điền chuẩn giao comp bca-guest-list cho engine modal", () => {
  assert.match(content, /f\.comp === "bca-guest-list"\)\s*\{\s*await fillBcaGuestList\(f, result\);\s*continue;/);
});

test("mỗi người: mở modal, điền theo id, Lưu, chỉ tính thành công khi bảng có người đó; lỗi thì dừng", () => {
  const one = content.slice(content.indexOf("async function fillBcaGuest("), content.indexOf("async function fillBcaGuestList("));
  assert.match(one, /#btnAddPersonLT/);
  assert.match(one, /btnSaveNLT/);
  assert.match(one, /!bcaVisible\(modal\) && bcaGuestListed\(guest\)/);
  const list = content.slice(content.indexOf("async function fillBcaGuestList("), content.indexOf("async function fillFormStandard("));
  assert.match(list, /if \(bcaGuestListed\(guest\)\)/);
  assert.match(list, /result\.notFound\.push[\s\S]*return;/);
});

test("ngày gán qua cầu nối MAIN world (bootstrap-datepicker), cùng tên sự kiện hai phía", () => {
  for (const name of ["__HCC_BCA_DATES_REQUEST__", "__HCC_BCA_DATES_RESULT__"]) {
    assert.ok(content.includes(name) && main.includes(name), name);
  }
  assert.match(main, /\$el\.datepicker\("update", value\)/);
  const entry = manifest.content_scripts.find((cs) => (cs.js || []).includes("content/bca-datepicker-main.js"));
  assert.ok(entry && entry.world === "MAIN");
  assert.deepStrictEqual(entry.matches, ["https://dichvucong.dancuquocgia.gov.vn/*"]);
});

test("không thêm quyền / host_permissions (đổi quyền làm Chrome tắt extension chờ duyệt lại)", () => {
  assert.ok(!(manifest.host_permissions || []).some((h) => h.includes("dancuquocgia")));
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

test("cấp đổi căn cước: option \"Công an …\" khớp lỏng, nộp cấp tỉnh chỉ chọn Tỉnh, địa chỉ trạm một dòng thì chọn luôn", () => {
  const src = fs.readFileSync(path.join(__dirname, "..", FILE_STD), "utf8");
  const fn = src.slice(src.indexOf("async function fillBcaAgencyField("), src.indexOf("async function fillBcaRows("));
  assert.match(fn, /replace\(\/\^cong an\\s\+\/, ""\)/);
  assert.match(fn, /const provinceOnly = !wardName;/);
  assert.match(fn, /if \(!provinceOnly\) \{[\s\S]*?fillStandardSelect\(ward, wardOpt\.value\);/);
  // Đã chọn sẵn cơ quan vẫn phải chờ + chọn ô địa chỉ trạm.
  assert.match(fn, /\{\s*await waitBcaAgencyReady\(f\);\s*return;\s*\}/);
  assert.match(fn, /f\.value\?\.readyPick && options\.length === 1/);
});

test("thường trú: ô cơ quan theo cặp id BE gửi + chờ readySelect; bảng dòng bca-rows bấm Thêm ở dòng cuối", () => {
  const src = fs.readFileSync(path.join(__dirname, "..", FILE_STD), "utf8");
  assert.match(src, /document\.getElementById\(f\.value\?\.cityId \|\| "accomStay_cboPROVINCE_ID"\)/);
  assert.match(src, /f\.value\?\.readySelect/);
  assert.match(src, /f\.comp === "bca-rows"\)\s*\{\s*await fillBcaRows\(f, result\);\s*continue;/);
  const fn = src.slice(src.indexOf("async function fillBcaRows("), src.indexOf("async function fillBcaGuestList("));
  assert.match(fn, /buttons\[buttons\.length - 1\]\?\.click\(\)/);
});

test("đính kèm bca-row (tạm trú / thường trú) có ở Auto Fill, mở nhóm qua cầu nối MAIN world", () => {
  assert.match(content, /if \(isBcaPortal\(\) && Array\.isArray\(attachments\) && attachments\.some\(\(item\) => item\?\.target === "bca-row"\)\)/);
  assert.match(content, /async function attachFilesByBcaPlan\(/);
  assert.match(content, /bcaSwitchConfirmButton/);
  for (const name of ["__HCC_BCA_LOAD_GROUP_REQUEST__", "__HCC_BCA_LOAD_GROUP_RESULT__"]) {
    assert.ok(content.includes(name) && main.includes(name), name);
  }
});

test("điều chỉnh thông tin cư trú: bcaPlainTable lấy bảng đang hiện, rowFields điền Loại / Số lượng / Ghi chú của dòng", () => {
  const fn = content.slice(content.indexOf("async function attachFilesByBcaPlan("), content.indexOf("async function attachFilesByPlan("));
  assert.match(fn, /\(bcaPlainTable && bcaVisibleTable\(\)\) \|\| await bcaOpenGroup\(groupIndex, groupLabel \|\| ""\)/);
  assert.match(fn, /if \(ok\) bcaFillRowFields\(row, item\.rowFields\);/);
  const fill = content.slice(content.indexOf("function bcaFillRowFields("), content.indexOf("function bcaAddRowButton("));
  assert.match(fill, /select\[id\^="cboKIND_OF_FILE"\]/);
  assert.match(fill, /\["txtNUM_OF_DOC", fields\.count\], \["txtNOTE_OF_DOC", fields\.note\]/);
  assert.match(fill, /\(!current \|\| current === "0"\)/);
  // Trang có sẵn bảng #tblGiayToDinhKem (ô chọn tệp ẩn, không có nút chữ "Chọn tệp") vẫn là trang đính kèm.
  const gate = content.slice(content.indexOf("function hasAttachmentTarget("), content.indexOf("const ATTACHMENT_STEP_SNIPPETS"));
  assert.match(gate, /isBcaPortal\(\) && document\.querySelector\('#tblGiayToDinhKem, \[id\^="tphs_new_"\]/);
  // Tích ô chkIS_COMPULSORY của dòng, không tích ô ẩn td.bs-checkbox của bootstrap-table.
  assert.match(fn, /const checkbox = bcaRowCheckbox\(row\);/);
  assert.match(content, /input\[type="checkbox"\]\[id\^="chkIS_COMPULSORY"\]/);
  assert.match(content, /!box\.closest\("td\.bs-checkbox"\)/);
});

const RELATION_SRC = fs.readFileSync(path.join(root, "content.js"), "utf8");

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

// Cấp đổi / cấp lại căn cước (19/11): trang có thể đặt id radio khác trang từ đủ 14 tuổi → dò theo nhãn trong nhóm radIsNCC.
function runDeclarantByLabel(account, subject, wrapBoth = false) {
  const fn = RELATION_SRC.slice(RELATION_SRC.indexOf("async function fillBcaDeclarantField("),
    RELATION_SRC.indexOf("// \"Mối quan hệ của người kê khai với người cần cấp căn cước\""));
  const SELF = "Người kê khai là người cần cấp đổi căn cước";
  const OTHER = "Người kê khai là cha/mẹ/người đại diện hợp pháp của người cần cấp đổi căn cước";
  const radio = (text) => ({ text, checked: false, disabled: false, getAttribute: () => "radIsNCC",
    click() { this.checked = true; } });
  const radios = [radio(SELF), radio(OTHER), { text: OTHER, getAttribute: () => "radKhac" }];
  const els = { txtFULLNAME_NDN: { value: account.name }, txtIDENTIFY_NUMBER_NDN: { value: account.id } };
  const deps = {
    document: { getElementById: (id) => els[id] || null, querySelectorAll: () => radios },
    waitFor: async (cond) => cond(),
    bcaVisible: (el) => !!el,
    bcaGuestFold: (s) => String(s || "").replace(/Đ/g, "D").replace(/đ/g, "d").normalize("NFD")
      .replace(/[̀-ͯ]/g, "").replace(/\s+/g, " ").trim().toLowerCase(),
    radioLabelText: (r) => (wrapBoth ? `${SELF} ${OTHER}` : r.text),
    console: { log() {} },
  };
  const run = new Function(...Object.keys(deps), `${fn}; return fillBcaDeclarantField;`)(...Object.values(deps));
  const result = { filled: 0, notFound: [] };
  const value = { selfId: "chkIS_NCC", otherId: "chkIS_NOT_NCC", otherBlock: "divCheck_NDN", selfLabel: SELF,
    otherLabel: OTHER, subject };
  return run({ name: "radIsNCC", comp: "bca-declarant", value }, result)
    .then((decision) => ({ decision, self: radios[0].checked, other: radios[1].checked, result }));
}

test("bca-declarant: id radio lệch thì chọn theo nhãn (cấp đổi căn cước)", async () => {
  const subject = { name: "ĐINH VĂN MẪU", id: "001204000009" };
  let r = await runDeclarantByLabel({ name: "Nguyễn Văn Khác", id: "001204000001" }, subject);
  assert.deepStrictEqual([r.decision, r.self, r.other], ["other", false, true]);
  r = await runDeclarantByLabel({ name: "Đinh Văn Mẫu", id: "001204000009" }, subject);
  assert.deepStrictEqual([r.decision, r.self, r.other], ["self", true, false]);
  // Nhãn đọc ra chứa cả hai câu (thẻ cha bọc hai radio) → không chọn bừa.
  r = await runDeclarantByLabel({ name: "Nguyễn Văn Khác", id: "001204000001" }, subject, true);
  assert.deepStrictEqual([r.decision, r.self, r.other], [null, false, false]);
  assert.strictEqual(r.result.notFound.length, 1);
});

test("vòng điền chuẩn: ô bcaOtherOnly bỏ qua trừ khi bca-declarant chọn khai thay", () => {
  assert.match(RELATION_SRC, /f\.comp === "bca-declarant"\)\s*\{\s*bcaDeclarant = await fillBcaDeclarantField\(f, result\);/);
  assert.match(RELATION_SRC, /if \(f\.bcaOtherOnly && bcaDeclarant !== "other"\) continue;/);
  // SĐT / email Phần I của người cần cấp chỉ ghi khi tài khoản chính là người đó (cấp đổi căn cước, 19/11).
  assert.match(RELATION_SRC, /if \(f\.bcaSelfOnly && bcaDeclarant !== "self"\) continue;/);
});


// ── Cấp hộ chiếu 1.001456 (18/11): ô bootstrap-select chọn như người dùng + ô tích iCheck bấm lớp phủ ──
const vm = require("node:vm");
// Bỏ CR: working copy Windows checkout CRLF, fnSrc tìm "\n  }\n".
const RAW_SRC = fs.readFileSync(path.join(__dirname, "..", FILE_STD), "utf8").replace(/\r\n/g, "\n");

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

// ── Đính kèm lại cổng Bộ Công an (19/11, DOM thật): gỡ tệp cũ bằng span.trash-file trước khi gắn tệp mới ──
function bcaRowCtx(names) {
  const lis = names.map((name) => {
    const li = { isConnected: true, name };
    const span = { click() { li.isConnected = false; }, closest: () => span };
    const icon = { closest: (sel) => (sel.includes("span.trash-file") ? span : null) };
    li.querySelector = (sel) => (sel === "a.file-info" ? { textContent: name } : icon);
    return li;
  });
  const row = { querySelectorAll: () => lis.filter((li) => li.isConnected) };
  const ctx = {
    console: { log() {}, warn() {} },
    location: { hostname: "dichvucong.bocongan.gov.vn" },
    document: { querySelectorAll: () => [] },
    foldChoiceText: (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/gi, "d")
      .toLowerCase().replace(/\s+/g, " ").trim(),
    nodeText: (el) => String(el?.textContent || ""),
    readUploadedNames: () => ({}),
    attachSourceKey: (file) => file.name,
    isVisible: (el) => el.isConnected !== false,
    findButtonByText: () => null,
    sleep: () => Promise.resolve(),
    waitFor: async (fn, timeout) => {
      for (let t = 0; t <= timeout; t += 100) { const v = fn(); if (v) return v; await new Promise((r) => setTimeout(r, 1)); }
      return null;
    },
  };
  const consts = RAW_SRC.slice(RAW_SRC.indexOf("  const BCA_NTH_HOST"), RAW_SRC.indexOf("\n  async function clearBcaNthStaleFiles"));
  vm.runInNewContext(consts + "\n" + ["attpDocFingerprint", "shownIndexForFile", "clearBcaNthStaleFiles"].map(fnSrc).join("\n")
    + "\nthis.clear = clearBcaNthStaleFiles;", ctx);
  return { ctx, row, lis };
}

test("đính kèm lại Bộ Công an: gỡ tệp cũ khác lượt này, giữ tệp cùng tên (cổng thêm mốc giờ)", async () => {
  const { ctx, row, lis } = bcaRowCtx(["Ho_chieu_pho_thong_cap_lan_gan_nhat_1795063858.pdf", "Don_cu_1795060000.pdf"]);
  const removed = await ctx.clear(row, [{ name: "Ho_chieu_pho_thong_cap_lan_gan_nhat.pdf" }]);
  assert.equal(removed, 1);
  assert.equal(lis[0].isConnected, true, "tệp cùng tên (bỏ mốc giờ) được giữ, không đính trùng");
  assert.equal(lis[1].isConnected, false, "tệp của lượt trước bị gỡ bằng thùng rác");
});

test("đính kèm lại Bộ Công an: plan mới khác hẳn → gỡ hết; cổng khác không đụng", async () => {
  const { ctx, row, lis } = bcaRowCtx(["Ho_chieu_1795063858.pdf", "To_khai_1795063859.pdf"]);
  assert.equal(await ctx.clear(row, [{ name: "Don_trinh_bao_mat.pdf" }]), 2);
  assert.ok(lis.every((li) => !li.isConnected));
  const other = bcaRowCtx(["Ho_chieu_1795063858.pdf"]);
  other.ctx.location.hostname = "dichvucong.gov.vn";
  assert.equal(await other.ctx.clear(other.row, [{ name: "Khac.pdf" }]), 0);
});

test("đính kèm lại Bộ Công an: tệp đã bấm thùng rác (li bị ẩn) không còn tính là đã có trên dòng", () => {
  const li = (name, hidden = false) => ({ isConnected: true, hidden, querySelector: () => ({ textContent: name }) });
  const items = [li("Ho_chieu_1795063858.pdf", true), li("To_khai_1795063859.pdf")];
  const ul = {};
  const cell = {
    querySelectorAll: (sel) => (sel.includes("ul_file_info_") ? items : []),
    querySelector: (sel) => (sel.includes("ul_file_info_") ? ul : null),
  };
  const input = { closest: () => cell };
  const row = { querySelectorAll: () => [input] };
  const ctx = {
    foldChoiceText: (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/gi, "d")
      .toLowerCase().replace(/\s+/g, " ").trim(),
    nodeText: (el) => String(el?.textContent || ""),
    isVisible: (el) => !el.hidden,
  };
  vm.runInNewContext(["attpDocFingerprint", "attpRowUploadInput", "attpRowAttachedFingerprints"].map(fnSrc).join("\n")
    + "\nthis.fps = attpRowAttachedFingerprints;", ctx);
  assert.deepEqual(Array.from(ctx.fps(row)), ["tokhai1795063859"]);
  items[1].hidden = true;
  assert.deepEqual(Array.from(ctx.fps(row)), [], "gỡ hết → dòng trống, lượt đính mới phải gắn lại");
});

// ── Ảnh chân dung 4x6 (comp bca-photo, hộ chiếu 1.001456): gắn tệp JPEG BE gửi vào ô filename46, không bấm "Tải ảnh" ──
test("ảnh chân dung: gắn tệp JPEG vào input filename46, phát change, tính là đã điền", async () => {
  const vm = require("node:vm");
  const src = fs.readFileSync(path.join(__dirname, "..", FILE_STD), "utf8");
  assert.match(src, /f\.comp === "bca-photo"\)\s*\{\s*await fillBcaPhotoField\(f, result\);\s*continue;/);
  const fn = src.slice(src.indexOf("function findBcaPhotoInput("), src.indexOf("async function fillBcaAgencyField("));
  assert.doesNotMatch(fn, /\.click\(\)/, "không bấm nút Tải ảnh (mở hộp chọn tệp của Windows)");
  const events = [];
  const marks = [];
  const logs = [];
  const hidden = { value: "" };
  const input = {
    name: "filename46", files: null, parentElement: { id: "box" },
    getAttribute: (attr) => (attr === "typeimg" ? "46" : null),
    closest: () => ({ id: "group" }),
    dispatchEvent: (ev) => events.push(ev.type),
  };
  class FakeInput {}
  Object.defineProperty(FakeInput.prototype, "files", { set(v) { this._files = v; }, get() { return this._files; } });
  Object.setPrototypeOf(input, FakeInput.prototype);
  delete input.files;
  const ctx = {
    document: {
      querySelector: (sel) => (sel === 'input[type="file"][name="filename46"]' ? input : null),
      querySelectorAll: () => [],
      getElementById: (id) => (id === "custom-file-hidden46" ? hidden : null),
      getElementsByName: () => [],
    },
    CSS: { escape: (s) => s },
    HTMLInputElement: FakeInput,
    DataTransfer: class { constructor() { const list = []; this.items = { add: (f) => list.push(f) }; this.files = list; } },
    Event: class { constructor(type) { this.type = type; } },
    File, atob,
    console: { log: (m) => logs.push(["log", m]), warn: (m) => logs.push(["warn", m]) },
    sleep: async () => {},
    waitFor: async () => null,
    foldChoiceText: (s) => String(s || "").toLowerCase(),
    injectAutofillStyles: () => {},
    markFilled: (el) => marks.push(["filled", el.id]),
    markUnfilled: (el) => marks.push(["unfilled", el.id]),
  };
  vm.createContext(ctx);
  vm.runInContext(`${fn}\nthis.fillBcaPhotoField = fillBcaPhotoField;`, ctx);
  const result = { filled: 0, notFound: [] };
  const value = { name: "anh_chan_dung_4x6.jpg", type: "image/jpeg", dataUrl: "data:image/jpeg;base64,/9j/4AAQ" };
  assert.equal(await ctx.fillBcaPhotoField({ name: "filename46", comp: "bca-photo", value }, result), true);
  assert.equal(input.files.length, 1);
  assert.equal(input.files[0].name, "anh_chan_dung_4x6.jpg");
  assert.equal(input.files[0].type, "image/jpeg");
  assert.deepEqual(events, ["input", "change"]);
  assert.deepEqual(marks, [["filled", "group"]]);
  assert.equal(result.filled, 1);
  // Cổng chưa ghi tên tệp vào ô ẩn hd_filename46 → vẫn tính đã gắn nhưng ghi log cảnh báo để soát.
  assert.match(logs.at(-1)[1], /chưa thấy cổng nhận/);
  hidden.value = "anh_chan_dung_0123456789.jpg";
  await ctx.fillBcaPhotoField({ name: "filename46", comp: "bca-photo", value }, result);
  assert.deepEqual(logs.at(-1), ["log", "[AutoFill-STD] filename46: cổng đã nhận ảnh anh_chan_dung_4x6.jpg."]);
  // Trang không có ô ảnh → notFound, không lỗi.
  ctx.document.querySelector = () => null;
  const missing = { filled: 0, notFound: [] };
  assert.equal(await ctx.fillBcaPhotoField({ name: "filename46", comp: "bca-photo", value }, missing), false);
  assert.deepEqual(missing.notFound, ["filename46"]);
});
