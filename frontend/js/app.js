/**
 * StructGuard AI — Core Application JavaScript
 * ================================================
 * Teaching note: This file is the "brain" of the frontend.
 * It handles:
 *   1. API communication — all fetch() calls to the Flask backend
 *   2. Authentication state — storing/reading JWT tokens
 *   3. Client-side routing — showing/hiding pages without full page reload
 *   4. Theme toggle — light/dark mode
 *   5. Toast notifications — feedback messages
 *
 * We use Vanilla JS (no frameworks) so you can modify it directly for V2.
 */

"use strict";

/* ================================================================== */
/* CONFIGURATION                                                        */
/* ================================================================== */
const CONFIG = {
  API_BASE:   "https://structguard-api.onrender.com/api",
  TOKEN_KEY:  "sg_access_token",
  REFRESH_KEY:"sg_refresh_token",
  USER_KEY:   "sg_user",
};

/* ================================================================== */
/* API CLIENT                                                           */
/* Teaching note: All API calls go through this single function.       */
/* It automatically attaches the JWT token and handles 401 errors.     */
/* ================================================================== */
const api = {
  /**
   * Make an authenticated JSON API request.
   * @param {string} path   - e.g. "/projects" → becomes /api/projects
   * @param {object} options - fetch options (method, body, etc.)
   */
  async request(path, options = {}) {
    const token = auth.getToken();
    const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    try {
      const res = await fetch(`${CONFIG.API_BASE}${path}`, {
        ...options,
        headers,
      });

      // If token expired, try to refresh once
      if (res.status === 401 && token) {
        const refreshed = await auth.refreshToken();
        if (refreshed) {
          // Retry with new token
          headers["Authorization"] = `Bearer ${auth.getToken()}`;
          const retry = await fetch(`${CONFIG.API_BASE}${path}`, { ...options, headers });
          return { ok: retry.ok, status: retry.status, data: await retry.json() };
        } else {
          auth.logout();
          return { ok: false, status: 401, data: { error: "Session expired" } };
        }
      }

      const data = res.headers.get("content-type")?.includes("json")
        ? await res.json()
        : {};
      return { ok: res.ok, status: res.status, data };
    } catch (err) {
      console.error("API error:", err);
      return { ok: false, status: 0, data: { error: "Cannot connect to server. Is the backend running?" } };
    }
  },

  get:    (path)         => api.request(path, { method: "GET" }),
  post:   (path, body)   => api.request(path, { method: "POST",   body: JSON.stringify(body) }),
  put:    (path, body)   => api.request(path, { method: "PUT",    body: JSON.stringify(body) }),
  delete: (path)         => api.request(path, { method: "DELETE" }),

  /** Upload files via multipart form data */
  async upload(path, formData) {
    const token = auth.getToken();
    const headers = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    // Do NOT set Content-Type — let browser set multipart boundary automatically
    try {
      const res = await fetch(`${CONFIG.API_BASE}${path}`, {
        method: "POST", headers, body: formData
      });
      const data = res.headers.get("content-type")?.includes("json") ? await res.json() : {};
      return { ok: res.ok, status: res.status, data };
    } catch (err) {
      return { ok: false, status: 0, data: { error: "Upload failed — check connection" } };
    }
  }
};

/* ================================================================== */
/* AUTHENTICATION STATE                                                 */
/* ================================================================== */
const auth = {
  getToken()   { return localStorage.getItem(CONFIG.TOKEN_KEY); },
  getUser()    {
    try { return JSON.parse(localStorage.getItem(CONFIG.USER_KEY)); }
    catch { return null; }
  },
  isLoggedIn() { return !!this.getToken(); },

  save(accessToken, refreshToken, user) {
    localStorage.setItem(CONFIG.TOKEN_KEY,  accessToken);
    localStorage.setItem(CONFIG.REFRESH_KEY, refreshToken);
    localStorage.setItem(CONFIG.USER_KEY,   JSON.stringify(user));
  },

  /* Clear session without navigating — used by boot script */
  clearSession() {
    localStorage.removeItem(CONFIG.TOKEN_KEY);
    localStorage.removeItem(CONFIG.REFRESH_KEY);
    localStorage.removeItem(CONFIG.USER_KEY);
  },

  /* Log out and navigate to login page */
  logout() {
    this.clearSession();
    document.getElementById("app-shell").style.display = "none";
    router.show("login");
  },

  async refreshToken() {
    const refresh = localStorage.getItem(CONFIG.REFRESH_KEY);
    if (!refresh) return false;
    try {
      const res = await fetch(`${CONFIG.API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${refresh}`, "Content-Type": "application/json" }
      });
      if (res.ok) {
        const data = await res.json();
        localStorage.setItem(CONFIG.TOKEN_KEY, data.access_token);
        return true;
      }
      return false;
    } catch { return false; }
  }
};

