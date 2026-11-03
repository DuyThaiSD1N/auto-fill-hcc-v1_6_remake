// Tờ đơn và khối "Thông tin người nộp" (tài khoản VNeID) dùng chung field-key (vd data[birthday]). BE gắn
// scope/scopeAway/scopeNear cho ô của tờ đơn; engine handfree trước bỏ qua các khoá này nên ghi vào ô ĐẦU TIÊN
// trên trang (khối người nộp), còn ô của tờ đơn giữ ngày sinh của tài khoản.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const src = fs.readFileSync(path.join(__dirname, "..", "content", "fill-core.js"), "utf8");

function fnSource(name) {
  const start = src.search(new RegExp(`(async )?function ${name}\\(`));
  assert.ok(start >= 0, `thiếu hàm ${name}`);
  const end = src.indexOf("\n}\n", start);
  return src.slice(start, end + 2);
}

// DOM giả tối thiểu: chỉ cần parentElement, contains, querySelector('[name="…"]').
function el(name, children = []) {
  const node = { name, children, parentElement: null };
  children.forEach((c) => { c.parentElement = node; });
  const all = (n) => n.children.flatMap((c) => [c, ...all(c)]);
  node.querySelector = (sel) => {
    const m = /\[name="(.+)"\]$/.exec(sel);
    return m ? all(node).find((c) => c.name === m[1]) || null : null;
  };
  node.querySelectorAll = (sel) => {
    const m = /\[name="(.+)"\]$/.exec(sel);
    return m ? all(node).filter((c) => c.name === m[1]) : [];
  };
  node.contains = (other) => other === node || all(node).includes(other);
  return node;
}

function setup() {
  const nopBirthday = el("data[birthday]");
  const donBirthday = el("data[birthday]");
  const nguoiNop = el("", [el("data[chonDoiTuong]"), el("data[identityAgency]"), nopBirthday]);
  const don = el("", [el("data[fullName]"), donBirthday, el("data[provincenoisinh]")]);
  const body = el("", [nguoiNop, el("", [don])]);
  const documentElement = el("", [body]);
  const document = {
    body,
    documentElement,
    querySelector: (sel) => (sel.startsWith(".") ? null : body.querySelector(sel)),
    querySelectorAll: (sel) => body.querySelectorAll(sel),
  };
  const ctx = {
    document,
    CSS: { escape: (s) => s },
    console: { warn() {}, log() {} },
    standardNameVariants: (names) => names,
    fieldCandidates: (f) => [f.name],
  };
  vm.runInNewContext([
    "standardScopeRoot", "standardScopeAwayNames", "standardScopeHasControl", "standardAnchoredScopeRoot",
    "standardUnscopedDataNames", "standardForbiddenRoots", "standardInsideForbidden",
  ].map(fnSource).join("\n") + `
    const STANDARD_DATA_COMPS = new Set(["dom-input", "dom-date", "dom-datetime", "dom-select", "raw"]);
    this.scopeRoot = standardScopeRoot; this.forbidden = standardForbiddenRoots; this.inside = standardInsideForbidden;`, ctx);
  return { ctx, nguoiNop, don, donBirthday, nopBirthday };
}

const BIRTHDAY = {
  name: "data[birthday]",
  comp: "dom-date",
  value: "01/01/1990",
  scope: ".formio-component-khongCoTrenTrang",
  scopeAway: ["data[chonDoiTuong]", "data[identityAgency]"],
  scopeNear: "data[provincenoisinh]",
};

test("ô khai scope: vùng dò là khối tờ đơn, không chứa ô của khối người nộp", () => {
  const { ctx, nguoiNop, donBirthday, nopBirthday } = setup();
  // Selector scope không khớp (trả null) → leo từ ô neo Nơi sinh lên tới sát khối người nộp.
  const root = ctx.scopeRoot({ ...BIRTHDAY, scope: "" });
  assert.ok(root && root.contains(donBirthday));
  assert.equal(root.contains(nopBirthday), false);
  assert.equal(root.contains(nguoiNop), false);
});

test("khối người nộp được nhận là khối cấm ghi", () => {
  const { ctx, nguoiNop, don } = setup();
  const fields = [BIRTHDAY, { name: "data[fullName]", comp: "dom-input", value: "NGUYEN VAN A" }];
  const roots = ctx.forbidden(fields);
  assert.equal(roots.length, 1);
  assert.ok(roots[0].contains(nguoiNop) || roots[0] === nguoiNop);
  assert.equal(ctx.inside(roots, don), false);
});

test("không có ô neo mà vùng dò chứa khối cấm → BỎ ô, không dò cả trang", () => {
  const { ctx } = setup();
  assert.equal(ctx.scopeRoot({ ...BIRTHDAY, scope: "", scopeNear: "data[khongTonTai]" }), null);
});

test("vòng điền và các vòng retry/điền lại đều dò theo khối", () => {
  const body = fnSource("fillFormStandard");
  assert.match(body, /let root = await standardScopeRootWaiting\(f\);/);
  assert.match(body, /if \(!root\) continue;/);
  assert.match(body, /findStandardInputForField\(f, candidates, occurrence, root\)/);
  assert.match(body, /restoreStandardForbidden\(forbiddenSnapshot, standardWrittenValueKeys\(fields\)\)/);
  for (const name of ["retryStandardAreaSelects", "stabilizeStandardAreaSelects", "reapplyEmptyStandardTextFields"]) {
    assert.match(fnSource(name), /const root = standardScopeRoot\(f\);/, name);
  }
});

test("ô ngày flatpickr chọn trên lịch, không dựa vào el._flatpickr (isolated world không thấy)", () => {
  // Gõ "11/10/2010" vào ô ngày Form.io bị cổng đọc kiểu Mỹ rồi đổi thành 20/10/2011.
  const fill = fnSource("fillStandardDate");
  assert.match(fill, /pickFlatpickrCalendarDate\(el, dateObj\)/);
  assert.doesNotMatch(fill, /_flatpickr/);
  assert.doesNotMatch(fnSource("fillFormStandard"), /\._flatpickr/);
});
