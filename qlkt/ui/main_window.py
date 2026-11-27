"""Cửa sổ chính (bản mẫu bước 1: xem dữ liệu, chưa sửa/nhập)."""
from __future__ import annotations

import os
import sqlite3
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QListWidget, QMainWindow, QPushButton, QSplitter, QStackedWidget,
    QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

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


def o_trang_thai(ma: str) -> QTableWidgetItem:
    it = QTableWidgetItem(TRANG_THAI.get(ma, ma))
    it.setForeground(QColor(MAU_TRANG_THAI.get(ma, "#000")))
    f = QFont(); f.setBold(True); it.setFont(f)
    return it


def tieu_de(text: str) -> QLabel:
    lb = QLabel(text); lb.setObjectName("tieuDe")
    return lb


def nut_chua_lam(text: str, buoc: str) -> QPushButton:
    b = QPushButton(text)
    b.setEnabled(False)
    b.setToolTip(f"Sẽ làm ở {buoc}")
    return b


# ---------------------------------------------------------------- Tổng quan
class TrangTongQuan(QWidget):
    def __init__(self, c: sqlite3.Connection):
        super().__init__()
        self.c = c
        v = QVBoxLayout(self)
        v.addWidget(tieu_de("Tổng quan"))
        self.canh_bao = QLabel(); self.canh_bao.setObjectName("canhBao"); self.canh_bao.setWordWrap(True)
        v.addWidget(self.canh_bao)
        self.luoi = QGridLayout(); v.addLayout(self.luoi)
        v.addWidget(QLabel("<b>Hạn sắp tới và quá hạn</b>"))
        self.bang_han = bang(["Hạn", "Còn lại", "Nội dung", "Liên quan"])
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
        c, hn = self.c, hom_nay()
        nam = hn[:4]
        dang_xl = c.execute("SELECT COUNT(*) FROM ho_so WHERE da_xoa=0 AND trang_thai IN "
                            "('tiep_nhan','tra_lai','da_trinh')").fetchone()[0]
        qd = c.execute("SELECT COUNT(*) FROM ho_so WHERE da_xoa=0 AND trang_thai='da_co_qd' "
                       "AND substr(qd_ngay,1,4)=?", (nam,)).fetchone()[0]
        luot = c.execute("SELECT COUNT(*), COALESCE(SUM(so_tien),0) FROM v_lich_su_khen_thuong "
                         "WHERE nam=?", (int(nam),)).fetchone()

        han = c.execute("""
            SELECT han, tieu_de, COALESCE(pt.ten, hs.trich_yeu, '') AS lq FROM han_cong_viec h
            LEFT JOIN phong_trao pt ON pt.id=h.phong_trao_id
            LEFT JOIN ho_so hs ON hs.id=h.ho_so_id WHERE h.da_xong=0
            UNION ALL
            SELECT han_xu_ly, 'Xử lý hồ sơ: ' || trich_yeu, d.ten FROM ho_so hs
            JOIN don_vi d ON d.id=hs.don_vi_id
            WHERE hs.da_xoa=0 AND han_xu_ly IS NOT NULL AND trang_thai IN ('tiep_nhan','tra_lai','da_trinh')
            ORDER BY 1""").fetchall()
        rows, qua, sap = [], 0, 0
        d0 = date.fromisoformat(hn)
        for r in han:
            con = (date.fromisoformat(r[0]) - d0).days
            it = QTableWidgetItem("Quá hạn %d ngày" % -con if con < 0 else
                                  ("Hôm nay" if con == 0 else f"{con} ngày"))
            if con < 0:
                it.setForeground(QColor("#b91c1c")); qua += 1
            elif con <= 3:
                it.setForeground(QColor("#c2410c")); sap += 1
            rows.append([ngay_vn(r[0]), it, r[1], r[2]])
        do_du_lieu(self.bang_han, rows)

        self._the(0, str(dang_xl), "Hồ sơ đang xử lý", "#1f6feb")
        self._the(1, str(sap + qua), "Việc sắp đến hạn / quá hạn", "#c2410c" if qua or sap else "#15803d")
        self._the(2, str(qd), f"Quyết định khen thưởng năm {nam}", "#15803d")
        self._the(3, tien(luot[1]), f"Tiền thưởng năm {nam} (đồng, {luot[0]} lượt)", "#12355b")
        self.canh_bao.setText(
            f"⚠ Có {qua} việc quá hạn và {sap} việc đến hạn trong 3 ngày tới." if qua or sap
            else "Không có việc nào sắp đến hạn.")


