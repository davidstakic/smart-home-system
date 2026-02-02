import json
import paho.mqtt.client as mqtt

class MQTTCommandListener:
    def __init__(self, config, door_light, door_buzzer, mqtt_sender):
        self.config = config
        self.door_light = door_light
        self.door_buzzer = door_buzzer
        self.mqtt_sender = mqtt_sender
        
        mqtt_cfg = self.config.get_mqtt_config()
        self.client = mqtt.Client()
        self.client.connect(mqtt_cfg['broker'], mqtt_cfg['port'], 60)
        self.client.on_message = self._on_message
    
    def start(self):
        device_info = self.config.get_device_info()
        base_topic = f"smart_home/{device_info['pi_id']}/cmd/#"
        self.client.subscribe(base_topic)
        self.client.loop_start()
        print(f"MQTT listener subscribed to: {base_topic}")
    
    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            action = payload.get("action")
            
            print(f"[CMD RECEIVED] {msg.topic} -> {action}")
            
            if msg.topic.endswith("door_light"):
                self._handle_light(action)
            elif msg.topic.endswith("door_buzzer"):
                self._handle_buzzer(payload)
        except Exception as e:
            print(f"[CMD ERROR] {e}")
    
    def _handle_light(self, action):
        """Handle light and send to MQTT"""
        if action == "on":
            self.door_light.on()
        elif action == "off":
            self.door_light.off()
        elif action == "toggle":
            self.door_light.toggle()
        else:
            return
        
        value = 1.0 if self.door_light.is_on else 0.0
        device_info = self.config.get_device_info()
        
        payload = {
            "pi_id": device_info["pi_id"],
            "device_name": device_info["device_name"],
            "sensor_type": "door_light",
            "simulated": self.config.is_simulated("DL"),
            "value": value
        }
        
        self.mqtt_sender.enqueue(payload)
        print(f"Sent to MQTT: door_light = {value}")
    
    def _handle_buzzer(self, payload):
        """Handle buzzer and send to MQTT"""
        action = payload.get("action")
        
        if action == "beep":
            times = payload.get("times", 1)
            duration = payload.get("duration", 0.2)
            
            for _ in range(times):
                self.door_buzzer.beep(duration)
            
            device_info = self.config.get_device_info()
            buzzer_payload = {
                "pi_id": device_info["pi_id"],
                "device_name": device_info["device_name"],
                "sensor_type": "door_buzzer",
                "simulated": self.config.is_simulated("DB"),
                "value": 1.0
            }
            
            self.mqtt_sender.enqueue(buzzer_payload)
            print(f"Sent to MQTT: door_buzzer beep")
