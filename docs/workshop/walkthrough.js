"use strict";

(() => {
  const svgNS = "http://www.w3.org/2000/svg";
  const motion = matchMedia("(prefers-reduced-motion: reduce)");

  function installFlow(list) {
    const items = [...list.children];
    if (items.length < 2) return;
    const stage = document.createElement("div");
    stage.className = "flow-stage";
    const wire = document.createElementNS(svgNS, "svg");
    wire.classList.add("flow-wire");
    wire.setAttribute("aria-hidden", "true");
    list.before(stage);
    stage.append(wire, list);
    list.dataset.enhanced = "";
    list.setAttribute("role", "list");

    const figure = stage.closest("figure");
    const trace = figure?.querySelector(".trace");
    const steps = trace ? [...trace.children] : [];
    const controls = figure?.querySelector(".controls");
    const slider = controls?.querySelector("input");
    const back = controls?.querySelector("[data-prev]");
    const next = controls?.querySelector("[data-next]");
    const play = controls?.querySelector("[data-play]");
    const reading = trace ? null : document.createElement("div");
    if (reading) {
      reading.className = "flow-reading";
      reading.setAttribute("role", "status");
      stage.after(reading);
    }

    const buttons = items.map((item, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "flow-choice";
      const mark = document.createElement("span");
      mark.className = "flow-mark";
      mark.setAttribute("aria-hidden", "true");
      mark.textContent = String(index + 1).padStart(2, "0");
      button.append(mark, ...item.querySelectorAll(":scope > :not(.hop)"));
      item.prepend(button);
      return button;
    });

    const paths = items.slice(1).map(() => document.createElementNS(svgNS, "path"));
    wire.append(...paths);
    const redraw = () => {
      const box = stage.getBoundingClientRect();
      if (!box.width || !box.height) return;
      wire.setAttribute("viewBox", `0 0 ${box.width} ${box.height}`);
      const vertical = getComputedStyle(list).flexDirection === "column";
      const points = buttons.map(button => {
        const dot = button.querySelector(".flow-mark").getBoundingClientRect();
        return [dot.left - box.left + dot.width / 2, dot.top - box.top + dot.height / 2, dot.width / 2];
      });
      paths.forEach((path, i) => {
        const [ax, ay, ar] = points[i];
        const [bx, by, br] = points[i + 1];
        if (vertical) {
          const a = ay + ar;
          const b = by - br;
          path.setAttribute("d", `M${ax},${a} C${ax + 13},${a + 9} ${bx + 13},${b - 9} ${bx},${b}`);
        } else {
          const a = ax + ar;
          const b = bx - br;
          const mid = (a + b) / 2;
          path.setAttribute("d", `M${a},${ay} C${mid},${ay + 20} ${mid},${by - 20} ${b},${by}`);
        }
      });
    };
    new ResizeObserver(redraw).observe(stage);
    redraw();

    let active = 0;
    let timer = null;
    function show(index) {
      active = index;
      items.forEach((item, i) => {
        if (index === i) item.setAttribute("aria-current", "step");
        else item.removeAttribute("aria-current");
        buttons[i].tabIndex = i === index ? 0 : -1;
        if (steps[i]) steps[i].hidden = index !== i;
        paths[i]?.toggleAttribute("data-visited", i < index);
      });
      if (reading) {
        const label = document.createElement("span");
        label.textContent = `Langkah ${index + 1} dari ${items.length}`;
        const title = document.createElement("strong");
        title.textContent = buttons[index].querySelector("strong").textContent;
        const description = document.createElement("p");
        const summary = buttons[index].querySelector("span:not(.flow-mark)").textContent;
        const handoff = items[index].querySelector(".hop")?.textContent;
        description.textContent = items[index].dataset.read ??
          (handoff ? `${summary}. Berikutnya: ${handoff.toLocaleLowerCase("id")}.` : summary);
        reading.replaceChildren(label, title, description);
      }
      if (slider) {
        slider.value = String(index + 1);
        slider.setAttribute("aria-valuetext", `Langkah ${index + 1} dari ${items.length}`);
        back.disabled = index === 0;
        next.disabled = index === items.length - 1;
      }
    }
    function stop() {
      clearInterval(timer);
      timer = null;
      if (play) play.textContent = "Putar alur";
    }
    buttons.forEach((button, index) => {
      button.addEventListener("click", () => { stop(); show(index); });
      button.addEventListener("keydown", event => {
        const offsets = {ArrowLeft: -1, ArrowUp: -1, ArrowRight: 1, ArrowDown: 1};
        const requested = event.key === "Home" ? 0
          : event.key === "End" ? buttons.length - 1
            : index + (offsets[event.key] ?? 0);
        if (!(event.key in offsets) && event.key !== "Home" && event.key !== "End") return;
        event.preventDefault();
        const destination = Math.min(buttons.length - 1, Math.max(0, requested));
        stop();
        show(destination);
        buttons[destination].focus();
      });
    });
    if (controls) {
      back.addEventListener("click", () => { stop(); show(active - 1); });
      next.addEventListener("click", () => { stop(); show(active + 1); });
      slider.addEventListener("input", () => { stop(); show(Number(slider.value) - 1); });
      play.addEventListener("click", () => {
        if (timer !== null) { stop(); return; }
        if (active === items.length - 1) show(0);
        play.textContent = "Jeda";
        timer = setInterval(() => {
          show(active + 1);
          if (active === items.length - 1) stop();
        }, 2400);
      });
      motion.addEventListener("change", () => {
        if (motion.matches) stop();
        play.hidden = motion.matches;
      });
      play.hidden = motion.matches;
      controls.hidden = false;
    }
    show(0);
  }

  document.querySelectorAll(".flow").forEach(installFlow);

  const chapters = [...document.querySelectorAll(".toc a[href^='#']")]
    .map(link => [link, document.getElementById(link.hash.slice(1))])
    .filter(([, section]) => section);
  if (chapters.length && "IntersectionObserver" in window) {
    const observer = new IntersectionObserver(entries => {
      const reached = entries.filter(entry => entry.isIntersecting).at(-1)?.target;
      if (!reached) return;
      chapters.forEach(([link, section]) => {
        if (section === reached) link.setAttribute("aria-current", "location");
        else link.removeAttribute("aria-current");
      });
    }, {rootMargin: "0px 0px -65% 0px"});
    chapters.forEach(([, section]) => observer.observe(section));
  }
})();
