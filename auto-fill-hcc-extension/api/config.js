const BACKEND_URL = "http://localhost:12005";     // Backend CHÍNH — ĐANG TRỎ LOCAL để thử FE (prod: https://trolyhoso-hcc-admin.tiengnoi.vn)
// Backend PHỤ (dự phòng) — điền domain server phụ để BẬT failover; để TRỐNG = tắt (chạy như cũ).
// ⚠ 2 backend PHẢI dùng chung JWT_ACCESS_SECRET/JWT_REFRESH_SECRET và có cùng tài khoản,
// nếu không khi chuyển sang phụ user sẽ bị đá ra đăng nhập lại.

const BACKEND_URL_FALLBACK = "";   // TẮT khi test local (prod: https://trolyhoso-hcc-admin.vnekyc.vn)
// Timeout mỗi request. PHẢI đủ dài cho request nặng (OCR+LLM có thể ~25s+, nhiều file lâu hơn) —
// đặt ngắn sẽ abort NHẦM khi server vẫn đang xử lý → báo "không kết nối" oan. Chỉ dùng để cắt
// server TREO thật (không phản hồi trong 100s) rồi mới chuyển sang phụ.
const BACKEND_TIMEOUT_MS = 100000;
// Sau khi backend chính lỗi, trong khoảng này ưu tiên gọi PHỤ trước (khỏi chờ chết lại mỗi lần);
// quá hạn thì thử lại CHÍNH → tự phục hồi khi chính sống lại.
const BACKEND_FAILOVER_COOLDOWN_MS = 30000;

// WS cho phiên tải ảnh QR: https→wss (http→ws). WebSocket chạy THẲNG từ popup iframe
// (không proxy qua background — SW MV3 bị kill sẽ rớt kết nối).
// LƯU Ý: phiên QR có TRẠNG THÁI (session + file nằm ở 1 server) nên GHIM vào backend chính,
// KHÔNG auto-failover giữa chừng — chính chết thì làm lại phiên trên phụ.
const WS_BASE = BACKEND_URL.replace(/^http/, "ws");
const WS_BASE_FALLBACK = BACKEND_URL_FALLBACK ? BACKEND_URL_FALLBACK.replace(/^http/, "ws") : "";

if (typeof window !== "undefined") {
  window.BACKEND_URL = BACKEND_URL;
  window.BACKEND_URL_FALLBACK = BACKEND_URL_FALLBACK;
  window.WS_BASE = WS_BASE;
  window.WS_BASE_FALLBACK = WS_BASE_FALLBACK;
}