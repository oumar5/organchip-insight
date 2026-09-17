import { readFile } from "node:fs/promises";

import { expect, test } from "@playwright/test";

const SYNTHETIC_FIELD_PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAAAAACPAi4CAAAAqklEQVR4nO2VwQ2AIBAE1ViCddh/HVTkx4fK7EpQ4z2Oj4E9hl0iMC7DszY9nJ+ABCQgDGB2Ytm/q6kZ5YVSTj3JkBGK7d46oHo2wQ5wPTaBAOEXhwkg85LwxY8kDaBUA8x8Ev8/CxXAJgA5YIQEvABw9x/JASP4DLUIDgwBpE/2QFogAR0IAg5zBCxlrHwbrzeHyiU3cbXdBgdHF33Pe2OLeBYSkIAEdLUN0GMT9TKhZYgAAAAASUVORK5CYII=",
  "base64",
);

const phase = process.env.ORGANCHIP_PERSISTENCE_PHASE;
const experimentName = process.env.ORGANCHIP_PERSISTENCE_EXPERIMENT_NAME;

test("preserves a completed experiment across a Docker restart", async ({ page }) => {
  test.skip(
    !phase || !experimentName,
    "This test is orchestrated in seed and verify phases by validate_release_persistence.sh.",
  );
  test.setTimeout(90_000);
  if (!phase || !experimentName) return;

  await page.goto("/");
  await expect(page.getByText("Inférence disponible")).toBeVisible();

  if (phase === "seed") {
    await page.getByRole("button", { name: /Nouvelle expérience/ }).first().click();
    await page.getByLabel("Nom de l’expérience").fill(experimentName);
    await page
      .getByLabel("Hypothèse ou objectif")
      .fill("Vérifier la persistance SQLite, des sources et des artefacts après redémarrage Docker.");
    await page.getByRole("button", { name: "Créer l’expérience" }).click();
    await page.getByRole("radio", { name: /adaptative/i }).click();
    await page.locator('input[type="file"]').setInputFiles({
      name: "release-persistence.png",
      mimeType: "image/png",
      buffer: SYNTHETIC_FIELD_PNG,
    });
    await page.getByRole("button", { name: /Importer les images/ }).click();
    await expect(page.getByRole("status")).toContainText("1 importé");
    await page.getByRole("button", { name: "Lancer l’analyse" }).click();
  } else {
    expect(phase).toBe("verify");
    const experimentSelect = page.getByLabel("Expérience active");
    await expect(experimentSelect.getByRole("option", { name: experimentName })).toBeAttached();
    await experimentSelect.selectOption({ label: experimentName });
    await page.getByRole("button", { name: "Résultats" }).click();
  }

  await expect(page.getByText(`Expérience : ${experimentName}`)).toBeVisible();
  await expect(page.getByText("Composantes connexes", { exact: true })).toBeVisible();
  await expect(page.getByText(/pas validé comme cellule ou noyau/)).toBeVisible();
  const gallery = page.getByRole("list", { name: "Overlays de segmentation" });
  await expect(gallery.getByRole("button")).toHaveCount(1);
  await gallery.getByRole("button").click();
  const viewer = page.getByRole("dialog");
  await expect(viewer.getByRole("button", { name: "Segmentation" })).toHaveClass(/active/);
  await viewer.getByRole("button", { name: "Source (aperçu)" }).click();
  await expect(viewer.getByAltText(/aperçu source/)).toBeVisible();
  await viewer.getByRole("button", { name: "Fermer" }).click();

  const jsonDownloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: "Exporter JSON" }).click();
  const jsonPath = await (await jsonDownloadPromise).path();
  expect(jsonPath).not.toBeNull();
  const exportedResult = JSON.parse(await readFile(jsonPath!, "utf-8"));
  expect(exportedResult.image_count).toBe(1);
  expect(exportedResult.image_results).toHaveLength(1);

  const csvDownloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: "Exporter CSV" }).click();
  const csvPath = await (await csvDownloadPromise).path();
  expect(csvPath).not.toBeNull();
  expect(await readFile(csvPath!, "utf-8")).toContain("release-persistence.png");
});
