// Mọi mốc thời gian trên trang quản trị đọc theo GIỜ VIỆT NAM, không theo múi giờ của máy đang
// mở trang: báo cáo được gửi/đối chiếu giữa nhiều nơi, một máy đặt sai múi là cả bảng lệch mà
// không ai biết. Backend luôn trả ISO có offset nên Date() dựng đúng mốc; chỗ này chỉ quyết
// định hiển thị. Xem thêm VIETNAM_TZ ở dashboard.
export const VIETNAM_TZ = "Asia/Ho_Chi_Minh";

export function fmtDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString("vi-VN", {
      timeZone: VIETNAM_TZ,
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

// "2026-09-14" → "14/9/2026". Chuỗi này backend đã quy sẵn về giờ VN nên TÁCH TAY, không dựng
// Date rồi format lại — làm thế là mượn múi giờ của máy và lệch mất một ngày.
export function dayMonthYear(isoDate: string): string {
  const [year, month, day] = String(isoDate || "").split("-");
  if (!year || !month || !day) return isoDate;
  return `${Number(day)}/${Number(month)}/${year}`;
}

// Thời gian xử lý: < 1s hiển thị ms, còn lại đổi ra giây (2 số lẻ).
export function fmtMs(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toLocaleString("vi-VN", { maximumFractionDigits: 2 })} s`;
}

// Dung lượng payload: tự chọn B / KB / MB.
export function fmtBytes(n: number | null | undefined): string {
  if (n == null) return "—";
  if (n < 1024) return `${n} B`;
  const kb = n / 1024;
  if (kb < 1024) return `${kb.toLocaleString("vi-VN", { maximumFractionDigits: 0 })} KB`;
  return `${(kb / 1024).toLocaleString("vi-VN", { maximumFractionDigits: 2 })} MB`;
}

// Thời gian LÀM HỒ SƠ (bắt đầu → bấm nộp): tính bằng phút/giờ, khác fmtMs vốn để đo độ trễ
// xử lý của máy chủ. Hồ sơ làm dở không có mốc nộp → "—", không bịa số.
export function fmtDuration(ms: number | null | undefined): string {
  if (ms == null || ms < 0) return "—";
  const totalMinutes = Math.round(ms / 60000);
  if (totalMinutes < 1) return "< 1 phút";
  if (totalMinutes < 60) return `${totalMinutes} phút`;
  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;
  return m ? `${h} giờ ${m} phút` : `${h} giờ`;
}
