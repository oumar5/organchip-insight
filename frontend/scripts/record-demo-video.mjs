import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const manifestPath = resolve(
  process.env.ORGANCHIP_REAL_E2E_MANIFEST ??
    resolve(repositoryRoot, "data/manifests/product-real-smoke-v1.json"),
);
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:18283";
const rawVideoPath = resolve(
  process.env.ORGANCHIP_DEMO_RAW_VIDEO ??
    resolve(repositoryRoot, "output/video/organchip-insight-demo-candidate.webm"),
);
const burnCaptions = process.env.ORGANCHIP_DEMO_BURN_CAPTIONS !== "false";
const subtitlePath = resolve(
  process.env.ORGANCHIP_DEMO_SUBTITLE ??
    resolve(repositoryRoot, "output/video/organchip-insight-demo-candidate.en.srt"),
);

const scenes = [
  {
    end: 18,
    caption:
      "Organ-on-chip microscopy needs more than a model score. OrganChip Insight keeps images, measurements, provenance, and scientific limits in one local experiment.",
  },
  {
    end: 50,
    caption:
      "A named objective is recorded before analysis. This public smoke batch combines RGB and grayscale OoC images with an external BBBC019 TIFF; uploads remain separate from inference.",
  },
  {
    end: 86,
    caption:
      "The default adaptive engine is local, CPU-only, and weight-free. TIFF previews are display-only; the original source is analyzed. The interface never calls connected components validated cells.",
  },
  {
    end: 116,
    caption:
      "Every overlay stays linked to its source and measurements. Areas and diameters remain in pixels because physical calibration is unavailable, and the reservation is visible beside the result.",
  },
  {
    end: 136,
    caption:
      "JSON and CSV exports preserve the experiment, engine, parameters, per-image results, and generation time for downstream audit.",
  },
  {
    end: 172,
    caption:
      "Versioned external benchmarks expose both accuracy and cost. µSAM is stronger on BBBC019 foreground segmentation, but fails two of three preregistered BBBC038 promotion criteria and remains isolated.",
  },
  {
    end: 198,
    caption:
      "Quality classification did not demonstrate a robust signal independent of acquisition shortcuts, so the frozen test set remains unopened. The reproducible product ships with abstention, checksums, tests, and explicit limits.",
  },
];

