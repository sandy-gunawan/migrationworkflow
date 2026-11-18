const assert = require("node:assert/strict");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { browser, ROOT } = require("./helpers.cjs");

const modulePath = path.join(ROOT, "docs", "training", "workflow-migration-overview.html");

async function withModule(run, viewport = { width: 1280, height: 900 }, hash = "") {
  const engine = await browser();
  const page = await engine.newPage({ viewport });
  const errors = [], outbound = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("request", request => {
    if (/^https?:/u.test(request.url())) outbound.push(request.url());
  });
  try {
    await page.goto(pathToFileURL(modulePath).href + hash);
    await page.waitForFunction(() => document.body.dataset.ready === "true");
    await run(page);
    assert.deepEqual(errors, [], "The teaching page raised JavaScript errors.");
    assert.deepEqual(outbound, [], "The teaching page made automatic network requests.");
  } finally {
    await engine.close();
  }
}

async function chapter(page, id) {
  const menu = page.locator("#chapter-menu");
  if (!(await menu.evaluate(element => element.open))) await menu.locator("summary").first().click();
  await page.locator(`button.chapter-button[data-chapter="${id}"]`).click();
}

module.exports = { withModule, chapter };
