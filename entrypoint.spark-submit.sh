#!/bin/bash

# Run spark_consumer.py
/opt/bitnami/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  --deploy-mode client \
  --verbose \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.5,org.apache.spark:spark-avro_2.12:3.5.5 \
  /opt/spark-apps/spark_consumer.py &

