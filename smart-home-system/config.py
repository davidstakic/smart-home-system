from configparser import ConfigParser

class Config:
    def __init__(self, config_file='pi1_config.ini'):
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
