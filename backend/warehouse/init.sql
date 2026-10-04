-- =============================================================================
-- RevenueOS – Database Initialization
-- Creates schemas and all Bronze / Silver / Gold tables.
-- Run once at database startup (Docker entrypoint or manually).
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Schemas
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

-- ---------------------------------------------------------------------------
-- BRONZE LAYER
-- Raw data as close to source as possible.
-- Additions: source_file, ingestion_timestamp, run_id
-- No business transformations. Invalid records NOT silently deleted.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS bronze.orders (
    run_id               TEXT,
    source_file          TEXT,
    ingestion_timestamp  TIMESTAMPTZ DEFAULT NOW(),
    order_id             TEXT,
    customer_id          TEXT,
    product_id           TEXT,
    order_date           TEXT,          -- raw, may be unparsed
    quantity             TEXT,
    unit_price           TEXT,
    discount             TEXT,
    channel              TEXT,
    location             TEXT,
    status               TEXT,
    _raw_row             INTEGER        -- original row number in source file
);

CREATE TABLE IF NOT EXISTS bronze.customers (
    run_id               TEXT,
    source_file          TEXT,
    ingestion_timestamp  TIMESTAMPTZ DEFAULT NOW(),
    customer_id          TEXT,
    name                 TEXT,
    email                TEXT,
    city                 TEXT,
    region               TEXT,
    signup_date          TEXT,
    segment              TEXT,
    _raw_row             INTEGER
);

CREATE TABLE IF NOT EXISTS bronze.products (
    run_id               TEXT,
    source_file          TEXT,
    ingestion_timestamp  TIMESTAMPTZ DEFAULT NOW(),
    product_id           TEXT,
    product_name         TEXT,
    category             TEXT,
    subcategory          TEXT,
    supplier             TEXT,
    cost                 TEXT,
    selling_price        TEXT,
    _raw_row             INTEGER
);

CREATE TABLE IF NOT EXISTS bronze.payments (
    run_id               TEXT,
    source_file          TEXT,
    ingestion_timestamp  TIMESTAMPTZ DEFAULT NOW(),
    payment_id           TEXT,
    order_id             TEXT,
    payment_date         TEXT,
    payment_method       TEXT,
    amount               TEXT,
    payment_status       TEXT,
    failure_reason       TEXT,
    _raw_row             INTEGER
);

CREATE TABLE IF NOT EXISTS bronze.returns (
    run_id               TEXT,
    source_file          TEXT,
    ingestion_timestamp  TIMESTAMPTZ DEFAULT NOW(),
    return_id            TEXT,
    order_id             TEXT,
    product_id           TEXT,
    return_date          TEXT,
    quantity_returned    TEXT,
    return_reason        TEXT,
    _raw_row             INTEGER
);

CREATE TABLE IF NOT EXISTS bronze.inventory (
    run_id               TEXT,
    source_file          TEXT,
    ingestion_timestamp  TIMESTAMPTZ DEFAULT NOW(),
    product_id           TEXT,
    warehouse            TEXT,
    snapshot_date        TEXT,
    units_available      TEXT,
    units_reserved       TEXT,
    units_sold           TEXT,
    _raw_row             INTEGER
);

CREATE TABLE IF NOT EXISTS bronze.marketing (
    run_id               TEXT,
    source_file          TEXT,
    ingestion_timestamp  TIMESTAMPTZ DEFAULT NOW(),
    campaign_id          TEXT,
    date                 TEXT,
    channel              TEXT,
    spend                TEXT,
    impressions          TEXT,
    clicks               TEXT,
    orders_attributed    TEXT,
    revenue_attributed   TEXT,
    _raw_row             INTEGER
);

-- Quality audit log (written by quality engine)
CREATE TABLE IF NOT EXISTS bronze.quality_log (
    log_id               SERIAL PRIMARY KEY,
    run_id               TEXT,
    logged_at            TIMESTAMPTZ DEFAULT NOW(),
    source_table         TEXT,
    check_type           TEXT,
    severity             TEXT,          -- INFO | WARNING | ERROR | CRITICAL
    message              TEXT,
    affected_count       INTEGER,
    sample_values        TEXT
);

