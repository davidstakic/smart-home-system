from datetime import datetime
import random
import time

try:
    import RPi.GPIO as GPIO
    RUNNING_ON_PI = True
except ImportError:
    from mock_rpi import GPIO
    RUNNING_ON_PI = False


class DoorSensor:
    def __init__(self, gpio_pin, simulate=False, on_press_callback=None):
        self.gpio_pin = gpio_pin
        self.simulate = simulate
        self.on_press_callback = on_press_callback
        self.value = 0.0  # 0 = otpušten, 1 = pritisnut

        if not simulate:
            GPIO.setup(gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(
                gpio_pin,
                GPIO.FALLING,
                callback=self._on_button_press,
                bouncetime=100
            )

    def _on_button_press(self, channel):
        self.value = 1.0
        print(f"[DS1] BUTTON PRESS na GPIO {self.gpio_pin}")
        if self.on_press_callback:
            self.on_press_callback()

        time.sleep(0.3)
        self.value = 0.0

    def read(self):
        if self.simulate:
            self.value = float(random.choice([0, 1]))
        return self.value


class MotionSensor:
    def __init__(self, gpio_pin, simulate=False,
                 on_motion_callback=None, on_no_motion_callback=None):
        self.gpio_pin = gpio_pin
        self.simulate = simulate
        self.on_motion_callback = on_motion_callback
        self.on_no_motion_callback = on_no_motion_callback
        self.value = 0.0  # 0 = nema pokreta, 1 = pokret

        if not simulate:
            GPIO.setup(gpio_pin, GPIO.IN)
            GPIO.add_event_detect(
                gpio_pin,
                GPIO.RISING,
                callback=self._on_motion_detected
            )
            GPIO.add_event_detect(
                gpio_pin,
                GPIO.FALLING,
                callback=self._on_no_motion
            )

    def _on_motion_detected(self, channel):
        self.value = 1.0
        print(f"[DPIR1] MOTION DETECTED na GPIO {self.gpio_pin}")
        if self.on_motion_callback:
            self.on_motion_callback()

    def _on_no_motion(self, channel):
        self.value = 0.0
        print(f"[DPIR1] NO MOTION na GPIO {self.gpio_pin}")
        if self.on_no_motion_callback:
            self.on_no_motion_callback()

    def read(self):
        if self.simulate:
            self.value = float(random.choice([0, 1]))
        return self.value


class UltrasonicSensor:
    def __init__(self, trigger_pin, echo_pin, simulate=False):
        self.trigger_pin = trigger_pin
        self.echo_pin = echo_pin
        self.simulate = simulate
        self.last_distance = -1.0

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
                    return -1.0
                pulse_start = time.time()

            timeout_start = time.time()
            while GPIO.input(self.echo_pin) == 1:
                if time.time() - timeout_start > 0.02:
                    return -1.0
                pulse_end = time.time()

            pulse_duration = pulse_end - pulse_start
            distance = (pulse_duration * 34300) / 2
            self.last_distance = round(distance, 2)
            return self.last_distance

        except Exception:
            return -1.0


class MembraneSwitch:
    def __init__(self, gpio_pin, simulate=False, on_press_callback=None):
        self.gpio_pin = gpio_pin
        self.simulate = simulate
        self.on_press_callback = on_press_callback
        self.value = 0.0  # 0 = otpušten, 1 = pritisnut

        if not simulate:
            GPIO.setup(gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(
                gpio_pin,
                GPIO.FALLING,
                callback=self._on_membrane_press,
                bouncetime=100
            )

    def _on_membrane_press(self, channel):
        self.value = 1.0
        print(f"[DMS] PRESSED na GPIO {self.gpio_pin}")
        if self.on_press_callback:
            self.on_press_callback()

        time.sleep(0.3)
        self.value = 0.0

    def read(self):
        if self.simulate:
            self.value = float(random.choice([0, 1]))
        return self.value
