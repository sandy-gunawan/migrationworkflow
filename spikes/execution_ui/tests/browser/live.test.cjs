const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const { ROOT, browser, targets, origin, writeEvidence } = require("./helpers.cjs");

if(process.env.KPP_UI_LIVE!=="1")throw new Error("Set KPP_UI_LIVE=1 explicitly for paid demo smoke tests.");
for(const kind of targets())test(kind+" live MCP and blocked UI smoke",{timeout:600000},async()=>{
  const engine=await browser(),page=await engine.newPage({viewport:{width:1600,height:1080}});
  const errors=[],records=[];
  page.on("pageerror",error=>errors.push(error.message));
  try{
    for(const route of ["mcp","work_iq"]){
      await page.goto(origin(kind)+"/");
      await page.waitForFunction(()=>!document.getElementById("run-button").disabled);
      const context=await page.evaluate(async()=>await(await fetch("/ui/context")).json());
      assert.equal(context.identity_mode,"azure_cli");
      const item=context.presets.find(value=>value.route===route);
      assert.ok(item,"Missing requested route preset.");
      await page.locator(".catalog > summary").click();
      await page.locator("#case-select").selectOption(item.id);
      const stream=page.waitForResponse(response=>response.url().endsWith("/ui/runs")&&response.request().method()==="POST",{timeout:360000});
      await page.locator("#run-button").click();
      const response=await stream;
      assert.equal(response.status(),200);
      const frames=(await response.text()).trim().split("\n").map(line=>JSON.parse(line));
      const terminal=frames.findLast(frame=>["result","error"].includes(frame.type));
      assert.ok(terminal,"No terminal event.");
      assert.equal(terminal.type,"result",JSON.stringify(terminal));
      const output=terminal.output;
      assert.equal(output.result.route,route);
      assert.equal(output.result.status,item.expected_status);
      await page.waitForFunction(()=>!document.getElementById("run-button").disabled);
      if(route==="mcp"){
        assert.ok(output.result.answer.includes("WO001"),JSON.stringify(output.result));
        assert.ok(output.result.sources.length>0);
        assert.ok(frames.some(frame=>frame.type==="progress"&&frame.update.tool_name));
        assert.ok((await page.locator("#result-answer").textContent()).includes("WO001"));
        const folder=path.join(ROOT,"docs","how-to","screenshots","local-ui");
        fs.mkdirSync(folder,{recursive:true});
        await page.screenshot({path:path.join(folder,kind+"-mcp.png"),fullPage:true});
      }else{
        assert.equal(output.result.answer,null);
        assert.equal(output.result.sources.length,0);
        assert.ok(output.result.error);
        assert.ok(!frames.some(frame=>frame.type==="progress"&&frame.update.phase==="specialist"&&
          frame.update.status!=="skipped"));
      }
      assert.equal(await page.locator("#fixture-warning").isVisible(),false);
      records.push({case_id:item.id,question:item.question,result:output.result,trace:output.trace,
        progress:frames.filter(frame=>frame.type==="progress").map(frame=>frame.update)});
    }
    assert.deepEqual(errors,[]);
    writeEvidence(kind,{status:"PASS",kind,case_count:records.length,browser:await engine.version(),
      live_model_calls_authorized:true,fabric_resumed:false,page_errors:errors,cases:records});
  }finally{await engine.close()}
});
