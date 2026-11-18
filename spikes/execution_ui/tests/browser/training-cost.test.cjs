const assert = require("node:assert/strict");
const { test } = require("node:test");
const { withModule, chapter } = require("./training-helpers.cjs");

const row = (page, path) => page.locator(`.cost-result-row[data-cost-path="${path}"]`);
const value = async (page, path) => Number(await row(page, path).getAttribute("data-value"));

test("cost compares the same model usage fairly and does not invent a YAML SDK fee", async () => {
  await withModule(async page => {
    await chapter(page, "cost");
    await page.locator("#cost-example").click();
    assert.equal(await row(page, "yaml").getAttribute("data-state"), "complete");
    assert.equal(await value(page, "yaml"), 31.4);
    assert.equal(await value(page, "code"), 31.4);
    assert.equal(await value(page, "foundry"), 11.4);
    assert.equal(await value(page, "logicapps"), 11.7);
    await page.locator('#cost-form [name="requests"]').fill("2000");
    assert.equal(await value(page, "yaml"), 32.8);
    assert.equal(await value(page, "code"), 32.8);
    assert.equal(await value(page, "logicapps"), 13.4);
    await page.locator('#cost-form [name="requests"]').fill("0");
    assert.equal(await value(page, "yaml"), 30);
    assert.equal(await value(page, "logicapps"), 10);
    assert.match(await page.locator("#cost-assumptions").textContent(), /contoh|ilustrasi/u);
  });
});

test("cost preserves unknown prices and explicitly rejects invalid or overflowing inputs", async () => {
  await withModule(async page => {
    await chapter(page, "cost");
    assert.equal(await row(page, "yaml").getAttribute("data-state"), "partial");
    assert.equal(await row(page, "yaml").getAttribute("data-value"), null);
    await page.locator("#cost-example").click();
    await page.locator('#cost-form [name="mafHost"]').fill("");
    assert.equal(await row(page, "yaml").getAttribute("data-state"), "partial");
    assert.match(await row(page, "yaml").textContent(), /belum diketahui/u);
    await page.locator('#cost-form [name="requests"]').fill("-1");
    assert.equal(await page.locator("#cost-error").isVisible(), true);
    assert.equal(await row(page, "yaml").getAttribute("data-state"), "invalid");
    await page.locator('#cost-form [name="requests"]').fill("1e309");
    assert.equal(await page.locator("#cost-error").isVisible(), true);
    assert.doesNotMatch(await page.locator("#cost-results").textContent(), /NaN|Infinity/u);
    await page.locator('#cost-form [name="requests"]').fill("1000");
    assert.equal(await row(page, "yaml").getAttribute("data-state"), "partial");
    await page.locator('#cost-form [name="mafHost"]').fill("20");
    assert.equal(await row(page, "yaml").getAttribute("data-state"), "complete");
  });
});

test("Standard hosting is an explicit rate assumption while model costs remain", async () => {
  await withModule(async page => {
    await chapter(page, "cost");
    await page.locator("#cost-example").click();
    await page.locator('#cost-form [name="logicPlan"]').selectOption("standard");
    assert.equal(await row(page, "logicapps").getAttribute("data-state"), "partial");
    await page.locator('#cost-form [name="logicHost"]').fill("100");
    await page.locator('#cost-form [name="standardStorage"]').fill("0");
    assert.equal(await value(page, "logicapps"), 111.4);
    assert.equal(await value(page, "yaml"), 31.4);
    assert.match(await page.locator("#logic-billing-note").textContent(), /managed|calls/u);
    await page.locator('#cost-form [name="logicPlan"]').selectOption("consumption");
    assert.equal(await value(page, "logicapps"), 11.7);
  });
});
