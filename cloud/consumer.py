"""Cloud-side consumer: prints everything the site publishes.

Uses a persistent session (fixed client id + clean_session=False), so QoS 1 messages
published while this consumer is down are delivered when it comes back.
"""
import json
import os

import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPIC = os.getenv("SUBSCRIBE_TOPIC", "site/#")


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"[cloud] connected: {reason_code} (session resumed: {flags.session_present})", flush=True)
    client.subscribe(TOPIC, qos=1)


def on_message(client, userdata, msg):
    text = msg.payload.decode()
    try:
        data = json.loads(text)
        text = f"{data['value']!s:>8}  quality={data['quality']}  source_ts={data['source_ts']}"
    except (ValueError, KeyError, TypeError):
        pass  # plain-text status messages
    retained = "  [retained]" if msg.retain else ""
    print(f"[cloud] {msg.topic:<48} {text}{retained}", flush=True)


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="cloud-consumer", clean_session=False)
client.on_connect = on_connect
client.on_message = on_message
client.connect_async(MQTT_HOST, MQTT_PORT)
client.loop_forever(retry_first_connection=True)
