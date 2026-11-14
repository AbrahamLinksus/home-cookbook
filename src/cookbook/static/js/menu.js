import { api, uiText } from "./api.js";

const NOTICE_KEY = "cookbook.import-notice";

function messageBox() {
  return document.querySelector('[data-testid="menu-message"]');
}

function showMessage(text) {
  const box = messageBox();
  if (!box) return;
  box.textContent = text;
  box.hidden = false;
}

async function importFile(input) {
  const file = input.files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  const { status, data } = await api("POST", "/api/import", form);
  input.value = "";
  input.closest("details")?.removeAttribute("open");
  if (status === 200) {
    sessionStorage.setItem(NOTICE_KEY, data.message);
    window.location.reload();
  } else {
    showMessage(data.message || uiText("network"));
  }
}

function start() {
  const notice = sessionStorage.getItem(NOTICE_KEY);
  if (notice) {
    sessionStorage.removeItem(NOTICE_KEY);
    showMessage(notice);
  }
  const input = document.querySelector('[data-testid="import-input"]');
  input?.addEventListener("change", () => importFile(input));
}

start();
