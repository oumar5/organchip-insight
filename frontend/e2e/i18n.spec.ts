import { expect, test } from "@playwright/test";

test("switches the complete interface to English and persists the preference", async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => window.localStorage.removeItem("organchip.locale"));
  await page.reload();

  await expect(page.locator("html")).toHaveAttribute("lang", "fr");
  await expect(page.getByRole("button", { name: "Espace de travail" })).toBeVisible();

  await page.getByRole("button", { name: "EN", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.getByRole("button", { name: "Workspace", exact: true })).toBeVisible();
  await expect(page.getByText("Inference available")).toBeVisible();
  await expect(page.getByRole("button", { name: /New experiment/ }).first()).toBeVisible();

  await page.getByRole("button", { name: /New experiment/ }).first().click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByLabel("Experiment name")).toBeVisible();
  await expect(dialog.getByRole("button", { name: "Create experiment" })).toBeVisible();
  await dialog.getByRole("button", { name: "Cancel" }).click();

  await page.getByRole("button", { name: "Benchmarks", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Engine comparison" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Organoid foreground · iOrganoAssay v1.1.0" })).toBeVisible();

  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.getByRole("button", { name: "Workspace", exact: true })).toBeVisible();

  await page.getByRole("button", { name: "FR", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "fr");
  await expect(page.getByRole("button", { name: "Espace de travail" })).toBeVisible();
});
