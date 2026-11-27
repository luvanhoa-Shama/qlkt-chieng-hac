"""Cửa sổ chính và các trang nghiệp vụ."""
from __future__ import annotations

import os
import sqlite3
from datetime import date
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QCompleter, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
    QMainWindow, QMessageBox, QPushButton, QSplitter, QStackedWidget, QTableWidget, QTableWidgetItem,
    QTabWidget, QVBoxLayout, QWidget,
)

from qlkt.bao_mat.phan_quyen import che_stk, co_quyen
from qlkt.db.database import LOI_CSDL
from qlkt.services import excel_mau, sao_luu, van_ban
from qlkt.services.nghiep_vu import CHUYEN_TRANG_THAI, LoiNghiepVu, NghiepVu, ten_hien_thi
from qlkt.ui.hop_thoai import HopThoaiChonNhieu, HopThoaiNhap, Truong

TRANG_THAI = {
    "tiep_nhan": "Mới tiếp nhận",
    "tra_lai": "Trả lại bổ sung",
    "da_trinh": "Đã trình",
    "da_co_qd": "Đã có quyết định",
    "khong_duyet": "Không được duyệt",
}
MAU_TRANG_THAI = {
    "tiep_nhan": "#1f6feb", "tra_lai": "#c2410c", "da_trinh": "#7c3aed",
    "da_co_qd": "#15803d", "khong_duyet": "#6b7280",
}
LOAI_DT = [("Cá nhân", "ca_nhan"), ("Tập thể", "tap_the")]

STYLE = """
QMainWindow, QWidget { font-size: 10pt; }
#sidebar { background: #12355b; border: none; color: white; font-size: 11pt; }
#sidebar::item { padding: 10px 14px; }
#sidebar::item:selected { background: #1f5fa0; }
#tieuDe { font-size: 15pt; font-weight: bold; color: #12355b; }
#the { background: white; border: 1px solid #d0d7de; border-radius: 6px; }
#soLon { font-size: 20pt; font-weight: bold; }
#nhan { color: #57606a; }
#canhBao { background: #fff8c5; border: 1px solid #d4a72c; border-radius: 4px; padding: 6px; }
QTableWidget { background: white; gridline-color: #e5e7eb; }
QHeaderView::section { background: #eef2f7; padding: 4px; border: none; font-weight: bold; }
QPushButton { padding: 5px 12px; }
QPushButton#chinh { background: #1f5fa0; color: white; border-radius: 3px; }
QPushButton#chinh:disabled { background: #9db5cf; }
"""


def hom_nay() -> str:
    # Cho phép đặt ngày cố định khi chụp màn hình mẫu
    return os.environ.get("QLKT_HOM_NAY") or date.today().isoformat()


def ngay_vn(iso: str | None) -> str:
    if not iso:
        return ""
    y, m, d = iso[:10].split("-")
    return f"{d}/{m}/{y}"


def tien(so: int | None) -> str:
    return "" if so is None else f"{so:,}".replace(",", ".")


def bang(cot: list[str], gian: int | None = None) -> QTableWidget:
    """gian: cột được kéo giãn chiếm phần còn lại (mặc định cột cuối)."""
    t = QTableWidget(0, len(cot))
    t.setHorizontalHeaderLabels(cot)
    t.verticalHeader().setVisible(False)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setSelectionMode(QAbstractItemView.SingleSelection)
    t.setAlternatingRowColors(True)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    if gian is None:
        t.horizontalHeader().setStretchLastSection(True)
    else:
        t.horizontalHeader().setSectionResizeMode(gian, QHeaderView.Stretch)
    return t


def do_du_lieu(t: QTableWidget, rows: list[list], du_lieu_an: list | None = None) -> None:
    t.setRowCount(0)
    for i, r in enumerate(rows):
        t.insertRow(i)
        for j, v in enumerate(r):
            item = v if isinstance(v, QTableWidgetItem) else QTableWidgetItem("" if v is None else str(v))
            if j == 0 and du_lieu_an is not None:
                item.setData(Qt.UserRole, du_lieu_an[i])
            t.setItem(i, j, item)


def id_dang_chon(t: QTableWidget):
    sel = t.selectedItems()
    return t.item(sel[0].row(), 0).data(Qt.UserRole) if sel else None


def o_trang_thai(ma: str) -> QTableWidgetItem:
    it = QTableWidgetItem(TRANG_THAI.get(ma, ma))
    it.setForeground(QColor(MAU_TRANG_THAI.get(ma, "#000")))
    f = QFont(); f.setBold(True); it.setFont(f)
    return it


def tieu_de(text: str) -> QLabel:
    lb = QLabel(text); lb.setObjectName("tieuDe")
    return lb


# Nút cần quyền (theo chữ trên nút). Tầng nghiệp vụ vẫn kiểm tra lại; ẩn nút để giao diện gọn, đúng vai trò.
QUYEN_NUT = {
    **dict.fromkeys(["+ Thêm hạn công việc", "Đánh dấu đã xong", "Tạo mới…", "Nhập hồ sơ từ Excel…", "+ Hồ sơ mới",
                     "Sửa thông tin", "Xóa", "+ Thêm tập thể/cá nhân", "Sửa thành tích/tiền", "Bỏ khỏi hồ sơ",
                     "+ Thêm", "+ Phong trào mới", "Xuất mẫu Excel gửi các phòng…"], "sua_du_lieu"),
    "Sửa": "sua_stk",   # trang Cá nhân, tập thể: kế toán sửa được số tài khoản
    **dict.fromkeys(["Trả lại bổ sung…", "Nhận lại hồ sơ đã bổ sung", "Trình (nhập số Tờ trình)…", "Nhập Quyết định…",
                     "Không được duyệt…"], "luong_ho_so"),
    **dict.fromkeys(["Tờ trình (Word)", "Dự thảo QĐ + danh sách (Word)", "Danh sách đề nghị (Excel)",
                     "Xuất báo cáo Excel…", "Xuất dữ liệu liên thông (CSV/JSON)…"], "xuat_van_ban"),
    "Danh sách chi trả (Excel)": "xuat_chi_tra",
    "Sửa thông tin cơ quan…": "danh_muc",
}
_vai_tro_hien_tai: list[str | None] = [None]   # đặt bởi CuaSoChinh trước khi dựng các trang


class _NutAn(QPushButton):
    """Nút của chức năng tài khoản không có quyền: luôn ẩn, kể cả khi trang gọi setVisible(True)."""

    def setVisible(self, _v: bool) -> None:  # noqa: N802 - tên hàm của Qt
        super().setVisible(False)


def nut(text: str, ham=None, chinh: bool = False, quyen: str | None = None) -> QPushButton:
    quyen = quyen or QUYEN_NUT.get(text)
    an = quyen is not None and not co_quyen(_vai_tro_hien_tai[0], quyen)
    b = _NutAn(text) if an else QPushButton(text)
    if an:
        b.setVisible(False)
    if chinh:
        b.setObjectName("chinh")
    if ham:
        b.clicked.connect(ham)
    return b


def chay(parent: QWidget, ham, *args, **kw):
    """Gọi nghiệp vụ, báo lỗi thân thiện. Trả về (thành công, kết quả)."""
    try:
        return True, ham(*args, **kw)
    except LoiNghiepVu as e:
        QMessageBox.warning(parent, "Không thực hiện được", str(e))
    except LOI_CSDL as e:
        QMessageBox.critical(parent, "Lỗi dữ liệu", f"Lỗi CSDL: {e}")
    return False, None


def hoi(parent: QWidget, cau_hoi: str) -> bool:
    return QMessageBox.question(parent, "Xác nhận", cau_hoi) == QMessageBox.Yes


class Trang(QWidget):
    def __init__(self, nv: NghiepVu):
        super().__init__()
        self.nv = nv
        self.c = nv.c

    def nap(self) -> None:  # nạp lại dữ liệu khi mở trang
        pass

    def lua_chon(self, sql: str, co_trong: str | None = None) -> list[tuple[str, object]]:
        ds = [(r[1], r[0]) for r in self.c.execute(sql)]
        return ([(co_trong, None)] if co_trong is not None else []) + ds


