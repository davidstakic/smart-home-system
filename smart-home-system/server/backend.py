from mqtt_client import start_mqtt
from influx_writer import write_sensor_data

import paho.mqtt.client as mqtt
import threading
import json
import time
import math
from collections import deque

# ========== GLOBAL STATE (shared sa app.py preko importa) ==========

door_light_state = {"on": False}

light_timers = {}
distance_history = {}
door_open_start = {}
door_button_timers = {}

security_state = {
    "mode": "DISARMED",  # DISARMED | ARMING | ARMED | ENTRY_DELAY | ALARM
}

arming_timer = None
entry_timer = None

VALID_PIN = "1234"
entered_pin = ""

people_count = 0

dht_data = {}          # {pi_id: {room: {"humidity": val, "temperature": val}}}
lcd_timers = {}        # {pi_id: Timer}
LCD_SWITCH_DELAY = 5   # seconds between DHT rotations on LCD

COLORS = ["RED", "GREEN", "BLUE", "YELLOW", "PURPLE", "LIGHTBLUE", "WHITE"]

IR_TO_COLOR = {
    "1": "RED",
    "2": "GREEN",
    "3": "BLUE",
    "4": "YELLOW",
    "5": "PURPLE",
    "6": "LIGHTBLUE",
    "0": "WHITE",
    "*": "OFF",
    "#": "OFF",
}

stopwatch_state = {
    "time_sec": 0,
    "running": False,
    "add_sec": 5,
    "blink": False,
}
stopwatch_lock = threading.Lock()

timer_config_pi2 = {
    "initial_seconds": 0,
    "btn_increment": 5,
}

command_client = mqtt.Client()
command_client.connect("localhost", 1883, 60)
command_client.loop_start()

# ========== HELPERI ==========

def send_mqtt_command(pi_id, device, action_payload):
    """Publish a command to a given PI/device."""
    topic = f"smart_home/{pi_id}/cmd/{device}"
    payload = action_payload if isinstance(action_payload, dict) else {"action": action_payload}
    command_client.publish(topic, json.dumps(payload))


def write_influx(pi_id, sensor_type, value, device_name="SmartDoor"):
    payload = {
        "pi_id": pi_id,
        "device_name": device_name,
        "sensor_type": sensor_type,
        "simulated": False,
        "value": value,
    }
    write_sensor_data(payload)


def turn_light_for_10s(pi_id):
    """Turn door_light ON for 10s on given PI."""
    if pi_id in light_timers:
        light_timers[pi_id].cancel()

    print(f"[AUTO] Turning ON door_light on {pi_id} for 10s")
    send_mqtt_command(pi_id, "door_light", "on")
    write_influx(pi_id, "door_light", 1.0)

    timer = threading.Timer(10.0, lambda: send_mqtt_command(pi_id, "door_light", "off"))
    light_timers[pi_id] = timer
    timer.start()


def detect_direction(pi_id):
    """Update people_count based on ultrasonic distance history."""
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

# ========== ALARM LOGIKA ==========

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
    print("ACTIVATE ALARM")
    if security_state["mode"] == "ALARM":
        return
    security_state["mode"] = "ALARM"
    print("[ALARM] ACTIVATED" + (f" ({reason})" if reason else ""))
    write_influx("SERVER", "alarm_state", 1.0, device_name="SecuritySystem")
    send_mqtt_command("PI1", "door_buzzer", "on")


def disarm_system():
    global arming_timer, entry_timer
    if arming_timer:
        arming_timer.cancel()
    if entry_timer:
        entry_timer.cancel()

    security_state["mode"] = "DISARMED"
    print("[SECURITY] DISARMED")
    write_influx("SERVER", "alarm_state", 0.0, device_name="SecuritySystem")
    send_mqtt_command("PI1", "door_buzzer", "off")

# ========== LCD / DHT LOGIKA ==========

