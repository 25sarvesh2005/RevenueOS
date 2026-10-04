-- =============================================================================
-- RevenueOS – Marketing Efficiency Analytics
-- Produces the data for gold.gold_marketing_efficiency and Power BI Page 07.
--
-- Key metrics:
--   Spend, Revenue, Gross Profit, CTR, Conversion Rate,
--   CAC, ROAS, Contribution After Marketing, Efficiency Tier
--
-- Attribution model: follows the available orders_attributed field.
-- See docs/assumptions.md A4 for attribution assumption.
-- =============================================================================

WITH

-- ---------------------------------------------------------------------------
-- CTE 1: Campaign-level marketing spend and attribution
-- ---------------------------------------------------------------------------
campaign_marketing AS (
    SELECT
        dc.campaign_id,
        dc.channel,
        MIN(dd.full_date)                                   AS period_start,
        MAX(dd.full_date)                                   AS period_end,
        COUNT(DISTINCT dd.full_date)                        AS active_days,
        SUM(fm.spend)                                       AS total_spend,
        SUM(fm.impressions)                                 AS total_impressions,
        SUM(fm.clicks)                                      AS total_clicks,
        SUM(fm.orders_attributed)                           AS orders_attributed,
        SUM(fm.revenue_attributed)                          AS revenue_attributed,
        ROUND(SUM(fm.clicks) / NULLIF(SUM(fm.impressions), 0), 6)
                                                            AS ctr,
        ROUND(SUM(fm.orders_attributed) / NULLIF(SUM(fm.clicks), 0), 6)
                                                            AS conversion_rate
    FROM gold.fact_marketing fm
    JOIN gold.dim_campaign   dc ON fm.campaign_key = dc.campaign_key
    JOIN gold.dim_date       dd ON fm.date_key      = dd.date_key
    GROUP BY dc.campaign_id, dc.channel
),

-- ---------------------------------------------------------------------------
-- CTE 2: Gross profit on orders attributed to each campaign
-- (Join by channel since campaign-level order attribution is approximate)
-- ---------------------------------------------------------------------------
campaign_profit AS (
    SELECT
        dch.channel_name                                    AS channel,
        SUM(fo.gross_profit)                                AS channel_gross_profit,
        SUM(fo.net_sales)                                   AS channel_revenue,
        COUNT(DISTINCT fo.order_id)                         AS channel_orders
    FROM gold.fact_orders fo
    JOIN gold.dim_channel dch ON fo.channel_key = dch.channel_key
    WHERE fo.status != 'CANCELLED'
    GROUP BY dch.channel_name
),

-- ---------------------------------------------------------------------------
-- CTE 3: Rolling 30-day ROAS trend per campaign
-- ---------------------------------------------------------------------------
roas_trend AS (
    SELECT
        dc.campaign_id,
        ROUND(
            SUM(CASE
                WHEN dd.full_date >= CURRENT_DATE - INTERVAL '30 days'
                THEN fm.revenue_attributed ELSE 0
            END) /
            NULLIF(SUM(CASE
                WHEN dd.full_date >= CURRENT_DATE - INTERVAL '30 days'
                THEN fm.spend ELSE 0
            END), 0),
        2)                                                  AS roas_last_30d,
        ROUND(
            SUM(CASE
                WHEN dd.full_date >= CURRENT_DATE - INTERVAL '60 days'
                 AND dd.full_date  < CURRENT_DATE - INTERVAL '30 days'
                THEN fm.revenue_attributed ELSE 0
            END) /
            NULLIF(SUM(CASE
                WHEN dd.full_date >= CURRENT_DATE - INTERVAL '60 days'
                 AND dd.full_date  < CURRENT_DATE - INTERVAL '30 days'
                THEN fm.spend ELSE 0
            END), 0),
        2)                                                  AS roas_prev_30d
    FROM gold.fact_marketing fm
    JOIN gold.dim_campaign   dc ON fm.campaign_key = dc.campaign_key
    JOIN gold.dim_date       dd ON fm.date_key      = dd.date_key
    GROUP BY dc.campaign_id
)

