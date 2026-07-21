import { defineConfig } from "vite"

export default defineConfig({
  base: "./",
  build: {
    outDir: "../src/streamlit_testing_feedback/frontend/dist",
    emptyOutDir: true,
  },
})
