import os
import json
from kafka import KafkaConsumer
from google.cloud import bigquery

consumer = KafkaConsumer(
    "trades",
    bootstrap_servers=os.getenv("KAFKA_BROKER", "kafka:29092"),
    value_deserializer=lambda x: json.loads(x.decode("utf-8"))
)

client = bigquery.Client()
table_id = "skilful-card-498314-a2.crypto_analytics.trades_raw"

print("Listening for Kafka messages...")

for message in consumer:
    trade = message.value
    errors = client.insert_rows_json(table_id, [trade])

    if errors:
        print("BigQuery insert error:", errors)
    else:
        print("Inserted:", trade)