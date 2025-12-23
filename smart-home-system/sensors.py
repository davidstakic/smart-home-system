
from datetime import datetime
from configparser import ConfigParser
import random
import time

try:
    import RPi.GPIO as GPIO
    RUNNING_ON_PI = True
except ImportError:
    from mock_rpi import GPIO  # mock fajl
    RUNNING_ON_PI = False
    
class DoorSensor:
    """DS1 - Door Sensor (Button)"""
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
        self.state = "PRITISNUT"
        print(f"[DS1] BUTTON PRESS DETECTED na GPIO {self.gpio_pin}")
        if self.on_press_callback:
            self.on_press_callback()

        # vrati u OTPUŠTEN nakon malih zvuka
        time.sleep(0.5)
        self.state = "OTPUŠTEN"

    def read(self):
        if self.simulate:
            self.state = random.choice(["PRITISNUT", "OTPUŠTEN"])
            return self.state
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
        self.state = "POKRET DETEKTOVAN"
        print(f"[DPIR1] MOTION DETECTED na GPIO {self.gpio_pin}")
        if self.on_motion_callback:
            self.on_motion_callback()

    def _on_no_motion(self, channel):
        self.state = "NEMA POKRETA"
        print(f"[DPIR1] No motion na GPIO {self.gpio_pin}")
        if self.on_no_motion_callback:
            self.on_no_motion_callback()

    def read(self):
        if self.simulate:
            self.state = random.choice(["POKRET DETEKTOVAN", "NEMA POKRETA"])
            return self.state
        return self.state


class UltrasonicSensor:
    """DUS1 - Door Ultrasonic Sensor"""
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
        if self.simulate:
            distance = round(random.uniform(5.0, 200.0), 2)
            self.last_distance = distance
            return f"{distance:.2f} cm"

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
        self.state = "PRITISNUTO"
        print(f"[DMS] MEMBRANE SWITCH PRESSED na GPIO {self.gpio_pin}")
        if self.on_press_callback:
            self.on_press_callback()
        time.sleep(0.5)
        self.state = "OTPUŠTENO"

    def read(self):
        if self.simulate:
            self.state = random.choice(["PRITISNUTO", "OTPUŠTENO"])
            return self.state
        return self.state