import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Served from https://<user>.github.io/Lake-Tanganyika/ in production (GitHub
// Pages project site), but from / during local dev and preview.
export default defineConfig(({ command }) => ({
  base: command === "build" ? "/Lake-Tanganyika/" : "/",
  plugins: [react()],
}));
