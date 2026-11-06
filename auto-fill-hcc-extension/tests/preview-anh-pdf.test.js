// Khung xem trước: ảnh (chụp điện thoại, quét) hiện dưới dạng PDF để trình xem PDF của Chrome có nút tải xuống — cán
// bộ tải được bản PDF. Dùng chung bộ chuyển ảnh → PDF của bước đính kèm; chuyển lỗi thì hiện ảnh như cũ.
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const read = (p) => fs.readFileSync(path.join(root, p), "utf8");
const strip = (src) => src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const html = read("preview.html");
const js = strip(read("preview.js"));

test("preview.html nạp pdf-lib + bộ chuyển ảnh trước preview.js", () => {
  const order = ["vendor/pdf-lib.min.js", "lib/imageToPdf.js", "preview.js"].map((s) => html.indexOf(`src="${s}"`));
  assert.ok(order.every((i, k) => i > 0 && (k === 0 || i > order[k - 1])), `thứ tự nạp sai: ${order}`);
  const manifest = JSON.parse(read("manifest.json"));
  const war = manifest.web_accessible_resources.flatMap((w) => w.resources);
  assert.ok(war.includes("lib/*") && war.includes("vendor/*"), "khung xem trước nằm trên trang cổng → cần web_accessible");
});

test("ảnh → PDF hiện bằng trình xem PDF; chuyển lỗi → hiện ảnh; đổi tệp giữa chừng thì bỏ kết quả cũ", () => {
  const branch = js.slice(js.indexOf('loai.startsWith("image/")'), js.indexOf("} else {", js.indexOf('loai.startsWith("image/")') + 400) + 200);
  assert.match(branch, /const pdfUrl = await anhSangPdf\(/);
  assert.match(branch, /if \(pdfUrl\) URL\.revokeObjectURL\(pdfUrl\);\s*return;/);
  assert.match(branch, /f\.src = pdfUrl \+ "#navpanes=0";/);
  assert.match(branch, /document\.createElement\("img"\)/);
  assert.match(js, /typeof PdfConvert === "undefined" \|\| !window\.PDFLib \|\| !PdfConvert\.isImage\(loai, name\)/);
});

// Chạy thật: ảnh dọc → trang A4 dọc, ảnh ngang → A4 ngang (trang to bằng số điểm ảnh thì in mặc định chỉ ra một góc).
test("ảnh chuyển sang PDF khổ A4 đúng chiều", async () => {
  const vm = require("node:vm");
  globalThis.window = globalThis;
  globalThis.PDFLib = require(path.join(root, "vendor/pdf-lib.min.js"));
  vm.runInThisContext(`${read("lib/imageToPdf.js")};globalThis.PdfConvert = PdfConvert;`);
  const src = read("preview.js");
  vm.runInThisContext(`${src.slice(src.indexOf("const A4_LE"), src.indexOf("async function ve("))};globalThis.anhSangPdf = anhSangPdf;`);
  const DOC = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB4AAAAoCAIAAABmcd1FAAAAPklEQVR4nO3QMREAMAjAQIpq5FROZbGHmaF3eQEZcuq+2JFL3TA9+BocAg4Bh4BDwCHgEHAIOAQcAg6BP4c07YwCMFlnSFkAAAAASUVORK5CYII=";
  const NGANG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACgAAAAeCAIAAADRv8uKAAAARklEQVR4nO3QQREAIBDDwKOqkYMcZPGlBtJPY2Bnsva5k0gRdQqDicT+CmOJo7zCWOIorzCWOMorjCWO8gpjiaO8wlix1Q9LZgIcjpzawQAAAABJRU5ErkJggg==";
  for (const [dataUrl, want] of [[DOC, [595, 842]], [NGANG, [842, 595]]]) {
    const url = await globalThis.anhSangPdf(dataUrl, "anh.png", "image/png");
    const pdf = await globalThis.PDFLib.PDFDocument.load(await (await fetch(url)).arrayBuffer());
    const page = pdf.getPage(0);
    assert.deepEqual([Math.round(page.getWidth()), Math.round(page.getHeight())], want);
  }
});
