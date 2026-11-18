const assert = require("node:assert/strict");
const { test } = require("node:test");
const { withModule, chapter } = require("./training-helpers.cjs");

test("the offline course stays readable through all chapters on mobile and desktop", async () => {
  await withModule(async page => {
    const content = JSON.parse(await page.locator("#module-data").textContent());
    const ids = await page.locator("[id]").evaluateAll(elements => elements.map(element => element.id));
    assert.equal(ids.length, new Set(ids).size, "Embedded SVG IDs must not collide across diagrams.");
    for (const width of [390, 768, 1280]) {
      await page.setViewportSize({ width, height: 900 });
      for (const item of content.chapters) {
        await chapter(page, item.id);
        if (item.diagram) {
          const detail = page.locator(".chapter-panel:visible .diagram-details");
          if (!(await detail.evaluate(element => element.open))) await detail.locator("summary").click();
          const fontSizes = await page.locator(".chapter-panel:visible .diagram-svg").evaluateAll(containers =>
            containers.flatMap(container => {
              const svg = container.querySelector("svg"), matrix = svg.getScreenCTM();
              const scale = Math.hypot(matrix.a, matrix.b);
              return [...svg.querySelectorAll("foreignObject div")]
                .filter(element => element.textContent.trim() && element.children.length === 0)
                .map(element => parseFloat(getComputedStyle(element).fontSize) * scale);
            }));
          assert.ok(fontSizes.length > 0 && fontSizes.every(size => size >= 12),
            JSON.stringify({ chapter: item.id, width, fontSizes }));
        }
        const size = await page.evaluate(() => ({
          width: innerWidth, scroll: document.documentElement.scrollWidth
        }));
        assert.ok(size.scroll <= size.width, JSON.stringify({ chapter: item.id, ...size }));
      }
      await chapter(page, "journey");
      const labels = await page.locator(".node-button .node-label").evaluateAll(elements =>
        elements.map(element => parseFloat(getComputedStyle(element).fontSize)));
      assert.ok(labels.every(size => size >= 12));
    }
    const storage = await page.evaluate(() => ({
      local: localStorage.length, session: sessionStorage.length
    }));
    assert.deepEqual(storage, { local: 0, session: 0 });
  });
});

test("deep links, keyboard focus, presentation and print retain the teaching context", async () => {
  await withModule(async page => {
    assert.equal(await page.locator("#path-label").textContent(), "MAF dengan kode");
    assert.match(await page.locator("#step-process").textContent(), /WorkflowBuilder/u);
    const node = page.locator('.node-button[data-node="router"]');
    await node.focus();
    await page.keyboard.press("Enter");
    assert.match(await page.locator("#node-title").textContent(), /Router/u);
    await page.locator('[data-mode="present"]').click();
    assert.equal(await page.locator("#present-banner").isVisible(), true);
    await page.keyboard.press("Escape");
    assert.equal(await page.locator("#present-banner").isVisible(), false);
    await page.emulateMedia({ media: "print" });
    assert.equal(await page.locator(".chapter-panel:visible").count(), 10);
    assert.equal(await page.locator("#cost-assumptions").isVisible(), true);
  }, { width: 1280, height: 900 }, "#chapter=code&path=code&node=orchestrator");
});

test("editable diagrams are embedded downloads, not remote assets or fake portal captures", async () => {
  await withModule(async page => {
    await chapter(page, "yaml");
    await page.locator(".diagram-details").filter({ has: page.locator('[data-diagram="maf-yaml"]') }).locator("summary").click();
    const download = page.locator('a.diagram-download[data-diagram="maf-yaml"][data-format="drawio"]');
    assert.match(await download.getAttribute("href"), /^data:application\/xml;base64,/u);
    assert.match(await download.getAttribute("download"), /\.drawio$/u);
    assert.match(await page.locator('[data-diagram-caption="maf-yaml"]').textContent(), /ilustrasi|Ilustrasi/u);
  });
});
