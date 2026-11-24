// Base URL of the Flask app (auth, quizzes, dashboard, admin, certificates).
// In dev this points at the Flask dev server directly; in a combined
// deployment behind one domain this can be set to "".
export const APP_BASE_URL = import.meta.env.VITE_APP_BASE_URL ?? "http://127.0.0.1:5000";

export const appUrl = (path) => `${APP_BASE_URL}${path}`;
