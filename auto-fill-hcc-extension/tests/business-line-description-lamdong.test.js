// Tài khoản tỉnh Lâm Đồng: ô mô tả TỪNG DÒNG ngành nghề phải để TRỐNG (chỉ giữ tên ngành chính thức
// cổng tự điền theo mã VSIC). Quy tắc này từng bị mất khi thay nguyên thư mục extension bằng bản FE
// mới, nên khoá lại bằng test ở CẢ HAI đầu: popup.js bật cờ, content script tuân theo cờ.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

// ---- Đầu 1: popup.js gắn cờ skipBusinessLineDescription theo tỉnh của tài khoản ----
const popupSource = fs.readFileSync(path.join(__dirname, "..", "popup.js"), "utf8");
const popupStart = popupSource.indexOf("function normalizeProcedureSearch(value)");
const popupEnd = popupSource.indexOf("\nfunction selectedProcedureConfig", popupStart);
assert.ok(popupStart >= 0 && popupEnd > popupStart, "Không tách được khối default theo địa bàn của popup.js");

const popupSandbox = {};
vm.runInNewContext(`
  ${popupSource.slice(popupStart, popupEnd)}
  globalThis.buildDefaults = buildBusinessDefaults;
`, popupSandbox);

const lamDong = popupSandbox.buildDefaults({ username: "ldxuanhuong", xa: "Phường Xuân Hương", tinh: "Tỉnh Lâm Đồng" });
assert.equal(lamDong.skipBusinessLineDescription, true, "Tài khoản Lâm Đồng phải bật cờ bỏ trống ô mô tả ngành nghề");
assert.ok(lamDong.businessActText, "Xuân Hương vẫn giữ ghi chú ô 'Ngành, nghề chưa khớp mã' — đó là ô khác");

assert.equal(
  popupSandbox.buildDefaults({ xa: "Xã Đơn Dương", tinh: "Tỉnh Lâm Đồng" }).skipBusinessLineDescription,
  true,
  "Quy tắc áp cho MỌI xã/phường của tỉnh Lâm Đồng, không riêng Xuân Hương",
);
assert.equal(
  popupSandbox.buildDefaults({ xa: "Phường Hải Châu", tinh: "Đà Nẵng" }).skipBusinessLineDescription,
  undefined,
  "Tỉnh khác không được dính quy tắc của Lâm Đồng",
);
assert.equal(popupSandbox.buildDefaults({ tinh: "Hà Nội", xa: "Phường Láng" }), null);

// ---- Đầu 2: content script bỏ qua ô mô tả khi thấy cờ ----
const contentSource = fs.readFileSync(
  path.join(__dirname, "..", "content", "procedures", "business-registration.js"), "utf8");
const fnStart = contentSource.indexOf("function fillBusinessLineDescriptions(nn, defaults)");
const fnEnd = contentSource.indexOf("\n  function findBusinessLineUpdateButton", fnStart);
assert.ok(fnStart >= 0 && fnEnd > fnStart, "Không tách được fillBusinessLineDescriptions (chữ ký phải nhận defaults)");

let written = 0;
const contentSandbox = {
  console: { log() {}, warn() {} },
  getBusinessLineNameByCode: () => ({ 4632: "Bán buôn thực phẩm (bán buôn rau, quả)" }),
  findBusinessRowByCode: () => ({}),
  getBusinessRowDescription: () => ({ value: "" }),
  getBusinessRowOfficialName: () => "Bán buôn thực phẩm",
  foldBusinessLineName: (value) => String(value || "").toLowerCase().trim(),
  shouldFillBusinessDescription: (official, extracted) => official !== extracted,
  setNativeValue: () => { written += 1; },
};
vm.runInNewContext(`
  ${contentSource.slice(fnStart, fnEnd)}
  globalThis.fill = fillBusinessLineDescriptions;
`, contentSandbox);

assert.equal(contentSandbox.fill({ items: [] }, { skipBusinessLineDescription: true }), 0,
  "Có cờ thì không được ghi gì vào ô mô tả");
assert.equal(written, 0, "Có cờ thì tuyệt đối không gọi setNativeValue lên ô mô tả");

assert.equal(contentSandbox.fill({ items: [] }, null), 1,
  "Không có cờ thì vẫn ghi mô tả như cũ (tên đọc từ hồ sơ khác tên chính thức)");
assert.equal(written, 1);

// Cả hai chỗ gọi đều phải truyền defaults xuống, nếu không cờ vô nghĩa.
const callSites = contentSource.match(/fillBusinessLineDescriptions\([^)]*\)/g)
  .filter((call) => !call.startsWith("fillBusinessLineDescriptions(nn, defaults"));
assert.ok(callSites.length >= 2, "Phải còn đủ các chỗ gọi fillBusinessLineDescriptions");
for (const call of callSites) {
  assert.ok(call.includes("st.businessDefaults"), `Chỗ gọi thiếu defaults: ${call}`);
}

console.log("ok - Lâm Đồng bỏ trống ô mô tả ngành nghề");
