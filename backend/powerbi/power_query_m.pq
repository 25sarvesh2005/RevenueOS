/* =============================================================================
   RevenueOS – Power Query (M) Script Library
   Connects Power BI directly to PostgreSQL "gold" star schema tables.
   
   Instructions:
   1. In Power BI Desktop: Home -> Transform Data (Power Query Editor).
   2. Manage Parameters -> Create:
        - "DBServer"   (Text, e.g. "localhost:5432")
        - "DBDatabase" (Text, e.g. "revenueos")
   3. New Source -> Blank Query -> Advanced Editor -> Paste the corresponding query.
   ============================================================================= */

// -----------------------------------------------------------------------------
// Parameters
// -----------------------------------------------------------------------------
// Parameter: DBServer
"localhost:5432" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]

// Parameter: DBDatabase
"revenueos" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]


// -----------------------------------------------------------------------------
// DimDate
// -----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database(DBServer, DBDatabase),
    gold_dim_date = Source{[Schema="gold",Item="dim_date"]}[Data],
    ChangedTypes = Table.TransformColumnTypes(gold_dim_date,{
        {"date_key", Int64.Type},
        {"full_date", type date},
        {"year", Int64.Type},
        {"quarter", Int64.Type},
        {"month", Int64.Type},
        {"month_name", type text},
        {"week", Int64.Type},
        {"day_of_week", Int64.Type},
        {"day_name", type text},
        {"is_weekend", type logical},
        {"fiscal_year", Int64.Type},
        {"fiscal_quarter", Int64.Type}
    })
in
    ChangedTypes


// -----------------------------------------------------------------------------
// DimCustomer
// -----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database(DBServer, DBDatabase),
    gold_dim_cust = Source{[Schema="gold",Item="dim_customer"]}[Data],
    ChangedTypes = Table.TransformColumnTypes(gold_dim_cust,{
        {"customer_key", Int64.Type},
        {"customer_id", type text},
        {"name", type text},
        {"email", type text},
        {"city", type text},
        {"region", type text},
        {"signup_date", type date},
        {"segment", type text}
    })
in
    ChangedTypes


// -----------------------------------------------------------------------------
// DimProduct
// -----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database(DBServer, DBDatabase),
    gold_dim_prod = Source{[Schema="gold",Item="dim_product"]}[Data],
    ChangedTypes = Table.TransformColumnTypes(gold_dim_prod,{
        {"product_key", Int64.Type},
        {"product_id", type text},
        {"product_name", type text},
        {"category", type text},
        {"subcategory", type text},
        {"supplier", type text},
        {"cost", Currency.Type},
        {"selling_price", Currency.Type},
        {"margin_pct", Percentage.Type}
    })
in
    ChangedTypes


// -----------------------------------------------------------------------------
// FactOrders
// -----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database(DBServer, DBDatabase),
    gold_fact_orders = Source{[Schema="gold",Item="fact_orders"]}[Data],
    ChangedTypes = Table.TransformColumnTypes(gold_fact_orders,{
        {"order_line_key", Int64.Type},
        {"order_id", type text},
        {"date_key", Int64.Type},
        {"customer_key", Int64.Type},
        {"product_key", Int64.Type},
        {"channel_key", Int64.Type},
        {"location_key", Int64.Type},
        {"quantity", Int64.Type},
        {"unit_price", Currency.Type},
        {"discount_pct", Percentage.Type},
        {"discount_amount", Currency.Type},
        {"gross_revenue", Currency.Type},
        {"net_sales", Currency.Type},
        {"cogs", Currency.Type},
        {"gross_profit", Currency.Type},
        {"gross_margin_pct", Percentage.Type},
        {"status", type text},
        {"run_id", type text}
    })
in
    ChangedTypes


// -----------------------------------------------------------------------------
// FactPayments
// -----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database(DBServer, DBDatabase),
    gold_fact_payments = Source{[Schema="gold",Item="fact_payments"]}[Data],
    ChangedTypes = Table.TransformColumnTypes(gold_fact_payments,{
        {"payment_line_key", Int64.Type},
        {"payment_id", type text},
        {"order_id", type text},
        {"date_key", Int64.Type},
        {"payment_method_key", Int64.Type},
        {"amount", Currency.Type},
        {"payment_status", type text},
        {"failure_reason", type text},
        {"run_id", type text}
    })
in
    ChangedTypes


// -----------------------------------------------------------------------------
// FactReturns
// -----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database(DBServer, DBDatabase),
    gold_fact_returns = Source{[Schema="gold",Item="fact_returns"]}[Data],
    ChangedTypes = Table.TransformColumnTypes(gold_fact_returns,{
        {"return_line_key", Int64.Type},
        {"return_id", type text},
        {"order_id", type text},
        {"date_key", Int64.Type},
        {"product_key", Int64.Type},
        {"quantity_returned", Int64.Type},
        {"return_value", Currency.Type},
        {"return_reason", type text},
        {"run_id", type text}
    })
in
    ChangedTypes


