import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("has a visible keyboard focus and no detectable accessibility violation", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Inférence disponible")).toBeVisible();

  await page.keyboard.press("Tab");
  const focus = await page.evaluate(() => {
    const element = document.activeElement as HTMLElement | null;
    if (!element) return null;
    const style = window.getComputedStyle(element);
    return {
      tag: element.tagName,
      outlineStyle: style.outlineStyle,
      outlineWidth: Number.parseFloat(style.outlineWidth),
    };
  });
  expect(focus).not.toBeNull();
  expect(focus?.tag).not.toBe("BODY");
  expect(focus?.outlineStyle).not.toBe("none");
  expect(focus?.outlineWidth).toBeGreaterThanOrEqual(2);

  const audit = await new AxeBuilder({ page }).analyze();
  expect(
    audit.violations.map((violation) => ({
      id: violation.id,
      impact: violation.impact,
      targets: violation.nodes.flatMap((node) => node.target),
    })),
  ).toEqual([]);
});

for (const viewport of [
  { name: "mobile", width: 390, height: 844 },
  { name: "effective 200% zoom", width: 640, height: 720 },
]) {
  test(`keeps the primary workflow usable at ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await expect(page.getByText("Inférence disponible")).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Sections" })).toBeVisible();
    await expect(page.getByRole("button", { name: /Nouvelle expérience/ }).first()).toBeVisible();

    const horizontalOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(horizontalOverflow).toBeLessThanOrEqual(1);

    await page.getByRole("button", { name: /Nouvelle expérience/ }).first().click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByLabel("Nom de l’expérience")).toBeVisible();
    await expect(dialog.getByRole("button", { name: "Créer l’expérience" })).toBeVisible();
    await dialog.getByRole("button", { name: "Annuler" }).click();
    await expect(dialog).toBeHidden();
  });
}
