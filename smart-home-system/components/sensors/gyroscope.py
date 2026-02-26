import time
try:
    import MPU6050 # type: ignore
    RUNNING_ON_PI = True
except ImportError:
    RUNNING_ON_PI = False

import random

class Gyroscope:
    INVALID_VALUE = None

    def __init__(self, simulate=False):
        self.simulate = simulate
        self.accel = [0.0, 0.0, 0.0]
        self.gyro = [0.0, 0.0, 0.0]

        if not simulate:
            self.mpu = MPU6050.MPU6050()
            self.mpu.dmp_initialize()
        else:
            self.mpu = None

    def read(self):
        if self.simulate:
            self.accel = [round(random.uniform(-1, 1), 2) for _ in range(3)]
            self.gyro = [round(random.uniform(-250, 250), 2) for _ in range(3)]
        else:
            try:
                raw_accel = self.mpu.get_acceleration()
                raw_gyro = self.mpu.get_rotation()
                self.accel = [v / 16384.0 for v in raw_accel]
                self.gyro = [v / 131.0 for v in raw_gyro]
            except Exception:
                self.accel = [0.0, 0.0, 0.0]
                self.gyro = [0.0, 0.0, 0.0]
        return self.accel, self.gyro


def run_gyro_loop(sensor, delay, callback, stop_event):
    while True:
        accel, gyro = sensor.read()
        payload = {
            "accel_x": accel[0],
            "accel_y": accel[1],
            "accel_z": accel[2],
            "gyro_x": gyro[0],
            "gyro_y": gyro[1],
            "gyro_z": gyro[2]
        }
        callback(payload)
        if stop_event.is_set():
            break
        time.sleep(delay)
