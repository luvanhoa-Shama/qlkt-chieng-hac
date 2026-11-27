"""Chụp các màn hình mẫu ra PNG (dùng dữ liệu giả). Chạy: python scripts/chup_man_hinh.py thu_muc_ra"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QLKT_HOM_NAY", "2026-11-27")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtGui import QFont  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from qlkt.db.database import ket_noi  # noqa: E402
from qlkt.ui.main_window import CuaSoChinh  # noqa: E402
from tao_du_lieu_mau import tao  # noqa: E402

ra = Path(sys.argv[1] if len(sys.argv) > 1 else "anh-man-hinh")
ra.mkdir(parents=True, exist_ok=True)
db = Path(tempfile.mkdtemp()) / "mau.db"
tao(db)
app = QApplication(sys.argv)
app.setFont(QFont("DejaVu Sans", 9))
w = CuaSoChinh(ket_noi(db), "Thường trực TĐKT (mẫu)")
w.resize(1280, 760)
w.show()
for i, (ten, _) in enumerate(CuaSoChinh.TRANG):
    w.menu.setCurrentRow(i)
    app.processEvents()
    if i == 1:  # Hồ sơ: chọn hồ sơ "Đã trình" cho có nhiều dòng
        w.stack.currentWidget().ds.selectRow(2)
    if i == 2:  # Đối tượng: chọn người đã có lịch sử khen thưởng
        w.stack.currentWidget().ds.selectRow(1)
        app.processEvents()
    w.grab().save(str(ra / f"{i + 1}-{ten.replace(' ', '-').replace(',', '')}.png"))
# Hộp thoại mẫu
trang_hs = w.stack.widget(1)
w.menu.setCurrentRow(1)
from qlkt.ui.hop_thoai import HopThoaiNhap  # noqa: E402
d = HopThoaiNhap("Hồ sơ mới", trang_hs._truong_ho_so(), parent=w)
d.show(); app.processEvents()
d.grab().save(str(ra / "7-Hop-thoai-ho-so-moi.png"))
d.close()
from qlkt.ui.main_window import TrangDoiTuong  # noqa: E402
d = HopThoaiNhap("Thêm tập thể/cá nhân", TrangDoiTuong.truong(w.nv.c), parent=w,
                 ghi_chu="Không nhập CCCD. Số tài khoản là dữ liệu cá nhân, chỉ nhập khi cần chi trả.")
d.show(); app.processEvents()
d.grab().save(str(ra / "8-Hop-thoai-doi-tuong.png"))
print("Đã chụp", len(CuaSoChinh.TRANG), "màn hình vào", ra)

# Bước 4: cài đặt lần đầu, đăng nhập, trang Quản trị (tài khoản giả, thư mục tạm)
from qlkt.duong_dan import MoiTruong  # noqa: E402
from qlkt.services import sao_luu, tai_khoan  # noqa: E402
from qlkt.ui.dang_nhap import HopThoaiCaiDatDauTien, HopThoaiDangNhap  # noqa: E402

d = HopThoaiCaiDatDauTien(True); d.show(); app.processEvents()
d.grab().save(str(ra / "9-Cai-dat-lan-dau.png")); d.close()
c = ket_noi(db)
qt = tai_khoan.tao_quan_tri_dau_tien(c, "quantri", "Quản trị (mẫu)", "quantri123")
tai_khoan.them_nguoi_dung(c, qt.id, "thuongtruc2", "Cán bộ thường trực (mẫu)", "thuong_truc", "tam12345")
tai_khoan.them_nguoi_dung(c, qt.id, "ketoan", "Kế toán (mẫu)", "ke_toan", "tam12345")
tai_khoan.them_nguoi_dung(c, qt.id, "lanhdao", "Lãnh đạo UBND (mẫu)", "lanh_dao", "tam12345")
d = HopThoaiDangNhap(c); d.show(); app.processEvents()
d.grab().save(str(ra / "10-Dang-nhap.png")); d.close()
tam = Path(tempfile.mkdtemp())
mt = MoiTruong(tam / "du-lieu", tam / "sao-luu"); mt.du_lieu.mkdir(); mt.sao_luu.mkdir()
sao_luu.sao_luu(c, None, mt.sao_luu, "tu-dong")
sao_luu.sao_luu(c, None, mt.sao_luu, "tay")
w2 = CuaSoChinh(c, tai_khoan.dang_nhap(c, "quantri", "quantri123"), mt, None)
w2.resize(1280, 760); w2.show()
w2.menu.setCurrentRow(w2.menu.count() - 1); app.processEvents()
w2.grab().save(str(ra / "11-Quan-tri.png"))
w3 = CuaSoChinh(c, tai_khoan.dang_nhap(c, "lanhdao", "tam12345"), mt, None)
w3.resize(1280, 760); w3.show(); w3.menu.setCurrentRow(1); app.processEvents()
w3.stack.currentWidget().ds.selectRow(2); app.processEvents()
w3.grab().save(str(ra / "12-Lanh-dao-chi-xem.png"))
print("Đã chụp thêm màn hình bước 4")
