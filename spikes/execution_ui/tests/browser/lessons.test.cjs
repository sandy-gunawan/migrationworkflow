const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const { pathToFileURL } = require("node:url");
const { browser, targets, guide } = require("./helpers.cjs");

for(const kind of targets())test(kind+" HTML teaches preparation, source mapping and quizzes offline",async()=>{
  const engine=await browser(),page=await engine.newPage({viewport:{width:1500,height:1000}});
  const errors=[],outbound=[];
  page.on("pageerror",error=>errors.push(error.message));
  page.on("request",request=>{if(/^https?:/.test(request.url()))outbound.push(request.url())});
  try{
    await page.goto(pathToFileURL(guide(kind)).href);
    const data=JSON.parse(await page.locator("#lesson-data").textContent());
    await page.locator("#tab-source").click();
    for(const step of data.steps){
      await page.locator(`[data-step="${step.id}"]`).click();
      assert.equal(await page.locator("#step-title").textContent(),step.title);
      assert.equal(await page.locator("#code-select").inputValue(),step.source_key);
      assert.ok((await page.locator("#code-text").textContent()).includes(data.sources[step.source_key].text.trim().split("\n")[0].trim()));
    }
    const owned=Object.entries(data.owners).find(([,owner])=>owner);
    await page.locator(`.definition-line[data-line="${owned[0]}"]`).click();
    assert.ok(await page.locator(".definition-line.selected").count()>0);
    await page.locator("#tab-practice").click();
    for(let index=0;index<data.quiz.length;index++){
      const question=data.quiz[index],wrong=(question.correct+1)%question.choices.length;
      await page.locator(`button[data-quiz="${index}"][data-choice="${wrong}"]`).click();
      assert.ok((await page.locator(`p[data-quiz="${index}"]`).textContent()).startsWith("Belum tepat."));
      await page.locator(`button[data-quiz="${index}"][data-choice="${question.correct}"]`).click();
      assert.ok((await page.locator(`p[data-quiz="${index}"]`).textContent()).startsWith("Tepat."));
    }
    for(const width of [1500,900,390]){
      await page.setViewportSize({width,height:900});
      for(const name of ["story","start","source","practice","proof"]){
        await page.locator("#tab-"+name).click();
        const size=await page.evaluate(()=>({viewport:innerWidth,content:document.documentElement.scrollWidth}));
        assert.ok(size.content<=size.viewport,JSON.stringify({kind,name,...size}));
      }
    }
    assert.deepEqual(errors,[]);assert.deepEqual(outbound,[]);
  }finally{await engine.close()}
});

