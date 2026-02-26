import time

try:
    import RPi.GPIO as GPIO  # type: ignore
    RUNNING_ON_PI = True
except ImportError:
    from mock_rpi import GPIO
    RUNNING_ON_PI = False


class Buzzer:
    def __init__(self, gpio_pin, simulate=False, state_callback=None):
        self.gpio_pin = gpio_pin
        self.simulate = simulate
        self.state_callback = state_callback

        if not simulate:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(gpio_pin, GPIO.OUT)
            GPIO.output(gpio_pin, GPIO.LOW)

    def _notify(self, value):
        if self.state_callback:
            self.state_callback(value)

    def on(self):
        if not self.simulate:
            GPIO.output(self.gpio_pin, GPIO.HIGH)
        else:
            print("[BUZZER] BEEP")
        self._notify(1.0)

    def off(self):
        if not self.simulate:
            GPIO.output(self.gpio_pin, GPIO.LOW)
        else:
            print("[BUZZER] OFF")
        self._notify(0.0)
