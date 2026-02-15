from flask import Flask, jsonify, request
from flask_cors import CORS
from mqtt_client import start_mqtt
from influx_writer import write_sensor_data
from collections import deque
import threading
import paho.mqtt.client as mqtt
import time
import json
import math

app = Flask(__name__)
CORS(app)

# Globalna stanja
door_light_state = {"on": False}
light_timers = {}
distance_history = {}
door_open_start = {}

security_state = {
    "mode": "DISARMED",   # DISARMED | ARMING | ARMED | ENTRY_DELAY | ALARM
}

arming_timer = None
entry_timer = None
VALID_PIN = "1234"
people_count = 0

dht_data = {}      # {pi_id: {room: {"humidity": val, "temperature": val}}}
lcd_timers = {}    # {pi_id: Timer}
LCD_SWITCH_DELAY = 5  # sekunde između smene senzora

IR_TO_COLOR = {
    "1": "red",
    "2": "green",
    "3": "blue",
    "4": "yellow",
    "5": "purple",
    "6": "lightblue",
    "0": "white",
    "*": "off",
    "#": "off"
}

stopwatch_state = {
    "time_sec": 0,           # trenutno vreme u sekundama
    "running": False,        # da li štoperica odbrojava
    "add_sec": 5,            # N sekundi koje dugme dodaje
    "blink": False,          # da li treperi 00:00
    "stop_blink_event": None # event za zaustavljanje treperenja
}

stopwatch_lock = threading.Lock()

command_client = mqtt.Client()
command_client.connect("localhost", 1883, 60)
command_client.loop_start()

def send_mqtt_command(pi_id, device, action):
    topic = f"smart_home/{pi_id}/cmd/{device}"
    payload = {"action": action}
    command_client.publish(topic, json.dumps(payload))

def write_influx(pi_id, sensor_type, value, device_name="SmartDoor"):
    payload = {
        "pi_id": pi_id,
        "device_name": device_name,
        "sensor_type": sensor_type,
        "simulated": False,
        "value": value
    }
    write_sensor_data(payload)

def turn_light_for_10s(pi_id):
    if pi_id in light_timers:
        light_timers[pi_id].cancel()

    print(f"[AUTO] Turning ON door_light on {pi_id} for 10s")
    send_mqtt_command(pi_id, "door_light", "on")
    write_influx(pi_id, "door_light", 1.0)

    timer = threading.Timer(10.0, lambda: send_mqtt_command(pi_id, "door_light", "off"))
    light_timers[pi_id] = timer
    timer.start()

# Prepoznaje kretnje i azurira broj ljudi u prostoriji
def detect_direction(pi_id):
    global people_count
    history = distance_history.get(pi_id)
    if not history or len(history) < 5:
        return

    values = [v for (_, v) in list(history)[-5:]]
    diff = values[-1] - values[0]
    threshold = 15

    if diff < -threshold:
        people_count += 1
        print(f"[ENTRY] Person entered. Count = {people_count}")
    elif diff > threshold and people_count > 0:
        people_count -= 1
        print(f"[EXIT] Person exited. Count = {people_count}")

# Manipulisanje alarmom
def arm_system():
    global arming_timer
    if security_state["mode"] != "DISARMED":
        return
    print("[SECURITY] ARMING... 10 seconds delay")
    security_state["mode"] = "ARMING"
    arming_timer = threading.Timer(10.0, complete_arming)
    arming_timer.start()

def complete_arming():
    security_state["mode"] = "ARMED"
    print("[SECURITY] SYSTEM ARMED")

def activate_alarm(reason=None):
    if security_state["mode"] == "ALARM":
        return
    security_state["mode"] = "ALARM"
    msg = "[ALARM] ACTIVATED" + (f" ({reason})" if reason else "")
    print(msg)
    write_influx("SERVER", "alarm_state", 1.0, device_name="SecuritySystem")
    send_mqtt_command("PI1", "door_buzzer", "on")

def disarm_system():
    global arming_timer, entry_timer
    if arming_timer: arming_timer.cancel()
    if entry_timer: entry_timer.cancel()

    security_state["mode"] = "DISARMED"
    print("[SECURITY] DISARMED")
    write_influx("SERVER", "alarm_state", 0.0, device_name="SecuritySystem")
    send_mqtt_command("PI1", "door_buzzer", "off")

