// wbs/static/wbs/gantt.js

document.addEventListener("DOMContentLoaded", function () {
  /* ------------------------------------------------------------
     Build lookup tables
  ------------------------------------------------------------ */
  const rows = Array.from(document.querySelectorAll("tbody tr.gantt-row"));
  const rowsByCode = {};
  const parentByCode = {};
  const ganttRoot = document.getElementById("gantt-root");
  const pxPerDay = ganttRoot ? parseFloat(ganttRoot.dataset.pxPerDay || "4") : 4;
  const minStartStr = ganttRoot ? ganttRoot.dataset.minStart : null;
  const minStartDate = minStartStr ? new Date(minStartStr + "T00:00:00") : null;
  const setDatesEndpoint = "/gantt/set-dates/";
  const optimizeEndpoint = "/gantt/optimize/";

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift();
  }
  const csrfToken =
    getCookie("csrftoken") ||
    document.querySelector('input[name="csrfmiddlewaretoken"]')?.value ||
    document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") ||
    "";

  rows.forEach(row => {
    const code = row.dataset.code;
    const parentCode = row.dataset.parentCode || "";
    rowsByCode[code] = row;
    parentByCode[code] = parentCode;
  });

  /* ------------------------------------------------------------
     Helpers
  ------------------------------------------------------------ */
  function getDescendants(code) {
    const prefix = code + ".";
    return rows.filter(r => r.dataset.code.startsWith(prefix));
  }

  function isAnyAncestorCollapsed(code) {
    let current = parentByCode[code];
    while (current) {
      const row = rowsByCode[current];
      if (!row) break;
      const exp = row.querySelector(".expander[data-has-children='true']");
      if (exp && exp.dataset.expanded === "false") {
        return true;
      }
      current = parentByCode[current] || "";
    }
    return false;
  }

  function daysBetween(a, b) {
    const diffMs = b.getTime() - a.getTime();
    return Math.round(diffMs / (1000 * 60 * 60 * 24));
  }

  function addDays(d, n) {
    const copy = new Date(d.getTime());
    copy.setDate(copy.getDate() + n);
    return copy;
  }

  function parseDate(val) {
    return val ? new Date(val + "T00:00:00") : null;
  }

  function earliestAllowedStart(row) {
    const preds = (row.dataset.predecessors || "").split(",").filter(Boolean);
    let latest = null;
    preds.forEach(code => {
      const r = rowsByCode[code];
      if (!r) return;
      const bar = r.querySelector(".bar");
      if (!bar || !bar.dataset.end) return;
      const end = parseDate(bar.dataset.end);
      if (!end) return;
      if (!latest || end > latest) latest = end;
    });
    return latest;
  }

  function refreshTasks(updates) {
    if (!updates || !updates.length) return;
    const map = {};
    updates.forEach(u => {
      if (u.code) map[u.code] = u;
    });
    rows.forEach(row => {
      const code = row.dataset.code;
      const upd = map[code];
      if (!upd) return;
      const bar = row.querySelector(".bar");
      if (!bar) return;

      bar.dataset.start = upd.start;
      bar.dataset.end = upd.end;

      const startDate = new Date(upd.start + "T00:00:00");
      const endDate = new Date(upd.end + "T00:00:00");
      const offsetDays = minStartDate ? daysBetween(minStartDate, startDate) : 0;
      bar.style.marginLeft = `${Math.max(0, offsetDays * pxPerDay)}px`;
      bar.style.width = `${Math.max(1, daysBetween(startDate, endDate) + 1) * pxPerDay}px`;
      updateRowDates(row, upd.start, upd.end);
    });
  }

  /* ------------------------------------------------------------
     Per-row expand/collapse
  ------------------------------------------------------------ */
  document
    .querySelectorAll(".expander[data-has-children='true']")
    .forEach(exp => {
      const row = exp.closest("tr.gantt-row");
      const code = row.dataset.code;

      exp.addEventListener("click", (event) => {
        // Don't trigger row click selection when toggling
        event.stopPropagation();

        const currentlyExpanded = exp.dataset.expanded === "true";
        const newExpanded = !currentlyExpanded;

        exp.dataset.expanded = newExpanded ? "true" : "false";
        exp.textContent = newExpanded ? "▾" : "▸";

        const descendants = getDescendants(code);

        if (!newExpanded) {
          // collapsing
          descendants.forEach(r => {
            r.style.display = "none";
          });
        } else {
          // expanding
          descendants.forEach(r => {
            if (!isAnyAncestorCollapsed(r.dataset.code)) {
              r.style.display = "";
            }
          });
        }
      });
    });

  /* ------------------------------------------------------------
     Expand All / Collapse All
  ------------------------------------------------------------ */
  const expandAllBtn = document.getElementById("expand-all");
  const collapseAllBtn = document.getElementById("collapse-all");

  if (expandAllBtn) {
    expandAllBtn.addEventListener("click", () => {
      // expand all expander icons
      document
        .querySelectorAll(".expander[data-has-children='true']")
        .forEach(exp => {
          exp.dataset.expanded = "true";
          exp.textContent = "▾";
        });

      // show all rows
      rows.forEach(row => {
        row.style.display = "";
      });
    });
  }

  if (collapseAllBtn) {
    collapseAllBtn.addEventListener("click", () => {
      // collapse all expander icons
      document
        .querySelectorAll(".expander[data-has-children='true']")
        .forEach(exp => {
          exp.dataset.expanded = "false";
          exp.textContent = "▸";
        });

      // hide all children
      rows.forEach(row => {
        const parentCode = row.dataset.parentCode || "";
        row.style.display = parentCode ? "none" : "";
      });
    });
  }

  /* ------------------------------------------------------------
     Hover highlighting for dependencies
  ------------------------------------------------------------ */
  function clearHighlights() {
    rows.forEach(r => {
      r.classList.remove("highlight-row");
      const bar = r.querySelector(".bar");
      if (bar) {
        bar.classList.remove("highlight-bar");
      }
    });
  }

  /* ------------------------------------------------------------
     Side panel: click row → show ProjectItems
  ------------------------------------------------------------ */
  const panel = document.getElementById("project-detail-panel");
  const headerEl = document.getElementById("detail-task-header");
  const itemsEl = document.getElementById("detail-project-items");

  function clearSelection() {
    rows.forEach(r => r.classList.remove("selected"));
  }

  function renderPanelForRow(row) {
    if (!panel || !headerEl || !itemsEl) return;

    const code = row.dataset.code || "";
    const name =
      row.dataset.wbsName ||
      (row.querySelector(".task-name")?.innerText || "").trim();

    clearSelection();
    row.classList.add("selected");

    headerEl.innerHTML = `
      <div class="selected-task">${code} — ${name}</div>
    `;

    const hidden = row.querySelector(".hidden-project-items");
    if (!hidden) {
      itemsEl.innerHTML = '<div class="muted">No project items.</div>';
      return;
    }

    const itemNodes = hidden.querySelectorAll(".project-item");
    if (!itemNodes.length) {
      itemsEl.innerHTML =
        '<div class="muted">No project items for this task.</div>';
      return;
    }

    itemsEl.innerHTML = "";
    itemNodes.forEach(node => {
      itemsEl.appendChild(node.cloneNode(true));
    });
  }

  /* ------------------------------------------------------------
     Bind mouse & click handlers to rows
  ------------------------------------------------------------ */
  rows.forEach(row => {
    // Dependency hover
    row.addEventListener("mouseenter", () => {
      clearHighlights();

      const code = row.dataset.code;
      const preds = (row.dataset.predecessors || "")
        .split(",")
        .filter(Boolean);
      const succs = (row.dataset.successors || "")
        .split(",")
        .filter(Boolean);

      const allCodes = new Set();
      if (code) allCodes.add(code);
      preds.forEach(c => allCodes.add(c));
      succs.forEach(c => allCodes.add(c));

      allCodes.forEach(c => {
        const r = rowsByCode[c];
        if (!r) return;
        r.classList.add("highlight-row");
        const bar = r.querySelector(".bar");
        if (bar) {
          bar.classList.add("highlight-bar");
        }
      });
    });

    row.addEventListener("mouseleave", () => {
      clearHighlights();
    });

    // Click → show ProjectItems in side panel
    row.addEventListener("click", () => {
      renderPanelForRow(row);
    });
  });

  /* ------------------------------------------------------------
     Drag-to-reschedule bars
  ------------------------------------------------------------ */
  const shiftEndpoint = "/gantt/shift/";

  function updateRowDates(row, newStart, newEnd) {
    const cells = row.querySelectorAll("td");
    if (cells[2]) cells[2].textContent = newStart;
    if (cells[3]) cells[3].textContent = newEnd;
  }

  function attachBarDrag(bar) {
    const row = bar.closest("tr.gantt-row");
    if (!row || !minStartDate) return;

    const durationDays = (() => {
      const start = new Date(bar.dataset.start + "T00:00:00");
      const end = new Date(bar.dataset.end + "T00:00:00");
      return Math.max(0, daysBetween(start, end));
    })();

    let startX = 0;
    let lastDeltaDays = 0;
    let pointerActive = false;

    const onMove = (e) => {
      if (!pointerActive) return;
      const deltaPx = e.clientX - startX;
      const deltaDays = Math.round(deltaPx / pxPerDay);
      lastDeltaDays = deltaDays;
      bar.style.transform = `translateX(${deltaDays * pxPerDay}px)`;
    };

    const onUp = (e) => {
      if (!pointerActive) return;
      pointerActive = false;
      bar.releasePointerCapture(e.pointerId);
      bar.style.transform = "";
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerup", onUp);

      if (lastDeltaDays === 0) return;

      const originalStart = new Date(bar.dataset.start + "T00:00:00");
      let newStart = addDays(originalStart, lastDeltaDays);
      let snapped = false;

      const earliest = earliestAllowedStart(row);
      if (earliest && newStart < earliest) {
        const snapStr = earliest.toISOString().slice(0, 10);
        const ok = confirm(
          `This move would violate a predecessor. Snap to ${snapStr}?`
        );
        if (!ok) {
          return;
        }
        newStart = earliest;
        snapped = true;
      }

      const newEnd = addDays(newStart, durationDays);

      fetch(shiftEndpoint, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": csrfToken,
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: new URLSearchParams({
          code: bar.dataset.code,
          new_start: newStart.toISOString().slice(0, 10),
        }),
      })
        .then(async (resp) => {
          const text = await resp.text();
          let data = {};
          try {
            data = JSON.parse(text);
          } catch (_) {
            data = {};
          }
          if (!resp.ok || !data.ok) {
            const msg = data.error || text || `HTTP ${resp.status}`;
            throw new Error(msg);
          }
          // Update bar position and metadata
          const offsetDays = minStartDate
            ? daysBetween(minStartDate, newStart)
            : 0;
          bar.style.marginLeft = `${offsetDays * pxPerDay}px`;
          bar.dataset.start = data.start;
          bar.dataset.end = data.end || newEnd.toISOString().slice(0, 10);
          updateRowDates(row, bar.dataset.start, bar.dataset.end);
        })
        .catch((err) => {
          alert(`Could not reschedule: ${err.message}`);
        });
    };

    bar.addEventListener("pointerdown", (e) => {
      e.stopPropagation();
      pointerActive = true;
      startX = e.clientX;
      lastDeltaDays = 0;
      bar.setPointerCapture(e.pointerId);
      document.addEventListener("pointermove", onMove);
      document.addEventListener("pointerup", onUp);
    });
  }

  document
    .querySelectorAll(".draggable-bar")
    .forEach(bar => attachBarDrag(bar));

  /* ------------------------------------------------------------
     Inline date edit via modal
  ------------------------------------------------------------ */
  const modal = document.createElement("div");
  modal.className = "gantt-modal hidden";
  modal.innerHTML = `
    <div class="gantt-modal-backdrop"></div>
    <div class="gantt-modal-card">
      <h3>Edit Dates</h3>
      <label>Start <input type="date" id="modal-start"></label>
      <label>End <input type="date" id="modal-end"></label>
      <div class="modal-actions">
        <button type="button" id="modal-cancel">Cancel</button>
        <button type="button" id="modal-save">Save</button>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
  const startInput = modal.querySelector("#modal-start");
  const endInput = modal.querySelector("#modal-end");
  const cancelBtn = modal.querySelector("#modal-cancel");
  const saveBtn = modal.querySelector("#modal-save");
  let modalTarget = null;

  function openModal(bar) {
    modalTarget = bar;
    startInput.value = bar.dataset.start;
    endInput.value = bar.dataset.end;
    modal.classList.remove("hidden");
  }

  function closeModal() {
    modal.classList.add("hidden");
    modalTarget = null;
  }

  cancelBtn.addEventListener("click", closeModal);
  modal.querySelector(".gantt-modal-backdrop").addEventListener("click", closeModal);

  saveBtn.addEventListener("click", () => {
    if (!modalTarget) return;
    const newStart = startInput.value;
    const newEnd = endInput.value;
    if (!newStart || !newEnd) {
      alert("Start and end are required");
      return;
    }
    fetch(setDatesEndpoint, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "X-CSRFToken": csrfToken,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({
        code: modalTarget.dataset.code,
        start: newStart,
        end: newEnd,
      }),
    })
      .then(async (resp) => {
        const text = await resp.text();
        let data = {};
        try {
          data = JSON.parse(text);
        } catch (_) {
          data = {};
        }
        if (!resp.ok || !data.ok) {
          const msg = data.error || text || `HTTP ${resp.status}`;
          throw new Error(msg);
        }

        const row = modalTarget.closest("tr.gantt-row");
        // Update bar data and position
        modalTarget.dataset.start = data.start;
        modalTarget.dataset.end = data.end;
        const startDate = new Date(data.start + "T00:00:00");
        const endDate = new Date(data.end + "T00:00:00");
        const offsetDays = minStartDate ? daysBetween(minStartDate, startDate) : 0;
        modalTarget.style.marginLeft = `${Math.max(0, offsetDays * pxPerDay)}px`;
        modalTarget.style.width = `${Math.max(1, daysBetween(startDate, endDate) + 1) * pxPerDay}px`;
        updateRowDates(row, data.start, data.end);
      })
      .catch((err) => {
        alert(`Could not update dates: ${err.message}`);
      })
      .finally(() => {
        closeModal();
      });
  });

  document.querySelectorAll(".draggable-bar").forEach(bar => {
    bar.addEventListener("dblclick", (e) => {
      e.stopPropagation();
      openModal(bar);
    });
  });

  /* ------------------------------------------------------------
     Optimize Schedule button (stub)
  ------------------------------------------------------------ */
  const optimizeBtn = document.getElementById("optimize-schedule");
  if (optimizeBtn) {
    optimizeBtn.addEventListener("click", () => {
      optimizeBtn.disabled = true;
      optimizeBtn.textContent = "Optimizing...";
      fetch(optimizeEndpoint, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": csrfToken,
        },
      })
        .then(async (resp) => {
          const text = await resp.text();
          const redirectedToLogin =
            resp.redirected || (resp.url && resp.url.includes("login"));
          let data = {};
          try {
            data = JSON.parse(text);
          } catch (_) {
            data = {};
          }
          if (redirectedToLogin) {
            throw new Error("Authentication required: log in as staff/admin and retry.");
          }
          if (!resp.ok || !data.ok) {
            const msg = data.error || text || `HTTP ${resp.status}`;
            throw new Error(msg);
          }
          refreshTasks(data.tasks || []);
          alert(data.message || "Schedule optimized.");
        })
        .catch((err) => {
          alert(`Optimize failed: ${err.message}`);
        })
        .finally(() => {
          optimizeBtn.disabled = false;
          optimizeBtn.textContent = "Optimize Schedule";
        });
    });
  }

  /* ------------------------------------------------------------
     Toggle Project Items panel
  ------------------------------------------------------------ */
  const togglePanelBtn = document.getElementById("toggle-project-panel");
  if (panel && togglePanelBtn) {
    togglePanelBtn.addEventListener("click", () => {
      panel.classList.toggle("collapsed");
    });
  }
});
