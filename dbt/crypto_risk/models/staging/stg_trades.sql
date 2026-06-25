-- models/staging/stg_trades.sql

select
    event_time,
    product_id,
    price,
    volume_24_h,
    best_bid,
    best_ask,
    best_ask - best_bid as bid_ask_spread,
    price_percent_chg_24_h,
    source
from `skilful-card-498314-a2.crypto_analytics.trades_raw`
where
    price > 0
    and product_id is not null