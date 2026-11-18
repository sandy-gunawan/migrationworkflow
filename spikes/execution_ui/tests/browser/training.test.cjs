const assert = require("node:assert/strict");
const { test } = require("node:test");
const { withModule, chapter } = require("./training-helpers.cjs");

test("the first screen makes YAML-versus-code editing ownership explicit", async () => {
  await withModule(async page => {
    const yaml = page.locator('#file-change-comparison [data-choice="yaml"]');
    const code = page.locator('#file-change-comparison [data-choice="code"]');
    const logic = page.locator('#file-change-comparison [data-choice="logicapps"]');
    assert.match(await yaml.locator(".edit-target").textContent(), /YAML/u);
    assert.match(await code.locator(".edit-target").textContent(), /Python/u);
    assert.match(await logic.locator(".edit-target").textContent(), /Logic Apps/u);
    assert.match(await yaml.textContent(), /sama.*export|export.*sama/iu);
    assert.match(await yaml.textContent(), /kondisi.*YAML|YAML.*kondisi/iu);
    assert.match(await code.textContent(), /YAML saja tidak mengubah/iu);
    assert.match(await page.locator("#yaml-sync-note").textContent(), /tidak otomatis/iu);
    for (const card of [yaml, code, logic]) {
      const bounds = await card.locator(".edit-target").boundingBox();
      assert.ok(bounds && bounds.y >= 0 && bounds.y + bounds.height <= 900,
        "The editable artifact must be visible without navigating or scrolling.");
    }
  });
});

test("one solution architecture locates local Python, App Service, Foundry and data", async () => {
  await withModule(async page => {
    const architecture = page.locator("#solution-architecture");
    await architecture.scrollIntoViewIfNeeded();
    assert.equal(await architecture.locator(".diagram-svg > svg").count(), 1);
    const diagram = await architecture.locator(".diagram-svg").textContent();
    for (const location of [/Komputer pengguna/u, /Python \+ MAF/u, /Azure App Service/u,
      /Foundry project/u, /Router agent/u, /Specialist/u, /Fabric/u]) {
      assert.match(diagram, location);
    }
    assert.match(await architecture.textContent(), /alternatif penempatan/u);
    assert.match(await architecture.textContent(), /bukan dua server/u);
    assert.match(await architecture.textContent(), /tidak diklaim otomatis sudah selesai/u);
  });
});

test("the mobile workshop opens focused lessons without repeating the overview", async () => {
  await withModule(async page => {
    const menu = page.locator("#chapter-menu");
    assert.equal(await menu.evaluate(element => element.open), false);
    assert.equal(await page.locator("#overview-shell").isVisible(), true);
    const entry = page.locator('[data-open-chapter="yaml"]');
    const bounds = await entry.boundingBox();
    assert.ok(bounds && bounds.height >= 44, "Lesson entry must have a usable touch target.");
    await page.locator('[data-choice="yaml"] .choice-details summary').click();
    const sizes = await page.locator('[data-choice="yaml"] p').evaluateAll(elements =>
      elements.map(element => parseFloat(getComputedStyle(element).fontSize)));
    assert.ok(sizes.length > 0 && sizes.every(size => size >= 16),
      "Expanded teaching text must remain readable on mobile.");
    await entry.click();
    assert.match(page.url(), /chapter=yaml/u);
    assert.equal(await page.locator("#overview-shell").isVisible(), false);
    assert.equal(await page.locator("#current-chapter-title").evaluate(element =>
      element === document.activeElement), true);
    await chapter(page, "code");
    assert.equal(await menu.evaluate(element => element.open), false);
    assert.match(await page.locator("#current-chapter-title").textContent(), /kode/u);
    await chapter(page, "start");
    assert.equal(await page.locator("#overview-shell").isVisible(), true);
    await page.setViewportSize({ width: 1280, height: 900 });
    assert.equal(await menu.evaluate(element => element.open), true);
    assert.equal(await page.locator('button.chapter-button[data-chapter="code"]').isVisible(), true);
  }, { width: 390, height: 900 });
});

