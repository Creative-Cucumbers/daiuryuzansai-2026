"use strict";

let works = [];
const grid = document.querySelector("#works-grid");
const count = document.querySelector("#work-count");
const dialog = document.querySelector("#work-dialog");
const visuals = new Set(["lime", "lilac", "orange", "pink", "blue", "yellow"]);
let lastTrigger;
const rotationDelay = 60_000;
const rotationDuration = 600;
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const activePointers = new Set();
let rotationTimer;
let rotationAnimations = [];
let keyboardNavigation = false;

function finishRotation() {
  rotationAnimations.forEach((animation) => animation.cancel());
  rotationAnimations = [];
}

function scheduleRotation() {
  window.clearTimeout(rotationTimer);
  rotationTimer = window.setTimeout(rotateWorks, rotationDelay);
}

function rotateWorks() {
  // Start a fresh idle period even when a pause condition prevents this turn.
  scheduleRotation();
  if (document.hidden || dialog.open || activePointers.size
      || (keyboardNavigation && grid.contains(document.activeElement))) return;
  const cards = [...grid.querySelectorAll(".work-card")];
  if (!cards.length) return;
  const firstRow = cards[0].getBoundingClientRect();
  if (firstRow.top < 0 || firstRow.top >= window.innerHeight) return;
  const columns = getComputedStyle(grid).gridTemplateColumns.split(" ").length;
  if (cards.length <= columns) return;

  finishRotation();
  const positions = cards.map((card) => card.getBoundingClientRect());
  // Move existing nodes so their numbers, event handlers and identity stay intact.
  cards.slice(0, columns).forEach((card) => grid.append(card));
  if (reducedMotion.matches) return;
  rotationAnimations = cards.map((card, index) => {
    const after = card.getBoundingClientRect();
    const before = positions[index];
    // The outgoing row fades in at the end rather than crossing the whole grid.
    const frames = index < columns
      ? [{ opacity: 0 }, { opacity: 1 }]
      : [{ transform: `translate(${before.left - after.left}px, ${before.top - after.top}px)` },
        { transform: "translate(0, 0)" }];
    return card.animate(frames, {
      duration: rotationDuration,
      easing: "cubic-bezier(.22, 1, .36, 1)",
    });
  });
}

function recordActivity() {
  finishRotation();
  scheduleRotation();
}

document.addEventListener("pointerdown", (event) => {
  keyboardNavigation = false;
  activePointers.add(event.pointerId);
  recordActivity();
}, { passive: true });
function releasePointer(event) {
  activePointers.delete(event.pointerId);
  recordActivity();
}
document.addEventListener("pointerup", releasePointer, { passive: true });
document.addEventListener("pointercancel", releasePointer, { passive: true });
document.addEventListener("keydown", () => {
  keyboardNavigation = true;
  recordActivity();
});
["pointermove", "click", "wheel", "scroll", "focusin", "focusout"].forEach((type) => {
  document.addEventListener(type, recordActivity, { passive: true, capture: true });
});
window.addEventListener("resize", recordActivity);
window.addEventListener("blur", () => {
  activePointers.clear();
  recordActivity();
});
document.addEventListener("visibilitychange", () => {
  activePointers.clear();
  recordActivity();
});
reducedMotion.addEventListener("change", finishRotation);

function makeElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function visualName(work) {
  if (visuals.has(work.visual)) return work.visual;
  const index = Number.parseInt(work.id?.slice(-2), 16) % visuals.size;
  return [...visuals][index] || "lime";
}

function makeArtwork(work) {
  const art = makeElement("span", `work-art art-${visualName(work)}`);
  art.setAttribute("aria-hidden", "true");
  const character = makeElement("span", "art-character");
  character.append(makeElement("span", "character-symbol", work.symbol || "✳"));
  character.append(makeElement("span", "character-eyes"));
  art.append(character, makeElement("span", "art-label", "A CONVERSATION PIECE"));
  if (work.screenshot) {
    const screenshot = makeElement("img", "work-screenshot");
    screenshot.alt = "";
    screenshot.decoding = "async";
    screenshot.addEventListener("error", () => {
      art.classList.remove("has-screenshot");
      screenshot.remove();
    });
    art.classList.add("has-screenshot");
    screenshot.src = work.screenshot;
    art.append(screenshot);
  }
  return art;
}

