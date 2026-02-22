try:
    import RPi.GPIO as GPIO  # type: ignore
except ImportError:
    from mock_rpi import GPIO


class RGBLed:

    COLORS = {
        "OFF": (0, 0, 0),
        "WHITE": (1, 1, 1),
        "RED": (1, 0, 0),
        "GREEN": (0, 1, 0),
        "BLUE": (0, 0, 1),
        "YELLOW": (1, 1, 0),
        "PURPLE": (1, 0, 1),
        "LIGHTBLUE": (0, 1, 1),
    }

    def __init__(self, red_pin, green_pin, blue_pin, simulate=False):
        self.red_pin = red_pin
        self.green_pin = green_pin
        self.blue_pin = blue_pin
        self.simulate = simulate

        if not simulate:
            GPIO.setup(self.red_pin, GPIO.OUT)
            GPIO.setup(self.green_pin, GPIO.OUT)
            GPIO.setup(self.blue_pin, GPIO.OUT)

        self.turn_off()

    def set_color(self, color_name):
        color_name = color_name.lower()

        if color_name not in self.COLORS:
            print(f"Nepoznata boja: {color_name}")
            return

        r, g, b = self.COLORS[color_name]

        if self.simulate:
            print(f"[SIMULATION] LED -> {color_name}")
            return

        GPIO.output(self.red_pin, GPIO.HIGH if r else GPIO.LOW)
        GPIO.output(self.green_pin, GPIO.HIGH if g else GPIO.LOW)
        GPIO.output(self.blue_pin, GPIO.HIGH if b else GPIO.LOW)

    def turn_off(self):
        if self.simulate:
            print("[SIMULATION] LED -> OFF")
            return

        GPIO.output(self.red_pin, GPIO.LOW)
        GPIO.output(self.green_pin, GPIO.LOW)
        GPIO.output(self.blue_pin, GPIO.LOW)

    def cleanup(self):
        self.turn_off()