test("training separates YAML startup, code-first runtime and native Logic Apps ownership", async () => {
  await withModule(async page => {
    await chapter(page, "yaml");
    assert.equal(await page.locator("#path-label").textContent(), "MAF dengan YAML");
    await page.locator('button[data-phase="prepare"]').click();
    assert.match(await page.locator("#preparation-steps").textContent(), /YAML/u);
    assert.match(await page.locator("#lifecycle-note").textContent(), /startup|mulai/u);
    await page.locator('button[data-phase="runtime"]').click();
    await page.locator('.node-button[data-node="orchestrator"]').click();
    assert.match(await page.locator("#step-process").textContent(), /WorkflowFactory/u);
    assert.match(await page.locator("#step-process").textContent(), /baru/u);
    await chapter(page, "code");
    await page.locator('.node-button[data-node="orchestrator"]').click();
    assert.match(await page.locator("#step-process").textContent(), /WorkflowBuilder/u);
    assert.match(await page.locator("#lifecycle-note").textContent(), /referensi/u);
    await chapter(page, "logicapps");
    await page.locator('.node-button[data-node="orchestrator"]').click();
    assert.match(await page.locator("#step-process").textContent(), /Logic Apps/u);
    assert.match(await page.locator("#step-process").textContent(), /gateway/u);
    await page.locator("#scenario-select").selectOption("blocked");
    assert.equal(await page.locator("#flow-result").getAttribute("data-status"), "blocked");
    assert.equal(await page.locator("#flow-result").getAttribute("data-sources"), "0");
    assert.equal(await page.locator('.node-button[data-node="specialist"]').getAttribute("data-state"), "skipped");
    await page.locator("#scenario-select").selectOption("success");
    await page.locator('.node-button[data-node="result"]').click();
    assert.match(await page.locator("#step-output").textContent(), /WO001/u);
    assert.equal(await page.locator("#flow-result").getAttribute("data-status"), "success");
    assert.match(await page.locator("#simulation-note").textContent(), /tidak memanggil Azure/u);
    await page.locator('#path-options button[data-path="yaml"]').click();
    assert.equal(await page.locator("#path-label").textContent(), "MAF dengan YAML");
    await page.locator("#scenario-select").selectOption("clarification");
    assert.equal(await page.locator("#flow-result").getAttribute("data-sources"), "0");
    await page.locator("#scenario-select").selectOption("denied");
    assert.equal(await page.locator('.node-button[data-node="router"]').getAttribute("data-state"), "skipped");
  });
});

test("training links glossary and changed layers to a transparent path choice", async () => {
  await withModule(async page => {
    await chapter(page, "basics");
    const term = page.locator('.chapter-panel[data-chapter="basics"] .term-button[data-term="workflow"]').first();
    await term.click();
    assert.equal(await page.locator("#glossary-dialog").isVisible(), true);
    assert.match(await page.locator("#glossary-body").textContent(), /urutan/iu);
    await page.keyboard.press("Escape");
    assert.equal(await page.locator("#glossary-dialog").isVisible(), false);
    assert.equal(await term.evaluate(element => element === document.activeElement), true);
    await chapter(page, "choices");
    await page.locator("#decision-visual").selectOption("yes");
    assert.match(await page.locator("#decision-title").textContent(), /Logic Apps/u);
    await page.locator("#decision-visual").selectOption("no");
    await page.locator("#decision-custom").selectOption("yes");
    assert.match(await page.locator("#decision-title").textContent(), /code-first/u);
    await page.locator("#decision-custom").selectOption("no");
    await page.locator("#decision-yaml").selectOption("yes");
    assert.match(await page.locator("#decision-title").textContent(), /YAML/u);
    assert.match(await page.locator("#decision-note").textContent(), /bukan.*penilaian/u);
    await chapter(page, "ui");
    await page.locator("#change-select").selectOption("identity");
    assert.match(await page.locator("#change-detail").textContent(), /izin|identitas/u);
    await chapter(page, "migration");
    assert.match(await page.locator("#evidence-summary").textContent(), /baseline/iu);
    assert.match(await page.locator("#evidence-summary").textContent(), /dua request smoke|2 request/iu);
    const data = JSON.parse(await page.locator("#module-data").textContent());
    for (const [index, question] of data.quiz.entries()) {
      const wrong = (question.correct + 1) % question.choices.length;
      await page.locator(`.quiz-button[data-quiz="${index}"][data-choice="${wrong}"]`).click();
      assert.match(await page.locator(`#quiz-feedback-${index}`).textContent(), /^Belum tepat/u);
      await page.locator(`.quiz-button[data-quiz="${index}"][data-choice="${question.correct}"]`).click();
      assert.match(await page.locator(`#quiz-feedback-${index}`).textContent(), /^Tepat/u);
    }
  });
});