def start_lcd_cycle(pi_id):
    """Ciklično prikazivanje DHT1-3 na LCD-u."""
    index = 0

    def cycle():
        nonlocal index
        rooms = list(dht_data.get(pi_id, {}).keys())
        if not rooms:
            return
        
        print("LCD")

        room = rooms[index % len(rooms)]
        index += 1
        sensor = dht_data[pi_id][room]
        if sensor["humidity"] is None or sensor["temperature"] is None:
            timer = threading.Timer(LCD_SWITCH_DELAY, cycle)
            lcd_timers[pi_id] = timer
            timer.start()
            return

        line1 = f"{room.capitalize()[:6]} T:{sensor['temperature']:.1f}C"
        line2 = f"H:{sensor['humidity']:.1f}%"
        line1 = line1[:16]
        line2 = line2[:16]
        message = f"{line1}\n{line2}"
        lcd_payload = {
            "action": "display",
            "message": message
        }
        command_client.publish(
            f"smart_home/{pi_id}/cmd/lcd",
            json.dumps(lcd_payload)
        )

        timer = threading.Timer(LCD_SWITCH_DELAY, cycle)
        lcd_timers[pi_id] = timer
        timer.start()

    cycle()


def handle_ir_mqtt(pi_id, color):
    if color:
        print(f"[IR] Boja {color}")
        command_client.publish(
            f"smart_home/{pi_id}/cmd/rgb_led", json.dumps({"color": color})
        )

# ========== STOPWATCH / 4SD LOGIKA ==========

def format_time_4sd(total_sec):
    mins = total_sec // 60
    secs = total_sec % 60
    return f"{mins:02d}{secs:02d}"


def stopwatch_loop(pi_id, stop_event):
    while not stop_event.is_set():
        with stopwatch_lock:
            if stopwatch_state["running"]:
                if stopwatch_state["time_sec"] > 0:
                    stopwatch_state["time_sec"] -= 1
                    display_value = format_time_4sd(stopwatch_state["time_sec"])
                    command_client.publish(
                        f"smart_home/{pi_id}/cmd/4sd",
                        json.dumps({"value": display_value, "blink": False}),
                    )
                else:
                    stopwatch_state["blink"] = True
                    stopwatch_state["running"] = False
                    command_client.publish(
                        f"smart_home/{pi_id}/cmd/4sd",
                        json.dumps({"value": "0000", "blink": True}),
                    )
        time.sleep(1)

# ========== MQTT CALLBACK – SENZORI I KOMANDE ==========

