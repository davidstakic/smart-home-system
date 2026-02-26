from influxdb_client import InfluxDBClient
from config import INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET 

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
query_api = client.query_api()

def _query_single_value(flux: str):
    tables = query_api.query(flux)
    for table in tables:
        for rec in table.records:
            return rec.get_value()
    return None

def get_last(measurement: str, pi_id: str | None = None):
    pi_filter = f'  |> filter(fn: (r) => r["pi_id"] == "{pi_id}")\n' if pi_id else ""
    flux = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: -10m)
{pi_filter}  |> filter(fn: (r) => r["_measurement"] == "{measurement}")
  |> last()
'''
    return _query_single_value(flux)

def get_series(measurement: str, pi_id: str | None = None, window: str = "1m"):
    pi_filter = f'  |> filter(fn: (r) => r["pi_id"] == "{pi_id}")\n' if pi_id else ""
    flux = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: -1h)
{pi_filter}  |> filter(fn: (r) => r["_measurement"] == "{measurement}")
  |> aggregateWindow(every: {window}, fn: last, createEmpty: false)
  |> yield(name: "series")
'''
    tables = query_api.query(flux)
    data = []
    for table in tables:
        for rec in table.records:
            data.append({"time": rec.get_time().isoformat(), "value": rec.get_value()})
    return data

def get_alarm_events(limit: int = 50):
    flux = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: -24h)
  |> filter(fn: (r) => r["_measurement"] =~ /alarm_/)
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: {limit})
'''
    tables = query_api.query(flux)
    events = []
    for table in tables:
        for rec in table.records:
            events.append({
                "time": rec.get_time().isoformat(),
                "measurement": rec.get_measurement(),
                "pi_id": rec.values.get("pi_id"),
                "field": rec.get_field(),
                "value": rec.get_value()
            })
    return events

def get_people_count_series(window: str = "1m"):
    return get_series("people_count", pi_id=None, window=window)
