// 1) Radio KHÔNG khớp thì tuyệt đối không được tick đại một ô (hồ sơ pháp lý: bịa câu trả lời còn
//    tệ hơn bỏ trống). Lỗi thật: đơn ghi "Khấu trừ", cổng lại nhận "Không phải nộp thuế GTGT".
// 2) Trang "Thông tin về bảo hiểm xã hội": nhận trang + tick đúng kỳ đóng theo NHÃN hiển thị.
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const read = (...p) => fs.readFileSync(path.join(__dirname, "..", ...p), "utf8")
  .split(String.fromCharCode(13)).join("");

// ---------------------------------------------------------------- DOM giả tối thiểu
function makeRadio(value, labelText, name) {
  const radio = {
    type: "radio", value, name, checked: false, disabled: false, id: `r_${value}`,
    _label: labelText,
    getAttribute: (k) => (k === "name" ? name : null),
    closest: () => null,
    parentElement: { textContent: labelText },
    dispatchEvent() { return true; },
    click() { radio.checked = true; },
    setAttribute() {}, removeAttribute() {},
  };
  return radio;
}

function makeDoc(radios) {
  return {
    querySelectorAll: (sel) => {
      if (/radio/.test(sel)) {
        const m = sel.match(/name="([^"]+)"/);
        return m ? radios.filter((r) => r.name === m[1]) : radios;
      }
      return [];
    },
    querySelector: () => null,   // không có <label for> -> đi nhánh parentElement.textContent
  };
}

// ---------------------------------------------------------------- 1. fillStandardRadio
const contentSrc = read("content.js");
function loadRadioFiller(doc) {
  const grab = (name, end) => {
    const a = contentSrc.indexOf(`  function ${name}(`);
    const b = contentSrc.indexOf(end, a);
    assert.ok(a >= 0 && b > a, `không tách được ${name}`);
    return contentSrc.slice(a, b);
  };
  const fillStart = contentSrc.indexOf("  async function fillStandardRadio(");
  const fillEnd = contentSrc.indexOf("  function isStandardEmptyControl(", fillStart);
  const box = {
    document: doc,
    console: { warn(...a) { box.warns.push(a.join(" ")); } },
    warns: [],
    CSS: { escape: (s) => s },
    foldChoiceText: (s) => String(s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/gi, "d").toLowerCase().replace(/\s+/g, " ").trim(),
    waitFor: async () => null,
    sleep: async () => {},
    markFilled() {},
    standardMarkTarget: (x) => x,
    Event: class { constructor(t) { this.type = t; } },
  };
  vm.runInNewContext(`
    ${grab("radioLabelText", "  function radioValueMatches(")}
    ${grab("radioValueMatches", "  async function fillStandardRadio(")}
    ${contentSrc.slice(fillStart, fillEnd)}
    globalThis.fill = fillStandardRadio;
  `, box);
  return box;
}

(async () => {
  const NAME = "ctl00$C$UC_DW_TAXEditCtl$TAX_CAL_METHOD_IDRbBox";
  // Cổng dùng value là MÃ LẠ (không phải bộ DED/DAT/DIR/NAT mà mapper từng tự đặt).
  const radios = [
    makeRadio("1", "Khấu trừ", NAME),
    makeRadio("2", "Trực tiếp trên GTGT", NAME),
    makeRadio("3", "Trực tiếp trên doanh số", NAME),
    makeRadio("4", "Không phải nộp thuế GTGT", NAME),
  ];
  const box = loadRadioFiller(makeDoc(radios));

  // a) Gửi NHÃN (bản đã sửa của mapper) -> tick đúng ô "Khấu trừ".
  assert.strictEqual(await box.fill(radios[0], "Khấu trừ"), true);
  assert.ok(radios[0].checked, "phải tick ô Khấu trừ");
  assert.ok(!radios[3].checked, "không được tick ô Không phải nộp thuế GTGT");
  console.log("ok - gửi nhãn thì tick đúng ô, kể cả khi value của cổng là mã lạ");

  // b) Gửi MÃ tự chế (bản cũ) -> KHÔNG khớp ô nào -> phải bỏ trống + cảnh báo, KHÔNG tick đại.
  radios.forEach((r) => { r.checked = false; });
  const box2 = loadRadioFiller(makeDoc(radios));
  const ok = await box2.fill(radios[0], "DED");
  assert.strictEqual(ok, false, "không khớp thì phải trả false");
  assert.ok(radios.every((r) => !r.checked),
    `không khớp thì KHÔNG được tick ô nào, thực tế tick: ${radios.filter((r) => r.checked).map((r) => r._label)}`);
  assert.ok(box2.warns.join(" ").includes("không khớp"), "phải cảnh báo ra console để cán bộ biết mà sửa");
  console.log("ok - giá trị không khớp thì bỏ trống + cảnh báo, không bịa câu trả lời");

  // c) Nhãn RỖNG không được nuốt mọi giá trị ("".includes(x) luôn đúng).
  const blank = [makeRadio("x", "", "g"), makeRadio("y", "Hàng tháng", "g")];
  const box3 = loadRadioFiller(makeDoc(blank));
  await box3.fill(blank[0], "Hàng tháng");
  assert.ok(blank[1].checked && !blank[0].checked,
    "ô nhãn rỗng không được khớp bừa; phải tick đúng ô có nhãn Hàng tháng");
  console.log("ok - ô radio nhãn rỗng không nuốt mọi giá trị");
})();

