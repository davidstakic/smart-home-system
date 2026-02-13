from flask import Flask, jsonify, request
from flask_cors import CORS
from mqtt_client import start_mqtt
from influx_writer import write_sensor_data
import paho.mqtt.client as mqtt
import threading
import json

app = Flask(__name__)
CORS(app)

door_light_state = {"on": False}

command_client = mqtt.Client()
command_client.connect("localhost", 1883, 60)
command_client.loop_start()

def on_cmd_message(client, userdata, msg):
    """Callback - prima komande i piše u InfluxDB"""
    global door_light_state

    try:
        if "/cmd/" not in msg.topic:
            return

        payload = json.loads(msg.payload.decode())
        action = payload.get("action")

        print(f"[CMD LISTENER] {msg.topic} -> {action}")

        if msg.topic.endswith("door_light"):
            if action == "on":
                value = 1.0
                door_light_state["on"] = True
            elif action == "off":
                value = 0.0
                door_light_state["on"] = False
            else:
                return

            influx_payload = {
                "pi_id": "PI1",
                "device_name": "SmartDoor",
                "sensor_type": "door_light",
                "simulated": False,
                "value": value
            }

            write_sensor_data(influx_payload)
            print(f"[InfluxDB] door_light = {value}")

        elif msg.topic.endswith("door_buzzer"):
            influx_payload = {
                "pi_id": "PI1",
                "device_name": "SmartDoor",
                "sensor_type": "door_buzzer",
                "simulated": False,
                "value": 1.0
            }

            write_sensor_data(influx_payload)
            print(f"[InfluxDB] door_buzzer = 1.0")

    except Exception as e:
        print(f"[CMD ERROR] {e}")
        import traceback
        traceback.print_exc()

cmd_listener = mqtt.Client(client_id="flask_cmd_listener")
cmd_listener.on_message = on_cmd_message
cmd_listener.connect("localhost", 1883, 60)
cmd_listener.subscribe("smart_home/+/cmd/#")
cmd_listener.loop_start()
print("Command listener started")

@app.route('/health')
def health():
    return jsonify({"status": "running"})

@app.route('/api/actuator/light', methods=['POST'])
def control_light():
    global door_light_state

    data = request.json
    action = data.get('action')

    if action == "toggle":
        door_light_state["on"] = not door_light_state["on"]
        action = "on" if door_light_state["on"] else "off"
        print(f"[TOGGLE] {action}")

    mqtt_payload = {"action": action}
    command_client.publish("smart_home/pi1/cmd/door_light", json.dumps(mqtt_payload))

    return jsonify({"status": "success", "action": action})

@app.route('/api/actuator/buzzer', methods=['POST'])
def control_buzzer():
    data = request.json
    action = data.get('action', 'beep')
    times = data.get('times', 3)
    duration = data.get('duration', 0.2)

    mqtt_payload = {"action": action, "times": times, "duration": duration}
    command_client.publish("smart_home/pi1/cmd/door_buzzer", json.dumps(mqtt_payload))

    return jsonify({"status": "success", "action": action})

def init_mqtt():
    mqtt_thread = threading.Thread(target=start_mqtt, daemon=True)
    mqtt_thread.start()
    print("MQTT sensor listener started")

if __name__ == '__main__':
    init_mqtt()
    app.run(host='0.0.0.0', port=5001, debug=False)