test("Logic Apps lightweight guide keeps native assets and its UI path offline",async()=>{
  const engine=await browser(),page=await engine.newPage({viewport:{width:1280,height:960}});
  const errors=[],outbound=[];
  page.on("pageerror",error=>errors.push(error.message));
  page.on("console",message=>{if(message.type()==="error")errors.push(message.text())});
  page.on("request",request=>{if(/^https?:/.test(request.url()))outbound.push(request.url())});
  try{
    const target=path.join(path.dirname(guide("logicapps")),"logicapps-alur-request.html");
    for(const filename of ["logicapps-alur-request.html","logicapps-node-walkthrough.html"]){
      const file=path.join(path.dirname(target),filename),html=fs.readFileSync(file,"utf8");
      assert.ok(fs.statSync(file).size<1024*1024,"HTML must stay below 1 MiB: "+filename);
      assert.ok(!html.includes("data:image/png;base64,"),"PNG data must remain outside HTML.");
      assert.ok(!html.includes("logicapps-20261117/"),"User-provided captures must not be referenced.");
      assert.ok(!html.includes("portal-gallery-data"),"The old embedded gallery must not be packaged.");
    }
    await page.goto(pathToFileURL(target).href);
    await page.waitForFunction(()=>document.querySelector("[data-overview-image]").getAttribute("src"));
    assert.equal(await page.locator("#guide-error").isVisible(),false);
    const storyData=JSON.parse(await page.locator("#logic-data").textContent());
    assert.deepEqual(storyData.screenshots,[]);
    const nativeOverview=page.locator("[data-overview-image]").first();
    await nativeOverview.evaluate(image=>image.decode());
    assert.equal(await nativeOverview.getAttribute("src"),storyData.capture_overview.image);
    assert.equal(await nativeOverview.evaluate(image=>image.naturalWidth),storyData.capture_overview.width);
    assert.ok((await page.locator('[data-node-shot="Initialize_result"]').textContent()).includes("belum tersedia"));
    assert.equal(await page.locator("[data-node-shot] button").count(),0);
    const example=async name=>JSON.parse(await page.locator(`[data-example="${name}"]`).textContent());
    const first=await example("initialVariables"),last=await example("finalVariables");
    assert.equal(first.Result.status,"failed");
    assert.equal(last.Result.status,"success");
    assert.deepEqual((await example("logicResponse")).body,last.Result);
    assert.deepEqual((await example("uiFrame")).output.result,last.Result);
    assert.equal((await example("toolOutput")).data[0].order_id,"WO001");
    const config=JSON.parse(await page.locator('[data-node-config="set_result_mcp"]').textContent());
    assert.equal(config.inputs.name,"Result");
    assert.equal(config.inputs.value,"@body('normalize_mcp')");
    const range=page.locator('#router-replay input[type="range"]');
    const end=Number(await range.inputValue());
    await page.getByRole("button",{name:"Sebelumnya",exact:true}).click();
    assert.equal(Number(await range.inputValue()),end-1);
    await page.getByRole("button",{name:"Berikutnya",exact:true}).click();
    assert.equal(Number(await range.inputValue()),end);
    const escaped=await page.locator("#router-replay").evaluate(figure=>
      [...figure.querySelectorAll("g.ve-n")].flatMap(node=>{
        const shape=node.querySelector("rect.sh");
        if(!shape)throw new Error("A flow node has no measurable box.");
        const box=shape.getBBox();
        return [...node.querySelectorAll("text")].filter(text=>{
          const value=text.getBBox();
          return value.x<box.x-1||value.x+value.width>box.x+box.width+1;
        }).map(text=>text.textContent);
      }));
    assert.deepEqual(escaped,[]);
    await page.locator("[data-overview-open]").click();
    const overviewDialog=page.locator(".capture-overview-dialog");
    assert.equal(await overviewDialog.isVisible(),true);
    await overviewDialog.locator("select").selectOption("2");
    assert.equal(await overviewDialog.locator("img").evaluate(image=>parseFloat(image.style.width)),storyData.capture_overview.width*2);
    await page.keyboard.press("Escape");
    assert.equal(await overviewDialog.isVisible(),false);
    await page.emulateMedia({reducedMotion:"reduce"});
    for(const width of [1280,800,390]){
      await page.setViewportSize({width,height:900});
      const size=await page.evaluate(()=>({viewport:innerWidth,content:document.documentElement.scrollWidth}));
      assert.ok(size.content<=size.viewport,JSON.stringify(size));
    }
    await page.locator('[data-node-link="set_result_mcp"]').first().click();
    await page.waitForURL(/node=set_result_mcp/);
    assert.equal(await page.locator("#node-select").inputValue(),"set_result_mcp");
    assert.ok((await page.locator("#node-parameters").textContent()).includes("@body('normalize_mcp')"));
    assert.equal(await page.locator('[role="tab"]').count(),0);
    await page.locator("#overview-details summary").click();
    await page.locator("[data-overview-image]").evaluate(image=>image.decode());
    await page.locator("[data-overview-open]").click();
    assert.equal(await page.locator(".capture-overview-dialog").isVisible(),true);
    await page.keyboard.press("Escape");
    for(const width of [1280,390]){
      await page.setViewportSize({width,height:900});
      const size=await page.evaluate(()=>({viewport:innerWidth,content:document.documentElement.scrollWidth}));
      assert.ok(size.content<=size.viewport,JSON.stringify(size));
    }
    assert.deepEqual(errors,[]);assert.deepEqual(outbound,[]);
  }finally{await engine.close()}
});

