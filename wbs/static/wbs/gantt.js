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
        modalTarget.style.marginLeft = `${Math.max(0, offsetDays * currentPxPerDay)}px`;
        modalTarget.style.width = `${Math.max(1, daysBetween(startDate, endDate) + 1) * currentPxPerDay}px`;
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
     Theme toggle (light / dark) with localStorage persistence
     ------------------------------------------------------------ */
  // Uses initializeThemeToggle() from shared-theme.js
  initializeThemeToggle("toggle-theme", "ganttTheme", "dark");
});