# ---------------------------------------------------------------- Tổng quan
class TrangTongQuan(Trang):
    def __init__(self, nv: NghiepVu):
        super().__init__(nv)
        v = QVBoxLayout(self)
        v.addWidget(tieu_de("Tổng quan"))
        self.canh_bao = QLabel(); self.canh_bao.setObjectName("canhBao"); self.canh_bao.setWordWrap(True)
        v.addWidget(self.canh_bao)
        self.luoi = QGridLayout(); v.addLayout(self.luoi)
        hang = QHBoxLayout()
        hang.addWidget(QLabel("<b>Hạn sắp tới và quá hạn</b>")); hang.addStretch()
        hang.addWidget(nut("+ Thêm hạn công việc", self.them_han))
        self.nut_xong = nut("Đánh dấu đã xong", self.danh_dau_xong)
        hang.addWidget(self.nut_xong)
        v.addLayout(hang)
        self.bang_han = bang(["Hạn", "Còn lại", "Nội dung", "Liên quan"], gian=2)
        v.addWidget(self.bang_han)
        self.nap()

    def _the(self, col: int, so: str, nhan: str, mau: str) -> None:
        f = QFrame(); f.setObjectName("the")
        lv = QVBoxLayout(f)
        s = QLabel(so); s.setObjectName("soLon"); s.setStyleSheet(f"color:{mau}")
        n = QLabel(nhan); n.setObjectName("nhan")
        lv.addWidget(s); lv.addWidget(n)
        self.luoi.addWidget(f, 0, col)

    def nap(self) -> None:
        while self.luoi.count():
            self.luoi.takeAt(0).widget().deleteLater()
        c, hn = self.c, hom_nay()
        nam = hn[:4]
        dang_xl = c.execute("SELECT COUNT(*) FROM ho_so WHERE da_xoa=0 AND trang_thai IN "
                            "('tiep_nhan','tra_lai','da_trinh')").fetchone()[0]
        qd = c.execute("SELECT COUNT(*) FROM ho_so WHERE da_xoa=0 AND trang_thai='da_co_qd' "
                       "AND substr(qd_ngay,1,4)=?", (nam,)).fetchone()[0]
        luot = c.execute("SELECT COUNT(*), COALESCE(SUM(so_tien),0) FROM v_lich_su_khen_thuong "
                         "WHERE nam=?", (int(nam),)).fetchone()
        # id dương: han_cong_viec (đánh dấu xong được); id âm: hạn xử lý hồ sơ
        han = c.execute("""
            SELECT h.id, han, tieu_de, COALESCE(pt.ten, hs.trich_yeu, '') AS lq FROM han_cong_viec h
            LEFT JOIN phong_trao pt ON pt.id=h.phong_trao_id
            LEFT JOIN ho_so hs ON hs.id=h.ho_so_id WHERE h.da_xong=0
            UNION ALL
            SELECT -hs.id, han_xu_ly, 'Xử lý hồ sơ: ' || trich_yeu, d.ten FROM ho_so hs
            JOIN don_vi d ON d.id=hs.don_vi_id
            WHERE hs.da_xoa=0 AND han_xu_ly IS NOT NULL AND trang_thai IN ('tiep_nhan','tra_lai','da_trinh')
            UNION ALL
            SELECT -100000-id, han_nop_ho_so, 'Hạn nộp hồ sơ phong trào', ten FROM phong_trao
            WHERE da_xoa=0 AND han_nop_ho_so >= date(?, '-7 day')
            ORDER BY 2""", (hn,)).fetchall()
        rows, ids, qua, sap = [], [], 0, 0
        d0 = date.fromisoformat(hn)
        for r in han:
            con = (date.fromisoformat(r[1]) - d0).days
            it = QTableWidgetItem("Quá hạn %d ngày" % -con if con < 0 else
                                  ("Hôm nay" if con == 0 else f"{con} ngày"))
            if con < 0:
                it.setForeground(QColor("#b91c1c")); qua += 1
            elif con <= 3:
                it.setForeground(QColor("#c2410c")); sap += 1
            rows.append([ngay_vn(r[1]), it, r[2], r[3]])
            ids.append(r[0])
        do_du_lieu(self.bang_han, rows, ids)

        self._the(0, str(dang_xl), "Hồ sơ đang xử lý", "#1f6feb")
        self._the(1, str(sap + qua), "Việc sắp đến hạn / quá hạn", "#c2410c" if qua or sap else "#15803d")
        self._the(2, str(qd), f"Quyết định khen thưởng năm {nam}", "#15803d")
        self._the(3, tien(luot[1]), f"Tiền thưởng năm {nam} (đồng, {luot[0]} lượt)", "#12355b")
        self.canh_bao.setText(
            f"⚠ Có {qua} việc quá hạn và {sap} việc đến hạn trong 3 ngày tới." if qua or sap
            else "Không có việc nào sắp đến hạn.")

    def them_han(self) -> None:
        d = HopThoaiNhap("Thêm hạn công việc", [
            Truong("tieu_de", "Nội dung", bat_buoc=True),
            Truong("han", "Hạn", "ngay", bat_buoc=True),
            Truong("phong_trao_id", "Phong trào", "chon", lua_chon=self.lua_chon(
                "SELECT id, ten || ' (' || nam || ')' FROM phong_trao WHERE da_xoa=0 ORDER BY nam DESC", "—")),
            Truong("ghi_chu", "Ghi chú", "nhieu_dong"),
        ], parent=self)
        if d.exec() and chay(self, self.nv.luu_danh_muc, "han_cong_viec", d.ket_qua)[0]:
            self.nap()

    def danh_dau_xong(self) -> None:
        id_ = id_dang_chon(self.bang_han)
        if id_ is None:
            return
        if id_ < 0:
            QMessageBox.information(self, "Hạn hồ sơ", "Hạn này tự hết khi hồ sơ được xử lý xong "
                                    "(có quyết định hoặc cập nhật hạn trong hồ sơ).")
            return
        if chay(self, self.nv.luu_danh_muc, "han_cong_viec", {"da_xong": 1}, id_)[0]:
            self.nap()


# ---------------------------------------------------------------- Hộp chọn đối tượng
class HopThoaiChonDoiTuong(QDialog):
    def __init__(self, trang: "TrangHoSo"):
        super().__init__(trang)
        self.trang = trang
        self.setWindowTitle("Thêm tập thể, cá nhân vào hồ sơ")
        self.setMinimumWidth(560)
        self.doi_tuong_id = None
        self.thanh_tich = None
        v = QVBoxLayout(self)
        f = QFormLayout()
        self.chon = QComboBox(); self.chon.setEditable(True); self.chon.setInsertPolicy(QComboBox.NoInsert)
        self.chon.completer().setFilterMode(Qt.MatchContains)
        self.chon.completer().setCompletionMode(QCompleter.PopupCompletion)
        self._nap()
        hang = QHBoxLayout(); hang.addWidget(self.chon, 1); hang.addWidget(nut("Tạo mới…", self.tao_moi))
        f.addRow("Tập thể / cá nhân *", hang)
        self.tt = QLineEdit(); self.tt.setPlaceholderText("Tóm tắt thành tích")
        f.addRow("Thành tích", self.tt)
        v.addLayout(f)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Thêm")
        bb.button(QDialogButtonBox.Cancel).setText("Hủy")
        bb.accepted.connect(self._ok); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def _nap(self, chon_id=None) -> None:
        self.chon.clear()
        for r in self.trang.c.execute("SELECT id, loai, ten, chuc_vu, don_vi_cong_tac FROM doi_tuong "
                                      "WHERE da_xoa=0 ORDER BY loai, ten"):
            nhan = f"{'[TT] ' if r['loai'] == 'tap_the' else ''}{r['ten']}" + \
                   "".join(f" – {x}" for x in (r["chuc_vu"], r["don_vi_cong_tac"]) if x)
            self.chon.addItem(nhan, r["id"])
        self.chon.setCurrentIndex(self.chon.findData(chon_id) if chon_id else -1)

    def tao_moi(self) -> None:
        id_ = TrangDoiTuong.hop_thoai_doi_tuong(self, self.trang.nv)
        if id_:
            self._nap(id_)

    def _ok(self) -> None:
        i = self.chon.findText(self.chon.currentText())
        if i < 0:
            QMessageBox.warning(self, "Chưa chọn", "Chọn một tập thể/cá nhân trong danh sách hoặc bấm Tạo mới.")
            return
        self.doi_tuong_id = self.chon.itemData(i)
        self.thanh_tich = self.tt.text().strip() or None
        self.accept()


