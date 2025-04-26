import json
import os
from datetime import datetime

from confluent_kafka import avro
from confluent_kafka.avro import AvroProducer
from pytz import timezone

from weather_schema import weather_schema


# Coordinates of districts in Ho Chi Minh City
DEST_COORDS = json.loads(os.getenv("OPENWEATHER_DEST_COORDS"))
SCHEMA_REGISTRY_URL = os.getenv("SCHEMA_REGISTRY_URL")


# Timezone
VN_TZ = timezone("Asia/Ho_Chi_Minh")


# Kafka config
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC")
KAFKA_HOST = os.getenv("KAFKA_HOST").split(",")


def get_current_time():
    return datetime.now(VN_TZ).isoformat()


def send_to_kafka(data):
    print("Sending data to Kafka:", data)

    # Convert datetime fields to ISO format
    def convert_datetime_fields(d):
        if isinstance(d, dict):
            for key, value in d.items():
                if isinstance(value, datetime):
                    d[key] = value.isoformat()
                elif isinstance(value, dict):
                    convert_datetime_fields(value)
        return d

    data = convert_datetime_fields(data)

    # Create AvroProducer
    producer_config = {
        'bootstrap.servers': ",".join(KAFKA_HOST),
        'schema.registry.url': SCHEMA_REGISTRY_URL
    }

    avro_producer = AvroProducer(
        producer_config,
        default_value_schema=avro.loads(json.dumps(weather_schema))
    )

    # Send data to Kafka
    avro_producer.produce(
        topic=KAFKA_TOPIC,
        value=data
    )
    avro_producer.flush()
    print("Data sent to Kafka successfully.")