function srtTimestamp(seconds) {
  const milliseconds = Math.round(seconds * 1000);
  const hours = Math.floor(milliseconds / 3_600_000);
  const minutes = Math.floor((milliseconds % 3_600_000) / 60_000);
  const wholeSeconds = Math.floor((milliseconds % 60_000) / 1000);
  const remainder = milliseconds % 1000;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(wholeSeconds).padStart(2, "0")},${String(remainder).padStart(3, "0")}`;
}

function subtitleDocument() {
  let start = 0;
  return `${scenes
    .map((scene, index) => {
      const block = `${index + 1}\n${srtTimestamp(start)} --> ${srtTimestamp(scene.end)}\n${scene.caption}`;
      start = scene.end;
      return block;
    })
    .join("\n\n")}\n`;
}

async function sha256(path) {
  return createHash("sha256").update(await readFile(path)).digest("hex");
}

async function installCaption(page) {
  await page.evaluate(() => {
    const caption = document.createElement("div");
    caption.id = "submission-caption";
    Object.assign(caption.style, {
      position: "fixed",
      zIndex: "2147483647",
      left: "7%",
      right: "7%",
      bottom: "22px",
      padding: "14px 22px",
      borderRadius: "12px",
      background: "rgba(10, 30, 25, 0.92)",
      color: "white",
      font: "600 20px/1.35 Arial, sans-serif",
      textAlign: "center",
      boxShadow: "0 8px 28px rgba(0, 0, 0, 0.28)",
      pointerEvents: "none",
    });
    caption.setAttribute("aria-hidden", "true");
    document.body.append(caption);
  });
}

async function setCaption(page, text) {
  await page.evaluate((value) => {
    const caption = document.querySelector("#submission-caption");
    if (caption) caption.textContent = value;
  }, text);
}

const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
if (manifest.frozen_classification_test_used !== false || manifest.images.length !== 3) {
  throw new Error("The demo requires the locked three-image manifest with frozen test disabled.");
}
const imageRoot = resolve(dirname(manifestPath), manifest.path_root);
const sourcePaths = manifest.images.map((image) => resolve(imageRoot, image.path));
const sourceHashes = await Promise.all(sourcePaths.map(sha256));
if (sourceHashes.some((digest, index) => digest !== manifest.images[index].sha256)) {
  throw new Error("A locked demo source does not match its SHA-256.");
}

await mkdir(dirname(rawVideoPath), { recursive: true });
await writeFile(subtitlePath, subtitleDocument());

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  acceptDownloads: true,
  colorScheme: "light",
  locale: "fr-FR",
  recordVideo: { dir: dirname(rawVideoPath), size: { width: 1280, height: 720 } },
  viewport: { width: 1280, height: 720 },
});
const page = await context.newPage();
const video = page.video();
const startedAt = Date.now();

async function scene(index, action) {
  await setCaption(page, scenes[index].caption);
  await action();
  const remaining = scenes[index].end * 1000 - (Date.now() - startedAt);
  if (remaining > 0) await page.waitForTimeout(remaining);
}

let recordingError;
try {
  await page.goto(baseURL, { waitUntil: "networkidle" });
  if (burnCaptions) await installCaption(page);
  await scene(0, async () => {
    await page.locator("body").press("Home");
    await page.getByText("Inférence disponible").waitFor();
  });

  const experimentName = "Public demo · evidence-gated microscopy";
  await scene(1, async () => {
    await page.getByRole("button", { name: /Nouvelle expérience/ }).first().click();
    await page.getByLabel("Nom de l’expérience").fill(experimentName);
    await page
      .getByLabel("Hypothèse ou objectif")
      .fill("Demonstrate traceable analysis on three public, hash-locked images.");
    await page.getByRole("button", { name: "Créer l’expérience" }).click();
    await page.getByLabel("Expérience active").filter({ hasText: experimentName }).waitFor();
    await page.locator('input[type="file"]').setInputFiles(sourcePaths);
    await page.getByRole("button", { name: /Importer les images/ }).click();
    await page.getByRole("status").filter({ hasText: "3 importé(s)" }).waitFor();
    await page.getByText("3 images importées").scrollIntoViewIfNeeded();
  });

  await scene(2, async () => {
    const gallery = page.getByRole("list", { name: "Images importées" });
    await gallery.getByRole("button", { name: /SN90_C_1_000_dic\.tif/ }).click();
    const viewer = page.getByRole("dialog");
    await viewer.getByText("fichier source original").waitFor();
    await page.waitForTimeout(3500);
    await viewer.getByRole("button", { name: "Fermer" }).click();
    await page.getByRole("button", { name: "Lancer l’analyse" }).click();
    await page.getByText(`Expérience : ${experimentName}`).waitFor({ timeout: 90_000 });
    await page.getByText("Composantes connexes", { exact: true }).scrollIntoViewIfNeeded();
  });

  await scene(3, async () => {
    const gallery = page.getByRole("list", { name: "Overlays de segmentation" });
    await gallery.getByRole("button").first().click();
    const viewer = page.getByRole("dialog");
    await viewer.getByRole("button", { name: "Source (aperçu)" }).click();
    await page.waitForTimeout(3500);
    await viewer.getByRole("button", { name: "Segmentation" }).click();
    await page.waitForTimeout(3500);
    await viewer.getByRole("button", { name: "Fermer" }).click();
    await page.getByText(/pas validé comme cellule ou noyau/).scrollIntoViewIfNeeded();
  });

  await scene(4, async () => {
    const jsonDownload = page.waitForEvent("download");
    await page.getByRole("link", { name: "Exporter JSON" }).click();
    await jsonDownload;
    const csvDownload = page.waitForEvent("download");
    await page.getByRole("link", { name: "Exporter CSV" }).click();
    await csvDownload;
    await page.getByText("Niveau de preuve, limites et provenance").scrollIntoViewIfNeeded();
  });

  await scene(5, async () => {
    await page.getByRole("button", { name: "Benchmarks" }).click();
    await page.getByRole("heading", { name: "Comparaison des moteurs" }).waitFor();
    await page.getByText("Premier plan microfluidique · BBBC019").scrollIntoViewIfNeeded();
    await page.waitForTimeout(6000);
    await page.getByText("Instances nucléaires · BBBC038").scrollIntoViewIfNeeded();
    await page.waitForTimeout(6000);
    await page.getByText("Provenance des chiffres").click();
    await page.getByText(/reports\/benchmarks\/bbbc019/).first().scrollIntoViewIfNeeded();
  });

  await scene(6, async () => {
    await page.getByRole("button", { name: "Espace de travail" }).click();
    await page.getByRole("heading", { name: "Moteur" }).scrollIntoViewIfNeeded();
    const detailButtons = page.getByRole("button", { name: "Détails et limites" });
    await detailButtons.last().click();
    await page.getByRole("dialog").waitFor();
    await page.waitForTimeout(8000);
    await page.getByRole("dialog").getByRole("button", { name: "Fermer" }).click();
    await page.getByRole("button", { name: "Résultats" }).click();
    await page.getByRole("heading", { name: "Résultats" }).first().scrollIntoViewIfNeeded();
  });
} catch (error) {
  recordingError = error;
}

await page.close();
if (video) await video.saveAs(rawVideoPath);
await context.close();
await browser.close();
if (recordingError) throw recordingError;
if (!video) throw new Error("Playwright did not create a demo recording.");
if ((await Promise.all(sourcePaths.map(sha256))).some((digest, index) => digest !== sourceHashes[index])) {
  throw new Error("A locked demo source changed during recording.");
}
console.log(JSON.stringify({ raw_video: rawVideoPath, subtitles: subtitlePath, scenes: scenes.length }));