# ---------------------------------------------------------------- Hồ sơ đề nghị
class TrangHoSo(Trang):
    def __init__(self, nv: NghiepVu):
        super().__init__(nv)
        v = QVBoxLayout(self)
        v.addWidget(tieu_de("Hồ sơ đề nghị khen thưởng"))
        thanh = QHBoxLayout()
        self.loc = QComboBox(); self.loc.addItem("Tất cả trạng thái", None)
        for k, t in TRANG_THAI.items():
            self.loc.addItem(t, k)
        self.loc.currentIndexChanged.connect(self.nap)
        thanh.addWidget(QLabel("Lọc:")); thanh.addWidget(self.loc); thanh.addStretch()
        thanh.addWidget(nut("Nhập hồ sơ từ Excel…", self.nhap_excel, chinh=True))
        thanh.addWidget(nut("+ Hồ sơ mới", self.ho_so_moi))
        self.nut_sua = nut("Sửa thông tin", self.sua_ho_so); thanh.addWidget(self.nut_sua)
        self.nut_xoa = nut("Xóa", self.xoa_ho_so); thanh.addWidget(self.nut_xoa)
        v.addLayout(thanh)

        sp = QSplitter(Qt.Vertical)
        self.ds = bang(["Trạng thái", "Đơn vị đề nghị", "Trích yếu", "TTr đơn vị", "TTr VH-XH",
                        "Quyết định", "Hạn xử lý"], gian=2)
        self.ds.itemSelectionChanged.connect(self.chon)
        self.ds.doubleClicked.connect(self.sua_ho_so)
        sp.addWidget(self.ds)

        ct = QGroupBox("Chi tiết hồ sơ")
        cv = QVBoxLayout(ct)
        self.thong_tin = QLabel(); self.thong_tin.setWordWrap(True)
        self.thong_tin.setTextFormat(Qt.RichText)
        cv.addWidget(self.thong_tin)
        hang = QHBoxLayout()
        self.nut_them_dt = nut("+ Thêm tập thể/cá nhân", self.them_dt); hang.addWidget(self.nut_them_dt)
        self.nut_sua_dong = nut("Sửa thành tích/tiền", self.sua_dong); hang.addWidget(self.nut_sua_dong)
        self.nut_bo = nut("Bỏ khỏi hồ sơ", self.bo_dong); hang.addWidget(self.nut_bo)
        hang.addStretch()
        cv.addLayout(hang)
        self.ds_dt = bang(["STT", "Loại", "Tên", "Chức vụ, đơn vị", "Thành tích", "Kết quả", "Tiền thưởng"], gian=4)
        self.ds_dt.doubleClicked.connect(self.sua_dong)
        cv.addWidget(self.ds_dt)
        self.tong = QLabel(); cv.addWidget(self.tong)
        luong = QHBoxLayout()
        self.nut_luong = {
            "tra_lai": nut("Trả lại bổ sung…", self.tra_lai),
            "tiep_nhan": nut("Nhận lại hồ sơ đã bổ sung", self.nhan_lai),
            "da_trinh": nut("Trình (nhập số Tờ trình)…", self.trinh, chinh=True),
            "da_co_qd": nut("Nhập Quyết định…", self.nhap_qd, chinh=True),
            "khong_duyet": nut("Không được duyệt…", self.khong_duyet),
        }
        for b in self.nut_luong.values():
            luong.addWidget(b)
        luong.addStretch()
        cv.addLayout(luong)
        xuat = QHBoxLayout()
        xuat.addWidget(QLabel("Xuất:"))
        self.nut_xuat = [
            nut("Tờ trình (Word)", lambda: self.xuat("to_trinh")),
            nut("Dự thảo QĐ + danh sách (Word)", lambda: self.xuat("quyet_dinh")),
            nut("Danh sách đề nghị (Excel)", lambda: self.xuat("danh_sach")),
            nut("Danh sách chi trả (Excel)", lambda: self.xuat("chi_tra")),
        ]
        for b in self.nut_xuat:
            xuat.addWidget(b)
        xuat.addStretch()
        cv.addLayout(xuat)
        sp.addWidget(ct)
        sp.setSizes([230, 450])
        v.addWidget(sp)
        self.nap()

    # ---- nạp
    def nap(self, giu_id=None) -> None:
        giu_id = giu_id or id_dang_chon(self.ds)
        tt = self.loc.currentData()
        sql = ("SELECT hs.*, d.ten AS dv FROM ho_so hs JOIN don_vi d ON d.id=hs.don_vi_id "
               "WHERE hs.da_xoa=0" + (" AND trang_thai=?" if tt else "") + " ORDER BY hs.id DESC")
        rs = self.c.execute(sql, (tt,) if tt else ()).fetchall()
        self.ds.blockSignals(True)
        do_du_lieu(self.ds, [[o_trang_thai(r["trang_thai"]), r["dv"], r["trich_yeu"],
                              " ".join(filter(None, [r["ttr_dv_so"], ngay_vn(r["ttr_dv_ngay"])])),
                              " ".join(filter(None, [r["ttr_vhxh_so"], ngay_vn(r["ttr_vhxh_ngay"])])),
                              " ".join(filter(None, [r["qd_so"], ngay_vn(r["qd_ngay"])])),
                              ngay_vn(r["han_xu_ly"])] for r in rs], [r["id"] for r in rs])
        self.ds.blockSignals(False)
        ids = [r["id"] for r in rs]
        if ids:
            self.ds.selectRow(ids.index(giu_id) if giu_id in ids else 0)
        self.chon()

    def chon(self) -> None:
        hs_id = id_dang_chon(self.ds)
        self.hs_id = hs_id
        if hs_id is None:
            self.thong_tin.setText("<i>Chưa có hồ sơ. Bấm \"Nhập hồ sơ từ Excel…\" hoặc \"+ Hồ sơ mới\".</i>")
            do_du_lieu(self.ds_dt, [])
            self.tong.setText("")
            self._bat_nut(None)
            return
        r = self.c.execute("SELECT hs.*, d.ten dv, ht.ten ht, pt.ten pt FROM ho_so hs "
                           "JOIN don_vi d ON d.id=hs.don_vi_id JOIN hinh_thuc ht ON ht.id=hs.hinh_thuc_id "
                           "LEFT JOIN phong_trao pt ON pt.id=hs.phong_trao_id WHERE hs.id=?",
                           (hs_id,)).fetchone()
        tra_lai = (f"<br><span style='color:#c2410c'><b>Lý do trả lại:</b> {r['ly_do_tra_lai']}</span>"
                   if r["ly_do_tra_lai"] else "")
        qd = (f"<br><span style='color:#15803d'><b>Quyết định:</b> {r['qd_so']} ngày {ngay_vn(r['qd_ngay'])}"
              f"{', ' + r['qd_nguoi_ky'] if r['qd_nguoi_ky'] else ''}</span>" if r["qd_so"] else "")
        self.thong_tin.setText(
            f"<b>{r['trich_yeu']}</b><br>"
            f"Phong trào: {r['pt'] or '—'} &nbsp;|&nbsp; Hình thức: {r['ht']} &nbsp;|&nbsp; Đơn vị: {r['dv']}<br>"
            + (f"Biên bản họp: {r['bb_so'] or ''} ngày {ngay_vn(r['bb_ngay'])}, "
               f"dự {r['bb_so_du'] or '?'}/{r['bb_tong_so'] or '?'}, nhất trí {r['bb_ty_le'] or '?'}"
               if r["bb_ngay"] else "<span style='color:#c2410c'>Chưa có biên bản họp xét</span>")
            + tra_lai + qd)
        ds = self.c.execute("SELECT hd.*, dt.loai, dt.ten, dt.danh_xung, dt.cap_bac, dt.chuc_vu, dt.don_vi_cong_tac "
                            "FROM ho_so_doi_tuong hd JOIN doi_tuong dt ON dt.id=hd.doi_tuong_id "
                            "WHERE hd.ho_so_id=? ORDER BY dt.loai DESC, hd.thu_tu, hd.id", (hs_id,)).fetchall()
        kq = {"de_nghi": "Đề nghị", "duoc_khen": "Được khen", "khong_duoc": "Không được khen"}
        do_du_lieu(self.ds_dt, [[i + 1, "Tập thể" if d["loai"] == "tap_the" else "Cá nhân",
                                 ten_hien_thi(d),
                                 ", ".join(filter(None, [d["chuc_vu"], d["don_vi_cong_tac"]])),
                                 d["tom_tat_thanh_tich"], kq[d["ket_qua"]], tien(d["so_tien"])]
                                for i, d in enumerate(ds)], [d["id"] for d in ds])
        n_tt = sum(1 for d in ds if d["loai"] == "tap_the")
        tong = sum(d["so_tien"] or 0 for d in ds)
        self.tong.setText(f"<b>{n_tt} tập thể, {len(ds) - n_tt} cá nhân. "
                          f"Tổng tiền thưởng: {tien(tong)} đồng</b>")
        self._bat_nut(r["trang_thai"])

    def _bat_nut(self, trang_thai: str | None) -> None:
        mo = trang_thai in ("tiep_nhan", "tra_lai", "da_trinh")
        for b in (self.nut_sua, self.nut_them_dt, self.nut_sua_dong, self.nut_bo):
            b.setEnabled(mo)
        self.nut_xoa.setEnabled(trang_thai is not None and trang_thai != "da_co_qd")
        for b in self.nut_xuat:
            b.setEnabled(trang_thai is not None and trang_thai != "khong_duyet")
        duoc = CHUYEN_TRANG_THAI.get(trang_thai, set())
        for k, b in self.nut_luong.items():
            b.setVisible(k in duoc)

    # ---- form hồ sơ
    def _truong_ho_so(self) -> list[Truong]:
        return [
            Truong("trich_yeu", "Trích yếu", bat_buoc=True, goi_y="VD: Khen thưởng công tác quân sự năm 2026"),
            Truong("noi_dung_khen", "Nội dung khen (in trong văn bản)", "nhieu_dong",
                   goi_y="VD: có thành tích xuất sắc trong thực hiện nhiệm vụ công tác quân sự, "
                         "quốc phòng địa phương năm 2026"),
            Truong("phong_trao_id", "Phong trào", "chon", lua_chon=self.lua_chon(
                "SELECT id, ten || ' (' || nam || ')' FROM phong_trao WHERE da_xoa=0 ORDER BY nam DESC, id DESC", "—")),
            Truong("don_vi_id", "Đơn vị đề nghị", "chon", bat_buoc=True, lua_chon=self.lua_chon(
                "SELECT id, ten FROM don_vi WHERE dang_dung=1 ORDER BY ten")),
            Truong("hinh_thuc_id", "Hình thức", "chon", bat_buoc=True, lua_chon=self.lua_chon(
                "SELECT id, ten FROM hinh_thuc WHERE dang_dung=1 ORDER BY id")),
            Truong("ttr_dv_so", "Số TTr của đơn vị"), Truong("ttr_dv_ngay", "Ngày TTr của đơn vị", "ngay"),
            Truong("bb_so", "Số biên bản họp xét"), Truong("bb_ngay", "Ngày họp xét", "ngay"),
            Truong("bb_to_chuc_hop", "Tổ/Hội đồng họp xét"),
            Truong("bb_so_du", "Số thành viên dự", "so"), Truong("bb_tong_so", "Tổng số thành viên", "so"),
            Truong("bb_ty_le", "Tỷ lệ nhất trí", goi_y="VD: 100%"),
            Truong("han_xu_ly", "Hạn xử lý", "ngay"), Truong("ghi_chu", "Ghi chú", "nhieu_dong"),
        ]

    def ho_so_moi(self) -> None:
        d = HopThoaiNhap("Hồ sơ mới", self._truong_ho_so(), parent=self)
        if d.exec():
            ok, id_ = chay(self, self.nv.tao_ho_so, d.ket_qua)
            if ok:
                self.loc.setCurrentIndex(0)
                self.nap(id_)

    def sua_ho_so(self) -> None:
        if not self.nut_sua.isEnabled() or self.hs_id is None:
            return
        r = dict(self.c.execute("SELECT * FROM ho_so WHERE id=?", (self.hs_id,)).fetchone())
        d = HopThoaiNhap("Sửa thông tin hồ sơ", self._truong_ho_so(), r, parent=self)
        if d.exec() and chay(self, self.nv.sua_ho_so, self.hs_id, d.ket_qua)[0]:
            self.nap()

    def xoa_ho_so(self) -> None:
        if self.hs_id and hoi(self, "Xóa hồ sơ này? (Dữ liệu được đánh dấu xóa, vẫn còn trong nhật ký.)"):
            if chay(self, self.nv.xoa_ho_so, self.hs_id)[0]:
                self.nap()

    # ---- danh sách trong hồ sơ
    def them_dt(self) -> None:
        d = HopThoaiChonDoiTuong(self)
        if d.exec():
            ok, cb = chay(self, self.nv.them_vao_ho_so, self.hs_id, d.doi_tuong_id, d.thanh_tich)
            if ok:
                if cb:
                    QMessageBox.information(self, "Lưu ý", cb)
                self.nap()

    def sua_dong(self) -> None:
        dong = id_dang_chon(self.ds_dt)
        if dong is None or not self.nut_sua_dong.isEnabled():
            return
        r = self.c.execute("SELECT * FROM ho_so_doi_tuong WHERE id=?", (dong,)).fetchone()
        d = HopThoaiNhap("Sửa thành tích, tiền thưởng", [
            Truong("tom_tat_thanh_tich", "Thành tích", "nhieu_dong"),
            Truong("so_tien", "Tiền thưởng (đồng)", "so"),
        ], dict(r), parent=self, ghi_chu="Tiền thưởng được tính tự động; chỉ sửa tay khi có lý do. "
                                         "Khi trình hoặc nhập QĐ, phần mềm sẽ tính lại theo lương cơ sở.")
        if d.exec() and chay(self, self.nv.sua_dong_ho_so, dong, d.ket_qua["tom_tat_thanh_tich"],
                             d.ket_qua["so_tien"])[0]:
            self.nap()

    def bo_dong(self) -> None:
        dong = id_dang_chon(self.ds_dt)
        if dong and hoi(self, "Bỏ tập thể/cá nhân này khỏi hồ sơ?"):
            if chay(self, self.nv.bo_khoi_ho_so, dong)[0]:
                self.nap()

    # ---- luồng
    def tra_lai(self) -> None:
        d = HopThoaiNhap("Trả lại hồ sơ để bổ sung", [
            Truong("ly_do", "Lý do", "nhieu_dong", bat_buoc=True),
            Truong("han", "Hạn bổ sung", "ngay"),
        ], parent=self)
        if d.exec() and chay(self, self.nv.tra_lai, self.hs_id, d.ket_qua["ly_do"], d.ket_qua["han"])[0]:
            self.nap()

    def nhan_lai(self) -> None:
        if chay(self, self.nv.nhan_lai_bo_sung, self.hs_id)[0]:
            self.nap()

    def trinh(self) -> None:
        d = HopThoaiNhap("Trình Chủ tịch UBND xã", [
            Truong("so", "Số Tờ trình VH-XH", bat_buoc=True, goi_y="VD: 357/TTr-VHXH"),
            Truong("ngay", "Ngày Tờ trình", "ngay", bat_buoc=True),
        ], {"ngay": hom_nay()}, parent=self,
            ghi_chu="Nhập số, ngày Tờ trình sau khi đã có số trên iOffice. Tiền thưởng sẽ tính lại theo ngày này.")
        if d.exec() and chay(self, self.nv.trinh, self.hs_id, d.ket_qua["so"], d.ket_qua["ngay"])[0]:
            self.nap()

    def nhap_qd(self) -> None:
        d = HopThoaiNhap("Nhập Quyết định khen thưởng", [
            Truong("so", "Số Quyết định", bat_buoc=True, goi_y="VD: 123/QĐ-UBND"),
            Truong("ngay", "Ngày ký", "ngay", bat_buoc=True),
            Truong("nguoi_ky", "Người ký"),
        ], parent=self, ghi_chu="Chỉ nhập khi Quyết định đã ký, có số. Sau bước này hồ sơ không sửa được.")
        if not d.exec():
            return
        rows = self.c.execute("SELECT hd.id, dt.ten FROM ho_so_doi_tuong hd JOIN doi_tuong dt "
                              "ON dt.id=hd.doi_tuong_id WHERE hd.ho_so_id=? ORDER BY hd.thu_tu",
                              (self.hs_id,)).fetchall()
        chon = HopThoaiChonNhieu("Danh sách trong Quyết định",
                                 "Bỏ đánh dấu những tập thể/cá nhân KHÔNG có tên trong Quyết định.",
                                 [(r["ten"], r["id"], True) for r in rows], self)
        if not chon.exec():
            return
        khong = {r["id"] for r in rows} - chon.da_chon
        if chay(self, self.nv.nhap_quyet_dinh, self.hs_id, d.ket_qua["so"], d.ket_qua["ngay"],
                d.ket_qua["nguoi_ky"], khong)[0]:
            self.nap()

    def khong_duyet(self) -> None:
        d = HopThoaiNhap("Hồ sơ không được duyệt", [Truong("ly_do", "Lý do", "nhieu_dong", bat_buoc=True)],
                         parent=self)
        if d.exec() and chay(self, self.nv.khong_duyet, self.hs_id, d.ket_qua["ly_do"])[0]:
            self.nap()

    # ---- xuất văn bản
    def xuat(self, loai: str) -> None:
        if self.hs_id is None:
            return
        if not chay(self, self.nv.kiem_quyen, "xuat_chi_tra" if loai == "chi_tra" else "xuat_van_ban")[0]:
            return
        if loai == "chi_tra" and not hoi(self, "Danh sách chi trả có SỐ TÀI KHOẢN (dữ liệu cá nhân). "
                                              "Chỉ gửi cho kế toán, không gửi rộng hoặc đưa lên mạng. Tiếp tục?"):
            return
        ten = {"to_trinh": "To-trinh", "quyet_dinh": "Du-thao-QD", "danh_sach": "Danh-sach-de-nghi",
               "chi_tra": "Danh-sach-chi-tra"}[loai]
        duoi = "docx" if loai in ("to_trinh", "quyet_dinh") else "xlsx"
        p, _ = QFileDialog.getSaveFileName(self, "Lưu file", str(Path.home() / f"{ten}-ho-so-{self.hs_id}.{duoi}"),
                                           f"{duoi.upper()} (*.{duoi})")
        if not p:
            return
        try:
            if duoi == "docx":
                van_ban.sinh_word(self.c, self.hs_id, loai, p)
            elif loai == "danh_sach":
                van_ban.xuat_danh_sach(self.c, self.hs_id, p)
            else:
                van_ban.xuat_chi_tra(self.c, self.hs_id, p)
        except PermissionError:
            QMessageBox.warning(self, "Không lưu được", "File đang mở trong Word/Excel. Đóng file rồi thử lại.")
            return
        except Exception as e:  # noqa: BLE001 - báo lỗi cho người dùng thay vì thoát chương trình
            QMessageBox.critical(self, "Lỗi", f"Không tạo được file: {e}")
            return
        ghi_chu = ("\n\nĐây là DỰ THẢO. Rà soát các chỗ \"[...]\" và căn cứ trước khi trình ký trên iOffice."
                   if duoi == "docx" else "")
        QMessageBox.information(self, "Đã tạo", f"Đã lưu:\n{p}{ghi_chu}")

    # ---- nhập Excel
    def nhap_excel(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "Chọn file mẫu đã điền", "", "Excel (*.xlsx)")
        if not p:
            return
        kq = excel_mau.doc_mau(p)
        if kq.loi:
            QMessageBox.warning(self, "File có lỗi, chưa nhập",
                                "Sửa các lỗi sau rồi nhập lại:\n\n• " + "\n• ".join(kq.loi[:30]))
            return
        pt = self.c.execute("SELECT * FROM phong_trao WHERE id=?", (kq.phong_trao_id,)).fetchone() \
            if kq.phong_trao_id else None
        n_tt = sum(1 for x in kq.dong if x["loai"] == "tap_the")
        d = HopThoaiNhap("Nhập hồ sơ từ Excel", [
            Truong("trich_yeu", "Trích yếu", bat_buoc=True),
            Truong("hinh_thuc_id", "Hình thức", "chon", bat_buoc=True, lua_chon=self.lua_chon(
                "SELECT id, ten FROM hinh_thuc WHERE dang_dung=1 ORDER BY id")),
            Truong("han_xu_ly", "Hạn xử lý", "ngay"),
        ], {"trich_yeu": f"Khen thưởng {pt['ten']} năm {pt['nam']}" if pt else ""}, parent=self,
            ghi_chu=f"Đơn vị: {kq.thong_tin['don_vi']}. Phong trào: {pt['ten'] if pt else 'không rõ'}. "
                    f"Danh sách: {n_tt} tập thể, {len(kq.dong) - n_tt} cá nhân.")
        if not d.exec():
            return
        ok, kn = chay(self, excel_mau.nhap_ho_so, self.nv, kq, d.ket_qua["hinh_thuc_id"],
                      d.ket_qua["trich_yeu"], d.ket_qua["han_xu_ly"])
        if ok:
            tb = f"Đã tạo hồ sơ. Đối tượng mới: {kn.them_moi}; đã có sẵn: {kn.da_co}."
            if kn.canh_bao:
                tb += "\n\nLưu ý:\n• " + "\n• ".join(kn.canh_bao)
            QMessageBox.information(self, "Nhập xong", tb)
            self.loc.setCurrentIndex(0)
            self.nap(kn.ho_so_id)


