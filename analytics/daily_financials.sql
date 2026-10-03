-- =============================================================================
-- RevenueOS – Daily Financial Rollup
-- Produces the data for gold.gold_daily_financials and Power BI Pages 01 & 02.
--
-- Key metrics:
--   Gross Revenue, Discounts, Net Sales, Returns, Net Revenue,
--   COGS, Gross Profit, Gross Margin %, Orders, Units, AOV
--
-- Slices: Date, Channel, Category, Region
-- Supports: YoY, MoM, rolling 30-day, cohort comparison
-- =============================================================================

WITH

-- ---------------------------------------------------------------------------
-- CTE 1: Daily order metrics
-- ---------------------------------------------------------------------------
daily_orders AS (
    SELECT
        dd.full_date                                        AS report_date,
        dd.year,
        dd.quarter,
        dd.month,
        dd.month_name,
        dd.week,
        dd.day_name,
        dd.is_weekend,
        dch.channel_name                                    AS channel,
        dp.category,
        dp.subcategory,
        dl.location_name                                    AS location,
        dl.region,

        -- Volume
        COUNT(DISTINCT fo.order_id)                         AS order_count,
        SUM(fo.quantity)                                    AS units_sold,
        COUNT(DISTINCT fo.customer_key)                     AS unique_customers,

        -- Revenue waterfall
        SUM(fo.gross_revenue)                               AS gross_revenue,
        SUM(fo.discount_amount)                             AS discount_amount,
        SUM(fo.net_sales)                                   AS net_sales,
        SUM(fo.cogs)                                        AS cogs,
        SUM(fo.gross_profit)                                AS gross_profit,

        ROUND(SUM(fo.gross_profit) / NULLIF(SUM(fo.net_sales), 0), 4)
                                                            AS gross_margin_pct,
        ROUND(SUM(fo.net_sales) / NULLIF(COUNT(DISTINCT fo.order_id), 0), 2)
                                                            AS avg_order_value,
        ROUND(SUM(fo.discount_amount) / NULLIF(SUM(fo.gross_revenue), 0), 4)
                                                            AS avg_discount_pct

    FROM gold.fact_orders fo
    JOIN gold.dim_date     dd  ON fo.date_key      = dd.date_key
    JOIN gold.dim_channel  dch ON fo.channel_key   = dch.channel_key
    JOIN gold.dim_product  dp  ON fo.product_key   = dp.product_key
    JOIN gold.dim_location dl  ON fo.location_key  = dl.location_key
    WHERE fo.status != 'CANCELLED'
    GROUP BY 1,2,3,4,5,6,7,8,9,10,11,12,13
),

-- ---------------------------------------------------------------------------
-- CTE 2: Daily return metrics (joined back to order date, not return date)
-- ---------------------------------------------------------------------------
daily_returns AS (
    SELECT
        fo_orig.date_key,
        dch.channel_name                                    AS channel,
        dp.category,
        dl.region,
        SUM(fr.return_value)                                AS return_value,
        SUM(fr.quantity_returned)                           AS units_returned,
        COUNT(fr.return_id)                                 AS return_count
    FROM gold.fact_returns fr
    JOIN gold.fact_orders  fo_orig ON fr.order_id      = fo_orig.order_id
                                   AND fr.product_key   = fo_orig.product_key
    JOIN gold.dim_channel  dch     ON fo_orig.channel_key = dch.channel_key
    JOIN gold.dim_product  dp      ON fr.product_key   = dp.product_key
    JOIN gold.dim_location dl      ON fo_orig.location_key = dl.location_key
    GROUP BY 1,2,3,4
),

-- ---------------------------------------------------------------------------
-- CTE 3: Period-over-period comparison (MoM, YoY using window functions)
-- ---------------------------------------------------------------------------
with_returns AS (
    SELECT
        do2.*,
        COALESCE(dr.return_value, 0)                        AS return_value,
        COALESCE(dr.units_returned, 0)                      AS units_returned,
        COALESCE(dr.return_count, 0)                        AS return_count,
        do2.net_sales - COALESCE(dr.return_value, 0)        AS net_revenue,
        do2.gross_profit -
            COALESCE(dr.return_value, 0)                    AS net_gross_profit
    FROM daily_orders do2
    JOIN gold.dim_date dd ON dd.full_date = do2.report_date
    LEFT JOIN daily_returns dr
           ON dr.date_key   = dd.date_key
          AND dr.channel    = do2.channel
          AND dr.category   = do2.category
          AND dr.region     = do2.region
)

-- ---------------------------------------------------------------------------
-- Final Output: Daily Financial Summary with Rolling Metrics
-- ---------------------------------------------------------------------------
SELECT
    report_date,
    year,
    quarter,
    month,
    month_name,
    week,
    day_name,
    is_weekend,
    channel,
    category,
    subcategory,
    location,
    region,

    -- Volume
    order_count,
    units_sold,
    unique_customers,

    -- Revenue waterfall
    ROUND(gross_revenue, 2)                                 AS gross_revenue,
    ROUND(discount_amount, 2)                               AS discount_amount,
    ROUND(net_sales, 2)                                     AS net_sales,
    ROUND(return_value, 2)                                  AS return_value,
    ROUND(net_revenue, 2)                                   AS net_revenue,
    ROUND(cogs, 2)                                          AS cogs,
    ROUND(net_gross_profit, 2)                              AS gross_profit,
    gross_margin_pct,
    avg_order_value,
    avg_discount_pct,
    units_returned,
    return_count,
    ROUND(units_returned::NUMERIC / NULLIF(units_sold, 0), 4)
                                                            AS return_rate,

    -- Rolling 7-day revenue
    ROUND(SUM(net_revenue) OVER (
        PARTITION BY channel, category, region
        ORDER BY report_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2)                                                   AS rolling_7d_revenue,

    -- Rolling 30-day revenue
    ROUND(SUM(net_revenue) OVER (
        PARTITION BY channel, category, region
        ORDER BY report_date
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ), 2)                                                   AS rolling_30d_revenue,

    -- Rolling 30-day gross profit
    ROUND(SUM(net_gross_profit) OVER (
        PARTITION BY channel, category, region
        ORDER BY report_date
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ), 2)                                                   AS rolling_30d_gross_profit,

    -- Prior period (same day last week) via LAG
    ROUND(LAG(net_revenue, 7) OVER (
        PARTITION BY channel, category, region
        ORDER BY report_date
    ), 2)                                                   AS revenue_same_day_last_week,

    -- Prior period (same day last month, ~30 days)
    ROUND(LAG(net_revenue, 30) OVER (
        PARTITION BY channel, category, region
        ORDER BY report_date
    ), 2)                                                   AS revenue_30d_ago,

    -- Cumulative YTD
    ROUND(SUM(net_revenue) OVER (
        PARTITION BY year, channel, category, region
        ORDER BY report_date
    ), 2)                                                   AS ytd_revenue,

    ROUND(SUM(net_gross_profit) OVER (
        PARTITION BY year, channel, category, region
        ORDER BY report_date
    ), 2)                                                   AS ytd_gross_profit

FROM with_returns

ORDER BY report_date DESC, channel, category;
