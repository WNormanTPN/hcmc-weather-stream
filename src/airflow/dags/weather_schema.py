

# Define the schema for the weather data
weather_schema = {
    "type": "record",
    "name": "Weather",
    "fields": [
        {"name": "district", "type": "string"},
        {"name": "timestamp", "type": "string"},
        {"name": "sunrise", "type": "string"},
        {"name": "sunset", "type": "string"},
        {"name": "temp", "type": "float"},
        {"name": "feels_like", "type": "float"},
        {"name": "pressure", "type": "float"},
        {"name": "humidity", "type": "int"},
        {"name": "clouds", "type": "int"},
        {"name": "visibility", "type": "int"},
        {"name": "wind_speed", "type": "float"},
        {"name": "wind_deg", "type": "int"},
        {"name": "weather_main", "type": "string"},
        {"name": "weather_description", "type": "string"},
        {"name": "weather_id", "type": "int"},
        {"name": "dew_point", "type": "float"},
    ]
}
