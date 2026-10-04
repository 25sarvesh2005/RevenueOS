/**
 * RevenueOS Studio – Chart.js Visualizations Module
 * =================================================
 * Manages Chart.js instance lifecycles, cross-filtering interactions,
 * visual type transformations, and KPI card indicators.
 */

import { showToast } from "./toast.js";

export function renderCharts(state) {
  const data = state.getFilteredData();
  const isDark = !document.body.classList.contains("powerbi-fluent");
  const gridColor = isDark ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.06)";
  const textColor = isDark ? "#CCCCCC" : "#323130";

  // 1. Monthly Trend Visual (Combo Bar + Line)
  const ctxTrend = document.getElementById("chartMonthlyTrend")?.getContext("2d");
  if (ctxTrend) {
    if (state.charts.monthlyTrend) state.charts.monthlyTrend.destroy();
    try {
      state.charts.monthlyTrend = new Chart(ctxTrend, {
        type: "bar",
        data: {
          labels: data.timeSeries.map((t) => t.period),
          datasets: [
            {
              type: "line",
              label: "Gross Margin %",
              data: data.timeSeries.map((t) => t.marginPct),
              borderColor: "#F2C80F",
              backgroundColor: "#F2C80F",
              borderWidth: 2.5,
              tension: 0.35,
              yAxisID: "yMargin",
              pointRadius: 3,
            },
            {
              type: "bar",
              label: "Gross Revenue",
              data: data.timeSeries.map((t) => t.revenue),
              backgroundColor: "rgba(17, 141, 255, 0.85)",
              borderRadius: 4,
              yAxisID: "yRev",
            },
            {
              type: "bar",
              label: "Total COGS",
              data: data.timeSeries.map((t) => t.cost),
              backgroundColor: "rgba(230, 108, 55, 0.75)",
              borderRadius: 4,
              yAxisID: "yRev",
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: "top", labels: { color: textColor, font: { size: 11 } } },
          },
          scales: {
            x: { grid: { color: gridColor }, ticks: { color: textColor } },
            yRev: {
              type: "linear",
              position: "left",
              grid: { color: gridColor },
              ticks: { color: textColor, callback: (v) => `$${v >= 1e6 ? (v / 1e6).toFixed(1) + "M" : (v / 1e3).toFixed(0) + "K"}` },
            },
            yMargin: {
              type: "linear",
              position: "right",
              grid: { drawOnChartArea: false },
              ticks: { color: "#F2C80F", callback: (v) => `${v}%` },
            },
          },
        },
      });
    } catch (err) {
      console.warn("Error rendering monthlyTrend chart:", err);
    }
  }

  // 2. Category Share (Donut with Cross-Filter Click)
  const ctxCat = document.getElementById("chartCategoryShare")?.getContext("2d");
  if (ctxCat) {
    if (state.charts.categoryShare) state.charts.categoryShare.destroy();
    try {
      state.charts.categoryShare = new Chart(ctxCat, {
        type: "doughnut",
        data: {
          labels: data.byCategory.map((c) => c.category),
          datasets: [
            {
              data: data.byCategory.map((c) => c.revenue),
              backgroundColor: ["#118DFF", "#12239E", "#E66C37", "#DDAA33", "#3B7E67", "#744DA9"],
              borderWidth: 2,
              borderColor: isDark ? "#2D2D30" : "#FFFFFF",
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: "right", labels: { color: textColor, font: { size: 10 } } },
          },
          cutout: "68%",
          onClick: (evt, elements) => {
            if (elements.length > 0) {
              const idx = elements[0].index;
              const catName = data.byCategory[idx]?.category;
              if (catName) {
                const nextFilter = state.activeCategoryFilter === catName ? "ALL" : catName;
                state.activeCategoryFilter = nextFilter;
                state.notify("filter:changed", { type: "category", value: nextFilter });
                renderCharts(state);
              }
            }
          },
        },
      });
    } catch (err) {
      console.warn("Error rendering categoryShare chart:", err);
    }
  }

  // 3. Channel Bar (Bar with Click Filter)
  const ctxChan = document.getElementById("chartChannelBar")?.getContext("2d");
  if (ctxChan) {
    if (state.charts.channelBar) state.charts.channelBar.destroy();
    try {
      state.charts.channelBar = new Chart(ctxChan, {
        type: "bar",
        data: {
          labels: data.byChannel.map((c) => c.channel),
          datasets: [{ label: "Channel Revenue", data: data.byChannel.map((c) => c.revenue), backgroundColor: "#00B4D8", borderRadius: 4 }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { color: gridColor }, ticks: { color: textColor } },
            y: { grid: { color: gridColor }, ticks: { color: textColor, callback: (v) => `$${v >= 1e6 ? (v / 1e6).toFixed(1) + "M" : (v / 1e3).toFixed(0) + "K"}` } },
          },
          onClick: (evt, elements) => {
            if (elements.length > 0) {
              const idx = elements[0].index;
              const chanName = data.byChannel[idx]?.channel;
              if (chanName) {
                const nextFilter = state.activeChannelFilter === chanName ? "ALL" : chanName;
                state.activeChannelFilter = nextFilter;
                state.notify("filter:changed", { type: "channel", value: nextFilter });
                renderCharts(state);
              }
            }
          },
        },
      });
    } catch (err) {
      console.warn("Error rendering channelBar chart:", err);
    }
  }

  // 4. Top Products (Horizontal Bar)
  const ctxProd = document.getElementById("chartTopProducts")?.getContext("2d");
  if (ctxProd) {
    if (state.charts.topProducts) state.charts.topProducts.destroy();
    try {
      state.charts.topProducts = new Chart(ctxProd, {
        type: "bar",
        data: {
          labels: data.topProducts.map((p) => p.product),
          datasets: [{ label: "Sales ($)", data: data.topProducts.map((p) => p.revenue), backgroundColor: "rgba(242, 200, 15, 0.8)", borderRadius: 4 }],
        },
        options: {
          indexAxis: "y",
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { color: gridColor }, ticks: { color: textColor, callback: (v) => `$${v >= 1e6 ? (v / 1e6).toFixed(1) + "M" : (v / 1e3).toFixed(0) + "K"}` } },
            y: { grid: { color: gridColor }, ticks: { color: textColor, font: { size: 10 } } },
          },
        },
      });
    } catch (err) {
      console.warn("Error rendering topProducts chart:", err);
    }
  }

  // 5. Margin Trend (Page 2)
  const ctxMargin = document.getElementById("chartMarginTrend")?.getContext("2d");
  if (ctxMargin) {
    if (state.charts.marginTrend) state.charts.marginTrend.destroy();
    try {
      state.charts.marginTrend = new Chart(ctxMargin, {
        type: "line",
        data: {
          labels: data.timeSeries.map((t) => t.period),
          datasets: [{ label: "Gross Margin %", data: data.timeSeries.map((t) => t.marginPct), borderColor: "#2ECC71", backgroundColor: "rgba(46, 204, 113, 0.1)", fill: true, tension: 0.3 }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { grid: { color: gridColor }, ticks: { color: textColor } },
            y: { grid: { color: gridColor }, ticks: { color: textColor, callback: (v) => `${v}%` } },
          },
        },
      });
    } catch (err) {}
  }

  // 6. Customer Segments (Page 2)
  const ctxSeg = document.getElementById("chartSegmentRevenue")?.getContext("2d");
  if (ctxSeg) {
    if (state.charts.segmentRevenue) state.charts.segmentRevenue.destroy();
    try {
      state.charts.segmentRevenue = new Chart(ctxSeg, {
        type: "pie",
        data: {
          labels: data.bySegment.map((s) => s.segment),
          datasets: [{ data: data.bySegment.map((s) => s.revenue), backgroundColor: ["#118DFF", "#9B59B6", "#E66C37", "#2ECC71", "#F2C80F"] }],
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "right", labels: { color: textColor } } } },
      });
    } catch (err) {}
  }

  // 7. Marketing ROAS (Page 3)
  const ctxRoas = document.getElementById("chartMarketingROAS")?.getContext("2d");
  if (ctxRoas) {
    if (state.charts.marketingROAS) state.charts.marketingROAS.destroy();
    try {
      state.charts.marketingROAS = new Chart(ctxRoas, {
        type: "bar",
        data: {
          labels: data.marketing.map((m) => m.channel),
          datasets: [{ label: "ROAS (Return on Ad Spend)", data: data.marketing.map((m) => m.roas), backgroundColor: "#9B59B6", borderRadius: 4 }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { grid: { color: gridColor }, ticks: { color: textColor } },
            y: { grid: { color: gridColor }, ticks: { color: textColor, callback: (v) => `${v}x` } },
          },
        },
      });
    } catch (err) {}
  }

  // 8. Marketing Spend vs Revenue (Page 3)
  const ctxMktSpend = document.getElementById("chartMarketingSpend")?.getContext("2d");
  if (ctxMktSpend) {
    if (state.charts.marketingSpend) state.charts.marketingSpend.destroy();
    try {
      state.charts.marketingSpend = new Chart(ctxMktSpend, {
        type: "bar",
        data: {
          labels: data.marketing.map((m) => m.channel),
          datasets: [
            { label: "Ad Spend", data: data.marketing.map((m) => m.spend), backgroundColor: "#E74C3C", borderRadius: 4 },
            { label: "Attributed Sales", data: data.marketing.map((m) => m.revenue), backgroundColor: "#2ECC71", borderRadius: 4 },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { grid: { color: gridColor }, ticks: { color: textColor } },
            y: { grid: { color: gridColor }, ticks: { color: textColor, callback: (v) => `$${v >= 1e6 ? (v / 1e6).toFixed(1) + "M" : (v / 1e3).toFixed(0) + "K"}` } },
          },
        },
      });
    } catch (err) {}
  }

  // 9. Return Reasons (Page 4)
  const ctxReturns = document.getElementById("chartReturnReasons")?.getContext("2d");
  if (ctxReturns) {
    if (state.charts.returnReasons) state.charts.returnReasons.destroy();
    try {
      state.charts.returnReasons = new Chart(ctxReturns, {
        type: "doughnut",
        data: {
          labels: (data.returns.reasons || []).map((r) => r.reason.replace(/_/g, " ")),
          datasets: [{ data: (data.returns.reasons || []).map((r) => r.count), backgroundColor: ["#E74C3C", "#E66C37", "#F2C80F", "#3498DB", "#95A5A6"] }],
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "right", labels: { color: textColor } } } },
      });
    } catch (err) {}
  }

  updateKPICards(data.kpis, data.returns);
}

