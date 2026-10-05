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

  const startInput = document.getElementById("slicerStartDate");
  const endInput = document.getElementById("slicerEndDate");
  if (startInput && startInput.min) {
    startInput.value = startInput.min;
    state.dateRange.start = startInput.min;
  }
  if (endInput && endInput.max) {
    endInput.value = endInput.max;
    state.dateRange.end = endInput.max;
  }

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

  const startInput = document.getElementById("slicerStartDate");
  const endInput = document.getElementById("slicerEndDate");
  const isDateFiltered = startInput && endInput && (startInput.value !== startInput.min || endInput.value !== endInput.max);

  if (state.activeCategoryFilter !== "ALL" || state.activeChannelFilter !== "ALL" || isDateFiltered) {
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
    if (isDateFiltered && startInput && endInput) parts.push(`Date: ${startInput.value} ~ ${endInput.value}`);
    if (indicator) indicator.textContent = `Filtered (${parts.join(" · ")}) ✕`;
  } else if (indicator) {
    indicator.remove();
  }
}

export function populateSlicers(manifest, state, onFilterChange) {
  if (!manifest?.dashboard) return;
  const filterOptions = manifest.dashboard.filterOptions || {};

  // 1. Populate Category Pills
  const pillsContainer = document.querySelector(".slicer-pills");
  const categories = filterOptions.categories || (manifest.dashboard.byCategory || []).map((c) => c.category);
  if (pillsContainer && categories && categories.length > 0) {
    pillsContainer.innerHTML = "";
    
    // Add "All" pill
    const allPill = document.createElement("button");
    allPill.className = "slicer-pill" + (state.activeCategoryFilter === "ALL" ? " active" : "");
    allPill.dataset.category = "ALL";
    allPill.textContent = "All";
    allPill.addEventListener("click", () => {
      document.querySelectorAll(".slicer-pills .slicer-pill").forEach((p) => p.classList.remove("active"));
      allPill.classList.add("active");
      setCategoryFilter("ALL", state, onFilterChange);
    });
    pillsContainer.appendChild(allPill);

    // Add unique category pills (limit to top 8 to prevent overflow)
    const uniqueCategories = [...new Set(categories.filter(Boolean))].slice(0, 8);
    uniqueCategories.forEach((cat) => {
      const pill = document.createElement("button");
      pill.className = "slicer-pill" + (state.activeCategoryFilter === cat ? " active" : "");
      pill.dataset.category = cat;
      pill.textContent = cat;
      pill.addEventListener("click", () => {
        document.querySelectorAll(".slicer-pills .slicer-pill").forEach((p) => p.classList.remove("active"));
        pill.classList.add("active");
        setCategoryFilter(cat, state, onFilterChange);
      });
      pillsContainer.appendChild(pill);
    });
  }

  // 2. Populate Channel Dropdown
  const channelSelect = document.getElementById("channelSlicerSelect");
  const channels = filterOptions.channels || (manifest.dashboard.byChannel || []).map((c) => c.channel);
  if (channelSelect && channels && channels.length > 0) {
    channelSelect.innerHTML = `<option value="ALL">All Channels</option>`;
    const uniqueChannels = [...new Set(channels.filter(Boolean))];
    uniqueChannels.forEach((chan) => {
      const opt = document.createElement("option");
      opt.value = chan;
      opt.textContent = chan;
      if (state.activeChannelFilter === chan) opt.selected = true;
      channelSelect.appendChild(opt);
    });
  }

  // 3. Populate Date Range Inputs dynamically from timeSeries
  const timeSeries = manifest.dashboard.timeSeries || [];
  if (timeSeries.length > 0) {
    const periods = timeSeries.map((t) => t.period).filter(Boolean).sort();
    if (periods.length > 0) {
      const minP = periods[0];
      const maxP = periods[periods.length - 1];
      const startInput = document.getElementById("slicerStartDate");
      const endInput = document.getElementById("slicerEndDate");

      const startDateVal = `${minP}-01`;
      const [maxYear, maxMonth] = maxP.split("-");
      const lastDay = new Date(Number(maxYear), Number(maxMonth), 0).getDate();
      const endDateVal = `${maxP}-${String(lastDay).padStart(2, "0")}`;

      if (startInput) {
        startInput.min = startDateVal;
        startInput.max = endDateVal;
        if (!state.dateRange.start || state.dateRange.start < startDateVal) {
          startInput.value = startDateVal;
          state.dateRange.start = startDateVal;
        } else {
          startInput.value = state.dateRange.start;
        }
      }
      if (endInput) {
        endInput.min = startDateVal;
        endInput.max = endDateVal;
        if (!state.dateRange.end || state.dateRange.end > endDateVal) {
          endInput.value = endDateVal;
          state.dateRange.end = endDateVal;
        } else {
          endInput.value = state.dateRange.end;
        }
      }
    }
  }

  // 4. Wire Quick Date Preset Chips
  wireDatePresets(state, onFilterChange);
}

export function wireDatePresets(state, onFilterChange) {
  const chips = document.querySelectorAll("#datePresetChips .date-preset-pill");
  const startInput = document.getElementById("slicerStartDate");
  const endInput = document.getElementById("slicerEndDate");

  chips.forEach((chip) => {
    chip.onclick = () => {
      chips.forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");

      const preset = chip.dataset.preset;
      if (preset === "ALL") {
        if (startInput?.min) startInput.value = startInput.min;
        if (endInput?.max) endInput.value = endInput.max;
      } else if (preset === "2024") {
        if (startInput) startInput.value = "2024-01-01";
        if (endInput) endInput.value = "2024-12-31";
      } else if (preset === "2025") {
        if (startInput) startInput.value = "2025-01-01";
        if (endInput) endInput.value = "2025-12-31";
      }

      if (startInput) state.dateRange.start = startInput.value;
      if (endInput) state.dateRange.end = endInput.value;

      applySlicerFilters(state, onFilterChange);
    };
  });
}

