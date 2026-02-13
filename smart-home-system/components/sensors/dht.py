import time
import random

try:
    import RPi.GPIO as GPIO  # type: ignore
    RUNNING_ON_PI = True
except ImportError:
    from mock_rpi import GPIO
    RUNNING_ON_PI = False


class DHTSensor:
    DHTLIB_OK = 0
    DHTLIB_ERROR_CHECKSUM = -1
    DHTLIB_ERROR_TIMEOUT = -2
    DHTLIB_INVALID_VALUE = -999

    DHT11_WAKEUP = 0.020
    DHTLIB_TIMEOUT = 0.0001

    def __init__(self, gpio_pin, simulate=False):
        self.gpio_pin = gpio_pin
        self.simulate = simulate
        self.humidity = self.DHTLIB_INVALID_VALUE
        self.temperature = self.DHTLIB_INVALID_VALUE
        self.bits = [0, 0, 0, 0, 0]

        if not simulate:
            GPIO.setup(self.gpio_pin, GPIO.OUT)
            GPIO.output(self.gpio_pin, GPIO.HIGH)
            time.sleep(0.2)

    def _read_sensor(self):
        mask = 0x80
        idx = 0
        self.bits = [0, 0, 0, 0, 0]

        if self.simulate:
            self.humidity = round(random.uniform(30.0, 70.0), 1)
            self.temperature = round(random.uniform(20.0, 30.0), 1)
            return self.DHTLIB_OK

        try:
            GPIO.setup(self.gpio_pin, GPIO.OUT)
            GPIO.output(self.gpio_pin, GPIO.LOW)
            time.sleep(self.DHT11_WAKEUP)
            GPIO.output(self.gpio_pin, GPIO.HIGH)
            GPIO.setup(self.gpio_pin, GPIO.IN)

            t0 = time.time()
            while GPIO.input(self.gpio_pin) == 0:
                if (time.time() - t0) > self.DHTLIB_TIMEOUT:
                    return self.DHTLIB_ERROR_TIMEOUT

            t0 = time.time()
            while GPIO.input(self.gpio_pin) == 1:
                if (time.time() - t0) > self.DHTLIB_TIMEOUT:
                    return self.DHTLIB_ERROR_TIMEOUT

            for i in range(40):
                t0 = time.time()
                while GPIO.input(self.gpio_pin) == 0:
                    if (time.time() - t0) > self.DHTLIB_TIMEOUT:
                        return self.DHTLIB_ERROR_TIMEOUT
                t0 = time.time()
                while GPIO.input(self.gpio_pin) == 1:
                    if (time.time() - t0) > self.DHTLIB_TIMEOUT:
                        return self.DHTLIB_ERROR_TIMEOUT
                if (time.time() - t0) > 0.00005:
                    self.bits[idx] |= mask
                mask >>= 1
                if mask == 0:
                    mask = 0x80
                    idx += 1

            GPIO.setup(self.gpio_pin, GPIO.OUT)
            GPIO.output(self.gpio_pin, GPIO.HIGH)
            return self.DHTLIB_OK

        except Exception:
            return self.DHTLIB_ERROR_TIMEOUT

    def read(self):
        if self.simulate:
            self.humidity = round(random.uniform(30.0, 70.0), 1)
            self.temperature = round(random.uniform(20.0, 30.0), 1)
            return self.humidity, self.temperature, self.DHTLIB_OK

        code = self._read_sensor()
        if code != self.DHTLIB_OK:
            self.humidity = self.DHTLIB_INVALID_VALUE
            self.temperature = self.DHTLIB_INVALID_VALUE
            return self.humidity, self.temperature, code

        self.humidity = self.bits[0]
        self.temperature = self.bits[2] + self.bits[3] * 0.1
        sumChk = (self.bits[0] + self.bits[1] + self.bits[2] + self.bits[3]) & 0xFF
        if self.bits[4] != sumChk:
            code = self.DHTLIB_ERROR_CHECKSUM
        return self.humidity, self.temperature, code


def parseCheckCode(code):
    if code == 0:
        return "DHTLIB_OK"
    elif code == -1:
        return "DHTLIB_ERROR_CHECKSUM"
    elif code == -2:
        return "DHTLIB_ERROR_TIMEOUT"
    elif code == -999:
        return "DHTLIB_INVALID_VALUE"


def run_dht_loop(sensor, delay, callback, stop_event):
    while not stop_event.is_set():
        humidity, temperature, code = sensor.read()
        callback(humidity, temperature, parseCheckCode(code))
        time.sleep(delay)