export function updateKPICards(kpis, returns) {
  const revEl = document.getElementById("kpiRevenueVal");
  const profEl = document.getElementById("kpiProfitVal");
  const margEl = document.getElementById("kpiMarginVal");
  const ordEl = document.getElementById("kpiOrdersVal");
  const untEl = document.getElementById("kpiUnitsVal");
  const retEl = document.getElementById("kpiReturnsVal");

  if (revEl && kpis) revEl.textContent = `$${Math.round(kpis.totalRevenue || 0).toLocaleString()}`;
  if (profEl && kpis) profEl.textContent = `$${Math.round(kpis.grossProfit || 0).toLocaleString()}`;
  if (margEl && kpis) margEl.textContent = `${(kpis.grossMarginPct || 0).toFixed(1)}%`;
  if (ordEl && kpis) ordEl.textContent = Number(kpis.totalOrders || 0).toLocaleString();
  if (untEl && kpis) untEl.textContent = Number(kpis.totalUnits || 0).toLocaleString();
  if (retEl && returns) retEl.textContent = `${returns.totalReturns || 0} Items (${returns.returnRate || 0}%)`;
}

export function selectVisual(containerId, state) {
  state.selectedVisualId = containerId;
  document.querySelectorAll(".pbi-visual-container").forEach((c) => c.classList.remove("selected-visual"));
  const target = document.getElementById(containerId);
  if (target) {
    target.classList.add("selected-visual");
    const title = target.querySelector(".visual-title")?.textContent.trim() || "";
    const yWell = document.getElementById("wellYAxis");
    if (yWell) yWell.textContent = title;
  }
}

