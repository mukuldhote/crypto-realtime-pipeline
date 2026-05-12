import requests
import json
import time
from kafka import KafkaProducer

# ---------------------- CONFIG ----------------------
TOPIC_NAME = "crypto-topic"

coins = ["BTCUSDT", "ETHUSDT", "DOGEUSDT"]

url = "https://api.binance.com/api/v3/ticker/price"

# ---------------------- KAFKA PRODUCER ----------------------
producer = KafkaProducer(
    bootstrap_servers='kafka:9092',
    api_version=(0, 10, 1),

    value_serializer=lambda v: json.dumps(v).encode('utf-8'),

    # ✅ Key serializer for partitioning
    key_serializer=lambda k: k.encode('utf-8')
)

print("Producer started 🚀")

# ---------------------- MAIN LOOP ----------------------
try:

    while True:

        response = requests.get(url, timeout=10)

        # ---------------------- API CHECK ----------------------
        if response.status_code != 200:
            print("API Error:", response.text)
            time.sleep(5)
            continue

        data = response.json()

        # ---------------------- FILTER COINS ----------------------
        filtered_data = [
            coin for coin in data
            if coin["symbol"] in coins
        ]

        # ---------------------- SEND TO KAFKA ----------------------
        for coin in filtered_data:

            symbol = coin["symbol"]

            producer.send(
                TOPIC_NAME,

                # ✅ Same symbol -> same partition
                key=symbol,

                value=coin
            )

            print(
                f"Sent -> "
                f"{symbol}: {coin['price']}"
            )

        producer.flush()

        time.sleep(2)

except KeyboardInterrupt:
    print("Stopping Producer...")

except Exception as e:
    print("Producer Error:", e)

finally:
    producer.close()
    print("Producer closed ✅")