"""Kết nối và khởi tạo CSDL SQLite."""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1
_SCHEMA_FILE = Path(__file__).with_name("schema.sql")


def ket_noi(duong_dan: str | Path) -> sqlite3.Connection:
    """Mở CSDL (tạo mới nếu chưa có) và bảo đảm lược đồ đã được tạo."""
    conn = sqlite3.connect(str(duong_dan))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    khoi_tao(conn)
    return conn


def khoi_tao(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA_FILE.read_text(encoding="utf-8"))
    conn.execute(
        "INSERT OR IGNORE INTO cau_hinh(khoa, gia_tri) VALUES ('schema_version', ?)",
        (str(SCHEMA_VERSION),),
    )
    conn.commit()