test("Logic Apps concise node reference exposes the full URL and parameters without tabs",async()=>{
  const engine=await browser(),page=await engine.newPage({viewport:{width:1280,height:960}});
  const errors=[],outbound=[];
  page.on("pageerror",error=>errors.push(error.message));
  page.on("request",request=>{if(/^https?:/.test(request.url()))outbound.push(request.url())});
  try{
    const target=path.join(path.dirname(guide("logicapps")),"logicapps-node-walkthrough.html");
    const manifest=JSON.parse(fs.readFileSync(path.resolve(path.dirname(target),"..","..","config","logicapps-manifest.json"),"utf8"));
    await page.goto(pathToFileURL(target).href);
    assert.equal(await page.locator("#node-select").inputValue(),"kpp_mining_start");
    assert.equal(await page.locator("#node-url").textContent(),manifest.callback_url);
    assert.equal(await page.locator("#node-method").textContent(),"POST");
    assert.equal(await page.locator('[role="tab"]').count(),0);
    assert.equal(await page.locator("#node-json-details").evaluate(node=>node.open),false);
    assert.equal(await page.locator("#overview-details").evaluate(node=>node.open),false);
    const requestRows=await page.locator("#node-parameters").textContent();
    assert.ok(requestRows.includes("api-version (URL)")&&requestRows.includes(new URL(manifest.callback_url).searchParams.get("api-version")));
    assert.ok(requestRows.includes("question")&&requestRows.includes("1-4000"));
    assert.ok(requestRows.includes("run_id")&&requestRows.includes("opsional"));
    assert.deepEqual(JSON.parse(await page.locator("#node-output pre").textContent()),JSON.parse(await page.locator("#node-input pre").textContent()));
    for(const id of ["node-purpose","node-url","parameters-title","input-title","output-title"]){
      assert.equal(await page.locator("#"+id).isVisible(),true);
    }
    const output=await page.locator("#output-title").boundingBox();
    assert.ok(output.y+output.height<960,"Default node output heading must fit the desktop viewport: "+JSON.stringify(output));
    await page.locator("#node-select").selectOption("Validate_request");
    await page.locator("#node-next").focus();
    await page.keyboard.press("Enter");
    assert.equal(await page.locator("#node-select").inputValue(),"capture_question");
    await page.locator("#node-prev").click();
    assert.equal(await page.locator("#node-select").inputValue(),"Validate_request");
    await page.locator("#node-select").selectOption("classify_question");
    assert.ok((await page.locator("#node-url").textContent()).endsWith("/openai/v1/responses"));
    assert.ok((await page.locator("#node-parameters").textContent()).includes("kppdemo-router:1"));
    const input=JSON.parse(await page.locator("#node-input pre").textContent());
    assert.equal(input.input,"Show work orders for equipment TRK001.");
    assert.equal(input.conversation,"conv_contoh");
    assert.ok((await page.locator("#node-why").textContent()).includes("MCP"));
    await page.locator("#node-select").selectOption("set_result_mcp");
    assert.ok((await page.locator("#node-url").textContent()).includes("Tidak memakai URL"));
    assert.equal(await page.locator("#method-row").isVisible(),false);
    assert.ok((await page.locator("#node-parameters").textContent()).includes("@body('normalize_mcp')"));
    for(const width of [1280,800,390]){
      await page.setViewportSize({width,height:900});
      await page.locator("#node-select").selectOption("kpp_mining_start");
      const size=await page.evaluate(()=>({
        viewport:innerWidth,content:document.documentElement.scrollWidth,
        url:document.getElementById("node-url").scrollWidth,
        urlBox:document.getElementById("node-url").clientWidth
      }));
      assert.ok(size.content<=size.viewport,JSON.stringify(size));
      assert.ok(size.url<=size.urlBox+1,JSON.stringify(size));
      assert.equal(await page.locator("#node-url").textContent(),manifest.callback_url);
    }
    assert.deepEqual(errors,[]);assert.deepEqual(outbound,[]);
  }finally{await engine.close()}
});

