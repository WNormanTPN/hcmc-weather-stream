# HCMc Weather Data Streaming Pipeline

This project implements an end-to-end data engineering pipeline for collecting, streaming, storing, and analyzing weather data for the 22 districts of Ho Chi Minh City. It uses Apache Airflow for orchestration, Kafka for streaming, PySpark for processing, and Parquet/PostgreSQL for storage. A merge job consolidates raw Parquet files into a single output dataset, and you can build forecasting models on top of the cleaned data.

---
![Architectural Diagram](./images/Architectural%20Diagram.drawio.png)


## 🚀 Quick Start with Docker Compose

1. **Create data directories on host**  
   ```bash
   mkdir -p spark-shared-data/output_raw spark-shared-data/output_merged
   chmod 777 spark-shared-data
   ```
   

2. **Define environment variables** \
    Copy .env.example to .env and fill in:
    ```bash
    KAFKA_TOPIC=weather_topic
    KAFKA_HOST=kafka-1:9092,kafka-2:9092,kafka-3:9092
    SCHEMA_REGISTRY_URL=http://schema-registry:8081
    OPENWEATHER_API_URL=http://api.openweathermap.org/data/
    OPENWEATHER_API_KEY=your_api_key
    OPENWEATHER_DEST_COORDS='[
        {"name": "Thành phố Thủ Đức", "lat": 10.8526, "lon": 106.7558},
        {"name": "Quận Bình Tân", "lat": 10.7498, "lon": 106.6057},
        {"name": "Huyện Bình Chánh", "lat": 10.6674, "lon": 106.5732},
        {"name": "Quận Gò Vấp", "lat": 10.8316, "lon": 106.6691},
        {"name": "Quận 12", "lat": 10.8625, "lon": 106.654},
        {"name": "Quận Bình Thạnh", "lat": 10.8047, "lon": 106.7078},
        {"name": "Huyện Hóc Môn", "lat": 10.8916, "lon": 106.5949},
        {"name": "Huyện Củ Chi", "lat": 10.9667, "lon": 106.4667},
        {"name": "Quận Tân Phú", "lat": 10.7916, "lon": 106.6273},
        {"name": "Quận Tân Bình", "lat": 10.798, "lon": 106.6538},
        {"name": "Quận 8", "lat": 10.7404, "lon": 106.6658},
        {"name": "Quận 7", "lat": 10.7366, "lon": 106.7224},
        {"name": "Quận 10", "lat": 10.7732, "lon": 106.6678},
        {"name": "Quận 6", "lat": 10.7469, "lon": 106.6345},
        {"name": "Quận 1", "lat": 10.7851, "lon": 106.7008},
        {"name": "Quận 3", "lat": 10.7835, "lon": 106.6871},
        {"name": "Quận 11", "lat": 10.7642, "lon": 106.6433},
        {"name": "Huyện Nhà Bè", "lat": 10.7012, "lon": 106.739},
        {"name": "Quận 4", "lat": 10.7592, "lon": 106.7049},
        {"name": "Quận Phú Nhuận", "lat": 10.8001, "lon": 106.677},
        {"name": "Quận 5", "lat": 10.7561, "lon": 106.6704},
        {"name": "Huyện Cần Giờ", "lat": 10.411, "lon": 106.9537}
    ]'
    POSTGRES_HOST=postgres15
    POSTGRES_PORT=5432
    POSTGRES_DB=airflow
    POSTGRES_USER=airflow
    POSTGRES_PASSWORD=airflow
   ```
   

3. **Start the services**  
   ```bash
   docker-compose up -d --build
    ```


4. **Access Airflow UI** \
URL: http://localhost:8090 \
Username: `admin` / Password: `admin`


5. **Enable DAG**\
In Airflow UI, turn on weather_data_pipeline. It will run every 3 hours.

---

## 🔧 Configuration

### Airflow DAG (`dags/weather_data_pipeline.py`)
- **Schedule**: `schedule_interval=timedelta(hours=3)`

- **Tasks**:
  - **`fetch_current_weather`** — call Current Weather API, send to Kafka  
  - **`fetch_historical_weather`** — call One Call “timemachine” API for last 5 days  
  - Data is published to Kafka topic `weather_data_hcm`

### PySpark Consumer (`spark/spark_consumer.py`)
- **Streaming job**  
  - Reads from Kafka, decodes Avro payload, flattens JSON, writes raw Parquet to `/shared-data/output_raw`.

- **Merge job**  
  - Reads all raw Parquet, coalesces to 1 file, writes (append or overwrite) to `/shared-data/output_merged`.

### Docker Compose Services
- **`postgres15`**: Airflow metadata database  
- **`airflow-webserver` & `airflow-scheduler`**: Orchestrate DAGs  
- **`zookeeper` + `kafka-1/2/3`**: Kafka cluster for streaming  
- **`schema-registry`**: Confluent Schema Registry for Avro schemas  
- **`spark-master` & `spark-worker-*`**: Spark cluster  
- **`spark-submit`**: Runs `spark_consumer.py` on cluster  

---

## 📈 Data Flow

1. **Airflow**  
   - Triggers every 3 hours → PythonOperators call OpenWeatherMap APIs.  

2. **Kafka Producer**  
   - In DAG publishes JSON records to `weather_data_hcm`.  

3. **Spark Structured Streaming**  
   - Reads from Kafka → writes raw Parquet slices by batch to `/shared-data/output_raw`.  

4. **Merge job**  
   - Consolidates raw slices into a single Parquet dataset in `/shared-data/output_merged`.  

5. **Downstream**  
   - You can train forecasting models (LSTM/ARIMA/Prophet) or visualize via Streamlit/Metabase.  

