import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  // Tailwind v4 runs as a Vite plugin, so no tailwind.config.js or
  // postcss.config.js file is needed.
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
  },
});
