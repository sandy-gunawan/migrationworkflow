"use strict";

const el = id => document.getElementById(id);
const labels = {
  running:"Berjalan", waiting:"Menunggu", done:"Selesai", skipped:"Dilewati",
  failed:"Gagal", success:"Retrieval sukses", blocked:"Blocked",
  clarification:"Klarifikasi", unsupported:"Unsupported",
};
let context, currentSource, busy = false, startedAt = 0, clock, sourceSequence = 0;
const steps = new Map(), sourceCache = new Map();

function badge(node, status, text) {
  node.className = "badge " + status;
  node.textContent = text || labels[status] || status;
}
function setBusy(value) {
  busy = value;
  el("run-button").disabled = value || !context;
  el("run-button").textContent = value ? "Run sedang berjalan" : context.run_label;
  el("question").readOnly = value;
}
function showError(message) {
  el("form-error").textContent = message;
  el("form-error").hidden = false;
}
function requestError(body) {
  if (typeof body.error === "string") return body.error;
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) return body.detail.map(item => item.msg).join("; ");
  return "Request gagal. Periksa log lokal; tidak ada hasil pengganti.";
}
function selectLesson(id, manual = false) {
  const lesson = currentSource.lessons.find(item => item.id === id);
  if (!lesson) throw new Error("Bagian penjelasan tidak tersedia.");
  el("lesson-title").textContent = lesson.title;
  el("lesson-explanation").textContent = lesson.explanation;
  el("lesson-analogy").textContent = "Bayangkan pos kontrol tambang: " + lesson.analogy;
  el("source-code").querySelectorAll(".code-line").forEach(row => {
    const number = Number(row.dataset.line);
    row.classList.toggle("highlighted", number >= lesson.line && number <= lesson.end_line);
  });
  el("source-lessons").querySelectorAll("button").forEach(button => {
    button.setAttribute("aria-current", String(button.dataset.lesson === id));
  });
  if (manual) {
    el("follow-active").checked = false;
    const query = new URLSearchParams({code:currentSource.key,lesson:id});
    history.replaceState(null,"","/?" + query + "#code-title");
  }
}
async function loadSource(key, lessonId = null) {
  const sequence = ++sourceSequence;
  try {
    let source = sourceCache.get(key);
    if (!source) {
      const response = await fetch("/ui/code/" + encodeURIComponent(key));
      if (!response.ok) throw new Error("Source langkah ini tidak dapat dibaca.");
      source = await response.json();
      sourceCache.set(key,source);
    }
    if (sequence !== sourceSequence) return;
    currentSource = source;
    el("code-select").value = key;
    el("code-path").textContent = source.path;
    el("code-symbol").textContent = source.symbol + " / " + source.language;
    el("code-range").textContent = "Baris " + source.line + " sampai " + source.end_line;
    el("source-lessons").replaceChildren(...source.lessons.map(lesson => {
      const button = document.createElement("button");
      button.type = "button"; button.dataset.lesson = lesson.id;
      button.textContent = lesson.title;
      button.addEventListener("click",()=>selectLesson(lesson.id,true));
      return button;
    }));
    el("source-code").replaceChildren(...source.text.trimEnd().split("\n").map((text,index) => {
      const row = document.createElement("span"); row.className = "code-line";
      row.dataset.line = String(source.line + index); row.id = "source-line-" + row.dataset.line;
      const number = document.createElement("span"); number.className = "line-number";
      number.textContent = row.dataset.line;
      const content = document.createElement("span"); content.className = "line-content";
      content.textContent = text;
      row.append(number,content,document.createTextNode("\n"));
      return row;
    }));
    selectLesson(lessonId || source.lessons[0].id);
  } catch (error) {
    console.error("Source inspector failed",error);
    el("source-code").textContent = error.message;
    el("lesson-explanation").textContent = error.message;
  }
}
function chooseCase(item) {
  if (busy) return;
  el("question").value = item.question;
  el("character-count").textContent = item.question.length + " / 4000";
  el("case-select").value = item.id;
  el("expected").textContent = item.id + ": baseline " + item.route + " / " +
    item.expected_status + (item.route === "fabric_data" ?
      ". Fabric memerlukan F2 Active; UI ini tidak mengatur capacity." :
      ". Ini ekspektasi baseline, bukan hasil run baru.");
  document.querySelectorAll(".preset").forEach(button => {
    button.classList.toggle("selected",button.dataset.case === item.id);
  });
}
function selectStep(key, manual = false) {
  const item = steps.get(key);
  if (!item) throw new Error("Langkah yang dipilih tidak tersedia.");
  steps.forEach((value,id)=>value.row.classList.toggle("selected",id===key));
  el("explanation-title").textContent = item.update.label;
  el("explanation").textContent = item.update.detail;
  if (manual) el("follow-active").checked = false;
  loadSource(item.update.code_key);
}
function filterSteps() {
  steps.forEach(item => {
    item.row.hidden = item.update.status === "skipped" && !el("show-skipped").checked;
  });
}
function orderNativeSteps() {
  if (context.kind !== "logicapps") return;
  const rank = item => item.update.step_id === "submit_native_workflow" ? 0 :
    item.update.native_started ? 1 : 2;
  const ordered = [...steps.values()].sort((first,second) => {
    const category = rank(first)-rank(second);
    if (category) return category;
    if (first.update.native_started && second.update.native_started) {
      return first.update.native_started.localeCompare(second.update.native_started);
    }
    return 0;
  });
  el("steps").replaceChildren(...ordered.map(item=>item.row));
}
function progress(update) {
  const key = update.step_id + ":" + (update.tool_name || "");
  let item = steps.get(key);
  if (!item) {
    const row = document.createElement("li"); row.className = "step";
    const dot = document.createElement("span"); dot.className = "step-dot";
    const button = document.createElement("button"); button.type = "button"; button.className = "step-button";
    const header = document.createElement("span"); header.className = "step-header";
    const title = document.createElement("span"); title.className = "step-title";
    const status = document.createElement("span");
    const agent = document.createElement("span"); agent.className = "step-agent";
    const detail = document.createElement("span"); detail.className = "step-detail";
    const location = document.createElement("span"); location.className = "step-code";
    header.append(title,status); button.append(header,agent,detail,location);
    button.addEventListener("click",()=>selectStep(key,true));
    row.append(dot,button); el("steps").append(row);
    item = {row,title,status,agent,detail,location}; steps.set(key,item);
  }
  item.update = update;
  item.row.className = "step is-" + update.status;
  item.title.textContent = update.label;
  badge(item.status,update.status);
  item.agent.textContent = update.agent_name ?
    update.agent_name + " (v" + update.agent_version + ")" +
      (update.tool_name ? " / " + update.tool_name : "") : update.tool_name || "";
  item.detail.textContent = update.detail;
  item.location.textContent = update.step_id + (update.cloud_status ? " / Azure: " + update.cloud_status : "");
  if (update.status === "running" || update.status === "waiting") {
    el("run-status").textContent = update.label;
    badge(el("run-badge"),"running");
  }
  if (update.agent_name && update.status !== "skipped") {
    el("active-agent-label").textContent = update.status === "running" ? "Agent teramati aktif" : "Agent terakhir teramati";
    el("active-agent").textContent = update.agent_name + " (v" + update.agent_version + ")";
  }
  if (update.phase === "outcome" && update.status !== "skipped") {
    el("active-agent-label").textContent = "Branch tanpa specialist";
    el("active-agent").textContent = "Outcome non-dispatch";
  }
  filterSteps();
  orderNativeSteps();
  el("empty-state").hidden = true;
  if (el("follow-active").checked && update.status !== "skipped") selectStep(key);
}
function result(output) {
  const value = output.result;
  steps.forEach(item => {
    if (item.update.phase === "workflow" && ["running","waiting"].includes(item.update.status)) {
      item.update.status = "done";
      item.row.className = "step is-done";
      badge(item.status,"done");
    }
  });
  badge(el("run-badge"),value.status);
  badge(el("result-badge"),value.status);
  el("run-status").textContent = "Run selesai: " + value.route + " / " + value.status + ".";
  el("result-answer").textContent = value.answer || (
    value.status === "blocked" ? "Tidak ada retrieval. Capability ini tetap blocked." : "Tidak ada jawaban sukses."
  );
  el("result-error").hidden = !value.error;
  el("result-error").className = "notice " + (value.status === "blocked" ? "warning" : "error");
  el("result-error").textContent = value.error || "";
  el("sources").replaceChildren(...value.sources.map(source => {
    const li = document.createElement("li"), kind = document.createElement("small");
    kind.textContent = source.kind;
    const target = document.createElement(/^https?:\/\//i.test(source.id) ? "a" : "span");
    if (target.tagName === "A") {
      target.href = source.id; target.target = "_blank"; target.rel = "noopener noreferrer";
    }
    target.textContent = source.id; li.append(kind,target); return li;
  }));
  el("trace-output").textContent = JSON.stringify({run_id:value.run_id,...output.trace},null,2);
  el("trace-details").hidden = false;
}
function failure(message) {
  steps.forEach(item => {
    if (["running","waiting"].includes(item.update.status)) {
      item.row.className = "step is-failed";
      badge(item.status,"failed","Tidak terverifikasi");
    }
  });
  badge(el("run-badge"),"failed"); badge(el("result-badge"),"failed","Tidak terverifikasi");
  el("run-status").textContent = "Run tidak menghasilkan verifikasi lengkap.";
  el("result-answer").textContent = "Tidak ada jawaban atau sumber yang dibuat sebagai fallback.";
  el("result-error").textContent = message; el("result-error").hidden = false;
  el("result-error").className = "notice error";
}
async function refreshBusy() {
  try {
    const response = await fetch("/ui/context");
    if (!response.ok) throw new Error("Status backend tidak dapat dibaca.");
    const value = await response.json();
    setBusy(value.busy || value.stopping);
    if (value.busy) setTimeout(refreshBusy,2000);
  } catch (error) { showError(error.message); }
}
async function run(event) {
  event.preventDefault();
  if (busy || !context) return;
  const question = el("question").value;
  if (!question.trim()) { showError("Isi pertanyaan, bukan spasi saja."); return; }
  setBusy(true); startedAt = Date.now();
  steps.clear(); el("steps").replaceChildren(); el("sources").replaceChildren();
  el("form-error").hidden = true; el("result-error").hidden = true; el("trace-details").hidden = true;
  el("result-answer").textContent = "Menunggu hasil terverifikasi.";
  el("active-agent").textContent = "Belum ada event agent";
  el("follow-active").checked = true; el("empty-state").hidden = true;
  badge(el("run-badge"),"running","Menghubungkan"); badge(el("result-badge"),"waiting");
  el("run-status").textContent = "Mengirim pertanyaan ke backend " + context.kind + ".";
  clock = setInterval(()=>{ el("elapsed").textContent = ((Date.now()-startedAt)/1000).toFixed(1)+" detik"; },100);
  let terminal = false;
  try {
    const response = await fetch("/ui/runs",{
      method:"POST",headers:{"Content-Type":"application/json","X-Demo-CSRF":context.csrf_token},
      body:JSON.stringify({question}),
    });
    if (!response.ok) throw new Error(requestError(await response.json()));
    if (!response.body) throw new Error("Browser tidak mendukung streaming.");
    const reader = response.body.getReader(), decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const chunk = await reader.read();
      buffer += decoder.decode(chunk.value,{stream:!chunk.done});
      const lines = buffer.split("\n"); buffer = lines.pop() || "";
      for (const line of lines) {
        if (!line.trim()) continue;
        const frame = JSON.parse(line);
        if (frame.type === "started") startedAt = Date.parse(frame.timestamp);
        else if (frame.type === "progress") progress(frame.update);
        else if (frame.type === "result") { terminal = true; result(frame.output); }
        else if (frame.type === "error") { terminal = true; failure(frame.message); }
      }
      if (chunk.done) break;
    }
    if (!terminal) throw new Error("Stream terputus. Backend mungkin masih menyelesaikan run; jangan mengirim ulang otomatis.");
  } catch (error) {
    console.error("Execution failed",error); failure(error.message);
  } finally { clearInterval(clock); await refreshBusy(); }
}
async function boot() {
  try {
    const response = await fetch("/ui/context");
    if (!response.ok) throw new Error("Backend lokal belum siap.");
    context = await response.json();
    document.title = context.title;
    el("engine").textContent = context.engine;
    el("runtime-description").textContent = context.description;
    el("waiting-note").textContent = context.waiting_note;
    el("identity-mode").textContent = context.identity_mode === "azure_cli" ?
      "Lokal / Azure CLI identity" : "Contract fixture, bukan live Azure";
    el("fixture-warning").hidden = context.identity_mode !== "unit_fixture";
    el("runtime-proof").textContent = context.engine + " / source " + context.source_sha256.slice(0,12);
    el("definition-path").textContent = context.definition.path;
    el("definition-hash").textContent = "SHA-256 " + context.definition.sha256;
    context.presets.forEach(item => {
      const button = document.createElement("button"); button.type = "button"; button.className = "preset";
      button.dataset.case = item.id; button.textContent = item.label;
      button.addEventListener("click",()=>chooseCase(item)); el("presets").append(button);
    });
    context.cases.forEach(item => {
      const option = document.createElement("option"); option.value = item.id;
      option.textContent = item.id + ": " + item.question; el("case-select").append(option);
    });
    context.code.forEach(item => {
      const option = document.createElement("option"); option.value = item.key;
      option.textContent = item.label + " / " + item.language;
      el("code-select").append(option);
    });
    el("code-select").disabled = false;
    setBusy(context.busy || context.stopping);
    const first = context.presets.find(item=>item.route==="mcp");
    if (!first) throw new Error("Contoh MCP tidak ada dalam corpus yang diharapkan.");
    chooseCase(first);
    const params = new URLSearchParams(location.search);
    await loadSource(params.get("code") || "workflow",params.get("lesson"));
    if (params.has("code")) el("follow-active").checked = false;
    if (context.busy) refreshBusy();
  } catch (error) { console.error("Workbench startup failed",error); showError(error.message); }
}
el("question-form").addEventListener("submit",run);
el("question").addEventListener("input",()=>{ el("character-count").textContent = el("question").value.length+" / 4000"; });
el("question").addEventListener("keydown",event=>{
  if (event.ctrlKey && event.key==="Enter" && !busy) el("question-form").requestSubmit();
});
el("case-select").addEventListener("change",()=>{
  const item = context.cases.find(value=>value.id===el("case-select").value);
  if (item) chooseCase(item);
});
el("show-skipped").addEventListener("change",filterSteps);
el("code-select").addEventListener("change",()=>{
  el("follow-active").checked = false;
  loadSource(el("code-select").value);
});
el("definition-button").addEventListener("click",async()=>{
  try {
    const response = await fetch("/ui/definition");
    if (!response.ok) throw new Error("Snapshot definisi tidak dapat dibaca.");
    const value = await response.json();
    el("definition-text").textContent = value.text;
    el("definition-details").open = true;
    el("definition-details").scrollIntoView({block:"start"});
  } catch (error) { showError(error.message); }
});
boot();
