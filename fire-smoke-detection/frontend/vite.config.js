import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/**
 * Vite Configuration
 * ==================
 * dev server runs on port 3000 (bound to all interfaces so it's
 * reachable through an SSH tunnel from your local machine).
 *
 * SSH tunnel command (run on LOCAL laptop):
 *   ssh -L 3000:localhost:3000 -L 5050:localhost:5050 user@YOUR_SERVER_IP
 *
 * Then open http://localhost:3000 in your LOCAL browser.
 * Your LOCAL camera (getUserMedia) will work because the browser
 * runs on your local machine even though the server is remote.
 */
export default defineConfig({
  plugins: [react()],

  server: {
    host:   "0.0.0.0",   // bind to all interfaces → reachable via SSH tunnel
    port:    3000,
    strictPort: true,

    // Optional: proxy /api/* to the Flask backend running on the same server
    // This avoids CORS issues when both run on the same remote host.
    proxy: {
      "/api": {
        target:       "http://localhost:5050",
        changeOrigin: true,
        rewrite:      (path) => path,
      },
    },
  },

  build: {
    outDir:        "dist",
    sourcemap:     true,
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom"],
        },
      },
    },
  },

  // Ensure the app works at root path
  base: "/",
});
