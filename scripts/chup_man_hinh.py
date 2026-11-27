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
print("Đã chụp", len(CuaSoChinh.TRANG), "màn hình vào", ra)
