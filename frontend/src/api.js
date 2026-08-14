const TOKEN_KEY = "ai_drama_token";

export const state = {
  token: localStorage.getItem(TOKEN_KEY) || "",
  balance: 0,
};

export function setToken(token) {
  state.token = token;
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  state.token = "";
  state.balance = 0;
  localStorage.removeItem(TOKEN_KEY);
}

async function request(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const resp = await fetch(`/api${path}`, { ...options, headers });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(data.detail || data.message || resp.statusText);
  return data;
}

export const api = {
  register: (username, password) => request("/auth/register", { method: "POST", body: JSON.stringify({ username, password }) }),
  login: (username, password) => request("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  balance: () => request("/billing/balance"),
  templates: () => request("/projects/templates"),
  estimate: (payload) => request("/projects/estimate", { method: "POST", body: JSON.stringify(payload) }),
  createProject: (payload) => request("/projects", { method: "POST", body: JSON.stringify(payload) }),
  listProjects: () => request("/projects"),
  getProject: (id) => request(`/projects/${id}`),
  episodesStatus: (id) => request(`/projects/${id}/episodes`),
  resume: (id) => request(`/projects/${id}/resume`, { method: "POST" }),
  novelUrl: (id) => `/api/delivery/${id}/novel`,
  videoUrl: (id, ep = 1) => `/api/delivery/${id}/video/${ep}`,
  archiveUrl: (id) => `/api/delivery/${id}/archive`,
  collectionUrl: (id) => `/api/delivery/${id}/collection`,
  metadataUrl: (id) => `/api/delivery/${id}/metadata`,
  eventsUrl: (id) => `/api/projects/${id}/events?token=${encodeURIComponent(state.token)}`,
};
