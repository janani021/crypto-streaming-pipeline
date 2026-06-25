import json
import os
import time
from pathlib import Path

import websocket
from dotenv import load_dotenv
from kafka import KafkaProducer

load_dotenv()

COINBASE_WS_URL = "wss://advanced-trade-ws.coinbase.com"
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "trades")
PRODUCTS = ["BTC-USD", "ETH-USD", "SOL-USD"]

STATE_FILE = Path("state/last_checkpoint.json")
last_checkpoint = None

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    acks="all",
    retries=5,
    linger_ms=10,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    key_serializer=lambda v: v.encode("utf-8"),
)


def load_checkpoint():
    global last_checkpoint
    if STATE_FILE.exists():
        try:
            with STATE_FILE.open("r") as f:
                data = json.load(f)
                last_checkpoint = data.get("event_time")
                print(f"Loaded checkpoint: {last_checkpoint}")
        except Exception as e:
            print(f"Could not load checkpoint: {e}")


def save_checkpoint(event_time):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with STATE_FILE.open("w") as f:
        json.dump({"event_time": event_time}, f)


def on_open(ws):
    print("Connected!")
    ws.send(
        json.dumps(
            {
                "type": "subscribe",
                "channel": "ticker",
                "product_ids": PRODUCTS,
            }
        )
    )


def on_message(ws, message):
    data = json.loads(message)

    if data.get("channel") != "ticker":
        return

    timestamp = data.get("timestamp")

    for event in data.get("events", []):
        for ticker in event.get("tickers", []):
            trade = {
                "event_time": timestamp,
                "product_id": ticker.get("product_id"),
                "price": float(ticker.get("price")) if ticker.get("price") else None,
                "volume_24_h": float(ticker.get("volume_24_h")) if ticker.get("volume_24_h") else None,
                "best_bid": float(ticker.get("best_bid")) if ticker.get("best_bid") else None,
                "best_ask": float(ticker.get("best_ask")) if ticker.get("best_ask") else None,
                "price_percent_chg_24_h": float(ticker.get("price_percent_chg_24_h")) if ticker.get("price_percent_chg_24_h") else None,
                "source": "coinbase_ticker",
            }

            future = producer.send(
                KAFKA_TOPIC,
                key=trade["product_id"],
                value=trade,
            )

            future.get(timeout=10)
            save_checkpoint(trade["event_time"])
            print("Sent to Kafka:", trade)


def on_error(ws, error):
    print("ERROR:", error)


def on_close(ws, close_status_code, close_msg):
    print("Closed:", close_status_code, close_msg)


if __name__ == "__main__":
    load_checkpoint()

    if last_checkpoint:
        print(f"Resuming from {last_checkpoint}")

    while True:
        try:
            ws = websocket.WebSocketApp(
                COINBASE_WS_URL,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
            )
            ws.run_forever(ping_interval=20, ping_timeout=10)
        except Exception as e:
            print("Reconnect after error:", e)
            time.sleep(5)
        finally:
            try:
                producer.flush()
            except Exception:
                pass