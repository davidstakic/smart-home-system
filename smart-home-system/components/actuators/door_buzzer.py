import time

try:
    import RPi.GPIO as GPIO # type: ignore
    RUNNING_ON_PI = True
except ImportError:
    from mock_rpi import GPIO
    RUNNING_ON_PI = False

class DoorBuzzer:
    """DB - Door Buzzer"""
    def __init__(self, gpio_pin, simulate=False):
        self.gpio_pin = gpio_pin
        self.simulate = simulate
        
        if not simulate:
            GPIO.setup(gpio_pin, GPIO.OUT)
            GPIO.output(gpio_pin, GPIO.LOW)
    
    def beep(self, duration=0.2, times=3):
        for _ in range(times):
            if not self.simulate:
                GPIO.output(self.gpio_pin, GPIO.HIGH)
            time.sleep(duration)
            if not self.simulate:
                GPIO.output(self.gpio_pin, GPIO.LOW)
            time.sleep(0.1)
        print(f"DB (Buzzer): {times}x beep")
    
    def continuous(self, duration=2.0):
        if not self.simulate:
            GPIO.output(self.gpio_pin, GPIO.HIGH)
        time.sleep(duration)
        if not self.simulate:
            GPIO.output(self.gpio_pin, GPIO.LOW)
        print(f"DB (Buzzer): kontinuirano {duration}s")
