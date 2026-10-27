"""Gateway settings, read from environment variables so one image fits every site."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    opcua_url: str
    opcua_object: str
    publishing_interval_ms: int
    mqtt_host: str
    mqtt_port: int
    mqtt_client_id: str
    topic_prefix: str
    buffer_path: str
    buffer_max_messages: int

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            opcua_url=os.getenv("OPCUA_URL", "opc.tcp://localhost:4840/location1/"),
            opcua_object=os.getenv("OPCUA_OBJECT", "ns=2;s=Transformer3"),
            publishing_interval_ms=int(os.getenv("OPCUA_PUBLISHING_INTERVAL_MS", "500")),
            mqtt_host=os.getenv("MQTT_HOST", "localhost"),
            mqtt_port=int(os.getenv("MQTT_PORT", "1883")),
            mqtt_client_id=os.getenv("MQTT_CLIENT_ID", "edge-gateway-1"),
            topic_prefix=os.getenv("TOPIC_PREFIX", "site/location1/station1"),
            buffer_path=os.getenv("BUFFER_PATH", "buffer.db"),
            buffer_max_messages=int(os.getenv("BUFFER_MAX_MESSAGES", "100000")),
        )
