from kafka import KafkaConsumer
import json
import psycopg2

# ---------------------- CONFIG ----------------------
TOPIC_NAME = "crypto-topic"
GROUP_ID = "crypto-consumer-group"

BATCH_SIZE = 10

# ---------------------- DB CONNECTION ----------------------
conn = psycopg2.connect(
    host="localhost",
    database="crypto",
    user="admin",
    password="admin"
)

cursor = conn.cursor()

# ---------------------- CREATE TABLE ----------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS crypto_prices (

    id SERIAL PRIMARY KEY,

    symbol TEXT,

    price FLOAT,

    partition_id INT,

    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()

# ---------------------- KAFKA CONSUMER ----------------------
consumer = KafkaConsumer(

    TOPIC_NAME,

    bootstrap_servers='localhost:9092',

    api_version=(0, 10, 1),

    # ✅ Consumer Group
    group_id=GROUP_ID,

    auto_offset_reset='earliest',

    enable_auto_commit=True,

    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

print("Consumer started 🚀")

buffer = []

# ---------------------- MAIN LOOP ----------------------
try:

    for message in consumer:

        data = message.value

        symbol = data["symbol"]

        price = float(data["price"])

        partition = message.partition

        print(
            f"Partition {partition} | "
            f"{symbol}: {price}"
        )

        buffer.append(
            (symbol, price, partition)
        )

        # ---------------------- BATCH INSERT ----------------------
        if len(buffer) >= BATCH_SIZE:

            cursor.executemany(
                """
                INSERT INTO crypto_prices
                (symbol, price, partition_id)
                VALUES (%s, %s, %s)
                """,
                buffer
            )

            conn.commit()

            print("Batch committed ✅")

            buffer.clear()

except KeyboardInterrupt:
    print("Stopping Consumer...")

except Exception as e:
    print("Consumer Error:", e)

    conn.rollback()

finally:

    # ---------------------- FINAL INSERT ----------------------
    if buffer:

        cursor.executemany(
            """
            INSERT INTO crypto_prices
            (symbol, price, partition_id)
            VALUES (%s, %s, %s)
            """,
            buffer
        )

        conn.commit()

    consumer.close()

    cursor.close()

    conn.close()

    print("Consumer closed ✅")