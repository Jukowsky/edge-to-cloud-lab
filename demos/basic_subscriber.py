"""Lesson 1 - the 'cloud' side: connect to the broker and print every message under site/ludvika/."""
import paho.mqtt.client as mqtt

BROKER = "localhost"
TOPIC = "site/ludvika/#"  # '#' = everything below this level


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"[sub] connected: {reason_code}")
    client.subscribe(TOPIC, qos=1)
    print(f"[sub] subscribed to {TOPIC}")


def on_message(client, userdata, msg):
    flag = " (RETAINED)" if msg.retain else ""
    print(f"[sub] {msg.topic} = {msg.payload.decode()}  qos={msg.qos}{flag}", flush=True)


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="cloud-subscriber")
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, 1883)
client.loop_forever()
