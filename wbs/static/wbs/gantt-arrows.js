// wbs/static/wbs/gantt-arrows.js
import { redrawAsync } from "./gantt-utils.js";

// Builds arrow drawing/highlight helpers
export function createArrowDrawer({ rows, rowsByCode, scrollElement, depSvg }) {
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

    rows.forEach(row => {
      if (row.style.display === "none") return;
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
      const predRect = predBar.getBoundingClientRect();

      succs.forEach(succCode => {
        const succRow = rowsByCode[succCode];
        if (!succRow) return;
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

        const y1 = predRect.top - scrollRect.top + predRect.height / 2 + scrollElement.scrollTop;
        const y2 = succRect.top - scrollRect.top + succRect.height / 2 + scrollElement.scrollTop;
        let x1, x2;

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

  const redraw = () => redrawAsync(drawDependencyArrows);

  return { drawDependencyArrows, redrawAsync: redraw, clearHighlights, highlightDependencies };
}
