-- =============================================================================
-- RevenueOS – Investigation Queue Analytics
-- Produces the data for gold.gold_investigation_queue and Power BI Page 08.
--
-- This is the Decision Engine output — it converts analytics into a
-- prioritised analyst work queue.
--
-- Priority score = abs(estimated_impact) × severity_weight × confidence_weight
-- All values are investigation candidates, not confirmed findings.
-- =============================================================================

WITH

-- ---------------------------------------------------------------------------
-- CTE 1: High-priority product signals (Revenue Traps + Margin Deterioration)
-- ---------------------------------------------------------------------------
product_signals AS (
    SELECT
        'Product'                                           AS entity_type,
        pp.product_id                                       AS entity_id,
        pp.product_name                                     AS entity_name,
        CASE
            WHEN pp.classification = 'Revenue Trap'
                THEN 'Revenue Trap: High revenue with below-median margin'
            WHEN pp.gross_margin_pct < 0
                THEN 'Negative margin: losing money on every unit sold'
            WHEN pp.return_rate > 0.20
                THEN 'High return rate: above 20% of units returned'
            WHEN pp.stockout_days > 30
                THEN 'Chronic stockout: 30+ days out of stock'
            ELSE 'Margin below threshold'
        END                                                 AS issue,
        'gross_margin_pct'                                  AS primary_metric,
        pp.gross_margin_pct                                 AS observed_value,
        -- baseline: category average margin
        AVG(pp.gross_margin_pct) OVER (PARTITION BY pp.category)
                                                            AS baseline_value,
        pp.gross_profit                                     AS estimated_impact,
        CASE
            WHEN pp.gross_margin_pct < 0            THEN 'HIGH'
            WHEN pp.classification = 'Revenue Trap' THEN 'HIGH'
            WHEN pp.return_rate > 0.20              THEN 'MEDIUM'
            ELSE 'LOW'
        END                                                 AS priority,
        CASE
            WHEN pp.gross_margin_pct < 0            THEN 3
            WHEN pp.classification = 'Revenue Trap' THEN 2
            WHEN pp.return_rate > 0.20              THEN 1.5
            ELSE 1
        END                                                 AS severity_weight,
        'MEDIUM'                                            AS confidence,
        pp.avg_discount_pct,
        pp.return_rate

    FROM gold.gold_product_profitability pp
    WHERE pp.gross_margin_pct < 0.15
       OR pp.classification = 'Revenue Trap'
       OR pp.return_rate > 0.20
       OR pp.stockout_days > 30
),

-- ---------------------------------------------------------------------------
-- CTE 2: At-risk customer signals
-- ---------------------------------------------------------------------------
customer_signals AS (
    SELECT
        'Customer'                                          AS entity_type,
        ch.customer_id                                      AS entity_id,
        ch.customer_name                                    AS entity_name,
        CASE
            WHEN ch.health_tier = 'AT-RISK' AND ch.total_revenue > 10000
                THEN 'High-value customer at risk: declining health score'
            WHEN ch.revenue_trend_pct < -0.30
                THEN 'Revenue decline > 30% vs prior 30 days'
            WHEN ch.return_rate > 0.25
                THEN 'Abnormal return rate: above 25%'
            ELSE 'Low health score'
        END                                                 AS issue,
        'health_score'                                      AS primary_metric,
        ch.health_score                                     AS observed_value,
        0.5                                                 AS baseline_value,  -- midpoint
        ch.total_revenue                                    AS estimated_impact,
        CASE
            WHEN ch.health_tier = 'AT-RISK' AND ch.total_revenue > 10000 THEN 'HIGH'
            WHEN ch.revenue_trend_pct < -0.30                            THEN 'HIGH'
            WHEN ch.return_rate > 0.25                                   THEN 'MEDIUM'
            ELSE 'LOW'
        END                                                 AS priority,
        CASE
            WHEN ch.health_tier = 'AT-RISK' AND ch.total_revenue > 10000 THEN 2.5
            WHEN ch.revenue_trend_pct < -0.30                            THEN 2
            ELSE 1
        END                                                 AS severity_weight,
        'MEDIUM'                                            AS confidence,
        ch.discount_dependency,
        ch.return_rate

    FROM gold.gold_customer_health ch
    WHERE ch.health_tier IN ('AT-RISK', 'LOW')
       OR ch.revenue_trend_pct < -0.20
       OR ch.return_rate > 0.25
),

