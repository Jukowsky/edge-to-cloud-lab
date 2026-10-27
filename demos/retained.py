"""Lesson 2 - Retained messages: does a late subscriber get the 'last known value'?"""
import time

import paho.mqtt.client as mqtt

BROKER = "localhost"
NORMAL = "site/location1/station1/transformer3/temperature"
RETAINED = "site/location1/station1/transformer3/tap_position"

# 1) The device publishes two messages while NOBODY is subscribed.
pub = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="demo-publisher")
pub.connect(BROKER, 1883)
pub.loop_start()
pub.publish(NORMAL, "61.2", qos=1).wait_for_publish()
pub.publish(RETAINED, "7", qos=1, retain=True).wait_for_publish()
print("[pub] sent temperature=61.2 (normal) and tap_position=7 (retained), nobody listening")
pub.disconnect()

time.sleep(2)

# 2) A dashboard connects LATER.
print("[sub] a new subscriber connects 2 s later...")
sub = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="late-dashboard")
sub.on_message = lambda c, u, m: print(f"[sub] {m.topic} = {m.payload.decode()}  retain={m.retain}")
sub.connect(BROKER, 1883)
sub.subscribe("site/location1/#", qos=1)
sub.loop_start()
time.sleep(2)
sub.disconnect()
print("[sub] done. Temperature was lost, tap_position arrived because the broker kept it.")
