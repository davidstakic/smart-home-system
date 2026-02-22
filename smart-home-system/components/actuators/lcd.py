import time

try:
    from PCF8574 import PCF8574_GPIO
    from Adafruit_LCD1602 import Adafruit_CharLCD
    RUNNING_ON_PI = True
except ImportError:
    RUNNING_ON_PI = False


class LCD:
    def __init__(
        self,
        address=0x27,
        pin_rs=0,
        pin_e=2,
        pins_db=(4, 5, 6, 7),
        backlight_pin=3,
        simulate=False
    ):
        self.simulate = simulate
        self.address = address
        self.backlight_pin = backlight_pin
        self.lcd = None

        if not self.simulate:
            try:
                mcp = PCF8574_GPIO(address)
            except:
                mcp = PCF8574_GPIO(0x3F)

            self.mcp = mcp

            self.lcd = Adafruit_CharLCD(
                pin_rs=pin_rs,
                pin_e=pin_e,
                pins_db=list(pins_db),
                GPIO=mcp
            )

            self.lcd.begin(16, 2)
            self.lcd.clear()

    def display(self, line1="", line2=""):
        line1 = line1.ljust(16)[:16]
        line2 = line2.ljust(16)[:16]

        if self.simulate:
            print("------ LCD ------")
            print(line1)
            print(line2)
            print("-----------------")
        else:
            self.lcd.clear()
            self.lcd.setCursor(0, 0)
            self.lcd.message(line1)
            self.lcd.setCursor(0, 1)
            self.lcd.message(line2)

    def clear(self):
        if self.simulate:
            print("[LCD CLEAR]")
        else:
            self.lcd.clear()

    def backlight(self, state=True):
        if self.simulate:
            print(f"[LCD BACKLIGHT {'ON' if state else 'OFF'}]")
        else:
            self.mcp.output(self.backlight_pin, 1 if state else 0)

    def cleanup(self):
        if not self.simulate:
            self.lcd.clear()
        print("LCD cleanup done")