# ---------------------------------------------------------------- Đối tượng
class TrangDoiTuong(Trang):
    def __init__(self, nv: NghiepVu):
        super().__init__(nv)
        v = QVBoxLayout(self)
        v.addWidget(tieu_de("Cá nhân, tập thể"))
        thanh = QHBoxLayout()
        self.tim = QLineEdit(); self.tim.setPlaceholderText("Tìm theo tên, đơn vị…")
        self.tim.textChanged.connect(self.nap)
        self.loai = QComboBox()
        for t, k in (("Tất cả", None), *LOAI_DT):
            self.loai.addItem(t, k)
        self.loai.currentIndexChanged.connect(self.nap)
        thanh.addWidget(self.tim, 1); thanh.addWidget(self.loai)
        thanh.addWidget(nut("+ Thêm", self.them, chinh=True))
        thanh.addWidget(nut("Sửa", self.sua))
        thanh.addWidget(nut("Xóa", self.xoa))
        v.addLayout(thanh)
        sp = QSplitter(Qt.Vertical)
        self.ds = bang(["Loại", "Tên", "Chức vụ", "Đơn vị công tác", "Số lần được khen"], gian=1)
        self.ds.itemSelectionChanged.connect(self.chon)
        self.ds.doubleClicked.connect(self.sua)
        sp.addWidget(self.ds)
        g = QGroupBox("Lịch sử khen thưởng")
        gv = QVBoxLayout(g)
        self.ls = bang(["Năm", "Hình thức", "Nội dung", "Quyết định", "Tiền thưởng"], gian=2)
        gv.addWidget(self.ls)
        sp.addWidget(g)
        v.addWidget(sp)
        self.nap()

    @staticmethod
    def truong(c: sqlite3.Connection) -> list[Truong]:
        return [
            Truong("loai", "Loại", "chon", bat_buoc=True, lua_chon=LOAI_DT),
            Truong("danh_xung", "Ông/Bà", "chon", lua_chon=[("— (tự theo giới tính)", None), ("Ông", "Ông"),
                                                            ("Bà", "Bà")]),
            Truong("cap_bac", "Cấp bậc", goi_y="Chỉ ghi với Quân sự, Công an: Đại úy, Thiếu tá…"),
            Truong("ten", "Họ tên / Tên tập thể", bat_buoc=True),
            Truong("chuc_vu", "Chức vụ"),
            Truong("don_vi_cong_tac", "Đơn vị công tác"),
            Truong("don_vi_id", "Thuộc đơn vị đề nghị", "chon", lua_chon=[("—", None)] + [
                (r[1], r[0]) for r in c.execute("SELECT id, ten FROM don_vi WHERE dang_dung=1 ORDER BY ten")]),
            Truong("nam_sinh", "Năm sinh", "so"),
            Truong("gioi_tinh", "Giới tính", "chon", lua_chon=[("—", None), ("Nam", "Nam"), ("Nữ", "Nữ")]),
            Truong("nguoi_dai_dien", "Người đại diện (tập thể)"),
            Truong("so_tai_khoan", "Số tài khoản", goi_y="Chỉ nhập khi cần chi trả"),
            Truong("ngan_hang", "Ngân hàng"),
            Truong("ghi_chu", "Ghi chú", "nhieu_dong"),
        ]

    @staticmethod
    def hop_thoai_doi_tuong(parent: QWidget, nv: NghiepVu, id_: int | None = None) -> int | None:
        gt = dict(nv.c.execute("SELECT * FROM doi_tuong WHERE id=?", (id_,)).fetchone()) if id_ else None
        if gt and not nv.co_quyen("xem_stk"):
            gt["so_tai_khoan"] = che_stk(gt["so_tai_khoan"])
        d = HopThoaiNhap("Sửa tập thể/cá nhân" if id_ else "Thêm tập thể/cá nhân",
                         TrangDoiTuong.truong(nv.c), gt, parent=parent,
                         ghi_chu="Không nhập CCCD. Số tài khoản là dữ liệu cá nhân, chỉ nhập khi cần chi trả.")
        if not d.exec():
            return None
        if id_:
            return id_ if chay(parent, nv.sua_doi_tuong, id_, d.ket_qua)[0] else None
        ok, moi = chay(parent, nv.them_doi_tuong, d.ket_qua)
        return moi if ok else None

    def them(self) -> None:
        if self.hop_thoai_doi_tuong(self, self.nv):
            self.nap()

    def sua(self) -> None:
        id_ = id_dang_chon(self.ds)
        if id_ and self.hop_thoai_doi_tuong(self, self.nv, id_):
            self.nap()

    def xoa(self) -> None:
        id_ = id_dang_chon(self.ds)
        if id_ and hoi(self, "Xóa tập thể/cá nhân này?") and chay(self, self.nv.xoa_doi_tuong, id_)[0]:
            self.nap()

    def nap(self) -> None:
        q = f"%{self.tim.text().strip()}%"
        loai = self.loai.currentData()
        rs = self.c.execute(
            "SELECT dt.*, (SELECT COUNT(*) FROM v_lich_su_khen_thuong v WHERE v.doi_tuong_id=dt.id) n "
            "FROM doi_tuong dt WHERE da_xoa=0 AND (ten LIKE ? OR COALESCE(don_vi_cong_tac,'') LIKE ?)"
            + (" AND loai=?" if loai else "") + " ORDER BY loai, ten",
            (q, q, loai) if loai else (q, q)).fetchall()
        do_du_lieu(self.ds, [["Tập thể" if r["loai"] == "tap_the" else "Cá nhân", ten_hien_thi(r), r["chuc_vu"],
                              r["don_vi_cong_tac"], r["n"]] for r in rs], [r["id"] for r in rs])
        do_du_lieu(self.ls, [])

    def chon(self) -> None:
        dt = id_dang_chon(self.ds)
        if dt is None:
            return
        rs = self.c.execute("SELECT * FROM v_lich_su_khen_thuong WHERE doi_tuong_id=? ORDER BY qd_ngay DESC",
                            (dt,)).fetchall()
        do_du_lieu(self.ls, [[r["nam"], r["hinh_thuc"], r["trich_yeu"],
                              f"{r['qd_so']} ngày {ngay_vn(r['qd_ngay'])}", tien(r["so_tien"])] for r in rs])


