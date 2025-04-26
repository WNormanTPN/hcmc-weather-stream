#!/bin/sh

echo "⏳ Waiting for Kafka brokers to be ready..."
sleep 15

echo "🛠️ Creating topic weather_topic..."
kafka-topics --create \
  --topic weather_topic \
  --partitions 3 \
  --replication-factor 3 \
  --if-not-exists \
  --bootstrap-server kafka-1:9092,kafka-2:9092,kafka-3:9092

echo "✅ Kafka topic 'weather_topic' created (if not exists)"
