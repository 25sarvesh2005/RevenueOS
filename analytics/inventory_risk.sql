-- =============================================================================
-- RevenueOS – Inventory Risk Analytics
-- Produces the data for gold.gold_inventory_risk and Power BI Page 06.
--
-- Key metrics:
--   Inventory Value, Turnover, Days of Inventory,
--   Stockout Days, Dead Stock, Sell-through Rate,
--   Estimated Stockout Opportunity, Risk Tier
-- =============================================================================

WITH

-- ---------------------------------------------------------------------------
-- CTE 1: Latest inventory snapshot per product-warehouse
-- ---------------------------------------------------------------------------
latest_snapshot AS (
    SELECT DISTINCT ON (fi.product_key, fi.warehouse)
        fi.product_key,
        fi.warehouse,
        dd.full_date                                        AS snapshot_date,
        fi.units_available,
        fi.units_reserved,
        fi.units_sold,
        fi.inventory_value,
        fi.is_stockout
    FROM gold.fact_inventory fi
    JOIN gold.dim_date        dd ON fi.date_key = dd.date_key
    ORDER BY fi.product_key, fi.warehouse, dd.full_date DESC
),

-- ---------------------------------------------------------------------------
-- CTE 2: Historical inventory stats per product-warehouse
-- ---------------------------------------------------------------------------
inventory_history AS (
    SELECT
        fi.product_key,
        fi.warehouse,
        COUNT(*)                                            AS total_snapshots,
        SUM(CASE WHEN fi.is_stockout THEN 1 ELSE 0 END)    AS stockout_days,
        AVG(fi.units_available)                             AS avg_units_available,
        AVG(NULLIF(fi.units_sold, 0))                       AS avg_daily_units_sold,
        SUM(fi.units_sold)                                  AS total_units_sold,
        MAX(fi.units_available + fi.units_sold)             AS max_stock_level
    FROM gold.fact_inventory fi
    GROUP BY fi.product_key, fi.warehouse
),

-- ---------------------------------------------------------------------------
-- CTE 3: Sales velocity (avg daily sales from fact_orders)
-- ---------------------------------------------------------------------------
sales_velocity AS (
    SELECT
        fo.product_key,
        SUM(fo.quantity)                                    AS total_units_ordered,
        COUNT(DISTINCT dd.full_date)                        AS active_selling_days,
        ROUND(
            SUM(fo.quantity)::NUMERIC /
            NULLIF(COUNT(DISTINCT dd.full_date), 0),
        2)                                                  AS avg_daily_demand
    FROM gold.fact_orders fo
    JOIN gold.dim_date    dd ON fo.date_key = dd.date_key
    WHERE fo.status != 'CANCELLED'
    GROUP BY fo.product_key
)

-- ---------------------------------------------------------------------------
-- Final Output: Product-Warehouse Inventory Risk
-- ---------------------------------------------------------------------------
SELECT
    dp.product_id,
    dp.product_name,
    dp.category,
    dp.subcategory,
    dp.supplier,
    ls.warehouse,
    ls.snapshot_date,
    ls.units_available                                      AS current_units,
    ls.units_reserved,
    ls.inventory_value                                      AS current_inventory_value,
    dp.cost                                                 AS unit_cost,
    dp.selling_price,

    -- Historical metrics
    ih.stockout_days,
    ROUND(ih.avg_daily_units_sold, 2)                       AS avg_daily_units_sold,
    ih.total_units_sold,

    -- Sales velocity
    COALESCE(sv.avg_daily_demand, 0)                        AS avg_daily_demand,

    -- Derived metrics
    CASE
        WHEN COALESCE(sv.avg_daily_demand, 0) > 0
        THEN ROUND(ls.units_available / sv.avg_daily_demand, 1)
        ELSE NULL
    END                                                     AS days_of_inventory,

    -- Inventory turnover (annualised)
    CASE
        WHEN NULLIF(ls.units_available, 0) IS NOT NULL AND COALESCE(sv.avg_daily_demand, 0) > 0
        THEN ROUND((sv.avg_daily_demand * 365) / ls.units_available, 2)
        ELSE NULL
    END                                                     AS inventory_turnover,

    -- Sell-through rate
    CASE
        WHEN (ls.units_available + ih.total_units_sold) > 0
        THEN ROUND(
            ih.total_units_sold::NUMERIC /
            (ls.units_available + ih.total_units_sold),
        4)
        ELSE NULL
    END                                                     AS sell_through_rate,

    -- Stockout opportunity (estimate)
    ROUND(ih.stockout_days * COALESCE(sv.avg_daily_demand, 0) * dp.selling_price, 2)
                                                            AS estimated_stockout_opportunity,

    -- Dead stock flag: stock available but zero sales in history
    CASE
        WHEN ls.units_available > 0 AND COALESCE(ih.total_units_sold, 0) = 0
        THEN TRUE ELSE FALSE
    END                                                     AS is_dead_stock,

    -- Risk tier
    CASE
        WHEN ls.is_stockout
            THEN 'HIGH – Stockout'
        WHEN CASE
            WHEN COALESCE(sv.avg_daily_demand, 0) > 0
            THEN ls.units_available / sv.avg_daily_demand
            ELSE NULL
        END < 7
            THEN 'HIGH – Low Stock'
        WHEN ls.units_available > 0 AND COALESCE(ih.total_units_sold, 0) = 0
            THEN 'MEDIUM – Dead Stock'
        WHEN CASE
            WHEN COALESCE(sv.avg_daily_demand, 0) > 0
            THEN ls.units_available / sv.avg_daily_demand
            ELSE NULL
        END BETWEEN 7 AND 30
            THEN 'MEDIUM – Watch'
        ELSE 'LOW'
    END                                                     AS risk_tier

FROM latest_snapshot     ls
JOIN gold.dim_product    dp ON ls.product_key  = dp.product_key
JOIN inventory_history   ih ON ls.product_key  = ih.product_key
                            AND ls.warehouse   = ih.warehouse
LEFT JOIN sales_velocity sv ON ls.product_key  = sv.product_key

ORDER BY
    CASE
        WHEN ls.is_stockout THEN 0
        WHEN ls.units_available > 0 AND COALESCE(ih.total_units_sold, 0) = 0 THEN 1
        ELSE 2
    END,
    ls.inventory_value DESC;


-- ---------------------------------------------------------------------------
-- Warehouse-level Roll-up Summary
-- ---------------------------------------------------------------------------
SELECT
    ls.warehouse,
    COUNT(DISTINCT ls.product_key)                          AS product_count,
    ROUND(SUM(ls.inventory_value), 2)                       AS total_inventory_value,
    SUM(CASE WHEN ls.is_stockout THEN 1 ELSE 0 END)         AS stockout_products,
    SUM(CASE
        WHEN ls.units_available > 0 AND COALESCE(sv.avg_daily_demand, 0) = 0
        THEN 1 ELSE 0
    END)                                                    AS dead_stock_products,
    ROUND(SUM(ls.inventory_value) / NULLIF(COUNT(DISTINCT ls.product_key), 0), 2)
                                                            AS avg_value_per_product
FROM latest_snapshot     ls
LEFT JOIN sales_velocity sv ON ls.product_key = sv.product_key
GROUP BY ls.warehouse
ORDER BY total_inventory_value DESC;