# Smenjivanje vrednosti sa dht na lcd ekranu
def start_lcd_cycle(pi_id):
    index = 0

    def cycle():
        nonlocal index
        rooms = list(dht_data.get(pi_id, {}).keys())
        if not rooms:
            return

        room = rooms[index % len(rooms)]
        index += 1

        sensor = dht_data[pi_id][room]
        if sensor["humidity"] is None or sensor["temperature"] is None:
            timer = threading.Timer(LCD_SWITCH_DELAY, cycle)
            lcd_timers[pi_id] = timer
            timer.start()
            return

        line1 = f"{room.capitalize()} Temp: {sensor['temperature']:.1f}C"
        line2 = f"Hum: {sensor['humidity']:.1f}%"

        lcd_payload = {"action": "display", "line1": line1, "line2": line2}
        command_client.publish(f"smart_home/{pi_id}/cmd/lcd", json.dumps(lcd_payload))

        timer = threading.Timer(LCD_SWITCH_DELAY, cycle)
        lcd_timers[pi_id] = timer
        timer.start()

    cycle()
    
def handle_ir_mqtt(pi_id, button_value):
    color = IR_TO_COLOR.get(button_value)
    if color:
        print(f"[IR] Dugme {button_value} -> boja {color}")
        command_client.publish(f"smart_home/{pi_id}/cmd/rgb_led", json.dumps({"color": color}))

def format_time_4sd(total_sec):
    mins = total_sec // 60
    secs = total_sec % 60
    return f"{mins:02d}{secs:02d}"

def stopwatch_loop(pi_id, stop_event):
    blink_state = False
    while not stop_event.is_set():
        with stopwatch_lock:
            if stopwatch_state["running"]:
                if stopwatch_state["time_sec"] > 0:
                    stopwatch_state["time_sec"] -= 1
                    display_value = format_time_4sd(stopwatch_state["time_sec"])
                    command_client.publish(f"smart_home/{pi_id}/cmd/4sd", json.dumps({"value": display_value}))
                else:
                    stopwatch_state["blink"] = True
                    stopwatch_state["running"] = False
            elif stopwatch_state["blink"]:
                blink_state = not blink_state
                display_value = "0000" if blink_state else "    "
                command_client.publish(f"smart_home/{pi_id}/cmd/4sd", json.dumps({"value": display_value}))
        time.sleep(1)

# Senzor hendler
# prima vrednosti od senzora upise ih u influx i onda radi logiku, salje aktuatorima sta treba da rade
def on_cmd_message(client, userdata, msg):
    try:
        topic_parts = msg.topic.split("/")
        if len(topic_parts) < 4:
            return

        pi_id, category, device = topic_parts[1], topic_parts[2], topic_parts[3]
        payload = json.loads(msg.payload.decode())
        print(f"[MQTT] {msg.topic} -> {payload}")

        # ---------- Door motion ----------
        if category == "sensor" and payload.get("sensor_type") == "door_motion" and payload.get("value") == 1.0:
            if pi_id == "PI1": turn_light_for_10s(pi_id)
            detect_direction(pi_id)
            if people_count == 0 and security_state["mode"] != "DISARMED":
                activate_alarm()

        # ---------- Door distance ----------
        if category == "sensor" and payload.get("sensor_type") == "door_distance":
            value = payload.get("value")
            distance_history.setdefault(pi_id, deque(maxlen=20)).append((time.time(), value))

        # ---------- Door button ----------
        if category == "sensor" and payload.get("sensor_type") == "door_button":
            value = payload.get("value")
            if value == 1.0:
                door_open_start.setdefault(pi_id, time.time())
                if time.time() - door_open_start[pi_id] >= 5:
                    activate_alarm()
                if security_state["mode"] == "ARMED":
                    print("[SECURITY] Door opened. Waiting for PIN...")
                    security_state["mode"] = "ENTRY_DELAY"
                    global entry_timer
                    entry_timer = threading.Timer(10.0, activate_alarm)
                    entry_timer.start()
            else:
                door_open_start.pop(pi_id, None)
                if security_state["mode"] == "ALARM":
                    disarm_system()

        # ---------- Door membrane (PIN) ----------
        if category == "sensor" and payload.get("sensor_type") == "door_membrane":
            pin = payload.get("value")
            if pin == VALID_PIN:
                if security_state["mode"] in ["ARMING", "ARMED", "ENTRY_DELAY", "ALARM"]:
                    print("[SECURITY] Correct PIN")
                    disarm_system()
                else:
                    arm_system()

        # ---------- GSG movement ----------
        if category == "sensor" and payload.get("sensor_type") == "gsg":
            ax, ay, az = payload.get("accel_x", 0), payload.get("accel_y", 0), payload.get("accel_z", 0)
            magnitude = math.sqrt(ax*ax + ay*ay + az*az)
            print(f"[GSG] Magnitude: {magnitude}")
            if magnitude > 1.5 or magnitude < 0.5:
                if security_state["mode"] == "ARMED":
                    activate_alarm("Icon movement detected")

        # ---------- DHT sensors ----------
        if category == "sensor" and payload.get("sensor_type", "").endswith(("_dht_humidity", "_dht_temperature")):
            sensor_type = payload.get("sensor_type")
            value = payload.get("value")
            room = sensor_type.replace("_dht_humidity", "").replace("_dht_temperature", "")

            dht_data.setdefault(pi_id, {}).setdefault(room, {"humidity": None, "temperature": None})
            if sensor_type.endswith("_humidity"):
                dht_data[pi_id][room]["humidity"] = value
            else:
                dht_data[pi_id][room]["temperature"] = value

            if pi_id not in lcd_timers:
                start_lcd_cycle(pi_id)

        #----------- IR reciever -----------
        if category == "sensor" and payload.get("sensor_type") == "bedroom_ir":
            button_value = payload.get("value")
            handle_ir_mqtt(pi_id, button_value)

        # ---------- Commands ----------
        if category == "cmd":
            action = payload.get("action")
            if device in ["door_light", "door_buzzer"]:
                val = 1.0 if action == "on" else 0.0
                write_influx(pi_id, device, val)

    except Exception as e:
        print(f"[CMD ERROR] {e}")
        import traceback
        traceback.print_exc()