/* ================================================================== */
/* TOAST NOTIFICATIONS                                                  */
/* Teaching note: Toasts are small pop-up messages that appear        */
/* bottom-right to give feedback (success, error, warning, info).     */
/* ================================================================== */
const toast = {
  container: null,

  init() {
    this.container = document.getElementById("toast-container");
    if (!this.container) {
      this.container = document.createElement("div");
      this.container.id = "toast-container";
      this.container.className = "toast-container";
      document.body.appendChild(this.container);
    }
  },

  show(message, type = "info", duration = 4000) {
    if (!this.container) this.init();
    const icons = { success: "✅", error: "❌", warning: "⚠️", info: "ℹ️" };
    const t = document.createElement("div");
    t.className = `toast toast-${type}`;
    t.innerHTML = `<span>${icons[type] || "ℹ️"}</span><span>${message}</span>`;
    this.container.appendChild(t);
    setTimeout(() => { t.style.opacity = "0"; t.style.transition = "opacity .3s"; setTimeout(() => t.remove(), 300); }, duration);
  },

  success: (msg) => toast.show(msg, "success"),
  error:   (msg) => toast.show(msg, "error", 6000),
  warning: (msg) => toast.show(msg, "warning"),
  info:    (msg) => toast.show(msg, "info"),
};

/* ================================================================== */
/* THEME TOGGLE                                                         */
/* ================================================================== */
const theme = {
  KEY: "sg_theme",

  init() {
    const saved = localStorage.getItem(this.KEY) || "light";
    this.apply(saved);
  },

  toggle() {
    const current = document.documentElement.getAttribute("data-theme") || "light";
    this.apply(current === "dark" ? "light" : "dark");
  },

  apply(mode) {
    document.documentElement.setAttribute("data-theme", mode);
    localStorage.setItem(this.KEY, mode);
    // Update toggle button icon
    const btn = document.getElementById("theme-toggle");
    if (btn) btn.textContent = mode === "dark" ? "☀️ Light mode" : "🌙 Dark mode";
  }
};

/* ================================================================== */
/* RISK HELPERS                                                         */
/* ================================================================== */
const risk = {
  label(level) {
    return { safe: "SAFE", monitor: "MONITOR", high_risk: "HIGH RISK", critical: "CRITICAL" }[level] || level;
  },
  badgeClass(level) {
    return { safe: "badge-safe", monitor: "badge-monitor", high_risk: "badge-high", critical: "badge-critical" }[level] || "badge-monitor";
  },
  dotClass(level) {
    return { safe: "dot-safe", monitor: "dot-monitor", high_risk: "dot-high", critical: "dot-critical" }[level] || "dot-monitor";
  },
  fillClass(level) {
    return { safe: "fill-safe", monitor: "fill-monitor", high_risk: "fill-high", critical: "fill-critical" }[level] || "fill-monitor";
  },
  colour(level) {
    return { safe: "#22c55e", monitor: "#f59e0b", high_risk: "#f97316", critical: "#ef4444" }[level] || "#94a3b8";
  },
  badge(level) {
    return `<span class="badge ${risk.badgeClass(level)}"><span class="risk-dot ${risk.dotClass(level)}"></span>${risk.label(level)}</span>`;
  }
};

