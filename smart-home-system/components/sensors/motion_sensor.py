import random
import time

try:
    import RPi.GPIO as GPIO  # type: ignore
    RUNNING_ON_PI = True
except ImportError:
    from mock_rpi import GPIO
    RUNNING_ON_PI = False

class MotionSensor:
    NO_MOTION = 0
    MOTION = 1
    INVALID_VALUE = -999

    def __init__(self, gpio_pin, simulate=False):
        self.gpio_pin = gpio_pin
        self.simulate = simulate
        self.value = self.NO_MOTION

        if not simulate:
            GPIO.setup(gpio_pin, GPIO.IN)

    def read(self):
        if self.simulate:
            self.value = random.choice([self.NO_MOTION, self.MOTION])
        else:
            self.value = GPIO.input(self.gpio_pin)
        return self.value

def run_motion_loop(sensor, delay, callback, stop_event):
    while True:
        value = sensor.read()
        if value not in [sensor.NO_MOTION, sensor.MOTION]:
            value = sensor.INVALID_VALUE
        callback(value)
        if stop_event.is_set():
            break
        time.sleep(delay)
