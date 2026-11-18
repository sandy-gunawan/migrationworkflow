"use strict";

const element = (id) => document.getElementById(id);
const statuses = { running: "Berjalan", done: "Selesai", blocked: "Blocked", failed: "Gagal" };
const resultLabels = { success: "Retrieval sukses", blocked: "Blocked", failed: "Gagal", clarification: "Klarifikasi", unsupported: "Unsupported" };
let context;
let busy = false;
let startedAt = 0;
let timer;
let selectedStep;
let sourceRequest = 0;
let currentSource;
const steps = new Map();
const sourceCache = new Map();

function badge(node, text, status) {
  node.textContent = text;
  node.className = `badge ${status}`;
}

function setBusy(value) {
  busy = value;
  element("run-button").disabled = value || !context;
  element("run-button").textContent = value ? "MAF sedang berjalan" : "Jalankan MAF";
  element("question").readOnly = value;
}

function errorMessage(body) {
  if (typeof body.error === "string") return body.error;
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) return body.detail.map((item) => item.msg).join("; ");
  return "Permintaan tidak dapat diproses. Periksa koneksi dan log lokal.";
}

function lessonUrl(key, id) {
  const url = new URL(location.href);
  url.searchParams.set("code", key);
  url.searchParams.set("lesson", id);
  url.hash = "code-title";
  return `${url.pathname}${url.search}${url.hash}`;
}

function selectLesson(id, manual = false) {
  const lesson = currentSource.lessons.find((item) => item.id === id);
  if (!lesson) throw new Error("Bagian penjelasan kode tidak tersedia.");
  element("source-code").querySelectorAll(".code-line").forEach((row) => {
    const line = Number(row.dataset.line);
    row.classList.toggle("highlighted", line >= lesson.line && line <= lesson.end_line);
  });
  element("source-lessons").querySelectorAll("a").forEach((link) => {
    link.setAttribute("aria-current", String(link.dataset.lesson === id));
  });
  element("lesson-title").textContent = lesson.title;
  element("lesson-explanation").textContent = lesson.explanation;
  element("lesson-analogy").textContent = `Bayangkan pos kontrol tambang: ${lesson.analogy}`;
  element("lesson-range").textContent = `Lihat highlight baris ${lesson.line} sampai ${lesson.end_line}`;
  element("lesson-range").hidden = false;
  element("lesson-range").href = `#source-line-${lesson.line}`;
  const first = element(`source-line-${lesson.line}`);
  if (first) element("source-code").scrollTop = Math.max(0, first.offsetTop - 45);
  if (manual) {
    element("follow-active").checked = false;
    history.replaceState(null, "", lessonUrl(currentSource.key, id));
  }
}

async function loadSource(key, preferredLesson = null) {
  const version = ++sourceRequest;
  try {
    let code = sourceCache.get(key);
    if (!code) {
      const response = await fetch(`/ui/code/${encodeURIComponent(key)}`);
      if (!response.ok) throw new Error("Lokasi kode tidak tersedia.");
      code = await response.json();
      sourceCache.set(key, code);
    }
    if (version !== sourceRequest) return;
    currentSource = code;
    element("code-path").textContent = code.path;
    element("code-symbol").textContent = code.symbol;
    element("code-range").textContent = `Baris ${code.line} sampai ${code.end_line}`;
    const pre = element("source-code");
    pre.replaceChildren();
    const links = element("source-lessons");
    links.replaceChildren();
    code.lessons.forEach((lesson) => {
      const link = document.createElement("a");
      link.href = lessonUrl(key, lesson.id);
      link.dataset.lesson = lesson.id;
      link.textContent = `Baris ${lesson.line}-${lesson.end_line}: ${lesson.title}`;
      link.addEventListener("click", (event) => {
        event.preventDefault();
        selectLesson(lesson.id, true);
      });
      links.append(link);
    });
    const lines = code.text.trimEnd().split("\n");
    lines.forEach((line, index) => {
      const row = document.createElement("span");
      row.className = "code-line";
      row.id = `source-line-${code.line + index}`;
      row.dataset.line = String(code.line + index);
      const number = document.createElement("span");
      number.className = "line-number";
      const lesson = code.lessons.find(
        (item) => code.line + index >= item.line && code.line + index <= item.end_line
      );
      if (lesson) {
        const link = document.createElement("a");
        link.href = lessonUrl(key, lesson.id);
        link.textContent = String(code.line + index);
        link.setAttribute("aria-label", `Baris ${code.line + index}: ${lesson.title}`);
        link.addEventListener("click", (event) => {
          event.preventDefault();
          selectLesson(lesson.id, true);
        });
        number.append(link);
      } else {
        number.textContent = String(code.line + index);
      }
      const content = document.createElement("span");
      content.className = "line-content";
      content.textContent = line;
      row.append(number, content);
      pre.append(row, document.createTextNode("\n"));
    });
    selectLesson(preferredLesson || code.lessons[0].id);
  } catch (error) {
    if (version === sourceRequest) {
      element("source-code").textContent = error.message;
      element("source-lessons").replaceChildren();
      element("lesson-title").textContent = "Penjelasan belum tersedia";
      element("lesson-explanation").textContent = error.message;
      element("lesson-analogy").textContent = "";
      element("lesson-range").hidden = true;
    }
  }
}

