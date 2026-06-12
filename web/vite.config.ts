import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
    emptyOutDir: true
  },
  server: {
    port: 5173,
    // Dev-only: keep the SPA same-origin by proxying /api/v1 to the local backend,
    // mirroring what Caddy does in production. Never set VITE_API_BASE_URL.
    proxy: {
      "/api/v1": {
        target: "http://127.0.0.1:8000",
        changeOrigin: false
      }
    }
  }
});
