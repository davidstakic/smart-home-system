import time
import random
from datetime import datetime

try:
    import RPi.GPIO as GPIO # type: ignore
except ImportError:
    from mock_rpi import GPIO


class IRReceiver:

    INVALID_VALUE = "INVALID"

    BUTTONS = [
        0x300ff22dd, 0x300ffc23d, 0x300ff629d, 0x300ffa857,
        0x300ff9867, 0x300ffb04f, 0x300ff6897, 0x300ff02fd,
        0x300ff30cf, 0x300ff18e7, 0x300ff7a85, 0x300ff10ef,
        0x300ff38c7, 0x300ff5aa5, 0x300ff42bd, 0x300ff4ab5,
        0x300ff52ad
    ]

    BUTTON_NAMES = [
        "LEFT", "RIGHT", "UP", "DOWN",
        "2", "3", "1", "OK",
        "4", "5", "6", "7",
        "8", "9", "*", "0", "#"
    ]

    def __init__(self, gpio_pin, simulate=False):
        self.gpio_pin = gpio_pin
        self.simulate = simulate

        if not simulate:
            GPIO.setup(self.gpio_pin, GPIO.IN)

    def _get_binary(self):
        num1s = 0
        binary = 1
        command = []
        previousValue = 0
        value = GPIO.input(self.gpio_pin)

        while value:
            time.sleep(0.0001)
            value = GPIO.input(self.gpio_pin)

        startTime = datetime.now()

        while True:
            if previousValue != value:
                now = datetime.now()
                pulseTime = now - startTime
                startTime = now
                command.append((previousValue, pulseTime.microseconds))

            if value:
                num1s += 1
            else:
                num1s = 0

            if num1s > 10000:
                break

            previousValue = value
            value = GPIO.input(self.gpio_pin)

        for (typ, tme) in command:
            if typ == 1:
                if tme > 1000:
                    binary = binary * 10 + 1
                else:
                    binary *= 10

        if len(str(binary)) > 34:
            binary = int(str(binary)[:34])

        return binary

    def _convert_hex(self, binaryValue):
        tmp = int(str(binaryValue), 2)
        return hex(tmp)

    def read(self):
        if self.simulate:
            return random.choice(self.BUTTON_NAMES + [None])

        try:
            inData = self._convert_hex(self._get_binary())

            for i in range(len(self.BUTTONS)):
                if hex(self.BUTTONS[i]) == inData:
                    return self.BUTTON_NAMES[i]

            return self.INVALID_VALUE

        except:
            return self.INVALID_VALUE

def run_ir_loop(sensor, delay, callback, stop_event):
    while True:
        value = sensor.read()

        if value and value != sensor.INVALID_VALUE:
            callback(value)
            
        if stop_event.is_set():
            break

        time.sleep(delay)
