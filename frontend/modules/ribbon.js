/**
 * RevenueOS Studio – Ribbon, View Navigation & Metadata Tree
 * ==========================================================
 * Manages Power BI ribbon command tabs, main rail view switching
 * (Report / Data / Model), report pages, and the fields tree hierarchy.
 */

import { showToast } from "./toast.js";

export function setupRibbonTabs() {
  document.querySelectorAll(".ribbon-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".ribbon-tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".ribbon-content").forEach((c) => c.classList.remove("active"));
      tab.classList.add("active");
      const targetId = `tabContent${tab.dataset.tab.charAt(0).toUpperCase() + tab.dataset.tab.slice(1)}`;
      const targetContent = document.getElementById(targetId);
      if (targetContent) targetContent.classList.add("active");
    });
  });
}

export function switchView(viewName, state, onRenderView) {
  state.activeView = viewName;
  document.querySelectorAll(".rail-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.view === viewName);
  });
  document.querySelectorAll(".stage-view").forEach((v) => v.classList.remove("active"));

  if (viewName === "report") {
    document.getElementById("viewReport")?.classList.add("active");
    const slicerBar = document.getElementById("canvasSlicerBar");
    if (slicerBar) slicerBar.style.display = "flex";
  } else if (viewName === "data") {
    document.getElementById("viewData")?.classList.add("active");
    const slicerBar = document.getElementById("canvasSlicerBar");
    if (slicerBar) slicerBar.style.display = "none";
  } else if (viewName === "model") {
    document.getElementById("viewModel")?.classList.add("active");
    const slicerBar = document.getElementById("canvasSlicerBar");
    if (slicerBar) slicerBar.style.display = "none";
  }

  if (typeof onRenderView === "function") {
    onRenderView(viewName);
  }
}

export function switchPage(pageId, state) {
  state.activePage = pageId;
  document.querySelectorAll(".page-tab").forEach((t) => {
    t.classList.toggle("active", t.dataset.page === pageId);
  });
  document.querySelectorAll(".canvas-page").forEach((p) => p.classList.remove("active"));
  const target = document.getElementById(pageId);
  if (target) target.classList.add("active");

  setTimeout(() => {
    Object.values(state.charts).forEach((c) => c?.resize?.());
  }, 50);
}

export function addNewPage(state) {
  state.customPagesCount++;
  const pageId = `pageCustom_${state.customPagesCount}`;
  const pageTitle = `Page ${state.customPagesCount}: Ad-Hoc View`;

  // 1. Add tab button
  const tabsContainer = document.getElementById("pageTabsContainer");
  const addBtn = document.getElementById("btnAddPage");
  const newTab = document.createElement("button");
  newTab.className = "page-tab";
  newTab.dataset.page = pageId;
  newTab.textContent = pageTitle;
  newTab.onclick = () => switchPage(pageId, state);
  if (tabsContainer && addBtn) {
    tabsContainer.insertBefore(newTab, addBtn);
  }

  // 2. Add canvas container
  const canvasContainer = document.getElementById("activeReportCanvas");
  if (canvasContainer) {
    const newCanvasPage = document.createElement("div");
    newCanvasPage.className = "canvas-page";
    newCanvasPage.id = pageId;
    newCanvasPage.innerHTML = `
      <div class="page-title-banner">
        <h2>${pageTitle}</h2>
        <p>Custom user-created reporting canvas</p>
      </div>
      <div class="visuals-grid">
        <div class="pbi-visual-container span-12" id="visualCustom_${state.customPagesCount}">
          <div class="visual-header">
            <div class="visual-title">📈 Cross-Segment Performance Analysis</div>
          </div>
          <div class="visual-body">
            <canvas id="chartCustom_${state.customPagesCount}"></canvas>
          </div>
        </div>
      </div>
    `;
    canvasContainer.appendChild(newCanvasPage);
  }

  // 3. Switch to it and render chart
  switchPage(pageId, state);
  setTimeout(() => {
    const ctx = document.getElementById(`chartCustom_${state.customPagesCount}`)?.getContext("2d");
    if (ctx && window.Chart) {
      const data = state.getFilteredData();
      new window.Chart(ctx, {
        type: "bar",
        data: {
          labels: data.byCategory.map((c) => c.category),
          datasets: [{ label: "Net Revenue", data: data.byCategory.map((c) => c.revenue), backgroundColor: "#118DFF" }],
        },
        options: { responsive: true, maintainAspectRatio: false },
      });
    }
  }, 100);

  showToast(`Created ${pageTitle}`, "success");
}

export function renderFieldsTree(state, onSelectMeasure) {
  const tree = document.getElementById("fieldsTree");
  if (!tree) return;
  tree.innerHTML = "";

  const tables = state.currentManifest?.tables || [];
  const measures = state.currentManifest?.measures || [];

  // _Measures Node
  const mNode = document.createElement("div");
  mNode.className = "table-node open";
  mNode.innerHTML = `
    <div class="table-node-header" onclick="this.parentElement.classList.toggle('open')">
      <span class="node-arrow">▶</span>
      <span class="field-icon calc">📐</span>
      <span>_Measures</span>
    </div>
    <ul class="field-list"></ul>
  `;
  const mList = mNode.querySelector(".field-list");

  measures.forEach((m) => {
    const li = document.createElement("li");
    li.className = "field-item";
    li.innerHTML = `<span class="field-icon calc">fx</span> <span>[${m.name}]</span>`;
    li.onclick = () => {
      const sel = document.getElementById("daxMeasureDropdown");
      if (sel) sel.value = m.name;
      if (typeof onSelectMeasure === "function") {
        onSelectMeasure(m.name);
      }
    };
    mList.appendChild(li);
  });
  tree.appendChild(mNode);

  // Tables Nodes
  tables.forEach((tbl) => {
    const node = document.createElement("div");
    node.className = "table-node";
    const isFact = tbl.table_type === "fact" || tbl.name.includes("order") || tbl.name.includes("fact");
    node.innerHTML = `
      <div class="table-node-header" onclick="this.parentElement.classList.toggle('open')">
        <span class="node-arrow">▶</span>
        <span>${isFact ? "📊" : "📦"}</span>
        <span>${tbl.name}</span>
      </div>
      <ul class="field-list"></ul>
    `;
    const fList = node.querySelector(".field-list");

    (tbl.columns || []).forEach((c) => {
      const colName = typeof c === "string" ? c : c.name;
      let icon = "🔤";
      if (colName.includes("date") || colName.includes("time")) icon = "📅";
      else if (colName.includes("id") || colName.includes("key")) icon = "🔑";
      else if (
        colName.includes("amount") ||
        colName.includes("price") ||
        colName.includes("revenue") ||
        colName.includes("cost") ||
        colName.includes("qty")
      ) {
        icon = "∑";
      }

      const li = document.createElement("li");
      li.className = "field-item";
      li.innerHTML = `<span class="field-icon">${icon}</span> <span>${colName}</span>`;
      fList.appendChild(li);
    });
    tree.appendChild(node);
  });
}