# ---------------------------------------------------------------- Phong trào
class TrangPhongTrao(Trang):
    TRUONG = [
        Truong("ten", "Tên phong trào", bat_buoc=True),
        Truong("nam", "Năm", "so", bat_buoc=True),
        Truong("ngay_phat_dong", "Ngày phát động", "ngay"),
        Truong("han_nop_ho_so", "Hạn các đơn vị nộp hồ sơ", "ngay"),
        Truong("mo_ta", "Mô tả", "nhieu_dong"),
    ]

    def __init__(self, nv: NghiepVu):
        super().__init__(nv)
        v = QVBoxLayout(self)
        v.addWidget(tieu_de("Phong trào thi đua"))
        thanh = QHBoxLayout(); thanh.addStretch()
        thanh.addWidget(nut("Xuất mẫu Excel gửi các phòng…", self.xuat_mau, chinh=True))
        thanh.addWidget(nut("+ Phong trào mới", self.them))
        thanh.addWidget(nut("Sửa", self.sua))
        thanh.addWidget(nut("Xóa", self.xoa))
        v.addLayout(thanh)
        self.bang = bang(["Năm", "Tên phong trào", "Hạn nộp hồ sơ", "Số hồ sơ", "Đã có QĐ"], gian=1)
        self.bang.doubleClicked.connect(self.sua)
        v.addWidget(self.bang)
        huong_dan = QLabel("Cách dùng: chọn phong trào → \"Xuất mẫu Excel\" → gửi các phòng qua iOffice → "
                           "phòng điền, gửi lại → vào \"Hồ sơ đề nghị\" bấm \"Nhập hồ sơ từ Excel\".")
        huong_dan.setObjectName("nhan"); huong_dan.setWordWrap(True)
        v.addWidget(huong_dan)
        self.nap()

    def nap(self) -> None:
        rs = self.c.execute("SELECT pt.*, (SELECT COUNT(*) FROM ho_so h WHERE h.phong_trao_id=pt.id AND h.da_xoa=0) n,"
                            "(SELECT COUNT(*) FROM ho_so h WHERE h.phong_trao_id=pt.id AND h.da_xoa=0 "
                            "AND h.trang_thai='da_co_qd') q "
                            "FROM phong_trao pt WHERE da_xoa=0 ORDER BY nam DESC, id DESC").fetchall()
        do_du_lieu(self.bang, [[r["nam"], r["ten"], ngay_vn(r["han_nop_ho_so"]), r["n"], r["q"]] for r in rs],
                   [r["id"] for r in rs])

    def them(self) -> None:
        d = HopThoaiNhap("Phong trào mới", self.TRUONG, {"nam": int(hom_nay()[:4])}, parent=self)
        if d.exec() and chay(self, self.nv.them_phong_trao, d.ket_qua)[0]:
            self.nap()

    def sua(self) -> None:
        id_ = id_dang_chon(self.bang)
        if not id_:
            return
        r = dict(self.c.execute("SELECT * FROM phong_trao WHERE id=?", (id_,)).fetchone())
        d = HopThoaiNhap("Sửa phong trào", self.TRUONG, r, parent=self)
        if d.exec() and chay(self, self.nv.sua_phong_trao, id_, d.ket_qua)[0]:
            self.nap()

    def xoa(self) -> None:
        id_ = id_dang_chon(self.bang)
        if id_ and hoi(self, "Xóa phong trào này?") and chay(self, self.nv.xoa_phong_trao, id_)[0]:
            self.nap()

    def xuat_mau(self) -> None:
        id_ = id_dang_chon(self.bang)
        if not id_:
            QMessageBox.information(self, "Chưa chọn", "Chọn một phong trào trước.")
            return
        pt = dict(self.c.execute("SELECT * FROM phong_trao WHERE id=?", (id_,)).fetchone())
        ten = f"Mau-de-nghi-khen-thuong-{pt['nam']}-{pt['id']}.xlsx"
        p, _ = QFileDialog.getSaveFileName(self, "Lưu mẫu Excel", str(Path.home() / ten), "Excel (*.xlsx)")
        if p:
            excel_mau.xuat_mau(p, pt)
            self.nv.ghi_nhat_ky("xuat_file", "phong_trao", id_, Path(p).name)
            self.c.commit()
            QMessageBox.information(self, "Đã xuất", f"Đã lưu mẫu:\n{p}")


