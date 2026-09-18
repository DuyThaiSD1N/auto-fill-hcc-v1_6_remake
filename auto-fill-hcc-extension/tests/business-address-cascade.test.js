// Cascade địa chỉ trên cổng hộ kinh doanh (HkdOnline): mỗi cấp <select> là AutoPostBack, cổng dựng
// LẠI ô cấp dưới sau mỗi lần đổi. Test dựng đúng độ trễ đó để chốt: điền nhanh hơn postback thì
// KHÔNG được bỏ Phường/Xã, và giá trị bị postback xoá thì phải chọn lại.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const WARDS = {
  "Thành phố Đà Nẵng": ["Phường Hải Châu", "Phường Thanh Khê", "Xã Hòa Vang"],
  "Tỉnh Quảng Nam": ["Phường Điện Bàn", "Xã Duy Nghĩa"],
};

// <select> giả: đủ cho areaFold/areaFindOption/areaChoose + dấu vết node & danh sách option.
function makeSelect(name, labels = []) {
  const sel = {
    name,
    value: "",
    options: [],
    dispatchEvent(ev) { if (ev.type === "change") this.onchange?.(); return true; },
    onchange: null,
  };
  sel.setOptions = (list) => {
    sel.options = list.map((label) => ({ value: label, textContent: label }));
  };
  Object.defineProperty(sel, "selectedOptions", {
    get: () => sel.options.filter((o) => o.value === sel.value),
  });
  sel.setOptions(labels);
  return sel;
}

/**
 * Cổng giả. `wardDelay` = độ trễ postback của ô Tỉnh: đến khi postback về thì ô Phường/Xã mới có
 * danh sách của tỉnh vừa chọn. `wipeWardOnce` = postback về SAU khi ta đã chọn xã và xoá mất nó
 * (đúng cảnh cổng thật hay gặp).
 */
function makePortal({ wardDelay = 700, staleWards = [], wipeWardOnce = false } = {}) {
  const street = { name: "STREET_NUMBERFld", value: "" };
  const state = {
    country: makeSelect("COUNTRY_IDFld", ["Việt Nam"]),
    city: makeSelect("CITY_IDFld", Object.keys(WARDS)),
    ward: makeSelect("WARD_IDFld", staleWards),
    street,
    wardRebuilds: 0,
  };
  let wipesLeft = wipeWardOnce ? 1 : 0;

  // Đổi Quốc gia cũng là một postback: cổng dựng lại ô Tỉnh/Thành (cascade thật của cổng).
  state.country.onchange = () => {
    setTimeout(() => {
      state.city = makeSelect("CITY_IDFld", Object.keys(WARDS));
      state.city.onchange = onCityChange;
    }, wardDelay);
  };
  function onCityChange() {
    const wanted = WARDS[state.city.value] || [];
    setTimeout(() => {
      // Postback về: cổng THAY node ô Phường/Xã bằng node mới, danh sách của tỉnh vừa chọn.
      state.ward = makeSelect("WARD_IDFld", wanted);
      state.ward.onchange = onWardChange;
      state.wardRebuilds += 1;
      street.value = ""; // khối dựng lại xoá luôn ô Số nhà
    }, wardDelay);
  }
  state.city.onchange = onCityChange;
  function onWardChange() {
    if (wipesLeft <= 0) return;
    wipesLeft -= 1;
    const wanted = WARDS[state.city.value] || [];
    setTimeout(() => {
      state.ward = makeSelect("WARD_IDFld", wanted);
      state.ward.onchange = onWardChange;
      state.wardRebuilds += 1;
    }, wardDelay);
  }
  state.ward.onchange = onWardChange;
  return state;
}

function runCascade(portal, fields) {
  const sandbox = {
    console: { log() {}, warn() {}, error() {} },
    Event: class { constructor(type) { this.type = type; } },
    MouseEvent: class {},
    setTimeout,
    clearTimeout,
    Date,
    Array,
    String,
    RegExp,
    Object,
    getComputedStyle: () => ({ display: "block", visibility: "visible" }),
    chrome: { storage: { local: { get() {}, set() {}, remove() {} } }, runtime: {} },
    document: {
      getElementById: () => null,
      querySelector: () => null,
      querySelectorAll: () => [],
      forms: { namedItem: () => null },
    },
  };
  const pick = (names) => {
    const want = String(names[0] || "");
    if (/COUNTRY/.test(want)) return portal.country;
    if (/CITY/.test(want)) return portal.city;
    if (/WARD/.test(want)) return portal.ward;
    return null;
  };
  sandbox.window = {
    location: { pathname: "/HkdOnline/Forms/APP/Registration.aspx" },
    __HCC__: {
      sleep: (ms) => new Promise((r) => setTimeout(r, ms)),
      norm: (v) => String(v || "").trim().toLowerCase().replace(/\s+/g, " "),
      fieldCandidates: (f) => [f.name],
      setNativeValue: (el, value) => { el.value = value; },
      async waitFor(fn, timeout = 3000, interval = 100) {
        const start = Date.now();
        while (Date.now() - start < timeout) {
          const v = fn();
          if (v) return v;
          await new Promise((r) => setTimeout(r, interval));
        }
        return null;
      },
      readAcctContact: () => "",
      fillFormStandard: async () => {},
      findStandardInput: (names) => (/STREET/.test(String(names[0] || "")) ? portal.street : null),
      findStandardSelect: pick,
      isPostbackAddressField: () => true,
    },
    addEventListener() {},
  };
  const source = fs.readFileSync(
    path.join(__dirname, "..", "content", "procedures", "business-registration.js"),
    "utf8",
  );
  vm.runInNewContext(source, sandbox, { filename: "business-registration.js" });
  return sandbox.window.__HCC__.fillAddressCascade(fields);
}

