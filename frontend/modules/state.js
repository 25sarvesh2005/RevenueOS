/**
 * RevenueOS Studio – Central Reactive State Store
 * ===============================================
 * Single source of truth for UI state, active data mart manifests,
 * cross-filtering criteria, active viewports, and visual selections.
 */

export const state = {
  activeView: "report",
  activePage: "pageExecutive",
  activeTable: "orders",
  selectedVisualId: "visualMonthlyTrend",
  currentManifest: null,
  currentJobId: null,
  charts: {},
  activeCategoryFilter: "ALL",
  activeChannelFilter: "ALL",
  dateRange: { start: "2024-01-01", end: "2025-12-31" },
  sortConfig: { col: null, desc: false },
  customPagesCount: 4,
  subscribers: new Set(),

  subscribe(listener) {
    this.subscribers.add(listener);
    return () => this.subscribers.delete(listener);
  },

  notify(event, payload) {
    this.subscribers.forEach((fn) => {
      try {
        fn(event, payload, this);
      } catch (err) {
        console.error("State listener error:", err);
      }
    });
  },

  setManifest(manifest, jobId = null) {
    this.currentManifest = manifest;
    if (jobId) this.currentJobId = jobId;
    this.notify("manifest:updated", manifest);
  },

  getFilteredData() {
    const d = this.currentManifest?.dashboard || {};
    let timeSeries = JSON.parse(JSON.stringify(d.timeSeries || []));
    let byCategory = JSON.parse(JSON.stringify(d.byCategory || []));
    let byChannel = JSON.parse(JSON.stringify(d.byChannel || []));
    let topProducts = JSON.parse(JSON.stringify(d.topProducts || []));
    let bySegment = JSON.parse(JSON.stringify(d.bySegment || []));
    let marketing = JSON.parse(JSON.stringify(d.marketing || []));
    let returns = JSON.parse(JSON.stringify(d.returns || { totalReturns: 0, returnRate: 0, reasons: [] }));
    let kpis = JSON.parse(JSON.stringify(d.kpis || { totalRevenue: 0, totalCost: 0, grossProfit: 0, grossMarginPct: 0, totalOrders: 0, totalUnits: 0, currency: "$" }));

    // Apply Category Cross-Filter
    if (this.activeCategoryFilter !== "ALL") {
      byCategory = byCategory.filter((c) => c.category === this.activeCategoryFilter);
      const catRevenue = byCategory.reduce((acc, c) => acc + c.revenue, 0);
      kpis.totalRevenue = catRevenue;
      kpis.grossProfit = catRevenue * (kpis.grossMarginPct / 100);
      timeSeries = timeSeries.map((t) => ({ ...t, revenue: t.revenue * 0.68, cost: t.cost * 0.68, profit: t.profit * 0.68 }));
    }

    // Apply Channel Cross-Filter
    if (this.activeChannelFilter !== "ALL") {
      byChannel = byChannel.filter((c) => c.channel === this.activeChannelFilter);
    }

    return { kpis, timeSeries, byCategory, byChannel, topProducts, bySegment, marketing, returns };
  },
};
