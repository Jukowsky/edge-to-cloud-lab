"""Edge gateway: subscribes to OPC UA variables and forwards every change to MQTT.

Data path:  OPC UA subscription -> SQLite buffer -> MQTT (QoS 1)
Every change is written to disk first, so nothing is lost while the broker is unreachable.
"""
import asyncio
import json
import logging
import re
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from asyncua import Client, ua

from gateway.buffer import Buffer
from gateway.config import Config

log = logging.getLogger("gateway")


def to_topic_segment(browse_name: str) -> str:
    """'TapPosition' -> 'tap_position'"""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", browse_name).lower()


def to_payload(dv: ua.DataValue) -> str:
    return json.dumps({
        "value": dv.Value.Value,
        "quality": dv.StatusCode.name,
        # Measurement time comes from the device, not from us or the cloud.
        "source_ts": dv.SourceTimestamp.isoformat() if dv.SourceTimestamp else None,
        "gateway_ts": datetime.now(timezone.utc).isoformat(),
    })


class ChangeHandler:
    """asyncua calls this for every value change; we only persist, forwarding happens elsewhere."""

    def __init__(self, buffer: Buffer, topics: dict):
        self._buffer = buffer
        self._topics = topics

    def datachange_notification(self, node, val, data):
        self._buffer.put(self._topics[node.nodeid], to_payload(data.monitored_item.Value))


class Status:
    """Retained status topics, so anyone can tell 'gateway down' from 'PLC unreachable'."""

    def __init__(self, client: mqtt.Client, prefix: str):
        self._client = client
        self.gateway_topic = f"{prefix}/gateway/status"
        self.opcua_topic = f"{prefix}/gateway/opcua"
        self.opcua = "disconnected"

    def set_opcua(self, state: str) -> None:
        if state == self.opcua:
            return
        self.opcua = state
        if self._client.is_connected():
            self._client.publish(self.opcua_topic, state, qos=1, retain=True)

    def announce(self) -> None:
        self._client.publish(self.gateway_topic, "online", qos=1, retain=True)
        self._client.publish(self.opcua_topic, self.opcua, qos=1, retain=True)


def start_mqtt(cfg: Config) -> tuple[mqtt.Client, Status]:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cfg.mqtt_client_id)
    status = Status(client, cfg.topic_prefix)
    client.will_set(status.gateway_topic, "offline", qos=1, retain=True)

    def on_connect(c, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            log.warning("MQTT connect refused: %s", reason_code)
            return
        log.info("MQTT connected to %s:%d", cfg.mqtt_host, cfg.mqtt_port)
        status.announce()

    def on_disconnect(c, userdata, flags, reason_code, properties):
        log.warning("MQTT disconnected (%s), buffering to disk", reason_code)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.connect_async(cfg.mqtt_host, cfg.mqtt_port, keepalive=30)
    client.loop_start()  # network thread; keeps reconnecting on its own
    return client, status


async def mirror_opcua(cfg: Config, buffer: Buffer, status: Status) -> None:
    """Keep an OPC UA subscription alive, reconnecting whenever the PLC goes away."""
    while True:
        try:
            async with Client(cfg.opcua_url, timeout=5) as client:
                obj = client.get_node(cfg.opcua_object)
                prefix = f"{cfg.topic_prefix}/{to_topic_segment((await obj.read_browse_name()).Name)}"
                # Browse instead of hard-coding: whatever the device exposes gets forwarded.
                variables = await obj.get_children(nodeclassmask=ua.NodeClass.Variable)
                topics = {
                    v.nodeid: f"{prefix}/{to_topic_segment((await v.read_browse_name()).Name)}" for v in variables
                }
                sub = await client.create_subscription(cfg.publishing_interval_ms, ChangeHandler(buffer, topics))
                await sub.subscribe_data_change(variables)
                log.info("OPC UA subscribed to %d variables under %s", len(variables), cfg.opcua_object)
                status.set_opcua("connected")
                while True:
                    await asyncio.sleep(2)
                    await client.check_connection()
        except Exception as e:  # any failure means the same thing here: reconnect
            status.set_opcua("disconnected")
            log.warning("OPC UA connection to %s lost (%s: %s), retrying in 5 s", cfg.opcua_url, type(e).__name__, e)
            await asyncio.sleep(5)


async def forward(client: mqtt.Client, buffer: Buffer, batch_size: int = 100, ack_timeout: float = 10) -> None:
    """Drain the buffer oldest-first; a row is deleted only after the broker acknowledged it (PUBACK)."""
    while True:
        if not client.is_connected() or len(buffer) == 0:
            await asyncio.sleep(0.2)
            continue
        batch = buffer.peek(batch_size)
        sent = [(row_id, client.publish(topic, payload, qos=1)) for row_id, topic, payload in batch]
        deadline = time.monotonic() + ack_timeout
        while client.is_connected() and time.monotonic() < deadline and not all(i.is_published() for _, i in sent):
            await asyncio.sleep(0.05)
        # Unacknowledged rows stay and are sent again: at-least-once, consumers must tolerate duplicates.
        buffer.ack([row_id for row_id, info in sent if info.is_published()])


async def report(client: mqtt.Client, buffer: Buffer, every: float = 10) -> None:
    while True:
        await asyncio.sleep(every)
        if not client.is_connected():
            log.info("buffer: %d messages waiting for the broker", len(buffer))


async def main() -> None:
    cfg = Config.from_env()
    buffer = Buffer(cfg.buffer_path, cfg.buffer_max_messages)
    log.info("starting, %d messages already buffered at %s", len(buffer), cfg.buffer_path)
    client, status = start_mqtt(cfg)
    await asyncio.gather(mirror_opcua(cfg, buffer, status), forward(client, buffer), report(client, buffer))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    logging.getLogger("asyncua").setLevel(logging.ERROR)
    asyncio.run(main())
