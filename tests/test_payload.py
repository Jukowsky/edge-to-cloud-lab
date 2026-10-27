import json
from datetime import datetime, timezone

from asyncua import ua

from gateway.main import to_payload, to_topic_segment


def test_topic_segment_from_browse_name():
    assert to_topic_segment("TapPosition") == "tap_position"
    assert to_topic_segment("Transformer3") == "transformer3"


def test_payload_keeps_device_timestamp_and_quality():
    ts = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)
    dv = ua.DataValue(ua.Variant(61.2), ua.StatusCode(ua.StatusCodes.BadSensorFailure), SourceTimestamp=ts)

    data = json.loads(to_payload(dv))

    assert data["value"] == 61.2
    assert data["quality"] == "BadSensorFailure"
    assert data["source_ts"] == ts.isoformat()
