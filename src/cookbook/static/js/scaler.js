// Servings scaler (LLD section 8): pure, display only.
const METRIC = new Set(["g", "gram", "grams", "ml", "millilitre", "millilitres", "milliliter", "milliliters"]);
const FRACTIONS = [["", 0, 1], ["¼", 1, 4], ["⅓", 1, 3], ["½", 1, 2], ["⅔", 2, 3], ["¾", 3, 4]];
const WHOLE_STEP = [["", 0, 1]];
const COUNTED = [["", 0, 1], ["½", 1, 2]];
const CANDIDATES = { fraction: FRACTIONS, counted: COUNTED, metric: WHOLE_STEP };
const SMALLEST = { metric: { whole: 1, frac: "" }, counted: { whole: 0, frac: "½" }, fraction: { whole: 0, frac: "¼" } };
const PLURALS = [
  ["cup", "cups"], ["tablespoon", "tablespoons"], ["teaspoon", "teaspoons"], ["gram", "grams"],
  ["millilitre", "millilitres"], ["milliliter", "milliliters"], ["clove", "cloves"],
  ["slice", "slices"], ["pinch", "pinches"], ["can", "cans"], ["piece", "pieces"],
];

/**
 * Rounding kind for a unit (LLD §8.5).
 * @param {string | null | undefined} unit
 * @returns {"metric" | "counted" | "fraction"}
 */
export function kindFor(unit) {
  const u = String(unit ?? "").trim().toLowerCase();
  if (u === "") return "counted";
  return METRIC.has(u) ? "metric" : "fraction";
}

// Distance from remainder rem/d to a/b, scaled by d·b (compare after cross-multiplying by the other b).
function distance(rem, d, a, b) {
  return Math.abs(rem * b - a * d);
}

function nearest(rem, d, list) {
  // list ascends; the 1 (carry) candidate is appended. Ties go to the larger.
  const all = [...list, ["", 1, 1]];
  let best = all[0];
  for (const cand of all.slice(1)) {
    const lhs = distance(rem, d, cand[1], cand[2]) * best[2];
    const rhs = distance(rem, d, best[1], best[2]) * cand[2];
    if (lhs <= rhs) best = cand;
  }
  return best;
}

/**
 * Scale num/den from one number of servings to another, rounded for the kitchen (LLD §8.5).
 * @param {number} num
 * @param {number} den
 * @param {number} fromServings
 * @param {number} toServings
 * @param {"metric" | "counted" | "fraction"} kind
 * @returns {{whole: number, frac: "" | "¼" | "⅓" | "½" | "⅔" | "¾"}}
 */
export function scale(num, den, fromServings, toServings, kind) {
  const n = num * toServings;
  const d = den * fromServings;
  let whole = Math.floor(n / d);
  const best = nearest(n - whole * d, d, CANDIDATES[kind] || FRACTIONS);
  if (best[1] === 1 && best[2] === 1) return finish(whole + 1, "", kind);
  return finish(whole, best[0], kind);
}

function finish(whole, frac, kind) {
  if (whole === 0 && frac === "") return { ...(SMALLEST[kind] || SMALLEST.fraction) };
  return { whole, frac };
}

/**
 * Amount text for a scaled result, e.g. "1½", "½", "3", "84".
 * @param {{whole: number, frac: string}} result
 * @returns {string}
 */
export function formatAmount(result) {
  if (result.whole === 0) return result.frac || "0";
  return `${result.whole}${result.frac}`;
}

/**
 * Singular or plural form of a known unit ("cups" <-> "cup"); unknown units unchanged.
 * @param {string} unit
 * @param {{whole: number, frac: string}} result
 * @returns {string}
 */
export function unitFor(unit, result) {
  const key = String(unit ?? "").trim().toLowerCase();
  const pair = PLURALS.find((p) => p[0] === key || p[1] === key);
  if (!pair) return unit;
  return isMany(result) ? pair[1] : pair[0];
}

const IRREGULAR = { tomato: "tomatoes", potato: "potatoes", loaf: "loaves", leaf: "leaves", mango: "mangoes", chilli: "chillies" };
const SINGULAR_ONLY = { cookies: "cookie", brownies: "brownie", pies: "pie" };
const SINGULARS = { ...Object.fromEntries(Object.entries(IRREGULAR).map(([one, many]) => [many, one])), ...SINGULAR_ONLY };
// Names that read the same for one or many.
const INVARIANT = new Set([
  "fish", "sheep", "deer", "salmon", "trout", "cod", "tuna", "garlic", "rice", "thyme", "rosemary",
  "parsley", "basil", "sage", "mint", "molasses", "hummus", "couscous", "asparagus", "series", "species",
]);
// A leading word that is the thing counted: "clove garlic" -> "cloves garlic".
const COUNT_WORDS = new Set([
  "clove", "slice", "pinch", "can", "piece", "sprig", "head", "stick", "bunch", "sheet", "stalk",
  "rasher", "fillet", "knob", "handful", "jar", "tin", "packet", "bag", "bottle",
]);
const UNSAFE = /[,(]|\b(of|to|for|or|and)\b/i;

function pluralWord(word) {
  const lower = word.toLowerCase();
  if (IRREGULAR[lower]) return IRREGULAR[lower];
  if (lower.endsWith("s")) return word;
  if (/[^aeiou]y$/.test(lower)) return `${word.slice(0, -1)}ies`;
  if (/(ch|sh|x|z)$/.test(lower)) return `${word}es`;
  return `${word}s`;
}

function singularWord(word) {
  const lower = word.toLowerCase();
  if (SINGULARS[lower]) return SINGULARS[lower];
  if (/[^aeiou]ies$/.test(lower)) return `${word.slice(0, -3)}y`;
  if (/(ch|sh|x|zz|ss)es$/.test(lower)) return word.slice(0, -2);
  if (/(ss|us|is)$/.test(lower) || !lower.endsWith("s")) return word;
  return word.slice(0, -1);
}

function headIndex(words) {
  const first = words[0].toLowerCase();
  const counted = COUNT_WORDS.has(first) || COUNT_WORDS.has(singularWord(first));
  return words.length > 1 && counted ? 0 : words.length - 1;
}

function isMany(result) {
  return result.whole > 1 || (result.whole === 1 && result.frac !== "");
}

/**
 * Name of a counted item (no unit) for a scaled amount: plural above 1, singular at 1 or less.
 * Conservative: names with a comma, bracket or of/to/for/or/and, and names that read the same
 * for one or many, are returned unchanged. Display only.
 * @param {string} name saved ingredient name
 * @param {string} unit saved unit ("" for counted items)
 * @param {{whole: number, frac: string}} result from scale()
 * @returns {string}
 */
export function nameFor(name, unit, result) {
  const text = String(name ?? "").trim();
  if (!text || kindFor(unit) !== "counted" || UNSAFE.test(text)) return name;
  const words = text.split(/\s+/);
  const at = headIndex(words);
  if (INVARIANT.has(words[at].toLowerCase())) return name;
  words[at] = isMany(result) ? pluralWord(words[at]) : singularWord(words[at]);
  return words.join(" ");
}

window.cookbookScaler = { kindFor, scale, formatAmount, unitFor, nameFor };