// -----------------------------------------------------------------------------
// FactInventory
// -----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database(DBServer, DBDatabase),
    gold_fact_inv = Source{[Schema="gold",Item="fact_inventory"]}[Data],
    ChangedTypes = Table.TransformColumnTypes(gold_fact_inv,{
        {"inventory_key", Int64.Type},
        {"date_key", Int64.Type},
        {"product_key", Int64.Type},
        {"supplier_key", Int64.Type},
        {"warehouse", type text},
        {"units_available", Int64.Type},
        {"units_reserved", Int64.Type},
        {"units_sold", Int64.Type},
        {"inventory_value", Currency.Type},
        {"is_stockout", type logical},
        {"run_id", type text}
    })
in
    ChangedTypes


// -----------------------------------------------------------------------------
// FactMarketing
// -----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database(DBServer, DBDatabase),
    gold_fact_mkt = Source{[Schema="gold",Item="fact_marketing"]}[Data],
    ChangedTypes = Table.TransformColumnTypes(gold_fact_mkt,{
        {"marketing_key", Int64.Type},
        {"campaign_key", Int64.Type},
        {"date_key", Int64.Type},
        {"spend", Currency.Type},
        {"impressions", Int64.Type},
        {"clicks", Int64.Type},
        {"orders_attributed", Int64.Type},
        {"revenue_attributed", Currency.Type},
        {"ctr", Percentage.Type},
        {"conversion_rate", Percentage.Type},
        {"roas", type number},
        {"run_id", type text}
    })
in
    ChangedTypes


// -----------------------------------------------------------------------------
// DimChannel
// -----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database(DBServer, DBDatabase),
    gold_dim_channel = Source{[Schema="gold",Item="dim_channel"]}[Data],
    ChangedTypes = Table.TransformColumnTypes(gold_dim_channel,{
        {"channel_key", Int64.Type},
        {"channel_name", type text}
    })
in
    ChangedTypes


// -----------------------------------------------------------------------------
// DimLocation
// -----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database(DBServer, DBDatabase),
    gold_dim_location = Source{[Schema="gold",Item="dim_location"]}[Data],
    ChangedTypes = Table.TransformColumnTypes(gold_dim_location,{
        {"location_key", Int64.Type},
        {"location_name", type text},
        {"region", type text}
    })
in
    ChangedTypes


// -----------------------------------------------------------------------------
// DimSupplier
// -----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database(DBServer, DBDatabase),
    gold_dim_supplier = Source{[Schema="gold",Item="dim_supplier"]}[Data],
    ChangedTypes = Table.TransformColumnTypes(gold_dim_supplier,{
        {"supplier_key", Int64.Type},
        {"supplier_name", type text}
    })
in
    ChangedTypes


// -----------------------------------------------------------------------------
// DimCampaign
// -----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database(DBServer, DBDatabase),
    gold_dim_campaign = Source{[Schema="gold",Item="dim_campaign"]}[Data],
    ChangedTypes = Table.TransformColumnTypes(gold_dim_campaign,{
        {"campaign_key", Int64.Type},
        {"campaign_id", type text},
        {"channel", type text}
    })
in
    ChangedTypes


// -----------------------------------------------------------------------------
// DimPaymentMethod
// -----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database(DBServer, DBDatabase),
    gold_dim_payment_method = Source{[Schema="gold",Item="dim_payment_method"]}[Data],
    ChangedTypes = Table.TransformColumnTypes(gold_dim_payment_method,{
        {"payment_method_key", Int64.Type},
        {"method_name", type text}
    })
in
    ChangedTypes


// -----------------------------------------------------------------------------
// GoldInvestigationQueue
// -----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database(DBServer, DBDatabase),
    gold_queue = Source{[Schema="gold",Item="gold_investigation_queue"]}[Data],
    ChangedTypes = Table.TransformColumnTypes(gold_queue,{
        {"investigation_id", Int64.Type},
        {"created_at", type datetimezone},
        {"priority", type text},
        {"priority_score", type number},
        {"entity_type", type text},
        {"entity_id", type text},
        {"entity_name", type text},
        {"issue", type text},
        {"metric", type text},
        {"observed_value", type number},
        {"baseline_value", type number},
        {"estimated_impact", Currency.Type},
        {"possible_drivers", type text},
        {"recommended_investigation", type text},
        {"confidence", type text},
        {"evidence_summary", type text},
        {"status", type text}
    })
in
    ChangedTypes


// -----------------------------------------------------------------------------
// GoldProductProfitability
// -----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database(DBServer, DBDatabase),
    gold_product_prof = Source{[Schema="gold",Item="gold_product_profitability"]}[Data],
    ChangedTypes = Table.TransformColumnTypes(gold_product_prof,{
        {"product_id", type text},
        {"product_name", type text},
        {"category", type text},
        {"subcategory", type text},
        {"supplier", type text},
        {"revenue", Currency.Type},
        {"units_sold", Int64.Type},
        {"discount_amount", Currency.Type},
        {"return_value", Currency.Type},
        {"cogs", Currency.Type},
        {"gross_profit", Currency.Type},
        {"gross_margin_pct", Percentage.Type},
        {"units_in_inventory", type number},
        {"stockout_days", Int64.Type},
        {"return_rate", Percentage.Type},
        {"classification", type text},
        {"run_id", type text},
        {"computed_at", type datetimezone}
    })
