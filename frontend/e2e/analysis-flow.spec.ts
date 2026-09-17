import { readFile } from "node:fs/promises";

import AxeBuilder from "@axe-core/playwright";
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

  await page.getByRole("button", { name: /Nouvelle expérience/ }).first().click();
  const createDialog = page.getByRole("dialog");
  await createDialog.getByLabel("Nom de l’expérience").fill(experimentName);
  await createDialog
    .getByLabel("Hypothèse ou objectif")
    .fill("Vérifier le parcours reproductible de la création aux exports.");
  await createDialog.getByLabel("Identifiant de puce").fill("chip-e2e-01");
  await createDialog.getByLabel("Puits").fill("A01");
  await createDialog.getByLabel("Lignée / modèle").fill("iPSC-E2E");
  await createDialog.getByLabel("Jour de culture").fill("14");
  await createDialog.getByLabel("Échelle (µm/pixel)").fill("0.5");
  await createDialog.getByLabel("Source de calibration").fill("Microscope E2E metadata");
  await createDialog.getByRole("button", { name: "Créer l’expérience" }).click();
  await expect(page.getByLabel("Expérience active")).toContainText(experimentName);
  await expect(page.getByText("Puce · chip-e2e-01")).toBeVisible();
  await expect(page.getByText("0,5 µm/pixel")).toBeVisible();

  await page.getByRole("radio", { name: /adaptative/i }).click();
  await page.locator('input[type="file"]').setInputFiles({
    name: "champ-synthetique.png",
    mimeType: "image/png",
    buffer: SYNTHETIC_FIELD_PNG,
  });
  await expect(page.getByText("champ-synthetique.png")).toBeVisible();
  await page.getByRole("button", { name: /Importer les images/ }).click();
  await expect(page.getByRole("status")).toContainText("1 importé");

  const analyzeButton = page.getByRole("button", { name: "Lancer l’analyse" });
  await expect(analyzeButton).toBeEnabled();
  await analyzeButton.click();
  await expect(page.getByText(`Expérience : ${experimentName}`)).toBeVisible();
  await expect(page.getByText("Composantes connexes", { exact: true })).toBeVisible();
  await expect(page.getByText(/pas validé comme cellule ou noyau/)).toBeVisible();
  await expect(page.getByAltText("Segmentation de champ-synthetique.png")).toBeVisible();
  await page.getByRole("button", { name: "Benchmarks" }).click();
  await expect(page.getByRole("heading", { name: "Comparaison des moteurs" })).toBeVisible();
  await expect(page.getByText("0,816", { exact: true })).toBeVisible();
  await expect(page.getByText("Non promu · 2 critères sur 3 échouent")).toBeVisible();

  await page.getByRole("button", { name: "Résultats" }).click();
  await expect(page.getByRole("link", { name: "Exporter JSON" })).toBeVisible();
  const jsonDownloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: "Exporter JSON" }).click();
  const jsonDownload = await jsonDownloadPromise;
  const jsonPath = await jsonDownload.path();
  expect(jsonPath).not.toBeNull();
  const exportedResult = JSON.parse(await readFile(jsonPath!, "utf-8"));
  expect(exportedResult.task).toBe("segmentation");
  expect(exportedResult.image_count).toBe(1);
  expect(exportedResult.image_results).toHaveLength(1);
  expect(exportedResult.experiment_metadata).toMatchObject({
    chip_id: "chip-e2e-01",
    well_id: "A01",
    culture_day: 14,
    microns_per_pixel: 0.5,
    calibration_source: "Microscope E2E metadata",
  });

  const csvDownloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: "Exporter CSV" }).click();
  const csvDownload = await csvDownloadPromise;
  const csvPath = await csvDownload.path();
  expect(csvPath).not.toBeNull();
  const exportedCsv = await readFile(csvPath!, "utf-8");
  expect(exportedCsv).toContain("filename");
  expect(exportedCsv).toContain("champ-synthetique.png");
  expect(exportedCsv).toContain("mean_object_area_um2");

  await page.getByRole("button", { name: /Segmentation de champ-synthetique.png/ }).click();
  const viewer = page.getByRole("dialog");
  await expect(viewer.getByRole("heading", { name: "champ-synthetique.png" })).toBeVisible();
  await viewer.getByRole("button", { name: "Augmenter le zoom" }).click();
  await expect(viewer.getByText("125 %")).toBeVisible();
  await viewer.getByRole("button", { name: "Côte à côte" }).click();
  await expect(viewer.getByAltText(/aperçu source/)).toBeVisible();
  await expect(viewer.getByAltText(/segmentation/)).toBeVisible();
  await viewer.getByRole("button", { name: "Réinitialiser" }).click();
  await viewer.getByRole("button", { name: "Source (aperçu)" }).click();
  await expect(viewer.getByAltText(/aperçu source/)).toBeVisible();
  await expect(viewer.getByText(/PNG 8 bits destiné uniquement à l’affichage/)).toBeVisible();
  await viewer.getByRole("button", { name: "Fermer" }).click();
  await expect(viewer).toBeHidden();

  const comparisonName = `Comparaison E2E ${Date.now()}`;
  const comparisonCreate = await page.request.post("/api/v1/experiments", {
    data: {
      name: comparisonName,
      chip_id: "chip-e2e-02",
      well_id: "B02",
      cell_line: "iPSC-E2E",
      culture_day: 21,
      microns_per_pixel: 0.5,
      calibration_source: "Microscope E2E metadata",
    },
  });
  expect(comparisonCreate.ok()).toBeTruthy();
  const comparison = await comparisonCreate.json();
  const comparisonUpload = await page.request.post(`/api/v1/experiments/${comparison.id}/images`, {
    multipart: {
      files: {
        name: "comparaison-synthetique.png",
        mimeType: "image/png",
        buffer: SYNTHETIC_FIELD_PNG,
      },
    },
  });
  expect(comparisonUpload.ok()).toBeTruthy();
  const comparisonAnalysis = await page.request.post(`/api/v1/experiments/${comparison.id}/analyze`);
  expect(comparisonAnalysis.ok()).toBeTruthy();

  await page.reload();
  await page.getByLabel("Expérience active").selectOption({ label: experimentName });
  await page.getByRole("button", { name: "Résultats" }).click();
  await page.getByLabel("Seconde expérience").selectOption({ label: comparisonName });
  await expect(page.getByText("Métriques communes aux deux analyses", { exact: true })).toBeVisible();
  await expect(page.getByRole("rowheader", { name: "Aire moyenne calibrée (µm²)" })).toBeVisible();

  expect(page.getByRole("alert")).toHaveCount(0);
  expect(pageErrors).toEqual([]);
  expect(unexpectedHttpErrors).toEqual([]);

  const undersizedText = await page.evaluate(() => {
    const findings = new Set<string>();
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const text = node.textContent?.trim();
      const element = node.parentElement;
      if (!text || !element) continue;
      const style = window.getComputedStyle(element);
      if (
        style.display === "none" ||
        style.visibility === "hidden" ||
        Number(style.opacity) === 0 ||
        element.getClientRects().length === 0
      ) {
        continue;
      }
      const fontSize = Number.parseFloat(style.fontSize);
      if (fontSize < 12) {
        findings.add(`${element.tagName.toLowerCase()}.${element.className}: ${fontSize}px — ${text.slice(0, 60)}`);
      }
    }
    return [...findings].sort();
  });
  expect(undersizedText).toEqual([]);

  const contrastAudit = await new AxeBuilder({ page })
    .withRules(["color-contrast"])
    .analyze();
  const contrastFailures = contrastAudit.violations.flatMap((violation) =>
    violation.nodes.map((node) => ({
      target: node.target.join(" "),
      message: node.any.map((check) => check.message).join("; "),
    })),
  );
  expect(contrastFailures).toEqual([]);
});