# ---------------------------------------------------------------- Hồ sơ đề nghị
class TrangHoSo(QWidget):
    def __init__(self, c: sqlite3.Connection):
        super().__init__()
        self.c = c
        v = QVBoxLayout(self)
        v.addWidget(tieu_de("Hồ sơ đề nghị khen thưởng"))
        thanh = QHBoxLayout()
        self.loc = QComboBox(); self.loc.addItem("Tất cả trạng thái", None)
        for k, t in TRANG_THAI.items():
            self.loc.addItem(t, k)
        self.loc.currentIndexChanged.connect(self.nap)
        thanh.addWidget(QLabel("Lọc:")); thanh.addWidget(self.loc); thanh.addStretch()
        thanh.addWidget(nut_chua_lam("Nhập hồ sơ từ Excel…", "bước 2"))
        thanh.addWidget(nut_chua_lam("+ Hồ sơ mới", "bước 2"))
        v.addLayout(thanh)

        sp = QSplitter(Qt.Vertical)
        self.ds = bang(["Trạng thái", "Đơn vị đề nghị", "Trích yếu", "TTr đơn vị", "TTr VH-XH",
                        "Quyết định", "Hạn xử lý"], gian=2)
        self.ds.itemSelectionChanged.connect(self.chon)
        sp.addWidget(self.ds)

        ct = QGroupBox("Chi tiết hồ sơ")
        cv = QVBoxLayout(ct)
        self.thong_tin = QLabel(); self.thong_tin.setWordWrap(True)
        self.thong_tin.setTextFormat(Qt.RichText)
        cv.addWidget(self.thong_tin)
        self.ds_dt = bang(["STT", "Loại", "Tên", "Chức vụ, đơn vị", "Thành tích", "Kết quả", "Tiền thưởng"], gian=4)
        cv.addWidget(self.ds_dt)
        self.tong = QLabel(); cv.addWidget(self.tong)
        nut = QHBoxLayout()
        for t in ("Sinh Tờ trình (Word)", "Sinh dự thảo QĐ (Word)", "Xuất danh sách (Excel)",
                  "Xuất DS chi trả (Excel)"):
            nut.addWidget(nut_chua_lam(t, "bước 3"))
        nut.addWidget(nut_chua_lam("Trả lại bổ sung", "bước 2"))
        nut.addStretch()
        cv.addLayout(nut)
        sp.addWidget(ct)
        sp.setSizes([260, 420])
        v.addWidget(sp)
        self.nap()

    def nap(self) -> None:
        tt = self.loc.currentData()
        sql = ("SELECT hs.*, d.ten AS dv FROM ho_so hs JOIN don_vi d ON d.id=hs.don_vi_id "
               "WHERE hs.da_xoa=0" + (" AND trang_thai=?" if tt else "") + " ORDER BY hs.id DESC")
        rs = self.c.execute(sql, (tt,) if tt else ()).fetchall()
        do_du_lieu(self.ds, [[o_trang_thai(r["trang_thai"]), r["dv"], r["trich_yeu"],
                              " ".join(filter(None, [r["ttr_dv_so"], ngay_vn(r["ttr_dv_ngay"])])),
                              " ".join(filter(None, [r["ttr_vhxh_so"], ngay_vn(r["ttr_vhxh_ngay"])])),
                              " ".join(filter(None, [r["qd_so"], ngay_vn(r["qd_ngay"])])),
                              ngay_vn(r["han_xu_ly"])] for r in rs], [r["id"] for r in rs])
        if rs:
            self.ds.selectRow(0)

    def chon(self) -> None:
        sel = self.ds.selectedItems()
        if not sel:
            return
        hs_id = self.ds.item(sel[0].row(), 0).data(Qt.UserRole)
        r = self.c.execute("SELECT hs.*, d.ten dv, ht.ten ht, pt.ten pt FROM ho_so hs "
                           "JOIN don_vi d ON d.id=hs.don_vi_id JOIN hinh_thuc ht ON ht.id=hs.hinh_thuc_id "
                           "LEFT JOIN phong_trao pt ON pt.id=hs.phong_trao_id WHERE hs.id=?",
                           (hs_id,)).fetchone()
        tra_lai = (f"<br><span style='color:#c2410c'><b>Lý do trả lại:</b> {r['ly_do_tra_lai']}</span>"
                   if r["ly_do_tra_lai"] else "")
        self.thong_tin.setText(
            f"<b>{r['trich_yeu']}</b><br>"
            f"Phong trào: {r['pt'] or ''} &nbsp;|&nbsp; Hình thức: {r['ht']} &nbsp;|&nbsp; Đơn vị: {r['dv']}<br>"
            + (f"Biên bản họp: {r['bb_so']} ngày {ngay_vn(r['bb_ngay'])}, "
               f"dự {r['bb_so_du'] or '?'}/{r['bb_tong_so'] or '?'}, nhất trí {r['bb_ty_le'] or '?'}"
               if r["bb_ngay"] else "<span style='color:#c2410c'>Chưa có biên bản họp xét</span>")
            + tra_lai)
        ds = self.c.execute("SELECT hd.*, dt.loai, dt.ten, dt.danh_xung, dt.chuc_vu, dt.don_vi_cong_tac "
                            "FROM ho_so_doi_tuong hd JOIN doi_tuong dt ON dt.id=hd.doi_tuong_id "
                            "WHERE hd.ho_so_id=? ORDER BY dt.loai DESC, hd.thu_tu, hd.id", (hs_id,)).fetchall()
        kq = {"de_nghi": "Đề nghị", "duoc_khen": "Được khen", "khong_duoc": "Không được khen"}
        do_du_lieu(self.ds_dt, [[i + 1, "Tập thể" if d["loai"] == "tap_the" else "Cá nhân",
                                 " ".join(filter(None, [d["danh_xung"], d["ten"]])),
                                 ", ".join(filter(None, [d["chuc_vu"], d["don_vi_cong_tac"]])),
                                 d["tom_tat_thanh_tich"], kq[d["ket_qua"]], tien(d["so_tien"])]
                                for i, d in enumerate(ds)])
        n_tt = sum(1 for d in ds if d["loai"] == "tap_the")
        tong = sum(d["so_tien"] or 0 for d in ds)
        self.tong.setText(f"<b>{n_tt} tập thể, {len(ds) - n_tt} cá nhân. "
                          f"Tổng tiền thưởng dự kiến: {tien(tong)} đồng</b>")


