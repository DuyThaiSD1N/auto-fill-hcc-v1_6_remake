// scanDongBo.js — sổ sách "tệp quét trên đĩa (rel) ↔ tệp đã tải lên phiên (fid)".
//
// Vì sao cần: agent không có event "moved"/"renamed". Chuyển file vào thư mục con (hay đổi tên)
// bắn ra CẶP file.removed(rel cũ) + file.added(rel mới), và thứ tự KHÔNG cố định: cùng một lượt
// quét thì added đi trước (watcher.go Tick), khác lượt thì removed có thể đi trước vì file ở chỗ
// mới còn đang chờ "lành". Bản cũ xoá theo TÊN FILE nên hỏng cả hai chiều: phiên đã có hai tệp
// cùng tên → không dám xoá → dính hai bản; hoặc xoá nhầm tệp trùng tên công dân tải từ điện thoại.
//
// Cách làm giống autofill (popup.js importOneScanFile / handleScanAgentFileRemoved): khoá theo
// `rel`, không theo tên. added → tải lên, nhớ rel → fid. removed → xoá đúng fid của rel đó. Hai
// event độc lập với nhau nên tới theo thứ tự nào cũng còn đúng MỘT bản.
//
// Kèm `hash` (sha256 nội dung) cho từng rel: đối soát biết tệp trên đĩa có bị ghi đè không, và
// công dân/cán bộ gỡ tay thì nhớ được ĐÚNG nội dung đã gỡ.
//
// Thuần logic, không gọi mạng, không đụng storage: sidebar.js lo tải/xoá/lưu, file này chỉ trả
// lời "phải xoá fid nào".
(() => {
  function tao() {
    const theoRel = new Map(); // rel -> { fid, hash }
    const xoaLuc = new Map();  // rel -> số thứ tự của event xoá gần nhất
    // Tăng dần, KHÔNG bao giờ đặt lại: một lượt tải của phiên cũ còn đang bay mà đặt về 0 thì phép
    // so "xoá sau khi bắt đầu tải" ở taiXong ra sai.
    let seq = 0;

    // Gọi TRƯỚC await đầu tiên của lượt tải. Vé ghi lại mốc để taiXong biết có event xoá nào của
    // chính rel này chen vào giữa lúc đang tải hay không (tệp 3MB tải mất cả giây).
    function batDauTai(rel) {
      return { rel: String(rel || ""), seq };
    }

    // Tải xong, BE cấp fid. Trả mảng fid PHẢI XOÁ NGAY:
    //  - tệp bị xoá khỏi đĩa trong lúc đang tải → xoá luôn bản vừa tải lên;
    //  - rel đó đã có bản trước (máy quét ghi đè nội dung mới) → xoá bản cũ, giữ bản mới.
    function taiXong(ve, fid, hash = "") {
      if (!ve || !ve.rel || !fid) return [];
      const x = xoaLuc.get(ve.rel);
      if (x != null && x > ve.seq) return [fid];
      const cu = theoRel.get(ve.rel);
      theoRel.set(ve.rel, { fid, hash: String(hash || "") });
      return cu && cu.fid !== fid ? [cu.fid] : [];
    }

    // file.removed. Trả fid cần xoá, hoặc null nếu rel này không do mình tải lên — KHÔNG đoán theo
    // tên: tệp trùng tên có thể là giấy công dân tự tải từ điện thoại.
    function daXoa(rel) {
      rel = String(rel || "");
      seq += 1;
      xoaLuc.set(rel, seq);
      const cu = theoRel.get(rel);
      theoRel.delete(rel);
      return cu ? cu.fid : null;
    }

    // Tệp bị gỡ từ đường khác (bấm ✕ trong danh sách) → quên đi, để event xoá tới sau không cố xoá
    // lại một fid đã không còn.
    function quenFid(fid) {
      for (const [rel, v] of theoRel) if (v.fid === fid) theoRel.delete(rel);
    }

    function timTheoFid(fid) {
      for (const [rel, v] of theoRel) if (v.fid === fid) return { rel, hash: v.hash };
      return null;
    }

    function hashCua(rel) {
      return theoRel.get(String(rel || ""))?.hash || "";
    }

    // Đổi tên trên đĩa do CHÍNH mình gây ra: dời mục sang rel mới, fid và hash giữ nguyên.
    function doiRel(cu, moi) {
      const v = theoRel.get(cu);
      if (!v || !moi || cu === moi) return false;
      theoRel.delete(cu);
      theoRel.set(moi, v);
      return true;
    }

    function danhSach() {
      return [...theoRel].map(([rel, v]) => ({ rel, fid: v.fid, hash: v.hash }));
    }

    // Lưu/nạp. Ở chế độ đẩy trang, iframe sidebar bị DỰNG LẠI mỗi lần chuyển trang: sổ chỉ nằm trong
    // bộ nhớ thì sau một lần điều hướng, file.removed không còn tìm được fid → trùng bản quay lại.
    function xuat() {
      const o = {};
      for (const [rel, v] of theoRel) o[rel] = { fid: v.fid, hash: v.hash };
      return o;
    }

    // GỘP chứ không ghi đè: nạp là bất đồng bộ, event tới trong lúc chờ storage đã ghi mục MỚI hơn
    // bản đã lưu. Bỏ qua cả rel vừa bị xoá — không được hồi sinh tệp đã gỡ từ bản lưu cũ.
    function nap(obj) {
      if (!obj || typeof obj !== "object") return;
      for (const [rel, v] of Object.entries(obj)) {
        if (!rel || theoRel.has(rel) || xoaLuc.has(rel)) continue;
        if (!v || typeof v.fid !== "string" || !v.fid) continue;
        theoRel.set(rel, { fid: v.fid, hash: typeof v.hash === "string" ? v.hash : "" });
      }
    }

    // Sang công dân mới / đổi phiên. Giữ nguyên `seq` (xem chú thích ở trên).
    function datLai() {
      theoRel.clear();
      xoaLuc.clear();
    }

    return {
      batDauTai, taiXong, daXoa, quenFid, timTheoFid, hashCua, doiRel, danhSach, xuat, nap, datLai,
      soTep: () => theoRel.size,
    };
  }

  globalThis.TLNDScanDongBo = { tao };
})();
