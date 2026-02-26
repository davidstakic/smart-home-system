import random
import time

try:
    import RPi.GPIO as GPIO  # type: ignore
    RUNNING_ON_PI = True
except ImportError:
    from mock_rpi import GPIO
    RUNNING_ON_PI = False

class Button:
    DOOR_CLOSED = 0
    DOOR_OPEN = 1
    INVALID_VALUE = -999

    def __init__(self, gpio_pin, simulate=False):
        self.gpio_pin = gpio_pin
        self.simulate = simulate
        self.value = self.DOOR_CLOSED

        if not simulate:
            GPIO.setup(gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def read(self):
        if self.simulate:
            self.value = random.choice([self.DOOR_CLOSED, self.DOOR_OPEN])
        else:
            self.value = GPIO.input(self.gpio_pin)
        return self.value

def run_button_loop(button_sensor, delay, callback, stop_event):
    while True:
        value = button_sensor.read()
        
        if value not in [button_sensor.DOOR_CLOSED, button_sensor.DOOR_OPEN]:
            value = button_sensor.INVALID_VALUE
            
        callback(value)
        
        if stop_event.is_set():
            break
        
        time.sleep(delay)
