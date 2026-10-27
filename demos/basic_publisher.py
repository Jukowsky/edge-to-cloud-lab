"""Lesson 1 - the 'edge device' side: publish a transformer temperature once per second."""
import json
import random
import time

import paho.mqtt.client as mqtt

BROKER = "localhost"
TOPIC = "site/location1/station1/transformer3/temperature"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="demo-publisher")
client.connect(BROKER, 1883)
client.loop_start()  # runs network traffic (sending, PUBACKs) in a background thread

for i in range(5):
    payload = json.dumps({"value": round(60 + random.uniform(-2, 2), 2), "unit": "C", "ts": time.time()})
    client.publish(TOPIC, payload, qos=1)
    print(f"[pub] sent: {payload}", flush=True)
    time.sleep(1)

client.loop_stop()
client.disconnect()
