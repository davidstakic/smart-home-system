from datetime import datetime
from pathlib import Path
import threading

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
        self.buzzer = Buzzer(db_pin, self.config.is_simulated('DB'))

        self.device_info = self.config.get_device_info()
        mqtt_cfg = self.config.get_mqtt_config()
        self.mqtt_sender = MQTTBatchSender(
            mqtt_cfg["broker"],
            mqtt_cfg["port"],
            mqtt_cfg["base_topic"],
            mqtt_cfg["batch_size"],
            mqtt_cfg["send_interval"]
        )

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
        self.threads.append(threading.Thread(target=run_button_loop, args=(self.door_sensor, self.config.get_value("SENSOR_CONFIG", "BTN_DELAY", 0.5, float), self._door_callback, self.stop_event), daemon=True))
        self.threads.append(threading.Thread(target=run_motion_loop, args=(self.motion_sensor, self.config.get_value("SENSOR_CONFIG", "PIR_TIMEOUT", 30, float), self._motion_callback, self.stop_event), daemon=True))
        self.threads.append(threading.Thread(target=run_ultrasonic_loop, args=(self.ultrasonic, self.config.get_value("SENSOR_CONFIG", "ULTRASONIC_DELAY", 0.5, float), self._ultrasonic_callback, self.stop_event), daemon=True))
        self.threads.append(threading.Thread(target=run_membrane_loop, args=(self.membrane_switch, self.config.get_value("SENSOR_CONFIG", "DMS_DELAY", 0.2, float), self._membrane_callback, self.stop_event), daemon=True))

        for t in self.threads:
            t.start()

    def actuator_menu(self):
        try:
            while True:
                print("\n=== AKTUATORI ===")
                print("[1] Uključi svetlo")
                print("[2] Isključi svetlo")
                print("[3] Toggle svetlo")
                print("[4] Kratki beep")
                print("[5] Dugi beep")
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
                    self._send_measurement("door_buzzer", 1.0)
                elif choice == "5":
                    threading.Thread(target=self.buzzer.continuous, args=(2.0,), daemon=True).start()
                    self._send_measurement("door_buzzer", 1.0)
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


if __name__ == "__main__":
    controller = PI1_Controller()
    controller.run()
