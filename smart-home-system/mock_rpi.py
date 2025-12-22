class MockGPIO:
    BCM = 'BCM'
    OUT = 'OUT'
    IN = 'IN'
    HIGH = 1
    LOW = 0
    PUD_UP = 'PUD_UP'

    def __init__(self):
        self.mode = None
        self.pins = {}
        self.warnings = True

    def setmode(self, mode):
        self.mode = mode
        print(f"[MOCK GPIO] setmode({mode})")

    def setwarnings(self, flag):
        self.warnings = flag

    def setup(self, pin, direction, pull_up_down=None):
        self.pins[pin] = {
            "dir": direction,
            "value": self.LOW,
            "pull": pull_up_down,
        }
        print(f"[MOCK GPIO] setup(pin={pin}, dir={direction}, pud={pull_up_down})")

    def input(self, pin):
        # Vrati fiksnu vrednost ili je kasnije možeš menjati ručno
        val = self.pins.get(pin, {}).get("value", self.LOW)
        print(f"[MOCK GPIO] input(pin={pin}) -> {val}")
        return val

    def output(self, pin, value):
        if pin in self.pins:
            self.pins[pin]["value"] = value
        print(f"[MOCK GPIO] output(pin={pin}, value={value})")

    def cleanup(self):
        print("[MOCK GPIO] cleanup()")
        self.pins.clear()


# globalni objekat, da se ponaša kao modul RPi.GPIO
GPIO = MockGPIO()
