// Chuyển ảnh (jpg/png) → PDF 1 trang, LOSSLESS: nhúng NGUYÊN bytes ảnh (embedJpg/embedPng),
// KHÔNG qua <canvas>, KHÔNG resize/re-encode → chất lượng giữ nguyên byte-for-byte.
// Dùng cho bước ĐÍNH KÈM (không dùng cho OCR). Phụ thuộc window.PDFLib (vendor/pdf-lib.min.js) nạp trước.
const PdfConvert = {
  isImage(type, name) {
    const t = String(type || "").toLowerCase();
    if (t === "image/jpeg" || t === "image/jpg" || t === "image/png") return true;
    return /\.(jpe?g|png)$/i.test(String(name || ""));
  },

  _isPng(type, name) {
    return String(type || "").toLowerCase().includes("png") || /\.png$/i.test(String(name || ""));
  },

  _dataUrlToBytes(dataUrl) {
    const comma = String(dataUrl || "").indexOf(",");
    const b64 = comma >= 0 ? dataUrl.slice(comma + 1) : "";
    const bin = atob(b64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return bytes;
  },

  _bytesToPdfDataUrl(bytes) {
    // Chunk khi encode base64 để tránh tràn call-stack với ảnh lớn.
    let bin = "";
    const CHUNK = 0x8000;
    for (let i = 0; i < bytes.length; i += CHUNK) {
      bin += String.fromCharCode.apply(null, bytes.subarray(i, i + CHUNK));
    }
    return "data:application/pdf;base64," + btoa(bin);
  },

  // Trả { name, type, dataUrl } đã là PDF (1 trang = đúng kích thước ảnh). Ném lỗi nếu lib chưa nạp / ảnh hỏng.
  async imageToPdf(dataUrl, name, type) {
    if (!window.PDFLib) throw new Error("Thiếu thư viện PDF (pdf-lib).");
    const { PDFDocument } = window.PDFLib;
    const bytes = this._dataUrlToBytes(dataUrl);
    const pdf = await PDFDocument.create();
    const img = this._isPng(type, name) ? await pdf.embedPng(bytes) : await pdf.embedJpg(bytes);
    const page = pdf.addPage([img.width, img.height]);
    page.drawImage(img, { x: 0, y: 0, width: img.width, height: img.height });
    const out = await pdf.save();
    const base = String(name || "tai-lieu").replace(/\.[^.]+$/, "");
    return { name: base + ".pdf", type: "application/pdf", dataUrl: this._bytesToPdfDataUrl(out) };
  },

  // Gộp nhiều file ({name,type,dataUrl}) theo THỨ TỰ → 1 PDF, LOSSLESS.
  // Nguồn PDF → copyPages (giữ nguyên trang); nguồn ảnh → embed + addPage. Ném lỗi nếu lib chưa nạp.
  async mergeToPdf(sources, name) {
    if (!window.PDFLib) throw new Error("Thiếu thư viện PDF (pdf-lib).");
    const { PDFDocument } = window.PDFLib;
    const out = await PDFDocument.create();
    for (const s of sources || []) {
      if (!s || !s.dataUrl) continue;
      const bytes = this._dataUrlToBytes(s.dataUrl);
      const isPdf = String(s.type || "").toLowerCase().includes("pdf") || /\.pdf$/i.test(String(s.name || ""));
      if (isPdf) {
        const src = await PDFDocument.load(bytes);
        const pages = await out.copyPages(src, src.getPageIndices());
        for (const p of pages) out.addPage(p);
      } else {
        const img = this._isPng(s.type, s.name) ? await out.embedPng(bytes) : await out.embedJpg(bytes);
        const page = out.addPage([img.width, img.height]);
        page.drawImage(img, { x: 0, y: 0, width: img.width, height: img.height });
      }
    }
    const saved = await out.save();
    const base = String(name || "cccd").replace(/\.[^.]+$/, "").replace(/[\\/:*?"<>|]+/g, " ").trim() || "cccd";
    return { name: base + ".pdf", type: "application/pdf", dataUrl: this._bytesToPdfDataUrl(saved) };
  },
};

if (typeof window !== "undefined") window.PdfConvert = PdfConvert;
