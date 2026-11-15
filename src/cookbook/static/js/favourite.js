import { api, uiText } from "./api.js";

/** Show a short message in the shared menu-message area. */
function showMessage(text) {
  const message = document.querySelector('[data-testid="menu-message"]');
  if (!message) return;
  message.textContent = text;
  message.hidden = false;
}

/**
 * Set or clear a recipe's star on the server. Shows the right message on failure.
 * @param {string} id
 * @param {boolean} favourite
 * @returns {Promise<{ok: boolean, status: number}>}
 */
export async function setFavourite(id, favourite) {
  const { status, data } = await api("PUT", `/api/recipes/${id}/favourite`, { favourite });
  if (status === 200) return { ok: true, status };
  showMessage(status === 410 ? data.message || uiText("deleted_elsewhere") : uiText("favourite_failed"));
  return { ok: false, status };
}

/** Reflect the star state on a button (symbol, aria-pressed, label). */
export function paintStar(button, favourite) {
  button.setAttribute("aria-pressed", String(favourite));
  button.setAttribute("aria-label", uiText(favourite ? "remove_favourite" : "add_favourite"));
  button.textContent = favourite ? "★" : "☆";
}