test("Logic Apps info icons open interactive same-page popups without navigating",async()=>{
  const engine=await browser(),context=await engine.newContext({viewport:{width:1280,height:960}});
  const errors=[],outbound=[];
  context.on("page",page=>{
    page.on("pageerror",error=>errors.push(error.message));
    page.on("console",message=>{if(message.type()==="error")errors.push(message.text())});
  });
  context.on("request",request=>{if(/^https?:/.test(request.url()))outbound.push(request.url())});
  const page=await context.newPage();
  try{
    const target=path.join(path.dirname(guide("logicapps")),"logicapps-node-walkthrough.html");
    await page.goto(pathToFileURL(target).href+"#node=classify_question");
    const original=page.url(),icon=page.locator('#node-parameters button[data-help-topic="authentication-foundry"]');
    assert.equal(await icon.getAttribute("aria-haspopup"),"dialog");
    assert.equal(await icon.getAttribute("href"),null);
    await icon.focus();
    await page.keyboard.press("Enter");
    const help=page.locator("#node-help");
    assert.equal(await help.isVisible(),true);
    assert.equal(context.pages().length,1);
    assert.equal(page.url(),original);
    assert.equal(await page.locator("#node-select").inputValue(),"classify_question");
    const setup=await help.locator("#authentication-foundry").textContent();
    assert.ok(setup.includes("Foundry User")&&setup.includes("scope project"));
    assert.ok(setup.includes("tidak otomatis memberi izin"));
    assert.ok(setup.includes("kppdemo-mining-48254cc6"));
    await help.locator('[data-auth-step="iam"]').click();
    assert.equal(await help.locator('[data-auth-panel="iam"]').isVisible(),true);
    assert.equal(await help.locator('[data-auth-panel="identity"]').isVisible(),false);
    await help.locator('[data-auth-step="runtime"]').click();
    assert.ok((await help.locator('[data-auth-panel="runtime"]').textContent()).includes("https://ai.azure.com"));
    await page.keyboard.press("Tab");
    assert.equal(await help.evaluate(element=>element.contains(document.activeElement)),true);
    await page.keyboard.press("Escape");
    assert.equal(await help.isVisible(),false);
    assert.equal(await icon.evaluate(element=>document.activeElement===element),true);
    assert.equal(page.url(),original);
    await page.locator('#node-url-help button[data-help-topic="foundry-endpoint"]').click();
    await help.locator('[data-agent-example="specialist"]').click();
    const specialist=JSON.parse(await help.locator("#agent-request-example").textContent());
    assert.equal(specialist.agent_reference.name,"kppdemo-mcp");
    await help.locator('[data-agent-example="router"]').click();
    assert.equal(JSON.parse(await help.locator("#agent-request-example").textContent()).agent_reference.name,"kppdemo-router");
    await page.locator("#help-close").click();
    const reference=JSON.parse(await page.locator("#logic-data").textContent());
    for(const node of reference.nodes){
      for(const row of node.parameters.filter(parameter=>parameter.help)){
        assert.equal(await help.locator("#"+row.help).count(),1);
      }
    }
    for(const width of [1280,800,390]){
      await page.setViewportSize({width,height:900});
      await icon.click();
      const size=await help.evaluate(element=>({
        viewport:innerWidth,width:element.getBoundingClientRect().width,
        content:document.getElementById("help-content").scrollWidth,
        bodyWidth:document.getElementById("help-content").clientWidth
      }));
      assert.ok(size.width<=size.viewport&&size.content<=size.bodyWidth+1,JSON.stringify(size));
      await page.keyboard.press("Escape");
      const frame=await page.evaluate(()=>({viewport:innerWidth,content:document.documentElement.scrollWidth}));
      assert.ok(frame.content<=frame.viewport,JSON.stringify(frame));
    }
    await page.locator('[data-flow-node="invoke_mcp"]').click();
    assert.equal(await page.locator("#node-select").inputValue(),"invoke_mcp");
    assert.equal(await page.locator('[data-flow-node="invoke_mcp"]').getAttribute("aria-current"),"step");
    await page.locator("#node-select").selectOption("Initialize_result");
    await page.locator('#node-parameters button[data-help-topic="workflow-values"]').first().click();
    await help.locator('[data-variable-state="final"]').click();
    assert.equal(JSON.parse(await help.locator("#variable-state-example").textContent()).Result.status,"success");
    await help.locator('[data-variable-state="initial"]').click();
    assert.equal(JSON.parse(await help.locator("#variable-state-example").textContent()).Result.status,"failed");
    await page.mouse.click(2,2);
    assert.equal(await help.isVisible(),false);
    await page.locator("#node-select").selectOption("normalize_mcp");
    assert.equal(await page.locator('#node-parameters button[data-help-topic="normalizer"]').count(),1);
    const result=JSON.parse(await page.locator("#node-output pre").textContent());
    await page.locator("#node-select").selectOption("kpp_mining_end");
    assert.deepEqual(JSON.parse(await page.locator("#node-output pre").textContent()).body,result);
    assert.equal(await page.locator("#node-next").isDisabled(),true);
    await page.locator("#node-select").selectOption("invoke_rest_api");
    assert.ok((await page.locator("#scenario-status").textContent()).includes("tidak melewati node ini"));
    assert.equal(context.pages().length,1);
    assert.deepEqual(errors,[]);assert.deepEqual(outbound,[]);
  }finally{await engine.close()}
});