/* ================================================================== */
/* ROLE HELPERS                                                         */
/* Teaching note: What each role CAN see is determined by the backend. */
/* These helpers decide what UI elements to show/hide accordingly.    */
/* ================================================================== */
const roles = {
  labels: {
    supervisor:  "Site Supervisor",
    developer:   "Developer / Owner",
    inspector:   "Regulatory Inspector",
    agency_admin:"Agency Administrator",
  },
  label: (r) => roles.labels[r] || r,

  canSubmit:    (u) => u && ["supervisor", "developer"].includes(u.role),
  canSeeAll:    (u) => u && ["inspector", "agency_admin"].includes(u.role),
  canEnforce:   (u) => u && u.role === "agency_admin",
  canAnalytics: (u) => u && ["inspector", "agency_admin"].includes(u.role),

  /** Returns the nav items relevant to the user's role */
  navItems(user) {
    const base = [
      { id: "dashboard",  icon: "🏠", label: "Dashboard" },
      { id: "projects",   icon: "🏗️", label: "Projects"  },
    ];

    if (roles.canSubmit(user)) {
      base.push({ id: "submit",    icon: "📸", label: "Submit Photos" });
    }
    if (roles.canSeeAll(user)) {
      base.push({ id: "inspect",   icon: "🔍", label: "Inspection Queue" });
      base.push({ id: "analytics", icon: "📊", label: "Analytics" });
    }
    if (roles.canEnforce(user)) {
      base.push({ id: "users",     icon: "👥", label: "User Management" });
    }

    base.push({ id: "profile", icon: "👤", label: "My Profile" });
    return base;
  }
};

/* ================================================================== */
/* ROUTER — Single-page navigation                                     */
/* Teaching note: We show/hide <section> elements instead of loading  */
/* new HTML pages. This avoids full page reloads and is faster.       */
/* ================================================================== */
const router = {
  current: null,

  navigate(page) {
    if (!auth.isLoggedIn() && page !== "login" && page !== "register") {
      this.current = page;
      this.show("login");
      return;
    }
    this.show(page);
  },

  show(page) {
    this.current = page;

    // Teaching note: We remove page-active from ALL pages first (hides them),
    // then add it only to the target page (shows it).
    // Auth pages need display:flex, content pages need display:block.
    // We handle both cases below.
    document.querySelectorAll(".page").forEach(p => {
      p.classList.remove("page-active");
      p.style.display = "none";  // belt-and-suspenders fallback
    });

    const target = document.getElementById(`page-${page}`);
    if (target) {
      // Auth pages (login, register) need flex for vertical centering
      const isAuthPage = target.classList.contains("auth-page");
      target.style.display = isAuthPage ? "flex" : "block";
      target.classList.add("page-active");
    }
    // Update nav highlight
    document.querySelectorAll(".nav-item").forEach(n => {
      n.classList.toggle("active", n.dataset.page === page);
    });
    // Update topbar title
    const titles = {
      dashboard:  "Dashboard",
      projects:   "Projects",
      submit:     "Submit Site Photos",
      inspect:    "Inspection Queue",
      analytics:  "Analytics",
      users:      "User Management",
      profile:    "My Profile",
      login:      "",
      register:   "",
    };
    const titleEl = document.getElementById("topbar-title");
    if (titleEl) titleEl.textContent = titles[page] || page;

    // Load page data
    pages.load(page);
  }
};

/* ================================================================== */
/* UTILITIES                                                            */
/* ================================================================== */
const utils = {
  formatDate(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("en-NG", { day: "numeric", month: "short", year: "numeric" });
  },
  formatDateTime(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleString("en-NG", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  },
  initials(name) {
    return (name || "?").split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
  },
  statusBadge(status) {
    const map = {
      registered: ["🔵", "#e0f2fe", "#0369a1"],
      active:     ["🟢", "#dcfce7", "#15803d"],
      flagged:    ["🟠", "#fff7ed", "#9a3412"],
      stop_work:  ["🔴", "#fef2f2", "#991b1b"],
      completed:  ["⚫", "#f1f5f9", "#475569"],
      inspection_due: ["🟡", "#fffbeb", "#92400e"],
    };
    const [icon, bg, col] = map[status] || ["⚪", "#f1f5f9", "#475569"];
    return `<span style="background:${bg};color:${col};padding:2px 10px;border-radius:20px;font-size:12px;font-weight:600;">${icon} ${(status || "").replace("_"," ").toUpperCase()}</span>`;
  }
};