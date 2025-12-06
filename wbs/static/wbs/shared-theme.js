// wbs/static/wbs/shared-theme.js
/**
 * Shared theme utilities for all views (Gantt, Kanban, List).
 * Centralizes dark/light mode toggle, CSRF retrieval, and persistence logic.
 */

/**
 * Get cookie by name from document.cookie
 * @param {string} name - Cookie name
 * @returns {string|null} Cookie value or null
 */
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(";").shift();
  return null;
}

/**
 * Get or retrieve CSRF token from various sources.
 * Priority: getCookie() > hidden input > meta tag
 * @returns {string} CSRF token (empty string if not found)
 */
function getCSRFToken() {
  return (
    getCookie("csrftoken") ||
    document.querySelector('input[name="csrfmiddlewaretoken"]')?.value ||
    document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") ||
    ""
  );
}

/**
 * Apply theme (light/dark) and persist to localStorage
 * @param {string} theme - 'light' or 'dark'
 * @param {string} themeKey - localStorage key (default: 'appTheme')
 * @param {HTMLElement} toggleBtn - Optional button to update text
 */
function applyTheme(theme, themeKey = "appTheme", toggleBtn = null) {
  const isDark = theme === "dark";

  // Toggle body class
  document.body.classList.toggle("theme-dark", isDark);
  document.body.classList.toggle("theme-light", !isDark);

  // Update button text if provided
  if (toggleBtn) {
    toggleBtn.textContent = isDark ? "Light Mode" : "Dark Mode";
  }

  // Persist to localStorage
  localStorage.setItem(themeKey, theme);
}

/**
 * Initialize theme toggle button with persistence
 * @param {string} buttonId - ID of theme toggle button
 * @param {string} themeKey - localStorage key (default: 'appTheme')
 * @param {string} defaultTheme - Default theme if not in storage (default: 'dark')
 */
function initializeThemeToggle(buttonId, themeKey = "appTheme", defaultTheme = "dark") {
  const toggleBtn = document.getElementById(buttonId);
  if (!toggleBtn) return;

  // Apply saved theme or default
  const savedTheme = localStorage.getItem(themeKey) || defaultTheme;
  applyTheme(savedTheme, themeKey, toggleBtn);

  // Add click handler
  toggleBtn.addEventListener("click", () => {
    const currentTheme = document.body.classList.contains("theme-dark") ? "dark" : "light";
    const nextTheme = currentTheme === "dark" ? "light" : "dark";
    applyTheme(nextTheme, themeKey, toggleBtn);
  });
}

// Export for use in modules (if using module syntax)
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    getCookie,
    getCSRFToken,
    applyTheme,
    initializeThemeToggle,
  };
}
