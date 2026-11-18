import {mkdir, readFile, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';

const here = path.dirname(fileURLToPath(import.meta.url));
const definitions = {
  maf: {port: 8765, service: 'local-maf-ui', title: 'MAF code-first'},
  logicapps: {port: 8766, service: 'local-logicapps-ui', title: 'Logic Apps native'},
  declarative: {port: 8767, service: 'local-maf-declarative-ui', title: 'MAF declarative YAML'},
};
const kind = process.argv[2];
if (!(kind in definitions) || !process.argv.includes('--allow-live')) {
  throw new Error('Choose maf/logicapps/declarative and explicitly pass --allow-live.');
}
const definition = definitions[kind];
const raw = path.join(here, 'raw', kind);
await mkdir(raw, {recursive: true});
const receipt = path.join(raw, 'capture.local.json');
try {
  await readFile(receipt);
  throw new Error('A capture receipt already exists. Review it before authorizing another live run.');
} catch (error) {
  if (error.code !== 'ENOENT') throw error;
}
const origin = `http://127.0.0.1:${definition.port}`;
const health = await fetch(`${origin}/health`).then((response) => response.json());
if (health.service !== definition.service || health.status !== 'ready') {
  throw new Error('The local server is not the expected ready demo UI.');
}

const browser = await chromium.launch({
  channel: 'msedge',
  headless: true,
  args: ['--disable-background-networking'],
});
const context = await browser.newContext({
  viewport: {width: 1600, height: 900},
  deviceScaleFactor: 1,
  recordVideo: {dir: raw, size: {width: 1600, height: 900}},
});
const page = await context.newPage();
const video = page.video();
const started = performance.now();
const marks = {};
const mark = (name) => {
  marks[name] = (performance.now() - started) / 1000;
  console.log(`${kind}: ${name} at ${marks[name].toFixed(2)}s`);
};
let submissions = 0;
const errors = [];
page.on('pageerror', (error) => errors.push(error.message));
await page.route('**/*', (route) => {
  const url = new URL(route.request().url());
  if (route.request().method() === 'POST' && url.pathname === '/ui/runs') {
    submissions += 1;
    if (submissions > 1) return route.abort('blockedbyclient');
  }
  return url.origin === origin || url.protocol === 'data:'
    ? route.continue()
    : route.abort('blockedbyclient');
});

try {
  await page.goto(origin, {waitUntil: 'networkidle'});
  await page.locator('#run-button').waitFor({state: 'visible'});
  await page.waitForFunction(() => !document.querySelector('#run-button').disabled);
  const uiContext = await page.request.get(`${origin}/ui/context`).then((response) => response.json());
  if (uiContext.busy || uiContext.identity_mode === 'unit_fixture') {
    throw new Error('The UI is busy or configured as a contract fixture, not a live capture.');
  }
  mark('overview');
  await page.waitForTimeout(6000);
  if (kind === 'declarative') {
    mark('definition');
    await page.locator('.definition-summary > summary').click();
    await page.locator('#definition-button').click();
    await page.locator('#definition-details').scrollIntoViewIfNeeded();
    await page.waitForTimeout(7000);
    await page.locator('#question').scrollIntoViewIfNeeded();
    await page.waitForTimeout(1000);
  }
  mark('question');
  await page.locator('#question').click();
  await page.locator('#question').fill('');
  await page.locator('#question').pressSequentially(
    'Show work orders for equipment TRK001.', {delay: 65},
  );
  await page.waitForTimeout(5000);
  await writeFile(receipt, JSON.stringify({
    kind, status: 'authorized_submission_pending', captured_at: new Date().toISOString(),
    question: 'Show work orders for equipment TRK001.',
  }, null, 2));
  const completedResponse = page.waitForResponse(
    (response) => response.request().method() === 'POST' &&
      new URL(response.url()).pathname === '/ui/runs',
    {timeout: 420000},
  ).then(async (response) => {
    const body = await response.text();
    const events = body.trim().split('\n').filter(Boolean).map((line) => JSON.parse(line));
    const final = events.findLast((event) => event.type === 'result');
    if (!response.ok() || !final) {
      const failure = events.findLast((event) => event.type === 'error');
      throw new Error(`The live UI returned no result: ${failure?.message || response.status()}`);
    }
    return final.output;
  });
  mark('submitted');
  await page.locator('#run-button').click();
  const output = await completedResponse;
  const result = output.result;
  if (submissions !== 1 || result.route !== 'mcp' || result.status !== 'success' ||
      !result.answer.includes('WO001') || !result.answer.includes('TRK001') ||
      !result.sources.some((source) => source.id === 'urn:kppdemo:maintenance/TRK001')) {
    throw new Error('The captured live result does not prove the expected MCP01 facts and source.');
  }
  await page.waitForFunction(() => document.querySelector('#result-badge').textContent.includes('sukses'));
  mark('completed');
  await page.waitForTimeout(5000);
  await page.locator('#result-title').scrollIntoViewIfNeeded();
  mark('answer');
  await page.waitForTimeout(12000);
  const tools = page.locator('#steps .step-button').filter({hasText: 'get_work_orders'});
  const specialists = page.locator('#steps .step-button').filter({hasText: 'kppdemo-mcp'});
  const inspection = await tools.count() ? tools.first() : specialists.last();
  await inspection.scrollIntoViewIfNeeded();
  await inspection.click();
  await page.locator('#code-title').scrollIntoViewIfNeeded();
  mark('inspector');
  await page.waitForTimeout(12000);
  if (kind !== 'maf') {
    const select = page.locator('#code-select');
    const options = await select.locator('option').evaluateAll((nodes) =>
      nodes.map((node) => ({value: node.value, text: node.textContent})));
    const matching = options.find((option) =>
      kind === 'declarative' ? /yaml/i.test(option.text) : /json/i.test(option.text));
    if (matching) {
      await select.selectOption(matching.value);
      mark('nativeSource');
      await page.waitForTimeout(10000);
    }
  }
  await page.locator('#trace-details').scrollIntoViewIfNeeded();
  await page.locator('#trace-details > summary').click();
  await page.locator('#trace-output').scrollIntoViewIfNeeded();
  mark('trace');
  await page.waitForTimeout(10000);
  await page.locator('#result-title').scrollIntoViewIfNeeded();
  mark('closing');
  await page.waitForTimeout(7000);
  if (errors.length) throw new Error(`Browser errors: ${errors.join('; ')}`);
  mark('end');
  await context.close();
  const videoPath = await video.path();
  await writeFile(receipt, JSON.stringify({
    kind, title: definition.title, status: 'success',
    captured_at: new Date().toISOString(), viewport: {width: 1600, height: 900},
    video: path.relative(here, videoPath), marks, submissions, browser_errors: errors,
    result: {
      run_id: result.run_id, route: result.route, status: result.status,
      answer: result.answer, sources: result.sources,
    },
  }, null, 2));
  console.log(`${kind}: verified MCP01 live capture saved.`);
} finally {
  await context.close();
  await browser.close();
}
