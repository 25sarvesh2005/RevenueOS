/**
 * RevenueOS Studio – Slicers & Cross-Filtering Module
 * ===================================================
 * Manages category, sales channel, and date range slicers,
 * coordinating state filtering and canvas indicators.
 */

import { showToast } from "./toast.js";

export function setCategoryFilter(category, state, onFilterChange) {
  state.activeCategoryFilter = category;
  updateActiveFilterBanner(state, () => resetFilters(state, onFilterChange));
  if (typeof onFilterChange === "function") {
    onFilterChange();
  }
}

export function setChannelFilter(channel, state, onFilterChange) {
  state.activeChannelFilter = channel;
  updateActiveFilterBanner(state, () => resetFilters(state, onFilterChange));
  if (typeof onFilterChange === "function") {
    onFilterChange();
  }
}

export function resetFilters(state, onFilterChange) {
  state.activeCategoryFilter = "ALL";
  state.activeChannelFilter = "ALL";

  document.querySelectorAll(".slicer-pills .slicer-pill").forEach((p) => {
    p.classList.toggle("active", p.dataset.category === "ALL");
  });

  const sel = document.getElementById("channelSlicerSelect");
  if (sel) sel.value = "ALL";

  updateActiveFilterBanner(state, () => resetFilters(state, onFilterChange));
  if (typeof onFilterChange === "function") {
    onFilterChange();
  }
  showToast("All slicer filters reset", "info");
}

export function applySlicerFilters(state, onFilterChange) {
  updateActiveFilterBanner(state, () => resetFilters(state, onFilterChange));
  if (typeof onFilterChange === "function") {
    onFilterChange();
  }
}

export function updateActiveFilterBanner(state, onReset) {
  let indicator = document.getElementById("activeFilterBanner");
  const container = document.getElementById("canvasSlicerBar");

  if (state.activeCategoryFilter !== "ALL" || state.activeChannelFilter !== "ALL") {
    if (!indicator && container) {
      indicator = document.createElement("div");
      indicator.id = "activeFilterBanner";
      indicator.className = "active-filter-indicator";
      if (typeof onReset === "function") {
        indicator.onclick = onReset;
      }
      container.appendChild(indicator);
    }
    const parts = [];
    if (state.activeCategoryFilter !== "ALL") parts.push(`Category: ${state.activeCategoryFilter}`);
    if (state.activeChannelFilter !== "ALL") parts.push(`Channel: ${state.activeChannelFilter}`);
    if (indicator) indicator.textContent = `Filtered (${parts.join(" · ")}) ✕`;
  } else if (indicator) {
    indicator.remove();
  }
}
