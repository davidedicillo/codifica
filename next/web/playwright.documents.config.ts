import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  testMatch: ["documents.spec.ts", "channels.spec.ts"],
  use: { baseURL: "http://127.0.0.1:8794", headless: true },
  workers: 1,
  reporter: "list",
  timeout: 30000,
  webServer: {
    command: "cd .. && CODIFICA_DEV_AUTH=1 CODIFICA_ORIGIN=http://127.0.0.1:8794 CODIFICA_SECRET_KEY=document-tests-local-only-secret-2026 CODIFICA_PILOT_EMAILS=davide@example.com,enrico@example.com CODIFICA_DATABASE_PATH=document-e2e.sqlite .venv-api/bin/python -m uvicorn server.app:app --host 127.0.0.1 --port 8794 --no-access-log",
    url: "http://127.0.0.1:8794/health",
    reuseExistingServer: false,
  },
});
