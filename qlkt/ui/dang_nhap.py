"""Hộp thoại: cài đặt lần đầu, đăng nhập, đổi mật khẩu, mật khẩu khôi phục, khóa phiên."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QLabel, QLineEdit, QMessageBox, QPushButton,
    QVBoxLayout, QWidget,
)

from qlkt.bao_mat.mat_khau import loi_mat_khau
from qlkt.services import tai_khoan
from qlkt.services.nghiep_vu import LoiNghiepVu

TEN_PHAN_MEM = "Quản lý thi đua – khen thưởng · UBND xã Chiềng Hặc"


def _o_mat_khau(goi_y: str = "") -> QLineEdit:
    o = QLineEdit(); o.setEchoMode(QLineEdit.Password)
    if goi_y:
        o.setPlaceholderText(goi_y)
    return o


def _ghi_chu(text: str, mau: str = "#57606a") -> QLabel:
    lb = QLabel(text); lb.setWordWrap(True); lb.setStyleSheet(f"color:{mau}")
    return lb


def _nut(bb: QDialogButtonBox, ok: str, huy: str | None = "Hủy") -> None:
    bb.button(QDialogButtonBox.Ok).setText(ok)
    if huy and bb.button(QDialogButtonBox.Cancel):
        bb.button(QDialogButtonBox.Cancel).setText(huy)


class HopThoaiCaiDatDauTien(QDialog):
    """Tạo tài khoản Quản trị và (nếu cần) mật khẩu khôi phục. Kết quả ở self.ket_qua."""

    def __init__(self, can_mat_khau_khoi_phuc: bool = True, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Cài đặt lần đầu")
        self.setMinimumWidth(560)
        self.can_kp = can_mat_khau_khoi_phuc
        self.ket_qua: dict = {}
        v = QVBoxLayout(self)
        v.addWidget(QLabel(f"<b>{TEN_PHAN_MEM}</b>"))
        g1 = QGroupBox("1. Tài khoản Quản trị hệ thống")
        f1 = QFormLayout(g1)
        self.ho_ten = QLineEdit(); self.ten = QLineEdit(); self.ten.setPlaceholderText("VD: quantri")
        self.mk, self.mk2 = _o_mat_khau("Ít nhất 8 ký tự, có chữ và số"), _o_mat_khau()
        f1.addRow("Họ tên *", self.ho_ten); f1.addRow("Tên đăng nhập *", self.ten)
        f1.addRow("Mật khẩu *", self.mk); f1.addRow("Nhập lại *", self.mk2)
        v.addWidget(g1)
        if self.can_kp:
            g2 = QGroupBox("2. Mật khẩu khôi phục dữ liệu")
            f2 = QFormLayout(g2)
            f2.addRow(_ghi_chu(
                "Dữ liệu được mã hóa. Khi cài lại Windows, đổi máy hoặc khôi phục bản sao lưu trên máy khác, "
                "phải có mật khẩu này mới mở được. <b>Mất mật khẩu này và hỏng máy = mất dữ liệu.</b> "
                "Ghi ra giấy, niêm phong, giao Lãnh đạo giữ; không lưu trong máy tính, không gửi qua mạng.",
                "#9a3412"))
            self.kp, self.kp2 = _o_mat_khau("Ít nhất 12 ký tự, có chữ và số"), _o_mat_khau()
            f2.addRow("Mật khẩu khôi phục *", self.kp); f2.addRow("Nhập lại *", self.kp2)
            self.da_ghi = QCheckBox("Tôi đã ghi mật khẩu khôi phục ra giấy và sẽ niêm phong, bàn giao.")
            f2.addRow(self.da_ghi)
            v.addWidget(g2)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        _nut(bb, "Tạo", "Thoát")
        bb.accepted.connect(self._kiem); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def _kiem(self) -> None:
        loi = None
        if not self.ho_ten.text().strip() or not self.ten.text().strip():
            loi = "Chưa nhập họ tên hoặc tên đăng nhập."
        elif self.mk.text() != self.mk2.text():
            loi = "Hai lần nhập mật khẩu không khớp."
        else:
            loi = loi_mat_khau(self.mk.text())
        if not loi and self.can_kp:
            if self.kp.text() != self.kp2.text():
                loi = "Hai lần nhập mật khẩu khôi phục không khớp."
            elif self.kp.text() == self.mk.text():
                loi = "Mật khẩu khôi phục phải khác mật khẩu đăng nhập."
            else:
                loi = loi_mat_khau(self.kp.text(), 12)
                if not loi and not self.da_ghi.isChecked():
                    loi = "Hãy ghi mật khẩu khôi phục ra giấy rồi đánh dấu xác nhận."
        if loi:
            QMessageBox.warning(self, "Chưa hợp lệ", loi)
            return
        self.ket_qua = {"ho_ten": self.ho_ten.text().strip(), "ten_dang_nhap": self.ten.text().strip(),
                        "mat_khau": self.mk.text(), "khoi_phuc": self.kp.text() if self.can_kp else None}
        self.accept()


class HopThoaiDangNhap(QDialog):
    """Đăng nhập. Kết quả: self.nguoi_dung. co_dinh: chỉ cho người này (mở khóa phiên)."""

    def __init__(self, c, co_dinh: tai_khoan.NguoiDung | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.c = c
        self.co_dinh = co_dinh
        self.nguoi_dung: tai_khoan.NguoiDung | None = None
        self.dang_xuat = False
        self.setWindowTitle("Mở khóa phiên làm việc" if co_dinh else "Đăng nhập")
        self.setMinimumWidth(400)
        v = QVBoxLayout(self)
        v.addWidget(QLabel(f"<b>{TEN_PHAN_MEM}</b>"))
        if co_dinh:
            v.addWidget(_ghi_chu("Phiên làm việc đã khóa do lâu không thao tác. Nhập mật khẩu để tiếp tục."))
        f = QFormLayout()
        self.ten = QLineEdit(co_dinh.ten_dang_nhap if co_dinh else "")
        self.ten.setEnabled(co_dinh is None)
        self.mk = _o_mat_khau()
        f.addRow("Tên đăng nhập", self.ten); f.addRow("Mật khẩu", self.mk)
        v.addLayout(f)
        v.addWidget(_ghi_chu("Quên mật khẩu: liên hệ Quản trị để đặt lại. Sai 5 lần, tài khoản sẽ bị khóa."))
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        _nut(bb, "Đăng nhập" if not co_dinh else "Mở khóa", "Thoát" if not co_dinh else None)
        if co_dinh:
            bb.removeButton(bb.button(QDialogButtonBox.Cancel))
            b = QPushButton("Đăng xuất"); bb.addButton(b, QDialogButtonBox.RejectRole)
            b.clicked.connect(self._dang_xuat)
        else:
            bb.rejected.connect(self.reject)
        bb.accepted.connect(self._thu)
        v.addWidget(bb)
        (self.mk if co_dinh else self.ten).setFocus()

    def _dang_xuat(self) -> None:
        self.dang_xuat = True
        self.reject()

    def _thu(self) -> None:
        try:
            nd = tai_khoan.dang_nhap(self.c, self.ten.text(), self.mk.text())
        except LoiNghiepVu as e:
            QMessageBox.warning(self, "Không đăng nhập được", str(e))
            self.mk.clear(); self.mk.setFocus()
            return
        self.nguoi_dung = nd
        self.accept()

    def keyPressEvent(self, e):  # Esc khi khóa phiên không được bỏ qua màn khóa
        if self.co_dinh and e.key() == Qt.Key_Escape:
            return
        super().keyPressEvent(e)


class HopThoaiDoiMatKhau(QDialog):
    def __init__(self, c, nd: tai_khoan.NguoiDung, bat_buoc: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self.c, self.nd = c, nd
        self.setWindowTitle("Đổi mật khẩu")
        self.setMinimumWidth(420)
        v = QVBoxLayout(self)
        if bat_buoc:
            v.addWidget(_ghi_chu("Đây là mật khẩu tạm do Quản trị cấp. Anh/chị cần đặt mật khẩu mới để tiếp tục.",
                                 "#9a3412"))
        f = QFormLayout()
        self.cu, self.moi, self.moi2 = _o_mat_khau(), _o_mat_khau("Ít nhất 8 ký tự, có chữ và số"), _o_mat_khau()
        f.addRow("Mật khẩu hiện tại", self.cu); f.addRow("Mật khẩu mới", self.moi); f.addRow("Nhập lại", self.moi2)
        v.addLayout(f)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        _nut(bb, "Đổi", "Thoát" if bat_buoc else "Hủy")
        bb.accepted.connect(self._doi); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def _doi(self) -> None:
        if self.moi.text() != self.moi2.text():
            QMessageBox.warning(self, "Chưa hợp lệ", "Hai lần nhập mật khẩu mới không khớp.")
            return
        try:
            tai_khoan.doi_mat_khau(self.c, self.nd.id, self.cu.text(), self.moi.text())
        except LoiNghiepVu as e:
            QMessageBox.warning(self, "Không đổi được", str(e))
            return
        QMessageBox.information(self, "Đã đổi", "Đã đổi mật khẩu.")
        self.accept()


class HopThoaiMatKhauKhoiPhuc(QDialog):
    """Hỏi mật khẩu khôi phục. Kết quả: self.mat_khau."""

    def __init__(self, ly_do: str, parent: QWidget | None = None, dat_moi: bool = False):
        super().__init__(parent)
        self.dat_moi = dat_moi
        self.mat_khau = ""
        self.setWindowTitle("Đặt mật khẩu khôi phục mới" if dat_moi else "Mật khẩu khôi phục")
        self.setMinimumWidth(460)
        v = QVBoxLayout(self)
        v.addWidget(_ghi_chu(ly_do))
        f = QFormLayout()
        self.mk = _o_mat_khau("Ít nhất 12 ký tự, có chữ và số" if dat_moi else "")
        f.addRow("Mật khẩu khôi phục" + (" mới" if dat_moi else ""), self.mk)
        if dat_moi:
            self.mk2 = _o_mat_khau(); f.addRow("Nhập lại", self.mk2)
        v.addLayout(f)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        _nut(bb, "Đồng ý")
        bb.accepted.connect(self._ok); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def _ok(self) -> None:
        if self.dat_moi:
            loi = ("Hai lần nhập không khớp." if self.mk.text() != self.mk2.text()
                   else loi_mat_khau(self.mk.text(), 12))
            if loi:
                QMessageBox.warning(self, "Chưa hợp lệ", loi)
                return
        if not self.mk.text():
            return
        self.mat_khau = self.mk.text()
        self.accept()
