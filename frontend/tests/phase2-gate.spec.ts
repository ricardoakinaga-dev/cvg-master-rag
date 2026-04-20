import { expect, test, type Page } from "@playwright/test";
import path from "path";

const ROUTES: Array<{ path: string; title: string }> = [
  { path: "/", title: "Início" },
  { path: "/documents", title: "Documentos" },
  { path: "/search", title: "Busca" },
  { path: "/chat", title: "Chat" },
  { path: "/admin", title: "Admin" },
  { path: "/dashboard", title: "Dashboard" },
  { path: "/audit", title: "Auditoria" },
];

const EMAILS = {
  admin: "admin@demo.local",
  operator: "operator@demo.local",
  viewer: "viewer@demo.local",
} as const;

async function loginAs(
  page: Page,
  role: "admin" | "operator" | "viewer" = "admin",
  tenantId = "default",
) {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: /Entre com identidade/i })).toBeVisible();
  await page.getByLabel("Perfil").selectOption(role);
  await page.getByLabel("E-mail").fill(EMAILS[role]);
  await page.getByLabel("Tenant").selectOption(tenantId);
  await page.getByLabel("Senha").fill("demo1234");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: "Início" })).toBeVisible();
}

test.describe("Fase 2 gate smoke", () => {
  test("rotas principais renderizam no desktop", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await loginAs(page, "admin");

    for (const route of ROUTES) {
      await page.goto(route.path);
      await expect(page.getByRole("heading", { name: route.title })).toBeVisible();
    }
  });

  test("documentos executa upload web pela UI", async ({ page }) => {
    const fixture = path.join(process.cwd(), "tests", "fixtures", "upload-smoke.txt");

    await loginAs(page, "admin", "acme-lab");
    await page.goto("/documents");
    await expect(page.getByLabel("Workspace").first()).toHaveValue("acme-lab");
    await page.getByRole("button", { name: "Aplicar filtros" }).click();
    await page.getByRole("button", { name: "Upload" }).click();
    const dialog = page.getByRole("dialog", { name: "Upload de documento" });
    await expect(dialog).toBeVisible();
    await expect(page.getByText("Arraste e solte")).toBeVisible();
    await dialog.getByLabel("Arquivo").setInputFiles(fixture);
    await dialog.getByRole("button", { name: "Enviar" }).click();

    await expect(page.getByText("Documento enviado")).toBeVisible({ timeout: 30000 });
    await expect(page.getByText("upload-smoke.txt").first()).toBeVisible();
  });

  test("troca de tenant mantém isolamento visual mínimo", async ({ page }) => {
    await loginAs(page, "admin", "acme-lab");
    await page.goto("/documents");

    await expect(page.getByLabel("Workspace").first()).toHaveValue("acme-lab");
    await expect(page.getByText("upload-smoke.txt").first()).toBeVisible();

    await page.getByLabel("Tenant ativo").selectOption("northwind");

    await expect(page.getByLabel("Workspace").first()).toHaveValue("northwind");
    await expect(page.getByText("northwind-playbook.txt").first()).toBeVisible();
    await expect(page.getByText("upload-smoke.txt")).toHaveCount(0);
  });

  test("busca executa retrieval pela UI", async ({ page }) => {
    await loginAs(page, "admin");
    await page.goto("/search");
    await page.getByLabel("Pergunta").fill("reembolso prazo");
    await page.getByRole("button", { name: "Executar busca" }).click();

    await expect(page.getByText("Detalhe da evidência")).toBeVisible();
    await expect(page.getByText(/30 dias corridos/i).first()).toBeVisible();
    await expect(page.getByText("Raw JSON")).toBeVisible();
  });

  test("chat executa query pela UI", async ({ page }) => {
    await loginAs(page, "admin");
    await page.goto("/chat");
    await page.getByLabel("Pergunta").fill("Qual o prazo para reembolso?");
    await page.getByRole("button", { name: "Gerar resposta" }).click();

    await expect(page.getByText("Resposta").first()).toBeVisible();
    await expect(page.getByText(/Citação:/)).toBeVisible();
    await expect(page.getByText(/reembolso/i).first()).toBeVisible();
  });

  test("tablet mantém módulos acessíveis", async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await loginAs(page, "admin");

    for (const route of ROUTES.slice(1)) {
      await page.goto(route.path);
      await expect(page.getByRole("heading", { name: route.title })).toBeVisible();
    }
  });
});
