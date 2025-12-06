// wbs/static/wbs/gantt-expand.js
import { getDescendants, isAnyAncestorCollapsed, redrawAsync } from "./gantt-utils.js";

export function initExpandCollapse({ rows, rowsByCode, parentByCode, drawDependencyArrows }) {
  const redraw = () => redrawAsync(drawDependencyArrows);

  document
    .querySelectorAll(".expander[data-has-children='true']")
    .forEach(exp => {
      const row = exp.closest("tr.gantt-row");
      const code = row?.dataset.code;
      if (!row || !code) return;

      exp.addEventListener("click", event => {
        event.stopPropagation();

        const currentlyExpanded = exp.dataset.expanded === "true";
        const newExpanded = !currentlyExpanded;

        exp.dataset.expanded = newExpanded ? "true" : "false";
        exp.setAttribute("aria-expanded", newExpanded ? "true" : "false");
        exp.textContent = newExpanded ? "▾" : "▸";

        const descendants = getDescendants(code, rows);

        if (!newExpanded) {
          descendants.forEach(r => {
            r.style.display = "none";
          });
        } else {
          descendants.forEach(r => {
            if (!isAnyAncestorCollapsed(r.dataset.code, parentByCode, rowsByCode)) {
              r.style.display = "";
            }
          });
        }

        redraw();
      });
    });

  const expandAllBtn = document.getElementById("expand-all");
  const collapseAllBtn = document.getElementById("collapse-all");

  if (expandAllBtn) {
    expandAllBtn.addEventListener("click", () => {
      document
        .querySelectorAll(".expander[data-has-children='true']")
        .forEach(exp => {
          exp.dataset.expanded = "true";
          exp.setAttribute("aria-expanded", "true");
          exp.textContent = "▾";
        });

      rows.forEach(row => {
        row.style.display = "";
      });

      redraw();
    });
  }

  if (collapseAllBtn) {
    collapseAllBtn.addEventListener("click", () => {
      document
        .querySelectorAll(".expander[data-has-children='true']")
        .forEach(exp => {
          exp.dataset.expanded = "false";
          exp.setAttribute("aria-expanded", "false");
          exp.textContent = "▸";
        });

      rows.forEach(row => {
        const parentCode = row.dataset.parentCode || "";
        row.style.display = parentCode ? "none" : "";
      });

      redraw();
    });
  }
}
