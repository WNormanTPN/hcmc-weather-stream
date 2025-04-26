import os
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import psycopg2
import requests

from common import VN_TZ, send_to_kafka, DEST_COORDS

# OpenWeatherMap API config
API_URL = os.getenv("OPENWEATHER_API_URL")
API_KEY = os.getenv("OPENWEATHER_API_KEY")


# Database config
DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT")
DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")


def get_max_dates_from_db():
    print("Fetching furthest date from database")
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT district, MAX(timestamp) FROM weather_data
        GROUP BY district;
    """)
    results = cur.fetchall()
    cur.close()
    conn.close()
    print("Fetched furthest date from database")
    return {row[0]: row[1] for row in results}  # {district_name: max_timestamp}


def fetch_historical_weather(dest, dt):
    timestamp = int(dt.timestamp())
    url = (f"{API_URL}/3.0/onecall/timemachine"
           f"?lat={dest['lat']}&lon={dest['lon']}&dt={timestamp}"
           f"&appid={API_KEY}&units=metric")

    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return {
            "district": dest["name"],
            "timestamp": datetime.fromtimestamp(data["dt"], tz=VN_TZ),
            "sunrise": datetime.fromtimestamp(data["sunrise"], tz=VN_TZ),
            "sunset": datetime.fromtimestamp(data["sunset"], tz=VN_TZ),
            "temp": data["temp"],
            "feels_like": data["feels_like"],
            "pressure": data["pressure"],
            "humidity": data["humidity"],
            "dew_point": data["dew_point"],
            "clouds": data["clouds"],
            "visibility": data["visibility"],
            "wind_speed": data["wind_speed"],
            "wind_deg": data["wind_deg"],
            "weather_main": data["weather"][0]["main"],
            "weather_description": data["weather"][0]["description"],
            "weather_id": data["weather"][0]["id"],
        }
    else:
        raise Exception(f"Failed to fetch historical weather for {dest['name']} on {dt}")


def fetch_and_send_historical():
    print("Fetching historical weather")
    max_dates = get_max_dates_from_db()

    for dest in DEST_COORDS:
        district = dest["name"]
        max_date = max_dates.get(district)

        if max_date is None:
            # If no data is found, use the current time
            now = datetime.now(tz=VN_TZ)
            max_date = now.replace(minute=0, second=0, microsecond=0) - timedelta(days=5)
        else:
            max_date = max_date.replace(minute=0, second=0, microsecond=0)

        # Get 40 timestamps, 3 hours apart
        for i in range(1, 41):
            dt = max_date - timedelta(hours=3 * i)
            try:
                print(f"📥 Fetching {district} for {dt.strftime('%Y-%m-%d %H:%M')}")
                data = fetch_historical_weather(dest, dt)
                send_to_kafka(data)
            except Exception as e:
                print(f"❌ Error: {e}")


default_args = {
    "owner": "airflow",
    "start_date": datetime.now(VN_TZ),
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "fetch_historical_weather",
    default_args=default_args,
    schedule_interval="0 3 * * *",  # 3AM HCM (UTC+7)
    catchup=False,
    description="Fetch historical weather every day at 3AM HCM",
)

task = PythonOperator(
    task_id="get_historical_weather",
    python_callable=fetch_and_send_historical,
    dag=dag,
)
