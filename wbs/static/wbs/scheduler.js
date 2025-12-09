// Scheduler bulk operations (keep Gantt read-only)
import logger from "./logger.js";

const csrfToken = (typeof window !== "undefined" && window.getCSRFToken) ? window.getCSRFToken() : "";
const selected = new Set();

const selectAll = document.getElementById("select-all");
const checkboxes = Array.from(document.querySelectorAll(".task-checkbox"));
const selectedCount = document.getElementById("selected-count");
const btnDelete = document.getElementById("bulk-delete");
const btnStatus = document.getElementById("bulk-status");
const btnExport = document.getElementById("bulk-export");
const btnClear = document.getElementById("bulk-clear");
const statusSelect = document.getElementById("status-select");

function updateState() {
  const count = selected.size;
  selectedCount.textContent = count;
  const enabled = count > 0;
  [btnDelete, btnStatus, btnExport, btnClear].forEach(btn => {
    if (btn) btn.disabled = !enabled;
  });
}

function getCodes() {
  return Array.from(selected);
}

function postJSON(url, payload) {
  return fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: JSON.stringify(payload),
  }).then(async (resp) => {
    const data = await resp.json().catch(() => ({}));
    return { ok: resp.ok, status: resp.status, data };
  });
}

if (selectAll) {
  selectAll.addEventListener("change", (e) => {
    const checked = e.target.checked;
    checkboxes.forEach(cb => {
      cb.checked = checked;
      if (checked) selected.add(cb.dataset.code);
      else selected.delete(cb.dataset.code);
    });
    updateState();
  });
}

checkboxes.forEach(cb => {
  cb.addEventListener("change", (e) => {
    if (e.target.checked) selected.add(e.target.dataset.code);
    else selected.delete(e.target.dataset.code);
    if (!e.target.checked && selectAll) selectAll.checked = false;
    updateState();
  });
});

if (btnClear) {
  btnClear.addEventListener("click", () => {
    selected.clear();
    checkboxes.forEach(cb => cb.checked = false);
    if (selectAll) selectAll.checked = false;
    updateState();
  });
}

if (btnDelete) {
  btnDelete.addEventListener("click", async () => {
    const codes = getCodes();
    if (codes.length === 0) return;
    if (!confirm(`Delete ${codes.length} selected task(s)? This cannot be undone.`)) return;
    const { ok, data } = await postJSON("/gantt/bulk-delete/", { codes });
    if (ok) {
      alert(data.message || "Deleted");
      window.location.reload();
    } else {
      alert(data.error || "Delete failed");
      logger.error("Bulk delete failed", data);
    }
  });
}

if (btnStatus) {
  btnStatus.addEventListener("click", async () => {
    const codes = getCodes();
    const status = statusSelect ? statusSelect.value : "";
    if (codes.length === 0 || !status) return;
    const { ok, data } = await postJSON("/gantt/bulk-update-status/", { codes, status });
    if (ok) {
      alert(data.message || "Status updated");
      window.location.reload();
    } else {
      alert(data.error || "Status update failed");
      logger.error("Bulk status failed", data);
    }
  });
}

if (btnExport) {
  btnExport.addEventListener("click", () => {
    const codes = getCodes();
    if (codes.length === 0) return;

    const rows = checkboxes
      .filter(cb => codes.includes(cb.dataset.code))
      .map(cb => {
        const row = cb.closest("tr");
        if (!row) return null;
        const cells = row.querySelectorAll("td");
        return [
          cb.dataset.code,
          cells[2]?.textContent?.trim() || "",
          cells[3]?.textContent?.trim() || "",
          cells[4]?.textContent?.trim() || "",
          cells[5]?.textContent?.trim() || "",
        ];
      })
      .filter(Boolean);

    const csv = [
      ["Code", "Task", "Start", "End", "Status"],
      ...rows,
    ]
      .map(r => r.map(cell => `"${(cell || "").replace(/"/g, '""')}"`).join(","))
      .join("\n");

    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `scheduler-export-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  });
}

updateState();
