import json
import paho.mqtt.client as mqtt
from influx_writer import write_sensor_data
from config import MQTT_BROKER, MQTT_PORT, MQTT_TOPIC

def on_connect(client, userdata, flags, rc):
    print(f"[MQTT SENSOR] Connected (code {rc})")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    try:
        if "/cmd/" in msg.topic:
            return

        payload = json.loads(msg.payload.decode())

        if "sensor_type" not in payload:
            return

        write_sensor_data(payload)
        # print(f"[MQTT SENSOR] {payload['sensor_type']} = {payload.get('value')}")

    except Exception as e:
        print(f"[MQTT SENSOR] Error: {e}")

def start_mqtt():
    client = mqtt.Client(client_id="flask_sensor_listener")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()