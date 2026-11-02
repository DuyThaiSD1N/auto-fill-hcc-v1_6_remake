// Chống trùng khi đính kèm lại phải lần theo TỆP NGUỒN: tên đặt theo LLM đổi giữa hai lượt, cổng cắt ngắn tên hiển thị.
// Chạy thật các hàm so khớp lấy từ source (cả handfree lẫn Auto Fill nếu có repo bên cạnh). Dữ liệu giả.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const SOURCES = [
  ["handfree", path.join(__dirname, "..", "content", "attach-core.js")],
  ["autofill", path.join(__dirname, "..", "..", "auto-fill-hcc-extension", "content.js")],
].filter(([, file]) => fs.existsSync(file));

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

function load(file) {
  const src = fs.readFileSync(file, "utf8");
  const store = new Map();
  const ctx = {
    location: { host: "dichvucongbyt.moh.gov.vn" },
    sessionStorage: { getItem: (k) => store.get(k) ?? null, setItem: (k, v) => store.set(k, String(v)) },
    ATTACH_FILE_SOURCE: new WeakMap(),
    UPLOADED_NAMES_KEY: "hcc_attach_uploaded_names",
    shownOnRow: [],
    foldChoiceText: (v) => String(v || "").normalize("NFD").replace(/[̀-ͯ]/g, "")
      .replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase(),
  };
  const fns = ["attpDocFingerprint", "attachSourceKey", "readUploadedNames", "rememberUploadedFiles",
    "shownIndexForFile", "filesNotOnRow"].map((n) => extract(src, n)).join("\n");
  vm.runInNewContext(`${fns}
    function attpRowAttachedFingerprints() { return shownOnRow.map(attpDocFingerprint); }
    this.api = { filesNotOnRow, rememberUploadedFiles };`, ctx);
  const makeFile = (name, payload) => {
    const file = { name };
    ctx.ATTACH_FILE_SOURCE.set(file, payload);
    return file;
  };
  return { ...ctx.api, ctx, makeFile };
}

const SCAN = { name: "scan-0001.pdf", dataUrl: "data:application/pdf;base64,AAAA" };
const SCAN_KHAC = { name: "scan-0002.pdf", dataUrl: "data:application/pdf;base64,BBBBBB" };
const TEN_LUOT_1 = "Đơn đề nghị cấp đổi, cấp lại Giấy xác nhận khuyết tật.pdf";
const HIEN_CAT_NGAN = "Đơn đề nghị cấp đổi_ cấp lại Giấy xác nhận khuyết ....pdf";

for (const [label, file] of SOURCES) {
  test(`${label}: lượt sau đổi tên khác + cổng cắt ngắn tên → vẫn nhận ra tệp nguồn đã đính`, () => {
    const { filesNotOnRow, rememberUploadedFiles, ctx, makeFile } = load(file);
    rememberUploadedFiles([makeFile(TEN_LUOT_1, SCAN)]);
    ctx.shownOnRow = [HIEN_CAT_NGAN];
    assert.deepEqual(filesNotOnRow({}, [makeFile("Giấy tờ khác.pdf", SCAN)]).length, 0);
  });

  test(`${label}: tệp nguồn KHÁC mang cùng nhãn → vẫn đính, không bỏ nhầm`, () => {
    const { filesNotOnRow, rememberUploadedFiles, ctx, makeFile } = load(file);
    rememberUploadedFiles([makeFile(TEN_LUOT_1, SCAN)]);
    ctx.shownOnRow = [HIEN_CAT_NGAN];
    assert.equal(filesNotOnRow({}, [makeFile(TEN_LUOT_1, SCAN_KHAC)]).length, 1);
  });

  test(`${label}: đã nhớ nhưng cán bộ đã xoá tệp khỏi dòng → đính lại`, () => {
    const { filesNotOnRow, rememberUploadedFiles, ctx, makeFile } = load(file);
    rememberUploadedFiles([makeFile(TEN_LUOT_1, SCAN)]);
    ctx.shownOnRow = [];
    assert.equal(filesNotOnRow({}, [makeFile(TEN_LUOT_1, SCAN)]).length, 1);
  });

  test(`${label}: chưa có trí nhớ → chỉ bỏ khi trùng TRỌN tên`, () => {
    const { filesNotOnRow, ctx, makeFile } = load(file);
    ctx.shownOnRow = [TEN_LUOT_1];
    assert.equal(filesNotOnRow({}, [makeFile(TEN_LUOT_1, SCAN)]).length, 0);
    ctx.shownOnRow = [HIEN_CAT_NGAN];
    assert.equal(filesNotOnRow({}, [makeFile(TEN_LUOT_1, SCAN)]).length, 1);
  });

  test(`${label}: mỗi tệp đang hiện chỉ đỡ cho MỘT tệp`, () => {
    const { filesNotOnRow, rememberUploadedFiles, ctx, makeFile } = load(file);
    rememberUploadedFiles([makeFile(TEN_LUOT_1, SCAN), makeFile("Căn cước công dân.pdf", SCAN_KHAC)]);
    ctx.shownOnRow = [HIEN_CAT_NGAN];
    const pending = filesNotOnRow({}, [makeFile("A.pdf", SCAN), makeFile("Căn cước công dân.pdf", SCAN_KHAC)]);
    assert.deepEqual(pending.map((f) => f.name), ["Căn cước công dân.pdf"]);
  });
}
