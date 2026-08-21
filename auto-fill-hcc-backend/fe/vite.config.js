import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
// Proxy /api & /auth sang backend khi dev để khỏi lo CORS/cấu hình base URL.
//
// HAI entry độc lập, build ra 2 bundle riêng (đường dẫn tương đối được Vite resolve từ root):
//   index.html      → trang QUẢN TRỊ (admin, xem PII/OCR mọi phường)
//   dashboard.html  → BẢNG THỐNG KÊ PHƯỜNG (cán bộ phường, chỉ số liệu phường mình)
// Tách bundle để tài khoản phường KHÔNG nhận code/endpoint của trang quản trị.
export default defineConfig({
    plugins: [react()],
    build: {
        rollupOptions: {
            input: {
                main: "index.html",
                dashboard: "dashboard.html",
            },
        },
    },
    server: {
        port: 5173,
        proxy: {
            "/api": { target: "http://localhost:8000", changeOrigin: true },
            "/auth": { target: "http://localhost:8000", changeOrigin: true },
        },
    },
});
