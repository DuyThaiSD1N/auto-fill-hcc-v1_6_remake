/**
 * Popup "Địa chỉ thực hiện thủ tục" + "Mở trang kê khai".
 *
 * Chạy popup-locations.js và data/procedure-links.js trong sandbox có chrome/fetch giả để bắt đúng
 * lớp lỗi đã gặp: file không được nạp trong popup.html, hoặc popup.js trỏ sai tên global.
 */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const read = (rel) => fs.readFileSync(path.join(root, rel), "utf8");

// --- popup.html phải nạp đủ script dữ liệu TRƯỚC popup.js ---
const html = read("popup.html");
const order = ["popup-locations.js", "data/procedure-links.js", "popup.js"]
  .map((src) => html.indexOf(`src="${src}"`));
assert.ok(order.every((i) => i >= 0), "popup.html phải nạp popup-locations.js + data/procedure-links.js");
assert.ok(order[0] < order[2] && order[1] < order[2], "script dữ liệu phải đứng trước popup.js");

for (const id of ["provinceSelect", "wardSelect", "locationStatus", "locationSection",
  "procedureSection", "keKhaiSection", "keKhaiSelect", "keKhaiStatus",
  "destSection", "destPickers", "destGoBtn", "destBackBtn", "docsSection"]) {
  assert.ok(html.includes(`id="${id}"`), `popup.html thiếu #${id}`);
}
// Bỏ nút Lưu: chọn tỉnh/xã tới đâu ghi storage tới đó.
assert.ok(!html.includes('id="saveLocationBtn"'), "popup.html còn nút Lưu địa chỉ");
// --- một khối "Đi đến thủ tục": bung ô chọn rồi mới mở trang; KHÔNG còn 2 mode ---
assert.ok(!html.includes('class="view-modes"'), "vẫn còn thanh 2 chế độ");
assert.ok(!html.includes('id="modeAttachBtn"') && !html.includes('id="modeFullBtn"'),
  "vẫn còn nút chuyển chế độ");
assert.ok(!html.includes('id="openKeKhaiBtn"'), 'còn nút "Mở trang kê khai" riêng');
// Ô chọn phải ẩn sẵn: mở panel lên là thấy đúng màn đính kèm giấy tờ như cũ.
assert.match(html, /<div id="destPickers" hidden>/, "destPickers phải ẩn mặc định");

const popupJs = read("popup.js");
assert.match(popupJs, /async function persistLocation\(\)/, "popup.js phải tự lưu khi đổi lựa chọn");
// Địa chỉ mặc định lấy từ tài khoản, nhưng KHÔNG được đè lên lựa chọn cán bộ tự đổi.
assert.match(popupJs, /async function applyStoredLocation\(\)/, "thiếu áp địa chỉ mặc định");
assert.match(popupJs, /store\?\.locationFor\?\.\(currentUser\?\.tinh, currentUser\?\.xa\)/,
  "phải map tỉnh/xã của tài khoản qua locationFor");
assert.match(popupJs, /stored\.source === "manual" \|\| stored\.username === currentUser\?\.username/,
  "tự đổi hoặc cùng tài khoản thì giữ nguyên lựa chọn cũ");
assert.equal((popupJs.match(/currentLocation\.source = "manual";/g) || []).length, 2,
  "đổi tỉnh và đổi xã đều phải đánh dấu manual");
// /auth/me về sau khi khối địa chỉ đã dựng -> phải áp lại.
assert.match(popupJs, /userLabel\.textContent = user\?\.name[\s\S]{0,200}applyStoredLocation\(\)/,
  "đăng nhập xong phải áp lại địa chỉ mặc định của tài khoản");
assert.match(popupJs, /function applyDestOpen\(open\)/, "thiếu applyDestOpen");
assert.match(popupJs, /if \(procedureSection\) procedureSection\.hidden = showPickers;/,
  'đang chọn điểm đến phải ẩn combo "Loại thủ tục"');
// Bung khối điểm đến = màn chỉ còn việc chọn nơi đến; giấy tờ để lúc quay về hẵng lo.
assert.match(popupJs, /if \(docsSection\) docsSection\.hidden = showPickers;/,
  "bung khối Đi đến thủ tục phải ẩn khối Giấy tờ");
assert.match(popupJs, /if \(destBackBtn\) destBackBtn\.hidden = !showPickers;/,
  "nút Quay lại chỉ hiện khi đang bung");
assert.match(popupJs, /destBackBtn\?\.addEventListener\("click", \(\) => void setDestOpen\(false\)\);/,
  "nút Quay lại phải thu khối lại");
