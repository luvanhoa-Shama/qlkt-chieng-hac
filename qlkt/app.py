"""Điểm khởi chạy: python -m qlkt.app [đường_dẫn_csdl]"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from qlkt.db.database import ket_noi
from qlkt.ui.main_window import CuaSoChinh


def main() -> int:
    duong_dan = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("du-lieu/qlkt.db")
    duong_dan.parent.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)
    app.setApplicationName("QLKT Chiềng Hặc")
    cua_so = CuaSoChinh(ket_noi(duong_dan), "Thường trực TĐKT")
    cua_so.resize(1280, 780)
    cua_so.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
