-- =============================================================================
-- RevenueOS – Customer Health Analytics
-- Produces the data for gold.gold_customer_health and Power BI Page 04.
--
-- Key metrics:
--   Revenue, Profit, Margin, Orders, Return Rate,
--   Discount Dependency, Revenue Trend, Health Tier
-- =============================================================================

-- ---------------------------------------------------------------------------
-- CTE 1: Customer Order Aggregates
-- ---------------------------------------------------------------------------
WITH customer_orders AS (
    SELECT
        fo.customer_key,
        dc.customer_id,
        dc.name                                             AS customer_name,
        dc.segment,
        dc.region,
        dc.signup_date,
        COUNT(DISTINCT fo.order_id)                         AS order_count,
        SUM(fo.gross_revenue)                               AS total_gross_revenue,
        SUM(fo.discount_amount)                             AS total_discounts,
        SUM(fo.net_sales)                                   AS total_net_sales,
        SUM(fo.cogs)                                        AS total_cogs,
        SUM(fo.gross_profit)                                AS total_gross_profit,
        SUM(fo.quantity)                                    AS total_units,
        MAX(dd.full_date)                                   AS last_order_date,
        MIN(dd.full_date)                                   AS first_order_date,
        ROUND(AVG(fo.net_sales), 2)                         AS avg_order_value,
        ROUND(AVG(fo.gross_margin_pct), 4)                  AS avg_gross_margin_pct
    FROM gold.fact_orders fo
    JOIN gold.dim_customer dc ON fo.customer_key = dc.customer_key
    JOIN gold.dim_date     dd ON fo.date_key      = dd.date_key
    WHERE fo.status != 'CANCELLED'
    GROUP BY 1, 2, 3, 4, 5, 6
),

-- ---------------------------------------------------------------------------
-- CTE 2: Customer Return Metrics
-- ---------------------------------------------------------------------------
customer_returns AS (
    SELECT
        fo.customer_key,
        SUM(fr.quantity_returned)                           AS units_returned,
        SUM(fr.return_value)                                AS total_return_value
    FROM gold.fact_returns fr
    JOIN (
        SELECT DISTINCT order_id, customer_key
        FROM gold.fact_orders
    ) fo ON fr.order_id = fo.order_id
    GROUP BY 1
),

-- ---------------------------------------------------------------------------
-- CTE 3: Payment Failure Rate per Customer
-- ---------------------------------------------------------------------------
customer_payment_failures AS (
    SELECT
        fo.customer_key,
        COUNT(fp.payment_id)                                AS total_payments,
        SUM(CASE WHEN fp.payment_status = 'FAILED' THEN 1 ELSE 0 END) AS failed_payments,
        ROUND(
            SUM(CASE WHEN fp.payment_status = 'FAILED' THEN 1 ELSE 0 END)::NUMERIC /
            NULLIF(COUNT(fp.payment_id), 0),
        4)                                                  AS payment_fail_rate
    FROM gold.fact_payments fp
    JOIN (
        SELECT DISTINCT order_id, customer_key
        FROM gold.fact_orders
    ) fo ON fp.order_id = fo.order_id
    GROUP BY 1
),

-- ---------------------------------------------------------------------------
-- CTE 4: 30-day vs prior 30-day Revenue Trend
-- ---------------------------------------------------------------------------
revenue_windows AS (
    SELECT
        fo.customer_key,
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
    co.customer_id,
    co.customer_name,
    co.segment,
    co.region,
    CURRENT_DATE - co.signup_date                           AS customer_tenure_days,
    co.order_count,
    co.total_gross_revenue,
    co.total_discounts,
    co.total_net_sales                                      AS total_revenue,
    co.total_cogs,
    co.total_gross_profit,
    ROUND(co.total_gross_profit / NULLIF(co.total_net_sales, 0), 4)
                                                            AS gross_margin_pct,
    co.total_units,
    co.avg_order_value,
    co.last_order_date,
    CURRENT_DATE - co.last_order_date                       AS days_since_last_order,

    -- Return metrics
    COALESCE(cr.units_returned, 0)                          AS units_returned,
    COALESCE(cr.total_return_value, 0)                      AS total_return_value,
    ROUND(
        COALESCE(cr.units_returned, 0)::NUMERIC /
        NULLIF(co.total_units, 0),
    4)                                                      AS return_rate,

    -- Discount dependency
    ROUND(co.total_discounts / NULLIF(co.total_net_sales, 0), 4)
                                                            AS discount_dependency,

    -- Payment behavior
    COALESCE(cpf.payment_fail_rate, 0)                      AS payment_fail_rate,

    -- Revenue trend
    COALESCE(rw.revenue_last_30d, 0)                        AS revenue_last_30d,
    COALESCE(rw.revenue_prev_30d, 0)                        AS revenue_prev_30d,
    CASE
        WHEN COALESCE(rw.revenue_prev_30d, 0) = 0 THEN NULL
        ELSE ROUND(
            (rw.revenue_last_30d - rw.revenue_prev_30d) /
            rw.revenue_prev_30d,
        4)
    END                                                     AS revenue_trend_pct,

    -- Health tier from pre-computed gold table
    ch.health_score,
    ch.health_tier

FROM customer_orders          co
LEFT JOIN customer_returns    cr  ON co.customer_key = cr.customer_key
LEFT JOIN customer_payment_failures cpf ON co.customer_key = cpf.customer_key
LEFT JOIN revenue_windows     rw  ON co.customer_key = rw.customer_key
LEFT JOIN gold.gold_customer_health ch ON co.customer_id = ch.customer_id

ORDER BY co.total_gross_profit DESC;
