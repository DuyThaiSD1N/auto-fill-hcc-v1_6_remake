const BACKEND_URL = "http://localhost:12006";
// WS cho phiên tải ảnh QR: https→wss (http→ws). WebSocket chạy THẲNG từ popup iframe
// (không proxy qua background — SW MV3 bị kill sẽ rớt kết nối).
const WS_BASE = BACKEND_URL.replace(/^http/, "ws");

if (typeof window !== "undefined") {
  window.BACKEND_URL = BACKEND_URL;
  window.WS_BASE = WS_BASE;
}
