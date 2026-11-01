// Nén tệp rất nặng TRƯỚC KHI GỬI vào phiên tải (máy quét tại quầy, chọn tệp tay). Ở handfree bản gửi BE cũng
// là bản đính lên cổng (cache byte / kéo lại từ phiên), nên planner kiểm trần dung lượng cổng khớp tệp thật.
// Gateway OCR chỉ đọc trang ở ~200 DPI (A4 ≈ 1654×2339 px) nên điểm ảnh của bản quét trên 2400 px bị bỏ trước khi
// đọc; thu về 2000 px (~240 DPI trên A4, vẫn rõ), JPEG 85 không làm chữ OCR lệch hơn mức OCR tự dao động (đo 60
// tệp thật) mà ảnh nhẹ khoảng một nửa. Chỉ tệp trên 10 MB; trong PDF chỉ thay ảnh JPEG (DCTDecode) màu RGB/xám,
// ảnh loại khác giữ nguyên. Lỗi bất kỳ → gửi bản gốc. Bản sao của auto-fill-hcc-extension/lib/nenTep.js.
// Phụ thuộc window.PDFLib.
const NenTep = {
  MIN_BYTES: 10 * 1024 * 1024,
  MAX_EDGE: 2400,
  TARGET_EDGE: 2000,
  QUALITY: 0.85,
  PARALLEL: 4,

  async forUpload(blob) {
    if (!blob || blob.size <= this.MIN_BYTES) return blob;
    try {
      const head = new Uint8Array(await blob.slice(0, 4).arrayBuffer());
      let out = null;
      if (head[0] === 0x25 && head[1] === 0x50 && head[2] === 0x44 && head[3] === 0x46) {
        out = await this._shrinkPdf(blob);
      } else if (head[0] === 0xff && head[1] === 0xd8 && head[2] === 0xff) {
        const res = await this._reencode(blob);
        out = res && res.blob;
      }
      return out && out.size < blob.size ? out : blob;
    } catch (_) {
      return blob;
    }
  },

  // Ảnh JPEG cạnh dài trên MAX_EDGE → { blob, width, height } đã thu về TARGET_EDGE; nhỏ hơn thì null.
  async _reencode(jpegBlob) {
    const bitmap = await createImageBitmap(jpegBlob);
    try {
      const edge = Math.max(bitmap.width, bitmap.height);
      if (edge <= this.MAX_EDGE) return null;
      const width = Math.max(1, Math.round(bitmap.width * this.TARGET_EDGE / edge));
      const height = Math.max(1, Math.round(bitmap.height * this.TARGET_EDGE / edge));
      const canvas = new OffscreenCanvas(width, height);
      const ctx = canvas.getContext("2d");
      ctx.imageSmoothingQuality = "high";
      ctx.drawImage(bitmap, 0, 0, width, height);
      return { blob: await canvas.convertToBlob({ type: "image/jpeg", quality: this.QUALITY }), width, height };
    } finally {
      if (bitmap.close) bitmap.close();
    }
  },

  // Ảnh trong PDF thay được bằng JPEG RGB mà không đổi cách trang hiển thị: JPEG, không mặt nạ/Decode,
  // màu RGB/xám (CMYK trình duyệt giải mã lệch màu).
  _replaceable(dict) {
    const { PDFName, PDFArray } = window.PDFLib;
    const name = (n) => PDFName.of(n);
    if (dict.lookup(name("Subtype")) !== name("Image")) return false;
    const filter = dict.lookup(name("Filter"));
    const dct = filter === name("DCTDecode")
      || (filter instanceof PDFArray && filter.size() === 1 && filter.lookup(0) === name("DCTDecode"));
    if (!dct) return false;
    if (["SMask", "Mask", "Decode", "ImageMask", "DecodeParms"].some((k) => dict.has(name(k)))) return false;
    const cs = dict.lookup(name("ColorSpace"));
    if (cs === name("DeviceRGB") || cs === name("DeviceGray")) return true;
    if (cs instanceof PDFArray && cs.lookup(0) === name("ICCBased")) {
      const icc = cs.lookup(1);
      const n = icc && icc.dict && icc.dict.lookup(name("N"));
      return !!n && (n.asNumber() === 1 || n.asNumber() === 3);
    }
    return false;
  },

  async _shrinkPdf(blob) {
    const { PDFDocument, PDFName, PDFNumber, PDFRawStream } = window.PDFLib;
    const pdf = await PDFDocument.load(new Uint8Array(await blob.arrayBuffer()), { updateMetadata: false });
    if (pdf.isEncrypted) return null;
    const jobs = pdf.context.enumerateIndirectObjects().filter(([, obj]) => {
      if (!(obj instanceof PDFRawStream) || !this._replaceable(obj.dict)) return false;
      const w = obj.dict.lookup(PDFName.of("Width"));
      const h = obj.dict.lookup(PDFName.of("Height"));
      return !!w && !!h && Math.max(w.asNumber(), h.asNumber()) > this.MAX_EDGE;
    });
    if (!jobs.length) return null;
    let next = 0;
    const worker = async () => {
      while (next < jobs.length) {
        const [ref, obj] = jobs[next++];
        const res = await this._reencode(new Blob([obj.contents], { type: "image/jpeg" }));
        if (!res) continue;
        const dict = obj.dict;
        dict.set(PDFName.of("Width"), PDFNumber.of(res.width));
        dict.set(PDFName.of("Height"), PDFNumber.of(res.height));
        dict.set(PDFName.of("BitsPerComponent"), PDFNumber.of(8));
        dict.set(PDFName.of("ColorSpace"), PDFName.of("DeviceRGB"));
        pdf.context.assign(ref, PDFRawStream.of(dict, new Uint8Array(await res.blob.arrayBuffer())));
      }
    };
    await Promise.all(Array.from({ length: Math.min(this.PARALLEL, jobs.length) }, worker));
    return new Blob([await pdf.save()], { type: "application/pdf" });
  },
};
