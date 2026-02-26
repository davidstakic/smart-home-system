import time

import time

try:
    import RPi.GPIO as GPIO # type: ignore
    RUNNING_ON_PI = True
except ImportError:
    from mock_rpi import GPIO
    RUNNING_ON_PI = False

class Display4SD:
    def __init__(self, segment_pins, digit_pins, simulate=False, brightness=7, update_interval=0.002):
        self.segment_pins = segment_pins
        self.digit_pins = digit_pins
        self.simulate = simulate
        self.brightness = brightness
        self.update_interval = update_interval
        self.blink = False
        self._blink_state = True
        self.value = "    "
        self._stop_event = None

        self.num_map = {
            ' ': (0,0,0,0,0,0,0),
            '0': (1,1,1,1,1,1,0),
            '1': (0,1,1,0,0,0,0),
            '2': (1,1,0,1,1,0,1),
            '3': (1,1,1,1,0,0,1),
            '4': (0,1,1,0,0,1,1),
            '5': (1,0,1,1,0,1,1),
            '6': (1,0,1,1,1,1,1),
            '7': (1,1,1,0,0,0,0),
            '8': (1,1,1,1,1,1,1),
            '9': (1,1,1,1,0,1,1),
        }

        if not simulate:
            self.GPIO = GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            for pin in self.segment_pins:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, 0)
            for pin in self.digit_pins:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, 1)
        else:
            self.GPIO = None

    def update(self, value: str):
        self.value = str(value).rjust(4)
        print("[DISPLAY] " + str(value))

    def run_loop(self, stop_event):
        self._stop_event = stop_event
        blink_timer = time.time()
        while not stop_event.is_set():
            if self.blink:
                if time.time() - blink_timer > 0.5:
                    self._blink_state = not self._blink_state
                    blink_timer = time.time()
            else:
                self._blink_state = True

            for digit_idx in range(4):
                for seg_idx in range(7):
                    seg_val = self.num_map.get(self.value[digit_idx], (0,0,0,0,0,0,0))[seg_idx]
                    if not self.simulate:
                        self.GPIO.output(self.segment_pins[seg_idx], seg_val if self._blink_state else 0)
                if not self.simulate:
                    self.GPIO.output(self.digit_pins[digit_idx], 0 if self._blink_state else 1)
                time.sleep(self.update_interval)
                if not self.simulate:
                    self.GPIO.output(self.digit_pins[digit_idx], 1)

    def turn_off(self):
        if not self.simulate:
            for pin in self.segment_pins:
                self.GPIO.output(pin, 0)
            for pin in self.digit_pins:
                self.GPIO.output(pin, 1)
        self.value = "    "

    def cleanup(self):
        if not self.simulate and self.GPIO:
            self.turn_off()
            self.GPIO.cleanup()
