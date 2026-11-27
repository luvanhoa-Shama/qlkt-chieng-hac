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


def _nut_hien(w, chu: str) -> bool:
    return any(b.text() == chu and b.isVisibleTo(w) for b in w.findChildren(QtWidgets.QPushButton))


def test_giao_dien_theo_vai_tro(app, nv, tmp_path):
    from qlkt.duong_dan import MoiTruong
    from qlkt.services import tai_khoan
    c = nv.c
    qt = tai_khoan.tao_quan_tri_dau_tien(c, "quantri", "Quản trị", "quantri123")
    ld_id = tai_khoan.them_nguoi_dung(c, qt.id, "lanhdao", "Lãnh đạo", "lanh_dao", "tam12345")
    kt_id = tai_khoan.them_nguoi_dung(c, qt.id, "ketoan", "Kế toán", "ke_toan", "tam12345")
    mt = MoiTruong(tmp_path / "du", tmp_path / "sl"); mt.du_lieu.mkdir(); mt.sao_luu.mkdir()

    ld = tai_khoan.dang_nhap(c, "lanhdao", "tam12345")
    w = CuaSoChinh(c, ld, mt, None)
    assert w.menu.count() == len(CuaSoChinh.TRANG)           # không có trang Quản trị
    assert not _nut_hien(w, "+ Hồ sơ mới") and not _nut_hien(w, "Danh sách chi trả (Excel)")
    w.menu.setCurrentRow(1); app.processEvents()
    assert not _nut_hien(w, "Trình (nhập số Tờ trình)…")      # trang gọi setVisible(True) vẫn bị chặn
    w.hen_gio.stop(); w.close()

    kt = tai_khoan.dang_nhap(c, "ketoan", "tam12345")
    w = CuaSoChinh(c, kt, mt, None)
    assert w.menu.item(w.menu.count() - 1).text() == "Quản trị"  # kế toán được sao lưu
    assert not _nut_hien(w, "+ Thêm tài khoản") and not _nut_hien(w, "Khôi phục bản đã chọn…")
    w.hen_gio.stop(); w.close()

    q = tai_khoan.dang_nhap(c, "quantri", "quantri123")
    w = CuaSoChinh(c, q, mt, None)
    w.menu.setCurrentRow(w.menu.count() - 1); app.processEvents()
    assert _nut_hien(w, "+ Thêm tài khoản") and _nut_hien(w, "Khôi phục bản đã chọn…")
    assert w.stack.currentWidget().ds_tk.rowCount() == 3
    w.close()                                                  # thoát → sao lưu tự động
    assert len(list(mt.sao_luu.glob("qlkt-tu-dong-*.db"))) >= 1
    assert ld_id and kt_id


def test_hop_thoai_dang_nhap(app, nv):
    from qlkt.services import tai_khoan
    from qlkt.ui.dang_nhap import HopThoaiCaiDatDauTien, HopThoaiDangNhap
    tai_khoan.tao_quan_tri_dau_tien(nv.c, "quantri", "Quản trị", "quantri123")
    d = HopThoaiDangNhap(nv.c)
    d.ten.setText("quantri"); d.mk.setText("quantri123"); d._thu()
    assert d.nguoi_dung and d.nguoi_dung.vai_tro == "quan_tri"
    cd = HopThoaiCaiDatDauTien(True)
    cd.ho_ten.setText("A"); cd.ten.setText("a"); cd.mk.setText("abc12345"); cd.mk2.setText("abc12345")
    cd.kp.setText("khoi phuc 2026 x"); cd.kp2.setText("khoi phuc 2026 x"); cd.da_ghi.setChecked(True)
    cd._kiem()
    assert cd.ket_qua["khoi_phuc"] == "khoi phuc 2026 x"