assert.match(html, /<button id="destBackBtn"[^>]*hidden>/, "destBackBtn phải ẩn mặc định");
// Nút mở trang ở TRÊN, quay lại ở DƯỚI.
assert.ok(html.indexOf('id="destGoBtn"') < html.indexOf('id="destBackBtn"'),
  "nút Mở trang phải nằm trên nút Quay lại");
assert.match(read("popup.css"), /\.dest-actions \{ display: flex; flex-direction: column; \}/,
  "hai nút phải xếp dọc, không nằm cùng hàng");

// --- 3 ô chọn dài phải là combobox có ô tìm kiếm + danh sách cuộn (không phải <select> trần) ---
for (const id of ["provinceSelect", "wardSelect", "keKhaiSelect"]) {
  const tag = html.slice(html.indexOf(`id="${id}"`), html.indexOf(`id="${id}"`) + 200);
  assert.match(tag, /combo-select-hidden/, `#${id} phải ẩn đi, thay bằng combobox`);
}
assert.match(popupJs, /function enhanceSelectWithSearch\(select, \{ searchPlaceholder \}\)/,
  "thiếu widget combobox có tìm kiếm");
// Phải phát `change` trên <select> gốc thì handler sẵn có (loadWards/persistLocation…) mới chạy.
assert.match(popupJs, /select\.dispatchEvent\(new Event\("change", \{ bubbles: true \}\)\)/,
  "chọn trong combobox phải phát change trên select gốc");
// Nạp dữ liệu bất đồng bộ không phát change -> phải đồng bộ nhãn tay ở cả 3 chỗ.
assert.equal((popupJs.match(/^\s*syncDestCombos\(\);$/gm) || []).length, 3,
  "phải đồng bộ nhãn sau: khôi phục địa chỉ, đổi tỉnh, nạp danh sách thủ tục");
const cssText = read("popup.css");
assert.match(cssText, /\.combo-list \{[^}]*max-height: 210px;[^}]*overflow-y: auto;/,
  "danh sách phải giới hạn chiều cao + có thanh kéo");
