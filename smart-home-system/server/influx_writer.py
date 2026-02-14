from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from config import INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET

client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG
)

write_api = client.write_api(write_options=SYNCHRONOUS)

def write_sensor_data(payload: dict):
    measurement = payload["sensor_type"]

    point = (
        Point(measurement)
        .tag("pi_id", payload["pi_id"])
        .tag("device_name", payload["device_name"])
        .tag("simulated", str(payload["simulated"]))
    )

    value = payload["value"]

    if isinstance(value, (int, float)):
        point = point.field("value_num", float(value))
    elif isinstance(value, bool):
        point = point.field("value_bool", value)
    else:
        point = point.field("value_str", str(value))

    write_api.write(
        bucket=INFLUX_BUCKET,
        org=INFLUX_ORG,
        record=point
    )
