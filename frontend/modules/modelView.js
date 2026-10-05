/**
 * RevenueOS Studio – Model View & Star Schema Diagram Module
 * ==========================================================
 * Renders Kimball Star Schema table cards, column metadata,
 * and dynamically calculates SVG relationship connector wires.
 */

import { showToast } from "./toast.js";

export function renderModelView(state) {
  const grid = document.getElementById("modelDiagramGrid");
  if (!grid) return;
  grid.innerHTML = "";

  const tables = state.currentManifest?.tables || [];
  const rels = state.currentManifest?.relationships || [];

  // Update dynamic topology stats badge
  const statsBadge = document.getElementById("modelStatsBadge");
  if (statsBadge) {
    const factCount = tables.filter((t) => t.table_type === "fact" || t.name.includes("order") || t.name.includes("fact")).length;
    const dimCount = Math.max(0, tables.length - factCount);
    statsBadge.textContent = `${factCount} Fact Table${factCount === 1 ? "" : "s"} · ${dimCount} Dimension${dimCount === 1 ? "" : "s"} · ${rels.length} Active 1:* Relationships`;
  }

  tables.forEach((tbl) => {
    const isFact = tbl.table_type === "fact" || tbl.name.includes("order") || tbl.name.includes("fact");
    const card = document.createElement("div");
    card.className = `schema-table-card ${isFact ? "fact" : "dim"}`;
    card.id = `schemaCard_${tbl.name}`;

    const cols = tbl.columns || [];
    const colItems = cols
      .map((c) => {
        const colName = typeof c === "string" ? c : c.name;
        const isPk = c.is_key || colName === tbl.primary_key || colName.endsWith("_id");
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
      <ul class="card-columns">${colItems}</ul>
    `;

    card.onclick = () => showTableInspector(tbl);
    grid.appendChild(card);
  });

  // Draw live SVG connectors after layout rendering
  setTimeout(() => drawModelRelationships(state), 100);
}

export function drawModelRelationships(state) {
  const svg = document.getElementById("modelSvgOverlay");
  const container = document.getElementById("modelCanvas");
  if (!svg || !container) return;

  svg.innerHTML = "";
  const rels = state.currentManifest?.relationships || [];
  const containerRect = container.getBoundingClientRect();

  svg.setAttribute("width", container.scrollWidth);
  svg.setAttribute("height", container.scrollHeight);

  rels.forEach((rel) => {
    const fromCard = document.getElementById(`schemaCard_${rel.from_table}`);
    const toCard = document.getElementById(`schemaCard_${rel.to_table}`);
    if (!fromCard || !toCard) return;

    const r1 = fromCard.getBoundingClientRect();
    const r2 = toCard.getBoundingClientRect();

    const x1 = r1.left - containerRect.left + r1.width / 2 + container.scrollLeft;
    const y1 = r1.top - containerRect.top + r1.height / 2 + container.scrollTop;
    const x2 = r2.left - containerRect.left + r2.width / 2 + container.scrollLeft;
    const y2 = r2.top - containerRect.top + r2.height / 2 + container.scrollTop;

    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    const dx = (x2 - x1) * 0.5;
    const d = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;

    path.setAttribute("d", d);
    path.setAttribute("stroke", "#118DFF");
    path.setAttribute("stroke-width", "2");
    path.setAttribute("fill", "none");
    path.setAttribute("stroke-dasharray", "4,4");
    path.style.cursor = "pointer";

    path.onclick = () => {
      showToast(`Relationship: ${rel.from_table}.${rel.from_column} (*) ── (1) ${rel.to_table}.${rel.to_column}`, "info");
    };

    svg.appendChild(path);
  });
}

export function showTableInspector(tbl) {
  showToast(`Inspecting table '${tbl.name}': ${tbl.row_count} rows, ${tbl.columns.length} columns`, "info");
}