function makeAppPreview(work) {
  const art = makeArtwork(work);
  const url = publicUrl(work.url);
  if (work.sample || !url) return art;
  const link = makeElement("a", "work-preview");
  link.href = url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.setAttribute("aria-label", `${work.title}を開く（新しいタブ）`);
  link.append(art);
  return link;
}

function renderWorks() {
  const fragment = document.createDocumentFragment();
  works.forEach((work, index) => {
    const article = makeElement("article", "work-card");
    const button = makeElement("button", "work-open");
    button.type = "button";
    button.setAttribute("aria-haspopup", "dialog");
    button.setAttribute("aria-label", `${work.title}の作品紹介を見る`);
    const art = makeArtwork(work);
    const number = String(index + 1).padStart(2, "0");
    art.append(makeElement("span", "work-number", `NO. ${number}`));
    art.append(makeElement("span", "work-initials", work.initials || work.author));
    if (work.sample) art.append(makeElement("span", "sample-label", "SAMPLE"));
    const body = makeElement("span", "work-body");
    const heading = makeElement("span", "work-heading");
    const icon = makeElement("span", "work-arrow", "＋");
    icon.setAttribute("aria-hidden", "true");
    heading.append(makeElement("span", "work-name", work.title), icon);
    body.append(heading);
    body.append(makeElement("span", "sr-only", `制作者 ${work.initials || work.author || ""}`));
    button.append(art, body);
    button.addEventListener("click", () => openWork(work, button));
    const cardHeading = makeElement("h3", "work-card-heading");
    cardHeading.append(button);
    article.append(cardHeading);
    fragment.append(article);
  });
  grid.replaceChildren(fragment);
  if (!works.length) grid.append(makeElement("p", "empty-state", "作品は準備中です。"));
  count.textContent = `${String(works.length).padStart(2, "0")} WORKS`;
  scheduleRotation();
}

function publicUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}

function openWork(work, trigger) {
  recordActivity();
  lastTrigger = trigger;
  document.querySelector("#dialog-title").textContent = work.title;
  document.querySelector("#dialog-category").textContent = work.sample ? "サンプル作品" : (work.category || "学生作品");
  document.querySelector("#dialog-description").textContent = work.description;
  document.querySelector("#dialog-prompt").textContent = `「${work.prompt}」`;
  document.querySelector(".prompt-box").hidden = !work.prompt;
  document.querySelector("#dialog-credit").textContent = work.initials || work.author;
  document.querySelector("#dialog-art").replaceChildren(makeAppPreview(work));
  const link = document.querySelector("#dialog-link");
  const unavailable = document.querySelector("#dialog-unavailable");
  const url = publicUrl(work.url);
  link.hidden = work.sample || !url;
  link.removeAttribute("href");
  if (!link.hidden) link.href = url;
  unavailable.hidden = !link.hidden;
  unavailable.textContent = work.sample
    ? "展示準備中のサンプルです。実際のチャットボットには接続しません。"
    : "チャットボットの公開を準備しています。";
  dialog.showModal();
  document.body.classList.add("dialog-is-open");
}

document.querySelector(".dialog-close").addEventListener("click", () => dialog.close());
dialog.addEventListener("click", (event) => {
  if (event.target !== dialog) return;
  const bounds = dialog.getBoundingClientRect();
  if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
});
dialog.addEventListener("close", () => {
  document.body.classList.remove("dialog-is-open");
  lastTrigger?.focus();
  scheduleRotation();
});

async function loadWorks() {
  count.textContent = "読み込み中…";
  try {
    const response = await fetch("./data/works.json", { cache: "no-cache" });
    if (!response.ok) throw new Error(`作品データを読み込めません (${response.status})`);
    const data = await response.json();
    if (!Array.isArray(data)) throw new Error("作品データの形式が正しくありません");
    works = data;
    renderWorks();
  } catch (error) {
    console.error(error);
    count.textContent = "";
    const message = makeElement("p", "empty-state", "作品一覧を読み込めませんでした。再読み込みしてください。");
    message.setAttribute("role", "alert");
    grid.replaceChildren(message);
  }
}

loadWorks();
