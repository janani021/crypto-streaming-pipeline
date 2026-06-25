{{ config(
    materialized='table'
) }}

with base as (
    select
        timestamp_trunc(event_time, minute) as minute_bucket,
        product_id,
        price,
        volume_24_h,
        best_bid,
        best_ask,
        bid_ask_spread,
        price_percent_chg_24_h
    from {{ ref('stg_trades') }}
)

select
    minute_bucket,
    product_id,
    count(*) as trade_count,
    avg(price) as avg_price,
    min(price) as min_price,
    max(price) as max_price,
    avg(volume_24_h) as avg_volume_24_h,
    avg(best_bid) as avg_best_bid,
    avg(best_ask) as avg_best_ask,
    avg(bid_ask_spread) as avg_bid_ask_spread,
    avg(price_percent_chg_24_h) as avg_price_percent_chg_24_h
from base
group by 1, 2