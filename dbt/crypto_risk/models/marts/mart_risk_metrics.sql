select
    product_id,
    event_time,
    price,
    best_ask - best_bid as bid_ask_spread,
    price_percent_chg_24_h
from {{ ref('stg_trades') }}