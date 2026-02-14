from datetime import datetime
from pathlib import Path
import threading
import time

from components.sensors.dht import DHTSensor, run_dht_loop
from components.sensors.motion_sensor import MotionSensor, run_motion_loop
from components.sensors.infrared import IRReceiver, run_ir_loop
from components.actuators.rgb_led import RGBLed
from components.actuators.lcd import LCD16x2
from config.config import Config
from mqtt_batch_sender import MQTTBatchSender

try:
    import RPi.GPIO as GPIO  # type: ignore
    RUNNING_ON_PI = True
except ImportError:
    from mock_rpi import GPIO
    RUNNING_ON_PI = False


class PI3_Controller:
    def __init__(self, config_file=None):
        if config_file is None:
            base_dir = Path(__file__).resolve().parent
            config_file = base_dir / "config" / "pi3_config.ini"

        self.config = Config(str(config_file))
        print("========== PI3 ==========")

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        red_pin = self.config.get_pin("LED_RED")
        green_pin = self.config.get_pin("LED_GREEN")
        blue_pin = self.config.get_pin("LED_BLUE")
        ir_pin = self.config.get_pin("IR_PIN")
        dht1_pin = self.config.get_pin("DHT1_PIN")
        dht2_pin = self.config.get_pin("DHT2_PIN")
        dpir3_pin = self.config.get_pin("DPIR3_PIN")

        self.dht1 = DHTSensor(dht1_pin, self.config.is_simulated("DHT1"))
        self.dht2 = DHTSensor(dht2_pin, self.config.is_simulated("DHT2"))
        self.dpir3 = MotionSensor(dpir3_pin, self.config.is_simulated("DPIR3"))
        self.ir_sensor = IRReceiver(ir_pin, self.config.is_simulated("IR"))

        self.rgb_led = RGBLed(red_pin, green_pin, blue_pin, simulate=self.config.is_simulated("BRGB"))
        self.lcd = LCD16x2(address=self.config.get_value("LCD_CONFIG", "I2C_ADDRESS", 0x27, int),
                           simulate=self.config.is_simulated("LCD"))

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

    def _dht1_callback(self, humidity, temperature, code):
        self._send_measurement("bedroom_dht_humidity", humidity)
        self._send_measurement("bedroom_dht_temperature", temperature)

    def _dht2_callback(self, humidity, temperature, code):
        self._send_measurement("master_dht_humidity", humidity)
        self._send_measurement("master_dht_temperature", temperature)

    def _motion_callback(self, value):
        self._send_measurement("livingroom_motion", value)

    def _ir_callback(self, value):
        self._send_measurement("bedroom_ir", value)

    def start_sensors(self):
        cfg = self.config

        self.threads.append(threading.Thread(
            target=run_dht_loop,
            args=(self.dht1, cfg.get_value("SENSOR_CONFIG", "DHT_DELAY", 2.0, float), self._dht1_callback, self.stop_event),
            daemon=True
        ))

        self.threads.append(threading.Thread(
            target=run_dht_loop,
            args=(self.dht2, cfg.get_value("SENSOR_CONFIG", "DHT_DELAY", 2.0, float), self._dht2_callback, self.stop_event),
            daemon=True
        ))

        self.threads.append(threading.Thread(
            target=run_motion_loop,
            args=(self.dpir3, cfg.get_value("SENSOR_CONFIG", "PIR_TIMEOUT", 30, float), self._motion_callback, self.stop_event),
            daemon=True
        ))

        self.threads.append(threading.Thread(
            target=run_ir_loop,
            args=(self.ir_sensor, cfg.get_value("SENSOR_CONFIG", "IR_DELAY", 0.2, float), self._ir_callback, self.stop_event),
            daemon=True
        ))

        for t in self.threads:
            t.start()

    def actuator_menu(self):
        try:
            while True:
                print("\n=== AKTUATORI ===")
                print("[1] RGB LED WHITE")
                print("[2] RGB LED RED")
                print("[3] RGB LED GREEN")
                print("[4] RGB LED BLUE")
                print("[5] Turn off RGB")
                print("[6] Update LCD message")
                print("[0] Izlaz")
                choice = input("Odaberi opciju: ").strip()

                if choice == "1":
                    self.rgb_led.white()
                    self._send_measurement("rgb_led", "WHITE")
                elif choice == "2":
                    self.rgb_led.red()
                    self._send_measurement("rgb_led", "RED")
                elif choice == "3":
                    self.rgb_led.green()
                    self._send_measurement("rgb_led", "GREEN")
                elif choice == "4":
                    self.rgb_led.blue()
                    self._send_measurement("rgb_led", "BLUE")
                elif choice == "5":
                    self.rgb_led.turn_off()
                    self._send_measurement("rgb_led", "OFF")
                elif choice == "6":
                    msg = input("Unesi poruku za LCD: ")
                    self.lcd.display_text(msg)
                    self._send_measurement("lcd_message", msg)
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
        self.rgb_led.cleanup()
        self.lcd.cleanup()
        GPIO.cleanup()
        print("Kraj programa.")

    def run(self):
        self.start_sensors()
        self.actuator_menu()
        self.cleanup()


if __name__ == "__main__":
    controller = PI3_Controller()
    controller.run()