# ---------------------------------------------------------------- Báo cáo
class TrangBaoCao(Trang):
    def __init__(self, nv: NghiepVu):
        super().__init__(nv)
        v = QVBoxLayout(self)
        v.addWidget(tieu_de("Báo cáo, thống kê"))
        self.t = bang(["Năm", "Hình thức", "Tập thể", "Cá nhân", "Tổng tiền (đồng)"], gian=1)
        v.addWidget(QLabel("<b>Tổng hợp khen thưởng theo năm</b>"))
        v.addWidget(self.t)
        hang = QHBoxLayout()
        hang.addWidget(QLabel("Năm:"))
        self.nam = QComboBox()
        hang.addWidget(self.nam)
        hang.addWidget(nut("Xuất báo cáo Excel…", self.xuat_bao_cao, chinh=True))
        hang.addWidget(nut("Xuất dữ liệu liên thông (CSV/JSON)…", self.xuat_lien_thong))
        hang.addStretch()
        v.addLayout(hang)
        self.nap()

    def nap(self) -> None:
        rs = self.c.execute("SELECT nam, hinh_thuc, SUM(loai='tap_the') tt, SUM(loai='ca_nhan') cn, "
                            "SUM(so_tien) tien FROM v_lich_su_khen_thuong GROUP BY nam, hinh_thuc "
                            "ORDER BY nam DESC").fetchall()
        do_du_lieu(self.t, [[r["nam"], r["hinh_thuc"], r["tt"], r["cn"], tien(r["tien"])] for r in rs])
        chon = self.nam.currentData()
        self.nam.clear()
        nam_ht = int(hom_nay()[:4])
        for n in sorted({nam_ht, *(r["nam"] for r in rs if r["nam"])}, reverse=True):
            self.nam.addItem(str(n), n)
        if chon is not None and self.nam.findData(chon) >= 0:
            self.nam.setCurrentIndex(self.nam.findData(chon))

    def xuat_bao_cao(self) -> None:
        nam = self.nam.currentData()
        p, _ = QFileDialog.getSaveFileName(self, "Lưu báo cáo", str(Path.home() / f"Bao-cao-khen-thuong-{nam}.xlsx"),
                                           "Excel (*.xlsx)")
        if p:
            ok, _ = chay(self, van_ban.xuat_bao_cao_nam, self.c, nam, p)
            if ok:
                QMessageBox.information(self, "Đã tạo", f"Đã lưu:\n{p}")

    def xuat_lien_thong(self) -> None:
        nam = self.nam.currentData()
        thu_muc = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu dữ liệu liên thông", str(Path.home()))
        if thu_muc:
            ok, kq = chay(self, van_ban.xuat_lien_thong, self.c, thu_muc, nam)
            if ok:
                QMessageBox.information(self, "Đã xuất", "Đã lưu:\n" + "\n".join(str(x) for x in kq)
                                        + "\n\nĐịnh dạng nội bộ, chưa theo chuẩn CSDL TĐKT quốc gia "
                                          "(chưa có hướng dẫn). Không chứa số tài khoản.")


