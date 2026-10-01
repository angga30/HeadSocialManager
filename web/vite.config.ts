import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Dev: proxy /api to the FastAPI backend on :8080.
// Prod: output to dist/, served by FastAPI at /app.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: "/app/",
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8080",
        changeOrigin: true,
      },
      "/media": {
        target: "http://localhost:8080",
        changeOrigin: true,
      },
      "/brand-assets": {
        target: "http://localhost:8080",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});