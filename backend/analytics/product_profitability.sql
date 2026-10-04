-- =============================================================================
-- RevenueOS – Product Profitability Analytics
-- Produces the data for gold.gold_product_profitability and Power BI Page 05.
--
-- Key metrics:
--   Revenue, Margin, COGS, Returns, Classification (quadrant),
--   Inventory Status, Stockout Days, Supplier performance
-- =============================================================================

-- ---------------------------------------------------------------------------
-- CTE 1: Product Order Aggregates
-- ---------------------------------------------------------------------------
WITH product_orders AS (
    SELECT
        fo.product_key,
        dp.product_id,
        dp.product_name,
        dp.category,
        dp.subcategory,
        dp.supplier,
        dp.cost                                             AS unit_cost,
        dp.selling_price,
        dp.margin_pct                                       AS catalogue_margin_pct,

        COUNT(DISTINCT fo.order_id)                         AS order_count,
        SUM(fo.quantity)                                    AS units_sold,
        SUM(fo.gross_revenue)                               AS gross_revenue,
        SUM(fo.discount_amount)                             AS discount_amount,
        SUM(fo.net_sales)                                   AS net_sales,
        SUM(fo.cogs)                                        AS total_cogs,
        SUM(fo.gross_profit)                                AS gross_profit,

        ROUND(SUM(fo.gross_profit) / NULLIF(SUM(fo.net_sales), 0), 4)
                                                            AS realised_margin_pct,
        ROUND(SUM(fo.discount_amount) / NULLIF(SUM(fo.gross_revenue), 0), 4)
                                                            AS avg_discount_pct,
        COUNT(DISTINCT fo.customer_key)                     AS unique_customers
    FROM gold.fact_orders fo
    JOIN gold.dim_product dp ON fo.product_key = dp.product_key
    WHERE fo.status != 'CANCELLED'
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9
),

-- ---------------------------------------------------------------------------
-- CTE 2: Return Metrics per Product
-- ---------------------------------------------------------------------------
product_returns AS (
    SELECT
        fr.product_key,
        SUM(fr.quantity_returned)                           AS units_returned,
        SUM(fr.return_value)                                AS total_return_value,
        COUNT(fr.return_id)                                 AS return_transactions,

        -- Most common return reason
        MODE() WITHIN GROUP (ORDER BY fr.return_reason)     AS top_return_reason
    FROM gold.fact_returns fr
    GROUP BY 1
),

-- ---------------------------------------------------------------------------
-- CTE 3: Inventory Position per Product
-- ---------------------------------------------------------------------------
product_inventory AS (
    SELECT
        fi.product_key,
        SUM(fi.units_available)                             AS current_stock,
        SUM(fi.inventory_value)                             AS inventory_value,
        SUM(CASE WHEN fi.is_stockout THEN 1 ELSE 0 END)    AS stockout_snapshots,
        MAX(fi.units_sold)                                  AS max_daily_units_sold,

        -- Days of inventory = current stock / avg daily sales rate
        ROUND(
            SUM(fi.units_available) /
            NULLIF(AVG(NULLIF(fi.units_sold, 0)), 0),
        1)                                                  AS days_of_inventory
    FROM gold.fact_inventory fi
    GROUP BY 1
),

-- ---------------------------------------------------------------------------
-- CTE 4: Revenue Rank and Margin Rank (for quadrant classification)
-- ---------------------------------------------------------------------------
ranked AS (
    SELECT
        product_id,
        PERCENT_RANK() OVER (ORDER BY net_sales)            AS revenue_pct_rank,
        PERCENT_RANK() OVER (ORDER BY realised_margin_pct)  AS margin_pct_rank
    FROM product_orders
),

-- ---------------------------------------------------------------------------
-- CTE 5: 30-day Revenue Trend per Product
-- ---------------------------------------------------------------------------
product_trend AS (
    SELECT
        fo.product_key,
        SUM(CASE
            WHEN dd.full_date >= CURRENT_DATE - INTERVAL '30 days'
            THEN fo.net_sales ELSE 0
        END)                                                AS revenue_last_30d,
        SUM(CASE
            WHEN dd.full_date >= CURRENT_DATE - INTERVAL '60 days'
             AND dd.full_date  < CURRENT_DATE - INTERVAL '30 days'
            THEN fo.net_sales ELSE 0
        END)                                                AS revenue_prev_30d
    FROM gold.fact_orders fo
    JOIN gold.dim_date    dd ON fo.date_key = dd.date_key
    GROUP BY 1
)

-- ---------------------------------------------------------------------------
-- Final Output
-- ---------------------------------------------------------------------------
SELECT
    po.product_id,
    po.product_name,
    po.category,
    po.subcategory,
    po.supplier,
    po.unit_cost,
    po.selling_price,
    po.catalogue_margin_pct,

    -- Sales performance
    po.order_count,
    po.units_sold,
    po.gross_revenue,
    po.discount_amount,
    po.net_sales,
    po.total_cogs,
    po.gross_profit,
    po.realised_margin_pct,
    po.avg_discount_pct,
    po.unique_customers,

    -- Return performance
    COALESCE(pr.units_returned, 0)                          AS units_returned,
    COALESCE(pr.total_return_value, 0)                      AS total_return_value,
    ROUND(
        COALESCE(pr.units_returned, 0)::NUMERIC /
        NULLIF(po.units_sold, 0),
    4)                                                      AS return_rate,
    pr.top_return_reason,

    -- Inventory
    COALESCE(pi.current_stock, 0)                           AS current_stock,
    COALESCE(pi.inventory_value, 0)                         AS inventory_value,
    COALESCE(pi.stockout_snapshots, 0)                      AS stockout_days,
    pi.days_of_inventory,

    -- Revenue trend
    COALESCE(pt.revenue_last_30d, 0)                        AS revenue_last_30d,
    COALESCE(pt.revenue_prev_30d, 0)                        AS revenue_prev_30d,
    CASE
        WHEN COALESCE(pt.revenue_prev_30d, 0) = 0 THEN NULL
        ELSE ROUND(
            (pt.revenue_last_30d - pt.revenue_prev_30d) /
            pt.revenue_prev_30d,
        4)
    END                                                     AS revenue_trend_pct,

    -- Quadrant classification
    -- Thresholds: 50th percentile for both revenue and margin
    CASE
        WHEN r.revenue_pct_rank >= 0.5 AND r.margin_pct_rank >= 0.5
            THEN 'Revenue Winner'
        WHEN r.revenue_pct_rank >= 0.5 AND r.margin_pct_rank  < 0.5
            THEN 'Revenue Trap'
        WHEN r.revenue_pct_rank  < 0.5 AND r.margin_pct_rank >= 0.5
            THEN 'Hidden Winner'
        WHEN COALESCE(pi.current_stock, 0) > 0 AND COALESCE(po.units_sold, 0) = 0
            THEN 'Dead Stock Candidate'
        ELSE 'Low Priority'
    END                                                     AS product_classification,

    r.revenue_pct_rank,
    r.margin_pct_rank

FROM product_orders          po
LEFT JOIN product_returns    pr  ON po.product_key = pr.product_key
LEFT JOIN product_inventory  pi  ON po.product_key = pi.product_key
LEFT JOIN ranked             r   ON po.product_id  = r.product_id
LEFT JOIN product_trend      pt  ON po.product_key = pt.product_key

ORDER BY po.gross_profit DESC;