-- ---------------------------------------------------------------------------
-- CTE 3: Existing anomaly signals
-- ---------------------------------------------------------------------------
anomaly_signals AS (
    SELECT
        'Order'                                             AS entity_type,
        an.entity_id,
        COALESCE(an.entity_id, 'Unknown')                  AS entity_name,
        CONCAT('Anomaly in ', an.metric, ': ', an.detection_method, ' method')
                                                            AS issue,
        an.metric                                           AS primary_metric,
        an.observed_value,
        an.baseline_value,
        COALESCE(an.estimated_financial_impact, 0)          AS estimated_impact,
        an.severity                                         AS priority,
        CASE
            WHEN an.severity = 'CRITICAL' THEN 3
            WHEN an.severity = 'HIGH'     THEN 2
            WHEN an.severity = 'MEDIUM'   THEN 1
            ELSE 0.5
        END                                                 AS severity_weight,
        'MEDIUM'                                            AS confidence,
        NULL::NUMERIC                                       AS avg_discount_pct,
        NULL::NUMERIC                                       AS return_rate
    FROM gold.gold_business_anomalies an
    WHERE an.status = 'OPEN'
),

-- ---------------------------------------------------------------------------
-- CTE 4: Inventory risk signals
-- ---------------------------------------------------------------------------
inventory_signals AS (
    SELECT
        'Product'                                           AS entity_type,
        ir.product_id                                       AS entity_id,
        ir.product_name                                     AS entity_name,
        CASE
            WHEN ir.risk_tier LIKE 'HIGH%'
                THEN 'Inventory risk: ' || ir.risk_tier
            ELSE 'Inventory watch: ' || ir.risk_tier
        END                                                 AS issue,
        'inventory_units'                                   AS primary_metric,
        ir.units_available                                  AS observed_value,
        ir.avg_daily_units_sold * 7                         AS baseline_value,   -- 1-week buffer
        ir.estimated_stockout_opportunity                   AS estimated_impact,
        CASE
            WHEN ir.risk_tier LIKE 'HIGH%' THEN 'HIGH'
            WHEN ir.risk_tier LIKE 'MEDIUM%' THEN 'MEDIUM'
            ELSE 'LOW'
        END                                                 AS priority,
        CASE WHEN ir.risk_tier LIKE 'HIGH%' THEN 2 ELSE 1 END
                                                            AS severity_weight,
        'LOW'                                               AS confidence,   -- stockout is an estimate
        NULL::NUMERIC                                       AS avg_discount_pct,
        NULL::NUMERIC                                       AS return_rate
    FROM gold.gold_inventory_risk ir
    WHERE ir.risk_tier LIKE 'HIGH%' OR ir.risk_tier LIKE 'MEDIUM%'
),

