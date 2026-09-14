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

  // Nhận diện định dạng theo BYTES thật — KHÔNG tin tên/mime (điện thoại hay đặt .png cho ảnh
  // JPG, và ngược lại). Chọn sai embedPng/embedJpg là ra "The input is not a PNG file!".
  _sniffImageType(bytes) {
    if (bytes && bytes.length >= 4 && bytes[0] === 0x89 && bytes[1] === 0x50
        && bytes[2] === 0x4e && bytes[3] === 0x47) return "png";
    if (bytes && bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return "jpg";
    return "other";
  },

  // Chuẩn hóa ảnh pdf-lib KHÔNG nhúng được (PNG interlaced/16-bit/grayscale+alpha, webp, mime
  // sai…) → vẽ lên canvas rồi xuất JPEG. Chỉ dùng làm PHAO khi embed gốc lỗi; đường thường vẫn
  // nhúng nguyên bytes (lossless).
  async _reencodeToJpeg(dataUrl) {
    if (typeof document === "undefined") throw new Error("Không chuẩn hóa được ảnh (thiếu canvas).");
    const img = await new Promise((resolve, reject) => {
      const im = new Image();
      im.onload = () => resolve(im);
      im.onerror = () => reject(new Error("Không đọc được ảnh để chuẩn hóa."));
      im.src = dataUrl;
    });
    const canvas = document.createElement("canvas");
    canvas.width = img.naturalWidth || img.width;
    canvas.height = img.naturalHeight || img.height;
    if (!canvas.width || !canvas.height) throw new Error("Ảnh không có kích thước hợp lệ.");
    canvas.getContext("2d").drawImage(img, 0, 0);
    return this._dataUrlToBytes(canvas.toDataURL("image/jpeg", 0.92));
  },

  // Nhúng ảnh vào PDF theo BYTES thật; embed lỗi (định dạng lạ / pdf-lib không đọc được) → phao
  // canvas→JPEG. Fix "The input is not a PNG file!" cho PNG bị nhận nhầm hoặc PNG biến thể lạ.
  async _embedImage(pdf, bytes, dataUrl, name, type) {
    const sniff = this._sniffImageType(bytes);
    try {
      if (sniff === "jpg") return await pdf.embedJpg(bytes);
      if (sniff === "png") return await pdf.embedPng(bytes);
      return this._isPng(type, name) ? await pdf.embedPng(bytes) : await pdf.embedJpg(bytes);
    } catch (e) {
      const jpegBytes = await this._reencodeToJpeg(dataUrl);
      return await pdf.embedJpg(jpegBytes);
    }
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
    const img = await this._embedImage(pdf, bytes, dataUrl, name, type);
    const page = pdf.addPage([img.width, img.height]);
    page.drawImage(img, { x: 0, y: 0, width: img.width, height: img.height });
    const out = await pdf.save();
    const base = String(name || "tai-lieu").replace(/\.[^.]+$/, "");
    return { name: base + ".pdf", type: "application/pdf", dataUrl: this._bytesToPdfDataUrl(out) };
  },

  _hasDifferentPageSizes(pages) {
    if (!Array.isArray(pages) || pages.length < 2) return false;
    const first = pages[0];
    // Máy scan thường lệch 1-2 pt giữa hai mặt cùng một giấy tờ. Sai số đó không đáng để
    // đổi cấu trúc PDF; chỉ chuẩn hóa khi kích thước thực sự khác nhau.
    return pages.some((page) =>
      Math.abs(Number(page.width) - Number(first.width)) > 2 ||
      Math.abs(Number(page.height) - Number(first.height)) > 2
    );
  },

  _drawOnA4(out, embedded, kind) {
    const [A4_WIDTH, A4_HEIGHT] = window.PDFLib.PageSizes.A4;
    const MARGIN = 24;
    const width = Number(embedded.width);
    const height = Number(embedded.height);
    // Không phóng trang scan nhỏ: phóng CCCD cỡ thật lên kín A4 làm ảnh mờ. Trang lớn
    // chỉ được thu nhỏ vừa khung, luôn giữ đúng tỷ lệ và nguyên stream ảnh/PDF nguồn.
    const scale = Math.min(
      1,
      (A4_WIDTH - MARGIN * 2) / width,
      (A4_HEIGHT - MARGIN * 2) / height
    );
    const drawWidth = width * scale;
    const drawHeight = height * scale;
    const options = {
      x: (A4_WIDTH - drawWidth) / 2,
      y: (A4_HEIGHT - drawHeight) / 2,
      width: drawWidth,
      height: drawHeight,
    };
    const page = out.addPage(window.PDFLib.PageSizes.A4);
    if (kind === "pdf") {
      page.drawPage(embedded, {
        x: options.x,
        y: options.y,
        xScale: scale,
        yScale: scale,
      });
    } else {
      page.drawImage(embedded, options);
    }
  },

  // Gộp nhiều file ({name,type,dataUrl}) theo THỨ TỰ → 1 PDF, LOSSLESS.
  // Engine tự chuẩn hóa khung A4 khi các trang nguồn khác kích thước; nội dung gốc không bị rasterize.
  async mergeToPdf(sources, name) {
    const segments = (sources || []).map((_, fileIndex) => ({ fileIndex, pageIndexes: null }));
    return this.composeSegmentsToPdf(sources, segments, name || "cccd");
  },

  // Dựng 1 PDF từ các đoạn trang BE chỉ định. segments giữ đúng thứ tự cần đính:
  // [{fileIndex, pageIndexes:[0,1]}]. pageIndexes=null nghĩa là lấy toàn bộ file nguồn.
  async composeSegmentsToPdf(sourceFiles, segments, name) {
    if (!window.PDFLib) throw new Error("Thiếu thư viện PDF (pdf-lib).");
    const { PDFDocument } = window.PDFLib;
    const out = await PDFDocument.create();
    const sourcePages = [];

    for (const segment of segments || []) {
      const sourceIndex = Number(segment?.fileIndex);
      const source = sourceFiles?.[sourceIndex];
      if (!Number.isInteger(sourceIndex) || !source?.dataUrl) {
        throw new Error(`Không tìm thấy file nguồn số ${segment?.fileIndex}.`);
      }
      const bytes = this._dataUrlToBytes(source.dataUrl);
      const isPdf = String(source.type || "").toLowerCase().includes("pdf") || /\.pdf$/i.test(String(source.name || ""));
      if (!isPdf) {
        const indexes = segment?.pageIndexes;
        if (Array.isArray(indexes) && (indexes.length !== 1 || Number(indexes[0]) !== 0)) {
          throw new Error(`Ảnh ${source.name || sourceIndex} chỉ có một trang.`);
        }
        const img = await this._embedImage(out, bytes, source.dataUrl, source.name, source.type);
        sourcePages.push({ kind: "image", embedded: img, width: img.width, height: img.height });
        continue;
      }

      const src = await PDFDocument.load(bytes);
      const indexes = Array.isArray(segment?.pageIndexes)
        ? segment.pageIndexes.map(Number)
        : src.getPageIndices();
      if (!indexes.length || indexes.some((index) => !Number.isInteger(index) || index < 0 || index >= src.getPageCount())) {
        throw new Error(`Khoảng trang của ${source.name || sourceIndex} không hợp lệ.`);
      }
      for (const index of indexes) {
        const page = src.getPage(index);
        sourcePages.push({
          kind: "pdf",
          src,
          index,
          width: page.getWidth(),
          height: page.getHeight(),
        });
      }
    }

    if (!sourcePages.length) throw new Error("Kế hoạch tách PDF không có trang nào.");
    const normalizeToA4 = this._hasDifferentPageSizes(sourcePages);
    for (const sourcePage of sourcePages) {
      if (normalizeToA4) {
        const embedded = sourcePage.kind === "pdf"
          ? await out.embedPage(sourcePage.src.getPage(sourcePage.index))
          : sourcePage.embedded;
        this._drawOnA4(out, embedded, sourcePage.kind);
      } else if (sourcePage.kind === "pdf") {
        const [page] = await out.copyPages(sourcePage.src, Array.of(sourcePage.index));
        out.addPage(page);
      } else {
        const page = out.addPage(Array.of(sourcePage.width, sourcePage.height));
        page.drawImage(sourcePage.embedded, {
          x: 0,
          y: 0,
          width: sourcePage.width,
          height: sourcePage.height,
        });
      }
    }

    const saved = await out.save();
    const base = String(name || "tai-lieu").replace(/\.[^.]+$/, "").replace(/[\\/:*?"<>|]+/g, " ").trim() || "tai-lieu";
    return { name: base + ".pdf", type: "application/pdf", dataUrl: this._bytesToPdfDataUrl(saved) };
  },
};

if (typeof window !== "undefined") window.PdfConvert = PdfConvert;
