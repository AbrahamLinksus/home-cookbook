import { api, uiText } from "./api.js";
import { setFavourite, paintStar } from "./favourite.js";
import { startUndo } from "./undo.js";
import { kindFor, scale, formatAmount, unitFor, nameFor } from "./scaler.js";

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

// Servings scaling: display only, always computed from the saved amounts.
const MAX_SERVINGS = 1000; // same limit as domain/rules.py MAX_SERVINGS (LLD §1.2)
const input = document.querySelector('[data-testid="servings-input"]');
const note = document.querySelector('[data-testid="scaled-note"]');
const status = document.querySelector('[data-testid="scale-status"]');
const lines = [...document.querySelectorAll('[data-testid="ingredient-line"]')];

function scaledText(line, from, to) {
  const { num, den, unit, name } = line.dataset;
  if (to === from || num === "" || den === "") return null;
  const result = scale(Number(num), Number(den), from, to, kindFor(unit));
  const parts = [formatAmount(result), unitFor(unit, result), nameFor(name, unit, result)];
  return parts.filter(Boolean).join(" ");
}

function savedText(line) {
  const { text, unit, name } = line.dataset;
  return [text, unit, name].filter(Boolean).join(" ");
}

function servingsText(key, n) {
  return uiText(n === 1 ? `${key}_one` : key, { n: String(n) });
}

function applyServings(to) {
  const from = Number(input.dataset.saved);
  input.value = String(to);
  for (const line of lines) line.textContent = scaledText(line, from, to) ?? savedText(line);
  note.hidden = to === from;
  note.querySelector('[data-testid="scaled-text"]').textContent = servingsText("scaled_from", from);
  status.textContent = servingsText("scaled_to", to);
}

function onServingsChange(raw) {
  const text = String(raw).trim();
  const value = Number(text);
  if (!/^\d+$/.test(text) || value < 1 || value > MAX_SERVINGS) {
    input.value = input.dataset.current;
    return;
  }
  input.dataset.current = String(value);
  applyServings(value);
}

if (input) {
  input.dataset.current = input.dataset.saved;
  input.addEventListener("change", () => onServingsChange(input.value));
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") onServingsChange(input.value); });
  document.querySelector('[data-testid="servings-down"]').addEventListener("click",
    () => onServingsChange(Number(input.dataset.current) - 1));
  document.querySelector('[data-testid="servings-up"]').addEventListener("click",
    () => onServingsChange(Number(input.dataset.current) + 1));
  note.querySelector('[data-testid="reset-scale"]').addEventListener("click",
    () => onServingsChange(input.dataset.saved));
}

const star = document.querySelector('[data-testid="star"]');
star?.addEventListener("click", async () => {
  const next = star.getAttribute("aria-pressed") !== "true";
  star.disabled = true;
  const { ok } = await setFavourite(star.dataset.id, next);
  if (ok) paintStar(star, next);
  star.disabled = false;
});
