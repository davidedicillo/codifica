import { defineConfig, loadEnv } from "vite";
export default defineConfig(({ mode }) => ({
  server: {
    port: 5173,
    proxy: { "/api": { target: loadEnv(mode, ".", "CODIFICA_").CODIFICA_API_PROXY || "http://127.0.0.1:8791", changeOrigin: false } },
  },
}));
