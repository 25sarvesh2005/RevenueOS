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

    const origRev = d.kpis?.totalRevenue || byCategory.reduce((acc, c) => acc + (c.revenue || 0), 0) || 1;

    // 1. Apply Date Range Filter on Time Series
    if (this.dateRange.start || this.dateRange.end) {
      const startPeriod = this.dateRange.start ? this.dateRange.start.slice(0, 7) : null;
      const endPeriod = this.dateRange.end ? this.dateRange.end.slice(0, 7) : null;
      timeSeries = timeSeries.filter((t) => {
        if (startPeriod && t.period < startPeriod) return false;
        if (endPeriod && t.period > endPeriod) return false;
        return true;
      });
    }

    // 2. Apply Category Cross-Filter
    let categoryRatio = 1;
    if (this.activeCategoryFilter !== "ALL") {
      const origCatTotal = byCategory.reduce((acc, c) => acc + (c.revenue || 0), 0);
      byCategory = byCategory.filter((c) => c.category === this.activeCategoryFilter);
      const catRevenue = byCategory.reduce((acc, c) => acc + (c.revenue || 0), 0);
      categoryRatio = origCatTotal > 0 ? (catRevenue / origCatTotal) : 1;
      
      // Filter top products belonging to selected category if available
      topProducts = topProducts.filter((p) => !p.category || p.category === this.activeCategoryFilter);
      if (topProducts.length === 0 && d.topProducts) {
        topProducts = JSON.parse(JSON.stringify(d.topProducts)).slice(0, 5).map((p) => ({ ...p, revenue: p.revenue * categoryRatio }));
      }
    }

    // 3. Apply Channel Cross-Filter
    let channelRatio = 1;
    if (this.activeChannelFilter !== "ALL") {
      const origChanTotal = byChannel.reduce((acc, c) => acc + (c.revenue || 0), 0);
      byChannel = byChannel.filter((c) => c.channel === this.activeChannelFilter);
      const chanRevenue = byChannel.reduce((acc, c) => acc + (c.revenue || 0), 0);
      channelRatio = origChanTotal > 0 ? (chanRevenue / origChanTotal) : 1;

      // Filter marketing channels if matched
      marketing = marketing.filter((m) => m.channel.toLowerCase() === this.activeChannelFilter.toLowerCase() || this.activeChannelFilter === "ALL");
      if (marketing.length === 0 && d.marketing) {
        marketing = JSON.parse(JSON.stringify(d.marketing));
      }
    }

    const combinedRatio = categoryRatio * channelRatio;

    // Apply combined filter ratio to time series
    if (combinedRatio !== 1) {
      timeSeries = timeSeries.map((t) => ({
        ...t,
        revenue: t.revenue * combinedRatio,
        cost: t.cost * combinedRatio,
        profit: t.profit * combinedRatio,
        units: Math.round((t.units || 0) * combinedRatio),
      }));
      byCategory = byCategory.map((c) => ({ ...c, revenue: c.revenue * channelRatio }));
      byChannel = byChannel.map((c) => ({ ...c, revenue: c.revenue * categoryRatio }));
      bySegment = bySegment.map((s) => ({ ...s, revenue: s.revenue * combinedRatio }));
    }

    // 4. Dynamically compute aggregated KPIs from filtered time series
    if (timeSeries.length > 0) {
      const sumRev = timeSeries.reduce((acc, t) => acc + (t.revenue || 0), 0);
      const sumCost = timeSeries.reduce((acc, t) => acc + (t.cost || 0), 0);
      const sumProfit = sumRev - sumCost;
      const marginPct = sumRev > 0 ? (sumProfit / sumRev) * 100 : 0;
      const sumUnits = timeSeries.reduce((acc, t) => acc + (t.units || 0), 0);

      const overallRatio = origRev > 0 ? (sumRev / origRev) : 1;
      const estOrders = Math.max(1, Math.round((d.kpis?.totalOrders || 500) * overallRatio));
      const aov = estOrders > 0 ? (sumRev / estOrders) : 0;

      kpis.totalRevenue = sumRev;
      kpis.totalCost = sumCost;
      kpis.grossProfit = sumProfit;
      kpis.grossMarginPct = marginPct;
      kpis.totalOrders = estOrders;
      kpis.totalUnits = sumUnits > 0 ? sumUnits : Math.round((d.kpis?.totalUnits || 1229) * overallRatio);
      kpis.avgOrderValue = aov;
      kpis.currency = d.kpis?.currency || "$";

      // Calculate dynamic Month-over-Month growth
      if (timeSeries.length >= 2) {
        const lastPeriod = timeSeries[timeSeries.length - 1].revenue || 0;
        const prevPeriod = timeSeries[timeSeries.length - 2].revenue || 0;
        kpis.momGrowthPct = prevPeriod > 0 ? ((lastPeriod - prevPeriod) / prevPeriod) * 100 : 0;
      } else {
        kpis.momGrowthPct = 0;
      }

      // Calculate dynamic return metrics
      const origReturnsCount = d.returns?.totalReturns || 34;
      const origUnitsCount = d.kpis?.totalUnits || 1229;
      const retRatio = origUnitsCount > 0 ? (kpis.totalUnits / origUnitsCount) : overallRatio;
      const dynamicReturnsCount = Math.round(origReturnsCount * retRatio);
      const dynamicReturnRate = kpis.totalUnits > 0 ? (dynamicReturnsCount / kpis.totalUnits) * 100 : 0;
      returns.totalReturns = dynamicReturnsCount;
      returns.returnRate = Number(dynamicReturnRate.toFixed(2));
    }

    return { kpis, timeSeries, byCategory, byChannel, topProducts, bySegment, marketing, returns };
  },
};