const fieldsFor = (city, ward) => [
  { name: "ctl00$C$PERSCtl$ADDRCCtl$COUNTRY_IDFld", comp: "dom-select", value: "Việt Nam" },
  { name: "ctl00$C$PERSCtl$ADDRCCtl$CITY_IDFld", comp: "dom-select", value: city },
  { name: "ctl00$C$PERSCtl$ADDRCCtl$WARD_IDFld", comp: "dom-select", value: ward },
  { name: "ctl00$C$PERSCtl$ADDRCCtl$STREET_NUMBERFld", comp: "dom-input", value: "12 Lê Lợi" },
];

(async () => {
  // 1. Postback ô Tỉnh về CHẬM (700ms): ô Phường/Xã lúc ta đọc còn rỗng. Bản cũ bỏ cấp xã ngay tại
  //    đây ("chưa có option") — đúng lỗi cán bộ gặp. Bản mới phải CHỜ danh sách rồi chọn được.
  let portal = makePortal({ wardDelay: 700 });
  await runCascade(portal, fieldsFor("Thành phố Đà Nẵng", "Phường Hải Châu"));
  assert.equal(portal.city.value, "Thành phố Đà Nẵng", "Tỉnh phải vào");
  assert.equal(portal.ward.value, "Phường Hải Châu", "Phường/Xã phải vào dù postback Tỉnh về chậm");

  // 2. Ô Phường/Xã còn danh sách của TỈNH TRƯỚC và tình cờ có tên xã đích: bản cũ chọn vào node
  //    sắp bị thay nên postback về là xã trắng. Bản mới phải kết thúc với xã đã vào node MỚI.
  portal = makePortal({ wardDelay: 600, staleWards: ["Phường Hải Châu", "Xã Cũ"] });
  await runCascade(portal, fieldsFor("Thành phố Đà Nẵng", "Phường Hải Châu"));
  assert.ok(portal.wardRebuilds >= 1, "cổng phải đã dựng lại ô Phường/Xã");
  assert.equal(portal.ward.value, "Phường Hải Châu", "xã phải nằm trên node sau cùng, không phải node cũ");

  // 3. Postback của chính ô Phường/Xã xoá mất giá trị vừa chọn → phải chọn LẠI trên node mới.
  portal = makePortal({ wardDelay: 500, wipeWardOnce: true });
  await runCascade(portal, fieldsFor("Tỉnh Quảng Nam", "Xã Duy Nghĩa"));
  assert.equal(portal.ward.value, "Xã Duy Nghĩa", "xã bị postback xoá thì phải được chọn lại");

  // 4. Số nhà điền SAU khi cascade đã lắng: postback dựng lại khối không được xoá mất nó.
  assert.equal(portal.street.value, "12 Lê Lợi", "Số nhà phải còn sau mọi postback");

  // 5. Hồ sơ ghi "Hòa Vang", cổng ghi "Xã Hòa Vang": khớp lỏng đã chọn đúng thì KHÔNG được coi là
  //    trượt (coi là trượt thì cấp dưới bị bỏ oan và vòng 2 chọn lại vô ích).
  portal = makePortal({ wardDelay: 300 });
  await runCascade(portal, fieldsFor("Đà Nẵng", "Hòa Vang"));
  assert.equal(portal.city.value, "Thành phố Đà Nẵng");
  assert.equal(portal.ward.value, "Xã Hòa Vang");

  // 6. Không chọn được Tỉnh (hồ sơ ghi tỉnh không có trong danh sách) → BỎ Phường/Xã, không ghi xã
  //    của tỉnh khác vào hồ sơ.
  portal = makePortal({ wardDelay: 300, staleWards: ["Phường Hải Châu"] });
  await runCascade(portal, fieldsFor("Tỉnh Không Tồn Tại", "Phường Hải Châu"));
  assert.equal(portal.city.value, "", "không khớp tỉnh thì không chọn bừa");
  assert.equal(portal.ward.value, "", "Tỉnh chưa vào thì không được chọn xã theo danh sách tỉnh khác");

  console.log("business-address-cascade: OK");
})();
