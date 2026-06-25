{{ config(materialized='table') }}

select
    minute_bucket,
    product_id,
    trade_count,
    avg_price,
    avg_bid_ask_spread,
    avg_price_percent_chg_24_h,

    case
    when avg_price_percent_chg_24_h <= -2 then 'HIGH'
    when avg_bid_ask_spread >= 0.05 then 'HIGH'

    when avg_price_percent_chg_24_h <= -0.5 then 'MEDIUM'
    when avg_bid_ask_spread >= 0.02 then 'MEDIUM'

    else 'LOW'
end as risk_level

from {{ ref('fct_trade_metrics') }}