# WEB API
@app.route('/health')
def health(): return jsonify({"status": "running"})

@app.route('/api/actuator/light', methods=['POST'])
def control_light():
    data = request.json
    action = data.get("action")
    if action == "toggle":
        door_light_state["on"] = not door_light_state["on"]
        action = "on" if door_light_state["on"] else "off"
        print(f"[TOGGLE] {action}")
    send_mqtt_command("PI1", "door_light", action)
    return jsonify({"status": "success", "action": action})

@app.route('/api/actuator/buzzer', methods=['POST'])
def control_buzzer():
    data = request.json
    action = data.get("action", "beep")
    times = data.get("times", 3)
    duration = data.get("duration", 0.2)
    mqtt_payload = {"action": action, "times": times, "duration": duration}
    send_mqtt_command("PI1", "door_buzzer", mqtt_payload)
    return jsonify({"status": "success", "action": action})

@app.route("/api/actuator/rgb_led", methods=["POST"])
def control_rgb_led():
    data = request.json
    color = data.get("color", "off")
    command_client.publish("smart_home/PI1/cmd/rgb_led", json.dumps({"color": color}))
    return jsonify({"status": "success", "color": color})

@app.route("/api/stopwatch/set_time", methods=["POST"])
def set_stopwatch_time():
    data = request.json
    mins = data.get("minutes", 0)
    secs = data.get("seconds", 0)
    with stopwatch_lock:
        stopwatch_state["time_sec"] = mins*60 + secs
        stopwatch_state["running"] = True
    return jsonify({"status": "success", "time_sec": stopwatch_state["time_sec"]})

@app.route("/api/stopwatch/set_add_sec", methods=["POST"])
def set_add_seconds():
    data = request.json
    n = data.get("add_sec", 5)
    with stopwatch_lock:
        stopwatch_state["add_sec"] = n
    return jsonify({"status": "success", "add_sec": stopwatch_state["add_sec"]})

@app.route("/api/stopwatch/add_sec", methods=["POST"])
def add_stopwatch_seconds():
    with stopwatch_lock:
        if stopwatch_state["blink"]:
            stopwatch_state["blink"] = False
            command_client.publish("smart_home/PI1/cmd/4sd", json.dumps({"value": "0000"}))
        elif stopwatch_state["running"]:
            stopwatch_state["time_sec"] += stopwatch_state["add_sec"]
        else:
            stopwatch_state["running"] = True

    return jsonify({"status": "success", "time_sec": stopwatch_state["time_sec"]})

def init_mqtt():
    mqtt_thread = threading.Thread(target=start_mqtt, daemon=True)
    mqtt_thread.start()
    print("MQTT sensor listener started")

cmd_listener = mqtt.Client(client_id="flask_cmd_listener")
cmd_listener.on_message = on_cmd_message
cmd_listener.connect("localhost", 1883, 60)
cmd_listener.subscribe("smart_home/+/cmd/#")
cmd_listener.subscribe("smart_home/+/sensor/#")
cmd_listener.loop_start()
print("Command listener started")

if __name__ == "__main__":
    init_mqtt()
    
    stopwatch_stop_event = threading.Event()
    threading.Thread(target=stopwatch_loop, args=("PI1", stopwatch_stop_event), daemon=True).start()
    
    app.run(host="0.0.0.0", port=5001, debug=False)
