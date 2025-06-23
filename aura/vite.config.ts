import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    host: true,
    cors: true,
  },
  build: {
    outDir: "dist",
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ["react", "react-dom"],
          router: ["react-router-dom"],
          ui: ["lucide-react", "@heroicons/react"],
          crypto: ["axios"],
        },
      },
    },
    // Security headers and CSP will be handled by the server
    assetsInlineLimit: 4096,
    chunkSizeWarningLimit: 1000,
  },
  define: {
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version || "1.0.0"),
    __BUILD_TIME__: JSON.stringify(new Date().toISOString()),
  },
  // PWA and security optimizations
  esbuild: {
    drop: process.env.NODE_ENV === "production" ? ["console", "debugger"] : [],
  },
});
