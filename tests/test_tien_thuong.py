from qlkt.db.database import ket_noi
from qlkt.services.tien_thuong import doc_so_tien, luong_co_so_tai, tinh_tien


def test_doc_so_tien_mau_thuc_te():
    # Tổng tiền trong mẫu danh sách chi trả 8/2026
    assert doc_so_tien(5_608_000) == "Năm triệu sáu trăm linh tám nghìn đồng"


def test_doc_so_tien_cac_truong_hop():
    assert doc_so_tien(759_000) == "Bảy trăm năm mươi chín nghìn đồng"
    assert doc_so_tien(1_518_000) == "Một triệu năm trăm mười tám nghìn đồng"
    assert doc_so_tien(8_349_000) == "Tám triệu ba trăm bốn mươi chín nghìn đồng"
    assert doc_so_tien(1_000_005) == "Một triệu không trăm linh năm đồng"
    assert doc_so_tien(21_000) == "Hai mươi mốt nghìn đồng"
    assert doc_so_tien(15_000) == "Mười lăm nghìn đồng"
    assert doc_so_tien(24_000) == "Hai mươi tư nghìn đồng"


def test_tinh_tien_theo_mau():
    assert tinh_tien(0.3, 2_530_000) == 759_000
    assert tinh_tien(0.6, 2_530_000) == 1_518_000
    assert tinh_tien(0.3, 2_340_000) == 702_000
    assert tinh_tien(None, 2_530_000) is None


def test_luong_co_so_theo_thoi_diem(tmp_path):
    conn = ket_noi(tmp_path / "t.db")
    conn.execute("INSERT INTO luong_co_so(ap_dung_tu, muc) VALUES ('2024-07-01', 2340000)")
    conn.execute("INSERT INTO luong_co_so(ap_dung_tu, muc) VALUES ('2026-10-01', 2530000)")
    assert luong_co_so_tai(conn, "2026-08-15") == 2_340_000
    assert luong_co_so_tai(conn, "2026-11-26") == 2_530_000
    assert luong_co_so_tai(conn, "2020-01-01") is None


def test_nhat_ky_khong_xoa_duoc(tmp_path):
    import sqlite3
    import pytest
    conn = ket_noi(tmp_path / "t.db")
    conn.execute("INSERT INTO nhat_ky(hanh_dong) VALUES ('thu')")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM nhat_ky")
