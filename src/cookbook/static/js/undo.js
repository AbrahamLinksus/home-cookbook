import { api, uiText } from "./api.js";

const KEY = "cookbook.undo";
const NOTICE_KEY = "cookbook.undo-notice";
let timer = null;

function bar() {
  return document.querySelector('[data-testid="undo-bar"]');
}

function hideBar() {
  const el = bar();
  if (el) {
    el.hidden = true;
    el.replaceChildren();
  }
}

function showText(text, withButton, id) {
  const el = bar();
  if (!el) return;
  const span = document.createElement("span");
  span.textContent = text;
  el.replaceChildren(span);
  if (withButton) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = uiText("undo");
    button.dataset.testid = "undo-button";
    button.addEventListener("click", () => restore(id));
    el.append(button);
  }
  el.hidden = false;
}

async function restore(id) {
  const { status, data } = await api("POST", `/api/recipes/${id}/restore`);
  sessionStorage.removeItem(KEY);
  if (status === 200) {
    const text = data.renamed_to
      ? uiText("restored_renamed", { title: data.title, renamed: data.renamed_to })
      : uiText("restored", { title: data.title });
    sessionStorage.setItem(NOTICE_KEY, text);
  } else {
    sessionStorage.setItem(NOTICE_KEY, data.message || uiText("undo_failed"));
  }
  window.location.reload();
}

function show(entry) {
  const left = entry.until - Date.now();
  if (left <= 0) {
    sessionStorage.removeItem(KEY);
    return;
  }
  showText(uiText("deleted", { title: entry.title }), true, entry.id);
  clearTimeout(timer);
  timer = setTimeout(() => {
    sessionStorage.removeItem(KEY);
    hideBar();
  }, left);
}

/**
 * Show the undo bar for a just-deleted recipe, on this and the next pages.
 * @param {number} id
 * @param {string} title
 * @param {number} seconds
 */
export function startUndo(id, title, seconds) {
  const entry = { id, title, until: Date.now() + seconds * 1000 };
  sessionStorage.setItem(KEY, JSON.stringify(entry));
  show(entry);
}

function resume() {
  const notice = sessionStorage.getItem(NOTICE_KEY);
  if (notice) {
    sessionStorage.removeItem(NOTICE_KEY);
    showText(notice, false);
    setTimeout(hideBar, 6000);
    return;
  }
  const raw = sessionStorage.getItem(KEY);
  if (raw) show(JSON.parse(raw));
}

resume();
