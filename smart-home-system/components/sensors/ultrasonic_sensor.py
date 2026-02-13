import random
import time

try:
    import RPi.GPIO as GPIO  # type: ignore
    RUNNING_ON_PI = True
except ImportError:
    from mock_rpi import GPIO
    RUNNING_ON_PI = False

class UltrasonicSensor:
    INVALID_DISTANCE = -1.0

    def __init__(self, trigger_pin, echo_pin, simulate=False):
        self.trigger_pin = trigger_pin
        self.echo_pin = echo_pin
        self.simulate = simulate
        self.last_distance = self.INVALID_DISTANCE

        if not simulate:
            GPIO.setup(trigger_pin, GPIO.OUT)
            GPIO.setup(echo_pin, GPIO.IN)
            GPIO.output(trigger_pin, GPIO.LOW)
            time.sleep(0.2)

    def read(self):
        if self.simulate:
            self.last_distance = round(random.uniform(5.0, 200.0), 2)
            return self.last_distance

        try:
            GPIO.output(self.trigger_pin, False)
            time.sleep(0.0002)
            GPIO.output(self.trigger_pin, True)
            time.sleep(0.00001)
            GPIO.output(self.trigger_pin, False)

            timeout_start = time.time()
            while GPIO.input(self.echo_pin) == 0:
                if time.time() - timeout_start > 0.02:
                    self.last_distance = self.INVALID_DISTANCE
                    return self.last_distance
                pulse_start = time.time()

            timeout_start = time.time()
            while GPIO.input(self.echo_pin) == 1:
                if time.time() - timeout_start > 0.02:
                    self.last_distance = self.INVALID_DISTANCE
                    return self.last_distance
                pulse_end = time.time()

            pulse_duration = pulse_end - pulse_start
            distance = (pulse_duration * 34300) / 2
            self.last_distance = round(distance, 2)
            return self.last_distance

        except Exception:
            self.last_distance = self.INVALID_DISTANCE
            return self.last_distance

def run_ultrasonic_loop(sensor, delay, callback, stop_event):
    while True:
        distance = sensor.read()
        callback(distance)
        if stop_event.is_set():
            break
        time.sleep(delay)
