"""Kiểm thử khói giao diện (chạy không cần màn hình)."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")

from qlkt.ui.hop_thoai import HopThoaiNhap, Truong  # noqa: E402
from qlkt.ui.main_window import CuaSoChinh  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_mo_tat_ca_trang(app, nv):
    a = nv.them_doi_tuong({"loai": "ca_nhan", "ten": "A"})
    hs = nv.tao_ho_so({"don_vi_id": 1, "hinh_thuc_id": 1, "trich_yeu": "X"})
    nv.them_vao_ho_so(hs, a)
    w = CuaSoChinh(nv.c, "test")
    for i in range(len(CuaSoChinh.TRANG)):
        w.menu.setCurrentRow(i)
        app.processEvents()
    trang_hs = w.stack.widget(1)
    assert trang_hs.hs_id == hs
    assert trang_hs.ds_dt.rowCount() == 1
    assert trang_hs.nut_luong["da_trinh"].isVisibleTo(trang_hs)
    assert not trang_hs.nut_luong["da_co_qd"].isVisibleTo(trang_hs)


def test_form_kiem_tra_dinh_dang(app):
    d = HopThoaiNhap("t", [Truong("ten", "Tên", bat_buoc=True), Truong("ngay", "Ngày", "ngay"),
                           Truong("so", "Số", "so"), Truong("hs", "Hệ số", "so_thuc")])
    d.o["ten"].setText(" A ")
    d.o["ngay"].setText("5/8/2026")
    d.o["so"].setText("2.530.000")
    d.o["hs"].setText("0,3")
    d._luu()
    assert d.ket_qua == {"ten": "A", "ngay": "2026-08-05", "so": 2530000, "hs": 0.3}
