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
