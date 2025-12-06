// Attach a synced horizontal scrollbar above the Django admin table

document.addEventListener("DOMContentLoaded", function () {
  const results = document.querySelector(".change-list .results");
  if (!results) return;

  // Create top scrollbar
  const topScroller = document.createElement("div");
  topScroller.style.overflowX = "auto";
  topScroller.style.overflowY = "hidden";
  topScroller.style.height = "14px";
  topScroller.style.marginBottom = "4px";

  const inner = document.createElement("div");
  inner.style.height = "1px";
  inner.style.width = results.scrollWidth + "px";

  topScroller.appendChild(inner);

  results.parentNode.insertBefore(topScroller, results);

  // Sync scrolling both ways
  let syncing = false;

  topScroller.addEventListener("scroll", () => {
    if (syncing) return;
    syncing = true;
    results.scrollLeft = topScroller.scrollLeft;
    syncing = false;
  });

  results.addEventListener("scroll", () => {
    if (syncing) return;
    syncing = true;
    topScroller.scrollLeft = results.scrollLeft;
    syncing = false;
  });

  // Update width if columns resize
  const observer = new ResizeObserver(() => {
    inner.style.width = results.scrollWidth + "px";
  });
  observer.observe(results);
});

