import os
from datetime import timedelta, datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
import requests
import math

from common import send_to_kafka, get_current_time, DEST_COORDS, VN_TZ

API_URL = os.getenv("OPENWEATHER_API_URL")
API_KEY = os.getenv("OPENWEATHER_API_KEY")


def calculate_dew_point(temp, humidity):
    """
    Calculate dew point from temperature and humidity.
    """
    a = 17.27
    b = 237.7
    alpha = (a * temp / (b + temp)) + math.log(humidity / 100.0)
    dew_point = (b * alpha) / (a - alpha)
    return round(dew_point, 2)


def fetch_current_weather(dest):
    url = (f"{API_URL}/2.5/weather?lat={dest['lat']}&lon={dest['lon']}&appid"
           f"={API_KEY}&units=metric")
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        filtered_data = {
            "district": data["name"],
            "timestamp": get_current_time(),
            "sunrise": datetime.fromtimestamp(data["sys"]["sunrise"], tz=VN_TZ),
            "sunset": datetime.fromtimestamp(data["sys"]["sunset"], tz=VN_TZ),
            "temp": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "pressure": data["main"]["pressure"],
            "humidity": data["main"]["humidity"],
            "clouds": data["clouds"]["all"],
            "visibility": data.get("visibility"),
            "wind_speed": data["wind"]["speed"],
            "wind_deg": data["wind"]["deg"],
            "weather_main": data["weather"][0]["main"],
            "weather_description": data["weather"][0]["description"],
            "weather_id": data["weather"][0]["id"],
        }
        filtered_data["dew_point"] = calculate_dew_point(
            filtered_data["temp"], filtered_data["humidity"]
        )
        return filtered_data
    else:
        raise Exception(f"Failed to fetch historical weather for {dest['name']}")


def fetch_and_send_current():
    print("Fetching current weather")
    for dest in DEST_COORDS:
        print(f"Fetching current weather for {dest['name']}")
        data = fetch_current_weather(dest)
        send_to_kafka(data)


default_args = {
    "owner": "airflow",
    "start_date": datetime.now(VN_TZ),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "fetch_current_weather",
    default_args=default_args,
    schedule_interval="0 */3 * * *",  # Every 3 hours (UTC+7)
    catchup=False,
    description="Fetch current weather every 3 hours",
)

task = PythonOperator(
    task_id="get_current_weather",
    python_callable=fetch_and_send_current,
    dag=dag,
)
