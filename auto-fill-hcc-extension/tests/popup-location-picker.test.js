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
  "destSection", "destPickers", "destGoBtn", "docsSection"]) {
  assert.ok(html.includes(`id="${id}"`), `popup.html thiếu #${id}`);
}
// Bỏ nút Lưu: chọn tỉnh/xã tới đâu ghi storage tới đó.
assert.ok(!html.includes('id="saveLocationBtn"'), "popup.html còn nút Lưu địa chỉ");
// --- khối "Đi đến thủ tục" TỰ hiện theo trang: không còn nút bật/tắt, không còn nút quay lại ---
assert.ok(!html.includes('class="view-modes"'), "vẫn còn thanh 2 chế độ");
assert.ok(!html.includes('id="modeAttachBtn"') && !html.includes('id="modeFullBtn"'),
  "vẫn còn nút chuyển chế độ");
assert.ok(!html.includes('id="openKeKhaiBtn"'), 'còn nút "Mở trang kê khai" riêng');
assert.ok(!html.includes('id="destBackBtn"'), "còn nút Quay lại — giờ panel tự đổi màn");
assert.match(html, /<section class="block" id="destSection" hidden>/,
  "khối điểm đến phải ẩn sẵn, chờ biết đang ở trang nào mới hiện");

const popupJs = read("popup.js");
assert.match(popupJs, /async function persistLocation\(\)/, "popup.js phải tự lưu khi đổi lựa chọn");
assert.match(popupJs, /async function refreshDestVisibility\(\)/, "thiếu tự đổi màn theo trang");
assert.match(popupJs, /!!state\.atPortalHome/,
  "chỉ hiện khối điểm đến khi đang ở trang chủ/tra cứu DVC");
assert.match(popupJs, /msg\?\.action === "portalFlowChanged"/,
  "phải nghe tin đổi trang từ content script (SPA không tải lại trang)");
assert.match(popupJs, /if \(procedureSection\) procedureSection\.hidden = showDest;/,
  'đang chọn điểm đến phải ẩn combo "Loại thủ tục"');
assert.match(popupJs, /if \(docsSection\) docsSection\.hidden = showDest;/,
  "đang chọn điểm đến phải ẩn khối Giấy tờ");
assert.match(popupJs, /async function onKeKhaiProcedureChosen\(\)/, "thiếu đồng bộ pipeline");
assert.match(popupJs, /async function passInfoModalIfAny\(\)/, "thiếu bước xác nhận Thông tin chung");
assert.match(popupJs, /if \(!\(await passInfoModalIfAny\(\)\)\) return;/,
  '"Quét và nhập dữ liệu" phải qua modal trước khi gọi backend');

// --- content script: báo trạng thái trang + đủ chặng của luồng tro-ly ---
const agency = read("content/agency-select.js");
for (const action of ["getPortalFlowState", "confirmInfoModal"]) {
  assert.ok(agency.includes(`"${action}"`), `content/agency-select.js thiếu action ${action}`);
}
assert.match(agency, /INFO_MODAL_TITLE = "thong tin chung"/, "thiếu nhận diện modal Thông tin chung");
assert.match(agency, /atPortalHome: !\(onProcedurePage \|\| infoModal \|\| ownerInfo \|\| ready\)/,
  "atPortalHome phải là: chưa dính tới thủ tục nào");
assert.match(agency, /action: "portalFlowChanged"/, "phải báo popup khi trang đổi");
assert.ok(!agency.includes("DEST_OPEN_KEY"), "bỏ hẳn cờ storage cũ, giờ tự nhận theo trang");
assert.match(agency, /async function confirmStage\(arm\)/, "thiếu chặng bấm Xác nhận");
assert.match(agency, /arm\.autoConfirm \? \{ \.\.\.arm, stage: "confirm"/,
  "chỉ thủ tục bật autoConfirm mới đi tiếp sang chặng Xác nhận");
assert.match(popupJs, /autoConfirm: !!link\.autoConfirm/, "popup phải gửi cờ autoConfirm sang content");
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
