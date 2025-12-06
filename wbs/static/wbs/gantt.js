// wbs/static/wbs/gantt.js
// Requires: shared-theme.js (for getCSRFToken)

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

        drawDependencyArrows();
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

      drawDependencyArrows();
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

      drawDependencyArrows();
    });
  }

  /* ------------------------------------------------------------
     Dependency arrow visualization (simplified)
  ------------------------------------------------------------ */
  const depSvg = document.getElementById("dependency-svg");
  const scrollElement = document.querySelector(".gantt-scroll");

  function drawDependencyArrows() {
    if (!depSvg || !scrollElement) return;

    // Clear existing arrows
    while (depSvg.firstChild) {
      depSvg.removeChild(depSvg.firstChild);
    }

    const scrollRect = scrollElement.getBoundingClientRect();
    const svgWidth = scrollElement.scrollWidth;
    const svgHeight = scrollElement.scrollHeight;

    depSvg.setAttribute("width", svgWidth);
    depSvg.setAttribute("height", svgHeight);
    depSvg.style.width = `${svgWidth}px`;
    depSvg.style.height = `${svgHeight}px`;

    const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    const marker = document.createElementNS("http://www.w3.org/2000/svg", "marker");
    marker.setAttribute("id", "arrowhead");
    marker.setAttribute("markerWidth", "8");
    marker.setAttribute("markerHeight", "8");
    marker.setAttribute("refX", "7");
    marker.setAttribute("refY", "3");
    marker.setAttribute("orient", "auto");
    const polygon = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
    polygon.setAttribute("points", "0 0, 8 3, 0 6");
    polygon.setAttribute("fill", "#42c778");
    marker.appendChild(polygon);
    defs.appendChild(marker);
    depSvg.appendChild(defs);

    // Draw arrows for each dependency (anchor to bars)
    rows.forEach(row => {
      // Skip collapsed/hidden rows
      if (row.style.display === "none") return;
      const code = row.dataset.code;
      const succs = (row.dataset.successors || "").split(",").filter(Boolean);
      const succLinksRaw = (row.dataset.successorMeta || "").split("|").filter(Boolean);
      const succLinks = succLinksRaw.map(s => {
        const parts = s.split(":");
        return { code: parts[0], type: parts[1] || "FS", lag: parseInt(parts[2] || "0", 10) || 0 };
      });
      const succByCode = {};
      succLinks.forEach(link => { succByCode[link.code] = link; });
      const predBar = row.querySelector(".bar");
      if (!predBar) return;
      const predRect = predBar.getBoundingClientRect();

      succs.forEach(succCode => {
        const succRow = rowsByCode[succCode];
        if (!succRow) return;
        const succBar = succRow.querySelector(".bar");
        if (!succBar) return;
        const succRect = succBar.getBoundingClientRect();

        // Skip if both bars are out of view vertically
        if (predRect.bottom < scrollRect.top && succRect.bottom < scrollRect.top) return;
        if (predRect.top > scrollRect.bottom && succRect.top > scrollRect.bottom) return;

        const linkMeta = succByCode[succCode] || { type: "FS", lag: 0 };
        const depType = (linkMeta.type || "FS").toUpperCase();
        const depColor = {
          FS: "#42c778",
          SS: "#4da3ff",
          FF: "#f39c12",
          SF: "#e56bff",
        };

        const y1 = predRect.top - scrollRect.top + predRect.height / 2 + scrollElement.scrollTop;
        const y2 = succRect.top - scrollRect.top + succRect.height / 2 + scrollElement.scrollTop;
        let x1, x2;

        // Anchor points based on dependency type
        switch (depType) {
          case "SS":
            x1 = predRect.left - scrollRect.left + scrollElement.scrollLeft;
            x2 = succRect.left - scrollRect.left + scrollElement.scrollLeft;
            break;
          case "FF":
            x1 = predRect.right - scrollRect.left + scrollElement.scrollLeft;
            x2 = succRect.right - scrollRect.left + scrollElement.scrollLeft;
            break;
          case "SF":
            x1 = predRect.left - scrollRect.left + scrollElement.scrollLeft;
            x2 = succRect.right - scrollRect.left + scrollElement.scrollLeft;
            break;
          case "FS":
          default:
            x1 = predRect.right - scrollRect.left + scrollElement.scrollLeft;
            x2 = succRect.left - scrollRect.left + scrollElement.scrollLeft;
            break;
        }

        // Draw a smooth path from pred end to succ start
        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        const midX = x1 + Math.max(12, (x2 - x1) * 0.35);
        const d = `M ${x1} ${y1} C ${midX} ${y1}, ${x2 - 12} ${y2}, ${x2} ${y2}`;
        path.setAttribute("d", d);
        path.setAttribute("fill", "none");
        path.setAttribute("stroke", depColor[depType] || "#42c778");
        path.setAttribute("stroke-width", "1.4");
        path.setAttribute("opacity", "0.8");
        path.setAttribute("marker-end", "url(#arrowhead)");
        path.setAttribute("class", `dependency-arrow dep-type-${depType.toLowerCase()}`);
        path.setAttribute("data-pred", code);
        path.setAttribute("data-succ", succCode);

        depSvg.appendChild(path);

        if (linkMeta.lag && linkMeta.lag !== 0) {
          const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
          const labelX = x1 + (x2 - x1) * 0.6;
          const labelY = y1 + (y2 - y1) * 0.4;
          text.setAttribute("x", labelX);
          text.setAttribute("y", labelY);
          text.setAttribute("class", "dep-lag");
          text.textContent = `+${linkMeta.lag}d`;
          depSvg.appendChild(text);
        }
      });
    });
  }

  // Draw on load with delay
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      setTimeout(drawDependencyArrows, 50);
    });
  } else {
    setTimeout(drawDependencyArrows, 50);
  }

  // Redraw on scroll
  if (scrollElement) {
    scrollElement.addEventListener("scroll", drawDependencyArrows);
  }

  // Redraw on window resize
  window.addEventListener("resize", drawDependencyArrows);

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

    // Clear arrow highlighting
    if (depSvg) {
      const arrows = depSvg.querySelectorAll(".dependency-arrow");
      arrows.forEach(a => {
        a.setAttribute("opacity", "0.5");
        a.setAttribute("stroke-width", "2");
      });
    }
  }

  function highlightDependencies(code) {
    clearHighlights();

    const preds = (rowsByCode[code]?.dataset.predecessors || "")
      .split(",")
      .filter(Boolean);
    const succs = (rowsByCode[code]?.dataset.successors || "")
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

    // Highlight related arrows
    if (depSvg) {
      const arrows = depSvg.querySelectorAll(".dependency-arrow");
      arrows.forEach(a => {
        const pred = a.getAttribute("data-pred");
        const succ = a.getAttribute("data-succ");
        const isRelated = pred === code || succ === code || preds.includes(pred) || succs.includes(succ);

        if (isRelated) {
          a.setAttribute("opacity", "1");
          a.setAttribute("stroke-width", "3");
        }
      });
    }
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

  /* ------------------------------------------------------------
     Theme toggle (light / dark) with localStorage persistence
     ------------------------------------------------------------ */
  // Uses initializeThemeToggle() from shared-theme.js
  initializeThemeToggle("toggle-theme", "ganttTheme", "dark");
});
