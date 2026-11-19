"use strict";

const trace = document.querySelector("[data-trace]");
const steps = [...trace.querySelectorAll(".trace > li")];
const nodes = [...trace.querySelectorAll(".flow > li")];
const controls = trace.querySelector(".controls");
const range = controls.querySelector("input");
const back = controls.querySelector("[data-prev]");
const next = controls.querySelector("[data-next]");
const play = controls.querySelector("[data-play]");
const motion = matchMedia("(prefers-reduced-motion: reduce)");

let index = 0;
let timer = null;

function show(step) {
  index = step;
  for (const [i, item] of steps.entries()) {
    item.hidden = index !== i;
    if (index === i) nodes[i].setAttribute("aria-current", "step");
    else nodes[i].removeAttribute("aria-current");
  }
  range.value = String(index + 1);
  range.setAttribute("aria-valuetext", `Langkah ${index + 1} dari ${steps.length}`);
  back.disabled = index === 0;
  next.disabled = index === steps.length - 1;
}

function stop() {
  clearInterval(timer);
  timer = null;
  play.textContent = "Putar alur";
}

back.addEventListener("click", () => { stop(); show(index - 1); });
next.addEventListener("click", () => { stop(); show(index + 1); });
range.addEventListener("input", () => { stop(); show(Number(range.value) - 1); });
play.addEventListener("click", () => {
  if (timer !== null) {
    stop();
    return;
  }
  if (index === steps.length - 1) show(0);
  play.textContent = "Jeda";
  timer = setInterval(() => {
    show(index + 1);
    if (index === steps.length - 1) stop();
  }, 2400);
});
motion.addEventListener("change", () => {
  if (motion.matches) stop();
  play.hidden = motion.matches;
});

show(0);
play.hidden = motion.matches;
controls.hidden = false;
