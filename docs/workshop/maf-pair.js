"use strict";

(() => {
  const $ = id => document.getElementById(id);
  const data = window.mafPair;
  if (!data?.sources?.yaml || data.lines?.length !== data.sources.yaml.lines.length || !data.entries?.length) {
    $("pair-load-error").hidden = false;
    return;
  }

  const repo = "https://github.com/sandy-gunawan/migrationworkflow/blob/main/";
  const yaml = $("pair-yaml");
  const python = $("pair-python");
  const action = $("pair-action");
  const target = $("pair-target");
  const entries = data.entries;
  const byEntry = new Map(entries.map((entry, index) => [entry.id, index]));
  const preferredLine = data.lines.findIndex((line) => entries[line.entry].id === "route_mcp" && line.field === "condition");
  let selected = Math.max(0, preferredLine);
  let selectedTarget = data.lines[selected].target;

  function option(value, label) {
    const item = document.createElement("option");
    item.value = value;
    item.textContent = label;
    return item;
  }

  function codeRow(text, number, interactive) {
    const row = document.createElement(interactive ? "button" : "div");
    row.className = "pair-row";
    row.dataset.line = number;
    if (interactive) row.type = "button";
    const gutter = document.createElement("span");
    gutter.className = "pair-number";
    gutter.textContent = number;
    gutter.setAttribute("aria-hidden", "true");
    const line = document.createElement("code");
    line.textContent = text || " ";
    row.append(gutter, line);
    if (interactive) row.setAttribute("aria-label", `Baris ${number}: ${text.trim() || "baris kosong"}`);
    return row;
  }

  function reveal(container, row) {
    if (row) container.scrollTop = Math.max(0, row.offsetTop - container.firstElementChild.offsetTop - 48);
  }

  const yamlRows = data.sources.yaml.lines.map((line, index) => codeRow(line, index + 1, true));
  yaml.append(...yamlRows);
  action.append(...entries.map(entry => option(entry.id, `${entry.title} · ${entry.id}`)));

  function render(jump = true) {
    const line = data.lines[selected];
    const entry = entries[line.entry];
    const pair = entry.targets[selectedTarget];
    const reference = pair.ref;
    const source = data.sources[reference.file];

    action.value = entry.id;
    target.replaceChildren(...entry.targets.map((item, index) => option(index, item.label)));
    target.value = selectedTarget;
    $("pair-yaml-source").href = `${repo}${data.sources.yaml.path}#L${selected + 1}`;
    $("pair-python-source").href = `${repo}${source.path}#L${reference.start}-L${reference.end}`;
    $("pair-python-source").textContent = `${source.name} · L${reference.start}–${reference.end}`;

    const focused = new Set(line.focus);
    yamlRows.forEach((row, i) => {
      row.toggleAttribute("data-block", i + 1 >= entry.yaml.start && i + 1 <= entry.yaml.end);
      row.toggleAttribute("data-highlight", focused.has(i + 1));
      row.setAttribute("aria-pressed", String(i === selected));
      row.tabIndex = i === selected ? 0 : -1;
    });
    const code = source.lines.slice(reference.start - 1, reference.end)
      .map((text, index) => codeRow(text, reference.start + index, false));
    const lines = new Set(reference.focus);
    code.forEach(row => row.toggleAttribute("data-highlight", lines.has(Number(row.dataset.line))));
    python.replaceChildren(...code);
    if (jump) reveal(yaml, yamlRows[selected]);
    reveal(python, python.querySelector("[data-highlight]"));
    $("pair-selection").textContent = `YAML baris ${selected + 1} · ${line.field} → ${pair.label}`;
    $("pair-explanation").textContent = pair.detail;
  }

  function select(index, focus = false) {
    selected = index;
    selectedTarget = data.lines[index].target;
    render();
    if (focus) yamlRows[index].focus({preventScroll: true});
  }

  yaml.addEventListener("click", event => {
    const row = event.target.closest("button[data-line]");
    if (row) select(Number(row.dataset.line) - 1, true);
  });
  yaml.addEventListener("keydown", event => {
    const row = event.target.closest("button[data-line]");
    if (!row) return;
    const index = Number(row.dataset.line) - 1;
    const next = {ArrowUp: index - 1, ArrowDown: index + 1, Home: 0, End: yamlRows.length - 1};
    if (!Object.hasOwn(next, event.key)) return;
    event.preventDefault();
    select(Math.min(yamlRows.length - 1, Math.max(0, next[event.key])), true);
  });
  action.addEventListener("change", () => select(data.lines.findIndex(line => line.entry === byEntry.get(action.value))));
  target.addEventListener("change", () => {
    selectedTarget = Number(target.value);
    render(false);
  });

  $("pair-inspector").hidden = false;
  render();
  $("pair-fallback").hidden = true;
})();
