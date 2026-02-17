from datetime import datetime
from pathlib import Path
import threading
import time
import paho.mqtt.client as mqtt
import json

from components.sensors.button import Button, run_button_loop
from components.sensors.motion_sensor import MotionSensor, run_motion_loop
from components.sensors.ultrasonic_sensor import UltrasonicSensor, run_ultrasonic_loop
from components.sensors.membrane_switch import MembraneSwitch, run_membrane_loop
from components.actuators.light import Light
from components.actuators.buzzer import Buzzer
from config.config import Config
from mqtt_batch_sender import MQTTBatchSender

try:
    import RPi.GPIO as GPIO # type: ignore
    RUNNING_ON_PI = True
except ImportError:
    from mock_rpi import GPIO
    RUNNING_ON_PI = False


class PI1_Controller:
    def __init__(self, config_file=None):
        if config_file is None:
            base_dir = Path(__file__).resolve().parent
            config_file = base_dir / "config" / "pi1_config.ini"

        self.config = Config(str(config_file))

        print("========== PI1 ==========")

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        ds1_pin = self.config.get_pin('DS1_PIN')
        dpir1_pin = self.config.get_pin('DPIR1_PIN')
        dus1_trigger = self.config.get_pin('DUS1_TRIGGER')
        dus1_echo = self.config.get_pin('DUS1_ECHO')
        dl_pin = self.config.get_pin('DL_PIN')
        db_pin = self.config.get_pin('DB_PIN')
        
        row_pins = [
            self.config.get_pin("R1"),
            self.config.get_pin("R2"),
            self.config.get_pin("R3"),
            self.config.get_pin("R4"),
        ]

        col_pins = [
            self.config.get_pin("C1"),
            self.config.get_pin("C2"),
            self.config.get_pin("C3"),
            self.config.get_pin("C4"),
        ]

        self.door_sensor = Button(ds1_pin, self.config.is_simulated('DS1'))
        self.motion_sensor = MotionSensor(dpir1_pin, self.config.is_simulated('DPIR1'))
        self.ultrasonic = UltrasonicSensor(dus1_trigger, dus1_echo, self.config.is_simulated('DUS1'))
        self.membrane_switch = MembraneSwitch(row_pins, col_pins, simulate=self.config.is_simulated("DMS"))

        self.door_light = Light(dl_pin, self.config.is_simulated('DL'))
        self.buzzer = Buzzer(db_pin, self.config.is_simulated('DB'), state_callback=lambda val: self._send_measurement("door_buzzer", val))

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
        # ts = datetime.now().strftime("%H:%M:%S")
        # print(f"[{ts}] DS1 Door Button -> {value}")
        self._send_measurement("door_button", value)

    def _motion_callback(self, value):
        # ts = datetime.now().strftime("%H:%M:%S")
        # print(f"[{ts}] DPIR1 Motion -> {value}")
        self._send_measurement("door_motion", value)

    def _ultrasonic_callback(self, value):
        # ts = datetime.now().strftime("%H:%M:%S")
        # print(f"[{ts}] DUS1 Distance -> {value}")
        self._send_measurement("door_distance", value)

    def _membrane_callback(self, value):
        # ts = datetime.now().strftime("%H:%M:%S")
        # print(f"[{ts}] DMS Membrane -> {value}")
        self._send_measurement("door_membrane", value)

    def start_sensors(self):
        # self.threads.append(threading.Thread(target=run_button_loop, args=(self.door_sensor, self.config.get_value("SENSOR_CONFIG", "BTN_DELAY", 0.5, float), self._door_callback, self.stop_event), daemon=True))
        # self.threads.append(threading.Thread(target=run_motion_loop, args=(self.motion_sensor, self.config.get_value("SENSOR_CONFIG", "PIR_TIMEOUT", 30, float), self._motion_callback, self.stop_event), daemon=True))
        # self.threads.append(threading.Thread(target=run_ultrasonic_loop, args=(self.ultrasonic, self.config.get_value("SENSOR_CONFIG", "ULTRASONIC_DELAY", 0.5, float), self._ultrasonic_callback, self.stop_event), daemon=True))
        # self.threads.append(threading.Thread(target=run_membrane_loop, args=(self.membrane_switch, self.config.get_value("SENSOR_CONFIG", "DMS_DELAY", 0.2, float), self._membrane_callback, self.stop_event), daemon=True))

        for t in self.threads:
            t.start()

    def actuator_menu(self):
        try:
            while True:
                print("\n=== PI1 MENI ===")
                print("--- Aktuatori ---")
                print("[1] Uključi svetlo")
                print("[2] Isključi svetlo")
                print("[3] Toggle svetlo")
                print("[4] Kratki beep")
                print("[5] Dugi beep")
                print("--- Test senzora / demo ---")
                print("[6] TEST DPIR1 -> door_motion (tačka 1)")
                print("[7] TEST DUS1 ulazak (tačka 2 ENTRY)")
                print("[8] TEST DUS1 izlazak (tačka 2 EXIT)")
                print("[9] TEST DS1 otvoreno 6s (tačka 3)")
                print("[10] TEST DMS PIN 1234 (tačka 4A)")
                print("[0] Izlaz")
                choice = input("Odaberi opciju: ").strip()

                if choice == "1":
                    self.door_light.turn_on()
                    self._send_measurement("door_light", 1.0)
                elif choice == "2":
                    self.door_light.turn_off()
                    self._send_measurement("door_light", 0.0)
                elif choice == "3":
                    self.door_light.toggle()
                    self._send_measurement("door_light", 1.0 if self.door_light.is_on else 0.0)
                elif choice == "4":
                    threading.Thread(target=self.buzzer.beep, args=(0.2, 3), daemon=True).start()
                elif choice == "5":
                    threading.Thread(target=self.buzzer.continuous, args=(2.0,), daemon=True).start()
                elif choice == "6":
                    self.test_dpir1_pulse()
                elif choice == "7":
                    self.test_dus1_entry_sequence()
                elif choice == "8":
                    self.test_dus1_exit_sequence()
                elif choice == "9":
                    self.test_ds1_open_alarm()
                elif choice == "10":
                    self.test_dms_pin()
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
        GPIO.cleanup()
        print("Kraj programa.")

    def run(self):
        self.start_sensors()
        self.actuator_menu()
        self.cleanup()

        # ===== TEST / DEMO FUNKCIJE =====

    def test_dpir1_pulse(self):
        """Tačka 1: DPIR1 -> door_motion=1.0 jednokratno."""
        print("[TEST] DPIR1 door_motion = 1.0")
        self._send_measurement("door_motion", 1.0)

    def test_dus1_entry_sequence(self):
        """Tačka 2: DUS1 ulazak, opadajuće distance."""
        seq = [200, 150, 100, 80, 60, 40]
        print("[TEST] DUS1 ENTRY distances:", seq)
        for v in seq:
            self._send_measurement("door_distance", float(v))
            time.sleep(0.3)

    def test_dus1_exit_sequence(self):
        """Tačka 2: DUS1 izlazak, rastuće distance."""
        seq = [80, 120, 160, 180, 230]
        print("[TEST] DUS1 EXIT distances:", seq)
        for v in seq:
            self._send_measurement("door_distance", float(v))
            time.sleep(0.3)

    def test_ds1_open_alarm(self):
        """Tačka 3: DS1 drži 1.0 > 5s pa 0.0."""
        print("[TEST] DS1 door_button = 1.0 (držanje >5s)")
        self._send_measurement("door_button", 1.0)
        time.sleep(8.0)
        print("[TEST] DS1 door_button = 0.0 (zatvaranje)")
        self._send_measurement("door_button", 0.0)

    def test_dms_pin(self):
        """Tačka 4A: DMS PIN 1234."""
        pin = "1234"
        print(f"[TEST] DMS door_membrane = {pin}")
        self._send_measurement("door_membrane", pin)

    def _on_cmd_message(self, client, userdata, msg):
        try:
            topic_parts = msg.topic.split("/")
            device = topic_parts[3]

            payload = json.loads(msg.payload.decode())
            print(f"[CMD RECEIVED] {msg.topic} -> {payload}")

            action = payload.get("action")

            # if device == "door_light":
            #     if action == "on":
            #         self.door_light.turn_on()
            #         self._send_measurement("door_light", 1.0)
            #     elif action == "off":
            #         self.door_light.turn_off()
            #         self._send_measurement("door_light", 0.0)
            # elif device == "door_buzzer":
            #     if action == "on":
            #         self.buzzer.continuous(5.0)
            #     # dodati stop metodu
            #     # elif action == "off":
            #     #     self.buzzer.stop()
        except Exception as e:
            print(f"[CMD ERROR] {e}")


if __name__ == "__main__":
    controller = PI1_Controller()
    controller.run()
