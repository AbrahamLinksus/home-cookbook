import { uiText } from "./api.js";
import { setFavourite } from "./favourite.js";

const DEBOUNCE_MS = 150;

const form = document.querySelector("form.search");
const list = document.getElementById("recipe-list");

/**
 * Fetch the list fragment for the form's current query.
 * @param {HTMLFormElement} searchForm
 * @param {AbortSignal} signal
 * @returns {Promise<string>}
 */
async function fetchFragment(searchForm, signal) {
  const params = new URLSearchParams(new FormData(searchForm));
  const response = await fetch(`/recipes/_list?${params}`, { signal });
  if (!response.ok) throw new Error(String(response.status));
  return response.text();
}

/** Show a short error above the list, replacing the list content. */
function showError(target) {
  const note = document.createElement("p");
  note.className = "error";
  note.setAttribute("role", "alert");
  note.textContent = uiText("search_failed");
  target.replaceChildren(note);
}

function init() {
  if (!form || !list) return;
  let timer = null;
  let controller = null;

  const run = async () => {
    controller?.abort();
    controller = new AbortController();
    try {
      list.innerHTML = await fetchFragment(form, controller.signal);
      const params = new URLSearchParams(new FormData(form));
      history.replaceState(null, "", params.get("q") ? `/?${params}` : "/");
    } catch (error) {
      if (error.name !== "AbortError") showError(list);
    }
  };

  list.addEventListener("click", async (event) => {
    const star = event.target.closest(".star");
    if (!star) return;
    star.disabled = true;
    const id = star.dataset.id;
    const { ok, status } = await setFavourite(id, star.getAttribute("aria-pressed") !== "true");
    if (ok || status === 410) {
      await run();
      list.querySelector(`.star[data-id="${id}"]`)?.focus();
    } else {
      star.disabled = false;
    }
  });

  const schedule = () => {
    clearTimeout(timer);
    timer = setTimeout(run, DEBOUNCE_MS);
  };

  form.addEventListener("input", schedule);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    clearTimeout(timer);
    run();
  });
}

init();
