"""A device that leaves a Last Will when connecting, then announces itself online and publishes."""
import time

import paho.mqtt.client as mqtt

BROKER = "localhost"
STATUS = "site/ludvika/station1/demo_device/status"
TEMP = "site/ludvika/station1/transformer3/temperature"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="demo-device")

# "If I vanish without saying goodbye, publish this on my behalf."
# Must be set BEFORE connect(): the broker receives it inside the CONNECT packet.
client.will_set(STATUS, "offline", qos=1, retain=True)

client.connect(BROKER, 1883, keepalive=10)  # silent for 1.5 x 10 s -> broker declares us dead
client.loop_start()
client.publish(STATUS, "online", qos=1, retain=True)
print("[device] connected, status=online", flush=True)

while True:
    client.publish(TEMP, "61.0", qos=1)
    time.sleep(1)