function selectStep(key, automatic = false) {
  const step = steps.get(key);
  if (!step) return;
  selectedStep = key;
  steps.forEach((item, id) => item.row.classList.toggle("selected", id === key));
  if (!automatic) {
    element("follow-active").checked = false;
    if (matchMedia("(max-width: 1180px)").matches) {
      element("code-title").scrollIntoView({ block: "start" });
    }
  }
  element("explanation-title").textContent = step.update.label;
  element("explanation").textContent = step.update.detail;
  const preferredLessons = {
    context: "conversation", router: "agent_call", routing: "branch",
    activity: "route_marker", specialist: "agent_call", tool: "tool_evidence",
    normalization: "grounding", outcome: "blocked_result", workflow: "execute",
    capacity: step.update.step_id.endsWith("pause") ? "pause" : "resume",
  };
  loadSource(step.update.code_key, preferredLessons[step.update.phase]);
}

function showProgress(update, timestamp) {
  if (update.phase === "workflow" && update.status !== "running") {
    steps.forEach((item) => {
      if (item.update.phase === "workflow" && item.update.status === "running") {
        item.update.status = "done";
        item.row.classList.replace("is-running", "is-done");
        badge(item.status, "Selesai", "done");
      }
    });
  }
  const key = `${update.phase}:${update.step_id}:${update.tool_name || ""}`;
  let step = steps.get(key);
  if (!step) {
    const row = document.createElement("li");
    row.className = "step";
    const dot = document.createElement("span");
    dot.className = "step-dot";
    dot.setAttribute("aria-hidden", "true");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "step-button";
    const header = document.createElement("span");
    header.className = "step-header";
    const title = document.createElement("span");
    title.className = "step-title";
    const status = document.createElement("span");
    const detail = document.createElement("span");
    detail.className = "step-detail";
    const agent = document.createElement("span");
    agent.className = "step-agent";
    const location = document.createElement("span");
    location.className = "step-code";
    header.append(title, status);
    button.append(header, agent, detail, location);
    button.addEventListener("click", () => selectStep(key));
    row.append(dot, button);
    element("steps").append(row);
    step = { row, title, status, detail, agent, location, update };
    steps.set(key, step);
  }
  step.update = update;
  step.row.className = `step is-${update.status}${selectedStep === key ? " selected" : ""}`;
  step.title.textContent = update.label;
  badge(step.status, statuses[update.status], update.status);
  step.detail.textContent = update.detail;
  step.agent.textContent = update.agent_name
    ? `${update.agent_name}${update.agent_version ? ` (v${update.agent_version})` : ""}${update.tool_name ? ` / ${update.tool_name}` : ""}`
    : update.tool_name || "";
  const code = context.code.find((item) => item.key === update.code_key);
  step.location.textContent = `${update.step_id} / ${code ? `${code.path}:${code.line}` : update.code_key}`;
  if (update.status === "running") {
    element("run-status").textContent = update.label;
    badge(element("run-badge"), "Sedang berjalan", "running");
  }
  if (update.agent_name && ["router", "routing", "specialist"].includes(update.phase)) {
    element("active-agent-label").textContent = update.phase === "routing"
      ? "Agent dipilih" : update.status === "running" ? "Agent aktif" : "Agent terakhir";
    element("active-agent").textContent = `${update.agent_name} (v${update.agent_version || "?"})`;
  }
  if (update.phase === "routing" && !update.agent_name) {
    element("active-agent-label").textContent = "Branch tanpa specialist";
    element("active-agent").textContent = "Tidak ada specialist: branch non-dispatch";
  }
  if (element("follow-active").checked) {
    selectStep(key, true);
    const rail = element("steps");
    if (step.row.offsetTop + step.row.offsetHeight > rail.scrollTop + rail.clientHeight) {
      rail.scrollTop = step.row.offsetTop + step.row.offsetHeight - rail.clientHeight;
    }
  }
  element("empty-state").hidden = true;
}

