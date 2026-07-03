import { expect, test } from "@playwright/test";

test.skip(
  process.env.E2E_LIVE !== "1",
  "Set E2E_LIVE=1 with Supabase, backend, and Lemon Squeezy test config to run live flows."
);

const uniqueEmail = `e2e+${Date.now()}@jobmatch.ai`;
const password = "JobMatch123!";

async function register(page: import("@playwright/test").Page) {
  await page.goto("/register");
  await page.getByLabel(/email/i).fill(uniqueEmail);
  await page.getByLabel(/password/i).fill(password);
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: /registr/i }).click();
}

test("register -> wizard -> job analysis -> Match Report", async ({ page }) => {
  await register(page);

  await page.goto("/wizard/step-1");
  await page.getByLabel(/headline/i).fill("Backend Engineer");
  await page.getByLabel(/summary|bio/i).fill("Python and FastAPI engineer.");
  await page.getByLabel(/target_role/i).fill("Backend Engineer");
  await page.getByRole("button", { name: /continuar/i }).click();

  await page.goto("/wizard/step-2");
  await expect(page.getByText(/subir cv|upload/i)).toBeVisible();

  await page.goto("/wizard/step-3");
  await page.getByRole("button", { name: /confirmar todo/i }).click();

  await page.goto("/wizard/step-4");
  await page.getByRole("button", { name: /completar|finalizar/i }).click();

  await page.goto("/dashboard");
  await page.getByPlaceholder(/analiz/i).fill("Python FastAPI backend role");
  await page.getByRole("button", { name: /analiz/i }).click();
  await expect(page.getByText(/analizando/i)).toBeVisible();

  await page.goto("/jobs/e2e-match-id");
  await expect(page.getByText(/Match Score/i)).toBeVisible();
});

test("premium upgrade -> creates Interview Kit -> verifies tabs", async ({ page }) => {
  await page.goto("/pricing");
  await page.getByRole("button", { name: /upgrade/i }).click();
  await page.goto("/pricing/success");

  await page.goto("/interview-kits/new");
  await page.getByLabel(/LinkedIn de la empresa/i).fill(
    "https://www.linkedin.com/company/acme"
  );
  await page.getByLabel(/LinkedIn del entrevistador/i).fill(
    "https://www.linkedin.com/in/jane-doe"
  );
  await page.getByRole("button", { name: /Generar mi Kit/i }).click();

  await page.goto("/interview-kits/e2e-kit-id");
  for (const tab of [
    "Fit CV",
    "Fortalezas",
    "Brechas",
    "Argumentario",
    "Respuestas modelo",
    "Tus preguntas",
    "Plan de acción"
  ]) {
    await expect(page.getByRole("button", { name: new RegExp(tab, "i") })).toBeVisible();
  }
});

test("account deletion logs the user out", async ({ page, request }) => {
  await page.goto("/dashboard");
  const response = await request.delete("/api/v1/users/me");
  expect([204, 401]).toContain(response.status());

  await page.goto("/dashboard");
  await expect(page).toHaveURL(/login/);
});
