import random
import time

try:
    import RPi.GPIO as GPIO  # type: ignore
    RUNNING_ON_PI = True
except ImportError:
    from mock_rpi import GPIO
    RUNNING_ON_PI = False

class MembraneSwitch:
    SWITCH_OFF = 0
    SWITCH_ON = 1
    INVALID_VALUE = -999

    def __init__(self, gpio_pin, simulate=False):
        self.gpio_pin = gpio_pin
        self.simulate = simulate
        self.value = self.SWITCH_OFF

        if not simulate:
            GPIO.setup(gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def read(self):
        if self.simulate:
            self.value = random.choice([self.SWITCH_OFF, self.SWITCH_ON])
        else:
            self.value = GPIO.input(self.gpio_pin)
        return self.value

def run_membrane_loop(switch, delay, callback, stop_event):
    while True:
        value = switch.read()
        if value not in [switch.SWITCH_OFF, switch.SWITCH_ON]:
            value = switch.INVALID_VALUE
        callback(value)
        if stop_event.is_set():
            break
        time.sleep(delay)
