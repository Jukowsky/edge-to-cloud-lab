"""Lesson 3 - Last Will: if a device dies suddenly (power cut, cable pulled), how does the cloud find out?"""
import subprocess
import sys
import time
from pathlib import Path

import paho.mqtt.client as mqtt

STATUS = "site/location1/station1/demo_device/status"

monitor = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="cloud-monitor")
monitor.on_message = lambda c, u, m: print(f"[monitor] {time.strftime('%X')} device status: {m.payload.decode().upper()}", flush=True)
monitor.connect("localhost", 1883)
monitor.subscribe(STATUS, qos=1)
monitor.loop_start()

print("[demo] starting edge device...", flush=True)
device = subprocess.Popen([sys.executable, "-u", str(Path(__file__).with_name("edge_device.py"))])
time.sleep(4)

print(f"[demo] {time.strftime('%X')} killing the device (simulated power cut)", flush=True)
device.kill()  # dies WITHOUT disconnect() -> the broker sees an unexpected drop
time.sleep(3)

monitor.disconnect()
