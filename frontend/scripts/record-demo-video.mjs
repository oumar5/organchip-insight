import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { basename, dirname, resolve } from "node:path";
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
const language = process.env.ORGANCHIP_DEMO_LANGUAGE ?? "fr";
if (!new Set(["en", "fr"]).has(language)) {
  throw new Error(`Unsupported demo language: ${language}`);
}
const subtitlePath = resolve(
  process.env.ORGANCHIP_DEMO_SUBTITLE ??
    resolve(repositoryRoot, "output/video/organchip-insight-demo-candidate.en.srt"),
);

const ui = language === "en"
  ? {
      status: "Inference available",
      newExperiment: /New experiment/,
      experimentName: "Experiment name",
      objective: "Hypothesis or objective",
      createExperiment: "Create experiment",
      activeExperiment: "Active experiment",
      importImages: /Upload images/,
      importButtonText: "Upload images",
      importSummary: "3 imported",
      importedCount: "3 images imported",
      importedImages: "Imported images",
      sourceOriginal: "original source file",
      close: "Close",
      runAnalysis: "Run analysis",
      experimentPrefix: "Experiment",
      connectedComponents: "Connected components",
      overlays: "Segmentation overlays",
      sourcePreview: "Source (preview)",
      reservation: /not been validated as a cell or nucleus/,
      exportJson: "Export JSON",
      exportCsv: "Export CSV",
      evidence: "Evidence level, limitations, and provenance",
      engineComparison: "Engine comparison",
      foreground: "Microfluidic foreground · BBBC019",
      instances: "Nuclear instances · BBBC038",
      provenance: "Metric provenance",
      workspace: "Workspace",
      engine: "Engine",
      details: "Details and limits",
      results: "Results",
      description: "Demonstrate traceable analysis on three public, hash-locked images.",
      sideBySide: "Side by side",
      zoomIn: "Zoom in",
      secondExperiment: "Second experiment",
      comparisonMetrics: "Metrics shared by both analyses",
    }
  : {
      status: "Inférence disponible",
      newExperiment: /Nouvelle expérience/,
      experimentName: "Nom de l’expérience",
      objective: "Hypothèse ou objectif",
      createExperiment: "Créer l’expérience",
      activeExperiment: "Expérience active",
      importImages: /Importer les images/,
      importButtonText: "Importer les images",
      importSummary: "3 importé(s)",
      importedCount: "3 images importées",
      importedImages: "Images importées",
      sourceOriginal: "fichier source original",
      close: "Fermer",
      runAnalysis: "Lancer l’analyse",
      experimentPrefix: "Expérience",
      connectedComponents: "Composantes connexes",
      overlays: "Overlays de segmentation",
      sourcePreview: "Source (aperçu)",
      reservation: /pas validé comme cellule ou noyau/,
      exportJson: "Exporter JSON",
      exportCsv: "Exporter CSV",
      evidence: "Niveau de preuve, limites et provenance",
      engineComparison: "Comparaison des moteurs",
      foreground: "Premier plan microfluidique · BBBC019",
      instances: "Instances nucléaires · BBBC038",
      provenance: "Provenance des chiffres",
      workspace: "Espace de travail",
      engine: "Moteur",
      details: "Détails et limites",
      results: "Résultats",
      description: "Démontrer une analyse traçable sur trois images publiques verrouillées par empreinte.",
      sideBySide: "Côte à côte",
      zoomIn: "Augmenter le zoom",
      secondExperiment: "Seconde expérience",
      comparisonMetrics: "Métriques communes aux deux analyses",
    };

