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

function showText(text, entry) {
  const el = bar();
  if (!el) return;
  const span = document.createElement("span");
  span.textContent = text;
  el.replaceChildren(span);
  if (entry) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = uiText("undo");
    button.dataset.testid = "undo-button";
    button.addEventListener("click", () => restore(entry));
    el.append(button);
  }
  el.hidden = false;
}

function failureText(data, entry) {
  // The server may have purged the row and lost its title; the bar still knows it.
  if (data.error === "undo_expired") return uiText("undo_expired", { title: entry.title });
  return data.message || uiText("undo_failed");
}

async function restore(entry) {
  const { status, data } = await api("POST", `/api/recipes/${entry.id}/restore`);
  sessionStorage.removeItem(KEY);
  if (status === 200) {
    const text = data.renamed_to
      ? uiText("restored_renamed", { title: data.title, renamed: data.renamed_to })
      : uiText("restored", { title: data.title });
    sessionStorage.setItem(NOTICE_KEY, text);
  } else {
    sessionStorage.setItem(NOTICE_KEY, failureText(data, entry));
  }
  window.location.reload();
}

function show(entry) {
  const left = entry.until - Date.now();
  if (left <= 0) {
    sessionStorage.removeItem(KEY);
    return;
  }
  showText(uiText("deleted", { title: entry.title }), entry);
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
    showText(notice, null);
    setTimeout(hideBar, 6000);
    return;
  }
  const raw = sessionStorage.getItem(KEY);
  if (raw) show(JSON.parse(raw));
}

resume();
