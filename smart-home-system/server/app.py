from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import json

from influx_client import get_last, get_alarm_events, get_people_count_series

from backend import (
    init_mqtt_and_loops,
    send_mqtt_command,
    stopwatch_lock,
    stopwatch_state,
    command_client,
    door_light_state,
    VALID_PIN,
    security_state,
    arm_system,
    write_influx,
    disarm_system,
    timer_config_pi2,
    COLORS,
    handle_ir_mqtt,
    activate_alarm,
    people_count
)

app = Flask(__name__)
CORS(app)
init_mqtt_and_loops()

@app.route("/health")
def health():
    return jsonify({"status": "running"})

# ---------- UI Routes ----------

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/PI1")
def pi1_page():
    return render_template("PI1.html")

@app.get("/PI2")
def pi2_page():
    return render_template("PI2.html")

@app.get("/PI3")
def pi3_page():
    return render_template("PI3.html")

@app.get("/alarm")
def alarm_page():
    return render_template("alarm.html")

@app.get("/camera")
def camera_page():
    return render_template("camera.html")

# ---------- API: Alarm & global ----------

@app.get("/api/alarm/state")
def api_alarm_state():
    return jsonify({
        "alarm_state": get_last("alarm_state", None),
        "people_count": get_last("people_count", None),
    })

@app.get("/api/alarm/events")
def api_alarm_events():
    events = get_alarm_events(limit=50)
    return jsonify(events)

@app.get("/api/people/series")
def api_people_series():
    window = request.args.get("window", "1m")
    series = get_people_count_series(window=window)
    return jsonify(series)

# ---------- PI3 RGB & LCD ----------

@app.route("/api/actuator/rgb_led", methods=["POST"])
def control_rgb_led():
    data = request.json or {}
    color = data.get("color", "OFF")
    command_client.publish(
        "smart_home/PI3/cmd/rgb_led", json.dumps({"color": color})
    )
    return jsonify({"status": "success", "color": color})

@app.route("/api/PI3/rgb", methods=["POST"])
def pi3_set_rgb():
    data = request.json or {}
    color = str(data.get("color", "OFF")).upper().strip()

    if color not in COLORS:
        return jsonify({
            "success": False,
            "message": f"Invalid color '{color}'. Allowed: {sorted(COLORS)}"
        }), 400

    handle_ir_mqtt('PI3', color)

    return jsonify({"success": True, "color": color})

@app.route("/api/PI3/lcd", methods=["POST"])
def pi3_set_lcd():
    data = request.json or {}
    text = str(data.get("text", "")).strip()

    if not text:
        return jsonify({
            "success": False,
            "message": "Text must not be empty."
        }), 400

    max_len = 32
    if len(text) > max_len:
        text = text[:max_len]

    command_client.publish(
        "smart_home/PI3/cmd/lcd",
        json.dumps({"text": text})
    )

    return jsonify({"success": True, "text": text})

# ---------- Alarm arm/deactivate ----------

@app.route("/api/alarm/arm", methods=["POST"])
def api_alarm_arm():
    global arming_timer, entry_timer
    data = request.json or {}
    pin = str(data.get("pin", "")).strip()
    armed = bool(data.get("armed", False))

    if pin != VALID_PIN:
        return jsonify({"success": False, "message": "Invalid PIN"}), 401

    if armed:
        if security_state["mode"] == "ARMED":
            return jsonify({"success": True, "message": "Already armed"})
        arm_system()
        write_influx("SERVER", "alarm_event", "armed_web", device_name="SecuritySystem")
        return jsonify({"success": True, "message": "System arming"})
    else:
        if security_state["mode"] != "DISARMED":
            disarm_system()
            write_influx("SERVER", "alarm_event", "disarmed_web", device_name="SecuritySystem")
        return jsonify({"success": True, "message": "System disarmed"})

@app.route("/api/alarm/deactivate", methods=["POST"])
def api_alarm_deactivate():
    data = request.json or {}
    pin = str(data.get("pin", "")).strip()

    if security_state["mode"] == "ALARM":
        print("[SECURITY] Alarm deactivated via web")
        security_state["mode"] = "ARMED"
        write_influx("SERVER", "alarm_state", 0.0, device_name="SecuritySystem")
        send_mqtt_command("PI1", "door_buzzer", "off")

    if security_state["mode"] == "ARMED" and pin != VALID_PIN:
        activate_alarm()

    return jsonify({"success": True, "message": "System disarmed"})


# ---------- PI2 timer-config ----------

@app.route("/api/PI2/timer-config", methods=["POST"])
def api_pi2_timer_config():
    data = request.json or {}
    try:
        initial_seconds = int(data.get("initial_seconds", 0))
        btn_increment = int(data.get("btn_increment", 5))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Invalid numeric values"}), 400

    if initial_seconds < 0 or btn_increment <= 0:
        return jsonify({"success": False, "message": "Values must be >=0 and >0"}), 400

    timer_config_pi2["initial_seconds"] = initial_seconds
    timer_config_pi2["btn_increment"] = btn_increment

    print(f"[TIMER CONFIG] PI2 initial={initial_seconds}s, btn_increment={btn_increment}s")

    with stopwatch_lock:
        stopwatch_state["time_sec"] = initial_seconds
        stopwatch_state["running"] = True

    write_influx("PI2", "timer_initial_seconds", float(initial_seconds), device_name="KitchenTimer")
    write_influx("PI2", "timer_btn_increment", float(btn_increment), device_name="KitchenTimer")

    return jsonify({"success": True, "time_sec": stopwatch_state["time_sec"]})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
