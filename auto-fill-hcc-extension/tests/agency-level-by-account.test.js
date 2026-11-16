// Thủ tục "Sở hoặc UBND xã" (agencyLevelByAccount): HCC tỉnh → Sở; tài khoản khác có xã đang chọn → UBND xã;
// chưa có xã → Sở. Cùng luật với BE app/procedures/agency_level.py.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const SRC = fs.readFileSync(path.join(__dirname, "..", "popup.js"), "utf8");

function extractFunction(name) {
  const start = SRC.indexOf(`function ${name}(`);
  assert.ok(start >= 0, `thiếu hàm ${name}`);
  let depth = 0;
  for (let i = SRC.indexOf("{", start); i < SRC.length; i += 1) {
    if (SRC[i] === "{") depth += 1;
    else if (SRC[i] === "}" && (depth -= 1) === 0) return SRC.slice(start, i + 1);
  }
  throw new Error(`không tách được ${name}`);
}

function load(role, ward) {
  const body = ["agencyLevelFor", "withAgencyLevel", "selectSoFor", "submitCardIncludesFor"]
    .map(extractFunction).join("\n");
  // eslint-disable-next-line no-new-func
  return new Function("currentUser", "agencyLocationFor",
    `${body}\nreturn { selectSoFor, submitCardIncludesFor };`,
  )({ role }, () => ({ province: "Tỉnh A", provinceSlug: "a", ward }));
}

const LINK = {
  key: "cap-gcn-attp-co-so-kinh-doanh-dich-vu-an-uong-byt",
  // BE trải sẵn nhánh theo tài khoản vào trường cũ — bản mới phải chọn lại theo xã đang chọn.
  selectSo: true,
  submitCardIncludes: "Cơ quan thực hiện: Sở Y tế",
  agencyLevelByAccount: {
    xa: { selectSo: false, submitCardIncludes: "Cơ quan thực hiện: UBND" },
    so: { selectSo: true, submitCardIncludes: "Cơ quan thực hiện: Sở Y tế" },
  },
};

for (const [role, ward, so, card] of [
  ["province", "Xã B", true, "Cơ quan thực hiện: Sở Y tế"],
  ["commune", "Xã B", false, "Cơ quan thực hiện: UBND"],
  ["user", "Xã B", false, "Cơ quan thực hiện: UBND"],
  ["user", "", true, "Cơ quan thực hiện: Sở Y tế"],
  ["commune", "", true, "Cơ quan thực hiện: Sở Y tế"],
]) {
  test(`${role} + xã "${ward}" → ${so ? "Sở" : "UBND xã"}`, () => {
    const fns = load(role, ward);
    assert.strictEqual(fns.selectSoFor(LINK), so);
    assert.strictEqual(fns.submitCardIncludesFor(LINK), card);
  });
}

// Lào Cai cấp Sở: luôn tick Sở; HCC tỉnh bấm thẻ Sở NN&MT, tài khoản xã bấm thẻ "Chi nhánh VPĐKĐĐ khu vực …" của xã.
// BE đã trải nhánh "xa" của tài khoản xã vào trường cũ → nhánh "so" phải xoá bảng theo xã bằng {}.
const LAO_CAI_SO = "Sở Nông nghiệp và Môi trường tỉnh Lào Cai";
const LAO_CAI_BY_WARD = { "Xã Mường Lai": "khu vực Lục Yên", "Phường Cam Đường": "khu vực Lào Cai - Cam Đường" };
const LAO_CAI_LINK = {
  key: "giao-dat-cho-thue-dat-lao-cai",
  selectSo: true,
  submitCardIncludes: LAO_CAI_SO,
  submitCardIncludesByWard: LAO_CAI_BY_WARD,
  agencyLevelByAccount: {
    so: { submitCardIncludesByWard: {} },
    xa: { submitCardIncludesByWard: LAO_CAI_BY_WARD },
  },
};

for (const [role, ward, card] of [
  ["province", "Phường Cam Đường", LAO_CAI_SO],
  ["province", "", LAO_CAI_SO],
  ["commune", "Xã Mường Lai", "khu vực Lục Yên"],
  ["commune", "Phường Cam Đường", "khu vực Lào Cai - Cam Đường"],
  ["commune", "", LAO_CAI_SO],
]) {
  test(`Lào Cai: ${role} + xã "${ward}" → ${card}`, () => {
    const fns = load(role, ward);
    assert.strictEqual(fns.selectSoFor(LAO_CAI_LINK), true);
    assert.strictEqual(fns.submitCardIncludesFor(LAO_CAI_LINK), card);
  });
}

test("thủ tục không khai agencyLevelByAccount giữ nguyên cấu hình", () => {
  const fns = load("commune", "Xã B");
  const link = { selectSo: true, submitCardIncludes: "Cơ quan thực hiện: Sở X" };
  assert.strictEqual(fns.selectSoFor(link), true);
  assert.strictEqual(fns.submitCardIncludesFor(link), "Cơ quan thực hiện: Sở X");
});

test("đi vòng chép cả agencyLevelByAccount của link cầu", () => {
  const src = fs.readFileSync(path.join(__dirname, "..", "popup-ke-khai-di-vong.js"), "utf8");
  assert.match(src, /TRUONG_TRANG_DVC = \[[^\]]*"agencyLevelByAccount"/);
});
