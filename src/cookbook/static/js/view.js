import { api, uiText } from "./api.js";
import { startUndo } from "./undo.js";

const button = document.querySelector('[data-testid="delete"]');

async function deleteRecipe() {
  button.disabled = true;
  const { status, data } = await api("DELETE", `/api/recipes/${button.dataset.recipeId}`);
  if (status === 200) {
    startUndo(data.id, data.title, data.undo_seconds);
    window.location.assign("/");
    return;
  }
  button.disabled = false;
  const message = document.querySelector('[data-testid="menu-message"]');
  message.textContent = data.message || uiText("network");
  message.hidden = false;
}

button?.addEventListener("click", deleteRecipe);
