"use strict";

(() => {
  const $ = id => document.getElementById(id);
  const error = $("node-load-error");
  const data = window.logicWorkshop;
  if (!data?.nodes?.length || !data.overview?.image || !Array.isArray(data.shots)) {
    error.hidden = false;
    return;
  }

  const byId = new Map(data.nodes.map(node => [node.id, node]));
  const groups = new Map();
  for (const node of data.nodes) {
    if (!groups.has(node.group)) groups.set(node.group, []);
    groups.get(node.group).push(node);
  }
  const photos = new Map();
  for (const shot of data.shots) {
    if (!photos.has(shot.node)) photos.set(shot.node, []);
    photos.get(shot.node).push(shot);
  }
  const group = $("node-group");
  for (const [label, nodes] of groups) {
    const option = document.createElement("option");
    option.value = label;
    option.textContent = `${label} (${nodes.length})`;
    group.append(option);
  }

  const overview = data.overview;
  const canvas = $("node-canvas");
  const picture = $("node-canvas-image");
  const mark = $("node-canvas-mark");
  const rail = $("node-rail");
  const search = $("node-search");
  const prev = $("node-prev");
  const next = $("node-next");
  let active;
  let visibleNodes = [];

  picture.addEventListener("error", () => {
    canvas.closest("figure").querySelector("figcaption").textContent =
      "Gambar kanvas tidak bisa dibuka. Pastikan folder aset ikut tersalin.";
  });
  picture.setAttribute("href", overview.image);
  picture.setAttribute("width", overview.width);
  picture.setAttribute("height", overview.height);

  function showCanvas(node) {
    const [x, y, width, height] = overview.node_boxes[node.id];
    const left = Math.max(0, x - 43);
    const top = Math.max(0, y - 45);
    const w = Math.min(overview.width, x + width + 43) - left;
    const h = Math.min(overview.height, y + height + 45) - top;
    canvas.setAttribute("viewBox", [left, top, w, h].join(" "));
    canvas.setAttribute("width", w);
    canvas.setAttribute("height", h);
    $("node-canvas-label").textContent = `Posisi ${node.title} pada kanvas Azure Designer`;
    for (const [name, value] of Object.entries({x, y, width, height})) mark.setAttribute(name, value);

    const assets = photos.get(node.id) ?? [];
    if (!assets.length) {
      const notice = document.createElement("p");
      notice.className = "muted";
      notice.textContent = "Node ini terlihat di kanvas, tetapi belum ada cuplikan panel Parameters. Buka bagian parameter dan contoh untuk melihat nilainya.";
      $("node-shots").replaceChildren(notice);
      return;
    }
    $("node-shots").replaceChildren(...assets.map(shot => {
      const figure = document.createElement("figure");
      const img = document.createElement("img");
      const caption = document.createElement("figcaption");
      img.src = shot.image;
      img.width = shot.width;
      img.height = shot.height;
      img.loading = "lazy";
      img.alt = `Panel Parameters pada ${node.title}`;
      caption.textContent = shot.caption;
      img.addEventListener("error", () => {
        caption.textContent = `${shot.caption} Gambar tidak dapat dimuat.`;
      });
      figure.append(img, caption);
      return figure;
    }));
  }

  const readable = value => typeof value === "string" ? value : JSON.stringify(value, null, 2);

  function showDetail(node) {
    $("node-kind").textContent = `${node.type} / ${node.id}`;
    $("node-title").textContent = node.title;
    $("node-purpose").textContent = node.purpose;
    $("node-why").textContent = node.why;
    const rows = [
      ...(node.method ? [{name: "Method", value: node.method}] : []),
      ...(node.url ? [{name: "Endpoint contoh", value: node.url}] : []),
      ...node.parameters,
    ];
    $("node-parameters").replaceChildren(...rows.flatMap(row => {
      const label = document.createElement("dt");
      const description = document.createElement("dd");
      label.textContent = row.name;
      description.textContent = readable(row.value);
      return [label, description];
    }));
    const example = node.scenario;
    $("node-input-label").textContent = example?.input_label ?? "Input pada cabang ini";
    $("node-output-label").textContent = example?.output_label ?? "Contoh output pada cabang ini";
    $("node-input").textContent = readable(example ? example.input : node.input);
    $("node-output").textContent = readable(example ? example.output : node.output);
    $("node-json").textContent = JSON.stringify(node.raw, null, 2);
    $("node-announcement").textContent = `${node.title} dipilih.`;
    showCanvas(node);
  }

  function markRail() {
    const index = visibleNodes.indexOf(active);
    for (const [i, button] of [...rail.querySelectorAll("button")].entries()) {
      if (i === index) button.setAttribute("aria-current", "step");
      else button.removeAttribute("aria-current");
      button.tabIndex = i === Math.max(0, index) ? 0 : -1;
    }
    prev.disabled = index < 1;
    next.disabled = index >= visibleNodes.length - 1;
  }

  function drawRail() {
    const query = search.value.trim().toLocaleLowerCase("id");
    visibleNodes = groups.get(group.value).filter(node =>
      `${node.title} ${node.id} ${node.type}`.toLocaleLowerCase("id").includes(query));
    $("node-match-count").textContent = visibleNodes.length
      ? `${visibleNodes.length} node dalam pilihan ini.`
      : "Tidak ada node yang cocok. Ubah kata pencarian.";
    rail.replaceChildren(...visibleNodes.map(node => {
      const row = document.createElement("li");
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.node = node.id;
      button.textContent = node.title;
      button.setAttribute("aria-controls", "node-detail");
      row.append(button);
      return row;
    }));
    rail.hidden = visibleNodes.length === 0;
    markRail();
  }

  function select(node, share = true) {
    active = node;
    error.hidden = true;
    if (group.value !== node.group) {
      group.value = node.group;
      search.value = "";
      drawRail();
    } else markRail();
    showDetail(node);
    if (share) history.replaceState(null, "", "#" + new URLSearchParams({node: node.id}));
  }

  function selectFromHash() {
    const id = new URLSearchParams(location.hash.slice(1)).get("node");
    if (!id) return;
    const node = byId.get(id);
    if (!node) {
      error.textContent = "Node dari tautan tidak ditemukan. Pilih node dari daftar.";
      error.hidden = false;
      return;
    }
    select(node, false);
    $("jelajah").scrollIntoView();
  }

  rail.addEventListener("click", event => {
    const button = event.target.closest("button[data-node]");
    if (button) select(byId.get(button.dataset.node));
  });
  rail.addEventListener("keydown", event => {
    const button = event.target.closest("button[data-node]");
    if (!button) return;
    const i = visibleNodes.indexOf(byId.get(button.dataset.node));
    const destination = {ArrowUp: i - 1, ArrowDown: i + 1, Home: 0, End: visibleNodes.length - 1};
    if (!(event.key in destination)) return;
    event.preventDefault();
    const index = Math.max(0, Math.min(visibleNodes.length - 1, destination[event.key]));
    select(visibleNodes[index]);
    rail.querySelectorAll("button")[index].focus();
  });
  group.addEventListener("change", () => {
    search.value = "";
    select(groups.get(group.value)[0]);
    drawRail();
  });
  search.addEventListener("input", drawRail);
  prev.addEventListener("click", () => select(visibleNodes[visibleNodes.indexOf(active) - 1]));
  next.addEventListener("click", () => select(visibleNodes[visibleNodes.indexOf(active) + 1]));
  $("node-focus").addEventListener("click", () => $("node-detail").focus());
  addEventListener("hashchange", selectFromHash);
  $("node-explorer").hidden = false;
  select(data.nodes[0], false);
  drawRail();
  selectFromHash();
})();
