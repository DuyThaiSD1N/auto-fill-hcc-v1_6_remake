import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy /api & /auth sang backend khi dev để khỏi lo CORS/cấu hình base URL.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      "/auth": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
