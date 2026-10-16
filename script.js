"use strict";

const works = window.EXHIBITION_WORKS || [];
const grid = document.querySelector("#works-grid");
const count = document.querySelector("#work-count");
const dialog = document.querySelector("#work-dialog");
const visuals = new Set(["lime", "lilac", "orange", "pink", "blue", "yellow"]);
let lastTrigger;

function makeElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function visualName(work) {
  return visuals.has(work.visual) ? work.visual : "lime";
}

function makeArtwork(work) {
  const art = makeElement("div", `work-art art-${visualName(work)}`);
  art.setAttribute("aria-hidden", "true");
  const character = makeElement("div", "art-character");
  character.append(makeElement("span", "character-symbol", work.symbol || "✳"));
  character.append(makeElement("span", "character-eyes"));
  art.append(character, makeElement("span", "art-label", "A CONVERSATION PIECE"));
  return art;
}

function renderWorks(filter = "all") {
  const shown = works.filter((work) => filter === "all" || work.category === filter);
  const fragment = document.createDocumentFragment();
  shown.forEach((work) => {
    const article = makeElement("article", "work-card");
    const button = makeElement("button", "work-open");
    button.type = "button";
    button.setAttribute("aria-haspopup", "dialog");
    button.setAttribute("aria-label", `${work.title}の作品紹介を見る`);
    const art = makeArtwork(work);
    const number = String(works.indexOf(work) + 1).padStart(2, "0");
    art.append(makeElement("span", "work-number", `NO. ${number}`));
    if (work.sample) art.append(makeElement("span", "sample-label", "SAMPLE"));
    const body = makeElement("div", "work-body");
    body.append(makeElement("span", "work-category", work.category));
    const heading = makeElement("div", "work-heading");
    heading.append(makeElement("h3", "", work.title), makeElement("span", "work-arrow", "↗"));
    body.append(heading, makeElement("p", "work-tagline", work.tagline));
    body.append(makeElement("p", "work-author", work.author));
    button.append(art, body);
    button.addEventListener("click", () => openWork(work, button));
    article.append(button);
    fragment.append(article);
  });
  grid.replaceChildren(fragment);
  if (!shown.length) grid.append(makeElement("p", "empty-state", "このカテゴリの作品は準備中です。"));
  count.textContent = `${String(shown.length).padStart(2, "0")} WORKS`;
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
  lastTrigger = trigger;
  document.querySelector("#dialog-title").textContent = work.title;
  document.querySelector("#dialog-category").textContent = `${work.category} / ${work.sample ? "サンプル作品" : "学生作品"}`;
  document.querySelector("#dialog-description").textContent = work.description;
  document.querySelector("#dialog-prompt").textContent = `「${work.prompt}」`;
  document.querySelector("#dialog-credit").textContent = work.author;
  document.querySelector("#dialog-art").replaceChildren(makeArtwork(work));
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

document.querySelectorAll(".filter").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".filter").forEach((filter) => {
      const active = filter === button;
      filter.classList.toggle("is-active", active);
      filter.setAttribute("aria-pressed", String(active));
    });
    renderWorks(button.dataset.filter);
  });
});

document.querySelector(".dialog-close").addEventListener("click", () => dialog.close());
dialog.addEventListener("click", (event) => {
  if (event.target !== dialog) return;
  const bounds = dialog.getBoundingClientRect();
  if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
});
dialog.addEventListener("close", () => {
  document.body.classList.remove("dialog-is-open");
  lastTrigger?.focus();
});

renderWorks();