# ---------------------------------------------------------------- Danh mục
class TabDanhMuc(QWidget):
    def __init__(self, trang: "TrangDanhMuc", bang_db: str, truong: list[Truong], cot: list[str],
                 hien_thi, sql: str, ghi_chu: str = ""):
        super().__init__()
        self.trang, self.bang_db, self.truong, self.hien_thi, self.sql = trang, bang_db, truong, hien_thi, sql
        self.ghi_chu = ghi_chu
        v = QVBoxLayout(self)
        hang = QHBoxLayout(); hang.addStretch()
        hang.addWidget(nut("+ Thêm", self.them, quyen="danh_muc"))
        hang.addWidget(nut("Sửa", self.sua, quyen="danh_muc"))
        v.addLayout(hang)
        self.t = bang(cot, gian=1)
        self.t.doubleClicked.connect(self.sua)
        v.addWidget(self.t)

    def nap(self) -> None:
        rs = self.trang.c.execute(self.sql).fetchall()
        do_du_lieu(self.t, [self.hien_thi(r) for r in rs], [r["id"] for r in rs])

    def them(self) -> None:
        d = HopThoaiNhap("Thêm", self.truong, {"dang_dung": 1}, parent=self, ghi_chu=self.ghi_chu)
        if d.exec() and chay(self, self.trang.nv.luu_danh_muc, self.bang_db, d.ket_qua)[0]:
            self.nap()

    def sua(self) -> None:
        id_ = id_dang_chon(self.t)
        if not id_:
            return
        r = dict(self.trang.c.execute(f"SELECT * FROM {self.bang_db} WHERE id=?", (id_,)).fetchone())
        d = HopThoaiNhap("Sửa", self.truong, r, parent=self, ghi_chu=self.ghi_chu)
        if d.exec() and chay(self, self.trang.nv.luu_danh_muc, self.bang_db, d.ket_qua, id_)[0]:
            self.nap()


class TrangDanhMuc(Trang):
    def __init__(self, nv: NghiepVu):
        super().__init__(nv)
        v = QVBoxLayout(self)
        v.addWidget(tieu_de("Danh mục và cấu hình"))
        tabs = QTabWidget()
        dung = Truong("dang_dung", "Đang dùng", "co_khong")
        cb = "✓"
        self.tabs = [
            ("Hình thức khen thưởng", TabDanhMuc(
                self, "hinh_thuc",
                [Truong("ten", "Tên hình thức", bat_buoc=True),
                 Truong("loai", "Loại", "chon", lua_chon=[("Khen thưởng", "khen_thuong"), ("Danh hiệu", "danh_hieu")]),
                 Truong("he_so_ca_nhan", "Hệ số cá nhân", "so_thuc", goi_y="VD: 0,3"),
                 Truong("he_so_tap_the", "Hệ số tập thể", "so_thuc", goi_y="VD: 0,6"),
                 Truong("can_cu", "Căn cứ mức thưởng"), dung],
                ["Hình thức", "Loại", "Hệ số cá nhân", "Hệ số tập thể", "Căn cứ", "Đang dùng"],
                lambda r: [r["ten"], "Danh hiệu" if r["loai"] == "danh_hieu" else "Khen thưởng",
                           r["he_so_ca_nhan"], r["he_so_tap_the"], r["can_cu"], cb if r["dang_dung"] else ""],
                "SELECT * FROM hinh_thuc ORDER BY dang_dung DESC, id",
                "Hệ số × mức lương cơ sở = tiền thưởng. Nhập theo văn bản hiện hành.")),
            ("Mức lương cơ sở", TabDanhMuc(
                self, "luong_co_so",
                [Truong("ap_dung_tu", "Áp dụng từ ngày", "ngay", bat_buoc=True),
                 Truong("muc", "Mức (đồng/tháng)", "so", bat_buoc=True), Truong("can_cu", "Căn cứ")],
                ["Áp dụng từ", "Mức (đồng/tháng)", "Căn cứ"],
                lambda r: [ngay_vn(r["ap_dung_tu"]), tien(r["muc"]), r["can_cu"]],
                "SELECT * FROM luong_co_so ORDER BY ap_dung_tu DESC")),
            ("Đơn vị đề nghị", TabDanhMuc(
                self, "don_vi",
                [Truong("ten", "Tên đơn vị", bat_buoc=True),
                 Truong("loai", "Loại", "chon", lua_chon=[("Phòng chuyên môn", "phong_chuyen_mon"),
                                                          ("Đoàn thể", "doan_the"), ("Trường học", "truong_hoc"),
                                                          ("Ban", "ban"), ("Khác", "khac")]), dung],
                ["Đơn vị", "Loại", "Đang dùng"],
                lambda r: [r["ten"], r["loai"], cb if r["dang_dung"] else ""],
                "SELECT * FROM don_vi ORDER BY dang_dung DESC, ten")),
            ("Căn cứ pháp lý", TabDanhMuc(
                self, "can_cu",
                [Truong("noi_dung", "Nội dung căn cứ", "nhieu_dong", bat_buoc=True),
                 Truong("dung_cho", "Dùng cho", "chon", lua_chon=[("Cả hai", "ca_hai"), ("Tờ trình", "to_trinh"),
                                                                  ("Quyết định", "quyet_dinh")]),
                 Truong("thu_tu", "Thứ tự", "so"), dung],
                ["Thứ tự", "Nội dung căn cứ", "Dùng cho", "Đang dùng"],
                lambda r: [r["thu_tu"], r["noi_dung"], r["dung_cho"], cb if r["dang_dung"] else ""],
                "SELECT * FROM can_cu ORDER BY dang_dung DESC, thu_tu",
                "Căn cứ dùng khi sinh Tờ trình, Quyết định. Mỗi căn cứ một dòng, bắt đầu bằng \"Căn cứ…\". "
                "Cập nhật khi văn bản thay đổi.")),
        ]
        for ten, w in self.tabs:
            tabs.addTab(w, ten)
        ch = QWidget(); chv = QVBoxLayout(ch)
        self.bang_ch = bang(["Mục", "Giá trị"], gian=1)
        self.bang_ch.doubleClicked.connect(self.sua_cau_hinh)
        hang = QHBoxLayout(); hang.addStretch(); hang.addWidget(nut("Sửa thông tin cơ quan…", self.sua_cau_hinh))
        chv.addLayout(hang); chv.addWidget(self.bang_ch)
        tabs.insertTab(0, ch, "Thông tin cơ quan")
        tabs.setCurrentIndex(0)
        nk = QWidget(); nv_ = QVBoxLayout(nk)
        self.nhat_ky = bang(["Thời gian", "Người dùng", "Hành động", "Bảng", "Mã", "Nội dung"], gian=5)
        nv_.addWidget(self.nhat_ky)
        if nv.co_quyen("nhat_ky"):
            tabs.addTab(nk, "Nhật ký")
        v.addWidget(tabs)
        self.nap()

    def sua_cau_hinh(self) -> None:
        if not chay(self, self.nv.kiem_quyen, "danh_muc")[0]:
            return
        ch = van_ban.doc_cau_hinh(self.c)
        nhieu = {"quyen_ky_ttr", "quyen_ky_qd", "noi_nhan_ttr", "noi_nhan_qd", "thi_hanh_qd"}
        d = HopThoaiNhap("Thông tin cơ quan, người ký", [
            Truong(k, nhan, "nhieu_dong" if k in nhieu else "text") for k, nhan in van_ban.NHAN_CAU_HINH.items()
        ], ch, parent=self, ghi_chu="Dùng khi sinh Tờ trình, Quyết định, danh sách chi trả.")
        if d.exec():
            van_ban.luu_cau_hinh(self.c, d.ket_qua)
            self.nap()

    def nap(self) -> None:
        ch = van_ban.doc_cau_hinh(self.c)
        do_du_lieu(self.bang_ch, [[nhan, (ch[k] or "[chưa nhập]").replace("\n", " / ")]
                                  for k, nhan in van_ban.NHAN_CAU_HINH.items()])
        for _, w in self.tabs:
            w.nap()
        if not self.nv.co_quyen("nhat_ky"):
            return
        rs = self.c.execute("SELECT nk.*, nd.ten_dang_nhap FROM nhat_ky nk LEFT JOIN nguoi_dung nd "
                            "ON nd.id=nk.nguoi_dung_id ORDER BY nk.id DESC LIMIT 500").fetchall()
        do_du_lieu(self.nhat_ky, [[r["thoi_gian"], r["ten_dang_nhap"] or "", r["hanh_dong"], r["bang"],
                                   r["ban_ghi_id"], r["noi_dung"]] for r in rs])


