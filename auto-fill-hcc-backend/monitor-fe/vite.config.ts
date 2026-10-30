import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    // index.html = web Monitor (12007), lab.html = web Kiểm thử (12008) — chung engine mô phỏng form.
    rollupOptions: { input: { main: "index.html", lab: "lab.html" } },
  },
  server: {
    port: 5174,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      "/auth": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
