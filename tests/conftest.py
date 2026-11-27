import pytest

from qlkt.db.database import ket_noi
from qlkt.services.nghiep_vu import NghiepVu


@pytest.fixture
def nv(tmp_path):
    c = ket_noi(tmp_path / "t.db")
    c.execute("INSERT INTO don_vi(ten) VALUES ('Ban Chỉ huy Quân sự xã')")
    c.execute("INSERT INTO hinh_thuc(ten, he_so_ca_nhan, he_so_tap_the) VALUES ('Giấy khen', 0.3, 0.6)")
    c.execute("INSERT INTO luong_co_so(ap_dung_tu, muc) VALUES ('2024-07-01', 2340000)")
    c.execute("INSERT INTO luong_co_so(ap_dung_tu, muc) VALUES ('2026-10-01', 2530000)")
    c.execute("INSERT INTO phong_trao(ten, nam, han_nop_ho_so) VALUES ('Quốc phòng', 2026, '2026-11-30')")
    c.commit()
    return NghiepVu(c, None)
