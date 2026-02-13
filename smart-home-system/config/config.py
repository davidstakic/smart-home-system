from configparser import ConfigParser

class Config:
    def __init__(self, config_file='smart-home-system\pi1_config.ini'):
        self.config = ConfigParser()
        self.config.read(config_file, encoding='utf-8')

    def is_simulated(self, device):
        try:
            return self.config.getboolean('SIMULATION', device)
        except:
            return False

    def get_pin(self, key):
        try:
            return self.config.getint('GPIO_PINS', key)
        except:
            raise ValueError(f"Nedostaje '{key}' u [GPIO_PINS] u config fajlu")
        
    def get_device_info(self):
        return {
            "pi_id": self.config.get("DEVICE", "PI_ID"),
            "device_name": self.config.get("DEVICE", "DEVICE_NAME")
        }

    def get_mqtt_config(self):
        return {
            "broker": self.config.get("MQTT", "BROKER"),
            "port": self.config.getint("MQTT", "PORT"),
            "base_topic": self.config.get("MQTT", "BASE_TOPIC"),
            "batch_size": self.config.getint("MQTT", "BATCH_SIZE"),
            "send_interval": self.config.getint("MQTT", "SEND_INTERVAL")
        }
