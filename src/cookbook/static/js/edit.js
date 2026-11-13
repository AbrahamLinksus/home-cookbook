import { api, uiText } from "./api.js";

const form = document.getElementById("recipe-form");
const ingredientRows = document.getElementById("ingredient-rows");
const stepRows = document.getElementById("step-rows");
const saveButton = form.querySelector('[data-testid="save"]');
let leaving = false;

function addRow(container, templateId, values) {
  const row = document.getElementById(templateId).content.firstElementChild.cloneNode(true);
  for (const input of row.querySelectorAll("[data-field]")) {
    input.value = values[input.dataset.field] ?? "";
  }
  container.append(row);
  return row;
}

function addIngredient(values = {}) {
  return addRow(ingredientRows, "ingredient-template", values);
}

function addStep(text = "") {
  return addRow(stepRows, "step-template", { step: text });
}

/** Keep each field's error key, step number and move buttons in step with its position. */
function renumber() {
  [...ingredientRows.children].forEach((row, i) => {
    for (const input of row.querySelectorAll("[data-field]")) {
      input.dataset.key = `ingredients.${i}.${input.dataset.field}`;
    }
  });
  [...stepRows.children].forEach((row, i) => {
    row.querySelector(".step-num").textContent = String(i + 1);
    row.querySelector("[data-field]").dataset.key = `steps.${i}`;
  });
  for (const container of [ingredientRows, stepRows]) {
    for (const row of container.children) {
      row.querySelector('[data-action="up"]').disabled = row === container.firstElementChild;
      row.querySelector('[data-action="down"]').disabled = row === container.lastElementChild;
    }
  }
}

function readForm() {
  const value = (el) => el.value;
  return {
    title: form.elements.title.value,
    servings: form.elements.servings.value,
    ingredients: [...ingredientRows.children].map((row) => ({
      amount: value(row.querySelector('[data-field="amount"]')),
      unit: value(row.querySelector('[data-field="unit"]')),
      name: value(row.querySelector('[data-field="name"]')),
    })),
    steps: [...stepRows.children].map((row) => value(row.querySelector("[data-field]"))),
  };
}

function fill(data) {
  form.elements.title.value = data.title ?? "";
  form.elements.servings.value = data.servings ?? "";
  for (const item of data.ingredients?.length ? data.ingredients : [{}]) addIngredient(item);
  for (const text of data.steps?.length ? data.steps : [""]) addStep(text);
  renumber();
}

function clearErrors() {
  for (const el of form.querySelectorAll(".error-text")) el.remove();
  for (const el of form.querySelectorAll(".field-error")) {
    el.classList.remove("field-error");
    el.removeAttribute("aria-invalid");
  }
}

function showError(input, message) {
  const note = document.createElement("div");
  note.className = "error-text";
  note.setAttribute("role", "alert");
  note.textContent = message;
  note.dataset.testid = input.dataset.errorTestid || "field-error";
  input.classList.add("field-error");
  input.setAttribute("aria-invalid", "true");
  const holder = input.closest(".item");
  if (holder) holder.append(note);
  else input.insertAdjacentElement("afterend", note);
}

/**
 * Show messages beside their fields (keys: title, servings, ingredients.<i>.x, steps.<i>;
 * list-level "ingredients"/"steps" go under the section's add button). Any other key falls
 * back to the title so a refused save is never silent.
 */
function showFieldErrors(fields) {
  const inputs = [...form.querySelectorAll("[data-key]")];
  const known = new Set(inputs.map((input) => input.dataset.key));
  let first = null;
  for (const input of inputs) {
    const message = fields[input.dataset.key];
    if (!message) continue;
    showError(input, message);
    first ??= input;
  }
  for (const [key, message] of Object.entries(fields)) {
    if (known.has(key)) continue;
    showError(form.elements.title, message);
    first = form.elements.title;
  }
  first?.focus();
}

async function save() {
  clearErrors();
  saveButton.disabled = true;
  const { status, data } = await api("POST", "/api/recipes", { recipe: readForm() });
  if (status === 201) {
    leaving = true;
    window.location.assign(`/recipes/${data.id}`);
    return;
  }
  saveButton.disabled = false;
  if (status === 409 && data.error === "duplicate_title") {
    showFieldErrors({ title: data.message });
  } else if (status === 422) {
    showFieldErrors(data.fields || {});
  } else {
    showError(form.elements.title, data.message || "");
    form.elements.title.focus();
  }
}

function moveRow(row, direction) {
  const sibling = direction === "up" ? row.previousElementSibling : row.nextElementSibling;
  if (!sibling) return;
  if (direction === "up") sibling.before(row);
  else sibling.after(row);
  renumber();
  row.querySelector(`[data-action="${direction}"]`)?.focus();
}

function onRowClick(event) {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const row = button.closest(".item");
  if (button.dataset.action === "remove") {
    row.remove();
    renumber();
  } else {
    moveRow(row, button.dataset.action);
  }
}

let initial = "";
const isDirty = () => JSON.stringify(readForm()) !== initial;

function cancel() {
  if (isDirty() && !window.confirm(uiText("discard_changes"))) return;
  leaving = true;
  window.location.assign("/");
}

fill(JSON.parse(document.getElementById("form-data").textContent));
initial = JSON.stringify(readForm());
ingredientRows.addEventListener("click", onRowClick);
stepRows.addEventListener("click", onRowClick);
form.querySelector('[data-testid="add-ingredient"]').addEventListener("click", () => {
  addIngredient().querySelector("[data-field]").focus();
  renumber();
});
form.querySelector('[data-testid="add-step"]').addEventListener("click", () => {
  addStep().querySelector("[data-field]").focus();
  renumber();
});
form.querySelector('[data-testid="cancel"]').addEventListener("click", cancel);
form.addEventListener("submit", (event) => {
  event.preventDefault();
  save();
});
window.addEventListener("beforeunload", (event) => {
  if (!leaving && isDirty()) event.preventDefault();
});
