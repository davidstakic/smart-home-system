# ============================================================================
# PI1: DS1, DPIR1, DUS1, DMS, DL, DB
# ============================================================================

from datetime import datetime
from configparser import ConfigParser
import time

try:
    import RPi.GPIO as GPIO
    RUNNING_ON_PI = True
except ImportError:
    from mock_rpi import GPIO  # mock fajl
    RUNNING_ON_PI = False


class Config:
    def __init__(self, config_file='pi1_config.ini'):
        self.config = ConfigParser()
        self.config.read(config_file, encoding='utf-8')

    def is_simulated(self, device):
        try:
            return self.config.getboolean('SIMULATION', device)
        except:
            return False

    def get_pin(self, key):
        try:
            return self.config.getint('GPIO_PINS', key)
        except:
            raise ValueError(f"Nedostaje '{key}' u [GPIO_PINS] u config fajlu")


# ============================================================================
#  SENZORI
# ============================================================================

class DoorSensor:
    """DS1 - Door Sensor (Button) - EVENT-DRIVEN"""
    def __init__(self, gpio_pin, simulate=False, on_press_callback=None):
        self.gpio_pin = gpio_pin
        self.simulate = simulate
        self.on_press_callback = on_press_callback
        self.state = "OTPUŠTEN"

        if not simulate:
            GPIO.setup(gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(
                gpio_pin,
                GPIO.FALLING,  # LOW = pritisnut
                callback=self._on_button_press,
                bouncetime=100
            )

    def _on_button_press(self, channel):
        """Callback koji se automatski poziva kada je dugme pritisnut"""
        self.state = "PRITISNUT"
        print(f"[DS1] BUTTON PRESS DETECTED na GPIO {self.gpio_pin}")
        if self.on_press_callback:
            self.on_press_callback()

        # vrati u OTPUŠTEN nakon malih zvuka
        time.sleep(0.5)
        self.state = "OTPUŠTEN"

    def read(self):
        """Čita trenutno stanje"""
        if self.simulate:
            return "SIMULIRANO: dugme"
        return self.state


class MotionSensor:
    """DPIR1 - Door Motion Sensor (PIR)"""
    def __init__(self, gpio_pin, simulate=False, on_motion_callback=None, on_no_motion_callback=None):
        self.gpio_pin = gpio_pin
        self.simulate = simulate
        self.on_motion_callback = on_motion_callback
        self.on_no_motion_callback = on_no_motion_callback
        self.state = "NEMA POKRETA"

        if not simulate:
            GPIO.setup(gpio_pin, GPIO.IN)
            GPIO.add_event_detect(
                gpio_pin,
                GPIO.RISING, # pokret detektovan
                callback=self._on_motion_detected
            )
            GPIO.add_event_detect(
                gpio_pin,
                GPIO.FALLING, # pokret prestao
                callback=self._on_no_motion
            )

    def _on_motion_detected(self, channel):
        """Callback: pokret detektovan"""
        self.state = "POKRET DETEKTOVAN"
        print(f"[DPIR1] MOTION DETECTED na GPIO {self.gpio_pin}")
        if self.on_motion_callback:
            self.on_motion_callback()

    def _on_no_motion(self, channel):
        """Callback: pokret prestao"""
        self.state = "NEMA POKRETA"
        print(f"[DPIR1] No motion na GPIO {self.gpio_pin}")
        if self.on_no_motion_callback:
            self.on_no_motion_callback()

    def read(self):
        """Čita trenutno stanje"""
        if self.simulate:
            return "SIMULIRANO: nema pokreta"
        return self.state


class UltrasonicSensor:
    """DUS1 - Door Ultrasonic Sensor - POLLING (jer je fizički drugačija)"""
    def __init__(self, trigger_pin, echo_pin, simulate=False):
        self.trigger_pin = trigger_pin
        self.echo_pin = echo_pin
        self.simulate = simulate
        self.last_distance = None

        if not simulate:
            GPIO.setup(trigger_pin, GPIO.OUT)
            GPIO.setup(echo_pin, GPIO.IN)
            GPIO.output(trigger_pin, GPIO.LOW)
            time.sleep(0.2)

    def read(self):
        """Meri rastojanje"""
        if self.simulate:
            return "SIMULIRANO: 123.45 cm"

        # Trigger puls
        GPIO.output(self.trigger_pin, False)
        time.sleep(0.2)
        GPIO.output(self.trigger_pin, True)
        time.sleep(0.00001)
        GPIO.output(self.trigger_pin, False)

        # Čekanje početka eha
        pulse_start_time = time.time()
        timeout_start = time.time()
        max_iter = 100
        iter_count = 0

        while GPIO.input(self.echo_pin) == 0:
            if iter_count > max_iter or (time.time() - timeout_start) > 0.02:
                return "GREŠKA: nema odziva (start)"
            pulse_start_time = time.time()
            iter_count += 1

        # Čekanje kraja eha
        pulse_end_time = time.time()
        timeout_start = time.time()
        iter_count = 0

        while GPIO.input(self.echo_pin) == 1:
            if iter_count > max_iter or (time.time() - timeout_start) > 0.02:
                return "GREŠKA: nema odziva (end)"
            pulse_end_time = time.time()
            iter_count += 1

        # Računanje udaljenosti
        pulse_duration = pulse_end_time - pulse_start_time
        distance = (pulse_duration * 34300) / 2
        self.last_distance = distance
        return f"{distance:.2f} cm"


class MembraneSwitch:
    """DMS - Door Membrane Switch"""
    def __init__(self, gpio_pin, simulate=False, on_press_callback=None):
        self.gpio_pin = gpio_pin
        self.simulate = simulate
        self.on_press_callback = on_press_callback
        self.state = "OTPUŠTENO"

        if not simulate:
            GPIO.setup(gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(
                gpio_pin,
                GPIO.FALLING,
                callback=self._on_membrane_press,
                bouncetime=100
            )

    def _on_membrane_press(self, channel):
        """Callback: membrana pritisnuta"""
        self.state = "PRITISNUTO"
        print(f"[DMS] MEMBRANE SWITCH PRESSED na GPIO {self.gpio_pin}")
        if self.on_press_callback:
            self.on_press_callback()
        time.sleep(0.5)
        self.state = "OTPUŠTENO"

    def read(self):
        """Čita trenutno stanje"""
        if self.simulate:
            return "SIMULIRANO: membrana"
        return self.state


# ============================================================================
# AKTUATORI
# ============================================================================

class DoorLight:
    """DL - Door Light (LED diode)"""
    def __init__(self, gpio_pin, simulate=False):
        self.gpio_pin = gpio_pin
        self.simulate = simulate
        self.is_on = False
        
        if not simulate:
            GPIO.setup(gpio_pin, GPIO.OUT)
            GPIO.output(gpio_pin, GPIO.LOW)
            
    def turn_on(self):
        self.is_on = True
        
        if not self.simulate:
            GPIO.output(self.gpio_pin, GPIO.HIGH)
            
        print("DL (Svetlo): UKLJUČENO")
        
    def turn_off(self):
        self.is_on = False
        
        if not self.simulate:
            GPIO.output(self.gpio_pin, GPIO.LOW)
            
        print("DL (Svetlo): ISKLJUČENO")
        
    def toggle(self):
        if self.is_on:
            self.turn_off()
        else:
            self.turn_on()
    
    
class DoorBuzzer:
    """DB - Door Buzzer"""
    def __init__(self, gpio_pin, simulate=False):
        self.gpio_pin = gpio_pin
        self.simulate = simulate
        
        if not simulate:
            GPIO.setup(gpio_pin, GPIO.OUT)
            GPIO.output(gpio_pin, GPIO.LOW)
    
    def beep(self, duration=0.2, times=3):
        for _ in range(times):
            if not self.simulate:
                GPIO.output(self.gpio_pin, GPIO.HIGH)
            time.sleep(duration)
            if not self.simulate:
                GPIO.output(self.gpio_pin, GPIO.LOW)
            time.sleep(0.1)
        print(f"DB (Buzzer): {times}x beep")
    
    def continuous(self, duration=2.0):
        if not self.simulate:
            GPIO.output(self.gpio_pin, GPIO.HIGH)
        time.sleep(duration)
        if not self.simulate:
            GPIO.output(self.gpio_pin, GPIO.LOW)
        print(f"DB (Buzzer): kontinuirano {duration}s")

# ============================================================================
# GLAVNI KONTROLER PI1
# ============================================================================

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

    # Callback-i za senzore (automatizacija kuce)
    def _on_door_button_pressed(self):
        """Automatski uključi svetlo kad se pritisne DS1"""
        # self.door_light.turn_on()
        pass

    def _on_motion_started(self):
        """Automatski pali svetlo i zvuk pri pokretu"""
        # self.door_light.turn_on()
        # self.buzzer.beep(0.1, 1)
        pass

    def _on_motion_stopped(self):
        """Isključi svetlo kad pokret prestane"""
        # self.door_light.turn_off()
        pass

    def _on_membrane_pressed(self):
        """Neka akcija na pritisk membrane"""
        # self.buzzer.beep(0.15, 2)
        pass

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
