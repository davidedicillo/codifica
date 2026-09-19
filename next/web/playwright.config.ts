import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  use: { baseURL: process.env.CODIFICA_TEST_URL || "http://127.0.0.1:5173", headless: true },
  workers: 1,
  reporter: "list",
  timeout: 30000,
});
