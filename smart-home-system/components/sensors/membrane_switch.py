import time
import random
import threading

try:
    import RPi.GPIO as GPIO  # type: ignore
    RUNNING_ON_PI = True
except ImportError:
    from mock_rpi import GPIO
    RUNNING_ON_PI = False


class MembraneSwitch:
    INVALID_VALUE = None

    def __init__(self, row_pins, col_pins, simulate=False):
        self.row_pins = row_pins
        self.col_pins = col_pins
        self.simulate = simulate

        self.keys = [
            ["1", "2", "3", "A"],
            ["4", "5", "6", "B"],
            ["7", "8", "9", "C"],
            ["*", "0", "#", "D"]
        ]

        if not simulate:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)

            for pin in self.row_pins:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)

            for pin in self.col_pins:
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    def read(self):
        if self.simulate:
            return random.choice(
                ["1","2","3","A","4","5","6","B","7","8","9","C","*","0","#","D", None]
            )

        for row_index, row_pin in enumerate(self.row_pins):
            GPIO.output(row_pin, GPIO.HIGH)

            for col_index, col_pin in enumerate(self.col_pins):
                if GPIO.input(col_pin) == 1:
                    GPIO.output(row_pin, GPIO.LOW)
                    return self.keys[row_index][col_index]

            GPIO.output(row_pin, GPIO.LOW)

        return None


def run_membrane_loop(keypad, delay, callback, stop_event):
    while True:
        value = keypad.read()

        if value is not None:
            callback(value)

        if stop_event.is_set():
            break

        time.sleep(delay)
