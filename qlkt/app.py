"""Điểm khởi chạy.

    python -m qlkt.app                 # chạy thật: dữ liệu mã hóa, đăng nhập
    python -m qlkt.app --thu du-lieu/mau.db   # chế độ thử với dữ liệu giả: không mã hóa, không đăng nhập

Trình tự chạy thật:
1. Chưa có khoa.json → cài đặt lần đầu: tạo Quản trị + mật khẩu khôi phục, tạo khóa, tạo CSDL mã hóa.
   Nếu thư mục đã có CSDL cũ chưa mã hóa → chép sang CSDL mã hóa, tệp cũ đổi tên thành *.chua-ma-hoa.
2. Có khoa.json → mở khóa bằng Windows; không mở được (đổi máy, cài lại Windows) → hỏi mật khẩu khôi phục.
3. Đăng nhập (đổi mật khẩu nếu là mật khẩu tạm) → sao lưu tự động nếu đến hạn → cửa sổ chính.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from qlkt.bao_mat import khoa as kh
from qlkt.db.database import ket_noi, la_tep_chua_ma_hoa, ma_hoa_tep
from qlkt.duong_dan import MoiTruong
from qlkt.services import sao_luu, tai_khoan
from qlkt.services.nghiep_vu import LoiNghiepVu
from qlkt.ui.dang_nhap import HopThoaiCaiDatDauTien, HopThoaiDangNhap, HopThoaiDoiMatKhau, HopThoaiMatKhauKhoiPhuc
from qlkt.ui.main_window import CuaSoChinh

TIEU_DE = "QLKT Chiềng Hặc"


def _bao_loi(text: str) -> None:
    QMessageBox.critical(None, TIEU_DE, text)


def _cai_dat_lan_dau(mt: MoiTruong):
    tep = mt.tep_csdl
    if tep.exists() and not la_tep_chua_ma_hoa(tep):
        _bao_loi(f"Thư mục dữ liệu có CSDL đã mã hóa nhưng thiếu tệp khoa.json:\n{mt.du_lieu}\n\n"
                 "Chép tệp khoa-….json từ thư mục sao lưu (hoặc USB) vào đây, đổi tên thành khoa.json, rồi mở lại.")
        return None, None
    d = HopThoaiCaiDatDauTien(True)
    if not d.exec():
        return None, None
    k = d.ket_qua
    khoa = kh.tao_khoa(mt.du_lieu, k["khoi_phuc"])
    if tep.exists():   # CSDL cũ chưa mã hóa (bản thử bước 1–3)
        cu = tep.with_name(f"{tep.stem}-{datetime.now():%Y%m%d-%H%M%S}.chua-ma-hoa")
        tep.rename(cu)
        ma_hoa_tep(cu, tep, khoa)
        QMessageBox.information(None, TIEU_DE, f"Đã chuyển CSDL cũ sang dạng mã hóa.\nTệp cũ CHƯA mã hóa:\n{cu}\n\n"
                                               "Kiểm tra dữ liệu xong thì xóa tệp cũ này.")
    c = ket_noi(tep, khoa)
    if tai_khoan.chua_co_tai_khoan(c):
        tai_khoan.tao_quan_tri_dau_tien(c, k["ten_dang_nhap"], k["ho_ten"], k["mat_khau"])
    return c, khoa


def _mo_khoa(mt: MoiTruong):
    try:
        return kh.mo_khoa(mt.du_lieu)
    except kh.LoiKhoa as loi:
        ly_do = (f"{loi}\n\nNhập mật khẩu khôi phục (bản giấy niêm phong do Lãnh đạo giữ) để mở dữ liệu. "
                 "Sau khi mở, máy này sẽ tự mở được ở các lần sau.")
    for _ in range(5):
        d = HopThoaiMatKhauKhoiPhuc(ly_do)
        if not d.exec():
            return None
        try:
            return kh.mo_bang_mat_khau_khoi_phuc(mt.du_lieu, d.mat_khau)
        except kh.LoiKhoa as loi:
            ly_do = str(loi)
    return None


def _mo_csdl(mt: MoiTruong):
    if not kh.co_tep_khoa(mt.du_lieu):
        return _cai_dat_lan_dau(mt)
    khoa = _mo_khoa(mt)
    if khoa is None:
        return None, None
    c = ket_noi(mt.tep_csdl, khoa)
    if tai_khoan.chua_co_tai_khoan(c):
        d = HopThoaiCaiDatDauTien(False)
        if not d.exec():
            return None, None
        tai_khoan.tao_quan_tri_dau_tien(c, d.ket_qua["ten_dang_nhap"], d.ket_qua["ho_ten"], d.ket_qua["mat_khau"])
    return c, khoa


def _dang_nhap(c):
    d = HopThoaiDangNhap(c)
    if not d.exec():
        return None
    nd = d.nguoi_dung
    if nd.phai_doi_mat_khau:
        if not HopThoaiDoiMatKhau(c, nd, bat_buoc=True).exec():
            return None
        nd.phai_doi_mat_khau = False
    return nd


def chay_that(app: QApplication, tep: str | None) -> int:
    mt = MoiTruong.mac_dinh(tep)
    try:
        c, khoa = _mo_csdl(mt)
    except (LoiNghiepVu, kh.LoiKhoa) as e:
        _bao_loi(str(e))
        return 1
    if c is None:
        return 0
    if sao_luu.can_sao_luu_tu_dong(mt.sao_luu):
        try:
            sao_luu.sao_luu(c, khoa, mt.sao_luu, "tu-dong", mt.du_lieu)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(None, TIEU_DE, f"Sao lưu tự động khi mở bị lỗi: {e}")
    giu: dict = {}

    def mo_cua_so() -> None:
        nd = _dang_nhap(c)
        if nd is None:
            app.quit()
            return
        w = CuaSoChinh(c, nd, mt, khoa, khi_dang_xuat=mo_cua_so)
        w.resize(1280, 780)
        w.show()
        giu["w"] = w

    app.setQuitOnLastWindowClosed(False)

    def khi_dong() -> None:
        w = giu.get("w")
        if w is None or not w.dang_dang_xuat:
            app.quit()
    app.lastWindowClosed.connect(khi_dong)
    mo_cua_so()
    if "w" not in giu:
        return 0
    return app.exec()


def chay_thu(app: QApplication, tep: str) -> int:
    p = Path(tep)
    p.parent.mkdir(parents=True, exist_ok=True)
    w = CuaSoChinh(ket_noi(p), "CHẾ ĐỘ THỬ (dữ liệu giả)")
    w.resize(1280, 780)
    w.show()
    return app.exec()


def kiem_tra_ban_dong_goi(tep_ket_qua: str) -> int:
    """Dùng khi dựng bộ cài: thử mã hóa CSDL, khóa, mẫu Word, sinh văn bản trong bản đóng gói. Không mở cửa sổ."""
    import tempfile
    import traceback
    dong = []
    try:
        from qlkt.services import van_ban
        with tempfile.TemporaryDirectory() as tmp:
            khoa = kh.tao_khoa(tmp, "kiem tra 2026 abc")
            assert kh.mo_khoa(tmp) == khoa
            dong.append(f"Khoa: {'DPAPI' if sys.platform == 'win32' else 'tep'} OK")
            c = ket_noi(Path(tmp) / "t.db", khoa)
            c.execute("INSERT INTO don_vi(ten) VALUES ('Thu')"); c.commit()
            assert not la_tep_chua_ma_hoa(Path(tmp) / "t.db")
            dong.append("SQLCipher: OK " + c.execute("PRAGMA cipher_version").fetchone()[0])
            for ten in ("to_trinh.docx", "quyet_dinh.docx"):
                assert (van_ban.thu_muc_mau() / ten).exists(), ten
            dong.append(f"Mau Word: OK ({van_ban.thu_muc_mau()})")
            b = sao_luu.sao_luu(c, khoa, Path(tmp) / "sl", "tay", tmp)
            sao_luu.kiem_tra_ban_sao(b, khoa)
            dong.append("Sao luu: OK")
            c.close()
        ma = 0
    except Exception:  # noqa: BLE001
        dong.append(traceback.format_exc())
        ma = 1
    Path(tep_ket_qua).write_text("\n".join(dong), encoding="utf-8")
    return ma


def main() -> int:
    if len(sys.argv) > 2 and sys.argv[1] == "--kiem-tra":
        return kiem_tra_ban_dong_goi(sys.argv[2])
    app = QApplication(sys.argv)
    app.setApplicationName(TIEU_DE)
    args = sys.argv[1:]
    if args and args[0] == "--thu":
        return chay_thu(app, args[1] if len(args) > 1 else "du-lieu/mau.db")
    return chay_that(app, args[0] if args else None)


if __name__ == "__main__":
    sys.exit(main())
