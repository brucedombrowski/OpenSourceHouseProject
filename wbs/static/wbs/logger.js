// wbs/static/wbs/logger.js
/**
 * Environment-aware logging utility for browser console.
 *
 * Conditionally logs messages based on environment:
 * - Development: localhost, 127.0.0.1, or query param ?debug=true
 * - Production: all other hosts, logs suppressed
 *
 * This prevents console spam in production while maintaining debug visibility in dev.
 */

// Detect development environment
const isDevelopment = () => {
  const hostname = window.location.hostname;
  const isLocalhost = hostname === "localhost" || hostname === "127.0.0.1";
  const debugParam = new URLSearchParams(window.location.search).get("debug") === "true";
  return isLocalhost || debugParam;
};

/**
 * Logger object with conditional methods.
 *
 * Usage:
 *   logger.log("Task loaded:", task);    // Only in dev
 *   logger.warn("Missing start date");   // Always shown
 *   logger.error("Fetch failed:", err);  // Always shown
 */
const logger = {
  /**
   * Log debug messages (dev only).
   * @param {...any} args - Messages/values to log
   */
  log: isDevelopment() ? console.log.bind(console) : () => {},

  /**
   * Log warnings (always shown).
   * @param {...any} args - Messages/values to log
   */
  warn: console.warn.bind(console),

  /**
   * Log errors (always shown).
   * @param {...any} args - Messages/values to log
   */
  error: console.error.bind(console),

  /**
   * Log performance timing info (dev only).
   * @param {string} label - Performance marker label
   */
  time: isDevelopment() ? console.time.bind(console) : () => {},

  /**
   * End performance timing (dev only).
   * @param {string} label - Performance marker label
   */
  timeEnd: isDevelopment() ? console.timeEnd.bind(console) : () => {},

  /**
   * Check if debug logging is enabled.
   * @returns {boolean} True if in development mode
   */
  isDebugEnabled: isDevelopment,
};

// ES module export
export default logger;

// CommonJS export for compatibility
if (typeof module !== "undefined" && module.exports) {
  module.exports = logger;
}