-- ---------------------------------------------------------------------------
-- CTE 5: Combine all signals and score
-- ---------------------------------------------------------------------------
all_signals AS (
    SELECT
        entity_type, entity_id, entity_name, issue,
        primary_metric, observed_value, baseline_value,
        estimated_impact, priority, severity_weight, confidence,
        avg_discount_pct, return_rate,
        -- Priority score: impact × severity × confidence weight
        ABS(COALESCE(estimated_impact, 0)) * severity_weight *
        CASE confidence
            WHEN 'HIGH'   THEN 1.0
            WHEN 'MEDIUM' THEN 0.75
            WHEN 'LOW'    THEN 0.5
            ELSE 0.5
        END                                                 AS priority_score
    FROM product_signals
    UNION ALL
    SELECT
        entity_type, entity_id, entity_name, issue,
        primary_metric, observed_value, baseline_value,
        estimated_impact, priority, severity_weight, confidence,
        avg_discount_pct, return_rate,
        ABS(COALESCE(estimated_impact, 0)) * severity_weight *
        CASE confidence WHEN 'HIGH' THEN 1.0 WHEN 'MEDIUM' THEN 0.75 ELSE 0.5 END
    FROM customer_signals
    UNION ALL
    SELECT
        entity_type, entity_id, entity_name, issue,
        primary_metric, observed_value, baseline_value,
        estimated_impact, priority, severity_weight, confidence,
        avg_discount_pct, return_rate,
        ABS(COALESCE(estimated_impact, 0)) * severity_weight *
        CASE confidence WHEN 'HIGH' THEN 1.0 WHEN 'MEDIUM' THEN 0.75 ELSE 0.5 END
    FROM anomaly_signals
    UNION ALL
    SELECT
        entity_type, entity_id, entity_name, issue,
        primary_metric, observed_value, baseline_value,
        estimated_impact, priority, severity_weight, confidence,
        avg_discount_pct, return_rate,
        ABS(COALESCE(estimated_impact, 0)) * severity_weight *
        CASE confidence WHEN 'HIGH' THEN 1.0 WHEN 'MEDIUM' THEN 0.75 ELSE 0.5 END
    FROM inventory_signals
)

-- ---------------------------------------------------------------------------
-- Final Output: Prioritised Investigation Queue
-- ---------------------------------------------------------------------------
SELECT
    ROW_NUMBER() OVER (ORDER BY priority_score DESC)        AS investigation_rank,
    priority,
    entity_type,
    entity_id,
    entity_name,
    issue,
    primary_metric                                          AS metric,
    ROUND(observed_value, 4)                                AS observed_value,
    ROUND(baseline_value, 4)                                AS baseline_value,
    CASE
        WHEN baseline_value IS NOT NULL AND baseline_value != 0
        THEN ROUND((observed_value - baseline_value) / ABS(baseline_value), 4)
        ELSE NULL
    END                                                     AS deviation_pct,
    ROUND(estimated_impact, 2)                              AS estimated_impact,
    ROUND(priority_score, 2)                                AS priority_score,
    confidence,

    -- Evidence summary
    CASE
        WHEN avg_discount_pct IS NOT NULL
        THEN CONCAT('Avg discount: ', ROUND(avg_discount_pct * 100, 1), '%')
        ELSE ''
    END ||
    CASE
        WHEN return_rate IS NOT NULL
        THEN CONCAT(' | Return rate: ', ROUND(return_rate * 100, 1), '%')
        ELSE ''
    END                                                     AS evidence_summary,

    -- Recommended investigation
    CASE
        WHEN entity_type = 'Product' AND issue LIKE '%Revenue Trap%'
            THEN 'Review discount strategy, COGS changes, and return behaviour'
        WHEN entity_type = 'Product' AND issue LIKE '%stockout%'
            THEN 'Review reorder points and supplier lead times'
        WHEN entity_type = 'Customer' AND priority = 'HIGH'
            THEN 'Review account history, recent orders, and contact account manager'
        WHEN entity_type = 'Order' AND issue LIKE '%Anomaly%'
            THEN 'Review specific order records for data quality or unusual activity'
        ELSE 'Investigate ' || entity_type || ' ' || COALESCE(entity_id, '') || ' for ' || primary_metric
    END                                                     AS recommended_investigation,

    'OPEN'                                                  AS status,
    NOW()                                                   AS generated_at

FROM all_signals
WHERE estimated_impact > 0 OR priority IN ('HIGH', 'MEDIUM')

ORDER BY priority_score DESC
LIMIT 200;   -- surface top 200 investigations
