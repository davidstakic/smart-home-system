from datetime import datetime
from pathlib import Path
import threading
import paho.mqtt.client as mqtt
import json

from components.sensors.button import Button, run_button_loop
from components.sensors.motion_sensor import MotionSensor, run_motion_loop
from components.sensors.ultrasonic_sensor import UltrasonicSensor, run_ultrasonic_loop
from components.sensors.dht import DHTSensor, run_dht_loop
from components.sensors.gyroscope import Gyroscope, run_gyro_loop
from components.actuators.display_4sd import Display4SD
from config.config import Config
from mqtt_batch_sender import MQTTBatchSender

import time

try:
    import RPi.GPIO as GPIO  # type: ignore
    RUNNING_ON_PI = True
except ImportError:
    from mock_rpi import GPIO
    RUNNING_ON_PI = False


class PI2_Controller:
    def __init__(self, config_file=None):
        if config_file is None:
            base_dir = Path(__file__).resolve().parent
            config_file = base_dir / "config" / "pi2_config.ini"

        self.config = Config(str(config_file))
        print("========== PI2 ==========")

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        ds2_pin = self.config.get_pin("DS2_PIN")
        dpir2_pin = self.config.get_pin("DPIR2_PIN")
        dus2_trigger = self.config.get_pin("DUS2_TRIGGER")
        dus2_echo = self.config.get_pin("DUS2_ECHO")
        btn_pin = self.config.get_pin("BTN_PIN")
        dht3_pin = self.config.get_pin("DHT3_PIN")
        segment_pins = [
            self.config.get_pin("SEG_A"),
            self.config.get_pin("SEG_B"),
            self.config.get_pin("SEG_C"),
            self.config.get_pin("SEG_D"),
            self.config.get_pin("SEG_E"),
            self.config.get_pin("SEG_F"),
            self.config.get_pin("SEG_G"),
        ]

        digit_pins = [
            self.config.get_pin("DIGIT_1"),
            self.config.get_pin("DIGIT_2"),
            self.config.get_pin("DIGIT_3"),
            self.config.get_pin("DIGIT_4"),
        ]

        self.door_sensor = Button(ds2_pin, self.config.is_simulated("DS2"))
        self.motion_sensor = MotionSensor(dpir2_pin, self.config.is_simulated("DPIR2"))
        self.ultrasonic = UltrasonicSensor(dus2_trigger, dus2_echo, self.config.is_simulated("DUS2"))
        self.button = Button(btn_pin, self.config.is_simulated("BTN"))
        self.dht_sensor = DHTSensor(dht3_pin, self.config.is_simulated("DHT3"))
        self.gyroscope = Gyroscope(self.config.is_simulated("GSG"))

        self.display = Display4SD(
            segment_pins,
            digit_pins,
            simulate=self.config.is_simulated("4SD"),
            brightness=self.config.get_value("DISPLAY_CONFIG", "DISPLAY_BRIGHTNESS", 7, int),
            update_interval=self.config.get_value("DISPLAY_CONFIG", "DISPLAY_UPDATE_INTERVAL", 0.002, float)
        )

        self.device_info = self.config.get_device_info()
        mqtt_cfg = self.config.get_mqtt_config()
        self.mqtt_sender = MQTTBatchSender(
            mqtt_cfg["broker"],
            mqtt_cfg["port"],
            mqtt_cfg["base_topic"],
            mqtt_cfg["batch_size"],
            mqtt_cfg["send_interval"]
        )

        self.cmd_client = mqtt.Client(client_id=f"{self.device_info['pi_id']}_cmd")
        self.cmd_client.on_message = self._on_cmd_message
        self.cmd_client.connect(mqtt_cfg["broker"], mqtt_cfg["port"], 60)
        cmd_topic = f"{mqtt_cfg['base_topic']}/{self.device_info['pi_id']}/cmd/#"
        self.cmd_client.subscribe(cmd_topic)
        self.cmd_client.loop_start()

        self.stop_event = threading.Event()
        self.threads = []

    def _send_measurement(self, sensor_type, value):
        payload = {
            "pi_id": self.device_info["pi_id"],
            "device_name": self.device_info["device_name"],
            "sensor_type": sensor_type,
            "simulated": self.config.is_simulated(sensor_type),
            "value": value
        }
        self.mqtt_sender.enqueue(payload)

    def _door_callback(self, value):
        self._send_measurement("door_button", value)

    def _motion_callback(self, value):
        self._send_measurement("door_motion", value)

    def _ultrasonic_callback(self, value):
        self._send_measurement("door_distance", value)

    def _btn_callback(self, value):
        self._send_measurement("kitchen_button", value)

    def _dht_callback(self, humidity, temperature, code):
        self._send_measurement("kitchen_dht_humidity", humidity)
        self._send_measurement("kitchen_dht_temperature", temperature)

    def _gyro_callback(self, payload):
        self._send_measurement("gyroscope", payload)
    # def _gyro_callback(self, payload):
    #     self._send_measurement("gyro_accel_x", payload["accel_x"])
    #     self._send_measurement("gyro_accel_y", payload["accel_y"])
    #     self._send_measurement("gyro_accel_z", payload["accel_z"])
    #     self._send_measurement("gyro_gyro_x", payload["gyro_x"])
    #     self._send_measurement("gyro_gyro_y", payload["gyro_y"])
    #     self._send_measurement("gyro_gyro_z", payload["gyro_z"])


    def start_sensors(self):
        return
        # cfg = self.config
        # self.threads.append(threading.Thread(
        #     target=run_button_loop,
        #     args=(self.door_sensor, cfg.get_value("SENSOR_CONFIG", "BTN_DELAY", 0.5, float), self._door_callback, self.stop_event),
        #     daemon=True
        # ))
        # self.threads.append(threading.Thread(
        #     target=run_motion_loop,
        #     args=(self.motion_sensor, cfg.get_value("SENSOR_CONFIG", "PIR_TIMEOUT", 30, float), self._motion_callback, self.stop_event),
        #     daemon=True
        # ))
        # self.threads.append(threading.Thread(
        #     target=run_ultrasonic_loop,
        #     args=(self.ultrasonic, cfg.get_value("SENSOR_CONFIG", "ULTRASONIC_DELAY", 0.5, float), self._ultrasonic_callback, self.stop_event),
        #     daemon=True
        # ))
        # self.threads.append(threading.Thread(
        #     target=run_button_loop,
        #     args=(self.button, cfg.get_value("SENSOR_CONFIG", "BTN_DELAY", 0.5, float), self._btn_callback, self.stop_event),
        #     daemon=True
        # ))
        # self.threads.append(threading.Thread(
        #     target=run_dht_loop,
        #     args=(self.dht_sensor, cfg.get_value("SENSOR_CONFIG", "DHT_DELAY", 2.0, float), self._dht_callback, self.stop_event),
        #     daemon=True
        # ))
        # self.threads.append(threading.Thread(
        #     target=run_gyro_loop,
        #     args=(self.gyroscope, cfg.get_value("SENSOR_CONFIG", "GSG_DELAY", 0.1, float), self._gyro_callback, self.stop_event),
        #     daemon=True
        # ))

        # for t in self.threads:
        #     t.start()

    def actuator_menu(self):
        try:
            while True:
                print("\n=== PI2 MENI ===")
                print("--- Aktuatori ---")
                print("[1] Prikaz na 4SD (ručni unos)")
                print("[2] Isključi 4SD")
                print("--- Test senzora / demo ---")
                print("[3] TEST DPIR2 -> door_motion")
                print("[4] TEST DUS2 ulazak (ENTRY)")
                print("[5] TEST DUS2 izlazak (EXIT)")
                print("[6] TEST DS2 otvoreno 6s (ALARM)")
                print("[7] TEST GSG movement (ALARM)")
                print("[8] TEST GSG normal")
                print("[9] TEST Kitchen BTN (dodavanje N)")
                print("[0] Izlaz")
                choice = input("Odaberi opciju: ").strip()

                if choice == "1":
                    value = input("Unesi 4-cifreni broj: ").strip().rjust(4)
                    self.display.update(value)
                    self._send_measurement("display_4sd", value)
                elif choice == "2":
                    self.display.turn_off()
                    self._send_measurement("display_4sd", "    ")
                elif choice == "3":
                    self.test_dpir2_pulse()
                elif choice == "4":
                    self.test_dus2_entry_sequence()
                elif choice == "5":
                    self.test_dus2_exit_sequence()
                elif choice == "6":
                    self.test_ds2_open_alarm()
                elif choice == "7":
                    self.test_gsg_movement_alarm()
                elif choice == "8":
                    self.test_gsg_normal()
                elif choice == "9":
                    self.test_kitchen_btn_press()
                elif choice == "0":
                    print("Izlaz...")
                    break
                else:
                    print("Nepoznata opcija.")
        except KeyboardInterrupt:
            print("\nPrekid (Ctrl+C)")

    def cleanup(self):
        print("\nČišćenje resursa...")
        self.stop_event.set()
        for t in self.threads:
            t.join(timeout=1.0)
        self.display.cleanup()
        GPIO.cleanup()
        print("Kraj programa.")

    def run(self):
        self.start_sensors()
        self.actuator_menu()
        self.cleanup()

    def test_dpir2_pulse(self):
        print("[TEST] DPIR2 door_motion = 1.0")
        self._send_measurement("door_motion", 1.0)

    def test_dus2_entry_sequence(self):
        seq = [200, 150, 100, 80]
        print("[TEST] DUS2 ENTRY distances:", seq)
        for v in seq:
            self._send_measurement("door_distance", float(v))
            time.sleep(0.3)

    def test_dus2_exit_sequence(self):
        seq = [80, 120, 180, 230]
        print("[TEST] DUS2 EXIT distances:", seq)
        for v in seq:
            self._send_measurement("door_distance", float(v))
            time.sleep(0.3)

    def test_ds2_open_alarm(self):
        print("[TEST] DS2 door_button = 1.0 (držanje >5s)")
        self._send_measurement("door_button", 1.0)
        time.sleep(6.0)
        print("[TEST] DS2 door_button = 0.0 (zatvaranje)")
        self._send_measurement("door_button", 0.0)

    def test_gsg_movement_alarm(self):
        """Tačka 6: veliki pomeraj GSG."""
        payload = {
            "accel_x": 3.0,
            "accel_y": 0.1,
            "accel_z": 0.0,
            "gyro_x": 0.0,
            "gyro_y": 0.0,
            "gyro_z": 0.0,
        }
        print("[TEST] GSG movement payload:", payload)
        self._send_measurement("gyroscope", payload)

    def test_gsg_normal(self):
        """Normalno stanje gyroscope."""
        payload = {
            "accel_x": 0.1,
            "accel_y": 0.0,
            "accel_z": 0.0,
            "gyro_x": 0.0,
            "gyro_y": 0.0,
            "gyro_z": 0.0,
        }
        print("[TEST] GSG normal payload:", payload)
        self._send_measurement("gyroscope", payload)

    def test_kitchen_btn_press(self):
        """Simulira BTN pritisak za štopericu (ako ti BTN šalje 1 -> 0)."""
        print("[TEST] Kitchen BTN = 1.0 -> 0.0")
        self._send_measurement("kitchen_button", 1.0)
        time.sleep(0.2)
        self._send_measurement("kitchen_button", 0.0)

    def _on_cmd_message(self, client, userdata, msg):
        try:
            topic_parts = msg.topic.split("/")
            device = topic_parts[3]

            payload = json.loads(msg.payload.decode())
            print(f"[CMD RECEIVED] {msg.topic} -> {payload}")

            # if device == "4sd":
            #     value = payload.get("value")
            #     if value is not None:
            #         value_str = str(value)
            #         value_str = value_str[:4]
            #         self.display.update(value_str)
            #         self._send_measurement("display_4sd", value_str)
        except Exception as e:
            print(f"[CMD ERROR] {e}")


if __name__ == "__main__":
    controller = PI2_Controller()
    controller.run()
