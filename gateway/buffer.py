"""Durable FIFO queue on SQLite: messages survive broker outages and gateway restarts."""
import sqlite3


class Buffer:
    def __init__(self, path: str, max_messages: int = 100_000):
        self._max = max_messages
        self._db = sqlite3.connect(path)
        self._db.execute("PRAGMA journal_mode=WAL")  # crash-safe without fsync on every read
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS queue (id INTEGER PRIMARY KEY AUTOINCREMENT, topic TEXT, payload TEXT)"
        )
        self._db.commit()

    def put(self, topic: str, payload: str) -> None:
        cur = self._db.execute("INSERT INTO queue (topic, payload) VALUES (?, ?)", (topic, payload))
        # Disk is finite: during a long outage drop the oldest data, keep the newest.
        self._db.execute("DELETE FROM queue WHERE id <= ?", (cur.lastrowid - self._max,))
        self._db.commit()

    def peek(self, limit: int) -> list[tuple[int, str, str]]:
        return self._db.execute("SELECT id, topic, payload FROM queue ORDER BY id LIMIT ?", (limit,)).fetchall()

    def ack(self, ids: list[int]) -> None:
        self._db.executemany("DELETE FROM queue WHERE id = ?", [(i,) for i in ids])
        self._db.commit()

    def __len__(self) -> int:
        return self._db.execute("SELECT COUNT(*) FROM queue").fetchone()[0]

    def close(self) -> None:
        self._db.close()