in
    ChangedTypes


// -----------------------------------------------------------------------------
// GoldCustomerHealth
// -----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database(DBServer, DBDatabase),
    gold_cust_health = Source{[Schema="gold",Item="gold_customer_health"]}[Data],
    ChangedTypes = Table.TransformColumnTypes(gold_cust_health,{
        {"customer_id", type text},
        {"customer_name", type text},
        {"segment", type text},
        {"region", type text},
        {"total_revenue", Currency.Type},
        {"total_gross_profit", Currency.Type},
        {"gross_margin_pct", Percentage.Type},
        {"order_count", Int64.Type},
        {"avg_order_value", Currency.Type},
        {"return_rate", Percentage.Type},
        {"discount_dependency", Percentage.Type},
        {"payment_fail_rate", Percentage.Type},
        {"days_since_last_order", Int64.Type},
        {"revenue_last_30d", Currency.Type},
        {"revenue_prev_30d", Currency.Type},
        {"revenue_trend_pct", Percentage.Type},
        {"recency_score", type number},
        {"frequency_score", type number},
        {"monetary_score", type number},
        {"profitability_score", type number},
        {"trend_score", type number},
        {"behavior_score", type number},
        {"health_score", type number},
        {"health_tier", type text},
        {"run_id", type text},
        {"computed_at", type datetimezone}
    })
in
    ChangedTypes


// -----------------------------------------------------------------------------
// GoldDailyFinancials
// -----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database(DBServer, DBDatabase),
    gold_daily = Source{[Schema="gold",Item="gold_daily_financials"]}[Data],
    ChangedTypes = Table.TransformColumnTypes(gold_daily,{
        {"report_date", type date},
        {"channel", type text},
        {"category", type text},
        {"region", type text},
        {"gross_revenue", Currency.Type},
        {"discount_amount", Currency.Type},
        {"net_sales", Currency.Type},
        {"return_value", Currency.Type},
        {"net_revenue", Currency.Type},
        {"cogs", Currency.Type},
        {"gross_profit", Currency.Type},
        {"gross_margin_pct", Percentage.Type},
        {"order_count", Int64.Type},
        {"units_sold", Int64.Type},
        {"avg_order_value", Currency.Type},
        {"run_id", type text}
    })
in
    ChangedTypes


// -----------------------------------------------------------------------------
// GoldRevenueLeakage
// -----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database(DBServer, DBDatabase),
    gold_leakage = Source{[Schema="gold",Item="gold_revenue_leakage"]}[Data],
    ChangedTypes = Table.TransformColumnTypes(gold_leakage,{
        {"leakage_id", Int64.Type},
        {"run_id", type text},
        {"leakage_type", type text},
        {"entity_type", type text},
        {"entity_id", type text},
        {"entity_name", type text},
        {"estimated_impact", Currency.Type},
        {"leakage_rate", Percentage.Type},
        {"supporting_metric", type text},
        {"supporting_value", type number},
        {"threshold_used", type number},
        {"is_estimate", type logical},
        {"computed_at", type datetimezone}
    })
in
    ChangedTypes


// -----------------------------------------------------------------------------
// GoldInventoryRisk
// -----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database(DBServer, DBDatabase),
    gold_inv_risk = Source{[Schema="gold",Item="gold_inventory_risk"]}[Data],
    ChangedTypes = Table.TransformColumnTypes(gold_inv_risk,{
        {"product_id", type text},
        {"warehouse", type text},
        {"snapshot_date", type date},
        {"product_name", type text},
        {"category", type text},
        {"supplier", type text},
        {"units_available", Int64.Type},
        {"inventory_value", Currency.Type},
        {"stockout_days", Int64.Type},
        {"days_of_inventory", type number},
        {"inventory_turnover", type number},
        {"sell_through_rate", Percentage.Type},
        {"estimated_stockout_impact", Currency.Type},
        {"is_dead_stock", type logical},
        {"risk_tier", type text},
        {"run_id", type text},
        {"computed_at", type datetimezone}
    })
in
    ChangedTypes


// -----------------------------------------------------------------------------
// GoldMarketingEfficiency
// -----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database(DBServer, DBDatabase),
    gold_mkt_eff = Source{[Schema="gold",Item="gold_marketing_efficiency"]}[Data],
    ChangedTypes = Table.TransformColumnTypes(gold_mkt_eff,{
        {"campaign_id", type text},
        {"period_start", type date},
        {"period_end", type date},
        {"channel", type text},
        {"spend", Currency.Type},
        {"impressions", Int64.Type},
        {"clicks", Int64.Type},
        {"orders_attributed", Int64.Type},
        {"revenue_attributed", Currency.Type},
        {"gross_profit", Currency.Type},
        {"ctr", Percentage.Type},
        {"conversion_rate", Percentage.Type},
        {"cac", Currency.Type},
        {"roas", type number},
        {"contribution_after_marketing", Currency.Type},
        {"efficiency_tier", type text},
        {"run_id", type text},
        {"computed_at", type datetimezone}
    })
in
    ChangedTypes