class _BoDemNhanRoi(QObject):
    """Đếm thời gian không thao tác (chuột, bàn phím) để khóa phiên."""

    def __init__(self, timer: QTimer):
        super().__init__()
        self.timer = timer

    def eventFilter(self, _obj, e) -> bool:  # noqa: N802
        if e.type() in (QEvent.MouseButtonPress, QEvent.KeyPress, QEvent.Wheel, QEvent.MouseMove):
            self.timer.start()
        return False


class CuaSoChinh(QMainWindow):
    TRANG = [("Tổng quan", TrangTongQuan), ("Hồ sơ đề nghị", TrangHoSo), ("Cá nhân, tập thể", TrangDoiTuong),
             ("Phong trào", TrangPhongTrao), ("Báo cáo", TrangBaoCao), ("Danh mục", TrangDanhMuc)]
    PHUT_KHOA = 15

    def __init__(self, c, nguoi_dung=None, moi_truong=None, khoa: bytes | None = None,
                 khi_dang_xuat: Callable[[], None] | None = None):
        """nguoi_dung: NguoiDung (đã đăng nhập) hoặc chuỗi tên (chế độ thử, đủ quyền)."""
        super().__init__()
        self.nguoi_dung = nguoi_dung if not isinstance(nguoi_dung, str) else None
        self.ten_hien = nguoi_dung if isinstance(nguoi_dung, str) else (
            f"{nguoi_dung.ho_ten}\n{nguoi_dung.ten_vai_tro}" if nguoi_dung else "")
        self.moi_truong, self.khoa, self.khi_dang_xuat = moi_truong, khoa, khi_dang_xuat
        self.dang_dang_xuat = False
        self.setWindowTitle("Quản lý thi đua – khen thưởng · UBND xã Chiềng Hặc")
        self.setStyleSheet(STYLE)
        self._dung(c)
        msg = ("Dữ liệu lưu trên máy này, đã mã hóa, không kết nối Internet." if khoa else
               "CHẾ ĐỘ THỬ: dữ liệu chưa mã hóa, chỉ dùng dữ liệu giả.")
        self.statusBar().showMessage(msg)
        # khóa phiên khi không thao tác
        self.hen_gio = QTimer(self); self.hen_gio.setSingleShot(True)
        self.hen_gio.setInterval(self.PHUT_KHOA * 60 * 1000)
        self.hen_gio.timeout.connect(self.khoa_phien)
        self._bo_dem = _BoDemNhanRoi(self.hen_gio)
        if self.nguoi_dung is not None:
            from PySide6.QtWidgets import QApplication
            QApplication.instance().installEventFilter(self._bo_dem)
            self.hen_gio.start()

    def _dung(self, c) -> None:
        from qlkt.ui.quan_tri import TrangQuanTri   # tránh import vòng
        self.nv = NghiepVu(c, self.nguoi_dung.id if self.nguoi_dung else None)
        _vai_tro_hien_tai[0] = self.nv.vai_tro
        goc = QWidget(); h = QHBoxLayout(goc); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(0)
        trai = QWidget(); trai.setStyleSheet("background:#12355b")
        tv = QVBoxLayout(trai); tv.setContentsMargins(0, 12, 0, 12)
        logo = QLabel("  QL THI ĐUA –\n  KHEN THƯỞNG")
        logo.setStyleSheet("color:white;font-weight:bold;font-size:12pt;padding:4px 10px 14px 10px")
        tv.addWidget(logo)
        self.menu = QListWidget(); self.menu.setObjectName("sidebar"); self.menu.setFixedWidth(190)
        tv.addWidget(self.menu, 1)
        nd = QLabel(self.ten_hien); nd.setStyleSheet("color:#c9d6e3;padding:6px 10px"); nd.setWordWrap(True)
        tv.addWidget(nd)
        if self.nguoi_dung is not None:
            kieu = "color:#c9d6e3;background:transparent;border:1px solid #3d6a99;margin:2px 10px;padding:4px"
            for t, ham in (("Đổi mật khẩu", self.doi_mat_khau), ("Đăng xuất", self.dang_xuat)):
                b = QPushButton(t); b.setStyleSheet(kieu); b.clicked.connect(ham); tv.addWidget(b)
        self.stack = QStackedWidget()
        trang = list(self.TRANG)
        for ten, cls in trang:
            self.menu.addItem(ten)
            w = cls(self.nv); w.layout().setContentsMargins(16, 12, 16, 12)
            self.stack.addWidget(w)
        if any(self.nv.co_quyen(q) for q in ("nguoi_dung", "sao_luu", "khoi_phuc")):
            self.menu.addItem("Quản trị")
            w = TrangQuanTri(self.nv, self); w.layout().setContentsMargins(16, 12, 16, 12)
            self.stack.addWidget(w)
        self.menu.currentRowChanged.connect(self._doi_trang)
        self.menu.setCurrentRow(0)
        h.addWidget(trai); h.addWidget(self.stack, 1)
        cu = self.centralWidget()
        self.setCentralWidget(goc)
        if cu is not None:
            cu.deleteLater()

    def _doi_trang(self, i: int) -> None:
        self.stack.setCurrentIndex(i)
        self.stack.widget(i).nap()

    @property
    def c(self):
        return self.nv.c

    def thay_ket_noi(self, c) -> None:
        """Sau khi khôi phục: dựng lại các trang với kết nối mới."""
        self._dung(c)

    # ------------------------------------------------------------ tài khoản, phiên
    def doi_mat_khau(self) -> None:
        from qlkt.ui.dang_nhap import HopThoaiDoiMatKhau
        HopThoaiDoiMatKhau(self.c, self.nguoi_dung, parent=self).exec()

    def khoa_phien(self) -> None:
        from qlkt.ui.dang_nhap import HopThoaiDangNhap
        if self.nguoi_dung is None or not self.isVisible():
            return
        self.hen_gio.stop()
        self.centralWidget().setVisible(False)
        self.nv.ghi_nhat_ky("khoa_phien", "nguoi_dung", self.nguoi_dung.id); self.c.commit()
        d = HopThoaiDangNhap(self.c, co_dinh=self.nguoi_dung, parent=self)
        if d.exec():
            self.centralWidget().setVisible(True)
            self.hen_gio.start()
        else:
            self.dang_xuat()

    def dang_xuat(self) -> None:
        self.nv.ghi_nhat_ky("dang_xuat", "nguoi_dung", self.nguoi_dung.id if self.nguoi_dung else None)
        self.c.commit()
        self.dang_dang_xuat = True
        self.close()

    def closeEvent(self, e) -> None:  # noqa: N802
        from PySide6.QtWidgets import QApplication
        QApplication.instance().removeEventFilter(self._bo_dem)
        self.hen_gio.stop()
        if self.moi_truong is not None:
            try:
                sao_luu.sao_luu(self.c, self.khoa, self.moi_truong.sao_luu, "tu-dong", self.moi_truong.du_lieu,
                                self.nv.nguoi_dung_id)
            except Exception as loi:  # noqa: BLE001
                QMessageBox.warning(self, "Chưa sao lưu được", f"Sao lưu tự động khi thoát bị lỗi: {loi}")
        super().closeEvent(e)
        if self.dang_dang_xuat and self.khi_dang_xuat:
            QTimer.singleShot(0, self.khi_dang_xuat)   # mở lại màn đăng nhập sau khi cửa sổ đã đóng hẳn
