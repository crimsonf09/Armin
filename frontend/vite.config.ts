import { defineConfig } from "vite";

// When VITE_API_URL is `/api`, the browser calls the dev server; this proxy forwards to FastAPI.
export default defineConfig({
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
