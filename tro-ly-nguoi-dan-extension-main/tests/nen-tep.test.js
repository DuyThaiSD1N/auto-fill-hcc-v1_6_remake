const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { Blob } = require("node:buffer");
const PDFLib = require("../vendor/pdf-lib.min.js");

const MB = 1024 * 1024;
const jpegBytes = (size) => {
  const bytes = new Uint8Array(size);
  bytes.set([0xff, 0xd8, 0xff]);
  return bytes;
};

let decodeFails = false;
const decoded = [];
const context = {
  window: { PDFLib },
  Blob, Uint8Array, Array, Math, Promise, Error,
  createImageBitmap: async (blob) => {
    if (decodeFails) throw new Error("hỏng");
    decoded.push(blob.size);
    return { ...context.__dims, close() {} };
  },
  OffscreenCanvas: class {
    constructor(width, height) { this.width = width; this.height = height; }
    getContext() { return { drawImage() {} }; }
    async convertToBlob() { return new Blob([jpegBytes(1000)], { type: "image/jpeg" }); }
  },
};
vm.createContext(context);
vm.runInContext(`${fs.readFileSync(path.join(__dirname, "..", "lib", "nenTep.js"), "utf8")}\nglobalThis.NenTep = NenTep;`, context);
const { NenTep } = context;

async function pdfWithImage({ width, height, colorSpace = "DeviceRGB", size = 11 * MB }) {
  const doc = await PDFLib.PDFDocument.create();
  doc.addPage([595, 842]);
  const dict = doc.context.obj({
    Type: "XObject", Subtype: "Image", Width: width, Height: height,
    ColorSpace: colorSpace, BitsPerComponent: 8, Filter: "DCTDecode",
  });
  doc.context.register(PDFLib.PDFRawStream.of(dict, jpegBytes(size)));
  return new Blob([await doc.save()], { type: "application/pdf" });
}

async function images(blob) {
  const doc = await PDFLib.PDFDocument.load(new Uint8Array(await blob.arrayBuffer()));
  return doc.context.enumerateIndirectObjects()
    .filter(([, obj]) => obj instanceof PDFLib.PDFRawStream
      && obj.dict.lookup(PDFLib.PDFName.of("Subtype")) === PDFLib.PDFName.of("Image"))
    .map(([, obj]) => ({
      width: obj.dict.lookup(PDFLib.PDFName.of("Width")).asNumber(),
      height: obj.dict.lookup(PDFLib.PDFName.of("Height")).asNumber(),
      bytes: obj.contents.length,
    }));
}

(async () => {
  // Tệp ≤ 10 MB gửi nguyên.
  const small = await pdfWithImage({ width: 3400, height: 4400, size: 2 * MB });
  assert.equal(await NenTep.forUpload(small), small);

  // Ảnh quét 3400×4400 trong PDF 11 MB → thu về cạnh dài 2000 px, tệp nhỏ đi.
  context.__dims = { width: 3400, height: 4400 };
  const big = await pdfWithImage({ width: 3400, height: 4400 });
  const out = await NenTep.forUpload(big);
  assert.ok(out.size < big.size / 10);
  assert.deepEqual(await images(out), [{ width: 1545, height: 2000, bytes: 1000 }]);

  // Ảnh đã ≤ 2400 px: giữ nguyên tệp, không giải mã.
  decoded.length = 0;
  const sharp = await pdfWithImage({ width: 1654, height: 2339 });
  assert.equal(await NenTep.forUpload(sharp), sharp);
  assert.equal(decoded.length, 0);

  // CMYK: trình duyệt giải mã lệch màu → không đụng.
  const cmyk = await pdfWithImage({ width: 3400, height: 4400, colorSpace: "DeviceCMYK" });
  assert.equal(await NenTep.forUpload(cmyk), cmyk);

  // Giải mã lỗi → gửi bản gốc.
  decodeFails = true;
  assert.equal(await NenTep.forUpload(big), big);
  decodeFails = false;

  // Ảnh JPEG rời 11 MB, 4000×3000 → JPEG 2000×1500.
  context.__dims = { width: 4000, height: 3000 };
  const photo = new Blob([jpegBytes(11 * MB)], { type: "image/jpeg" });
  const shrunk = await NenTep.forUpload(photo);
  assert.equal(shrunk.size, 1000);

  // sidebar: nén trước khi dựng FormData, và cache byte để đính dùng đúng bản đã gửi.
  const sidebar = fs.readFileSync(path.join(__dirname, "..", "sidebar.js"), "utf8");
  const fn = sidebar.slice(sidebar.indexOf("async function uploadFilesToSession("), sidebar.indexOf("$fileInput?.addEventListener(\"change\""));
  assert.ok(fn.indexOf("NenTep.forUpload(f)") > 0);
  assert.ok(fn.indexOf("NenTep.forUpload(f)") < fn.indexOf("new FormData()"));
  assert.ok(fn.includes("await cacheUploadedBlobs(uploadSid, files, data?.accepted)"));
  const html = fs.readFileSync(path.join(__dirname, "..", "sidebar.html"), "utf8");
  assert.ok(html.indexOf('src="vendor/pdf-lib.min.js"') < html.indexOf('src="lib/nenTep.js"'));
  assert.ok(html.indexOf('src="lib/nenTep.js"') < html.indexOf('src="sidebar.js"'));

  console.log("nen-tep: ok");
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
