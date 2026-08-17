import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
// FE quản trị build xong được serve bằng nginx container riêng (service fe, port 12010),
// nginx proxy /api /auth /ws sang app:8010. Dev: vite proxy sang localhost:8010.
export default defineConfig({
    plugins: [react()],
    base: "/",
    server: {
        port: 5173,
        proxy: {
            "/api": { target: "http://localhost:8010", changeOrigin: true },
            "/auth": { target: "http://localhost:8010", changeOrigin: true },
        },
    },
});
