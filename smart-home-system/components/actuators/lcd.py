import time

try:
    import smbus # type: ignore
    RUNNING_ON_PI = True
except ImportError:
    RUNNING_ON_PI = False


class LCD16x2:

    LCD_WIDTH = 16
    LCD_CHR = 1
    LCD_CMD = 0

    LCD_LINE_1 = 0x80
    LCD_LINE_2 = 0xC0

    ENABLE = 0b00000100

    def __init__(self, address=0x27, bus=1, simulate=False):
        self.address = address
        self.simulate = simulate

        if not simulate and RUNNING_ON_PI:
            self.bus = smbus.SMBus(bus)
            self._init_lcd()
        else:
            self.bus = None

    def _write_byte(self, data):
        if not self.simulate:
            self.bus.write_byte(self.address, data)

    def _toggle_enable(self, bits):
        time.sleep(0.0005)
        self._write_byte(bits | self.ENABLE)
        time.sleep(0.0005)
        self._write_byte(bits & ~self.ENABLE)
        time.sleep(0.0005)

    def _send(self, bits, mode):
        high_bits = mode | (bits & 0xF0)
        low_bits = mode | ((bits << 4) & 0xF0)

        self._write_byte(high_bits)
        self._toggle_enable(high_bits)

        self._write_byte(low_bits)
        self._toggle_enable(low_bits)

    def _init_lcd(self):
        time.sleep(0.02)
        self._send(0x33, self.LCD_CMD)
        self._send(0x32, self.LCD_CMD)
        self._send(0x06, self.LCD_CMD)
        self._send(0x0C, self.LCD_CMD)
        self._send(0x28, self.LCD_CMD)
        self._send(0x01, self.LCD_CMD)
        time.sleep(0.005)

    def clear(self):
        if self.simulate:
            print("[SIMULATION] LCD CLEAR")
            return
        self._send(0x01, self.LCD_CMD)

    def display(self, text, line=1):
        text = text.ljust(self.LCD_WIDTH, " ")

        if self.simulate:
            print(f"[SIMULATION] LCD Line {line}: {text}")
            return

        if line == 1:
            self._send(self.LCD_LINE_1, self.LCD_CMD)
        elif line == 2:
            self._send(self.LCD_LINE_2, self.LCD_CMD)

        for char in text:
            self._send(ord(char), self.LCD_CHR)

    def cleanup(self):
        self.clear()