test("MAF code-first guide stays lightweight and preserves code mapping with same-page help",async()=>{
  const engine=await browser(),page=await engine.newPage({viewport:{width:1366,height:768}});
  const errors=[],outbound=[];
  page.on("pageerror",error=>errors.push(error.message));
  page.on("console",message=>{if(message.type()==="error")errors.push(message.text())});
  page.on("request",request=>{if(/^https?:/.test(request.url()))outbound.push(request.url())});
  try{
    const target=path.join(path.dirname(guide("logicapps")),"maf-code-first-walkthrough.html");
    const html=fs.readFileSync(target,"utf8");
    assert.ok(fs.statSync(target).size<1024*1024);
    assert.ok(!html.includes("portal-gallery-data")&&!html.includes("data:image/png;base64,"));
    await page.goto(pathToFileURL(target).href);
    assert.equal(await page.locator("#startup-error").isVisible(),false);
    const data=JSON.parse(await page.locator("#walkthrough-data").textContent());
    const line=data.sources.yaml.lines.findIndex(value=>value.trim()==="name: kppdemo-mcp")+1;
    await page.locator(`.yaml-line[data-yaml-line="${line}"]`).click();
    assert.equal(await page.locator("#map-block").inputValue(),"invoke_mcp");
    const highlighted=(await page.locator("#direct-python-code .is-highlighted").allTextContents()).join("\n");
    assert.ok(highlighted.includes('"kppdemo-mcp": "1"'));
    const original=page.url(),trigger=page.locator("#map-explain");
    await trigger.click();
    assert.equal(await page.locator("#selection-help").isVisible(),true);
    assert.equal(page.context().pages().length,1);
    assert.equal(page.url(),original);
    assert.ok((await page.locator("#selection-help-code").textContent()).includes('"kppdemo-mcp": "1"'));
    await page.keyboard.press("Escape");
    assert.equal(await page.locator("#selection-help").isVisible(),false);
    assert.equal(await trigger.evaluate(element=>element===document.activeElement),true);
    for(const viewport of [{width:1366,height:768},{width:1536,height:864}]){
      await page.setViewportSize(viewport);
      for(const view of ["map","steps"]){
        await page.locator("#view-tab-"+view).click();
        const bounds=await page.evaluate(()=>({viewport:innerWidth,content:document.documentElement.scrollWidth}));
        assert.ok(bounds.content<=bounds.viewport,JSON.stringify({view,...bounds}));
      }
    }
    assert.deepEqual(errors,[]);assert.deepEqual(outbound,[]);
  }finally{await engine.close()}
});

