// wbs/static/wbs/gantt-utils.js
// Shared helpers for Gantt modules

export function buildRowIndex(rows) {
  const rowsByCode = {};
  const parentByCode = {};
  rows.forEach(row => {
    const code = row.dataset.code;
    const parentCode = row.dataset.parentCode || "";
    rowsByCode[code] = row;
    parentByCode[code] = parentCode;
  });
  return { rowsByCode, parentByCode };
}

export function getDescendants(code, rows) {
  const prefix = code + ".";
  return rows.filter(r => r.dataset.code.startsWith(prefix));
}

export function isAnyAncestorCollapsed(code, parentByCode, rowsByCode) {
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

export function daysBetween(a, b) {
  const diffMs = b.getTime() - a.getTime();
  return Math.round(diffMs / (1000 * 60 * 60 * 24));
}

export function addDays(d, n) {
  const copy = new Date(d.getTime());
  copy.setDate(copy.getDate() + n);
  return copy;
}

export function parseDate(val) {
  return val ? new Date(val + "T00:00:00") : null;
}

export const redrawAsync = fn => requestAnimationFrame(fn);
