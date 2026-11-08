const JSON_HEADERS = { "Content-Type": "application/json" };

async function request(path, options = {}) {
  const response = await fetch(path, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail ? String(payload.detail) : `HTTP ${response.status}`);
  }
  return payload;
}

export const get = (path) => request(path);

export const post = (path, body) => request(path, { method: "POST", headers: JSON_HEADERS, body: JSON.stringify(body) });

export const patch = (path, body) => request(path, { method: "PATCH", headers: JSON_HEADERS, body: JSON.stringify(body) });

export const remove = (path) => request(path, { method: "DELETE" });

export const query = (path, params) => request(`${path}?${new URLSearchParams(params)}`);
