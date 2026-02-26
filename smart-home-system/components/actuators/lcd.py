import time

try:
    from PCF8574 import PCF8574_GPIO
    from Adafruit_LCD1602 import Adafruit_CharLCD
    RUNNING_ON_PI = True
except ImportError:
    RUNNING_ON_PI = False


class LCD:
    def __init__(self, simulate):
        self.simulate = simulate
        self.PCF8574_address = 0x27
        self.PCF8574A_address = 0x3F

        if not self.simulate:
            try:
                self.mcp = PCF8574_GPIO(self.PCF8574_address)
            except:
                try:
                    self.mcp = PCF8574_GPIO(self.PCF8574A_address)
                except:
                    print('I2C Address Error !')
                    exit(1)

            self.lcd = Adafruit_CharLCD(
                pin_rs=0,
                pin_e=2,
                pins_db=[4, 5, 6, 7],
                GPIO=self.mcp
            )

            self.mcp.output(3, 1)
            self.lcd.begin(16, 2)

    def display_message(self, message: str):
        if not self.simulate:
            self.lcd.clear()
            self.lcd.setCursor(0, 0)
            self.lcd.message(message)
        else:
            print("[LCD] " + message)

    def destroy(self):
        if not self.simulate:
            self.lcd.clear()
