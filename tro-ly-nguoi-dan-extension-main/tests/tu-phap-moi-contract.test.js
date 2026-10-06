// Tư pháp luồng mới: trang nộp MỘT TRANG của Cổng DVC quốc gia (dichvucong.gov.vn/nop-ho-so) —
// form SurveyJS + bảng "Tải lên file" + ô "Hình thức nhận kết quả" + nút "Lưu và nộp hồ sơ".
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const read = (f) => fs.readFileSync(path.join(root, f), "utf8");
const manifest = JSON.parse(read("manifest.json"));
const sidebar = read("sidebar.js");
const fillCore = read("content/fill-core.js");
const guided = read("content/guided-steps.js");
const main = read("content/surveyjs-main.js");
const engine = read("content/fill-surveyjs.js");
const page = read("content/tu-phap-moi.js");

test("các file mới biên dịch được", () => {
  for (const file of ["content/surveyjs-main.js", "content/fill-surveyjs.js", "content/tu-phap-moi.js"]) {
    assert.doesNotThrow(() => new vm.Script(read(file), { filename: file }), file);
  }
});

test("manifest nạp engine SAU attach-core (dùng helper đính kèm) và cầu MAIN world cho DVCQG", () => {
  const js = manifest.content_scripts[0].js;
  const at = (f) => js.indexOf(f);
  assert.ok(at("content/fill-core.js") >= 0 && at("content/attach-core.js") >= 0);
  assert.ok(at("content/fill-surveyjs.js") > at("content/attach-core.js"));
  assert.ok(at("content/tu-phap-moi.js") > at("content/fill-surveyjs.js"));
  const mainEntry = manifest.content_scripts.find((c) => c.world === "MAIN" && c.js.includes("content/surveyjs-main.js"));
  assert.ok(mainEntry, "thiếu content/surveyjs-main.js ở MAIN world");
  assert.deepEqual(mainEntry.matches, ["https://dichvucong.gov.vn/*"]);
});

test("cầu MAIN world dùng tên sự kiện RIÊNG — cài cùng Auto Fill không trả lời chồng", () => {
  for (const src of [main, engine]) {
    assert.match(src, /__TLND_SJS_REQUEST__/);
    assert.match(src, /__TLND_SJS_RESULT__/);
    assert.doesNotMatch(src, /__HCC_SJS_/);
  }
  assert.doesNotMatch(main + engine, /data-hcc-picker/);
});

test("fill-core nhận form SurveyJS TRƯỚC các nhánh khác và chuyển tài khoản quầy cho Kính gửi/Tại", () => {
  assert.match(fillCore, /function detectFormKind\(\) \{[\s\S]{0,400}?\.sd-question\[data-name\][\s\S]{0,80}?return "surveyjs"/);
  assert.match(fillCore, /H\.fillFormSurveyJs\(fields, msg\.toolAccount \|\| null\)/);
  assert.match(sidebar, /action: "fillFields", fields: a\.fields, toolAccount: a\.toolAccount \|\| null/);
});

test("mốc người nộp (tên + CCCD) đọc từ khối người nộp của trang SurveyJS", () => {
  assert.match(fillCore, /readSurveyJsAccountValue\("citizenName"\)/);
  assert.match(fillCore, /readSurveyJsAccountValue\("citizenIdentity"\)/);
});

test("guided-steps IM trên trang mới — không bấm nộp khi chưa soát ô", () => {
  assert.match(guided, /isSurveyDossierPage\?\.\(\)\) return;/);
});

test("ba lệnh sidebar sẵn có được trả lời trên trang mới", () => {
  assert.match(page, /"attachFilesByPlan", "selectResultMethod", "guidedSubmit"/);
  assert.match(page, /if \(!onPage\(\)\) return;/);
});

test("nộp: soát ô bắt buộc + khối bưu điện, thiếu thì KHÔNG bấm và trả danh sách", () => {
  assert.match(page, /markEmptyRequired\(\{ force: true \}\)/);
  assert.match(page, /includes\("buu dien"\)[\s\S]{0,120}?postalMissing\(\{ mark: true \}\)/);
  assert.match(page, /if \(missing\.length\) \{[\s\S]{0,120}?return \{ ok: false, clicked: false, missing/);
  assert.match(page, /fold\(el\.textContent\) === "luu va nop ho so"/);
  assert.match(sidebar, /missing: Array\.isArray\(res\?\.missing\) \? res\.missing : \[\]/);
});

test("đính lại cả lượt: tệp cùng tên đã có trên dòng thì bỏ qua", () => {
  assert.match(engine, /if \(count\(beforeText, wanted\) > 0\) \{\s*skippedNames\.push\(file\.name\)/);
  // Đặt tên cả lượt một lần để hai tệp cùng tên tài liệu không bị coi là trùng.
  assert.match(engine, /H\.dataUrlFilesForBatch\(named\.filter\(Boolean\)\)/);
});

test("khai capability để BE dẫn vào luồng mới", () => {
  assert.match(sidebar, /supportsTuPhapMoi: true/);
});