def on_cmd_message(client, userdata, msg):
    """Centralni MQTT handler: senzori + komande."""
    try:
        topic_parts = msg.topic.split("/")
        if len(topic_parts) < 4:
            return

        pi_id, category, device = topic_parts[1], topic_parts[2], topic_parts[3]
        payload = json.loads(msg.payload.decode())
        # print(f"[MQTT] {msg.topic} -> {payload} : {category}")

        # Door motion
        if category == "sensor" and payload.get("sensor_type") == "door_motion" and payload.get("value") == 1.0:
            # print("DOOR MOTION" + str(pi_id))
            print(str(people_count) + " " + security_state["mode"] + "\n")
            if pi_id == "PI1":
                turn_light_for_10s(pi_id)
            
            detect_direction(pi_id)
            if people_count == 0 and security_state["mode"] != "DISARMED":
                activate_alarm()

        # Door distance
        if category == "sensor" and payload.get("sensor_type") == "door_distance":
            # print("DOOR DISTANCE " + str(pi_id))
            value = payload.get("value")
            distance_history.setdefault(pi_id, deque(maxlen=20)).append((time.time(), value))

        # Door button
        if category == "sensor" and payload.get("sensor_type") == "door_button":
            value = payload.get("value")

            if value == 1.0:
                # zapamti vreme
                door_open_start[pi_id] = time.time()

                # ako postoji stari timer – otkaži ga
                old_timer = door_button_timers.get(pi_id)
                if old_timer:
                    old_timer.cancel()

                # startuj novi timer od 5s
                def check_door_still_open():
                    if pi_id in door_open_start:
                        if security_state["mode"] == "ARMED":
                            print("[SECURITY] Door opened. Starting entry delay...")
                            security_state["mode"] = "ENTRY_DELAY"
                            global entry_timer
                            entry_timer = threading.Timer(10.0, activate_alarm)
                            entry_timer.start()
                        elif security_state["mode"] != "DISARMED":
                            activate_alarm()
                        else:
                            # vrata otvorena >5s čak i kad je DISARMED
                            activate_alarm()

                t = threading.Timer(5.0, check_door_still_open)
                door_button_timers[pi_id] = t
                t.start()

            else:
                # stiglo 0.0 – zatvorena vrata: očisti stanje i otkaži timer
                door_open_start.pop(pi_id, None)
                timer = door_button_timers.get(pi_id)
                if timer:
                    timer.cancel()
                    door_button_timers.pop(pi_id, None)

        # Kitchen button (BTN)
        if category == "sensor" and payload.get("sensor_type") == "kitchen_button":
            print("KITCHEN BUTTON " + str(pi_id))
            with stopwatch_lock:
                if stopwatch_state["blink"]:
                    stopwatch_state["blink"] = False
                    command_client.publish(
                        f"smart_home/{pi_id}/cmd/4sd",
                        json.dumps({"value": "0000", "blink": False}),
                    )
                elif stopwatch_state["running"]:
                    stopwatch_state["time_sec"] += stopwatch_state["add_sec"]

        # Door membrane (PIN)
        if category == "sensor" and payload.get("sensor_type") == "door_membrane":
            global entered_pin
            print("DOOR MEMBRANE " + str(pi_id))
            key = payload.get("value")

            if key is None:
                return

            entered_pin += str(key)

            if len(entered_pin) == 4:
                print(f"[SECURITY] Entered PIN: {entered_pin}")
                if entered_pin == VALID_PIN:
                    print("[SECURITY] Correct PIN")
                    if security_state["mode"] in ["ARMING", "ARMED", "ENTRY_DELAY", "ALARM"]:
                        disarm_system()
                    else:
                        arm_system()
                else:
                    print("[SECURITY] Incorrect PIN")

                entered_pin = ""

        # GSG movement
        if category == "sensor" and payload.get("sensor_type") == "gyroscope":
            # print("DOOR GSG " + str(pi_id))
            ax = payload.get("accel_x", 0)
            ay = payload.get("accel_y", 0)
            az = payload.get("accel_z", 0)
            magnitude = math.sqrt(ax * ax + ay * ay + az * az)
            # print(f"[GSG] Magnitude: {magnitude}")
            if magnitude > 1.5 or magnitude < 0.5:
                if security_state["mode"] == "ARMED":
                    activate_alarm("Icon movement detected")

        # DHT sensors
        if category == "sensor" and payload.get("sensor_type", "").endswith(("_dht_humidity", "_dht_temperature")):
            # print("DHT SENSORS " + str(pi_id))
            sensor_type = payload.get("sensor_type")
            value = payload.get("value")
            room = sensor_type.replace("_dht_humidity", "").replace("_dht_temperature", "")
            dht_data.setdefault(pi_id, {}).setdefault(
                room, {"humidity": None, "temperature": None}
            )
            if sensor_type.endswith("_humidity"):
                dht_data[pi_id][room]["humidity"] = value
            else:
                dht_data[pi_id][room]["temperature"] = value
            if pi_id not in lcd_timers:
                start_lcd_cycle(pi_id)

        # IR receiver
        if category == "sensor" and payload.get("sensor_type") == "bedroom_ir":
            # print("DOOR IR " + str(pi_id))
            button_value = payload.get("value")
            handle_ir_mqtt(pi_id, IR_TO_COLOR.get(button_value))

        # Commands (door_light, door_buzzer) – log u Influx
        if category == "cmd":
            action = payload.get("action")
            if device in ["door_light", "door_buzzer"]:
                val = 1.0 if action == "on" else 0.0
                write_influx(pi_id, device, val)

    except Exception as e:
        print(f"[CMD ERROR] {e}")
        import traceback
        traceback.print_exc()

# ========== INIT ==========

def init_mqtt_and_loops():
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

    stop_event = threading.Event()
    threading.Thread(
        target=stopwatch_loop, args=("PI2", stop_event), daemon=True
    ).start()