const scenes = [
  {
    end: 16,
    caption:
      "OrganChip Insight keeps microscopy images, measurements, provenance, and limits together.",
  },
  {
    end: 42,
    caption:
      "Record the protocol first. Imports remain separate from inference.",
  },
  {
    end: 72,
    caption:
      "Analysis stays local and uses the original source, never the display preview.",
  },
  {
    end: 105,
    caption:
      "Zoom source and overlay together. Physical units require a documented scale.",
  },
  {
    end: 128,
    caption:
      "Exports stay auditable. Completed experiments are compared descriptively.",
  },
  {
    end: 156,
    caption:
      "Versioned benchmarks report accuracy, uncertainty, runtime, memory, and promotion decisions.",
  },
  {
    end: 180,
    caption:
      "Classification abstains; the frozen test set remains unopened, with limitations visible.",
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
  locale: language === "en" ? "en-US" : "fr-FR",
  recordVideo: { dir: dirname(rawVideoPath), size: { width: 1280, height: 720 } },
  viewport: { width: 1280, height: 720 },
});
await context.addInitScript((locale) => {
  window.localStorage.setItem("organchip.locale", locale);
}, language);
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
    await page.getByText(ui.status).waitFor();
  });

  const experimentName = "Public demo · evidence-gated microscopy";
  const comparisonName = "Public demo · descriptive repeat";
  await scene(1, async () => {
    await page.getByRole("button", { name: ui.newExperiment }).first().click();
    await page.getByLabel(ui.experimentName).fill(experimentName);
    await page
      .getByLabel(ui.objective)
      .fill(ui.description);
    await page.getByRole("button", { name: ui.createExperiment }).click();
    const experimentSelect = page.getByLabel(ui.activeExperiment);
    await experimentSelect.waitFor();
    await page.waitForFunction(
      ({ selector, expected }) => {
        const select = document.querySelector(selector);
        return select instanceof HTMLSelectElement
          && !select.disabled
          && select.selectedOptions[0]?.textContent === expected;
      },
      { selector: "#active-experiment", expected: experimentName },
    );
    const fileInput = page.locator('input[type="file"]');
    await page.waitForFunction(
      () => {
        const input = document.querySelector('input[type="file"]');
        return input instanceof HTMLInputElement && !input.disabled;
      },
    );
    await fileInput.setInputFiles(sourcePaths);
    await page.waitForFunction(
      (label) => Array.from(document.querySelectorAll("button")).some(
        (button) => button.textContent?.includes(label) && !button.disabled,
      ),
      ui.importButtonText,
    );
    await page.getByRole("button", { name: ui.importImages }).click();
    await page.getByRole("status").filter({ hasText: ui.importSummary }).waitFor();
    await page.getByText(ui.importedCount).scrollIntoViewIfNeeded();
  });

  await scene(2, async () => {
    const gallery = page.getByRole("list", { name: ui.importedImages });
    await gallery.getByRole("button", { name: /SN90_C_1_000_dic\.tif/ }).click();
    const viewer = page.getByRole("dialog");
    await viewer.getByText(ui.sourceOriginal).waitFor();
    await page.waitForTimeout(3500);
    await viewer.getByRole("button", { name: ui.close }).click();
    await page.getByRole("button", { name: ui.runAnalysis }).click();
    await page.getByText(`${ui.experimentPrefix} : ${experimentName}`).waitFor({ timeout: 90_000 });
    await page.getByText(ui.connectedComponents, { exact: true }).scrollIntoViewIfNeeded();
  });

  await scene(3, async () => {
    const gallery = page.getByRole("list", { name: ui.overlays });
    await gallery.getByRole("button").first().click();
    const viewer = page.getByRole("dialog");
    await viewer.getByRole("button", { name: ui.zoomIn }).click();
    await viewer.getByRole("button", { name: ui.sideBySide }).click();
    await page.waitForTimeout(6000);
    await viewer.getByRole("button", { name: ui.close }).click();
    await page.getByText(ui.reservation).scrollIntoViewIfNeeded();

    const comparisonCreate = await context.request.post(`${baseURL}/api/v1/experiments`, {
      data: {
        name: comparisonName,
        description: language === "fr"
          ? "Répétition technique descriptive sur une source publique."
          : "Descriptive technical repeat on one public source.",
      },
    });
    if (!comparisonCreate.ok()) throw new Error(`Comparison experiment creation failed: ${comparisonCreate.status()}`);
    const comparison = await comparisonCreate.json();
    const comparisonSource = sourcePaths[2];
    const comparisonUpload = await context.request.post(`${baseURL}/api/v1/experiments/${comparison.id}/images`, {
      multipart: {
        files: {
          name: basename(comparisonSource),
          mimeType: "image/tiff",
          buffer: await readFile(comparisonSource),
        },
      },
    });
    if (!comparisonUpload.ok()) throw new Error(`Comparison image upload failed: ${comparisonUpload.status()}`);
    const comparisonAnalysis = await context.request.post(`${baseURL}/api/v1/experiments/${comparison.id}/analyze`);
    if (!comparisonAnalysis.ok()) throw new Error(`Comparison analysis failed: ${comparisonAnalysis.status()}`);
  });

  await scene(4, async () => {
    const jsonDownload = page.waitForEvent("download");
    await page.getByRole("link", { name: ui.exportJson }).click();
    await jsonDownload;
    const csvDownload = page.waitForEvent("download");
    await page.getByRole("link", { name: ui.exportCsv }).click();
    await csvDownload;
    await page.getByText(ui.evidence).scrollIntoViewIfNeeded();
    await page.reload({ waitUntil: "networkidle" });
    await page.getByLabel(ui.activeExperiment).selectOption({ label: experimentName });
    await page.getByRole("button", { name: ui.results }).click();
    await page.getByLabel(ui.secondExperiment).selectOption({ label: comparisonName });
    await page.getByText(ui.comparisonMetrics, { exact: true }).scrollIntoViewIfNeeded();
  });

  await scene(5, async () => {
    await page.getByRole("button", { name: "Benchmarks" }).click();
    await page.getByRole("heading", { name: ui.engineComparison }).waitFor();
    await page.getByText(ui.foreground).scrollIntoViewIfNeeded();
    await page.waitForTimeout(6000);
    await page.getByText(ui.instances).scrollIntoViewIfNeeded();
    await page.waitForTimeout(6000);
    await page.getByText(ui.provenance).click();
    await page.getByText(/reports\/benchmarks\/bbbc019/).first().scrollIntoViewIfNeeded();
  });

  await scene(6, async () => {
    await page.getByRole("button", { name: ui.workspace }).click();
    await page.getByRole("heading", { name: ui.engine }).scrollIntoViewIfNeeded();
    const detailButtons = page.getByRole("button", { name: ui.details });
    await detailButtons.last().click();
    await page.getByRole("dialog").waitFor();
    await page.waitForTimeout(8000);
    await page.getByRole("dialog").getByRole("button", { name: ui.close }).click();
    await page.getByRole("button", { name: ui.results }).click();
    await page.getByRole("heading", { name: ui.results }).first().scrollIntoViewIfNeeded();
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
