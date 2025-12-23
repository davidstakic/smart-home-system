# ============================================================================
# PI1: DS1, DPIR1, DUS1, DMS, DL, DB
# ============================================================================

from datetime import datetime
from sensors import *
from actuators import *
from config import Config

try:
    import RPi.GPIO as GPIO
    RUNNING_ON_PI = True
except ImportError:
    from mock_rpi import GPIO  # mock fajl
    RUNNING_ON_PI = False


class PI1_Controller:
    def __init__(self, config_file='pi1_config.ini'):
        self.config = Config(config_file)

        print("=" * 70)
        print("PI1 - PAMETNA VRATA (KT1) - EVENT-DRIVEN")
        print("=" * 70)

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # Pinovi iz .ini
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

        self.running = True

    def read_all_sensors(self):
        """Ulazne podatke sa SVAKOG senzora ispisati u konzoli (KT1 uslov)."""
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{ts}] *** STANJE SENZORA NA PI1 ***")
        print(f"  DS1  (Door Button)     -> {self.door_sensor.read()}")
        print(f"  DPIR1(Door Motion)     -> {self.motion_sensor.read()}")
        print(f"  DUS1 (Ultrasonic dist) -> {self.ultrasonic.read()}")
        print(f"  DMS  (Membrane Switch) -> {self.membrane_switch.read()}")

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


if __name__ == "__main__":
    c = PI1_Controller()
    c.run()