export function transformSelectedVisual(newChartType, state) {
  if (!state.selectedVisualId) return;

  let chartKey = null;
  if (state.selectedVisualId === "visualMonthlyTrend") chartKey = "monthlyTrend";
  else if (state.selectedVisualId === "visualCategoryShare") chartKey = "categoryShare";
  else if (state.selectedVisualId === "visualChannelBar") chartKey = "channelBar";
  else if (state.selectedVisualId === "visualTopProducts") chartKey = "topProducts";

  const chartInstance = state.charts[chartKey];
  if (!chartInstance) return;

  if (newChartType === "horizontalBar") {
    chartInstance.config.type = "bar";
    chartInstance.config.options.indexAxis = "y";
  } else if (newChartType === "bar") {
    chartInstance.config.type = "bar";
    chartInstance.config.options.indexAxis = "x";
  } else if (newChartType === "area") {
    chartInstance.config.type = "line";
    chartInstance.data.datasets.forEach((ds) => {
      ds.fill = true;
      ds.backgroundColor = ds.borderColor ? ds.borderColor.replace(")", ", 0.25)").replace("rgb", "rgba") : "rgba(17,141,255,0.25)";
    });
  } else {
    chartInstance.config.type = newChartType;
    chartInstance.config.options.indexAxis = "x";
  }

  chartInstance.update();
  showToast(`Converted active visual to ${newChartType.toUpperCase()}`, "info");
}
