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
        
    def get_value(self, section, key, default=None, value_type=str):
        try:
            if value_type == int:
                return self.config.getint(section, key)
            elif value_type == float:
                return self.config.getfloat(section, key)
            elif value_type == bool:
                return self.config.getboolean(section, key)
            else:
                return self.config.get(section, key)
        except:
            return default
