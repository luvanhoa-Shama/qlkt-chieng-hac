"""Hộp thoại nhập liệu dùng chung."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPlainTextEdit, QVBoxLayout, QWidget,
)


@dataclass
class Truong:
    khoa: str
    nhan: str
    kieu: str = "text"          # text | so | so_thuc | ngay | chon | nhieu_dong | co_khong | mat_khau
    bat_buoc: bool = False
    lua_chon: list[tuple[str, object]] = field(default_factory=list)   # (nhãn, giá trị) cho kieu=chon
    goi_y: str = ""


def ngay_sang_iso(s: str) -> str | None:
    s = (s or "").strip()
    if not s:
        return None
    m = re.fullmatch(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})", s)
    if not m:
        raise ValueError
    d, mth, y = map(int, m.groups())
    return date(y, mth, d).isoformat()


def iso_sang_ngay(s: str | None) -> str:
    if not s:
        return ""
    y, m, d = s[:10].split("-")
    return f"{d}/{m}/{y}"


class HopThoaiNhap(QDialog):
    """Hộp thoại form chung. Kết quả: self.ket_qua (dict) khi bấm Lưu."""

    def __init__(self, tieu_de: str, truong: list[Truong], gia_tri: dict | None = None,
                 parent: QWidget | None = None, ghi_chu: str = ""):
        super().__init__(parent)
        self.setWindowTitle(tieu_de)
        self.setMinimumWidth(520)
        self.truong = truong
        self.o: dict[str, QWidget] = {}
        self.ket_qua: dict = {}
        gia_tri = gia_tri or {}
        v = QVBoxLayout(self)
        if ghi_chu:
            lb = QLabel(ghi_chu); lb.setWordWrap(True); lb.setStyleSheet("color:#57606a")
            v.addWidget(lb)
        f = QFormLayout()
        for t in truong:
            gt = gia_tri.get(t.khoa)
            if t.kieu == "chon":
                w = QComboBox()
                for nhan, val in t.lua_chon:
                    w.addItem(nhan, val)
                i = w.findData(gt)
                if i >= 0:
                    w.setCurrentIndex(i)
            elif t.kieu == "nhieu_dong":
                w = QPlainTextEdit("" if gt is None else str(gt)); w.setFixedHeight(70)
            elif t.kieu == "co_khong":
                w = QCheckBox(); w.setChecked(bool(gt))
            else:
                w = QLineEdit(iso_sang_ngay(gt) if t.kieu == "ngay" else ("" if gt is None else str(gt)))
                if t.kieu == "mat_khau":
                    w.setEchoMode(QLineEdit.Password)
                w.setPlaceholderText(t.goi_y or ("dd/mm/yyyy" if t.kieu == "ngay" else ""))
            self.o[t.khoa] = w
            f.addRow(t.nhan + (" *" if t.bat_buoc else ""), w)
        v.addLayout(f)
        nut = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        nut.button(QDialogButtonBox.Save).setText("Lưu")
        nut.button(QDialogButtonBox.Cancel).setText("Hủy")
        nut.accepted.connect(self._luu)
        nut.rejected.connect(self.reject)
        v.addWidget(nut)

    def _luu(self) -> None:
        kq: dict = {}
        for t in self.truong:
            w = self.o[t.khoa]
            try:
                if t.kieu == "chon":
                    val = w.currentData()
                elif t.kieu == "nhieu_dong":
                    val = w.toPlainText().strip() or None
                elif t.kieu == "co_khong":
                    val = 1 if w.isChecked() else 0
                else:
                    s = w.text().strip()
                    if t.kieu == "ngay":
                        val = ngay_sang_iso(s)
                    elif t.kieu == "so":
                        val = int(s.replace(".", "").replace(",", "")) if s else None
                    elif t.kieu == "so_thuc":
                        val = float(s.replace(",", ".")) if s else None
                    else:
                        val = s or None
            except ValueError:
                QMessageBox.warning(self, "Sai định dạng", f"\"{t.nhan}\" không đúng định dạng.")
                w.setFocus()
                return
            if t.bat_buoc and val in (None, ""):
                QMessageBox.warning(self, "Thiếu thông tin", f"Chưa nhập \"{t.nhan}\".")
                w.setFocus()
                return
            kq[t.khoa] = val
        self.ket_qua = kq
        self.accept()


class HopThoaiChonNhieu(QDialog):
    """Danh sách có ô đánh dấu. Kết quả: self.da_chon (set giá trị)."""

    def __init__(self, tieu_de: str, huong_dan: str, muc: list[tuple[str, object, bool]],
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(tieu_de)
        self.setMinimumWidth(480)
        v = QVBoxLayout(self)
        lb = QLabel(huong_dan); lb.setWordWrap(True)
        v.addWidget(lb)
        self.ds = QListWidget()
        for nhan, val, chon in muc:
            it = QListWidgetItem(nhan)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if chon else Qt.Unchecked)
            it.setData(Qt.UserRole, val)
            self.ds.addItem(it)
        v.addWidget(self.ds)
        nut = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        nut.button(QDialogButtonBox.Ok).setText("Đồng ý")
        nut.button(QDialogButtonBox.Cancel).setText("Hủy")
        nut.accepted.connect(self.accept)
        nut.rejected.connect(self.reject)
        v.addWidget(nut)

    @property
    def da_chon(self) -> set:
        return {self.ds.item(i).data(Qt.UserRole) for i in range(self.ds.count())
                if self.ds.item(i).checkState() == Qt.Checked}
