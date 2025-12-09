// wbs/static/wbs/gantt-arrows.js
import { redrawAsync } from "./gantt-utils.js";

// Builds arrow drawing/highlight helpers
export function createArrowDrawer({ rows, rowsByCode, scrollElement, depSvg }) {
  const isHidden = el => !el || el.offsetParent === null || el.style.display === "none";

  // Arrowhead markers for each dependency type
  function createArrowheadDefs() {
    const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");

    const depTypes = [
      { id: "arrowhead-fs", fill: "#42c778" },
      { id: "arrowhead-ss", fill: "#4da3ff" },
      { id: "arrowhead-ff", fill: "#f39c12" },
      { id: "arrowhead-sf", fill: "#e56bff" },
    ];

    depTypes.forEach(({ id, fill }) => {
      const marker = document.createElementNS("http://www.w3.org/2000/svg", "marker");
      marker.setAttribute("id", id);
      marker.setAttribute("markerWidth", "5");
      marker.setAttribute("markerHeight", "4");
      marker.setAttribute("refX", "4.5");
      marker.setAttribute("refY", "2");
      marker.setAttribute("orient", "auto");
      const polygon = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
      polygon.setAttribute("points", "0 0, 5 2, 0 4");
      polygon.setAttribute("fill", fill);
      marker.appendChild(polygon);
      defs.appendChild(marker);
    });

    return defs;
  }

  function drawDependencyArrows() {
    if (!depSvg || !scrollElement) return;

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

    depSvg.appendChild(createArrowheadDefs());

    rows.forEach(row => {
      if (isHidden(row)) return;
      const code = row.dataset.code;
      const succs = (row.dataset.successors || "").split(",").filter(Boolean);
      const succLinksRaw = (row.dataset.successorMeta || "").split("|").filter(Boolean);
      const succLinks = succLinksRaw.map(s => {
        const parts = s.split(":");
        return { code: parts[0], type: parts[1] || "FS", lag: parseInt(parts[2] || "0", 10) || 0 };
      });
      const succByCode = {};
      succLinks.forEach(link => {
        succByCode[link.code] = link;
      });
      const predBar = row.querySelector(".bar");
      if (!predBar) return;

      // Use cell positions instead of magic offsets
      const predRect = predBar.getBoundingClientRect();
      const predCellRight = predRect.right - scrollRect.left + scrollElement.scrollLeft;
      const predCellLeft = predRect.left - scrollRect.left + scrollElement.scrollLeft;
      const predY = predRect.top - scrollRect.top + predRect.height / 2 + scrollElement.scrollTop;

      succs.forEach(succCode => {
        const succRow = rowsByCode[succCode];
        if (!succRow) return;
        if (isHidden(succRow)) return;
        const succBar = succRow.querySelector(".bar");
        if (!succBar) return;
        const succRect = succBar.getBoundingClientRect();

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
        const arrowheadRef = {
          FS: "arrowhead-fs",
          SS: "arrowhead-ss",
          FF: "arrowhead-ff",
          SF: "arrowhead-sf",
        };

        // Calculate endpoint positions based on dependency type
        let x1, x2;
        const succCellRight = succRect.right - scrollRect.left + scrollElement.scrollLeft;
        const succCellLeft = succRect.left - scrollRect.left + scrollElement.scrollLeft;
        const succY = succRect.top - scrollRect.top + succRect.height / 2 + scrollElement.scrollTop;

        switch (depType) {
          case "SS": // Start-to-Start
            x1 = predCellLeft;
            x2 = succCellLeft;
            break;
          case "FF": // Finish-to-Finish
            x1 = predCellRight;
            x2 = succCellRight;
            break;
          case "SF": // Start-to-Finish
            x1 = predCellLeft;
            x2 = succCellRight;
            break;
          case "FS": // Finish-to-Start
          default:
            x1 = predCellRight;
            x2 = succCellLeft;
            break;
        }

        // Draw curved path (bezier curve)
        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        const midX = x1 + Math.max(12, (x2 - x1) * 0.35);
        const d = `M ${x1} ${predY} C ${midX} ${predY}, ${x2 - 12} ${succY}, ${x2} ${succY}`;
        path.setAttribute("d", d);
        path.setAttribute("fill", "none");
        path.setAttribute("stroke", depColor[depType] || "#42c778");
        path.setAttribute("stroke-width", "1.4");
        path.setAttribute("opacity", "0.8");
        path.setAttribute("marker-end", `url(#${arrowheadRef[depType]})`);
        path.setAttribute("class", `dependency-arrow dep-type-${depType.toLowerCase()}`);
        path.setAttribute("data-pred", code);
        path.setAttribute("data-succ", succCode);
        path.setAttribute("data-dep-type", depType);

        depSvg.appendChild(path);

        // Add dependency type label near the start of the arrow
        const typeLabel = document.createElementNS("http://www.w3.org/2000/svg", "text");
        const typeLabelX = x1 + Math.min(25, (x2 - x1) * 0.15);
        const typeLabelY = predY - 8;
        typeLabel.setAttribute("x", typeLabelX);
        typeLabel.setAttribute("y", typeLabelY);
        typeLabel.setAttribute("class", `dep-type-label dep-type-${depType.toLowerCase()}`);
        typeLabel.setAttribute("data-dep-type", depType);
        typeLabel.textContent = depType;
        depSvg.appendChild(typeLabel);

        // Add lag label if lag ≠ 0
        if (linkMeta.lag && linkMeta.lag !== 0) {
          const lagText = document.createElementNS("http://www.w3.org/2000/svg", "text");
          const lagX = x1 + (x2 - x1) * 0.6;
          const lagY = predY + (succY - predY) * 0.5 + 10;
          lagText.setAttribute("x", lagX);
          lagText.setAttribute("y", lagY);
          lagText.setAttribute("class", "dep-lag");
          lagText.textContent = linkMeta.lag > 0 ? `+${linkMeta.lag}d` : `${linkMeta.lag}d`;
          depSvg.appendChild(lagText);
        }
      });
    });
  }

  function clearHighlights() {
    rows.forEach(r => {
      r.classList.remove("highlight-row");
      const bar = r.querySelector(".bar");
      if (bar) {
        bar.classList.remove("highlight-bar");
      }
    });

    if (depSvg) {
      const arrows = depSvg.querySelectorAll(".dependency-arrow");
      arrows.forEach(a => {
        a.setAttribute("opacity", "0.5");
        a.setAttribute("stroke-width", "2");
        a.classList.remove("highlighted-arrow");
      });

      const labels = depSvg.querySelectorAll(".dep-type-label");
      labels.forEach(label => {
        label.setAttribute("opacity", "0.6");
      });
    }
  }

  function highlightDependencies(code) {
    clearHighlights();

    const predData = rowsByCode[code];
    if (!predData) return;

    const preds = (predData.dataset.predecessors || "")
      .split(",")
      .filter(Boolean);
    const succs = (predData.dataset.successors || "")
      .split(",")
      .filter(Boolean);

    const allCodes = new Set();
    if (code) allCodes.add(code);
    preds.forEach(c => allCodes.add(c));
    succs.forEach(c => allCodes.add(c));

    // Highlight rows
    allCodes.forEach(c => {
      const r = rowsByCode[c];
      if (!r) return;
      r.classList.add("highlight-row");
      const bar = r.querySelector(".bar");
      if (bar) {
        bar.classList.add("highlight-bar");
      }
    });

    // Highlight arrows and labels related to this code
    if (depSvg) {
      const arrows = depSvg.querySelectorAll(".dependency-arrow");
      arrows.forEach(a => {
        const pred = a.getAttribute("data-pred");
        const succ = a.getAttribute("data-succ");

        // Check if arrow is related to the selected code or its dependencies
        const isRelated =
          pred === code ||
          succ === code ||
          preds.includes(pred) ||
          preds.includes(succ) ||
          succs.includes(pred) ||
          succs.includes(succ);

        if (isRelated) {
          a.setAttribute("opacity", "1");
          a.setAttribute("stroke-width", "3");
          a.classList.add("highlighted-arrow");

          // Also highlight related labels
          const depType = a.getAttribute("data-dep-type");
          const relatedLabels = depSvg.querySelectorAll(
            `.dep-type-label[data-dep-type="${depType}"]`
          );
          relatedLabels.forEach(label => {
            // Check if label is near this arrow
            const labelX = parseFloat(label.getAttribute("x"));
            const arrowPath = a.getAttribute("d");
            if (arrowPath && arrowPath.includes(`M ${labelX}`)) {
              label.setAttribute("opacity", "1");
            }
          });
        }
      });
    }
  }

  // Allow keyboard/click selection to trigger highlighting
  function setupArrowInteractions() {
    if (!depSvg) return;

    depSvg.addEventListener("click", (e) => {
      const arrow = e.target.closest(".dependency-arrow");
      if (arrow) {
        const predCode = arrow.getAttribute("data-pred");
        highlightDependencies(predCode);
      }
    });

    depSvg.addEventListener("mouseenter", (e) => {
      const arrow = e.target.closest(".dependency-arrow");
      if (arrow) {
        const predCode = arrow.getAttribute("data-pred");
        highlightDependencies(predCode);
      }
    }, true);

    depSvg.addEventListener("mouseleave", clearHighlights);
  }

  const redraw = () => {
    redrawAsync(drawDependencyArrows);
    setupArrowInteractions();
  };

  return { drawDependencyArrows, redrawAsync: redraw, clearHighlights, highlightDependencies, setupArrowInteractions };
}
