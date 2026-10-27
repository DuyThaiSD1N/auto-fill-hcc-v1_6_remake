// "Kính gửi" / "Tại" theo cơ quan đã chọn ở thẻ "Chọn cơ quan thực hiện", gắn theo departmentId của trang nộp hồ sơ;
// mở thẳng trang nộp (mã cơ quan lạ) thì vẫn theo tài khoản.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const source = fs.readFileSync(path.join(root, "content/chosen-agency.js"), "utf8");

function load(store = {}) {
  const local = {
    async get(keys) { return Object.fromEntries(keys.filter((k) => k in store).map((k) => [k, store[k]])); },
    async set(items) { Object.assign(store, items); },
    async remove(key) { delete store[key]; },
  };
  const ns = {};
  // top khác window → bỏ qua phần theo dõi DOM, chỉ nạp hàm.
  const window = { __HCC__: ns, top: {} };
  vm.runInNewContext(source, { window, chrome: { storage: { local } }, URL, Date });
  return { api: ns.chosenAgency, store };
}

const PAGE = "https://dichvucong.gov.vn/nop-ho-so?formalityId=f1&departmentId=dep-lang-biang";
const ACCOUNT = { tinh: "Lâm Đồng", xa: "Phường Cam Ly - Đà Lạt" };

test("đọc departmentId chỉ ở trang nộp hồ sơ", () => {
  const { api } = load();
  assert.strictEqual(api.departmentIdOf(PAGE), "dep-lang-biang");
  assert.strictEqual(api.departmentIdOf("https://dichvucong.gov.vn/thu-tuc-hanh-chinh/x?departmentId=a"), "");
});

test("vừa chọn xong sang trang nộp → Kính gửi/Tại theo nơi đã chọn, không theo tài khoản", async () => {
  const pending = { tinh: "Tỉnh Lâm Đồng", xa: "Phường Lang Biang - Đà Lạt", at: Date.now() };
  const { api, store } = load({ chosen_agency_pending: pending });
  const place = await api.placeForPage(PAGE, ACCOUNT);
  assert.deepStrictEqual([place.xa, place.tinh, place.source], [pending.xa, pending.tinh, "chosen"]);
  assert.ok(!("chosen_agency_pending" in store), "lựa chọn chờ đã gắn thì xoá");
  // Hồ sơ sau cùng cơ quan, không đi qua bước chọn nữa → vẫn dùng nơi đã chọn.
  assert.strictEqual((await api.placeForPage(PAGE, ACCOUNT)).source, "chosen");
});

test("mở thẳng trang nộp của cơ quan chưa từng chọn → theo tài khoản", async () => {
  const { api } = load({ chosen_agency_by_department: { other: { tinh: "A", xa: "B", at: 1 } } });
  const place = await api.placeForPage(PAGE, ACCOUNT);
  assert.deepStrictEqual([place.xa, place.source], [ACCOUNT.xa, "account"]);
});

test("lựa chọn chờ quá cũ (lượt bỏ dở) không được gắn", () => {
  const { api } = load();
  assert.strictEqual(api.bindPending({}, { xa: "X", at: 0 }, "dep", 3 * 60 * 60 * 1000), null);
  assert.strictEqual(api.bindPending({}, null, "dep", 1), null);
  assert.ok(api.bindPending({}, { xa: "X", at: 0 }, "dep", 1000).dep);
});

test("chọn lại cùng cơ quan thì ghi đè; giữ tối đa 50 cơ quan gần nhất", () => {
  const { api } = load();
  let map = api.bindPending({}, { xa: "Cũ", at: 1 }, "dep", 2);
  map = api.bindPending(map, { xa: "Mới", at: 3 }, "dep", 4);
  assert.strictEqual(map.dep.xa, "Mới");
  for (let i = 0; i < 60; i += 1) map = api.bindPending(map, { xa: `X${i}`, at: 10 + i }, `d${i}`, 10 + i);
  assert.strictEqual(Object.keys(map).length, 50);
  assert.ok(map.d59 && !map.dep);
});

test("engine SurveyJS hỏi nơi đã chọn trước khi điền Kính gửi / Tại; manifest nạp module trước engine", () => {
  const fill = fs.readFileSync(path.join(root, "content/fill-surveyjs.js"), "utf8");
  assert.ok(fill.indexOf("H.chosenAgency.placeForPage(location.href, toolAccount)") <
            fill.indexOf('op: "fillPlace"'));
  const scripts = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8")).content_scripts
    .flatMap((entry) => entry.js || []);
  assert.ok(scripts.indexOf("content/chosen-agency.js") > -1 &&
            scripts.indexOf("content/chosen-agency.js") < scripts.indexOf("content/fill-surveyjs.js"));
});
