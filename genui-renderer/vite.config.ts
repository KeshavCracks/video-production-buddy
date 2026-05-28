import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [
    react(),
    {
      name: "video-production-buddy-strip-trailing-bundle-whitespace",
      generateBundle(_options, bundle) {
        for (const artifact of Object.values(bundle)) {
          if (artifact.type === "chunk") {
            artifact.code = artifact.code.replace(/[ \t]+$/gm, "");
          } else if (typeof artifact.source === "string") {
            artifact.source = artifact.source.replace(/[ \t]+$/gm, "");
          }
        }
      }
    }
  ],
  base: "/",
  build: {
    outDir: "../lib/genui/static/renderer",
    emptyOutDir: true,
    assetsDir: "assets",
    rollupOptions: {
      output: {
        entryFileNames: "assets/index.js",
        chunkFileNames: "assets/[name].js",
        assetFileNames: "assets/[name][extname]"
      }
    }
  }
});
