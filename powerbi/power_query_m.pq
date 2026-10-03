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
        {"order_key", Int64.Type},
        {"order_id", type text},
        {"order_date_key", Int64.Type},
        {"customer_key", Int64.Type},
        {"product_key", Int64.Type},
        {"channel_key", Int64.Type},
        {"location_key", Int64.Type},
        {"quantity", Int64.Type},
        {"unit_price", Currency.Type},
        {"discount_rate", Percentage.Type},
        {"discount_amount", Currency.Type},
        {"gross_revenue", Currency.Type},
        {"net_sales", Currency.Type},
        {"cogs", Currency.Type},
        {"gross_profit", Currency.Type},
        {"gross_margin_pct", Percentage.Type},
        {"order_status", type text}
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
        {"payment_key", Int64.Type},
        {"payment_id", type text},
        {"order_id", type text},
        {"payment_date_key", Int64.Type},
        {"payment_method_key", Int64.Type},
        {"amount", Currency.Type},
        {"payment_status", type text},
        {"failure_reason", type text}
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
        {"return_key", Int64.Type},
        {"return_id", type text},
        {"order_id", type text},
        {"product_key", Int64.Type},
        {"return_date_key", Int64.Type},
        {"quantity_returned", Int64.Type},
        {"return_value", Currency.Type},
        {"return_reason", type text}
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
        {"product_key", Int64.Type},
        {"snapshot_date_key", Int64.Type},
        {"warehouse", type text},
        {"units_available", Int64.Type},
        {"is_stockout", type logical},
        {"estimated_lost_revenue", Currency.Type}
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
        {"conversions", Int64.Type}
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