assert.match(cssText, /\.combo-search \{/, "thiếu style ô tìm kiếm");
assert.match(popupJs, /chrome\.storage\.onChanged\.addListener/,
  "phải nghe storage để tự thu khối sau khi vào hồ sơ");
assert.match(popupJs, /async function onKeKhaiProcedureChosen\(\)/, "thiếu đồng bộ pipeline");
assert.match(popupJs, /async function passInfoModalIfAny\(\)/, "thiếu bước xác nhận Thông tin chung");
assert.match(popupJs, /if \(!\(await passInfoModalIfAny\(\)\)\) return;/,
  '"Quét và nhập dữ liệu" phải qua modal trước khi gọi backend');

// --- content script: đủ chặng của luồng tro-ly + tín hiệu thu khối ---
const agency = read("content/agency-select.js");
for (const action of ["getPortalFlowState", "confirmInfoModal"]) {
  assert.ok(agency.includes(`"${action}"`), `content/agency-select.js thiếu action ${action}`);
}
assert.match(agency, /INFO_MODAL_TITLE = "thong tin chung"/, "thiếu nhận diện modal Thông tin chung");
assert.match(agency, /DEST_OPEN_KEY\]: false/, 'vào hồ sơ xong phải thu khối "Đi đến thủ tục"');
assert.match(agency, /async function confirmStage\(arm\)/, "thiếu chặng bấm Xác nhận");
assert.match(agency, /arm\.autoConfirm \? \{ \.\.\.arm, stage: "confirm"/,
  "chỉ thủ tục bật autoConfirm mới đi tiếp sang chặng Xác nhận");
assert.match(popupJs, /autoConfirm: !!link\.autoConfirm/, "popup phải gửi cờ autoConfirm sang content");
// Bước "Thông tin chủ hồ sơ": phải DẶN và CHẶN quét, vì cổng chưa dựng biểu mẫu kê khai.
assert.match(agency, /OWNER_STEP_MARKER = "thong tin chu ho so"/, "thiếu nhận diện bước chủ hồ sơ");
assert.match(agency, /OWNER_STEP_HINT =/, "thiếu câu dặn bấm Xác nhận");
assert.match(popupJs, /if \(state\.ownerInfo\) \{\s*setStatus\(state\.ownerStepHint, "warn"\);\s*return false;/,
  "ở bước chủ hồ sơ phải dặn và KHÔNG gọi backend");
// Cổng khác phải trả unsupported ngay, không để popup chờ hết vòng retry inject.
assert.match(read("content.js"), /getPortalFlowState[\s\S]{0,400}unsupported: true/,
  "content.js thiếu fallback unsupported cho cổng khác");

// --- manifest phải khai báo web_accessible_resources cho script popup dùng ---
const manifest = JSON.parse(read("manifest.json"));
const war = manifest.web_accessible_resources[0].resources;
assert.ok(war.includes("popup-locations.js"), "manifest thiếu popup-locations.js");
assert.ok(war.includes("data/*"), "manifest thiếu data/*");

// --- popup.js phải dùng ĐÚNG global mà popup-locations.js export ---
assert.match(popupJs, /window\.popupLocationManager/, "popup.js phải đọc window.popupLocationManager");

// --- chạy thật hai file dữ liệu ---
const dataUrl = path.join(root, "data", "vn_provinces_wards.json");
const sandbox = {
  console,
  chrome: { runtime: { getURL: (p) => path.join(root, p) } },
  fetch: async (p) => ({ json: async () => JSON.parse(fs.readFileSync(p, "utf8")) }),
};
sandbox.window = sandbox;
vm.runInNewContext(read("popup-locations.js"), sandbox, { filename: "popup-locations.js" });
vm.runInNewContext(read("data/procedure-links.js"), sandbox, { filename: "procedure-links.js" });

(async () => {
  const store = sandbox.window.popupLocationManager;
  assert.ok(store, "popup-locations.js phải export window.popupLocationManager");
  await store.load();

  const provinces = store.getProvinces();
  assert.equal(provinces.length, 34, "phải có 34 tỉnh/thành sau sáp nhập");
  const lamDong = provinces.find((p) => p.name === "Lâm Đồng");
  assert.ok(lamDong, "thiếu Lâm Đồng");
  assert.equal(lamDong.text, "Tỉnh Lâm Đồng");

  const wards = store.getWards(lamDong.slug);
  assert.ok(wards && wards.communes.length > 0, "Lâm Đồng phải có danh sách phường/xã");
  assert.ok(wards.communes.includes("Xã Đơn Dương"), "thiếu Xã Đơn Dương trong Lâm Đồng");
  assert.equal(store.getWards("khong-co-tinh-nay"), null);

  // --- tỉnh/xã gắn trong tài khoản -> địa chỉ mặc định (cùng hợp đồng location_for bên tro-ly) ---
  assert.deepEqual({ ...store.locationFor("Tỉnh Lâm Đồng", "Xã Đơn Dương") },
    { province: "Tỉnh Lâm Đồng", provinceSlug: lamDong.slug, ward: "Xã Đơn Dương" });
  // Tên ngắn (tài khoản hay lưu kiểu này) vẫn phải khớp.
  assert.deepEqual({ ...store.locationFor("Lâm Đồng", "Đơn Dương") },
    { province: "Tỉnh Lâm Đồng", provinceSlug: lamDong.slug, ward: "Xã Đơn Dương" });
  // Khớp tỉnh nhưng xã sai -> ward rỗng, KHÔNG đoán bừa.
  assert.equal(store.locationFor("Lâm Đồng", "Xã Không Có").ward, "");
  assert.equal(store.locationFor("Tỉnh Không Tồn Tại", "Xã Đơn Dương"), null);
  assert.equal(store.locationFor("", ""), null);

  // --- link kê khai: trùng key với registry của tro-ly-nguoi-dan-backend ---
  const links = sandbox.window.PROCEDURE_KE_KHAI_LINKS;
  assert.equal(links.length, 13, "phải có đủ 13 thủ tục có keKhaiUrl");
  const registry = fs.readFileSync(
    path.join(root, "..", "tro-ly-nguoi-dan-backend", "app", "procedures", "registry.py"), "utf8");
  for (const item of links) {
    assert.ok(item.key && item.label && /^https:\/\//.test(item.url), `link hỏng: ${item.key}`);
    assert.ok(registry.includes(`"${item.url}"`), `URL không khớp registry: ${item.key}`);
    assert.ok(registry.includes(`"key": "${item.key}"`), `key không có trong registry: ${item.key}`);
  }
  // autoConfirm chỉ dành cho nhóm cổng React (needsAgencySelect) — liên thông không có modal này.
  for (const item of links) {
    assert.equal(typeof item.autoConfirm, "boolean", `${item.key} thiếu cờ autoConfirm`);
    if (item.autoConfirm) {
      assert.equal(item.needsAgencySelect, true,
        `${item.key}: autoConfirm chỉ áp dụng cho thủ tục qua khối chọn cơ quan`);
    }
  }
  const keys = links.map((item) => item.key);
  assert.equal(new Set(keys).size, keys.length, "key trùng nhau trong procedure-links.js");

  console.log("popup location picker + ke khai links: passed");
})();
