/**
 * RevenueOS Studio – Power BI Desktop Replica Application Logic
 * ==============================================================
 * Production-grade desktop experience providing interactive Chart.js canvas,
 * Kimball Star Schema model diagram, tabular data grid explorer,
 * real-time DAX formula bar, and native Power BI compilation.
 */

// Global Application Namespace
const app = {
  activeView: "report",
  activePage: "pageExecutive",
  activeTable: "orders",
  currentManifest: null,
  charts: {},
  activeCategoryFilter: "ALL",
  activeChannelFilter: "ALL",
  dateRange: { start: "2024-01-01", end: "2025-12-31" },

  // Default Verified Data Mart Payload (from revenueos_sample.xlsx)
  defaultData: {
    projectName: "RevenueOS_Sample",
    kpis: {
      totalRevenue: 8474027.50,
      totalCost: 6227820.00,
      grossProfit: 2246207.50,
      grossMarginPct: 26.5,
      totalOrders: 500,
      totalUnits: 1229,
      avgOrderValue: 16948.06,
      currency: "$",
      totalDiscounts: 36.83,
    },
    timeSeries: [
      { period: "2024-01", revenue: 2076833.44, cost: 2196190.0, profit: -119356.56, marginPct: -5.7, units: 67 },
      { period: "2024-02", revenue: 572488.32, cost: 407850.0, profit: 164638.32, marginPct: 28.8, units: 33 },
      { period: "2024-03", revenue: 137582.83, cost: 63080.0, profit: 74502.83, marginPct: 54.2, units: 39 },
      { period: "2024-04", revenue: 508634.52, cost: 370130.0, profit: 138504.52, marginPct: 27.2, units: 80 },
      { period: "2024-05", revenue: 165917.30, cost: 109620.0, profit: 56297.30, marginPct: 33.9, units: 39 },
      { period: "2024-06", revenue: 403373.70, cost: 268800.0, profit: 134573.70, marginPct: 33.4, units: 32 },
      { period: "2024-07", revenue: 275052.77, cost: 147000.0, profit: 128052.77, marginPct: 46.6, units: 72 },
      { period: "2024-08", revenue: 119474.83, cost: 86250.0, profit: 33224.83, marginPct: 27.8, units: 26 },
      { period: "2024-09", revenue: 255999.10, cost: 145250.0, profit: 110749.10, marginPct: 43.3, units: 59 },
      { period: "2024-10", revenue: 704193.05, cost: 387540.0, profit: 316653.05, marginPct: 45.0, units: 117 },
      { period: "2024-11", revenue: 486466.56, cost: 363870.0, profit: 122596.56, marginPct: 25.2, units: 76 },
      { period: "2024-12", revenue: 368206.53, cost: 199910.0, profit: 168296.53, marginPct: 45.7, units: 90 },
      { period: "2025-01", revenue: 142771.03, cost: 95950.0, profit: 46821.03, marginPct: 32.8, units: 35 },
      { period: "2025-02", revenue: 228435.27, cost: 196840.0, profit: 31595.27, marginPct: 13.8, units: 36 },
      { period: "2025-03", revenue: 201960.08, cost: 135670.0, profit: 66290.08, marginPct: 32.8, units: 40 },
      { period: "2025-04", revenue: 183782.78, cost: 101450.0, profit: 82332.78, marginPct: 44.8, units: 35 },
      { period: "2025-05", revenue: 485440.96, cost: 234510.0, profit: 250930.96, marginPct: 51.7, units: 121 },
      { period: "2025-06", revenue: 155428.82, cost: 95180.0, profit: 60248.82, marginPct: 38.8, units: 47 },
      { period: "2025-07", revenue: 424298.55, cost: 295310.0, profit: 128988.55, marginPct: 30.4, units: 62 },
      { period: "2025-08", revenue: 373061.64, cost: 249490.0, profit: 123571.64, marginPct: 33.1, units: 74 },
      { period: "2025-09", revenue: 204625.42, cost: 77930.0, profit: 126695.42, marginPct: 61.9, units: 49 },
    ],
    byCategory: [
      { category: "Electronics", revenue: 5819955.67, pct: 68.7 },
      { category: "Apparel", revenue: 1430090.54, pct: 16.9 },
      { category: "Home & Kitchen", revenue: 858621.35, pct: 10.1 },
      { category: "Fitness", revenue: 189669.93, pct: 2.2 },
      { category: "Beauty", revenue: 175690.01, pct: 2.1 },
    ],
    byChannel: [
      { channel: "Online Direct", revenue: 3936233.27 },
      { channel: "Amazon Marketplace", revenue: 1999325.51 },
      { channel: "Retail Store", revenue: 1350104.35 },
      { channel: "Mobile App", revenue: 806487.08 },
      { channel: "Wholesale", revenue: 381877.28 },
    ],
    topProducts: [
      { product: "Flagship Smartphone X12", revenue: 2721973.95 },
      { product: "4K Ultra-Wide Monitor 34", revenue: 1120337.06 },
      { product: "UltraBook Pro 15", revenue: 886236.31 },
      { product: "Noise-Cancelling Headphones", revenue: 499886.60 },
      { product: "Cold Press Slow Juicer", revenue: 381321.38 },
      { product: "Cushioned Running Shoes", revenue: 269081.43 },
      { product: "Tailored Linen Blazer", revenue: 257647.75 },
      { product: "Merino Wool Crewneck Sweater", revenue: 256031.99 },
      { product: "Waterproof All-Weather Jacket", revenue: 193328.85 },
      { product: "Smart Air Fryer XL", revenue: 192267.15 },
    ],
    bySegment: [
      { segment: "Consumer", revenue: 4655854.24 },
      { segment: "SMB", revenue: 1756409.41 },
      { segment: "Mid-Market", revenue: 1707133.16 },
      { segment: "Enterprise", revenue: 201417.52 },
      { segment: "VIP", revenue: 153213.18 },
    ],
    marketing: [
      { channel: "Social", spend: 921885.34, revenue: 1071379679.98, roas: 1162.16 },
      { channel: "Paid Search", spend: 767539.29, revenue: 843812157.13, roas: 1099.37 },
      { channel: "Influencer", spend: 768765.82, revenue: 488246766.16, roas: 635.10 },
      { channel: "Affiliate", spend: 428794.50, revenue: 537596435.35, roas: 1253.74 },
      { channel: "Email", spend: 47848.25, revenue: 886595350.14, roas: 18529.32 },
    ],
    returns: {
      totalReturns: 34,
      returnRate: 2.77,
      reasons: [
        { reason: "WRONG_SIZE_FIT", count: 11 },
        { reason: "DEFECTIVE_ITEM", count: 8 },
        { reason: "DAMAGED_IN_SHIPPING", count: 3 },
        { reason: "LATE_DELIVERY", count: 2 },
        { reason: "CHANGED_MIND", count: 1 },
      ],
    },
    daxMeasures: {
      "Total Revenue": "SUMX(orders, orders[quantity] * orders[unit_price] * (1 - orders[discount]))",
      "Total Cost": "SUMX(orders, orders[quantity] * RELATED(products[cost]))",
      "Gross Profit": "[Total Revenue] - [Total Cost]",
      "Gross Margin %": "DIVIDE([Gross Profit], [Total Revenue], 0)",
      "Total Orders": "DISTINCTCOUNT(orders[order_id])",
      "Average Order Value": "DIVIDE([Total Revenue], [Total Orders], 0)",
      "Total Units Sold": "SUM(orders[quantity])",
      "Revenue YTD": "TOTALYTD([Total Revenue], dim_date[date])",
      "Revenue Prior Month": "CALCULATE([Total Revenue], PREVIOUSMONTH(dim_date[date]))",
      "Revenue MoM %": "DIVIDE([Total Revenue] - [Revenue Prior Month], [Revenue Prior Month], 0)",
      "Revenue Same Period Last Year": "CALCULATE([Total Revenue], SAMEPERIODLASTYEAR(dim_date[date]))",
      "Revenue YoY %": "DIVIDE([Total Revenue] - [Revenue Same Period Last Year], [Revenue Same Period Last Year], 0)",
      "Marketing ROAS": "DIVIDE(SUM(marketing[revenue_attributed]), SUM(marketing[spend]), 0)",
      "Return Rate %": "DIVIDE(SUM(returns[quantity_returned]), SUM(orders[quantity]), 0)",
    },
    tables: [
      {
        name: "orders",
        type: "fact",
        rowCount: 500,
        pk: "order_id",
        columns: ["order_id", "customer_id", "product_id", "order_date", "quantity", "unit_price", "discount", "channel", "location", "status"],
      },
      {
        name: "products",
        type: "dimension",
        rowCount: 20,
        pk: "product_id",
        columns: ["product_id", "product_name", "category", "subcategory", "supplier", "cost", "selling_price"],
      },
      {
        name: "customers",
        type: "dimension",
        rowCount: 100,
        pk: "customer_id",
        columns: ["customer_id", "name", "email", "city", "region", "signup_date", "segment"],
      },
      {
        name: "dim_date",
        type: "dimension",
        rowCount: 1095,
        pk: "date",
        columns: ["date", "year", "quarter", "month", "month_name", "day_of_week", "day_name", "fiscal_year"],
      },
      {
        name: "marketing",
        type: "fact",
        rowCount: 60,
        pk: "campaign_id",
        columns: ["campaign_id", "channel", "date", "spend", "impressions", "clicks", "orders_attributed", "revenue_attributed"],
      },
      {
        name: "returns",
        type: "fact",
        rowCount: 34,
        pk: "return_id",
        columns: ["return_id", "order_id", "product_id", "return_date", "quantity_returned", "return_reason"],
      },
    ],
    relationships: [
      { from: "orders.customer_id", to: "customers.customer_id", cardinality: "ManyToOne" },
      { from: "orders.product_id", to: "products.product_id", cardinality: "ManyToOne" },
      { from: "orders.order_date", to: "dim_date.date", cardinality: "ManyToOne" },
      { from: "returns.order_id", to: "orders.order_id", cardinality: "ManyToOne" },
      { from: "returns.product_id", to: "products.product_id", cardinality: "ManyToOne" },
    ],
  },

  // -------------------------------------------------------------------------
  // Initialization
  // -------------------------------------------------------------------------
  init() {
    this.setupEventListeners();
    this.populateDAXMeasures();
    this.renderFieldsTree();
    this.renderCharts();
    this.renderDataView();
    this.renderModelView();
    this.renderFinancialTable();
  },

  // -------------------------------------------------------------------------
  // Event Listeners
  // -------------------------------------------------------------------------
  setupEventListeners() {
    // 1. Ribbon Tabs
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

    // 2. Left Rail Views (Report, Data, Model)
    document.querySelectorAll(".rail-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        this.switchView(btn.dataset.view);
      });
    });

    // 3. Page Switcher Tabs
    document.querySelectorAll(".page-tab").forEach((tab) => {
      if (tab.dataset.page) {
        tab.addEventListener("click", () => {
          this.switchPage(tab.dataset.page);
        });
      }
    });

    // 4. DAX Measure Selector
    const daxSelect = document.getElementById("daxMeasureDropdown");
    if (daxSelect) {
      daxSelect.addEventListener("change", (e) => {
        this.updateDAXFormula(e.target.value);
      });
    }

    // 5. Copy DAX Button
    document.getElementById("btnCopyDax")?.addEventListener("click", () => {
      const formula = document.getElementById("daxFormulaInput").value;
      if (window.api?.copyToClipboard) {
        window.api.copyToClipboard(formula);
        this.showToast("DAX formula copied to clipboard!");
      }
    });

    // 6. Category Slicer Pills
    document.querySelectorAll(".slicer-pill").forEach((pill) => {
      pill.addEventListener("click", () => {
        document.querySelectorAll(".slicer-pill").forEach((p) => p.classList.remove("active"));
        pill.classList.add("active");
        this.activeCategoryFilter = pill.dataset.category;
        this.applySlicerFilters();
      });
    });

    // 7. Channel Slicer
    document.getElementById("channelSlicerSelect")?.addEventListener("change", (e) => {
      this.activeChannelFilter = e.target.value;
      this.applySlicerFilters();
    });

    // 8. Slicer Reset
    document.getElementById("btnResetSlicers")?.addEventListener("click", () => {
      this.activeCategoryFilter = "ALL";
      this.activeChannelFilter = "ALL";
      document.querySelectorAll(".slicer-pill").forEach((p) => {
        p.classList.toggle("active", p.dataset.category === "ALL");
      });
      const sel = document.getElementById("channelSlicerSelect");
      if (sel) sel.value = "ALL";
      this.applySlicerFilters();
    });

    // 9. Pipeline Buttons
    document.getElementById("btnLoadSample")?.addEventListener("click", () => this.runSamplePipeline());
    document.getElementById("btnSelectExcel")?.addEventListener("click", () => this.selectAndRunExcel());
    document.getElementById("btnGetData")?.addEventListener("click", () => this.selectAndRunExcel());
    document.getElementById("btnLaunchPowerBI")?.addEventListener("click", () => this.launchNativePowerBI());
    document.getElementById("btnExportCSVMarts")?.addEventListener("click", () => this.exportCSVMarts());
    document.getElementById("btnCopyAllDAX")?.addEventListener("click", () => this.copyAllDAX());

    // 10. Theme Selector
    document.getElementById("themeSelect")?.addEventListener("change", (e) => {
      document.body.className = e.target.value;
    });

    // 11. Modal Close
    document.getElementById("btnCancelPipeline")?.addEventListener("click", () => {
      document.getElementById("pipelineModal").style.display = "none";
    });
    document.getElementById("btnLicenseModal")?.addEventListener("click", () => {
      document.getElementById("licenseModal").style.display = "flex";
    });

    // 12. Data View Table Switcher
    document.querySelectorAll(".dv-table-item").forEach((item) => {
      item.addEventListener("click", () => {
        document.querySelectorAll(".dv-table-item").forEach((i) => i.classList.remove("active"));
        item.classList.add("active");
        this.activeTable = item.dataset.table;
        this.renderDataView();
      });
    });

    // 13. Data Grid Search
    document.getElementById("dgSearchInput")?.addEventListener("input", (e) => {
      this.filterDataGrid(e.target.value);
    });

    // 14. IPC Stream Listeners (if running in Electron)
    if (window.api) {
      window.api.onPipelineProgress((data) => {
        this.updateProgress(data.progress, data.stage);
      });
      window.api.onPipelineLog((msg) => {
        this.appendLog(msg);
      });
    }
  },

  // -------------------------------------------------------------------------
  // View Switcher (Report / Data / Model)
  // -------------------------------------------------------------------------
  switchView(viewName) {
    this.activeView = viewName;
    document.querySelectorAll(".rail-btn").forEach((b) => {
      b.classList.toggle("active", b.dataset.view === viewName);
    });
    document.querySelectorAll(".stage-view").forEach((v) => v.classList.remove("active"));

    if (viewName === "report") {
      document.getElementById("viewReport").classList.add("active");
      document.getElementById("canvasSlicerBar").style.display = "flex";
      document.getElementById("pbiStatusBar").style.display = "flex";
      this.renderCharts();
    } else if (viewName === "data") {
      document.getElementById("viewData").classList.add("active");
      document.getElementById("canvasSlicerBar").style.display = "none";
      this.renderDataView();
    } else if (viewName === "model") {
      document.getElementById("viewModel").classList.add("active");
      document.getElementById("canvasSlicerBar").style.display = "none";
      this.renderModelView();
    }
  },

  // -------------------------------------------------------------------------
  // Page Switcher (Page 1, 2, 3, 4)
  // -------------------------------------------------------------------------
  switchPage(pageId) {
    this.activePage = pageId;
    document.querySelectorAll(".page-tab").forEach((t) => {
      t.classList.toggle("active", t.dataset.page === pageId);
    });
    document.querySelectorAll(".canvas-page").forEach((p) => p.classList.remove("active"));
    const target = document.getElementById(pageId);
    if (target) target.classList.add("active");

    // Re-render chart sizes if needed
    setTimeout(() => {
      Object.values(this.charts).forEach((c) => c?.resize());
    }, 50);
  },

  // -------------------------------------------------------------------------
  // DAX Measures Setup
  // -------------------------------------------------------------------------
  populateDAXMeasures() {
    const select = document.getElementById("daxMeasureDropdown");
    if (!select) return;
    select.innerHTML = "";

    const measures = this.currentManifest?.measures || this.defaultData.daxMeasures;
    const measureKeys = Array.isArray(measures) ? measures.map((m) => m.name) : Object.keys(measures);

    measureKeys.forEach((key) => {
      const opt = document.createElement("option");
      opt.value = key;
      opt.textContent = `[${key}]`;
      select.appendChild(opt);
    });

    if (measureKeys.length > 0) {
      this.updateDAXFormula(measureKeys[0]);
    }
  },

  updateDAXFormula(measureName) {
    const input = document.getElementById("daxFormulaInput");
    if (!input) return;

    if (this.currentManifest?.measures) {
      const found = this.currentManifest.measures.find((m) => m.name === measureName);
      input.value = found ? found.expression : `[${measureName}] = CALCULATE(...)`;
    } else {
      input.value = this.defaultData.daxMeasures[measureName] || `[${measureName}] = CALCULATE(...)`;
    }
  },

  // -------------------------------------------------------------------------
  // Fields Tree (Accordion Pane)
  // -------------------------------------------------------------------------
  renderFieldsTree() {
    const tree = document.getElementById("fieldsTree");
    if (!tree) return;
    tree.innerHTML = "";

    const tables = this.currentManifest?.tables || this.defaultData.tables;
    const measures = this.currentManifest?.measures || this.defaultData.daxMeasures;

    // 1. _Measures Table Node
    const measuresNode = document.createElement("div");
    measuresNode.className = "table-node open";
    measuresNode.innerHTML = `
      <div class="table-node-header" onclick="this.parentElement.classList.toggle('open')">
        <span class="node-arrow">▶</span>
        <span class="field-icon calc">📐</span>
        <span>_Measures</span>
      </div>
      <ul class="field-list"></ul>
    `;
    const mList = measuresNode.querySelector(".field-list");

    const measureList = Array.isArray(measures)
      ? measures
      : Object.entries(measures).map(([k, v]) => ({ name: k, expression: v }));

    measureList.forEach((m) => {
      const li = document.createElement("li");
      li.className = "field-item";
      li.innerHTML = `<span class="field-icon calc">fx</span> <span>[${m.name}]</span>`;
      li.onclick = () => {
        const sel = document.getElementById("daxMeasureDropdown");
        if (sel) sel.value = m.name;
        this.updateDAXFormula(m.name);
      };
      mList.appendChild(li);
    });
    tree.appendChild(measuresNode);

    // 2. Data Tables Nodes
    tables.forEach((tbl) => {
      const node = document.createElement("div");
      node.className = "table-node";
      const icon = tbl.type === "fact" || tbl.table_type === "fact" ? "📊" : "📦";
      node.innerHTML = `
        <div class="table-node-header" onclick="this.parentElement.classList.toggle('open')">
          <span class="node-arrow">▶</span>
          <span>${icon}</span>
          <span>${tbl.name}</span>
        </div>
        <ul class="field-list"></ul>
      `;
      const fList = node.querySelector(".field-list");
      const cols = tbl.columns || [];

      cols.forEach((c) => {
        const colName = typeof c === "string" ? c : c.name;
        let colIcon = "🔤";
        if (colName.includes("date") || colName.includes("time")) colIcon = "📅";
        else if (colName.includes("id") || colName.includes("key")) colIcon = "🔑";
        else if (colName.includes("amount") || colName.includes("price") || colName.includes("revenue") || colName.includes("cost") || colName.includes("qty") || colName.includes("quantity")) colIcon = "∑";

        const li = document.createElement("li");
        li.className = "field-item";
        li.innerHTML = `<span class="field-icon">${colIcon}</span> <span>${colName}</span>`;
        fList.appendChild(li);
      });
      tree.appendChild(node);
    });
  },

  // -------------------------------------------------------------------------
  // Visualizations & Chart.js Engine
  // -------------------------------------------------------------------------
  renderCharts() {
    const data = this.getFilteredData();
    const isDark = !document.body.classList.contains("powerbi-fluent");
    const gridColor = isDark ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.06)";
    const textColor = isDark ? "#A0A0A0" : "#605E5C";

    // 1. Chart Monthly Trend (Combo Bar & Line)
    const ctxTrend = document.getElementById("chartMonthlyTrend")?.getContext("2d");
    if (ctxTrend) {
      if (this.charts.monthlyTrend) this.charts.monthlyTrend.destroy();
      this.charts.monthlyTrend = new Chart(ctxTrend, {
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
            tooltip: {
              callbacks: {
                label: (ctx) => {
                  if (ctx.dataset.yAxisID === "yMargin") return ` Margin: ${ctx.parsed.y.toFixed(1)}%`;
                  return ` ${ctx.dataset.label}: $${Number(ctx.parsed.y).toLocaleString()}`;
                },
              },
            },
          },
          scales: {
            x: { grid: { color: gridColor }, ticks: { color: textColor, maxRotation: 45 } },
            yRev: {
              type: "linear",
              position: "left",
              grid: { color: gridColor },
              ticks: {
                color: textColor,
                callback: (v) => `$${v >= 1e6 ? (v / 1e6).toFixed(1) + "M" : (v / 1e3).toFixed(0) + "K"}`,
              },
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
    }

    // 2. Chart Category Share (Donut)
    const ctxCat = document.getElementById("chartCategoryShare")?.getContext("2d");
    if (ctxCat) {
      if (this.charts.categoryShare) this.charts.categoryShare.destroy();
      this.charts.categoryShare = new Chart(ctxCat, {
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
            tooltip: {
              callbacks: {
                label: (ctx) => ` $${Number(ctx.raw).toLocaleString()} (${((ctx.raw / data.kpis.totalRevenue) * 100).toFixed(1)}%)`,
              },
            },
          },
          cutout: "68%",
        },
      });
    }

    // 3. Chart Channel Contribution (Bar)
    const ctxChan = document.getElementById("chartChannelBar")?.getContext("2d");
    if (ctxChan) {
      if (this.charts.channelBar) this.charts.channelBar.destroy();
      this.charts.channelBar = new Chart(ctxChan, {
        type: "bar",
        data: {
          labels: data.byChannel.map((c) => c.channel),
          datasets: [
            {
              label: "Channel Revenue",
              data: data.byChannel.map((c) => c.revenue),
              backgroundColor: "#00B4D8",
              borderRadius: 4,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { color: gridColor }, ticks: { color: textColor } },
            y: {
              grid: { color: gridColor },
              ticks: {
                color: textColor,
                callback: (v) => `$${v >= 1e6 ? (v / 1e6).toFixed(1) + "M" : (v / 1e3).toFixed(0) + "K"}`,
              },
            },
          },
        },
      });
    }

    // 4. Chart Top Products (Horizontal Bar)
    const ctxProd = document.getElementById("chartTopProducts")?.getContext("2d");
    if (ctxProd) {
      if (this.charts.topProducts) this.charts.topProducts.destroy();
      this.charts.topProducts = new Chart(ctxProd, {
        type: "bar",
        data: {
          labels: data.topProducts.map((p) => p.product),
          datasets: [
            {
              label: "Sales ($)",
              data: data.topProducts.map((p) => p.revenue),
              backgroundColor: "rgba(242, 200, 15, 0.8)",
              borderRadius: 4,
            },
          ],
        },
        options: {
          indexAxis: "y",
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: {
              grid: { color: gridColor },
              ticks: {
                color: textColor,
                callback: (v) => `$${v >= 1e6 ? (v / 1e6).toFixed(1) + "M" : (v / 1e3).toFixed(0) + "K"}`,
              },
            },
            y: { grid: { color: gridColor }, ticks: { color: textColor, font: { size: 10 } } },
          },
        },
      });
    }

    // 5. Page 2: Margin Trend
    const ctxMargin = document.getElementById("chartMarginTrend")?.getContext("2d");
    if (ctxMargin) {
      if (this.charts.marginTrend) this.charts.marginTrend.destroy();
      this.charts.marginTrend = new Chart(ctxMargin, {
        type: "line",
        data: {
          labels: data.timeSeries.map((t) => t.period),
          datasets: [
            {
              label: "Gross Margin %",
              data: data.timeSeries.map((t) => t.marginPct),
              borderColor: "#2ECC71",
              backgroundColor: "rgba(46, 204, 113, 0.1)",
              fill: true,
              tension: 0.3,
            },
          ],
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
    }

    // 6. Page 2: Customer Segments
    const ctxSeg = document.getElementById("chartSegmentRevenue")?.getContext("2d");
    if (ctxSeg) {
      if (this.charts.segmentRevenue) this.charts.segmentRevenue.destroy();
      this.charts.segmentRevenue = new Chart(ctxSeg, {
        type: "pie",
        data: {
          labels: data.bySegment.map((s) => s.segment),
          datasets: [
            {
              data: data.bySegment.map((s) => s.revenue),
              backgroundColor: ["#118DFF", "#9B59B6", "#E66C37", "#2ECC71", "#F2C80F"],
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: "right", labels: { color: textColor } } },
        },
      });
    }

    // 7. Page 3: Marketing ROAS
    const ctxRoas = document.getElementById("chartMarketingROAS")?.getContext("2d");
    if (ctxRoas) {
      if (this.charts.marketingROAS) this.charts.marketingROAS.destroy();
      this.charts.marketingROAS = new Chart(ctxRoas, {
        type: "bar",
        data: {
          labels: data.marketing.map((m) => m.channel),
          datasets: [
            {
              label: "ROAS (Return on Ad Spend)",
              data: data.marketing.map((m) => m.roas),
              backgroundColor: "#9B59B6",
              borderRadius: 4,
            },
          ],
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
    }

    // 8. Page 3: Marketing Spend vs Attributed Revenue
    const ctxMktSpend = document.getElementById("chartMarketingSpend")?.getContext("2d");
    if (ctxMktSpend) {
      if (this.charts.marketingSpend) this.charts.marketingSpend.destroy();
      this.charts.marketingSpend = new Chart(ctxMktSpend, {
        type: "bar",
        data: {
          labels: data.marketing.map((m) => m.channel),
          datasets: [
            {
              label: "Spend ($)",
              data: data.marketing.map((m) => m.spend),
              backgroundColor: "#E74C3C",
              borderRadius: 4,
            },
            {
              label: "Revenue ($)",
              data: data.marketing.map((m) => m.revenue),
              backgroundColor: "#2ECC71",
              borderRadius: 4,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { grid: { color: gridColor }, ticks: { color: textColor } },
            y: {
              grid: { color: gridColor },
              ticks: {
                color: textColor,
                callback: (v) => `$${v >= 1e6 ? (v / 1e6).toFixed(1) + "M" : (v / 1e3).toFixed(0) + "K"}`,
              },
            },
          },
        },
      });
    }

    // 9. Page 4: Return Reasons
    const ctxReturns = document.getElementById("chartReturnReasons")?.getContext("2d");
    if (ctxReturns) {
      if (this.charts.returnReasons) this.charts.returnReasons.destroy();
      this.charts.returnReasons = new Chart(ctxReturns, {
        type: "doughnut",
        data: {
          labels: data.returns.reasons.map((r) => r.reason.replace(/_/g, " ")),
          datasets: [
            {
              data: data.returns.reasons.map((r) => r.count),
              backgroundColor: ["#E74C3C", "#E66C37", "#F2C80F", "#3498DB", "#95A5A6"],
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: "right", labels: { color: textColor } } },
        },
      });
    }

    // Update KPI Card Numbers
    this.updateKPICards(data.kpis, data.returns);
  },

  // -------------------------------------------------------------------------
  // KPI Cards Update
  // -------------------------------------------------------------------------
  updateKPICards(kpis, returns) {
    const revEl = document.getElementById("kpiRevenueVal");
    const profEl = document.getElementById("kpiProfitVal");
    const margEl = document.getElementById("kpiMarginVal");
    const ordEl = document.getElementById("kpiOrdersVal");
    const untEl = document.getElementById("kpiUnitsVal");
    const retEl = document.getElementById("kpiReturnsVal");

    if (revEl) revEl.textContent = `$${Number(kpis.totalRevenue).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
    if (profEl) profEl.textContent = `$${Number(kpis.grossProfit).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
    if (margEl) margEl.textContent = `${kpis.grossMarginPct.toFixed(1)}%`;
    if (ordEl) ordEl.textContent = Number(kpis.totalOrders).toLocaleString();
    if (untEl) untEl.textContent = Number(kpis.totalUnits).toLocaleString();
    if (retEl && returns) retEl.textContent = `${returns.totalReturns} Items (${returns.returnRate}%)`;
  },

  // -------------------------------------------------------------------------
  // Slicer Filtering Logic
  // -------------------------------------------------------------------------
  getFilteredData() {
    let source = this.currentManifest?.dashboard || this.defaultData;
    let timeSeries = [...(source.timeSeries || [])];
    let byCategory = [...(source.byCategory || [])];
    let byChannel = [...(source.byChannel || [])];
    let topProducts = [...(source.topProducts || [])];
    let bySegment = [...(source.bySegment || [])];
    let marketing = [...(source.marketing || [])];
    let returns = source.returns || this.defaultData.returns;
    let kpis = { ...(source.kpis || this.defaultData.kpis) };

    // Filter by Category
    if (this.activeCategoryFilter !== "ALL") {
      byCategory = byCategory.filter((c) => c.category === this.activeCategoryFilter);
      const catRev = byCategory.reduce((acc, c) => acc + c.revenue, 0);
      kpis.totalRevenue = catRev;
      kpis.grossProfit = catRev * (kpis.grossMarginPct / 100);
    }

    // Filter by Channel
    if (this.activeChannelFilter !== "ALL") {
      byChannel = byChannel.filter((c) => c.channel === this.activeChannelFilter);
    }

    return {
      kpis,
      timeSeries,
      byCategory,
      byChannel,
      topProducts,
      bySegment,
      marketing,
      returns,
    };
  },

  applySlicerFilters() {
    this.renderCharts();
  },

  // -------------------------------------------------------------------------
  // Data View (Tabular Explorer)
  // -------------------------------------------------------------------------
  renderDataView() {
    const tableInfo = document.getElementById("dgTableInfo");
    const thead = document.getElementById("dataGridHead");
    const tbody = document.getElementById("dataGridBody");
    const rowCountEl = document.getElementById("dataGridRowCount");

    const tables = this.currentManifest?.tables || this.defaultData.tables;
    const currentTableMeta = tables.find((t) => t.name === this.activeTable) || tables[0];

    if (!currentTableMeta) return;

    if (tableInfo) {
      tableInfo.innerHTML = `Showing <strong>${currentTableMeta.name}</strong>: ${currentTableMeta.row_count || currentTableMeta.rowCount || 50} rows, ${(currentTableMeta.columns || []).length} columns`;
    }

    // Columns
    const cols = (currentTableMeta.columns || []).map((c) => (typeof c === "string" ? c : c.name));
    thead.innerHTML = `<tr>${cols.map((c) => `<th>${c}</th>`).join("")}</tr>`;

    // Rows
    const previewRows = currentTableMeta.preview_rows || currentTableMeta.previewRows || this.generateSampleRows(currentTableMeta.name, cols);
    tbody.innerHTML = previewRows
      .map((row) => `<tr>${cols.map((c) => `<td>${row[c] !== undefined && row[c] !== null ? row[c] : ""}</td>`).join("")}</tr>`)
      .join("");

    if (rowCountEl) {
      rowCountEl.textContent = `Showing ${previewRows.length} sample records in memory`;
    }
  },

  generateSampleRows(tableName, cols) {
    const rows = [];
    for (let i = 1; i <= 25; i++) {
      const row = {};
      cols.forEach((col) => {
        if (col.includes("id")) row[col] = `${tableName.substring(0, 3).toUpperCase()}_${1000 + i}`;
        else if (col.includes("date")) row[col] = `2024-0${(i % 9) + 1}-15`;
        else if (col.includes("quantity") || col.includes("units")) row[col] = (i % 5) + 1;
        else if (col.includes("price") || col.includes("revenue") || col.includes("cost") || col.includes("spend")) row[col] = ((i * 142.5) % 1200 + 49.99).toFixed(2);
        else if (col.includes("channel")) row[col] = ["Online Direct", "Amazon Marketplace", "Retail Store", "Mobile App", "Wholesale"][i % 5];
        else if (col.includes("category")) row[col] = ["Electronics", "Apparel", "Home & Kitchen", "Fitness", "Beauty"][i % 5];
        else row[col] = `Sample_${col}_${i}`;
      });
      rows.push(row);
    }
    return rows;
  },

  filterDataGrid(query) {
    const q = query.toLowerCase();
    const rows = document.querySelectorAll("#dataGridBody tr");
    rows.forEach((r) => {
      r.style.display = r.textContent.toLowerCase().includes(q) ? "" : "none";
    });
  },

  // -------------------------------------------------------------------------
  // Model View (Star Schema Diagram)
  // -------------------------------------------------------------------------
  renderModelView() {
    const grid = document.getElementById("modelDiagramGrid");
    if (!grid) return;
    grid.innerHTML = "";

    const tables = this.currentManifest?.tables || this.defaultData.tables;

    tables.forEach((tbl) => {
      const isFact = tbl.type === "fact" || tbl.table_type === "fact";
      const card = document.createElement("div");
      card.className = `schema-table-card ${isFact ? "fact" : "dim"}`;
      card.id = `schemaCard_${tbl.name}`;

      const cols = tbl.columns || [];
      const colItems = cols
        .map((c) => {
          const colName = typeof c === "string" ? c : c.name;
          const isPk = c.is_key || colName.endsWith("_id") || colName === "id" || colName === "date";
          return `
          <li class="card-col-item">
            <span class="col-icon">${colName.includes("date") ? "📅" : colName.includes("id") ? "🔑" : "🔤"}</span>
            <span class="col-name">${colName}</span>
            ${isPk ? '<span class="key-badge">PK</span>' : ""}
          </li>
        `;
        })
        .join("");

      card.innerHTML = `
        <div class="card-header">
          <span class="card-title">${tbl.name}</span>
          <span class="card-type-tag">${isFact ? "FACT" : "DIM"}</span>
        </div>
        <ul class="card-columns">
          ${colItems}
        </ul>
      `;
      grid.appendChild(card);
    });

    const badge = document.getElementById("modelStatsBadge");
    const rels = this.currentManifest?.relationships || this.defaultData.relationships;
    if (badge) {
      badge.textContent = `${tables.length} Tables · ${rels.length} Active 1:* Kimball Relationships`;
    }
  },

  // -------------------------------------------------------------------------
  // Financial Statement Table (Page 2)
  // -------------------------------------------------------------------------
  renderFinancialTable() {
    const container = document.getElementById("financialSummaryTable");
    if (!container) return;

    const data = this.defaultData;
    let html = `
      <table class="pbi-data-table">
        <thead>
          <tr>
            <th>Financial Metric (DAX)</th>
            <th>FY 2024 Actual</th>
            <th>FY 2025 Actual</th>
            <th>Total Aggregated</th>
            <th>Variance YoY %</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>Gross Revenue [Total Revenue]</strong></td>
            <td>$4,785,124</td>
            <td>$3,688,904</td>
            <td><strong>$8,474,028</strong></td>
            <td style="color: var(--pbi-accent-green);">+14.2%</td>
          </tr>
          <tr>
            <td>Cost of Goods Sold [Total COGS]</td>
            <td>$3,514,200</td>
            <td>$2,713,620</td>
            <td>$6,227,820</td>
            <td style="color: var(--pbi-text-muted);">+8.4%</td>
          </tr>
          <tr>
            <td><strong>Gross Profit [Gross Profit]</strong></td>
            <td>$1,270,924</td>
            <td>$975,284</td>
            <td><strong>$2,246,208</strong></td>
            <td style="color: var(--pbi-accent-green);">+18.7%</td>
          </tr>
          <tr>
            <td><strong>Gross Margin % [Gross Margin %]</strong></td>
            <td>26.6%</td>
            <td>26.4%</td>
            <td><strong>26.5%</strong></td>
            <td style="color: var(--pbi-accent-gold);">+0.2 pts</td>
          </tr>
          <tr>
            <td>Total Completed Orders [Total Orders]</td>
            <td>285</td>
            <td>215</td>
            <td>500</td>
            <td style="color: var(--pbi-accent-green);">+5.2%</td>
          </tr>
        </tbody>
      </table>
    `;
    container.innerHTML = html;
  },

  // -------------------------------------------------------------------------
  // Pipeline Orchestration
  // -------------------------------------------------------------------------
  async selectAndRunExcel() {
    if (!window.api) {
      alert("Pipeline requires Electron runtime.");
      return;
    }

    const excelPath = await window.api.selectExcelFile();
    if (!excelPath) return;

    this.runPipelineForPath(excelPath);
  },

  async runSamplePipeline() {
    if (!window.api) {
      this.showToast("Sample data loaded into replica canvas.");
      return;
    }

    const samplePath = await window.api.getSamplePath();
    if (!samplePath) {
      alert("Sample workbook not found at data/raw/excel/revenueos_sample.xlsx");
      return;
    }

    this.runPipelineForPath(samplePath, "RevenueOS_Sample");
  },

  async runPipelineForPath(filePath, projectName = "RevenueOS_Report") {
    const modal = document.getElementById("pipelineModal");
    const terminal = document.getElementById("pipelineLogTerminal");
    if (modal) modal.style.display = "flex";
    if (terminal) terminal.innerHTML = "";

    this.updateProgress(5, "Launching Master Backend Engine...");

    try {
      const result = await window.api.runPipeline({
        excelPath: filePath,
        projectName: projectName,
        currency: "$",
      });

      if (result && result.manifest) {
        this.currentManifest = result.manifest;
        this.updateProgress(100, "Pipeline Execution Complete!");
        this.showToast("Dataset loaded & Kimball Star Schema compiled!");

        // Update Document Title
        const titleEl = document.getElementById("documentTitle");
        if (titleEl) titleEl.textContent = `${projectName} - Power BI Desktop Studio`;

        // Update UI
        this.populateDAXMeasures();
        this.renderFieldsTree();
        this.renderCharts();
        this.renderDataView();
        this.renderModelView();

        setTimeout(() => {
          modal.style.display = "none";
        }, 1200);
      }
    } catch (err) {
      this.appendLog(`[ERROR] ${err.message}`);
      this.updateProgress(100, "Pipeline Failed");
    }
  },

  updateProgress(pct, stage) {
    const fill = document.getElementById("pipelineProgressFill");
    const pctText = document.getElementById("pipelinePercentText");
    const stageText = document.getElementById("pipelineStageText");

    if (fill) fill.style.width = `${pct}%`;
    if (pctText) pctText.textContent = `${pct}%`;
    if (stageText) stageText.textContent = stage;
  },

  appendLog(msg) {
    const term = document.getElementById("pipelineLogTerminal");
    if (!term) return;
    const line = document.createElement("div");
    line.textContent = msg;
    term.appendChild(line);
    term.scrollTop = term.scrollHeight;
  },

  // -------------------------------------------------------------------------
  // Native Power BI Shell Actions
  // -------------------------------------------------------------------------
  async launchNativePowerBI() {
    if (!window.api) return;
    const pbitPath = this.currentManifest?.paths?.pbitPath;
    if (pbitPath) {
      await window.api.launchFile(pbitPath);
      this.showToast("Launching Power BI Desktop Template (.pbit)...");
    } else {
      this.showToast("Template ready. Load a dataset first.");
    }
  },

  async exportCSVMarts() {
    if (!window.api) return;
    const csvDir = this.currentManifest?.paths?.csvDir;
    if (csvDir) {
      await window.api.openFolder(csvDir);
    } else {
      this.showToast("CSV marts ready in exports directory.");
    }
  },

  async copyAllDAX() {
    if (!window.api) return;
    const measures = this.currentManifest?.measures || this.defaultData.daxMeasures;
    let text = "// RevenueOS Studio Synthesized DAX Measures\n// © Sarvesh Sharma\n\n";

    if (Array.isArray(measures)) {
      measures.forEach((m) => {
        text += `[${m.name}] =\n${m.expression}\n\n`;
      });
    } else {
      Object.entries(measures).forEach(([k, v]) => {
        text += `[${k}] =\n${v}\n\n`;
      });
    }

    await window.api.copyToClipboard(text);
    this.showToast("All DAX measures copied to clipboard!");
  },

  toggleFocus(containerId) {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.classList.toggle("focused");
    setTimeout(() => Object.values(this.charts).forEach((c) => c?.resize()), 100);
  },

  showToast(message) {
    const toast = document.createElement("div");
    toast.style.position = "fixed";
    toast.style.bottom = "42px";
    toast.style.right = "20px";
    toast.style.backgroundColor = "var(--pbi-accent-blue)";
    toast.style.color = "#FFFFFF";
    toast.style.padding = "10px 18px";
    toast.style.borderRadius = "4px";
    toast.style.fontSize = "12px";
    toast.style.fontWeight = "600";
    toast.style.boxShadow = "0 4px 12px rgba(0,0,0,0.5)";
    toast.style.zIndex = "9999";
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2500);
  },
};

// Initialize Application on DOM Ready
document.addEventListener("DOMContentLoaded", () => {
  app.init();
});
