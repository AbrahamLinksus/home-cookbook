let texts = null;

/**
 * A user-facing text from web/messages.py, rendered by base.html into <body data-texts>.
 * @param {string} key
 * @param {Record<string, string>} [values] fills "{name}" placeholders
 * @returns {string}
 */
export function uiText(key, values = {}) {
  texts ??= JSON.parse(document.body.dataset.texts || "{}");
  const template = texts[key] || "";
  return template.replace(/\{(\w+)\}/g, (match, name) => (name in values ? values[name] : match));
}

/**
 * Send one request to the app. Never throws on HTTP errors.
 * @param {string} method
 * @param {string} url
 * @param {object | FormData} [body]
 * @returns {Promise<{status: number, data: object}>}
 */
export async function api(method, url, body) {
  const options = { method, headers: { Accept: "application/json" } };
  if (body instanceof FormData) {
    options.body = body;
  } else if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  try {
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));
    return { status: response.status, data };
  } catch {
    return {
      status: 0,
      data: { error: "network", message: uiText("network") },
    };
  }
}
