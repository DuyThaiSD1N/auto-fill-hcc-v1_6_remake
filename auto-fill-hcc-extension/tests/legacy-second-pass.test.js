// Điền đợt 2 trên form cũ (eForm x-*): BE soát lại sau lượt điền đầu, engine ghi lại RIÊNG các ô BE sửa — không đè ô
// cán bộ đã sửa tay, không xoá màu của lượt điền đầu, và chỉ thủ tục khai năng lực riêng mới chạy.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const read = (p) => fs.readFileSync(path.join(root, p), "utf8").replace(/^\s*\/\/.*$/gm, "");
const legacy = read("content/fill-legacy.js");
const patch = legacy.slice(legacy.indexOf("function legacyPatchUntouched"), legacy.indexOf("H.readLegacyField ="));

test("chỉ ghi ô còn trống hoặc còn đúng giá trị lượt đầu", () => {
  assert.match(patch, /const shown = readLegacyComponent\(found\.el\);\s*if \(shown === ""\) return true;/);
  assert.match(patch, /return legacyAreaPatchUntouched\(shown, field\.from\);/);
  assert.match(patch, /return !!legacyFieldState\(\{ \.\.\.field, value: field\.from, clear: false \}\)\.filled;/);
  assert.match(patch, /if \(untouched === false \|\| \(untouched === null && !isNew\)\) \{[\s\S]{0,200}reason: untouched === false \? "changed" : "not-found"/);
});

test("không chạy lại cả lượt điền: không xoá màu, không tô đỏ ô trống, không cài bộ giữ ổn định", () => {
  const body = patch.slice(patch.indexOf("async function patchFormLegacy"));
  assert.doesNotMatch(body, /clearAutofillMarks\(|markAllEmptyFieldsRed\(|armLegacyStabilityGuard\(|armLegacyRelationKeeper\(/);
  assert.match(body, /refreshRequestedLegacyMarks\(done\);\s*markLegacyDefaultsYellow\(done\);/);
});

test("khối địa bàn đã điền ở lượt đầu được ghi lại bằng bộ điền widget; khối động chờ cổng dựng", () => {
  assert.match(patch, /hasDivorceDecisionAreaValue\(area\) && \(area\.tinh \|\| area\.xa\)\s*\? await fillAreaWidgets\(found\.el, area\)\s*: await fillLegacyComponent\(found\.el, ff\);/);
  assert.match(patch, /if \(!found\.el && f\.comp === "x-select-area"\) \{\s*await waitFor\(/);
});

test("engine xuất bộ ghi lại ô và handler patchFields gọi đúng bộ theo nền tảng form", () => {
  assert.match(legacy, /H\.patchFormLegacy = patchFormLegacy;/);
  const handler = read("content.js");
  assert.match(handler, /const patcher = formKind === "surveyjs" \? H\.patchFormSurveyJs\s*: formKind === "legacy" \? H\.patchFormLegacy : formKind === "angular" \? H\.patchFormAngular : null;/);
  assert.match(handler, /Promise\.resolve\(\)\.then\(\(\) => \(canPatch \? patcher\(patch\) : \{ filled: 0, skipped: \[\] \}\)\)/);
});

test("khai năng lực riêng cho form cũ", () => {
  assert.match(read("popup.js"), /options\.fillSupports = \["secondPass", "secondPassLegacy", "secondPassAngular", "secondPassArea"\];/);
});

test("khối địa chỉ: phần lượt đầu không ghi lên được / không gửi thì vẫn ghi lại, phần đã ghi rồi bị đổi thì bỏ qua", () => {
  const src = fs.readFileSync(path.join(root, "content/fill-legacy.js"), "utf8");
  const grab = (name) => {
    const at = src.indexOf(`function ${name}(`);
    let depth = 0;
    for (let i = src.indexOf("{", at); i < src.length; i++) {
      if (src[i] === "{") depth++;
      else if (src[i] === "}" && --depth === 0) return src.slice(at, i + 1);
    }
    return "";
  };
  const norm = (s) => String(s ?? "").normalize("NFC").toLowerCase().replace(/\s+/g, " ").trim();
  const untouched = new Function("norm", [
    grab("legacyScalarMatches"), grab("legacyChoiceMatches"), grab("normalizeAreaValue"), grab("legacyAreaPatchUntouched"),
    "return legacyAreaPatchUntouched;",
  ].join("\n"))(norm);
  const first = { quocGia: "Việt Nam", tinh: "Bắc Ninh", xa: "Yên Tập", diaChi: "" };
  // Xã lượt đầu không có trên cổng (ô trống), địa chỉ cổng điền sẵn theo tài khoản → chưa ai sửa.
  assert.equal(untouched({ quocGia: "Việt Nam", tinh: "Thành phố Bắc Ninh", diaChi: "Xóm A" }, first), true);
  // Cán bộ đã chọn xã khác → bỏ qua.
  assert.equal(untouched({ tinh: "Thành phố Bắc Ninh", xa: "Phường B" }, first), false);
  // Địa chỉ lượt đầu đã ghi rồi bị sửa → bỏ qua; còn nguyên → ghi lại.
  const withDetail = { tinh: "Bắc Ninh", xa: "", diaChi: "Tổ 1" };
  assert.equal(untouched({ tinh: "Thành phố Bắc Ninh", diaChi: "Tổ 9" }, withDetail), false);
  assert.equal(untouched({ tinh: "Thành phố Bắc Ninh", diaChi: "Tổ 1" }, withDetail), true);
});