-- ---------------------------------------------------------------------------
-- Final Output
-- ---------------------------------------------------------------------------
SELECT
    cm.campaign_id,
    cm.channel,
    cm.period_start,
    cm.period_end,
    cm.active_days,

    -- Spend & reach
    ROUND(cm.total_spend, 2)                                AS total_spend,
    cm.total_impressions,
    cm.total_clicks,
    cm.orders_attributed,
    ROUND(cm.revenue_attributed, 2)                         AS revenue_attributed,

    -- Engagement
    ROUND(cm.ctr, 4)                                        AS ctr,
    ROUND(cm.conversion_rate, 4)                            AS conversion_rate,

    -- Efficiency metrics
    ROUND(cm.total_spend / NULLIF(cm.orders_attributed, 0), 2)
                                                            AS cac,
    ROUND(cm.revenue_attributed / NULLIF(cm.total_spend, 0), 2)
                                                            AS roas,

    -- Gross profit (channel-level allocation proportional to attributed revenue)
    ROUND(
        cp.channel_gross_profit *
        (cm.revenue_attributed / NULLIF(cp.channel_revenue, 0)),
    2)                                                      AS allocated_gross_profit,

    -- Contribution After Marketing
    ROUND(
        (cp.channel_gross_profit *
         (cm.revenue_attributed / NULLIF(cp.channel_revenue, 0)))
        - cm.total_spend,
    2)                                                      AS contribution_after_marketing,

    -- Revenue per £/$ spent
    ROUND(cm.revenue_attributed / NULLIF(cm.total_spend, 0), 2)
                                                            AS revenue_per_spend_unit,

    -- ROAS trend
    rt.roas_last_30d,
    rt.roas_prev_30d,
    CASE
        WHEN rt.roas_prev_30d IS NULL OR rt.roas_prev_30d = 0 THEN NULL
        ELSE ROUND((rt.roas_last_30d - rt.roas_prev_30d) / rt.roas_prev_30d, 4)
    END                                                     AS roas_trend_pct,

    -- Efficiency classification
    CASE
        WHEN ROUND(cm.revenue_attributed / NULLIF(cm.total_spend, 0), 2) >= 4
         AND (
            (cp.channel_gross_profit *
             (cm.revenue_attributed / NULLIF(cp.channel_revenue, 0)))
            - cm.total_spend
         ) > 0
            THEN 'Strong'
        WHEN ROUND(cm.revenue_attributed / NULLIF(cm.total_spend, 0), 2) BETWEEN 2 AND 4
            THEN 'Average'
        WHEN ROUND(cm.revenue_attributed / NULLIF(cm.total_spend, 0), 2) BETWEEN 1 AND 2
            THEN 'Weak'
        ELSE 'Loss-Making'
    END                                                     AS efficiency_tier

FROM campaign_marketing cm
LEFT JOIN campaign_profit cp ON cm.channel = cp.channel
LEFT JOIN roas_trend      rt ON cm.campaign_id = rt.campaign_id

ORDER BY contribution_after_marketing DESC NULLS LAST;


-- ---------------------------------------------------------------------------
-- Channel Roll-up (for Power BI filter context)
-- ---------------------------------------------------------------------------
SELECT
    cm.channel,
    ROUND(SUM(cm.total_spend), 2)                           AS total_spend,
    ROUND(SUM(cm.revenue_attributed), 2)                    AS total_revenue_attributed,
    ROUND(SUM(cm.total_spend) / NULLIF(SUM(cm.orders_attributed), 0), 2)
                                                            AS blended_cac,
    ROUND(SUM(cm.revenue_attributed) / NULLIF(SUM(cm.total_spend), 0), 2)
                                                            AS blended_roas,
    COUNT(DISTINCT cm.campaign_id)                          AS campaign_count,
    SUM(cm.total_impressions)                               AS total_impressions,
    ROUND(SUM(cm.total_clicks) / NULLIF(SUM(cm.total_impressions), 0), 4)
                                                            AS blended_ctr
FROM campaign_marketing cm
GROUP BY cm.channel
ORDER BY total_revenue_attributed DESC;
