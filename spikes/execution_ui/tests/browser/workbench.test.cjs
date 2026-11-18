const assert = require("node:assert/strict");
const { before, after, test } = require("node:test");
const { browser, fixture } = require("./helpers.cjs");
let service, engine, page;
const errors=[];

before(async()=>{
  service=await fixture();engine=await browser();
  page=await engine.newPage({viewport:{width:1600,height:1000}});
  page.on("pageerror",error=>errors.push(error.message));
});
after(async()=>{if(engine)await engine.close();if(service)await service.close()});

test("source, examples and definition inspection do not invoke a fixture run",async()=>{
  let posts=0;page.on("request",request=>{if(request.method()==="POST")posts++});
  await page.goto(service.origin+"/");
  await page.locator("#run-button").waitFor({state:"visible"});
  await page.waitForFunction(()=>!document.getElementById("run-button").disabled);
  assert.equal(await page.locator("#fixture-warning").isVisible(),true);
  await page.locator(".catalog > summary").click();
  await page.locator("#case-select").selectOption({index:2});
  assert.equal(await page.locator("#run-badge").textContent(),"Belum ada run");
  await page.locator(".definition-summary > summary").click();
  await page.locator("#definition-button").click();
  await page.locator("#definition-details[open]").waitFor({state:"visible"});
  assert.equal(await page.locator("#definition-text").textContent(),"fixture: true\n");
  await page.goto(service.origin+"/?code=http&lesson=explain");
  await page.waitForFunction(()=>document.getElementById("code-symbol").textContent.includes("create_app.run"));
  assert.ok((await page.locator("#source-code").textContent()).includes("runtime.execute"));
  await page.locator("#code-select").selectOption("boundary");
  await page.waitForFunction(()=>document.getElementById("code-symbol").textContent.includes("local_boundary"));
  assert.equal(posts,0);
});

test("blocked result and terminal authorization failure never invent retrieval sources",async()=>{
  await page.goto(service.origin+"/");
  await page.waitForFunction(()=>!document.getElementById("run-button").disabled);
  await page.locator("#question").fill("Fixture blocked request.");
  await page.locator("#run-button").click();
  await page.waitForFunction(()=>document.getElementById("result-badge").textContent==="Blocked");
  assert.equal(await page.locator("#sources li").count(),0);
  assert.ok((await page.locator("#trace-output").textContent()).includes('"fixture": true'));
  assert.equal(await page.locator(".step.is-running").count(),0);
  await page.waitForFunction(()=>!document.getElementById("run-button").disabled);
  await page.locator("#question").fill("Fixture authorization failure.");
  await page.locator("#question").press("Control+Enter");
  await page.waitForFunction(()=>document.getElementById("result-badge").textContent==="Tidak terverifikasi");
  assert.ok((await page.locator("#result-error").textContent()).includes("tidak diizinkan"));
  assert.equal(await page.locator("#sources li").count(),0);
});

test("loopback UI supports responsive layouts and rejects missing CSRF at runtime",async()=>{
  await page.goto(service.origin+"/");
  await page.waitForFunction(()=>!document.getElementById("run-button").disabled);
  const denied=await page.evaluate(async()=>{
    const response=await fetch("/ui/runs",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({question:"Must not execute."})});
    return response.status;
  });
  assert.equal(denied,403);
  const ordered=await page.evaluate(()=>{
    const kind=context.kind;context.kind="logicapps";
    for(const [id,time] of [["later","2026-01-01T00:00:02Z"],["earlier","2026-01-01T00:00:01Z"]]){
      progress({phase:"context",status:"done",step_id:id,code_key:"workflow",label:id,
        detail:"Fixture observation order test.",native_started:time});
    }
    context.kind=kind;
    return [...document.querySelectorAll(".step-title")].map(node=>node.textContent);
  });
  assert.deepEqual(ordered,["earlier","later"]);
  for(const width of [1600,900,390]){
    await page.setViewportSize({width,height:900});
    const size=await page.evaluate(()=>({viewport:innerWidth,content:document.documentElement.scrollWidth}));
    assert.ok(size.content<=size.viewport,JSON.stringify(size));
  }
  assert.deepEqual(errors,[]);
});
