try:
    import RPi.GPIO as GPIO # type: ignore
    RUNNING_ON_PI = True
except ImportError:
    from mock_rpi import GPIO
    RUNNING_ON_PI = False

class DoorLight:
    """DL - Door Light (LED diode)"""
    def __init__(self, gpio_pin, simulate=False):
        self.gpio_pin = gpio_pin
        self.simulate = simulate
        self.is_on = False
        
        if not simulate:
            GPIO.setup(gpio_pin, GPIO.OUT)
            GPIO.output(gpio_pin, GPIO.LOW)
            
    def turn_on(self):
        self.is_on = True
        
        if not self.simulate:
            GPIO.output(self.gpio_pin, GPIO.HIGH)
            
        print("DL (Svetlo): UKLJUČENO")
        
    def turn_off(self):
        self.is_on = False
        
        if not self.simulate:
            GPIO.output(self.gpio_pin, GPIO.LOW)
            
        print("DL (Svetlo): ISKLJUČENO")
        
    def toggle(self):
        if self.is_on:
            self.turn_off()
        else:
            self.turn_on()
