from gateway.buffer import Buffer


def test_fifo_order_and_ack(tmp_path):
    buf = Buffer(str(tmp_path / "q.db"))
    for i in range(3):
        buf.put("t", str(i))

    batch = buf.peek(2)
    assert [payload for _, _, payload in batch] == ["0", "1"]

    buf.ack([row_id for row_id, _, _ in batch])
    assert len(buf) == 1
    assert buf.peek(10)[0][2] == "2"


def test_unacked_messages_survive_restart(tmp_path):
    path = str(tmp_path / "q.db")
    buf = Buffer(path)
    buf.put("t", "alarm")
    buf.close()

    assert Buffer(path).peek(10)[0][1:] == ("t", "alarm")


def test_drops_oldest_when_full(tmp_path):
    buf = Buffer(str(tmp_path / "q.db"), max_messages=3)
    for i in range(5):
        buf.put("t", str(i))

    assert [payload for _, _, payload in buf.peek(10)] == ["2", "3", "4"]
