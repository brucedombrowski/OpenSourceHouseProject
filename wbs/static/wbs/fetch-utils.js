// wbs/static/wbs/fetch-utils.js
/**
 * Shared fetch utilities for API calls across views.
 * Centralizes error handling, response parsing, and CSRF injection.
 */

/**
 * Standard fetch wrapper with error handling, CSRF injection, and response parsing.
 *
 * @param {string} url - API endpoint URL
 * @param {object} options - Fetch options (method, body, headers, etc.)
 * @param {object} config - Additional config (onSuccess, onError, showAlert, buttonId)
 * @returns {Promise<object>} Parsed response data
 */
async function fetchWithErrorHandling(url, options = {}, config = {}) {
  const {
    onSuccess = null,
    onError = null,
    showAlert = true,
    buttonId = null,
    successMessage = "Request successful",
    errorPrefix = "Request failed",
  } = config;

  const button = buttonId ? document.getElementById(buttonId) : null;
  const originalText = button?.textContent;
  const originalDisabled = button?.disabled;

  try {
    // Set up default options
    const fetchOptions = {
      method: options.method || "POST",
      credentials: "same-origin",
      headers: {
        "X-CSRFToken": getCSRFToken ? getCSRFToken() : getCookie("csrftoken") || "",
        ...options.headers,
      },
      ...options,
    };

    // Show loading state
    if (button) {
      button.disabled = true;
      button.textContent = "Processing...";
    }

    // Execute fetch
    const response = await fetch(url, fetchOptions);
    const text = await response.text();

    // Check for redirect to login
    const redirectedToLogin =
      response.redirected || (response.url && response.url.includes("login"));
    if (redirectedToLogin) {
      throw new Error("Authentication required: log in as staff/admin and retry.");
    }

    // Try to parse JSON
    let data = {};
    try {
      data = JSON.parse(text);
    } catch (_) {
      data = {};
    }

    // Check response status
    if (!response.ok || !data.ok) {
      const errorMsg = data.error || text || `HTTP ${response.status}`;
      throw new Error(errorMsg);
    }

    // Call success callback
    if (onSuccess) {
      onSuccess(data);
    }

    // Show success alert if configured
    if (showAlert) {
      alert(data.message || successMessage);
    }

    return data;
  } catch (err) {
    // Call error callback
    if (onError) {
      onError(err);
    }

    // Show error alert if configured
    if (showAlert) {
      alert(`${errorPrefix}: ${err.message}`);
    }

    throw err;
  } finally {
    // Restore button state
    if (button) {
      button.disabled = originalDisabled || false;
      button.textContent = originalText || "Submit";
    }
  }
}

/**
 * Simplified POST fetch with standard error handling
 * @param {string} url - API endpoint
 * @param {object} data - Data to POST (will be JSON-encoded)
 * @param {object} config - Error handling config
 * @returns {Promise<object>} Response data
 */
async function postJSON(url, data = {}, config = {}) {
  return fetchWithErrorHandling(url, {
    method: "POST",
    body: JSON.stringify(data),
    headers: { "Content-Type": "application/json" },
  }, config);
}

// Export for use in modules (if using module syntax)
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    fetchWithErrorHandling,
    postJSON,
  };
}
