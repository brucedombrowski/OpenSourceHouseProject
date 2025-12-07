// wbs/static/wbs/gantt.js
// Requires: shared-theme.js (for getCSRFToken)
import {
  addDays,
  buildRowIndex,
  daysBetween,
  getDescendants,
  isAnyAncestorCollapsed,
  parseDate,
} from "./gantt-utils.js";
import { createArrowDrawer } from "./gantt-arrows.js";
import { initExpandCollapse } from "./gantt-expand.js";

document.addEventListener("DOMContentLoaded", function () {
  /* ------------------------------------------------------------
     Build lookup tables
  ------------------------------------------------------------ */
  const rows = Array.from(document.querySelectorAll("tbody tr.gantt-row"));
  const { rowsByCode, parentByCode } = buildRowIndex(rows);
  const ganttRoot = document.getElementById("gantt-root");
  const basePxPerDay = ganttRoot ? parseFloat(ganttRoot.dataset.pxPerDay || "4") : 4;
  const minStartStr = ganttRoot ? ganttRoot.dataset.minStart : null;
  const minStartDate = minStartStr ? new Date(minStartStr + "T00:00:00") : null;
  const baseTimelineWidth = ganttRoot ? parseFloat(ganttRoot.dataset.timelineWidth || "0") : 0;
  const setTimelineWidthVar = px => {
    if (!ganttRoot || Number.isNaN(px)) return;
    ganttRoot.style.setProperty("--timeline-width", `${px}px`);
  };
  const ZOOM_KEY = "ganttZoom";
  const clamp = (val, min, max) => Math.min(max, Math.max(min, val));
  const loadZoom = () => {
    const stored = parseFloat(localStorage.getItem(ZOOM_KEY) || "1");
    if (Number.isNaN(stored)) return 1;
    return clamp(stored, 0.5, 3);
  };
  let zoom = loadZoom();
  let currentPxPerDay = basePxPerDay * zoom;
  const setDatesEndpoint = "/gantt/set-dates/";
  const optimizeEndpoint = "/gantt/optimize/";

  setTimelineWidthVar(baseTimelineWidth);

  // CSRF token from shared-theme.js
  const csrfToken = getCSRFToken();

  rows.forEach(row => {
    const code = row.dataset.code;
    const parentCode = row.dataset.parentCode || "";
    rowsByCode[code] = row;
    parentByCode[code] = parentCode;
  });

  /* ------------------------------------------------------------
     Helpers
  ------------------------------------------------------------ */

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
      bar.style.marginLeft = `${Math.max(0, offsetDays * currentPxPerDay)}px`;
      bar.style.width = `${Math.max(1, daysBetween(startDate, endDate) + 1) * currentPxPerDay}px`;
      updateRowDates(row, upd.start, upd.end);
    });
  }

    /* ------------------------------------------------------------
       Dependency arrows and highlighting (module)
    ------------------------------------------------------------ */
  const depSvg = document.getElementById("dependency-svg");
  const scrollElement = document.querySelector(".gantt-scroll");
  const { drawDependencyArrows, clearHighlights, highlightDependencies } =
    createArrowDrawer({ rows, rowsByCode, scrollElement, depSvg });

  // Throttle expensive redraws to animation frames to avoid scroll jitter
  let arrowsQueued = false;
  const scheduleArrowRedraw = () => {
    if (arrowsQueued) return;
    arrowsQueued = true;
    requestAnimationFrame(() => {
      arrowsQueued = false;
      drawDependencyArrows();
    });
  };

  initExpandCollapse({ rows, rowsByCode, parentByCode, drawDependencyArrows });

  /* ------------------------------------------------------------
     Zoom controls (persisted in localStorage)
  ------------------------------------------------------------ */
  const timelineTrack = document.querySelector(".timeline-track");
  const barWrappers = Array.from(document.querySelectorAll(".bar-wrapper"));
  const timelineElements = Array.from(
    document.querySelectorAll(
      ".timeline .year-band, .timeline .month-band, .timeline .day-tick, .timeline .day-label"
    )
  );
  let basePositionsCached = false;

  function cacheTimelinePositions() {
    if (basePositionsCached) return;
    timelineElements.forEach(el => {
      const left = parseFloat(el.style.left || "0");
      if (!Number.isNaN(left)) {
        el.dataset.baseLeft = left;
      }
      const width = parseFloat(el.style.width || "");
      if (!Number.isNaN(width)) {
        el.dataset.baseWidth = width;
      }
    });
    basePositionsCached = true;
  }

  function applyZoom(nextZoom) {
    zoom = clamp(nextZoom, 0.5, 3);
    localStorage.setItem(ZOOM_KEY, String(zoom));
    currentPxPerDay = basePxPerDay * zoom;

    cacheTimelinePositions();

    const trackBaseWidth = baseTimelineWidth || (timelineTrack ? timelineTrack.getBoundingClientRect().width : 0);
    const newWidth = trackBaseWidth ? trackBaseWidth * zoom : 0;

    if (timelineTrack && newWidth) {
      timelineTrack.style.width = `${newWidth}px`;
    }

    if (newWidth) {
      setTimelineWidthVar(newWidth);
    }

    barWrappers.forEach(wrapper => {
      if (newWidth) {
        wrapper.style.width = `${newWidth}px`;
      }
    });

    timelineElements.forEach(el => {
      const baseLeft = parseFloat(el.dataset.baseLeft || "");
      if (!Number.isNaN(baseLeft)) {
        el.style.left = `${baseLeft * zoom}px`;
      }
      const baseWidth = parseFloat(el.dataset.baseWidth || "");
      if (!Number.isNaN(baseWidth)) {
        el.style.width = `${baseWidth * zoom}px`;
      }
    });

    rows.forEach(row => {
      const bar = row.querySelector(".bar");
      if (!bar || !minStartDate) return;
      const startDate = parseDate(bar.dataset.start);
      const endDate = parseDate(bar.dataset.end);
      if (!startDate || !endDate) return;
      const offsetDays = daysBetween(minStartDate, startDate);
      const widthDays = daysBetween(startDate, endDate) + 1;
      bar.style.marginLeft = `${Math.max(0, offsetDays * currentPxPerDay)}px`;
      bar.style.width = `${Math.max(1, widthDays * currentPxPerDay)}px`;
    });

    requestAnimationFrame(drawDependencyArrows);
  }

  applyZoom(zoom);

  const zoomInBtn = document.getElementById("zoom-in");
  const zoomOutBtn = document.getElementById("zoom-out");
  const zoomResetBtn = document.getElementById("zoom-reset");

  if (zoomInBtn) {
    zoomInBtn.addEventListener("click", () => applyZoom(zoom + 0.25));
  }
  if (zoomOutBtn) {
    zoomOutBtn.addEventListener("click", () => applyZoom(zoom - 0.25));
  }
  if (zoomResetBtn) {
    zoomResetBtn.addEventListener("click", () => applyZoom(1));
  }

  setTimeout(scheduleArrowRedraw, 50);
  if (scrollElement) {
    scrollElement.addEventListener("scroll", scheduleArrowRedraw, { passive: true });
  }
  window.addEventListener("resize", scheduleArrowRedraw);

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
      const code = row.dataset.code;
      highlightDependencies(code);
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
      const deltaDays = Math.round(deltaPx / currentPxPerDay);
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
              bar.style.marginLeft = `${offsetDays * currentPxPerDay}px`;
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

    const code = modalTarget.dataset.code;
    applyDateChange(code, newStart, newEnd)
      .then(() => {
        closeModal();
      })
      .catch((err) => {
        alert(`Could not update dates: ${err.message}`);
      });
  });

  document.querySelectorAll(".draggable-bar").forEach(bar => {
    bar.addEventListener("dblclick", (e) => {
      e.stopPropagation();
      openModal(bar);
    });
  });

  /* ------------------------------------------------------------
     Undo/Redo System for Date Changes
  ------------------------------------------------------------ */
  const historyStack = [];
  let historyIndex = -1;
  const MAX_HISTORY = 50;

  function pushHistory(action) {
    // Remove any actions after current index (if user undid then made a new change)
    if (historyIndex < historyStack.length - 1) {
      historyStack.splice(historyIndex + 1);
    }
    historyStack.push(action);
    // Limit history size
    if (historyStack.length > MAX_HISTORY) {
      historyStack.shift();
    } else {
      historyIndex++;
    }
  }

  function applyDateChange(code, start, end, skipHistory = false) {
    const row = rowsByCode[code];
    if (!row) return Promise.reject(new Error("Task not found"));

    const bar = row.querySelector(".draggable-bar");
    if (!bar) return Promise.reject(new Error("Bar not found"));

    const oldStart = bar.dataset.start;
    const oldEnd = bar.dataset.end;

    return fetch(setDatesEndpoint, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "X-CSRFToken": csrfToken,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({ code, start, end }),
    })
      .then(async (resp) => {
        const text = await resp.text();
        let data = {};
        try {
          data = JSON.parse(text);
        } catch (_) {}
        if (!resp.ok || !data.ok) {
          throw new Error(data.error || text || `HTTP ${resp.status}`);
        }

        // Update UI
        bar.dataset.start = data.start;
        bar.dataset.end = data.end;
        const startDate = new Date(data.start + "T00:00:00");
        const endDate = new Date(data.end + "T00:00:00");
        const offsetDays = minStartDate ? daysBetween(minStartDate, startDate) : 0;
        bar.style.marginLeft = `${Math.max(0, offsetDays * currentPxPerDay)}px`;
        bar.style.width = `${Math.max(1, daysBetween(startDate, endDate) + 1) * currentPxPerDay}px`;
        updateRowDates(row, data.start, data.end);

        // Add to history
        if (!skipHistory) {
          pushHistory({
            type: "dateChange",
            code,
            oldStart,
            oldEnd,
            newStart: data.start,
            newEnd: data.end,
          });
        }

        return data;
      });
  }

  function undo() {
    if (historyIndex < 0) {
      console.log("Nothing to undo");
      return;
    }

    const action = historyStack[historyIndex];
    if (action.type === "dateChange") {
      applyDateChange(action.code, action.oldStart, action.oldEnd, true)
        .then(() => {
          historyIndex--;
          console.log("Undo successful");
        })
        .catch((err) => {
          console.error("Undo failed:", err);
          alert(`Undo failed: ${err.message}`);
        });
    }
  }

  function redo() {
    if (historyIndex >= historyStack.length - 1) {
      console.log("Nothing to redo");
      return;
    }

    historyIndex++;
    const action = historyStack[historyIndex];
    if (action.type === "dateChange") {
      applyDateChange(action.code, action.newStart, action.newEnd, true)
        .then(() => {
          console.log("Redo successful");
        })
        .catch((err) => {
          historyIndex--;
          console.error("Redo failed:", err);
          alert(`Redo failed: ${err.message}`);
        });
    }
  }

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

  /* ------------------------------------------------------------
     Toggle Critical Path Highlighting
  ------------------------------------------------------------ */
  const criticalPathBtn = document.getElementById("toggle-critical-path");
  let criticalPathVisible = false;

  if (criticalPathBtn) {
    criticalPathBtn.addEventListener("click", () => {
      criticalPathVisible = !criticalPathVisible;
      criticalPathBtn.style.opacity = criticalPathVisible ? "1" : "0.6";
      criticalPathBtn.title = criticalPathVisible
        ? "Hide critical path"
        : "Show critical path";

      // Toggle visual styles for all bars
      document.querySelectorAll(".bar.critical-path").forEach(bar => {
        if (criticalPathVisible) {
          bar.style.display = "";
        } else {
          bar.style.opacity = "0.5";
        }
      });

      // For hidden, make less prominent but still visible
      if (!criticalPathVisible) {
        document.querySelectorAll(".bar:not(.critical-path)").forEach(bar => {
          bar.style.opacity = "0.3";
        });
      } else {
        document.querySelectorAll(".bar:not(.critical-path)").forEach(bar => {
          bar.style.opacity = "1";
        });
      }

      // Redraw dependency arrows if they exist
      if (typeof redrawDependencyArrows === "function") {
        redrawDependencyArrows();
      }
    });

    // Start with critical path visible
    criticalPathVisible = true;
  }

  /* ------------------------------------------------------------
     Toggle Baseline (Actual vs Planned) Comparison
  ------------------------------------------------------------ */
  const baselineBtn = document.getElementById("toggle-baseline");
  let baselineVisible = false;

  if (baselineBtn) {
    baselineBtn.addEventListener("click", () => {
      baselineVisible = !baselineVisible;
      baselineBtn.style.opacity = baselineVisible ? "1" : "0.6";
      baselineBtn.title = baselineVisible
        ? "Hide baseline (actual dates)"
        : "Show baseline (actual dates)";

      // Update baseline bar visibility and styling
      document.querySelectorAll(".baseline-bar").forEach(bar => {
        if (baselineVisible) {
          bar.style.display = "";
          // Color code based on schedule variance
          const wrapper = bar.parentElement;
          const plannedBar = wrapper?.querySelector(".draggable-bar");
          if (plannedBar && plannedBar.dataset.hasActual === "true") {
            // Get variance from title attribute (format: "..., Variance: X days")
            const title = bar.title;
            const varianceMatch = title.match(/Variance: (-?\d+)/);
            if (varianceMatch) {
              const variance = parseInt(varianceMatch[1], 10);
              bar.classList.remove("behind-schedule", "ahead-schedule");
              if (variance > 0) {
                bar.classList.add("behind-schedule");
              } else if (variance < 0) {
                bar.classList.add("ahead-schedule");
              }
            }
          }
        } else {
          bar.style.display = "none";
        }
      });
    });
  }

  /* ------------------------------------------------------------
     Export Gantt to PNG
  ------------------------------------------------------------ */
  const exportBtn = document.getElementById("export-gantt");
  if (exportBtn && typeof html2canvas !== "undefined") {
    exportBtn.addEventListener("click", async () => {
      exportBtn.disabled = true;
      exportBtn.textContent = "Exporting...";

      try {
        // Temporarily hide detail panel for cleaner export
        const detailPanel = document.getElementById("project-detail-panel");
        const wasCollapsed = detailPanel?.classList.contains("collapsed");
        if (detailPanel && !wasCollapsed) {
          detailPanel.classList.add("collapsed");
        }

        // Capture the gantt-main container
        const target = document.querySelector(".gantt-main");
        if (!target) {
          throw new Error("Gantt container not found");
        }

        const canvas = await html2canvas(target, {
          backgroundColor: document.body.classList.contains("theme-dark") ? "#0f172a" : "#ffffff",
          scale: 2,
          useCORS: true,
          logging: false,
          windowWidth: target.scrollWidth,
          windowHeight: target.scrollHeight,
        });

        // Restore panel visibility
        if (detailPanel && !wasCollapsed) {
          detailPanel.classList.remove("collapsed");
        }

        // Download as PNG
        const link = document.createElement("a");
        const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, "-");
        link.download = `gantt-${timestamp}.png`;
        link.href = canvas.toDataURL("image/png");
        link.click();
      } catch (err) {
        alert(`Export failed: ${err.message}`);
      } finally {
        exportBtn.disabled = false;
        exportBtn.textContent = "Export PNG";
      }
    });
  }

  /* ------------------------------------------------------------
     Inline Editing for Task Names
     ------------------------------------------------------------ */
  const editableNames = document.querySelectorAll(".editable-name");

  editableNames.forEach(nameEl => {
    nameEl.addEventListener("dblclick", function(e) {
      e.stopPropagation();

      const code = this.dataset.code;
      const currentName = this.textContent.trim();

      // Create input element
      const input = document.createElement("input");
      input.type = "text";
      input.value = currentName;
      input.className = "inline-edit-input";
      input.style.width = `${Math.max(this.offsetWidth, 150)}px`;

      // Replace text with input
      const originalContent = this.innerHTML;
      this.innerHTML = "";
      this.appendChild(input);
      input.focus();
      input.select();

      // Save function
      const saveName = async () => {
        const newName = input.value.trim();

        if (!newName || newName === currentName) {
          // Revert if empty or unchanged
          this.innerHTML = originalContent;
          return;
        }

        try {

    /* ------------------------------------------------------------
       Resource conflict marker tooltips
    ------------------------------------------------------------ */
    (function initResourceConflictTooltips() {
      const tooltip = document.createElement("div");
      tooltip.className = "resource-conflict-tooltip";
      tooltip.style.position = "absolute";
      tooltip.style.pointerEvents = "none";
      tooltip.style.zIndex = 1200;
      tooltip.style.padding = "6px 8px";
      tooltip.style.background = "rgba(17,24,39,0.95)";
      tooltip.style.color = "#fff";
      tooltip.style.borderRadius = "6px";
      tooltip.style.fontSize = "12px";
      tooltip.style.boxShadow = "0 4px 12px rgba(2,6,23,0.6)";
      tooltip.style.display = "none";
      document.body.appendChild(tooltip);

      function showTooltip(e, el) {
        const date = el.dataset.date || "";
        const owners = el.dataset.owners || "";
        tooltip.innerText = date + (owners ? " — " + owners : "");
        tooltip.style.display = "block";
        position(e);
      }

      function hideTooltip() {
        tooltip.style.display = "none";
      }

      function position(e) {
        const padding = 8;
        const w = tooltip.offsetWidth;
        const h = tooltip.offsetHeight;
        let left = e.pageX + padding;
        let top = e.pageY - h - padding;
        if (left + w + padding > window.scrollX + window.innerWidth) {
          left = window.scrollX + window.innerWidth - w - padding;
        }
        if (top < window.scrollY + padding) {
          top = e.pageY + padding;
        }
        tooltip.style.left = left + "px";
        tooltip.style.top = top + "px";
      }

      document.querySelectorAll(".resource-conflict").forEach(el => {
        el.addEventListener("mouseenter", (e) => showTooltip(e, el));
        el.addEventListener("mousemove", (e) => position(e));
        el.addEventListener("mouseleave", hideTooltip);
        el.addEventListener("click", (e) => {
          // On click, jump the timeline view roughly to that date
          const date = el.dataset.date;
          if (!date) return;
          // Compute pixel offset from left of timeline and scroll to it
          const ganttScroll = document.querySelector(".gantt-scroll");
          if (!ganttScroll) return;
          const px = parseFloat(el.style.left || "0");
          const target = Math.max(0, px - ganttScroll.clientWidth / 2);
          ganttScroll.scrollTo({ left: target, behavior: "smooth" });
        });
      });
    })();
          // Show loading state
          this.innerHTML = '<span class="saving">Saving...</span>';

          const response = await fetch("/gantt/update-name/", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": csrfToken,
            },
            body: JSON.stringify({
              code: code,
              name: newName
            })
          });

          if (response.ok) {
            const data = await response.json();
            this.textContent = data.name;
            this.title = "Double-click to edit";

            // Update data attribute in row
            const row = this.closest("tr");
            if (row) {
              row.dataset.wbsName = data.name;
            }
          } else {
            throw new Error("Failed to update name");
          }
        } catch (err) {
          console.error("Error updating task name:", err);
          alert("Failed to update task name. Please try again.");
          this.innerHTML = originalContent;
        }
      };

      // Handle Enter key
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          saveName();
        } else if (e.key === "Escape") {
          e.preventDefault();
          this.innerHTML = originalContent;
        }
      });

      // Handle blur (click away)
      input.addEventListener("blur", () => {
        saveName();
      });
    });

    // Add visual hint on hover
    nameEl.style.cursor = "text";
  });

  /* ------------------------------------------------------------
     Search Autocomplete
     ------------------------------------------------------------ */
  const searchInput = document.getElementById("gantt-search");
  const suggestionsDropdown = document.getElementById("search-suggestions");
  let autocompleteTimeout = null;
  let selectedSuggestionIndex = -1;

  if (searchInput && suggestionsDropdown) {
    // Fetch suggestions
    const fetchSuggestions = async (query) => {
      if (!query || query.length < 2) {
        suggestionsDropdown.style.display = "none";
        return;
      }

      try {
        const response = await fetch(`/gantt/search/?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        if (data.suggestions && data.suggestions.length > 0) {
          renderSuggestions(data.suggestions);
          suggestionsDropdown.style.display = "block";
        } else {
          suggestionsDropdown.style.display = "none";
        }
      } catch (err) {
        console.error("Autocomplete error:", err);
      }
    };

    // Render suggestions
    const renderSuggestions = (suggestions) => {
      selectedSuggestionIndex = -1;
      suggestionsDropdown.innerHTML = suggestions
        .map(
          (s, idx) => `
          <div class="autocomplete-item" data-index="${idx}" data-value="${s.value}">
            <span class="autocomplete-icon">${s.icon}</span>
            <span class="autocomplete-label">${s.label}</span>
          </div>
        `
        )
        .join("");

      // Add click handlers
      const items = suggestionsDropdown.querySelectorAll(".autocomplete-item");
      items.forEach((item) => {
        item.addEventListener("click", () => {
          searchInput.value = item.dataset.value;
          suggestionsDropdown.style.display = "none";
          searchInput.form.submit();
        });
      });
    };

    // Input event with debounce
    searchInput.addEventListener("input", (e) => {
      clearTimeout(autocompleteTimeout);
      autocompleteTimeout = setTimeout(() => {
        fetchSuggestions(e.target.value);
      }, 300);
    });

    // Keyboard navigation
    searchInput.addEventListener("keydown", (e) => {
      const items = suggestionsDropdown.querySelectorAll(".autocomplete-item");

      if (e.key === "ArrowDown") {
        e.preventDefault();
        selectedSuggestionIndex = Math.min(selectedSuggestionIndex + 1, items.length - 1);
        updateSelectedSuggestion(items);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        selectedSuggestionIndex = Math.max(selectedSuggestionIndex - 1, -1);
        updateSelectedSuggestion(items);
      } else if (e.key === "Enter" && selectedSuggestionIndex >= 0) {
        e.preventDefault();
        const selected = items[selectedSuggestionIndex];
        if (selected) {
          searchInput.value = selected.dataset.value;
          suggestionsDropdown.style.display = "none";
          searchInput.form.submit();
        }
      } else if (e.key === "Escape") {
        suggestionsDropdown.style.display = "none";
        selectedSuggestionIndex = -1;
      }
    });

    // Update visual selection
    const updateSelectedSuggestion = (items) => {
      items.forEach((item, idx) => {
        if (idx === selectedSuggestionIndex) {
          item.classList.add("selected");
        } else {
          item.classList.remove("selected");
        }
      });
    };

    // Close dropdown when clicking outside
    document.addEventListener("click", (e) => {
      if (!searchInput.contains(e.target) && !suggestionsDropdown.contains(e.target)) {
        suggestionsDropdown.style.display = "none";
      }
    });

    // Focus input on load if there's a query
    if (searchInput.value) {
      searchInput.focus();
    }
  }

  /* ------------------------------------------------------------
     Keyboard Shortcuts
     ------------------------------------------------------------ */
  const timelineScroll = document.querySelector(".gantt-timeline-scroll");
  const helpModal = document.getElementById("keyboard-help-modal");
  const helpCloseBtn = helpModal?.querySelector(".close-help");

  // Close help modal
  if (helpCloseBtn) {
    helpCloseBtn.addEventListener("click", () => {
      helpModal.style.display = "none";
    });
  }

  // Keyboard event handler
  document.addEventListener("keydown", (e) => {
    // Ignore if typing in input/textarea
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") {
      return;
    }

    // Ignore if modal is open (except ESC)
    const editModal = document.getElementById("edit-modal");
    const modalOpen = editModal && editModal.style.display === "flex";
    if (modalOpen && e.key !== "Escape") {
      return;
    }

    switch (e.key) {
      // ESC - Close modals
      case "Escape":
        if (editModal && editModal.style.display === "flex") {
          editModal.style.display = "none";
        }
        if (helpModal && helpModal.style.display === "flex") {
          helpModal.style.display = "none";
        }
        break;

      // Arrow keys - Pan timeline
      case "ArrowLeft":
        e.preventDefault();
        if (timelineScroll) {
          timelineScroll.scrollLeft -= 100;
        }
        break;

      case "ArrowRight":
        e.preventDefault();
        if (timelineScroll) {
          timelineScroll.scrollLeft += 100;
        }
        break;

      case "ArrowUp":
        e.preventDefault();
        window.scrollBy(0, -50);
        break;

      case "ArrowDown":
        e.preventDefault();
        window.scrollBy(0, 50);
        break;

      // + or = - Zoom in
      case "+":
      case "=":
        e.preventDefault();
        document.getElementById("zoom-in")?.click();
        break;

      // - - Zoom out
      case "-":
        e.preventDefault();
        document.getElementById("zoom-out")?.click();
        break;

      // T - Jump to today
      case "t":
      case "T":
        e.preventDefault();
        document.querySelector(".zoom-button[data-preset='daily']")?.click();
        if (minStartDate && timelineScroll) {
          const today = new Date();
          const daysFromStart = daysBetween(minStartDate, today);
          const scrollPos = daysFromStart * currentPxPerDay - (timelineScroll.clientWidth / 2);
          timelineScroll.scrollLeft = Math.max(0, scrollPos);
        }
        break;

      // D - Toggle dependencies
      case "d":
      case "D":
        e.preventDefault();
        document.getElementById("toggle-deps")?.click();
        break;

      // P - Toggle project items panel
      case "p":
      case "P":
        e.preventDefault();
        document.getElementById("toggle-panel")?.click();
        break;

      // ? - Show keyboard shortcuts help
      case "?":
        e.preventDefault();
        if (helpModal) {
          helpModal.style.display = "flex";
        }
        break;

      // O - Optimize schedule
      case "o":
      case "O":
        if (e.ctrlKey || e.metaKey) {
          e.preventDefault();
          const optimizeBtn = document.getElementById("optimize-btn");
          if (optimizeBtn && !optimizeBtn.disabled) {
            optimizeBtn.click();
          }
        }
        break;

      // Ctrl+Z - Undo
      case "z":
      case "Z":
        if (e.ctrlKey || e.metaKey) {
          if (e.shiftKey) {
            // Ctrl+Shift+Z - Redo
            e.preventDefault();
            redo();
          } else {
            // Ctrl+Z - Undo
            e.preventDefault();
            undo();
          }
        }
        break;

      // Ctrl+Y - Redo (alternative)
      case "y":
      case "Y":
        if (e.ctrlKey || e.metaKey) {
          e.preventDefault();
          redo();
        }
        break;

      // Home - Scroll to top
      case "Home":
        e.preventDefault();
        window.scrollTo(0, 0);
        if (timelineScroll) {
          timelineScroll.scrollLeft = 0;
        }
        break;

      // End - Scroll to bottom
      case "End":
        e.preventDefault();
        window.scrollTo(0, document.body.scrollHeight);
        break;
    }
  });

  /* ------------------------------------------------------------
     Bulk Selection and Operations
  ------------------------------------------------------------ */
  const selectAllCheckbox = document.getElementById("select-all-tasks");
  const taskCheckboxes = document.querySelectorAll(".task-checkbox");
  const bulkToolbar = document.getElementById("bulk-actions-toolbar");
  const selectedCountEl = document.getElementById("selected-count");
  const bulkClearBtn = document.getElementById("bulk-clear");
  const bulkDeleteBtn = document.getElementById("bulk-delete");
  const bulkExportBtn = document.getElementById("bulk-export");
  const bulkStatusBtn = document.getElementById("bulk-change-status");
  const bulkAssignBtn = document.getElementById("bulk-assign-owner");

  let selectedTasks = new Set();

  function updateBulkToolbar() {
    const count = selectedTasks.size;
    if (count > 0) {
      bulkToolbar.style.display = "block";
      selectedCountEl.textContent = count;
    } else {
      bulkToolbar.style.display = "none";
    }
  }

  function getSelectedCodes() {
    return Array.from(selectedTasks);
  }

  // Select all checkbox
  if (selectAllCheckbox) {
    selectAllCheckbox.addEventListener("change", (e) => {
      const checked = e.target.checked;
      taskCheckboxes.forEach(cb => {
        cb.checked = checked;
        if (checked) {
          selectedTasks.add(cb.dataset.code);
        } else {
          selectedTasks.delete(cb.dataset.code);
        }
      });
      updateBulkToolbar();
    });
  }

  // Individual task checkboxes
  taskCheckboxes.forEach(cb => {
    cb.addEventListener("change", (e) => {
      if (e.target.checked) {
        selectedTasks.add(e.target.dataset.code);
      } else {
        selectedTasks.delete(e.target.dataset.code);
        if (selectAllCheckbox) selectAllCheckbox.checked = false;
      }
      updateBulkToolbar();

      // If all are checked, check select-all
      if (selectedTasks.size === taskCheckboxes.length && selectAllCheckbox) {
        selectAllCheckbox.checked = true;
      }
    });
  });

  // Clear selection
  if (bulkClearBtn) {
    bulkClearBtn.addEventListener("click", () => {
      selectedTasks.clear();
      taskCheckboxes.forEach(cb => cb.checked = false);
      if (selectAllCheckbox) selectAllCheckbox.checked = false;
      updateBulkToolbar();
    });
  }

  // Bulk delete
  if (bulkDeleteBtn) {
    bulkDeleteBtn.addEventListener("click", () => {
      const codes = getSelectedCodes();
      if (codes.length === 0) return;

      if (!confirm(`Delete ${codes.length} selected task(s)? This action cannot be undone.`)) {
        return;
      }

      alert("Bulk delete not yet implemented. Selected codes: " + codes.join(", "));
      // TODO: Implement bulk delete endpoint
    });
  }

  // Bulk export
  if (bulkExportBtn) {
    bulkExportBtn.addEventListener("click", () => {
      const codes = getSelectedCodes();
      if (codes.length === 0) return;

      // Create CSV export
      const rows = codes.map(code => {
        const row = rowsByCode[code];
        if (!row) return null;
        const taskName = row.dataset.wbsName || "";
        const bar = row.querySelector(".draggable-bar");
        const start = bar?.dataset.start || "";
        const end = bar?.dataset.end || "";
        return [code, taskName, start, end];
      }).filter(Boolean);

      const csv = [
        ["Code", "Task Name", "Start", "End"],
        ...rows
      ].map(row => row.map(cell => `"${cell}"`).join(",")).join("\n");

      const blob = new Blob([csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `gantt-export-${new Date().toISOString().slice(0,10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    });
  }

  // Bulk status change
  if (bulkStatusBtn) {
    bulkStatusBtn.addEventListener("click", () => {
      const codes = getSelectedCodes();
      if (codes.length === 0) return;

      const status = prompt("Enter new status (e.g., Not Started, In Progress, Complete):");
      if (!status) return;

      alert(`Bulk status change not yet implemented. Would set ${codes.length} task(s) to: ${status}`);
      // TODO: Implement bulk status endpoint
    });
  }

  // Bulk assign owner
  if (bulkAssignBtn) {
    bulkAssignBtn.addEventListener("click", () => {
      const codes = getSelectedCodes();
      if (codes.length === 0) return;

      const owner = prompt("Enter owner username or name:");
      if (!owner) return;

      alert(`Bulk assign not yet implemented. Would assign ${codes.length} task(s) to: ${owner}`);
      // TODO: Implement bulk assign endpoint
    });
  }

  /* ------------------------------------------------------------
     Theme toggle (light / dark) with localStorage persistence
     ------------------------------------------------------------ */
  // Uses initializeThemeToggle() from shared-theme.js
  initializeThemeToggle("toggle-theme", "ganttTheme", "dark");
});