# ---------------------------------------------------------------- Đối tượng
class TrangDoiTuong(QWidget):
    def __init__(self, c: sqlite3.Connection):
        super().__init__()
        self.c = c
        v = QVBoxLayout(self)
        v.addWidget(tieu_de("Cá nhân, tập thể"))
        thanh = QHBoxLayout()
        self.tim = QLineEdit(); self.tim.setPlaceholderText("Tìm theo tên, đơn vị…")
        self.tim.textChanged.connect(self.nap)
        self.loai = QComboBox()
        for t, k in (("Tất cả", None), ("Cá nhân", "ca_nhan"), ("Tập thể", "tap_the")):
            self.loai.addItem(t, k)
        self.loai.currentIndexChanged.connect(self.nap)
        thanh.addWidget(self.tim, 1); thanh.addWidget(self.loai)
        thanh.addWidget(nut_chua_lam("+ Thêm", "bước 2"))
        thanh.addWidget(nut_chua_lam("Nhập từ Excel…", "bước 2"))
        v.addLayout(thanh)
        sp = QSplitter(Qt.Vertical)
        self.ds = bang(["Loại", "Tên", "Chức vụ", "Đơn vị công tác", "Số lần được khen"], gian=1)
        self.ds.itemSelectionChanged.connect(self.chon)
        sp.addWidget(self.ds)
        g = QGroupBox("Lịch sử khen thưởng")
        gv = QVBoxLayout(g)
        self.ls = bang(["Năm", "Hình thức", "Nội dung", "Quyết định", "Tiền thưởng"], gian=2)
        gv.addWidget(self.ls)
        sp.addWidget(g)
        v.addWidget(sp)
        self.nap()

    def nap(self) -> None:
        q = f"%{self.tim.text().strip()}%"
        loai = self.loai.currentData()
        rs = self.c.execute(
            "SELECT dt.*, (SELECT COUNT(*) FROM v_lich_su_khen_thuong v WHERE v.doi_tuong_id=dt.id) n "
            "FROM doi_tuong dt WHERE da_xoa=0 AND (ten LIKE ? OR COALESCE(don_vi_cong_tac,'') LIKE ?)"
            + (" AND loai=?" if loai else "") + " ORDER BY loai, ten",
            (q, q, loai) if loai else (q, q)).fetchall()
        do_du_lieu(self.ds, [["Tập thể" if r["loai"] == "tap_the" else "Cá nhân", r["ten"], r["chuc_vu"],
                              r["don_vi_cong_tac"], r["n"]] for r in rs], [r["id"] for r in rs])

    def chon(self) -> None:
        sel = self.ds.selectedItems()
        if not sel:
            return
        dt = self.ds.item(sel[0].row(), 0).data(Qt.UserRole)
        rs = self.c.execute("SELECT * FROM v_lich_su_khen_thuong WHERE doi_tuong_id=? ORDER BY qd_ngay DESC",
                            (dt,)).fetchall()
        do_du_lieu(self.ls, [[r["nam"], r["hinh_thuc"], r["trich_yeu"],
                              f"{r['qd_so']} ngày {ngay_vn(r['qd_ngay'])}", tien(r["so_tien"])] for r in rs])


