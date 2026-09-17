import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";

import { expect, test } from "@playwright/test";

interface RealImageManifest {
  manifest_id: string;
  path_root: string;
  frozen_classification_test_used: boolean;
  images: Array<{
    path: string;
    dataset: string;
    license: string;
    acquisition_mode: string;
    sha256: string;
  }>;
}

async function sha256(path: string): Promise<string> {
  return createHash("sha256").update(await readFile(path)).digest("hex");
}

test("analyzes the locked real-image manifest without changing its sources", async ({ page }) => {
  test.setTimeout(180_000);
  const manifestPath = process.env.ORGANCHIP_REAL_E2E_MANIFEST;
  test.skip(!manifestPath, "Set ORGANCHIP_REAL_E2E_MANIFEST to run the real-image path.");
  if (!manifestPath) return;

  const manifest = JSON.parse(await readFile(manifestPath, "utf-8")) as RealImageManifest;
  expect(manifest.frozen_classification_test_used).toBe(false);
  expect(manifest.images).toHaveLength(3);

  const imageRoot = resolve(dirname(manifestPath), manifest.path_root);
  const sourcePaths = manifest.images.map((image) => resolve(imageRoot, image.path));
  const hashesBefore = await Promise.all(sourcePaths.map(sha256));
  expect(hashesBefore).toEqual(manifest.images.map((image) => image.sha256));

  const pageErrors: string[] = [];
  const unexpectedHttpErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("response", (response) => {
    if (response.status() < 400) return;
    const isExpectedEmptyResult =
      response.status() === 404 && /\/experiments\/[^/]+\/results$/.test(response.url());
    if (!isExpectedEmptyResult) unexpectedHttpErrors.push(`${response.status()} ${response.url()}`);
  });

  const experimentName = `Validation images réelles ${Date.now()}`;
  await page.goto("/");
  await expect(page.getByText("Inférence disponible")).toBeVisible();
  await page.getByRole("button", { name: /Nouvelle expérience/ }).first().click();
  await page.getByLabel("Nom de l’expérience").fill(experimentName);
  await page
    .getByLabel("Hypothèse ou objectif")
    .fill(`Smoke test réel verrouillé par ${manifest.manifest_id}, sans accès au test gelé.`);
  await page.getByRole("button", { name: "Créer l’expérience" }).click();
  await expect(page.getByLabel("Expérience active")).toContainText(experimentName);

  await page.getByRole("radio", { name: /adaptative/i }).click();
  await page.locator('input[type="file"]').setInputFiles(sourcePaths);
  for (const sourcePath of sourcePaths) {
    await expect(page.getByText(sourcePath.split("/").at(-1) ?? sourcePath)).toBeVisible();
  }
  await page.getByRole("button", { name: /Importer les images/ }).click();
  await expect(page.getByRole("status")).toContainText("3 importé(s)");
  await expect(page.getByText("3 images importées")).toBeVisible();
  await expect(page.getByText("TIFF · 8 bits/canal")).toBeVisible();

  const sourceGallery = page.getByRole("list", { name: "Images importées" });
  await expect(sourceGallery.getByRole("button")).toHaveCount(3);
  await sourceGallery.getByRole("button", { name: /SN90_C_1_000_dic\.tif/ }).click();
  let viewer = page.getByRole("dialog");
  await expect(viewer.getByText("Format source")).toBeVisible();
  await expect(viewer.getByText("PNG 8 bits · affichage uniquement")).toBeVisible();
  await expect(viewer.getByText("fichier source original")).toBeVisible();
  await viewer.getByRole("button", { name: "Fermer" }).click();

  const analyzeButton = page.getByRole("button", { name: "Lancer l’analyse" });
  await expect(analyzeButton).toBeEnabled();
  await analyzeButton.click();
  await expect(page.getByText(`Expérience : ${experimentName}`)).toBeVisible({
    timeout: 90_000,
  });
  await expect(page.getByText("Composantes connexes", { exact: true })).toBeVisible();
  await expect(page.getByText(/pas validé comme cellule ou noyau/)).toBeVisible();

  const segmentationGallery = page.getByRole("list", { name: "Overlays de segmentation" });
  await expect(segmentationGallery.getByRole("button")).toHaveCount(3);
  await segmentationGallery.getByRole("button").first().click();
  viewer = page.getByRole("dialog");
  await expect(viewer.getByRole("button", { name: "Segmentation" })).toHaveClass(/active/);
  await viewer.getByRole("button", { name: "Source (aperçu)" }).click();
  await expect(viewer.getByAltText(/aperçu source/)).toBeVisible();
  await expect(viewer.getByText(/PNG 8 bits destiné uniquement à l’affichage/)).toBeVisible();
  await viewer.getByRole("button", { name: "Fermer" }).click();

  const jsonDownloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: "Exporter JSON" }).click();
  const jsonPath = await (await jsonDownloadPromise).path();
  expect(jsonPath).not.toBeNull();
  const exportedResult = JSON.parse(await readFile(jsonPath!, "utf-8"));
  expect(exportedResult.task).toBe("segmentation");
  expect(exportedResult.image_count).toBe(3);
  expect(exportedResult.image_results).toHaveLength(3);

  const csvDownloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: "Exporter CSV" }).click();
  const csvPath = await (await csvDownloadPromise).path();
  expect(csvPath).not.toBeNull();
  const exportedCsv = await readFile(csvPath!, "utf-8");
  expect(exportedCsv).toContain("filename");
  for (const sourcePath of sourcePaths) {
    expect(exportedCsv).toContain(sourcePath.split("/").at(-1) ?? sourcePath);
  }

  expect(await Promise.all(sourcePaths.map(sha256))).toEqual(hashesBefore);
  expect(page.getByRole("alert")).toHaveCount(0);
  expect(pageErrors).toEqual([]);
  expect(unexpectedHttpErrors).toEqual([]);
});