-- Pipeline execution audit log (written by automation engine)
CREATE TABLE IF NOT EXISTS bronze.pipeline_runs (
    run_id               TEXT PRIMARY KEY,
    started_at           TIMESTAMPTZ NOT NULL,
    completed_at         TIMESTAMPTZ,
    duration_seconds     NUMERIC,
    trigger_type         TEXT,          -- MANUAL | SCHEDULED | WATCHER | API
    phase                TEXT,
    status               TEXT,          -- RUNNING | SUCCESS | FAILED | CRITICAL_QUALITY_FAILURE
    records_processed    INTEGER DEFAULT 0,
    metrics_summary      JSONB,
    error_message        TEXT
);

-- ---------------------------------------------------------------------------
-- SILVER LAYER
-- Standardized, validated, typed data. Transformations documented in code.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS silver.orders (
    order_id             TEXT NOT NULL,
    customer_id          TEXT,
    product_id           TEXT,
    order_date           DATE,
    quantity             NUMERIC,
    unit_price           NUMERIC,
    discount_pct         NUMERIC,       -- normalized to 0–1
    channel              TEXT,
    location             TEXT,
    status               TEXT,
    gross_revenue        NUMERIC,       -- quantity × unit_price
    discount_amount      NUMERIC,       -- gross_revenue × discount_pct
    net_sales            NUMERIC,       -- gross_revenue - discount_amount
    source_file          TEXT,
    run_id               TEXT,
    ingested_at          TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS silver.customers (
    customer_id          TEXT NOT NULL,
    name                 TEXT,
    email                TEXT,
    city                 TEXT,
    region               TEXT,
    signup_date          DATE,
    segment              TEXT,
    source_file          TEXT,
    run_id               TEXT,
    ingested_at          TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS silver.products (
    product_id           TEXT NOT NULL,
    product_name         TEXT,
    category             TEXT,
    subcategory          TEXT,
    supplier             TEXT,
    cost                 NUMERIC,
    selling_price        NUMERIC,
    margin_pct           NUMERIC,       -- (selling_price - cost) / selling_price
    source_file          TEXT,
    run_id               TEXT,
    ingested_at          TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS silver.payments (
    payment_id           TEXT NOT NULL,
    order_id             TEXT,
    payment_date         DATE,
    payment_method       TEXT,
    amount               NUMERIC,
    payment_status       TEXT,
    failure_reason       TEXT,
    source_file          TEXT,
    run_id               TEXT,
    ingested_at          TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS silver.returns (
    return_id            TEXT NOT NULL,
    order_id             TEXT,
    product_id           TEXT,
    return_date          DATE,
    quantity_returned    NUMERIC,
    return_reason        TEXT,
    source_file          TEXT,
    run_id               TEXT,
    ingested_at          TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS silver.inventory (
    product_id           TEXT NOT NULL,
    warehouse            TEXT NOT NULL,
    snapshot_date        DATE NOT NULL,
    units_available      NUMERIC,
    units_reserved       NUMERIC,
    units_sold           NUMERIC,
    source_file          TEXT,
    run_id               TEXT,
    ingested_at          TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS silver.marketing (
    campaign_id          TEXT NOT NULL,
    date                 DATE NOT NULL,
    channel              TEXT,
    spend                NUMERIC,
    impressions          NUMERIC,
    clicks               NUMERIC,
    orders_attributed    NUMERIC,
    revenue_attributed   NUMERIC,
    ctr                  NUMERIC,       -- clicks / impressions
    source_file          TEXT,
    run_id               TEXT,
    ingested_at          TIMESTAMPTZ
);

-- ---------------------------------------------------------------------------
-- STAR SCHEMA – Dimension Tables
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS gold.dim_date (
    date_key             INTEGER PRIMARY KEY,  -- YYYYMMDD
    full_date            DATE NOT NULL,
    year                 SMALLINT,
    quarter              SMALLINT,
    month                SMALLINT,
    month_name           TEXT,
    week                 SMALLINT,
    day_of_week          SMALLINT,
    day_name             TEXT,
    is_weekend           BOOLEAN,
    fiscal_year          SMALLINT,
    fiscal_quarter       SMALLINT
);

CREATE TABLE IF NOT EXISTS gold.dim_customer (
    customer_key         SERIAL PRIMARY KEY,
    customer_id          TEXT UNIQUE NOT NULL,
    name                 TEXT,
    email                TEXT,
    city                 TEXT,
    region               TEXT,
    signup_date          DATE,
    segment              TEXT
);

CREATE TABLE IF NOT EXISTS gold.dim_product (
    product_key          SERIAL PRIMARY KEY,
    product_id           TEXT UNIQUE NOT NULL,
    product_name         TEXT,
    category             TEXT,
    subcategory          TEXT,
    supplier             TEXT,
    cost                 NUMERIC,
    selling_price        NUMERIC,
    margin_pct           NUMERIC
);

CREATE TABLE IF NOT EXISTS gold.dim_channel (
    channel_key          SERIAL PRIMARY KEY,
    channel_name         TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS gold.dim_location (
    location_key         SERIAL PRIMARY KEY,
    location_name        TEXT UNIQUE NOT NULL,
    region               TEXT
);

CREATE TABLE IF NOT EXISTS gold.dim_supplier (
    supplier_key         SERIAL PRIMARY KEY,
    supplier_name        TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS gold.dim_campaign (
    campaign_key         SERIAL PRIMARY KEY,
    campaign_id          TEXT UNIQUE NOT NULL,
    channel              TEXT
);

CREATE TABLE IF NOT EXISTS gold.dim_payment_method (
    payment_method_key   SERIAL PRIMARY KEY,
    method_name          TEXT UNIQUE NOT NULL
);

-- ---------------------------------------------------------------------------
-- STAR SCHEMA – Fact Tables
-- ---------------------------------------------------------------------------

-- Grain: one product line per order
CREATE TABLE IF NOT EXISTS gold.fact_orders (
    order_line_key       SERIAL PRIMARY KEY,
    order_id             TEXT NOT NULL,
    date_key             INTEGER REFERENCES gold.dim_date(date_key),
    customer_key         INTEGER REFERENCES gold.dim_customer(customer_key),
    product_key          INTEGER REFERENCES gold.dim_product(product_key),
    channel_key          INTEGER REFERENCES gold.dim_channel(channel_key),
    location_key         INTEGER REFERENCES gold.dim_location(location_key),
    status               TEXT,
    quantity             NUMERIC,
    unit_price           NUMERIC,
    discount_pct         NUMERIC,
    gross_revenue        NUMERIC,
    discount_amount      NUMERIC,
    net_sales            NUMERIC,       -- net sales before returns
    cogs                 NUMERIC,       -- quantity × product.cost
    gross_profit         NUMERIC,       -- net_sales - cogs
    gross_margin_pct     NUMERIC,       -- gross_profit / NULLIF(net_sales,0)
    run_id               TEXT
);

-- Grain: one payment transaction
CREATE TABLE IF NOT EXISTS gold.fact_payments (
    payment_line_key     SERIAL PRIMARY KEY,
    payment_id           TEXT NOT NULL,
    order_id             TEXT,
    date_key             INTEGER REFERENCES gold.dim_date(date_key),
    payment_method_key   INTEGER REFERENCES gold.dim_payment_method(payment_method_key),
    amount               NUMERIC,
    payment_status       TEXT,
    failure_reason       TEXT,
    run_id               TEXT
);

-- Grain: one returned product line
CREATE TABLE IF NOT EXISTS gold.fact_returns (
    return_line_key      SERIAL PRIMARY KEY,
    return_id            TEXT NOT NULL,
    order_id             TEXT,
    date_key             INTEGER REFERENCES gold.dim_date(date_key),
    product_key          INTEGER REFERENCES gold.dim_product(product_key),
    quantity_returned    NUMERIC,
    return_reason        TEXT,
    return_value         NUMERIC,       -- quantity_returned × unit_price
    run_id               TEXT
);

-- Grain: one product at one warehouse on one snapshot date
CREATE TABLE IF NOT EXISTS gold.fact_inventory (
    inventory_key        SERIAL PRIMARY KEY,
    date_key             INTEGER REFERENCES gold.dim_date(date_key),
    product_key          INTEGER REFERENCES gold.dim_product(product_key),
    supplier_key         INTEGER REFERENCES gold.dim_supplier(supplier_key),
    warehouse            TEXT,
    units_available      NUMERIC,
    units_reserved       NUMERIC,
    units_sold           NUMERIC,
    inventory_value      NUMERIC,       -- units_available × product.cost
    is_stockout          BOOLEAN,       -- units_available = 0
    run_id               TEXT
);

-- Grain: one campaign/channel/date combination
CREATE TABLE IF NOT EXISTS gold.fact_marketing (
    marketing_key        SERIAL PRIMARY KEY,
    date_key             INTEGER REFERENCES gold.dim_date(date_key),
    campaign_key         INTEGER REFERENCES gold.dim_campaign(campaign_key),
    spend                NUMERIC,
    impressions          NUMERIC,
    clicks               NUMERIC,
    orders_attributed    NUMERIC,
    revenue_attributed   NUMERIC,
    ctr                  NUMERIC,
    conversion_rate      NUMERIC,       -- orders_attributed / NULLIF(clicks,0)
    roas                 NUMERIC,       -- revenue_attributed / NULLIF(spend,0)
    run_id               TEXT
);

-- ---------------------------------------------------------------------------
-- GOLD LAYER – Analytical / Intelligence Tables
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS gold.gold_daily_financials (
    report_date          DATE NOT NULL,
    channel              TEXT,
    category             TEXT,
    region               TEXT,
    gross_revenue        NUMERIC,
    discount_amount      NUMERIC,
    net_sales            NUMERIC,
    return_value         NUMERIC,
    net_revenue          NUMERIC,       -- net_sales - return_value
    cogs                 NUMERIC,
    gross_profit         NUMERIC,
    gross_margin_pct     NUMERIC,
    order_count          INTEGER,
    units_sold           NUMERIC,
    avg_order_value      NUMERIC,
    run_id               TEXT,
    PRIMARY KEY (report_date, channel, category, region)
);

CREATE TABLE IF NOT EXISTS gold.gold_customer_health (
    customer_id          TEXT PRIMARY KEY,
    customer_name        TEXT,
    segment              TEXT,
    region               TEXT,
    total_revenue        NUMERIC,
    total_gross_profit   NUMERIC,
    gross_margin_pct     NUMERIC,
    order_count          INTEGER,
    avg_order_value      NUMERIC,
    return_rate          NUMERIC,
    discount_dependency  NUMERIC,       -- avg discount_pct
    payment_fail_rate    NUMERIC,
    days_since_last_order INTEGER,
    revenue_last_30d     NUMERIC,
    revenue_prev_30d     NUMERIC,
    revenue_trend_pct    NUMERIC,
    recency_score        NUMERIC,
    frequency_score      NUMERIC,
    monetary_score       NUMERIC,
    profitability_score  NUMERIC,
    trend_score          NUMERIC,
    behavior_score       NUMERIC,
    health_score         NUMERIC,       -- composite weighted score
    health_tier          TEXT,          -- HIGH / MEDIUM / LOW / AT-RISK
    run_id               TEXT,
    computed_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gold.gold_product_profitability (
    product_id           TEXT PRIMARY KEY,
    product_name         TEXT,
    category             TEXT,
    subcategory          TEXT,
    supplier             TEXT,
    revenue              NUMERIC,
    units_sold           NUMERIC,
    discount_amount      NUMERIC,
    return_value         NUMERIC,
    cogs                 NUMERIC,
    gross_profit         NUMERIC,
    gross_margin_pct     NUMERIC,
    units_in_inventory   NUMERIC,
    stockout_days        INTEGER,
    return_rate          NUMERIC,
    classification       TEXT,          -- Revenue Winner / Revenue Trap / Hidden Winner / Dead Stock
    run_id               TEXT,
    computed_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gold.gold_revenue_leakage (
    leakage_id           SERIAL PRIMARY KEY,
    run_id               TEXT,
    leakage_type         TEXT NOT NULL, -- Returns | Discounts | PaymentFailure | Cancellation | Stockout | LowMargin
    entity_type          TEXT,          -- Product | Customer | Channel | Campaign
    entity_id            TEXT,
    entity_name          TEXT,
    estimated_impact     NUMERIC,
    leakage_rate         NUMERIC,
    supporting_metric    TEXT,
    supporting_value     NUMERIC,
    threshold_used       NUMERIC,
    is_estimate          BOOLEAN DEFAULT TRUE,
    computed_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gold.gold_inventory_risk (
    product_id           TEXT NOT NULL,
    warehouse            TEXT NOT NULL,
    snapshot_date        DATE NOT NULL,
    product_name         TEXT,
    category             TEXT,
    supplier             TEXT,
    units_available      NUMERIC,
    inventory_value      NUMERIC,
    stockout_days        INTEGER,
    days_of_inventory    NUMERIC,
    inventory_turnover   NUMERIC,
    sell_through_rate    NUMERIC,
    estimated_stockout_impact NUMERIC,
    is_dead_stock        BOOLEAN,
    risk_tier            TEXT,          -- HIGH / MEDIUM / LOW
    run_id               TEXT,
    computed_at          TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (product_id, warehouse, snapshot_date)
);

CREATE TABLE IF NOT EXISTS gold.gold_marketing_efficiency (
    campaign_id          TEXT NOT NULL,
    period_start         DATE,
    period_end           DATE,
    channel              TEXT,
    spend                NUMERIC,
    impressions          NUMERIC,
    clicks               NUMERIC,
    orders_attributed    NUMERIC,
    revenue_attributed   NUMERIC,
    gross_profit         NUMERIC,
    ctr                  NUMERIC,
    conversion_rate      NUMERIC,
    cac                  NUMERIC,       -- spend / NULLIF(orders_attributed,0)
    roas                 NUMERIC,
    contribution_after_marketing NUMERIC, -- gross_profit - spend
    efficiency_tier      TEXT,          -- Strong / Average / Weak / Loss-Making
    run_id               TEXT,
    computed_at          TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (campaign_id, period_start)
);

CREATE TABLE IF NOT EXISTS gold.gold_business_anomalies (
    anomaly_id           SERIAL PRIMARY KEY,
    detected_at          TIMESTAMPTZ DEFAULT NOW(),
    run_id               TEXT,
    entity_type          TEXT NOT NULL,
    entity_id            TEXT,
    metric               TEXT NOT NULL,
    observed_value       NUMERIC,
    baseline_value       NUMERIC,
    deviation_pct        NUMERIC,
    severity             TEXT,          -- LOW | MEDIUM | HIGH | CRITICAL
    estimated_financial_impact NUMERIC,
    detection_method     TEXT,          -- IQR | ZScore | IsolationForest | BusinessRule
    status               TEXT DEFAULT 'OPEN'
);

CREATE TABLE IF NOT EXISTS gold.gold_investigation_queue (
    investigation_id     SERIAL PRIMARY KEY,
    created_at           TIMESTAMPTZ DEFAULT NOW(),
    run_id               TEXT,
    priority             TEXT NOT NULL, -- HIGH | MEDIUM | LOW
    priority_score       NUMERIC,
    entity_type          TEXT NOT NULL,
    entity_id            TEXT,
    entity_name          TEXT,
    issue                TEXT NOT NULL,
    metric               TEXT,
    observed_value       NUMERIC,
    baseline_value       NUMERIC,
    estimated_impact     NUMERIC,
    possible_drivers     TEXT,          -- JSON array as text
    recommended_investigation TEXT,
    confidence           TEXT,          -- HIGH | MEDIUM | LOW
    evidence_summary     TEXT,
    status               TEXT DEFAULT 'OPEN',
    anomaly_id           INTEGER REFERENCES gold.gold_business_anomalies(anomaly_id)
);

-- ---------------------------------------------------------------------------
-- Indexes for common query patterns
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_fact_orders_date       ON gold.fact_orders(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_orders_customer   ON gold.fact_orders(customer_key);
CREATE INDEX IF NOT EXISTS idx_fact_orders_product    ON gold.fact_orders(product_key);
CREATE INDEX IF NOT EXISTS idx_fact_orders_channel    ON gold.fact_orders(channel_key);
CREATE INDEX IF NOT EXISTS idx_fact_returns_date      ON gold.fact_returns(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_returns_product   ON gold.fact_returns(product_key);
CREATE INDEX IF NOT EXISTS idx_fact_payments_date     ON gold.fact_payments(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_inventory_date    ON gold.fact_inventory(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_inventory_product ON gold.fact_inventory(product_key);
CREATE INDEX IF NOT EXISTS idx_anomalies_entity       ON gold.gold_business_anomalies(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_queue_priority         ON gold.gold_investigation_queue(priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_silver_orders_date     ON silver.orders(order_date);
CREATE INDEX IF NOT EXISTS idx_silver_orders_cust     ON silver.orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_silver_orders_prod     ON silver.orders(product_id);
