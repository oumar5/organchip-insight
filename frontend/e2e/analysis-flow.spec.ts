import { readFile } from "node:fs/promises";

import { expect, test } from "@playwright/test";

const SYNTHETIC_FIELD_PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAAAAACPAi4CAAAAqklEQVR4nO2VwQ2AIBAE1ViCddh/HVTkx4fK7EpQ4z2Oj4E9hl0iMC7DszY9nJ+ABCQgDGB2Ytm/q6kZ5YVSTj3JkBGK7d46oHo2wQ5wPTaBAOEXhwkg85LwxY8kDaBUA8x8Ev8/CxXAJgA5YIQEvABw9x/JASP4DLUIDgwBpE/2QFogAR0IAg5zBCxlrHwbrzeHyiU3cbXdBgdHF33Pe2OLeBYSkIAEdLUN0GMT9TKhZYgAAAAASUVORK5CYII=",
  "base64",
);

test("creates, imports, analyzes and exports a microscopy experiment", async ({ page }) => {
  const pageErrors: string[] = [];
  const unexpectedHttpErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("response", (response) => {
    if (response.status() < 400) return;
    const isExpectedEmptyResult =
      response.status() === 404 && /\/experiments\/[^/]+\/results$/.test(response.url());
    if (!isExpectedEmptyResult) {
      unexpectedHttpErrors.push(`${response.status()} ${response.url()}`);
    }
  });

  const experimentName = `Validation E2E ${Date.now()}`;
  await page.goto("/");
  await expect(page.getByText("Inférence disponible")).toBeVisible();

  await page.getByLabel("Nom de l’expérience").fill(experimentName);
  await page
    .getByLabel("Hypothèse ou objectif")
    .fill("Vérifier le parcours reproductible de la création aux exports.");
  await page.getByRole("button", { name: "Créer l’expérience" }).click();
  await expect(page.getByLabel("Expérience active")).toContainText(experimentName);

  await page
    .locator(".field-grid label", { hasText: "Moteur" })
    .locator("select")
    .selectOption("adaptive-segmentation-v1");
  await page.locator('input[type="file"]').setInputFiles({
    name: "champ-synthetique.png",
    mimeType: "image/png",
    buffer: SYNTHETIC_FIELD_PNG,
  });
  await expect(page.getByText("champ-synthetique.png")).toBeVisible();
  await page.getByRole("button", { name: /Importer les images/ }).click();
  await expect(page.getByRole("status")).toContainText("1 importé");

  const analyzeButton = page.getByRole("button", { name: "Lancer l’inférence" });
  await expect(analyzeButton).toBeEnabled();
  await analyzeButton.click();
  await expect(page.getByText(`Expérience : ${experimentName}`)).toBeVisible();
  await expect(page.getByText("Composantes connexes")).toBeVisible();
  await expect(page.getByText(/pas validé comme cellule ou noyau/)).toBeVisible();
  await expect(page.getByAltText("Segmentation de champ-synthetique.png")).toBeVisible();

  const jsonDownloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: "Exporter JSON" }).click();
  const jsonDownload = await jsonDownloadPromise;
  const jsonPath = await jsonDownload.path();
  expect(jsonPath).not.toBeNull();
  const exportedResult = JSON.parse(await readFile(jsonPath!, "utf-8"));
  expect(exportedResult.task).toBe("segmentation");
  expect(exportedResult.image_count).toBe(1);
  expect(exportedResult.image_results).toHaveLength(1);

  const csvDownloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: "Exporter CSV" }).click();
  const csvDownload = await csvDownloadPromise;
  const csvPath = await csvDownload.path();
  expect(csvPath).not.toBeNull();
  const exportedCsv = await readFile(csvPath!, "utf-8");
  expect(exportedCsv).toContain("filename");
  expect(exportedCsv).toContain("champ-synthetique.png");

  expect(page.getByRole("alert")).toHaveCount(0);
  expect(pageErrors).toEqual([]);
  expect(unexpectedHttpErrors).toEqual([]);
});