// ---------------------------------------------------------------- 2. Trang BHXH
const entSrc = read("content", "procedures", "enterprise-registration.js");
(async () => {
  const NAME = "bhxh";
  const radios = [
    makeRadio("m", "Hàng tháng", NAME),
    makeRadio("q", "03 tháng một lần", NAME),
    makeRadio("h", "06 tháng một lần", NAME),
  ];
  const doc = makeDoc(radios);

  const slice = (start, end) => {
    const a = entSrc.indexOf(start);
    const b = entSrc.indexOf(end, a);
    assert.ok(a >= 0 && b > a, `không tách được ${start}`);
    return entSrc.slice(a, b);
  };
  const box = {
    document: doc,
    console: { log() {}, warn(...a) { box.warns.push(a.join(" ")); } },
    warns: [], toasts: [],
    CSS: { escape: (s) => s },
    Event: class { constructor(t) { this.type = t; } },
    visible: () => true,
    radioLabel: (r) => r._label,
    fold: (s) => String(s || "").replace(/đ/g, "d").replace(/Đ/g, "D")
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .toLowerCase().replace(/[^a-z0-9]+/g, " ").trim(),
    PAGE_SPEC: { "thong-tin-bao-hiem-xa-hoi": { label: "Thông tin về bảo hiểm xã hội", save: "s" } },
    progress() {}, sleep: async () => {},
    toast(m) { box.toasts.push(m); },
    setFillState: async () => {},
    scheduleStepFill() {},
    waitForSaveButton: async () => ({ click: () => { box.saved = true; } }),
    clickSaveDetectReload: async (b) => { b.click(); return true; },
  };
  vm.runInNewContext(`
    ${slice("  function findRadioByLabel(", "  function findBackButton(")}
    ${slice("  async function stepSocialInsurance(", "  function progress(")}
    globalThis.findRadioByLabel = findRadioByLabel;
    globalThis.step = stepSocialInsurance;
  `, box);

  // a) Khớp ĐÚNG kỳ đóng, không dính "03/06 tháng một lần" do chữ lồng nhau.
  const state = { pages: { "thong-tin-bao-hiem-xa-hoi": [{ name: "__bhxhMethod", value: "06 tháng một lần" }] }, done: [] };
  await box.step(state);
  assert.ok(radios[2].checked, "phải tick đúng '06 tháng một lần'");
  assert.ok(!radios[0].checked && !radios[1].checked, "không được tick nhầm kỳ đóng khác");
  assert.ok(box.saved, "phải bấm Lưu sau khi chọn");
  assert.ok(state.done.includes("thong-tin-bao-hiem-xa-hoi"), "phải đánh dấu xong để sang trang kế");
  console.log("ok - trang BHXH tick đúng kỳ đóng theo nhãn rồi Lưu");

  // b) Hồ sơ KHÔNG kê khai mục 10 -> không được chọn hộ, phải báo cho cán bộ.
  radios.forEach((r) => { r.checked = false; });
  box.saved = false;
  const empty = { pages: { "thong-tin-bao-hiem-xa-hoi": [] }, done: [] };
  await box.step(empty);
  assert.ok(radios.every((r) => !r.checked), "hồ sơ không kê khai thì KHÔNG được tự chọn kỳ đóng");
  assert.ok(box.toasts.some((t) => /bảo hiểm xã hội/.test(t)), "phải báo để cán bộ chọn tay");
  assert.ok(empty.done.includes("thong-tin-bao-hiem-xa-hoi"), "vẫn phải sang trang kế, không kẹt");
  console.log("ok - không kê khai thì bỏ trống + nhắc chọn tay, không kẹt luồng");
})();
