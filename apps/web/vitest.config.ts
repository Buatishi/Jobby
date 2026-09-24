import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  // Next compila el JSX con el runtime automático; los tests de rutas .tsx necesitan lo mismo.
  esbuild: {
    jsx: "automatic"
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL(".", import.meta.url))
    }
  },
  test: {
    environment: "node",
    globals: true,
    include: ["src/**/*.test.ts", "lib/**/*.test.ts"]
  }
});
