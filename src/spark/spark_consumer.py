import os
import shutil

import requests
import time
import threading
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_timestamp, substring, length, expr, to_date, unix_timestamp
from pyspark.sql.avro.functions import from_avro


# === ENVIRONMENT ===
KAFKA_HOST = os.getenv("KAFKA_HOST")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC")
SCHEMA_REGISTRY_URL = os.getenv("SCHEMA_REGISTRY_URL")
CHECKPOINT_PATH = "/shared-data/checkpoints"
OUTPUT_PATH = "/shared-data/output_raw"
INPUT_PATH = os.getenv("INPUT_PATH", "/shared-data/output_raw")
OUTPUT_MERGED_PATH = os.getenv("OUTPUT_PATH", "/shared-data/output_merged")


# === SPARK SESSION ===
spark = SparkSession.builder \
    .appName("Kafka Avro to Parquet and Merge") \
    .config("spark.sql.streaming.schemaInference", "true") \
    .config("spark.sql.catalogImplementation", "in-memory") \
    .config("spark.sql.shuffle.partitions", "10") \
    .config("spark.kryoserializer.buffer.max", "2000m") \
    .getOrCreate()
spark.sparkContext.setLogLevel("WARN")


# === FETCH LATEST SCHEMA ===
def fetch_latest_avro_schema(subject: str, registry_url: str) -> str:
    """Get the latest Avro schema from the Confluent Schema Registry."""
    url = f"{registry_url}/subjects/{subject}/versions/latest"
    while True:
        try:
            resp = requests.get(url)
            resp.raise_for_status()
            print(f"Schema found: {resp.json()['schema']}", flush=True)
            return resp.json()['schema']
        except requests.exceptions.RequestException as e:
            print(f"Schema not found, retrying in 10 seconds... Error: {e}", flush=True)
            time.sleep(10)


subject = f"{KAFKA_TOPIC}-value"
avro_schema_str = fetch_latest_avro_schema(subject, SCHEMA_REGISTRY_URL)


# === STREAMING JOB ===
def run_streaming_job():
    """Run the Kafka streaming job to read, decode, and write Parquet."""
    try:
        print("Starting streaming job...", flush=True)
        df_raw = spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", KAFKA_HOST) \
            .option("startingOffsets", "earliest") \
            .option("subscribe", KAFKA_TOPIC) \
            .option("failOnDataLoss", "false") \
            .load()

        df_avro_data = df_raw.withColumn("avro_value", expr("substring(value, 6, length(value) - 5)"))
        df_decoded = df_avro_data.select(from_avro(col("avro_value"), avro_schema_str).alias("data"))

        df_flattened = df_decoded.select("data.*") \
            .withColumn("timestamp", to_timestamp("timestamp"))

        query = df_flattened.writeStream \
            .outputMode("append") \
            .format("parquet") \
            .option("checkpointLocation", CHECKPOINT_PATH) \
            .option("path", OUTPUT_PATH) \
            .start()

        query.awaitTermination()
    except Exception as e:
        print(f"Error in streaming job: {e}", flush=True)
        raise


# === MERGE JOB ===
def run_merge_job():
    """Run the merge job to combine Parquet files and delete corresponding raw data."""
    try:
        print(f"Starting merge job at {datetime.now()}", flush=True)
        # Check if the input path has any Parquet files
        try:
            df = spark.read.parquet(INPUT_PATH)
            if df.count() == 0:
                print(f"No data found in {INPUT_PATH}, skipping merge", flush=True)
                return

            # Add date column for partitioning
            df = df.coalesce(1)
            df = df.withColumn(
                "date",
                to_date(unix_timestamp(col("timestamp"), "EEE MMM dd HH:mm:ss z yyyy").cast("timestamp"))
            )

            # Get distinct dates to merge
            dates = [row["date"] for row in df.select("date").distinct().collect()]
            print(f"Dates to merge: {dates}", flush=True)

            # Write to merged path with partitioning by date
            df.write \
                .partitionBy("date") \
                .mode("overwrite") \
                .option("partitionOverwriteMode", "dynamic") \
                .parquet(OUTPUT_MERGED_PATH)
            print(f"Merged parquet written to {OUTPUT_MERGED_PATH} at {datetime.now()}", flush=True)

            # Delete raw data
            try:
                print(f"Deleting raw data in {INPUT_PATH}...", flush=True)
                shutil.rmtree(INPUT_PATH, ignore_errors=True)
                os.makedirs(INPUT_PATH, exist_ok=True)
                print(f"Raw data in {INPUT_PATH} deleted and directory recreated at {datetime.now()}", flush=True)
            except Exception as e:
                print(f"Error deleting raw data in {INPUT_PATH}: {e}", flush=True)

        except Exception as e:
            if "Path does not exist" in str(e) or "Unable to infer schema" in str(e):
                print(f"No Parquet files found in {INPUT_PATH}, skipping merge: {e}", flush=True)
            else:
                print(f"Error merging parquet: {e}", flush=True)
    except Exception as e:
        print(f"Unexpected error in merge job: {e}", flush=True)


# === SCHEDULING LOGIC ===
def schedule_merge_job():
    """Schedule the merge job to run every day at 4 AM."""
    while True:
        try:
            now = datetime.now()
            if now.hour == 4 and now.minute == 0 and now.second < 30:
                run_merge_job()
                time.sleep(24 * 60 * 60)
            else:
                time.sleep(30)
        except Exception as e:
            print(f"Error in schedule_merge_job: {e}", flush=True)
            time.sleep(60)


# === MAIN EXECUTION ===
if __name__ == "__main__":
    # Run initial merge job in a separate thread
    initial_merge_thread = threading.Thread(target=run_merge_job, daemon=True)
    initial_merge_thread.start()

    # Run scheduled merge job in a separate thread
    schedule_thread = threading.Thread(target=schedule_merge_job, daemon=True)
    schedule_thread.start()

    # Run streaming job in main thread
    run_streaming_job()