# ---------------------------------------------------------------- Phong trào
class TrangPhongTrao(QWidget):
    def __init__(self, c: sqlite3.Connection):
        super().__init__()
        v = QVBoxLayout(self)
        v.addWidget(tieu_de("Phong trào thi đua"))
        thanh = QHBoxLayout(); thanh.addStretch()
        thanh.addWidget(nut_chua_lam("Xuất mẫu Excel gửi các phòng", "bước 2"))
        thanh.addWidget(nut_chua_lam("+ Phong trào mới", "bước 2"))
        v.addLayout(thanh)
        t = bang(["Năm", "Tên phong trào", "Hạn nộp hồ sơ", "Số hồ sơ", "Đã có QĐ"])
        rs = c.execute("SELECT pt.*, (SELECT COUNT(*) FROM ho_so h WHERE h.phong_trao_id=pt.id AND h.da_xoa=0) n,"
                       "(SELECT COUNT(*) FROM ho_so h WHERE h.phong_trao_id=pt.id AND h.trang_thai='da_co_qd') q "
                       "FROM phong_trao pt WHERE da_xoa=0 ORDER BY nam DESC, id DESC").fetchall()
        do_du_lieu(t, [[r["nam"], r["ten"], ngay_vn(r["han_nop_ho_so"]), r["n"], r["q"]] for r in rs])
        v.addWidget(t)


# ---------------------------------------------------------------- Báo cáo
class TrangBaoCao(QWidget):
    def __init__(self, c: sqlite3.Connection):
        super().__init__()
        v = QVBoxLayout(self)
        v.addWidget(tieu_de("Báo cáo, thống kê"))
        t = bang(["Năm", "Hình thức", "Tập thể", "Cá nhân", "Tổng tiền (đồng)"])
        rs = c.execute("SELECT nam, hinh_thuc, SUM(loai='tap_the') tt, SUM(loai='ca_nhan') cn, "
                       "SUM(so_tien) tien FROM v_lich_su_khen_thuong GROUP BY nam, hinh_thuc "
                       "ORDER BY nam DESC").fetchall()
        do_du_lieu(t, [[r["nam"], r["hinh_thuc"], r["tt"], r["cn"], tien(r["tien"])] for r in rs])
        v.addWidget(QLabel("<b>Tổng hợp khen thưởng theo năm</b>"))
        v.addWidget(t)
        nut = QHBoxLayout()
        for s in ("Xuất báo cáo Excel", "Xuất dữ liệu liên thông (CSV/JSON)"):
            nut.addWidget(nut_chua_lam(s, "bước 3"))
        nut.addStretch()
        v.addLayout(nut)


