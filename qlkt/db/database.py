"""Kết nối và khởi tạo CSDL.

- Có khóa: SQLCipher (AES-256, mã hóa toàn bộ tệp CSDL). Dùng khi chạy thật.
- Không khóa: SQLite thường. Chỉ dùng cho kiểm thử và dữ liệu giả.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

try:
    import sqlcipher3.dbapi2 as sqlcipher
except ImportError:  # máy phát triển chưa cài sqlcipher3-wheels
    sqlcipher = None

SCHEMA_VERSION = 2
_SCHEMA_FILE = Path(__file__).with_name("schema.sql")
_DAU_SQLITE = b"SQLite format 3\x00"

LOI_CSDL: tuple = (sqlite3.Error,) + ((sqlcipher.Error,) if sqlcipher else ())
LOI_TRUNG: tuple = (sqlite3.IntegrityError,) + ((sqlcipher.IntegrityError,) if sqlcipher else ())


class SaiKhoa(Exception):
    pass


def _pragma_khoa(khoa: bytes) -> str:
    return f"PRAGMA key = \"x'{khoa.hex()}'\""


def mo_tho(duong_dan: str | Path, khoa: bytes | None = None):
    """Mở kết nối, chưa khởi tạo lược đồ. Sai khóa → SaiKhoa."""
    if khoa is None:
        conn = sqlite3.connect(str(duong_dan))
        conn.row_factory = sqlite3.Row
        return conn
    if sqlcipher is None:
        raise RuntimeError("Chưa cài sqlcipher3-wheels: không mở được CSDL mã hóa.")
    conn = sqlcipher.connect(str(duong_dan))
    conn.row_factory = sqlcipher.Row
    try:
        conn.execute("PRAGMA cipher_log_level = NONE")   # không in lỗi giải mã ra màn hình khi thử sai khóa
    except sqlcipher.Error:
        pass
    conn.execute(_pragma_khoa(khoa))
    try:
        conn.execute("SELECT count(*) FROM sqlite_master").fetchone()
    except sqlcipher.DatabaseError as e:
        conn.close()
        raise SaiKhoa("Khóa không mở được tệp CSDL này.") from e
    return conn


def ket_noi(duong_dan: str | Path, khoa: bytes | None = None):
    """Mở CSDL (tạo mới nếu chưa có) và bảo đảm lược đồ đã được tạo, nâng cấp."""
    conn = mo_tho(duong_dan, khoa)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    khoi_tao(conn)
    return conn


def _them_cot_neu_thieu(conn, bang: str, cot: str, kieu: str) -> None:
    co = {r[1] for r in conn.execute(f"PRAGMA table_info({bang})")}
    if cot not in co:
        conn.execute(f"ALTER TABLE {bang} ADD COLUMN {cot} {kieu}")


def khoi_tao(conn) -> None:
    conn.executescript(_SCHEMA_FILE.read_text(encoding="utf-8"))
    # Nâng cấp CSDL tạo từ phiên bản 1
    _them_cot_neu_thieu(conn, "nguoi_dung", "dang_dung", "INTEGER NOT NULL DEFAULT 1")
    _them_cot_neu_thieu(conn, "nguoi_dung", "phai_doi_mat_khau", "INTEGER NOT NULL DEFAULT 0")
    _them_cot_neu_thieu(conn, "nguoi_dung", "dang_nhap_cuoi", "TEXT")
    conn.execute("INSERT INTO cau_hinh(khoa, gia_tri) VALUES ('schema_version', ?) "
                 "ON CONFLICT(khoa) DO UPDATE SET gia_tri=excluded.gia_tri", (str(SCHEMA_VERSION),))
    conn.commit()


def la_tep_chua_ma_hoa(duong_dan: str | Path) -> bool:
    p = Path(duong_dan)
    if not p.exists() or p.stat().st_size == 0:
        return False
    with open(p, "rb") as f:
        return f.read(16) == _DAU_SQLITE


def ma_hoa_tep(tep_cu: str | Path, tep_moi: str | Path, khoa: bytes) -> None:
    """Chép CSDL chưa mã hóa sang tệp mới đã mã hóa (tệp cũ giữ nguyên để người dùng tự xử lý)."""
    if sqlcipher is None:
        raise RuntimeError("Chưa cài sqlcipher3-wheels.")
    if Path(tep_moi).exists():
        raise FileExistsError(str(tep_moi))
    conn = sqlcipher.connect(str(tep_cu))
    try:
        conn.execute(f"ATTACH DATABASE ? AS moi KEY \"x'{khoa.hex()}'\"", (str(tep_moi),))
        conn.execute("SELECT sqlcipher_export('moi')")
        conn.execute("DETACH DATABASE moi")
    finally:
        conn.close()
