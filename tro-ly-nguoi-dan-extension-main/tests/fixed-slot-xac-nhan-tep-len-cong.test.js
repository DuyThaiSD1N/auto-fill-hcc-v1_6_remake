// Ô input cố định (vd mai táng BYT): gán được tệp vào input chưa phải đã lên cổng — chỉ nhận thành công khi tên
// tệp hiện trên dòng. Chạy thật hàm so khớp lấy từ source (cả handfree lẫn Auto Fill nếu có repo bên cạnh). Dữ liệu giả.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const src = fs.readFileSync(path.join(__dirname, "..", "content", "attach-core.js"), "utf8");
const code = src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const SOURCES = [
  ["handfree", src],
  ["autofill", path.join(__dirname, "..", "..", "auto-fill-hcc-extension", "content.js")],
].filter(([, v]) => v === src || fs.existsSync(v)).map(([label, v]) => [label, v === src ? v : fs.readFileSync(v, "utf8")]);

function extract(src, name) {
  const start = src.search(new RegExp(`function ${name}\\(`));
  assert.ok(start >= 0, `thiếu ${name}`);
  let depth = 0;
  for (let i = src.indexOf("{", start); i < src.length; i++) {
    if (src[i] === "{") depth++;
    else if (src[i] === "}" && --depth === 0) return src.slice(start, i + 1);
  }
  throw new Error(`không tách được ${name}`);
}

function load(src) {
  const store = new Map();
  const ctx = {
    location: { host: "dichvucong.moh.gov.vn" },
    sessionStorage: { getItem: (k) => store.get(k) ?? null, setItem: (k, v) => store.set(k, String(v)) },
    ATTACH_FILE_SOURCE: new WeakMap(),
    UPLOADED_NAMES_KEY: "hcc_attach_uploaded_names",
    shownOnRow: [],
    foldChoiceText: (v) => String(v || "").normalize("NFD").replace(/[̀-ͯ]/g, "")
      .replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase(),
  };
  const fns = ["attpDocFingerprint", "attachSourceKey", "readUploadedNames", "rememberUploadedFiles",
    "shownIndexForFile", "filesNotOnRow", "fixedSlotFilesLanded"].map((n) => extract(src, n)).join("\n");
  vm.runInNewContext(`${fns}
    function attpRowAttachedFingerprints() { return shownOnRow.map(attpDocFingerprint); }
    this.api = { fixedSlotFilesLanded, rememberUploadedFiles };`, ctx);
  const makeFile = (name, payload) => {
    const file = { name };
    ctx.ATTACH_FILE_SOURCE.set(file, payload);
    return file;
  };
  const row = (readonlyValues = []) => ({ querySelectorAll: () => readonlyValues.map((value) => ({ value })) });
  return { ...ctx.api, ctx, makeFile, row };
}

const SCAN = { name: "scan-0001.pdf", dataUrl: "data:application/pdf;base64,AAAA" };
const TEN = "Tờ khai đề nghị hỗ trợ chi phí mai táng.pdf";

for (const [label, src] of SOURCES) {
  test(`${label}: gán vào input nhưng dòng không hiện tên tệp → CHƯA lên cổng`, () => {
    const { fixedSlotFilesLanded, rememberUploadedFiles, makeFile, row } = load(src);
    const file = makeFile(TEN, SCAN);
    rememberUploadedFiles([file]);
    assert.equal(fixedSlotFilesLanded(row(), [file]), false);
  });

  test(`${label}: chip trên dòng hiện tên tệp (kể cả bị cổng cắt ngắn) → đã lên cổng`, () => {
    const { fixedSlotFilesLanded, rememberUploadedFiles, ctx, makeFile, row } = load(src);
    const file = makeFile(TEN, SCAN);
    rememberUploadedFiles([file]);
    ctx.shownOnRow = ["Tờ khai đề nghị hỗ trợ chi phí ....pdf"];
    assert.equal(fixedSlotFilesLanded(row(), [file]), true);
  });

  test(`${label}: tên tệp nằm trong ô readonly kiểu bootstrap-filestyle → đã lên cổng`, () => {
    const { fixedSlotFilesLanded, rememberUploadedFiles, makeFile, row } = load(src);
    const file = makeFile(TEN, SCAN);
    rememberUploadedFiles([file]);
    assert.equal(fixedSlotFilesLanded(row([`C:\\fakepath\\${TEN}`]), [file]), true);
  });

  test(`${label}: dòng chỉ hiện tệp KHÁC → chưa lên cổng`, () => {
    const { fixedSlotFilesLanded, rememberUploadedFiles, ctx, makeFile, row } = load(src);
    const file = makeFile(TEN, SCAN);
    rememberUploadedFiles([file]);
    ctx.shownOnRow = ["Giấy chứng tử của đối tượng.pdf"];
    assert.equal(fixedSlotFilesLanded(row(), [file]), false);
  });
}

test("nhánh input của fixed-slot chỉ đếm thành công sau khi thấy tên tệp trên dòng", () => {
  const start = code.indexOf("async function attachFilesByFixedSlot(");
  const branch = code.slice(start, code.indexOf("const tryMenuSlot", start));
  const wait = branch.indexOf("await waitFor(() => fixedSlotFilesLanded(liveRow(), pending)");
  assert.ok(wait > 0, "thiếu bước chờ tên tệp hiện trên dòng");
  assert.ok(branch.indexOf("if (!landed)") > wait);
  assert.ok(branch.indexOf("attachedNames.push(...pending.map((f) => f.name))") > branch.indexOf("if (!landed)"));
  assert.match(branch, /Cổng chưa ghi nhận tệp ở ô/);
  assert.match(branch, /markLandedFileChips\(liveRow\(\), pending\)/);
});
