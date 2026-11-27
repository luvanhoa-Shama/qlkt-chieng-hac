"""Trang Quản trị: tài khoản người dùng, sao lưu – khôi phục, mã hóa."""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog, QGroupBox, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout,
)

from qlkt.bao_mat import khoa as kh
from qlkt.bao_mat.phan_quyen import QUYEN, VAI_TRO, MO_TA_QUYEN
from qlkt.db.database import SaiKhoa
from qlkt.services import sao_luu, tai_khoan
from qlkt.ui.dang_nhap import HopThoaiMatKhauKhoiPhuc
from qlkt.ui.hop_thoai import HopThoaiNhap, Truong
from qlkt.ui.main_window import Trang, bang, chay, do_du_lieu, hoi, id_dang_chon, nut, tieu_de

LUA_CHON_VAI_TRO = [(t, k) for k, t in VAI_TRO.items()]


def _mo_thu_muc(p: Path) -> None:
    if sys.platform == "win32":
        os.startfile(str(p))  # noqa: S606 - mở thư mục sao lưu bằng Explorer
    else:
        subprocess.Popen(["xdg-open", str(p)])  # noqa: S603,S607


class TrangQuanTri(Trang):
    def __init__(self, nv, cua_so):
        super().__init__(nv)
        self.cs = cua_so
        v = QVBoxLayout(self)
        v.addWidget(tieu_de("Quản trị"))

        # --- tài khoản
        self.g_tk = QGroupBox("Tài khoản người dùng")
        gv = QVBoxLayout(self.g_tk)
        hang = QHBoxLayout()
        vt = "; ".join(f"<b>{VAI_TRO[k]}</b>: " + ", ".join(MO_TA_QUYEN[q].lower() for q in MO_TA_QUYEN
                                                         if q in QUYEN[k] and q != "xem")
                       for k in ("thuong_truc", "ke_toan", "lanh_dao"))
        ghi = QLabel("Mỗi người một tài khoản, không dùng chung. " + vt + ". Lãnh đạo xem tất cả.")
        ghi.setWordWrap(True); ghi.setStyleSheet("color:#57606a")
        gv.addWidget(ghi)
        hang.addStretch()
        for t, h in (("+ Thêm tài khoản", self.them), ("Sửa", self.sua), ("Đặt lại mật khẩu…", self.dat_lai),
                     ("Mở khóa", self.mo_khoa)):
            hang.addWidget(nut(t, h))
        gv.addLayout(hang)
        self.ds_tk = bang(["Tên đăng nhập", "Họ tên", "Vai trò", "Trạng thái", "Đăng nhập gần nhất"], gian=1)
        self.ds_tk.doubleClicked.connect(self.sua)
        gv.addWidget(self.ds_tk)
        v.addWidget(self.g_tk, 1)

        # --- sao lưu
        self.g_sl = QGroupBox("Sao lưu, khôi phục")
        sv = QVBoxLayout(self.g_sl)
        self.nhan_sl = QLabel(); self.nhan_sl.setWordWrap(True)
        sv.addWidget(self.nhan_sl)
        hang = QHBoxLayout()
        hang.addWidget(nut("Sao lưu ngay", self.sao_luu_ngay, chinh=True))
        hang.addWidget(nut("Sao lưu ra USB/thư mục khác…", self.sao_luu_ra))
        hang.addWidget(nut("Mở thư mục sao lưu", lambda: _mo_thu_muc(self.cs.moi_truong.sao_luu)))
        hang.addStretch()
        self.nut_kp = nut("Khôi phục bản đã chọn…", self.khoi_phuc_chon)
        self.nut_kp_tep = nut("Khôi phục từ tệp khác…", self.khoi_phuc_tep)
        hang.addWidget(self.nut_kp); hang.addWidget(self.nut_kp_tep)
        sv.addLayout(hang)
        self.ds_sl = bang(["Bản sao lưu", "Thời gian", "Dung lượng"], gian=0)
        sv.addWidget(self.ds_sl)
        v.addWidget(self.g_sl, 1)

        # --- mã hóa
        self.g_mh = QGroupBox("Mã hóa dữ liệu")
        mv = QHBoxLayout(self.g_mh)
        self.nhan_mh = QLabel(); self.nhan_mh.setWordWrap(True)
        mv.addWidget(self.nhan_mh, 1)
        self.nut_doi_kp = nut("Đổi mật khẩu khôi phục…", self.doi_mat_khau_khoi_phuc)
        mv.addWidget(self.nut_doi_kp)
        v.addWidget(self.g_mh)

        self.g_tk.setVisible(nv.co_quyen("nguoi_dung"))
        self.g_mh.setVisible(nv.co_quyen("nguoi_dung"))
        self.nut_kp.setVisible(nv.co_quyen("khoi_phuc"))
        self.nut_kp_tep.setVisible(nv.co_quyen("khoi_phuc"))
        self.nap()

    # ------------------------------------------------------------ nạp
    def nap(self) -> None:
        if self.nv.co_quyen("nguoi_dung"):
            rs = self.c.execute("SELECT * FROM nguoi_dung ORDER BY dang_dung DESC, ten_dang_nhap").fetchall()
            do_du_lieu(self.ds_tk, [[r["ten_dang_nhap"], r["ho_ten"], VAI_TRO.get(r["vai_tro"], r["vai_tro"]),
                                     "Ngừng sử dụng" if not r["dang_dung"] else
                                     ("Bị khóa" if r["bi_khoa"] else
                                      ("Chờ đổi mật khẩu" if r["phai_doi_mat_khau"] else "Đang dùng")),
                                     r["dang_nhap_cuoi"] or ""] for r in rs], [r["id"] for r in rs])
        mt = self.cs.moi_truong
        if mt is None:
            self.g_sl.setEnabled(False)
            self.nhan_sl.setText("Chế độ thử: không có thư mục sao lưu.")
        else:
            ds = sao_luu.danh_sach(mt.sao_luu)
            self.nhan_sl.setText(
                f"Thư mục sao lưu: <b>{mt.sao_luu}</b><br>Tự động sao lưu khi mở phần mềm (mỗi ngày một lần) và "
                f"khi thoát; giữ {sao_luu.GIU_TU_DONG} bản tự động gần nhất. Nên chép thêm ra USB mỗi tuần, cất "
                "nơi an toàn. Bản sao lưu đã mã hóa, mở được bằng mật khẩu khôi phục.")
            do_du_lieu(self.ds_sl, [[p.name, datetime.fromtimestamp(p.stat().st_mtime).strftime("%d/%m/%Y %H:%M"),
                                     f"{p.stat().st_size / 1024:,.0f} KB".replace(",", ".")] for p in ds],
                       [str(p) for p in ds])
        if self.cs.khoa is None:
            self.nhan_mh.setText("<b style='color:#b91c1c'>CHƯA MÃ HÓA</b> — đang chạy chế độ thử với dữ liệu "
                                 "giả. Không nhập dữ liệu thật ở chế độ này.")
            self.nut_doi_kp.setEnabled(False)
        else:
            self.nhan_mh.setText("Tệp CSDL được mã hóa AES-256 (SQLCipher). Khóa được Windows bảo vệ theo tài "
                                 "khoản đăng nhập máy và bằng mật khẩu khôi phục (giao Lãnh đạo giữ).")

    # ------------------------------------------------------------ tài khoản
    def _truong(self, moi: bool) -> list[Truong]:
        t = [Truong("ten_dang_nhap", "Tên đăng nhập", bat_buoc=True, goi_y="Không dấu, không cách: vd thuongtruc"),
             Truong("ho_ten", "Họ tên", bat_buoc=True),
             Truong("vai_tro", "Vai trò", "chon", bat_buoc=True, lua_chon=LUA_CHON_VAI_TRO)]
        if moi:
            t.append(Truong("mat_khau", "Mật khẩu tạm", "mat_khau", bat_buoc=True,
                            goi_y="Người dùng phải đổi khi đăng nhập lần đầu"))
        else:
            t = t[1:] + [Truong("dang_dung", "Đang sử dụng", "co_khong")]
        return t

    def them(self) -> None:
        d = HopThoaiNhap("Thêm tài khoản", self._truong(True), {"vai_tro": "thuong_truc"}, parent=self,
                         ghi_chu="Giao mật khẩu tạm trực tiếp cho người dùng, không gửi qua tin nhắn/mạng xã hội.")
        if d.exec():
            k = d.ket_qua
            if chay(self, tai_khoan.them_nguoi_dung, self.c, self.nv.nguoi_dung_id, k["ten_dang_nhap"], k["ho_ten"],
                    k["vai_tro"], k["mat_khau"])[0]:
                self.nap()

    def sua(self) -> None:
        id_ = id_dang_chon(self.ds_tk)
        if not id_:
            return
        r = dict(self.c.execute("SELECT * FROM nguoi_dung WHERE id=?", (id_,)).fetchone())
        d = HopThoaiNhap(f"Sửa tài khoản {r['ten_dang_nhap']}", self._truong(False), r, parent=self,
                         ghi_chu="Không xóa tài khoản (để giữ nhật ký); bỏ chọn \"Đang sử dụng\" khi người đó "
                                 "chuyển công tác.")
        if d.exec():
            k = d.ket_qua
            if chay(self, tai_khoan.sua_nguoi_dung, self.c, self.nv.nguoi_dung_id, id_, k["ho_ten"], k["vai_tro"],
                    bool(k.get("dang_dung")))[0]:
                self.nap()

    def dat_lai(self) -> None:
        id_ = id_dang_chon(self.ds_tk)
        if not id_:
            return
        d = HopThoaiNhap("Đặt lại mật khẩu", [Truong("mat_khau", "Mật khẩu tạm", "mat_khau", bat_buoc=True)],
                         parent=self, ghi_chu="Tài khoản được mở khóa; người dùng phải đổi mật khẩu khi đăng nhập.")
        if d.exec() and chay(self, tai_khoan.dat_lai_mat_khau, self.c, self.nv.nguoi_dung_id, id_,
                             d.ket_qua["mat_khau"])[0]:
            self.nap()

    def mo_khoa(self) -> None:
        id_ = id_dang_chon(self.ds_tk)
        if id_ and chay(self, tai_khoan.mo_khoa, self.c, self.nv.nguoi_dung_id, id_)[0]:
            self.nap()

    # ------------------------------------------------------------ sao lưu
    def sao_luu_ngay(self) -> None:
        mt = self.cs.moi_truong
        ok, p = chay(self, self._sao_luu, mt.sao_luu, "tay")
        if ok:
            QMessageBox.information(self, "Đã sao lưu", f"Đã lưu:\n{p}")
            self.nap()

    def _sao_luu(self, thu_muc, loai):
        self.nv.kiem_quyen("sao_luu")
        return sao_luu.sao_luu(self.c, self.cs.khoa, thu_muc, loai, self.cs.moi_truong.du_lieu,
                               self.nv.nguoi_dung_id)

    def sao_luu_ra(self) -> None:
        p = QFileDialog.getExistingDirectory(self, "Chọn thư mục (USB) để lưu bản sao")
        if not p:
            return
        ok, f = chay(self, self._sao_luu, p, "tay")
        if ok:
            QMessageBox.information(self, "Đã sao lưu",
                                    f"Đã lưu:\n{f}\n\nKèm tệp khoa-….json trong cùng thư mục. Cất USB nơi an toàn; "
                                    "mở được bằng mật khẩu khôi phục.")

    def khoi_phuc_chon(self) -> None:
        p = id_dang_chon(self.ds_sl)
        if not p:
            QMessageBox.information(self, "Chọn bản sao lưu", "Chọn một bản sao lưu trong danh sách.")
            return
        self._khoi_phuc(Path(p))

    def khoi_phuc_tep(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "Chọn bản sao lưu", "", "Sao lưu QLKT (qlkt-*.db);;Tất cả (*)")
        if p:
            self._khoi_phuc(Path(p))

    def _khoi_phuc(self, p: Path) -> None:
        if not self.nv.co_quyen("khoi_phuc"):
            QMessageBox.warning(self, "Không có quyền", "Chỉ Quản trị được khôi phục dữ liệu.")
            return
        khoa_bs = self.cs.khoa
        try:
            tt = sao_luu.kiem_tra_ban_sao(p, khoa_bs)
        except SaiKhoa:
            d = HopThoaiMatKhauKhoiPhuc("Bản sao lưu này tạo ở máy khác hoặc lần cài khác. Nhập mật khẩu khôi phục "
                                        "của lần cài đó (tệp khoa-….json phải nằm cùng thư mục bản sao).", self)
            if not d.exec():
                return
            try:
                khoa_bs = sao_luu.tim_khoa_cho_ban_sao(p, d.mat_khau)
                tt = sao_luu.kiem_tra_ban_sao(p, khoa_bs)
            except (kh.LoiKhoa, ValueError, SaiKhoa) as e:
                QMessageBox.warning(self, "Không mở được", str(e))
                return
        except ValueError as e:
            QMessageBox.warning(self, "Không dùng được bản này", str(e))
            return
        if not hoi(self, f"Khôi phục từ:\n{p.name}\n({tt.so_ho_so} hồ sơ, {tt.so_doi_tuong} tập thể/cá nhân)\n\n"
                         "Dữ liệu hiện tại sẽ được sao lưu trước rồi bị THAY bằng bản này. Tiếp tục?"):
            return
        mt = self.cs.moi_truong
        try:
            moi = sao_luu.khoi_phuc(self.c, self.cs.khoa, mt.tep_csdl, p, mt.sao_luu, khoa_bs, mt.du_lieu,
                                    self.nv.nguoi_dung_id)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Khôi phục lỗi", f"{e}\n\nKhởi động lại phần mềm; dữ liệu trước khi khôi "
                                                       "phục đã được sao lưu (qlkt-truoc-khoi-phuc-…).")
            return
        QMessageBox.information(self, "Đã khôi phục", "Đã khôi phục. Phần mềm nạp lại dữ liệu.")
        self.cs.thay_ket_noi(moi)

    # ------------------------------------------------------------ mã hóa
    def doi_mat_khau_khoi_phuc(self) -> None:
        d = HopThoaiMatKhauKhoiPhuc("Mật khẩu mới thay cho mật khẩu cũ (các bản sao lưu cũ vẫn mở bằng mật khẩu "
                                    "CŨ). Ghi ra giấy, niêm phong, giao Lãnh đạo giữ.", self, dat_moi=True)
        if not d.exec():
            return
        try:
            kh.doi_mat_khau_khoi_phuc(self.cs.moi_truong.du_lieu, self.cs.khoa, d.mat_khau)
        except kh.LoiKhoa as e:
            QMessageBox.warning(self, "Không đổi được", str(e))
            return
        self.nv.ghi_nhat_ky("doi_mat_khau_khoi_phuc", "he_thong"); self.c.commit()
        QMessageBox.information(self, "Đã đổi", "Đã đổi mật khẩu khôi phục. Nên sao lưu ngay một bản mới.")
