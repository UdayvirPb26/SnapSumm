// credentials: 'include' is what makes the Flask session cookie ride
// along with every request — without it, Flask-Login sees every request
// as a fresh, logged-out visitor.
const BASE = '';

async function request(path, options = {}) {
  const res = await fetch(BASE + path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });

  let data = null;
  try { data = await res.json(); } catch { /* not all responses are JSON */ }

  if (!res.ok) {
    throw new Error((data && data.error) || `Request failed (${res.status})`);
  }
  return data;
}

export const api = {
  me: () => request('/api/me'),
  login: (username, password) =>
    request('/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  register: (username, email, password, confirmPassword) =>
    request('/register', {
      method: 'POST',
      body: JSON.stringify({ username, email, password, confirm_password: confirmPassword }),
    }),
  guest: () => request('/guest', { method: 'POST' }),
  logout: () => request('/logout', { method: 'POST' }),

  summarize: (url) => request('/summarize', { method: 'POST', body: JSON.stringify({ url }) }),
  translateSummary: (text, targetLanguage) =>
    request('/translate-summary', { method: 'POST', body: JSON.stringify({ text, target_language: targetLanguage }) }),

  listSummaries: () => request('/summaries'),
  getSummary: (id) => request(`/summary/${id}`),
  saveSummary: (payload) => request('/save-summary', { method: 'POST', body: JSON.stringify(payload) }),
  deleteSummary: (id) => request(`/summary/${id}`, { method: 'DELETE' }),
  renameSummary: (id, title) => request(`/summary/${id}/rename`, { method: 'PATCH', body: JSON.stringify({ title }) }),

  listUsers: () => request('/api/admin/users'),
  deleteUser: (id) => request(`/admin/delete/${id}`, { method: 'POST' }),
};