function showResult(output) {
  const result = output.result;
  badge(element("result-badge"), resultLabels[result.status] || result.status, result.status);
  badge(element("run-badge"), resultLabels[result.status] || result.status, result.status);
  element("run-status").textContent = `Run selesai: ${result.route}, ${result.status}.`;
  element("result-answer").textContent = result.answer || (
    result.status === "blocked" ? "Tidak ada retrieval. Capability ini sengaja tetap blocked." : "Tidak ada jawaban data yang dinyatakan sukses."
  );
  element("result-error").hidden = !result.error;
  element("result-error").className = `notice ${result.status === "blocked" ? "warning" : "error"}`;
  element("result-error").textContent = result.error || "";
  element("sources").replaceChildren();
  result.sources.forEach((source) => {
    const item = document.createElement("li");
    const kind = document.createElement("small");
    kind.textContent = source.kind;
    let identity;
    if (/^https?:\/\//i.test(source.id)) {
      identity = document.createElement("a");
      identity.href = source.id;
      identity.target = "_blank";
      identity.rel = "noopener noreferrer";
    } else {
      identity = document.createElement("span");
    }
    identity.textContent = source.id;
    item.append(kind, identity);
    element("sources").append(item);
  });
  element("trace-details").hidden = false;
  element("active-agent-label").textContent = "Agent terakhir / branch";
  element("trace-output").textContent = JSON.stringify(
    { run_id: result.run_id, ...output.trace }, null, 2
  );
}

function showFailure(message) {
  steps.forEach((step) => {
    if (step.update.status === "running") {
      step.row.classList.remove("is-running");
      badge(step.status, "Tidak terverifikasi", "failed");
    }
  });
  badge(element("run-badge"), "Gagal", "failed");
  badge(element("result-badge"), "Tidak terverifikasi", "failed");
  element("run-status").textContent = "Run belum menghasilkan jawaban terverifikasi.";
  element("active-agent-label").textContent = steps.size
    ? "Agent terakhir teramati" : "Agent belum terkonfirmasi";
  if (!steps.size) element("active-agent").textContent = "Tidak ada event agent yang diterima";
  element("explanation-title").textContent = "Eksekusi tidak terverifikasi";
  element("explanation").textContent = message;
  element("result-answer").textContent = "Tidak ada hasil sukses atau sumber yang dibuat sebagai fallback.";
  element("result-error").hidden = false;
  element("result-error").className = "notice error";
  element("result-error").textContent = message;
}

function chooseCase(item) {
  if (busy) return;
  element("question").value = item.question;
  element("character-count").textContent = `${item.question.length} / 4000`;
  element("expected").textContent = `${item.id}: ${item.route} / ${item.expected_status}${item.facts.length ? ` / fakta: ${item.facts.join(", ")}` : " / tanpa specialist data"}`;
  document.querySelectorAll(".preset").forEach((node) => node.classList.toggle("selected", node.dataset.case === item.id));
  element("case-select").value = item.id;
}

async function refreshBusy() {
  try {
    const response = await fetch("/ui/context");
    if (!response.ok) throw new Error("Konteks UI tidak dapat dibaca.");
    const value = await response.json();
    setBusy(value.busy || value.stopping);
    if (value.busy) {
      element("run-status").textContent = "Run sebelumnya masih berjalan. Tunggu cleanup selesai.";
      setTimeout(refreshBusy, 5000);
    }
  } catch (error) {
    element("form-error").hidden = false;
    element("form-error").textContent = error.message;
  }
}

