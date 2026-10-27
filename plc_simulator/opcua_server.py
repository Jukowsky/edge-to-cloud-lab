"""Simulated PLC: exposes a power transformer over OPC UA. Values change every second."""
import asyncio
import logging
import math
import os
import random
import time

from asyncua import Server, ua

ENDPOINT = os.getenv("OPCUA_ENDPOINT", "opc.tcp://0.0.0.0:4840/ludvika/")
NAMESPACE = "urn:ludvika:station1"

log = logging.getLogger("plc")


async def main():
    server = Server()
    await server.init()
    server.set_endpoint(ENDPOINT)
    server.set_server_name("Station1 Simulated PLC")
    server.set_security_policy([ua.SecurityPolicyType.NoSecurity])  # lab only, see README roadmap

    # Vendor-specific nodes live in their own namespace (0 and 1 are reserved by the standard).
    ns = await server.register_namespace(NAMESPACE)

    trafo = await server.nodes.objects.add_object(ua.NodeId("Transformer3", ns), f"{ns}:Transformer3")
    temp = await trafo.add_variable(ua.NodeId("Transformer3.Temperature", ns), f"{ns}:Temperature", 60.0)
    oil = await trafo.add_variable(ua.NodeId("Transformer3.OilLevel", ns), f"{ns}:OilLevel", 87.0)
    tap = await trafo.add_variable(ua.NodeId("Transformer3.TapPosition", ns), f"{ns}:TapPosition", 7)
    breaker = await trafo.add_variable(ua.NodeId("Transformer3.BreakerClosed", ns), f"{ns}:BreakerClosed", True)
    await tap.set_writable()  # the one variable a client may write, like an operator command

    log.info("OPC UA server listening on %s (namespace index=%d)", ENDPOINT, ns)
    async with server:
        while True:
            t = time.time()
            await temp.write_value(round(60 + 5 * math.sin(t / 20) + random.uniform(-0.3, 0.3), 2))
            await oil.write_value(round(87 - (t % 600) / 100, 2))  # slow drain, resets every 10 min
            if random.random() < 0.02:  # occasional breaker operation
                await breaker.write_value(not await breaker.read_value())
            await asyncio.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    logging.getLogger("asyncua").setLevel(logging.WARNING)
    asyncio.run(main())
