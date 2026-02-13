import json
import time
import threading
from queue import Queue, Empty
import paho.mqtt.client as mqtt

class MQTTBatchSender:
    def __init__(self, broker, port, base_topic, batch_size, send_interval):
        self.queue = Queue()
        self.batch_size = batch_size
        self.send_interval = send_interval
        self.base_topic = base_topic
        self.running = True

        self.client = mqtt.Client()
        self.client.connect(broker, port, 60)
        self.client.loop_start()

        self.thread = threading.Thread(target=self._daemon, daemon=True)
        self.thread.start()

    def enqueue(self, payload: dict):
        self.queue.put(payload)

    def _daemon(self):
        batch = []
        last_send = time.time()

        while self.running:
            try:
                item = self.queue.get(timeout=1)
                batch.append(item)
            except Empty:
                pass

            now = time.time()
            if (
                len(batch) >= self.batch_size or
                (batch and now - last_send >= self.send_interval)
            ):
                for payload in batch:
                    topic = f"{self.base_topic}/{payload['sensor_type']}"
                    self.client.publish(topic, json.dumps(payload))
                batch.clear()
                last_send = now
