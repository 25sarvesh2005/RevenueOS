-- =============================================================================
-- RevenueOS – Revenue Leakage Analytics
-- Produces the data for gold.gold_revenue_leakage and Power BI Page 03.
--
-- Leakage mechanisms tracked:
--   1. Returns              – realised return value
--   2. Excessive Discounts  – discount amount on flagged orders
--   3. Payment Failures     – value of failed payment orders
--   4. Cancellations        – revenue of cancelled orders
--   5. Low-Margin Sales     – profit shortfall vs threshold
--   6. Stockout Opportunity – estimated demand × price during stockout
--
-- IMPORTANT: All values are ESTIMATES or POTENTIAL IMPACT, not confirmed losses.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. Return Leakage
-- ---------------------------------------------------------------------------
WITH return_leakage AS (
    SELECT
        'Returns'                                           AS leakage_type,
        dp.category,
        dp.product_name,
        SUM(fr.return_value)                                AS estimated_impact,
        SUM(fr.quantity_returned)                           AS units_affected,
        COUNT(fr.return_id)                                 AS transaction_count,
        ROUND(
            SUM(fr.quantity_returned)::NUMERIC /
            NULLIF(SUM(fo.quantity), 0),
        4)                                                  AS leakage_rate,
        'Realised return value at transaction price'        AS methodology_note
    FROM gold.fact_returns fr
    JOIN gold.dim_product  dp ON fr.product_key = dp.product_key
    JOIN gold.fact_orders  fo ON fr.order_id = fo.order_id AND fr.product_key = fo.product_key
    GROUP BY dp.category, dp.product_name
),

-- ---------------------------------------------------------------------------
-- 2. Discount Leakage
--    Flag: discount_pct > 25% AND gross_margin_pct < 15%
--    (Thresholds configurable – see docs/assumptions.md)
-- ---------------------------------------------------------------------------
discount_leakage AS (
    SELECT
        'Excessive Discounts'                               AS leakage_type,
        dp.category,
        dp.product_name,
        SUM(fo.discount_amount)                             AS estimated_impact,
        COUNT(fo.order_id)                                  AS transaction_count,
        SUM(fo.quantity)                                    AS units_affected,
        ROUND(AVG(fo.discount_pct), 4)                      AS leakage_rate,
        'Discount amount on orders where discount > 25% AND margin < 15%'
                                                            AS methodology_note
    FROM gold.fact_orders fo
    JOIN gold.dim_product dp ON fo.product_key = dp.product_key
    WHERE fo.discount_pct  > 0.25
      AND fo.gross_margin_pct < 0.15
      AND fo.status != 'CANCELLED'
    GROUP BY dp.category, dp.product_name
),

-- ---------------------------------------------------------------------------
-- 3. Payment Failure Leakage
--    Note: customers may retry; this is potentially affected order value.
-- ---------------------------------------------------------------------------
payment_failure_leakage AS (
    SELECT
        'Payment Failures'                                  AS leakage_type,
        dpm.method_name                                     AS category,
        'All Products'                                      AS product_name,
        SUM(fp.amount)                                      AS estimated_impact,
        COUNT(fp.payment_id)                                AS transaction_count,
        NULL::NUMERIC                                       AS units_affected,
        ROUND(
            COUNT(CASE WHEN fp.payment_status = 'FAILED' THEN 1 END)::NUMERIC /
            NULLIF(COUNT(fp.payment_id), 0),
        4)                                                  AS leakage_rate,
        'Potentially affected order value – customers may retry successfully'
                                                            AS methodology_note
    FROM gold.fact_payments fp
    JOIN gold.dim_payment_method dpm ON fp.payment_method_key = dpm.payment_method_key
    WHERE fp.payment_status = 'FAILED'
    GROUP BY dpm.method_name
),

-- ---------------------------------------------------------------------------
-- 4. Cancellation Leakage
-- ---------------------------------------------------------------------------
cancellation_leakage AS (
    SELECT
        'Cancellations'                                     AS leakage_type,
        dp.category,
        dp.product_name,
        SUM(fo.gross_revenue)                               AS estimated_impact,
        COUNT(fo.order_id)                                  AS transaction_count,
        SUM(fo.quantity)                                    AS units_affected,
        ROUND(
            COUNT(CASE WHEN fo.status = 'CANCELLED' THEN 1 END)::NUMERIC /
            NULLIF(COUNT(fo.order_id), 0),
        4)                                                  AS leakage_rate,
        'Gross revenue of cancelled orders'                 AS methodology_note
    FROM gold.fact_orders fo
    JOIN gold.dim_product dp ON fo.product_key = dp.product_key
    WHERE fo.status = 'CANCELLED'
    GROUP BY dp.category, dp.product_name
),

