// Table: orders
let
    Source = Csv.Document(File.Contents("C:/Partition/SERIOUS PROJECTS/RevenueOS/data/raw/excel/powerbi_export_revenueos_sample_20261004_141548/csv/orders.csv"),[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"order_id", type text}, {"customer_id", type text}, {"product_id", type text}, {"order_date", type datetime}, {"quantity", Int64.Type}, {"unit_price", type number}, {"discount", type number}, {"channel", type text}, {"location", type text}, {"status", type text}})
in
    #"Changed Type"


// Table: customers
let
    Source = Csv.Document(File.Contents("C:/Partition/SERIOUS PROJECTS/RevenueOS/data/raw/excel/powerbi_export_revenueos_sample_20261004_141548/csv/customers.csv"),[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"customer_id", type text}, {"name", type text}, {"email", type text}, {"city", type text}, {"region", type text}, {"signup_date", type datetime}, {"segment", type text}})
in
    #"Changed Type"


// Table: products
let
    Source = Csv.Document(File.Contents("C:/Partition/SERIOUS PROJECTS/RevenueOS/data/raw/excel/powerbi_export_revenueos_sample_20261004_141548/csv/products.csv"),[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"product_id", type text}, {"product_name", type text}, {"category", type text}, {"subcategory", type text}, {"supplier", type text}, {"cost", Int64.Type}, {"selling_price", Int64.Type}})
in
    #"Changed Type"


// Table: payments
let
    Source = Csv.Document(File.Contents("C:/Partition/SERIOUS PROJECTS/RevenueOS/data/raw/excel/powerbi_export_revenueos_sample_20261004_141548/csv/payments.csv"),[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"payment_id", type text}, {"order_id", type text}, {"payment_date", type datetime}, {"payment_method", type text}, {"amount", type number}, {"payment_status", type text}, {"failure_reason", type text}})
in
    #"Changed Type"


// Table: returns
let
    Source = Csv.Document(File.Contents("C:/Partition/SERIOUS PROJECTS/RevenueOS/data/raw/excel/powerbi_export_revenueos_sample_20261004_141548/csv/returns.csv"),[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"return_id", type text}, {"order_id", type text}, {"product_id", type text}, {"return_date", type datetime}, {"quantity_returned", Int64.Type}, {"return_reason", type text}})
in
    #"Changed Type"


// Table: inventory
let
    Source = Csv.Document(File.Contents("C:/Partition/SERIOUS PROJECTS/RevenueOS/data/raw/excel/powerbi_export_revenueos_sample_20261004_141548/csv/inventory.csv"),[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"product_id", type text}, {"warehouse", type text}, {"snapshot_date", type datetime}, {"units_available", Int64.Type}, {"units_reserved", Int64.Type}, {"units_sold", Int64.Type}})
in
    #"Changed Type"


// Table: marketing
let
    Source = Csv.Document(File.Contents("C:/Partition/SERIOUS PROJECTS/RevenueOS/data/raw/excel/powerbi_export_revenueos_sample_20261004_141548/csv/marketing.csv"),[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"campaign_id", type text}, {"channel", type text}, {"date", type datetime}, {"spend", type number}, {"impressions", Int64.Type}, {"clicks", Int64.Type}, {"orders_attributed", Int64.Type}, {"revenue_attributed", type number}})
in
    #"Changed Type"


// Table: dim_date
let
    Source = Csv.Document(File.Contents("C:/Partition/SERIOUS PROJECTS/RevenueOS/data/raw/excel/powerbi_export_revenueos_sample_20261004_141548/csv/dim_date.csv"),[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"date", type datetime}, {"full_date", type datetime}, {"year", Int64.Type}, {"quarter", type text}, {"quarter_number", Int64.Type}, {"month", Int64.Type}, {"month_name", type text}, {"month_year", type text}, {"month_year_sort", Int64.Type}, {"day_of_month", type datetime}, {"day_of_week", type datetime}, {"day_name", type text}, {"week_number", type number}, {"is_weekend", Int64.Type}})
in
    #"Changed Type"