# ---------------------------------------------------------------- Danh mục
class TrangDanhMuc(QWidget):
    def __init__(self, c: sqlite3.Connection):
        super().__init__()
        v = QVBoxLayout(self)
        v.addWidget(tieu_de("Danh mục và cấu hình"))
        tabs = QTabWidget()
        t1 = bang(["Hình thức", "Loại", "Hệ số cá nhân", "Hệ số tập thể", "Căn cứ"])
        do_du_lieu(t1, [[r["ten"], "Danh hiệu" if r["loai"] == "danh_hieu" else "Khen thưởng",
                         r["he_so_ca_nhan"], r["he_so_tap_the"], r["can_cu"]]
                        for r in c.execute("SELECT * FROM hinh_thuc")])
        tabs.addTab(t1, "Hình thức khen thưởng")
        t2 = bang(["Áp dụng từ", "Mức (đồng/tháng)", "Căn cứ"])
        do_du_lieu(t2, [[ngay_vn(r["ap_dung_tu"]), tien(r["muc"]), r["can_cu"]]
                        for r in c.execute("SELECT * FROM luong_co_so ORDER BY ap_dung_tu DESC")])
        tabs.addTab(t2, "Mức lương cơ sở")
        t3 = bang(["Đơn vị", "Loại"])
        do_du_lieu(t3, [[r["ten"], r["loai"]] for r in c.execute("SELECT * FROM don_vi ORDER BY ten")])
        tabs.addTab(t3, "Đơn vị đề nghị")
        t4 = bang(["Thứ tự", "Nội dung căn cứ", "Dùng cho"])
        do_du_lieu(t4, [[r["thu_tu"], r["noi_dung"], r["dung_cho"]]
                        for r in c.execute("SELECT * FROM can_cu ORDER BY thu_tu")])
        tabs.addTab(t4, "Căn cứ pháp lý")
        v.addWidget(tabs)
        lb = QLabel("Hệ số, mức lương cơ sở và căn cứ do cán bộ thường trực nhập theo văn bản hiện hành.")
        lb.setObjectName("nhan")
        v.addWidget(lb)


class CuaSoChinh(QMainWindow):
    TRANG = [("Tổng quan", TrangTongQuan), ("Hồ sơ đề nghị", TrangHoSo), ("Cá nhân, tập thể", TrangDoiTuong),
             ("Phong trào", TrangPhongTrao), ("Báo cáo", TrangBaoCao), ("Danh mục", TrangDanhMuc)]

    def __init__(self, c: sqlite3.Connection, ten_nguoi_dung: str = ""):
        super().__init__()
        self.setWindowTitle("Quản lý thi đua – khen thưởng · UBND xã Chiềng Hặc")
        self.setStyleSheet(STYLE)
        goc = QWidget(); h = QHBoxLayout(goc); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(0)
        trai = QWidget(); trai.setStyleSheet("background:#12355b")
        tv = QVBoxLayout(trai); tv.setContentsMargins(0, 12, 0, 12)
        logo = QLabel("  QL THI ĐUA –\n  KHEN THƯỞNG")
        logo.setStyleSheet("color:white;font-weight:bold;font-size:12pt;padding:4px 10px 14px 10px")
        tv.addWidget(logo)
        self.menu = QListWidget(); self.menu.setObjectName("sidebar"); self.menu.setFixedWidth(190)
        tv.addWidget(self.menu, 1)
        nd = QLabel(f"  {ten_nguoi_dung}"); nd.setStyleSheet("color:#c9d6e3;padding:6px")
        tv.addWidget(nd)
        self.stack = QStackedWidget()
        for ten, cls in self.TRANG:
            self.menu.addItem(ten)
            w = cls(c); w.layout().setContentsMargins(16, 12, 16, 12)
            self.stack.addWidget(w)
        self.menu.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.menu.setCurrentRow(0)
        h.addWidget(trai); h.addWidget(self.stack, 1)
        self.setCentralWidget(goc)
        self.statusBar().showMessage("Dữ liệu lưu trên máy này, không kết nối Internet.")
