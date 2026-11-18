const fs = require("node:fs");
const net = require("node:net");
const path = require("node:path");
const { spawn } = require("node:child_process");
const { setTimeout: delay } = require("node:timers/promises");
const { chromium } = require("playwright");

const ROOT = path.resolve(__dirname, "..", "..", "..", "..");
const targets = () => (process.env.KPP_UI_TARGETS || "logicapps,declarative").split(",");
const origin = kind => "http://127.0.0.1:" + (kind === "logicapps" ? "8766" : "8767");
const guide = kind => path.join(ROOT,"docs","how-to",kind === "logicapps" ?
  "logicapps-ui-walkthrough.html" : "maf-declarative-walkthrough.html");
const browser = () => chromium.launch({channel:"msedge",headless:true});

async function fixture() {
  const listener = net.createServer();
  await new Promise((resolve,reject) => {
    listener.once("error",reject); listener.listen(0,"127.0.0.1",resolve);
  });
  const port = listener.address().port;
  await new Promise(resolve=>listener.close(resolve));
  const child = spawn(path.join(ROOT,".venv","Scripts","python.exe"),
    ["-X","utf8","-m","spikes.execution_ui.tests.fixture_server","--port",String(port)],
    {cwd:ROOT,env:{...process.env,PYTHONUTF8:"1"},stdio:["ignore","pipe","pipe"]});
  let log = "";
  child.stdout.on("data",chunk=>{log=(log+chunk.toString()).slice(-4000)});
  child.stderr.on("data",chunk=>{log=(log+chunk.toString()).slice(-4000)});
  const base = "http://127.0.0.1:"+port;
  for (let attempt=0;attempt<80;attempt++) {
    if (child.exitCode!==null) throw new Error("Fixture startup failed: "+log);
    try { if ((await fetch(base+"/health")).ok) break; }
    catch (error) {
      if (attempt===79) {child.kill();throw new Error("Fixture readiness failed: "+error.message+" "+log)}
    }
    await delay(100);
  }
  return {
    origin:base,
    async close() {
      try {
        const context=await (await fetch(base+"/ui/context")).json();
        await fetch(base+"/ui/shutdown",{method:"POST",headers:{
          Origin:base,"X-Demo-CSRF":context.csrf_token,
        }});
        for(let attempt=0;attempt<30&&child.exitCode===null;attempt++) await delay(100);
      } finally { if(child.exitCode===null) child.kill(); }
    },
  };
}
function writeEvidence(kind, value) {
  const folder=path.join(ROOT,"evidence","local-ui");fs.mkdirSync(folder,{recursive:true});
  fs.writeFileSync(path.join(folder,kind+"-smoke.json"),JSON.stringify(value,null,2)+"\n");
}
module.exports={ROOT,targets,origin,guide,browser,fixture,writeEvidence};
