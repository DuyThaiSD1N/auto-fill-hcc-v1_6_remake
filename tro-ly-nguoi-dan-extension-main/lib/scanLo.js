// scanLo.js — quyết định tự tải LÔ tệp quét đã có sẵn trong thư mục lúc Trợ lý vừa nối máy quét
// hoặc vừa vào bước tải giấy tờ (cán bộ quét trước rồi mới mở Trợ lý).
//
// Chép NGUYÊN logic của autofill 1.17 (popup.js phanTichBatchGanNhat + attemptBatchImport) — cùng
// hằng số, cùng lý do, xem docs/tich-hop-scan-bridge.md mục 4.7 / 4.10 / 4.18 bên autofill. Tách
// thành hàm thuần để test được; sidebar.js chỉ lo tải lên và vẽ danh sách chọn tay.
(() => {
  const BATCH_SINGLE_FLOOR_MS = 5 * 60 * 1000; // file đứng một mình: cách file kế ≥ 5 phút mới tự tin
  const BATCH_GAP_RATIO = 4;                   // ranh giới phải ≥ 4 lần khoảng cách nội bộ lớn nhất
  const BATCH_GAP_FLOOR_MS = 20 * 1000;        // dưới 20s không tính là ranh giới, chỉ là quét liên tục
  const BATCH_MAX_FILES = 30;                  // quá số này mà chưa thấy ranh giới → không đoán
  const BATCH_MAX_SPAN_MS = 30 * 60 * 1000;    // quá 30 phút mà chưa thấy ranh giới → không đoán
  // Trần tuổi: lô "tự tin" mà tệp mới nhất đã quá 30 phút thì KHÔNG tự tải. Watermark bằng 0 ở lần
  // đầu dùng máy — không có trần là kéo cả giấy tuần trước vào hồ sơ công dân đang ngồi đây.
  const BATCH_AUTO_MAX_AGE_MS = 30 * 60 * 1000;
  const RECENT_LIST_WINDOW_MS = 2 * 60 * 60 * 1000; // danh sách chọn tay: chỉ 2 giờ gần nhất
  const RECENT_LIST_MAX = 30;

  // Đi ngược từ tệp mới nhất, mở rộng "lô" từng tệp, so khoảng cách tới tệp kế với các khoảng cách
  // nội bộ đã thấy. Trả {confident, batch}: confident=false thì không có ranh giới rõ, batch rỗng.
  function phanTichBatchGanNhat(chuaXuLy) {
    if (!chuaXuLy.length) return { confident: true, batch: [] };
    const list = [...chuaXuLy].sort((a, b) => b.mtimeMs - a.mtimeMs);
    const batch = [list[0]];
    let maxGapNoiBo = 0;
    for (let i = 1; i < list.length; i++) {
      const gap = list[i - 1].mtimeMs - list[i].mtimeMs;
      const nguong = batch.length === 1
        ? BATCH_SINGLE_FLOOR_MS
        : Math.max(BATCH_GAP_FLOOR_MS, BATCH_GAP_RATIO * maxGapNoiBo);
      if (gap >= nguong) break; // ranh giới rõ → dừng, tự tin với lô hiện tại
      batch.push(list[i]);
      maxGapNoiBo = Math.max(maxGapNoiBo, gap);
      if (batch.length >= BATCH_MAX_FILES || (list[0].mtimeMs - list[i].mtimeMs) >= BATCH_MAX_SPAN_MS) {
        return { confident: false, batch: [] };
      }
    }
    return { confident: true, batch };
  }

  // trenDia: kết quả /v1/files ({folder, files: [{rel, name, mtime}]}).
  // daCo: Set các rel đã nằm trên phiên. watermarkMs: tệp có mtime ≤ mốc là của công dân TRƯỚC.
  // Trả { hanhDong: "tu-them" | "chon-tay" | "khong", tuThem, chonTay, lyDo, nhatKy }.
  function quyetDinh({ trenDia, daCo = new Set(), watermarkMs = 0, now = Date.now() } = {}) {
    const tatCa = (trenDia?.files || [])
      .filter((f) => f?.rel)
      .map((f) => ({ rel: f.rel, name: f.name || String(f.rel).split("/").pop(), mtimeMs: new Date(f.mtime).getTime() }))
      .filter((f) => Number.isFinite(f.mtimeMs));
    const chuaCo = tatCa.filter((f) => !daCo.has(f.rel));
    // File bị ghi đè (cùng rel, nội dung mới) có mtime mới hơn mốc nên vẫn lọt qua — đúng ý.
    const chuaXuLy = chuaCo.filter((f) => f.mtimeMs > watermarkMs);
    const nhatKy = {
      tren_dia: tatCa.length,
      da_co_tren_phien: tatCa.length - chuaCo.length,
      bi_watermark_chan: chuaCo.length - chuaXuLy.length,
      con_ung_vien: chuaXuLy.length,
    };
    const khong = (lyDo) => ({ hanhDong: "khong", tuThem: [], chonTay: [], lyDo, nhatKy });
    if (!chuaXuLy.length) return khong("không có tệp mới");

    const { confident, batch } = phanTichBatchGanNhat(chuaXuLy);
    if (confident && !batch.length) return khong("không có tệp mới");
    // Xét tệp MỚI NHẤT của lô: lô đã liền mạch về thời gian, tệp mới nhất cũ thì cả lô đều cũ.
    const loQuaCu = batch.length > 0 && now - batch[0].mtimeMs > BATCH_AUTO_MAX_AGE_MS;
    if (confident && !loQuaCu) {
      return { hanhDong: "tu-them", tuThem: batch, chonTay: [], lyDo: `tự tải ${batch.length} tệp`, nhatKy };
    }
    const chonTay = chuaXuLy
      .filter((f) => now - f.mtimeMs <= RECENT_LIST_WINDOW_MS)
      .sort((a, b) => b.mtimeMs - a.mtimeMs)
      .slice(0, RECENT_LIST_MAX);
    const lyDo = !confident
      ? "không tự tin về ranh giới lô → để cán bộ chọn tay"
      : `lô mới nhất quét lúc ${new Date(batch[0].mtimeMs).toLocaleString()} — quá ${Math.round(BATCH_AUTO_MAX_AGE_MS / 60000)} phút → không tự tải`;
    if (!chonTay.length) return khong(lyDo);
    return { hanhDong: "chon-tay", tuThem: [], chonTay, lyDo, nhatKy };
  }

  globalThis.TLNDScanLo = {
    phanTichBatchGanNhat, quyetDinh,
    BATCH_AUTO_MAX_AGE_MS, RECENT_LIST_WINDOW_MS, RECENT_LIST_MAX,
  };
})();
