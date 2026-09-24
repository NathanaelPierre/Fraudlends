// Thin wrapper around the CipherLab backend (see ../../../backend/app).
// Base URL is configurable via VITE_API_BASE so this frontend can point at
// a deployed backend later; it defaults to the local uvicorn server.
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const TOKEN_KEY = "fraudlens_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, { method = "GET", body, auth = true, form = false } = {}) {
  const headers = {};
  if (!form && body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : form ? body : JSON.stringify(body),
    });
  } catch (err) {
    throw new ApiError(
      "Couldn't reach the CipherLab server. Make sure the backend is running on " + API_BASE + ".",
      0
    );
  }

  let data = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }

  if (!res.ok) {
    const detail = data && data.detail ? data.detail : `Request failed (${res.status}).`;
    const message = typeof detail === "string" ? detail : JSON.stringify(detail);
    throw new ApiError(message, res.status);
  }

  return data;
}

export const api = {
  // auth
  signup: (email, password) => request("/auth/signup", { method: "POST", body: { email, password }, auth: false }),
  login: (email, password) => {
    const form = new URLSearchParams();
    form.set("username", email);
    form.set("password", password);
    return request("/auth/login", { method: "POST", body: form, auth: false, form: true });
  },
  me: () => request("/auth/me"),
  requestPasswordReset: (email) =>
    request("/auth/password-reset/request", { method: "POST", body: { email }, auth: false }),
  verifyResetToken: (token) =>
    request(`/auth/password-reset/verify?token=${encodeURIComponent(token)}`, { auth: false }),
  confirmPasswordReset: (token, new_password) =>
    request("/auth/password-reset/confirm", { method: "POST", body: { token, new_password }, auth: false }),
  confirmEmailVerification: (token) =>
    request("/auth/verify-email/confirm", { method: "POST", body: { token }, auth: false }),
  resendEmailVerification: (email) =>
    request("/auth/verify-email/resend", { method: "POST", body: { email }, auth: false }),

  // checks
  createCheck: (payload) => request("/checks/", { method: "POST", body: payload }),
  createCheckFromImage: (file, { claimedSender, saveCheck = true } = {}) => {
    const form = new FormData();
    form.append("image", file);
    if (claimedSender) form.append("claimed_sender", claimedSender);
    form.append("save_check", String(saveCheck));
    return request("/checks/from-image", { method: "POST", body: form, form: true });
  },
  createCheckFromAudio: (file, { claimedSender, saveCheck = true } = {}) => {
    const form = new FormData();
    form.append("audio", file);
    if (claimedSender) form.append("claimed_sender", claimedSender);
    form.append("save_check", String(saveCheck));
    return request("/checks/from-audio", { method: "POST", body: form, form: true });
  },
  listChecks: ({ limit = 20, offset = 0, verdict } = {}) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (verdict) params.set("verdict", verdict);
    return request(`/checks/?${params.toString()}`);
  },
  getCheck: (id) => request(`/checks/${id}`),
  submitCheckFeedback: (id, isCorrect) =>
    request(`/checks/${id}/feedback`, { method: "POST", body: { is_correct: isCorrect } }),
  getChecksSummary: () => request("/checks/summary"),
  // CSV export triggers a real browser download rather than returning
  // JSON — fetched with the auth header manually (the plain `request`
  // helper always parses the response as JSON/text, which would mangle
  // the CSV), then handed to the browser as a Blob download.
  exportChecksCsv: async () => {
    const token = getToken();
    const res = await fetch(`${API_BASE}/checks/export`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new ApiError(`Export failed (${res.status}).`, res.status);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "fraudlens_checks_export.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },

  // settings
  getApiKeyStatus: () => request("/settings/api-key"),
  saveApiKey: (api_key) => request("/settings/api-key", { method: "POST", body: { api_key } }),
  deleteApiKey: () => request("/settings/api-key", { method: "DELETE" }),
  getAuditLog: ({ limit = 50, offset = 0 } = {}) =>
    request(`/settings/audit-log?limit=${limit}&offset=${offset}`),
  revokeSessions: () => request("/settings/revoke-sessions", { method: "POST" }),
  changePassword: (current_password, new_password) =>
    request("/settings/change-password", { method: "POST", body: { current_password, new_password } }),
  deleteAccount: (password) => request("/settings/delete-account", { method: "POST", body: { password } }),

  // admin
  adminOverview: () => request("/admin/overview"),
  adminHealth: () => request("/admin/health"),
  adminRegistry: () => request("/admin/registry"),
  adminListChecks: ({ limit = 25, offset = 0, verdict, registry_status, user_email, claimed_sender } = {}) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (verdict) params.set("verdict", verdict);
    if (registry_status) params.set("registry_status", registry_status);
    if (user_email) params.set("user_email", user_email);
    if (claimed_sender) params.set("claimed_sender", claimed_sender);
    return request(`/admin/checks?${params.toString()}`);
  },
  adminGetCheck: (id) => request(`/admin/checks/${id}`),
  adminListUsers: ({ limit = 50, offset = 0, q } = {}) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (q) params.set("q", q);
    return request(`/admin/users?${params.toString()}`);
  },
  adminSetRole: (id, role) => request(`/admin/users/${id}/role`, { method: "POST", body: { role } }),
  adminSuspendUser: (id) => request(`/admin/users/${id}/suspend`, { method: "POST" }),
  adminActivateUser: (id) => request(`/admin/users/${id}/activate`, { method: "POST" }),
  adminAuditLog: ({ limit = 50, offset = 0, event_type, user_email } = {}) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (event_type) params.set("event_type", event_type);
    if (user_email) params.set("user_email", user_email);
    return request(`/admin/audit-log?${params.toString()}`);
  },
  adminLoginAttempts: ({ limit = 50, offset = 0, email, successful } = {}) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (email) params.set("email", email);
    if (successful !== undefined) params.set("successful", String(successful));
    return request(`/admin/login-attempts?${params.toString()}`);
  },
};

// Live SIEM feed (SSE). EventSource can't carry an Authorization
// header, so the token rides along as a query param — see the
// server-side note in app/routers/admin.py above /admin/stream.
// Returns a plain close() function; onEvent receives each parsed
// {type, data, ts} event as it arrives (backlog first, then live).
export function subscribeAdminStream(onEvent, onError) {
  const token = getToken();
  const url = `${API_BASE}/admin/stream?token=${encodeURIComponent(token || "")}`;
  const source = new EventSource(url);

  source.onmessage = (e) => {
    if (!e.data) return;
    try {
      onEvent(JSON.parse(e.data));
    } catch {
      // keep-alive comments and malformed frames are silently skipped
    }
  };
  source.onerror = (e) => {
    if (onError) onError(e);
  };

  return () => source.close();
}

export { ApiError };