-- ---------------------------------------------------------------------------
-- 5. Low-Margin Leakage
--    Orders below 15% margin — profit shortfall vs threshold
-- ---------------------------------------------------------------------------
low_margin_leakage AS (
    SELECT
        'Low Margin'                                        AS leakage_type,
        dp.category,
        dp.product_name,
        -- Shortfall: what profit would be at 15% threshold minus actual profit
        SUM(fo.net_sales * 0.15 - fo.gross_profit)         AS estimated_impact,
        COUNT(fo.order_id)                                  AS transaction_count,
        SUM(fo.quantity)                                    AS units_affected,
        ROUND(AVG(fo.gross_margin_pct), 4)                  AS leakage_rate,
        'Profit shortfall vs 15% margin threshold on below-threshold orders'
                                                            AS methodology_note
    FROM gold.fact_orders fo
    JOIN gold.dim_product dp ON fo.product_key = dp.product_key
    WHERE fo.gross_margin_pct < 0.15
      AND fo.gross_margin_pct IS NOT NULL
      AND fo.status != 'CANCELLED'
    GROUP BY dp.category, dp.product_name
    HAVING SUM(fo.net_sales * 0.15 - fo.gross_profit) > 0
),

-- ---------------------------------------------------------------------------
-- 6. Stockout Opportunity (estimated lost sales)
--    Method: avg daily demand × stockout days × avg selling price
-- ---------------------------------------------------------------------------
stockout_opportunity AS (
    SELECT
        'Stockout Opportunity'                              AS leakage_type,
        dp.category,
        dp.product_name,
        -- Estimated opportunity = stockout_days × avg_daily_demand × avg_price
        ROUND(
            SUM(CASE WHEN fi.is_stockout THEN 1 ELSE 0 END) *
            AVG(NULLIF(fi.units_sold, 0)) *
            dp.selling_price,
        2)                                                  AS estimated_impact,
        SUM(CASE WHEN fi.is_stockout THEN 1 ELSE 0 END)    AS transaction_count,
        NULL::NUMERIC                                       AS units_affected,
        ROUND(
            SUM(CASE WHEN fi.is_stockout THEN 1 ELSE 0 END)::NUMERIC /
            NULLIF(COUNT(*), 0),
        4)                                                  AS leakage_rate,
        'Estimated: stockout_days × avg_daily_demand × selling_price. Not confirmed revenue.'
                                                            AS methodology_note
    FROM gold.fact_inventory fi
    JOIN gold.dim_product    dp ON fi.product_key = dp.product_key
    GROUP BY dp.category, dp.product_name, dp.selling_price
    HAVING SUM(CASE WHEN fi.is_stockout THEN 1 ELSE 0 END) > 0
)

-- ---------------------------------------------------------------------------
-- Union all leakage mechanisms
-- ---------------------------------------------------------------------------
SELECT
    leakage_type,
    category,
    product_name,
    ROUND(estimated_impact, 2)                              AS estimated_impact,
    transaction_count,
    units_affected,
    leakage_rate,
    TRUE                                                    AS is_estimate,
    methodology_note

FROM (
    SELECT * FROM return_leakage
    UNION ALL
    SELECT * FROM discount_leakage
    UNION ALL
    SELECT * FROM payment_failure_leakage
    UNION ALL
    SELECT * FROM cancellation_leakage
    UNION ALL
    SELECT * FROM low_margin_leakage
    UNION ALL
    SELECT * FROM stockout_opportunity
) all_leakage

WHERE estimated_impact > 0

ORDER BY estimated_impact DESC;


-- ---------------------------------------------------------------------------
-- Summary Roll-up by Mechanism (for waterfall chart in Power BI)
-- ---------------------------------------------------------------------------
SELECT
    leakage_type,
    ROUND(SUM(estimated_impact), 2)                         AS total_estimated_impact,
    SUM(transaction_count)                                  AS total_transactions,
    ROUND(AVG(leakage_rate), 4)                             AS avg_leakage_rate,
    COUNT(DISTINCT product_name)                            AS products_affected,
    'ESTIMATE'                                              AS value_type
FROM (
    SELECT leakage_type, estimated_impact, transaction_count, leakage_rate, product_name
    FROM return_leakage       UNION ALL
    SELECT leakage_type, estimated_impact, transaction_count, leakage_rate, product_name
    FROM discount_leakage     UNION ALL
    SELECT leakage_type, estimated_impact, transaction_count, leakage_rate, product_name
    FROM payment_failure_leakage UNION ALL
    SELECT leakage_type, estimated_impact, transaction_count, leakage_rate, product_name
    FROM cancellation_leakage UNION ALL
    SELECT leakage_type, estimated_impact, transaction_count, leakage_rate, product_name
    FROM low_margin_leakage   UNION ALL
    SELECT leakage_type, estimated_impact, transaction_count, leakage_rate, product_name
    FROM stockout_opportunity
) summary

GROUP BY leakage_type
ORDER BY total_estimated_impact DESC;
