import time
import threading

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

        self._stop_event = threading.Event()
        self._thread = None

        if not simulate:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(gpio_pin, GPIO.OUT)
            GPIO.output(gpio_pin, GPIO.LOW)

    def _notify(self, value):
        if self.state_callback:
            self.state_callback(value)

    def _play_tone(self, pitch, duration):
        period = 1.0 / pitch
        delay = period / 2
        cycles = int(duration * pitch)

        self._notify(1.0)

        for _ in range(cycles):
            if self._stop_event.is_set():
                break

            if not self.simulate:
                GPIO.output(self.gpio_pin, True)
            time.sleep(delay)

            if not self.simulate:
                GPIO.output(self.gpio_pin, False)
            time.sleep(delay)

        self._notify(0.0)

    def beep(self, pitch=440, duration=2.0):
        self.stop()
        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._play_tone,
            args=(pitch, duration),
            daemon=True
        )
        self._thread.start()

    def continuous(self, pitch=440):
        self.stop()
        self._stop_event.clear()

        def loop():
            self._notify(1.0)
            period = 1.0 / pitch
            delay = period / 2

            while not self._stop_event.is_set():
                if not self.simulate:
                    GPIO.output(self.gpio_pin, True)
                time.sleep(delay)
                if not self.simulate:
                    GPIO.output(self.gpio_pin, False)
                time.sleep(delay)

            self._notify(0.0)

        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join()

        if not self.simulate:
            GPIO.output(self.gpio_pin, GPIO.LOW)

        self._notify(0.0)
