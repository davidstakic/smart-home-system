from datetime import datetime
from components.sensors import *
from components.actuators import *
from config.config import Config
from mqtt_batch_sender import MQTTBatchSender

try:
    import RPi.GPIO as GPIO
    RUNNING_ON_PI = True
except ImportError:
    from mock_rpi import GPIO  # mock fajl
    RUNNING_ON_PI = False


class PI1_Controller:
    def __init__(self, config_file='smart-home-system\pi1_config.ini'):
        self.config = Config(config_file)

        print("=" * 70)
        print("PI1 - PAMETNA VRATA (KT1) - EVENT-DRIVEN")
        print("=" * 70)

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        ds1_pin = self.config.get_pin('DS1_PIN')
        dpir1_pin = self.config.get_pin('DPIR1_PIN')
        dus1_trigger = self.config.get_pin('DUS1_TRIGGER')
        dus1_echo = self.config.get_pin('DUS1_ECHO')
        dms_pin = self.config.get_pin('DMS_PIN')
        dl_pin = self.config.get_pin('DL_PIN')
        db_pin = self.config.get_pin('DB_PIN')

        # Senzori
        self.door_sensor = DoorSensor(
            ds1_pin,
            self.config.is_simulated('DS1'),
            on_press_callback=self._on_door_button_pressed
        )
        self.motion_sensor = MotionSensor(
            dpir1_pin,
            self.config.is_simulated('DPIR1'),
            on_motion_callback=self._on_motion_started,
            on_no_motion_callback=self._on_motion_stopped
        )
        self.ultrasonic = UltrasonicSensor(
            dus1_trigger,
            dus1_echo,
            self.config.is_simulated('DUS1')
        )
        self.membrane_switch = MembraneSwitch(
            dms_pin,
            self.config.is_simulated('DMS'),
            on_press_callback=self._on_membrane_pressed
        )

        # Aktuatori
        self.door_light = DoorLight(dl_pin, self.config.is_simulated('DL'))
        self.buzzer = DoorBuzzer(db_pin, self.config.is_simulated('DB'))
        
        self.device_info = self.config.get_device_info()
        mqtt_cfg = self.config.get_mqtt_config()

        self.mqtt_sender = MQTTBatchSender(
            mqtt_cfg["broker"],
            mqtt_cfg["port"],
            mqtt_cfg["base_topic"],
            mqtt_cfg["batch_size"],
            mqtt_cfg["send_interval"]
        )

        self.running = True
        
    def _send_measurement(self, sensor_type, value):
        payload = {
            "pi_id": self.device_info["pi_id"],
            "device_name": self.device_info["device_name"],
            "sensor_type": sensor_type,
            "simulated": self.config.is_simulated(sensor_type),
            "value": value
        }
        self.mqtt_sender.enqueue(payload)

    def read_all_sensors(self):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{ts}] *** STANJE SENZORA NA PI1 ***")

        v = self.door_sensor.read()
        print(f"  DS1  (Door Button)     -> {v}")
        self._send_measurement("door_button", v)

        v = self.motion_sensor.read()
        print(f"  DPIR1(Door Motion)     -> {v}")
        self._send_measurement("door_motion", v)

        v = self.ultrasonic.read()
        print(f"  DUS1 (Ultrasonic dist) -> {v}")
        self._send_measurement("door_distance", v)

        v = self.membrane_switch.read()
        print(f"  DMS  (Membrane Switch) -> {v}")
        self._send_measurement("door_membrane", v)

    def display_menu(self):
        print("\n" + "=" * 70)
        print("Konzolna aplikacija - PI1")
        print("=" * 70)
        print("[1] Čitanje svih senzora (DS1, DPIR1, DUS1, DMS)")
        print("[2] Uključi svetlo (DL)")
        print("[3] Isključi svetlo (DL)")
        print("[4] Toggle svetla (DL)")
        print("[5] Kratki beep (DB)")
        print("[6] Dugi beep (DB)")
        print("[0] Izlaz")
        print()

    def run(self):
        try:
            while self.running:
                self.display_menu()
                choice = input("Odaberi opciju: ").strip()

                if choice == "1":
                    self.read_all_sensors()
                elif choice == "2":
                    self.door_light.turn_on()
                elif choice == "3":
                    self.door_light.turn_off()
                elif choice == "4":
                    self.door_light.toggle()
                elif choice == "5":
                    self.buzzer.beep(0.2, 3)
                elif choice == "6":
                    self.buzzer.continuous(2.0)
                elif choice == "0":
                    print("Izlaz...")
                    self.running = False
                else:
                    print("Nepoznata opcija.")
        except KeyboardInterrupt:
            print("\nPrekid (Ctrl+C)")
        finally:
            self.cleanup()

    def cleanup(self):
        print("Čišćenje GPIO...")
        GPIO.cleanup()
        print("Kraj.")
        
    def _on_door_button_pressed(self):
        print("[EVENT] DS1 – dugme na vratima pritisnuto")
        self.buzzer.beep(0.1, 1)
        self._send_measurement("door_buzzer", 1.0)

    def _on_motion_started(self):
        print("[EVENT] DPIR1 – detektovan pokret")
        self.door_light.turn_on()
        self._send_measurement("door_light", 1.0)

    def _on_motion_stopped(self):
        print("[EVENT] DPIR1 – nema više pokreta")
        self.door_light.turn_off()
        self._send_measurement("door_light", 0.0)

    def _on_membrane_pressed(self):
        print("[EVENT] DMS – membranski prekidač pritisnut")
        self.buzzer.beep(0.2, 2)
        self._send_measurement("door_buzzer", 1.0)


if __name__ == "__main__":
    c = PI1_Controller()
    c.run()