test("MAF code-first diagram and route controls keep source selections synchronized",async()=>{
  const engine=await browser(),page=await engine.newPage({viewport:{width:1366,height:768}});
  const errors=[],outbound=[];
  page.on("pageerror",error=>errors.push(error.message));
  page.on("console",message=>{if(message.type()==="error")errors.push(message.text())});
  page.on("request",request=>{if(/^https?:/.test(request.url()))outbound.push(request.url())});
  try{
    const target=path.join(path.dirname(guide("logicapps")),"maf-code-first-walkthrough.html");
    const url=pathToFileURL(target).href;
    await page.goto(url+"#view=flow&entry=kpp_mining_start&route=mcp");
    const data=JSON.parse(await page.locator("#walkthrough-data").textContent());
    const image=page.locator("#paired-image");
    await image.evaluate(element=>element.decode());
    assert.equal(await image.getAttribute("src"),data.explorer.diagram.image);
    assert.equal(await image.evaluate(element=>element.naturalWidth),data.explorer.diagram.render_width*2);
    assert.equal(await page.locator("#flow-previous").isDisabled(),true);
    await page.locator("#flow-next").click();
    assert.equal(await page.locator("#map-block").inputValue(),"capture_question");
    await page.locator("#flow-next").click();
    assert.equal(await page.locator("#map-block").inputValue(),"classify_question");
    await page.locator("#flow-previous").click();
    assert.equal(await page.locator("#map-block").inputValue(),"capture_question");
    await page.locator('.diagram-hit[data-diagram-entry="classify_question"][data-lane="python"]').click();
    assert.equal(await page.locator("#map-block").inputValue(),"classify_question");
    await page.locator("#flow-explain").click();
    assert.equal(await page.locator("#selection-help").isVisible(),true);
    await page.locator("#selection-help-close").click();
    await page.locator("#flow-route").selectOption("rest_api");
    assert.ok((await page.locator("#flow-trace").textContent()).includes("invoke_rest_api"));
    assert.ok(!(await page.locator("#flow-trace").textContent()).includes("invoke_mcp"));
    await page.goto(url+"#view=screenshots");
    assert.equal(await page.locator("#view-tab-flow").getAttribute("aria-selected"),"true");
    assert.equal(await page.locator("#startup-error").isVisible(),false);
    const bounds=await page.evaluate(()=>({viewport:innerWidth,content:document.documentElement.scrollWidth}));
    assert.ok(bounds.content<=bounds.viewport,JSON.stringify(bounds));
    assert.deepEqual(errors,[]);assert.deepEqual(outbound,[]);
    await page.locator("#paired-image").evaluate(element=>element.dispatchEvent(new Event("error")));
    assert.equal(await page.locator("#startup-error").isVisible(),true);
    assert.ok((await page.locator("#startup-error").textContent()).includes(data.explorer.diagram.image));
  }finally{await engine.close()}
});

test("Declarative guide keeps all explanations, quizzes and original visuals with local assets",async()=>{
  const engine=await browser(),page=await engine.newPage({viewport:{width:1366,height:768}});
  const errors=[],outbound=[];
  page.on("pageerror",error=>errors.push(error.message));
  page.on("console",message=>{if(message.type()==="error")errors.push(message.text())});
  page.on("request",request=>{if(/^https?:/.test(request.url()))outbound.push(request.url())});
  try{
    const target=guide("declarative");
    assert.ok(fs.statSync(target).size<1024*1024);
    await page.goto(pathToFileURL(target).href);
    const data=JSON.parse(await page.locator("#lesson-data").textContent());
    assert.equal(data.steps.length,6);assert.equal(data.quiz.length,3);
    assert.equal(Object.keys(data.sources).length,40);
    assert.ok(!("diagram_png" in data)&&!("diagram_source" in data)&&!("screenshot" in data));
    const diagram=page.locator("#flow-diagram");
    await diagram.evaluate(image=>image.decode());
    assert.equal(await diagram.getAttribute("src"),data.assets.diagram.path);
    assert.equal(await diagram.evaluate(image=>image.naturalWidth),data.assets.diagram.width);
    assert.equal(await page.locator("#download-diagram").getAttribute("href"),data.assets.diagram_source.path);
    await page.locator("#tab-proof").click();
    const screenshot=page.locator("#screenshot");
    await screenshot.evaluate(image=>image.decode());
    assert.equal(await screenshot.getAttribute("src"),data.assets.screenshot.path);
    assert.equal(await screenshot.evaluate(image=>image.naturalWidth),data.assets.screenshot.width);
    assert.equal(await page.locator("#asset-warning").isVisible(),false);
    assert.equal(await page.locator("#asset-note").isVisible(),true);
    for(const viewport of [{width:1366,height:768},{width:1536,height:864}]){
      await page.setViewportSize(viewport);
      for(const name of ["story","start","source","practice","proof"]){
        await page.locator("#tab-"+name).click();
        const bounds=await page.evaluate(()=>({viewport:innerWidth,content:document.documentElement.scrollWidth}));
        assert.ok(bounds.content<=bounds.viewport,JSON.stringify({name,...bounds}));
      }
    }
    assert.deepEqual(errors,[]);assert.deepEqual(outbound,[]);
  }finally{await engine.close()}
});
