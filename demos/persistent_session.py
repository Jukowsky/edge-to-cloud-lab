"""Lesson 4 - QoS + persistent session: what happens to messages sent while a subscriber is offline?"""
import time

import paho.mqtt.client as mqtt

BROKER = "localhost"
TOPIC = "site/ludvika/station1/transformer3/events"


def archive_client():
    # clean_session=False -> "remember me and keep what arrives while I'm away"
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="cloud-archive", clean_session=False)
    c.on_message = lambda cl, u, m: print(f"[archive] received: {m.payload.decode()}  (qos={m.qos})")
    c.connect(BROKER, 1883)
    c.loop_start()
    return c


# 1) The archive service subscribes once, then goes offline (maintenance, network outage...).
archive = archive_client()
archive.subscribe(TOPIC, qos=1)
time.sleep(1)
archive.disconnect()
print("[archive] offline")

# 2) While it is away the device sends 4 messages: two QoS 0, two QoS 1.
pub = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="demo-publisher")
pub.connect(BROKER, 1883)
pub.loop_start()
for text, qos in [("reading-A", 0), ("ALARM-1: oil temperature high", 1), ("reading-B", 0), ("ALARM-2: fan failure", 1)]:
    pub.publish(TOPIC, text, qos=qos).wait_for_publish()
    print(f"[pub] sent: {text}  (qos={qos})")
pub.disconnect()

# 3) The archive comes back with the same client id.
time.sleep(1)
print("[archive] reconnecting...")
archive = archive_client()
time.sleep(2)
archive.disconnect()
