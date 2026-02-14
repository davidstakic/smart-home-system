import time

try:
    import RPi.GPIO as GPIO # type: ignore
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
            GPIO.setup(gpio_pin, GPIO.OUT)
            GPIO.output(gpio_pin, GPIO.LOW)

    def _notify(self, value):
        if self.state_callback:
            self.state_callback(value)

    def beep(self, duration=0.2, times=3):
        self._notify(1.0)

        for _ in range(times):
            if not self.simulate:
                GPIO.output(self.gpio_pin, GPIO.HIGH)
            time.sleep(duration)
            if not self.simulate:
                GPIO.output(self.gpio_pin, GPIO.LOW)
            time.sleep(0.1)

        self._notify(0.0)
        print(f"Buzzer: {times}x beep")

    def continuous(self, duration=2.0):
        self._notify(1.0)

        if not self.simulate:
            GPIO.output(self.gpio_pin, GPIO.HIGH)
        time.sleep(duration)
        if not self.simulate:
            GPIO.output(self.gpio_pin, GPIO.LOW)

        self._notify(0.0)
        print(f"Buzzer: kontinuirano {duration}s")