async function run(event) {
  event.preventDefault();
  if (busy || !context) return;
  const question = element("question").value;
  if (!question.trim()) {
    element("form-error").hidden = false;
    element("form-error").textContent = "Isi satu pertanyaan tentang data dummy.";
    return;
  }
  setBusy(true);
  startedAt = Date.now();
  clearInterval(timer);
  timer = setInterval(() => {
    element("elapsed").textContent = `${((Date.now() - startedAt) / 1000).toFixed(1)} detik`;
  }, 100);
  steps.clear();
  selectedStep = undefined;
  element("follow-active").checked = true;
  element("explanation-title").textContent = "Menyiapkan run baru";
  element("explanation").textContent = "Menunggu event asli dari graph MAF.";
  loadSource("workflow");
  element("steps").replaceChildren();
  element("sources").replaceChildren();
  element("form-error").hidden = true;
  element("result-error").hidden = true;
  element("trace-details").hidden = true;
  element("empty-state").hidden = true;
  element("result-answer").textContent = "Jawaban belum tersedia. Mengikuti eksekusi asli.";
  element("active-agent").textContent = "Menunggu router";
  element("active-agent-label").textContent = "Agent aktif";
  badge(element("result-badge"), "Menunggu evidence", "neutral");
  badge(element("run-badge"), "Menghubungkan", "running");
  element("run-status").textContent = "Mengirim pertanyaan ke MAF lokal.";
  let terminal = false;
  try {
    const response = await fetch("/ui/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Demo-CSRF": context.csrf_token },
      body: JSON.stringify({ question }),
    });
    if (!response.ok) throw new Error(errorMessage(await response.json()));
    if (!response.body) throw new Error("Browser tidak mendukung progress streaming.");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const chunk = await reader.read();
      buffer += decoder.decode(chunk.value, { stream: !chunk.done });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (!line.trim()) continue;
        const item = JSON.parse(line);
        if (item.type === "started") {
          startedAt = Date.parse(item.timestamp);
        } else if (item.type === "progress") {
          showProgress(item.update, item.timestamp);
        } else if (item.type === "result") {
          terminal = true;
          showResult(item.output);
        } else if (item.type === "error") {
          terminal = true;
          showFailure(`${item.message} (${item.error_type})`);
        }
      }
      if (chunk.done) break;
    }
    if (!terminal) throw new Error("Progress stream terputus sebelum hasil; run mungkin masih menyelesaikan cleanup.");
  } catch (error) {
    showFailure(error.message);
  } finally {
    clearInterval(timer);
    element("elapsed").textContent = `${((Date.now() - startedAt) / 1000).toFixed(1)} detik`;
    await refreshBusy();
  }
}

async function boot() {
  try {
    const response = await fetch("/ui/context");
    if (!response.ok) throw new Error("Konteks UI belum siap. Periksa server lokal.");
    context = await response.json();
    element("identity-mode").textContent = context.identity_mode === "azure_cli"
      ? "Lokal / Azure CLI ke Foundry" : "Contract test fixture / bukan live retrieval";
    element("framework-info").textContent = `Core ${context.framework_version} / source ${context.source_sha256.slice(0, 12)}`;
    context.presets.forEach((item) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "preset";
      button.dataset.case = item.id;
      const label = document.createElement("span");
      label.textContent = item.label;
      const status = document.createElement("small");
      status.textContent = item.expected_status === "success" ? "Retrieval" : item.expected_status;
      button.append(label, status);
      button.addEventListener("click", () => chooseCase(item));
      element("presets").append(button);
    });
    context.cases.forEach((item) => {
      const option = document.createElement("option");
      option.value = item.id;
      option.textContent = `${item.id}: ${item.question}`;
      element("case-select").append(option);
    });
    setBusy(context.busy || context.stopping);
    chooseCase(context.presets[0]);
    const guide = new URLSearchParams(location.search);
    await loadSource(guide.get("code") || "workflow", guide.get("lesson"));
    if (guide.has("code")) {
      element("explanation-title").textContent = "Belajar kode, belum menjalankan agent";
      element("explanation").textContent = "Tautan ini hanya membuka kode dan penjelasan. Tidak ada request data baru.";
      element("follow-active").checked = false;
    }
    if (context.busy) refreshBusy();
  } catch (error) {
    element("form-error").hidden = false;
    element("form-error").textContent = error.message;
    element("identity-mode").textContent = "Konteks belum tersedia";
  }
}

element("question-form").addEventListener("submit", run);
element("question").addEventListener("input", (event) => {
  element("character-count").textContent = `${event.target.value.length} / 4000`;
});
element("question").addEventListener("keydown", (event) => {
  if (event.ctrlKey && event.key === "Enter" && !busy) {
    event.preventDefault();
    element("question-form").requestSubmit();
  }
});
element("case-select").addEventListener("change", (event) => {
  const item = context.cases.find((candidate) => candidate.id === event.target.value);
  if (item) chooseCase(item);
});
element("follow-active").addEventListener("change", (event) => {
  if (event.target.checked && steps.size) selectStep(Array.from(steps.keys()).pop(), true);
});
boot();
