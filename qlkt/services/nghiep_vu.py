"""Nghiệp vụ thêm/sửa/xóa và luồng hồ sơ. Mọi thay đổi đều ghi nhật ký.

Không xóa cứng dữ liệu nghiệp vụ: đối tượng, phong trào, hồ sơ chỉ đánh dấu da_xoa=1.
"""
from __future__ import annotations

import functools
import sqlite3
import unicodedata
from datetime import date

from qlkt.services.tien_thuong import luong_co_so_tai, tinh_tien


from qlkt.db.database import LOI_TRUNG
from qlkt.bao_mat.phan_quyen import MO_TA_QUYEN, co_quyen


class LoiNghiepVu(Exception):
    """Lỗi hiển thị được cho người dùng."""


# Luồng trạng thái hồ sơ được phép
CHUYEN_TRANG_THAI = {
    "tiep_nhan": {"tra_lai", "da_trinh"},
    "tra_lai": {"tiep_nhan", "da_trinh"},
    "da_trinh": {"da_co_qd", "khong_duyet", "tra_lai"},
    "da_co_qd": set(),
    "khong_duyet": set(),
}

COT_DOI_TUONG = ("loai", "ten", "danh_xung", "cap_bac", "nam_sinh", "gioi_tinh", "chuc_vu", "don_vi_cong_tac",
                 "don_vi_id", "nguoi_dai_dien", "so_tai_khoan", "ngan_hang", "ghi_chu")
COT_PHONG_TRAO = ("ten", "nam", "ngay_phat_dong", "han_nop_ho_so", "mo_ta")
COT_HO_SO = ("phong_trao_id", "don_vi_id", "hinh_thuc_id", "trich_yeu", "noi_dung_khen", "ttr_dv_so", "ttr_dv_ngay",
             "bb_so", "bb_ngay", "bb_to_chuc_hop", "bb_so_du", "bb_tong_so", "bb_ty_le",
             "han_xu_ly", "ghi_chu")
# Trường không ghi giá trị vào nhật ký
NHAY_CAM = {"so_tai_khoan"}
COT_STK = ("so_tai_khoan", "ngan_hang")


def chuan_hoa(s: str | None) -> str:
    """Chuẩn hóa để so trùng: NFC, bỏ khoảng trắng thừa, chữ thường."""
    return " ".join(unicodedata.normalize("NFC", s or "").split()).lower()


def ten_hien_thi(dt) -> str:
    """Tên in trên danh sách, QĐ: cá nhân có cấp bậc (LLVT) thì in cấp bậc, không thì Ông/Bà."""
    if dt["loai"] == "tap_the":
        return dt["ten"]
    tien_to = dt["cap_bac"] or dt["danh_xung"]
    return f"{tien_to} {dt['ten']}" if tien_to else dt["ten"]


def chuan_hoa_doi_tuong(d: dict) -> dict:
    """Tập thể không có Ông/Bà, cấp bậc; cá nhân chưa chọn Ông/Bà thì suy từ giới tính."""
    d = dict(d)
    if d.get("loai") == "tap_the":
        d["danh_xung"] = d["cap_bac"] = None
    elif not d.get("danh_xung") and d.get("gioi_tinh") in ("Nam", "Nữ"):
        d["danh_xung"] = "Ông" if d["gioi_tinh"] == "Nam" else "Bà"
    if d.get("danh_xung") not in (None, "Ông", "Bà"):
        raise LoiNghiepVu("Ô \"Ông/Bà\" chỉ nhận Ông hoặc Bà. Cấp bậc (Đại úy…) ghi ở ô Cấp bậc.")
    if d.get("cap_bac"):
        d["cap_bac"] = " ".join(str(d["cap_bac"]).split())
    return d


def can_quyen(quyen: str):
    """Chặn ở tầng nghiệp vụ: tài khoản không đủ quyền thì không thực hiện, dù giao diện có hiện nút."""
    def boc(ham):
        @functools.wraps(ham)
        def chay(self, *a, **kw):
            self.kiem_quyen(quyen)
            return ham(self, *a, **kw)
        return chay
    return boc


class NghiepVu:
    def __init__(self, conn: sqlite3.Connection, nguoi_dung_id: int | None = None):
        self.c = conn
        self.nguoi_dung_id = nguoi_dung_id
        self.vai_tro: str | None = None    # None = chạy nội bộ (kịch bản, kiểm thử)
        if nguoi_dung_id is not None:
            r = conn.execute("SELECT vai_tro FROM nguoi_dung WHERE id=?", (nguoi_dung_id,)).fetchone()
            if r is None:
                raise LoiNghiepVu("Không tìm thấy tài khoản.")
            self.vai_tro = r["vai_tro"]

    def co_quyen(self, quyen: str) -> bool:
        return co_quyen(self.vai_tro, quyen)

    def kiem_quyen(self, quyen: str) -> None:
        if not self.co_quyen(quyen):
            raise LoiNghiepVu(f"Tài khoản của anh/chị không có quyền: {MO_TA_QUYEN.get(quyen, quyen)}.")

    # ------------------------------------------------------------ tiện ích
    def ghi_nhat_ky(self, hanh_dong: str, bang: str | None = None, ban_ghi_id: int | None = None,
                    noi_dung: str | None = None) -> None:
        self.c.execute("INSERT INTO nhat_ky(nguoi_dung_id, hanh_dong, bang, ban_ghi_id, noi_dung) "
                       "VALUES (?,?,?,?,?)", (self.nguoi_dung_id, hanh_dong, bang, ban_ghi_id, noi_dung))

    @staticmethod
    def _mo_ta(d: dict) -> str:
        return "; ".join(f"{k}=" + ("***" if k in NHAY_CAM else str(v)) for k, v in d.items())

    def _them(self, bang: str, cot_hop_le: tuple, du_lieu: dict) -> int:
        d = {k: (v if v != "" else None) for k, v in du_lieu.items() if k in cot_hop_le}
        cot = ", ".join(d)
        cur = self.c.execute(f"INSERT INTO {bang}({cot}) VALUES ({', '.join('?' * len(d))})",
                             tuple(d.values()))
        self.ghi_nhat_ky("them", bang, cur.lastrowid, self._mo_ta(d))
        return cur.lastrowid

    def _sua(self, bang: str, cot_hop_le: tuple, id_: int, du_lieu: dict) -> None:
        d = {k: (v if v != "" else None) for k, v in du_lieu.items() if k in cot_hop_le}
        if not d:
            return
        cu = self.c.execute(f"SELECT * FROM {bang} WHERE id=?", (id_,)).fetchone()
        if cu is None:
            raise LoiNghiepVu("Không tìm thấy bản ghi cần sửa.")
        doi = {k: v for k, v in d.items() if cu[k] != v}
        if not doi:
            return
        self.c.execute(f"UPDATE {bang} SET {', '.join(f'{k}=?' for k in doi)} WHERE id=?",
                       (*doi.values(), id_))
        self.ghi_nhat_ky("sua", bang, id_, self._mo_ta(doi))

    def _xoa_mem(self, bang: str, id_: int) -> None:
        self.c.execute(f"UPDATE {bang} SET da_xoa=1 WHERE id=?", (id_,))
        self.ghi_nhat_ky("xoa", bang, id_)

    # ------------------------------------------------------------ đối tượng
    def tim_doi_tuong_trung(self, loai: str, ten: str, don_vi_cong_tac: str | None,
                            bo_qua_id: int | None = None) -> sqlite3.Row | None:
        for r in self.c.execute("SELECT * FROM doi_tuong WHERE da_xoa=0 AND loai=?", (loai,)):
            if r["id"] != bo_qua_id and chuan_hoa(r["ten"]) == chuan_hoa(ten) and \
                    chuan_hoa(r["don_vi_cong_tac"]) == chuan_hoa(don_vi_cong_tac):
                return r
        return None

    @can_quyen("sua_du_lieu")
    def them_doi_tuong(self, d: dict) -> int:
        if not (d.get("ten") or "").strip():
            raise LoiNghiepVu("Chưa nhập tên.")
        if d.get("loai") not in ("ca_nhan", "tap_the"):
            raise LoiNghiepVu("Loại phải là Cá nhân hoặc Tập thể.")
        if self.tim_doi_tuong_trung(d["loai"], d["ten"], d.get("don_vi_cong_tac")):
            raise LoiNghiepVu(f"Đã có \"{d['ten']}\" cùng đơn vị công tác trong danh sách.")
        d = chuan_hoa_doi_tuong({**d, "ten": " ".join(d["ten"].split())})
        if not self.co_quyen("sua_stk"):
            d = {k: v for k, v in d.items() if k not in COT_STK}
        id_ = self._them("doi_tuong", COT_DOI_TUONG, d)
        self.c.commit()
        return id_

    def sua_doi_tuong(self, id_: int, d: dict) -> None:
        if not self.co_quyen("sua_du_lieu"):
            # Kế toán: chỉ sửa số tài khoản, ngân hàng
            self.kiem_quyen("sua_stk")
            d = {k: v for k, v in d.items() if k in COT_STK}
            if d:
                self._sua("doi_tuong", COT_STK, id_, d)
                self.c.commit()
            return
        if not self.co_quyen("sua_stk"):
            d = {k: v for k, v in d.items() if k not in COT_STK}
        if "ten" in d and not (d["ten"] or "").strip():
            raise LoiNghiepVu("Chưa nhập tên.")
        cu = self.c.execute("SELECT * FROM doi_tuong WHERE id=?", (id_,)).fetchone()
        loai, ten = d.get("loai", cu["loai"]), d.get("ten", cu["ten"])
        if self.tim_doi_tuong_trung(loai, ten, d.get("don_vi_cong_tac", cu["don_vi_cong_tac"]), id_):
            raise LoiNghiepVu(f"Đã có \"{ten}\" cùng đơn vị công tác trong danh sách.")
        d = chuan_hoa_doi_tuong({**dict(cu), **d})
        d = {k: v for k, v in d.items() if k in COT_DOI_TUONG}
        self._sua("doi_tuong", COT_DOI_TUONG, id_, d)
        self.c.commit()

    @can_quyen("sua_du_lieu")
    def xoa_doi_tuong(self, id_: int) -> None:
        n = self.c.execute("SELECT COUNT(*) FROM ho_so_doi_tuong hd JOIN ho_so hs ON hs.id=hd.ho_so_id "
                           "WHERE hd.doi_tuong_id=? AND hs.da_xoa=0", (id_,)).fetchone()[0]
        if n:
            raise LoiNghiepVu(f"Đối tượng đang có trong {n} hồ sơ, không xóa được.")
        self._xoa_mem("doi_tuong", id_)
        self.c.commit()

    # ------------------------------------------------------------ phong trào
    @can_quyen("sua_du_lieu")
    def them_phong_trao(self, d: dict) -> int:
        if not (d.get("ten") or "").strip() or not d.get("nam"):
            raise LoiNghiepVu("Cần nhập tên phong trào và năm.")
        id_ = self._them("phong_trao", COT_PHONG_TRAO, d)
        self.c.commit()
        return id_

    @can_quyen("sua_du_lieu")
    def sua_phong_trao(self, id_: int, d: dict) -> None:
        self._sua("phong_trao", COT_PHONG_TRAO, id_, d)
        self.c.commit()

    @can_quyen("sua_du_lieu")
    def xoa_phong_trao(self, id_: int) -> None:
        n = self.c.execute("SELECT COUNT(*) FROM ho_so WHERE phong_trao_id=? AND da_xoa=0", (id_,)).fetchone()[0]
        if n:
            raise LoiNghiepVu(f"Phong trào đang có {n} hồ sơ, không xóa được.")
        self._xoa_mem("phong_trao", id_)
        self.c.commit()

    # ------------------------------------------------------------ hồ sơ
    @can_quyen("sua_du_lieu")
    def tao_ho_so(self, d: dict) -> int:
        for k, ten in (("don_vi_id", "đơn vị đề nghị"), ("hinh_thuc_id", "hình thức khen thưởng"),
                       ("trich_yeu", "trích yếu")):
            if not d.get(k):
                raise LoiNghiepVu(f"Chưa nhập {ten}.")
        id_ = self._them("ho_so", COT_HO_SO, d)
        self.c.commit()
        return id_

    def _ho_so(self, id_: int) -> sqlite3.Row:
        r = self.c.execute("SELECT * FROM ho_so WHERE id=? AND da_xoa=0", (id_,)).fetchone()
        if r is None:
            raise LoiNghiepVu("Không tìm thấy hồ sơ.")
        return r

    def _chi_khi_chua_co_qd(self, hs: sqlite3.Row) -> None:
        if hs["trang_thai"] in ("da_co_qd", "khong_duyet"):
            raise LoiNghiepVu("Hồ sơ đã kết thúc (đã có quyết định hoặc không được duyệt), không sửa được.")

    @can_quyen("sua_du_lieu")
    def sua_ho_so(self, id_: int, d: dict) -> None:
        self._chi_khi_chua_co_qd(self._ho_so(id_))
        self._sua("ho_so", COT_HO_SO, id_, d)
        if "hinh_thuc_id" in d:
            self.tinh_lai_tien(id_)
        self.c.commit()

    @can_quyen("sua_du_lieu")
    def xoa_ho_so(self, id_: int) -> None:
        if self._ho_so(id_)["trang_thai"] == "da_co_qd":
            raise LoiNghiepVu("Hồ sơ đã có quyết định, không xóa được.")
        self._xoa_mem("ho_so", id_)
        self.c.commit()

    def _ngay_tinh_tien(self, hs: sqlite3.Row) -> str:
        return hs["qd_ngay"] or hs["ttr_vhxh_ngay"] or hs["ttr_dv_ngay"] or date.today().isoformat()

    def _tien_cho(self, hs: sqlite3.Row, loai: str) -> int | None:
        ht = self.c.execute("SELECT * FROM hinh_thuc WHERE id=?", (hs["hinh_thuc_id"],)).fetchone()
        he_so = ht["he_so_ca_nhan"] if loai == "ca_nhan" else ht["he_so_tap_the"]
        return tinh_tien(he_so, luong_co_so_tai(self.c, self._ngay_tinh_tien(hs)))

    def canh_bao_khen_trung(self, ho_so_id: int, doi_tuong_id: int) -> str | None:
        """Cảnh báo nếu đối tượng đã được khen cùng hình thức trong cùng năm (không chặn)."""
        hs = self._ho_so(ho_so_id)
        nam = (self._ngay_tinh_tien(hs))[:4]
        r = self.c.execute(
            "SELECT v.qd_so, v.qd_ngay FROM v_lich_su_khen_thuong v JOIN hinh_thuc ht ON ht.ten=v.hinh_thuc "
            "WHERE v.doi_tuong_id=? AND ht.id=? AND v.nam=? LIMIT 1",
            (doi_tuong_id, hs["hinh_thuc_id"], int(nam))).fetchone()
        if r:
            return f"Đã được khen cùng hình thức năm {nam} (QĐ {r['qd_so']})."
        return None

    @can_quyen("sua_du_lieu")
    def them_vao_ho_so(self, ho_so_id: int, doi_tuong_id: int, thanh_tich: str | None = None) -> str | None:
        """Thêm đối tượng vào danh sách hồ sơ. Trả về cảnh báo (nếu có)."""
        hs = self._ho_so(ho_so_id)
        self._chi_khi_chua_co_qd(hs)
        dt = self.c.execute("SELECT * FROM doi_tuong WHERE id=? AND da_xoa=0", (doi_tuong_id,)).fetchone()
        if dt is None:
            raise LoiNghiepVu("Không tìm thấy đối tượng.")
        if self.c.execute("SELECT 1 FROM ho_so_doi_tuong WHERE ho_so_id=? AND doi_tuong_id=?",
                          (ho_so_id, doi_tuong_id)).fetchone():
            raise LoiNghiepVu(f"\"{dt['ten']}\" đã có trong hồ sơ này.")
        thu_tu = self.c.execute("SELECT COALESCE(MAX(thu_tu),0)+1 FROM ho_so_doi_tuong WHERE ho_so_id=?",
                                (ho_so_id,)).fetchone()[0]
        cur = self.c.execute("INSERT INTO ho_so_doi_tuong(ho_so_id, doi_tuong_id, thu_tu, tom_tat_thanh_tich, "
                             "so_tien) VALUES (?,?,?,?,?)",
                             (ho_so_id, doi_tuong_id, thu_tu, thanh_tich, self._tien_cho(hs, dt["loai"])))
        self.ghi_nhat_ky("them", "ho_so_doi_tuong", cur.lastrowid, f"ho_so={ho_so_id}; doi_tuong={doi_tuong_id}")
        self.c.commit()
        return self.canh_bao_khen_trung(ho_so_id, doi_tuong_id)

    @can_quyen("sua_du_lieu")
    def sua_dong_ho_so(self, dong_id: int, thanh_tich: str | None, so_tien: int | None) -> None:
        r = self.c.execute("SELECT * FROM ho_so_doi_tuong WHERE id=?", (dong_id,)).fetchone()
        self._chi_khi_chua_co_qd(self._ho_so(r["ho_so_id"]))
        self.c.execute("UPDATE ho_so_doi_tuong SET tom_tat_thanh_tich=?, so_tien=? WHERE id=?",
                       (thanh_tich, so_tien, dong_id))
        self.ghi_nhat_ky("sua", "ho_so_doi_tuong", dong_id, f"so_tien={so_tien}")
        self.c.commit()

    @can_quyen("sua_du_lieu")
    def bo_khoi_ho_so(self, dong_id: int) -> None:
        r = self.c.execute("SELECT * FROM ho_so_doi_tuong WHERE id=?", (dong_id,)).fetchone()
        self._chi_khi_chua_co_qd(self._ho_so(r["ho_so_id"]))
        self.c.execute("DELETE FROM ho_so_doi_tuong WHERE id=?", (dong_id,))
        self.ghi_nhat_ky("xoa", "ho_so_doi_tuong", dong_id,
                         f"ho_so={r['ho_so_id']}; doi_tuong={r['doi_tuong_id']}")
        self.c.commit()

    @can_quyen("sua_du_lieu")
    def tinh_lai_tien(self, ho_so_id: int) -> None:
        hs = self._ho_so(ho_so_id)
        for r in self.c.execute("SELECT hd.id, dt.loai FROM ho_so_doi_tuong hd JOIN doi_tuong dt "
                                "ON dt.id=hd.doi_tuong_id WHERE hd.ho_so_id=?", (ho_so_id,)).fetchall():
            self.c.execute("UPDATE ho_so_doi_tuong SET so_tien=? WHERE id=?", (self._tien_cho(hs, r["loai"]), r["id"]))

    # ------------------------------------------------------------ luồng hồ sơ
    def _chuyen(self, id_: int, moi: str, cap_nhat: dict, ghi_chu: str = "") -> None:
        hs = self._ho_so(id_)
        if moi not in CHUYEN_TRANG_THAI[hs["trang_thai"]]:
            raise LoiNghiepVu("Không chuyển được hồ sơ sang trạng thái này từ trạng thái hiện tại.")
        cap_nhat = {**cap_nhat, "trang_thai": moi}
        self.c.execute(f"UPDATE ho_so SET {', '.join(f'{k}=?' for k in cap_nhat)} WHERE id=?",
                       (*cap_nhat.values(), id_))
        self.ghi_nhat_ky("chuyen_trang_thai", "ho_so", id_, f"{hs['trang_thai']} -> {moi}. {ghi_chu}".strip())

    @can_quyen("luong_ho_so")
    def tra_lai(self, id_: int, ly_do: str, han_bo_sung: str | None = None) -> None:
        if not (ly_do or "").strip():
            raise LoiNghiepVu("Cần ghi lý do trả lại.")
        self._chuyen(id_, "tra_lai", {"ly_do_tra_lai": ly_do.strip(), "han_xu_ly": han_bo_sung}, ly_do)
        self.c.commit()

    @can_quyen("luong_ho_so")
    def nhan_lai_bo_sung(self, id_: int) -> None:
        self._chuyen(id_, "tiep_nhan", {"ly_do_tra_lai": None})
        self.c.commit()

    @can_quyen("luong_ho_so")
    def trinh(self, id_: int, so_ttr: str, ngay_ttr: str) -> None:
        if not so_ttr or not ngay_ttr:
            raise LoiNghiepVu("Cần nhập số và ngày Tờ trình của Phòng VH-XH.")
        if not self.c.execute("SELECT 1 FROM ho_so_doi_tuong WHERE ho_so_id=?", (id_,)).fetchone():
            raise LoiNghiepVu("Hồ sơ chưa có tập thể, cá nhân nào.")
        self._chuyen(id_, "da_trinh", {"ttr_vhxh_so": so_ttr, "ttr_vhxh_ngay": ngay_ttr, "ly_do_tra_lai": None})
        self.tinh_lai_tien(id_)
        self.c.commit()

    @can_quyen("luong_ho_so")
    def nhap_quyet_dinh(self, id_: int, so_qd: str, ngay_qd: str, nguoi_ky: str | None,
                        khong_duoc_ids: set[int] | None = None) -> None:
        """Ghi QĐ. khong_duoc_ids: các dòng (ho_so_doi_tuong.id) không có tên trong QĐ."""
        if not so_qd or not ngay_qd:
            raise LoiNghiepVu("Cần nhập số và ngày quyết định.")
        self._chuyen(id_, "da_co_qd", {"qd_so": so_qd, "qd_ngay": ngay_qd, "qd_nguoi_ky": nguoi_ky,
                                       "han_xu_ly": None})
        khong = khong_duoc_ids or set()
        for r in self.c.execute("SELECT id FROM ho_so_doi_tuong WHERE ho_so_id=?", (id_,)).fetchall():
            self.c.execute("UPDATE ho_so_doi_tuong SET ket_qua=? WHERE id=?",
                           ("khong_duoc" if r["id"] in khong else "duoc_khen", r["id"]))
        self.tinh_lai_tien(id_)  # tính lại theo lương cơ sở tại ngày QĐ
        self.c.execute("UPDATE ho_so_doi_tuong SET so_tien=NULL WHERE ho_so_id=? AND ket_qua='khong_duoc'", (id_,))
        self.c.commit()

    @can_quyen("luong_ho_so")
    def khong_duyet(self, id_: int, ly_do: str) -> None:
        if not (ly_do or "").strip():
            raise LoiNghiepVu("Cần ghi lý do.")
        self._chuyen(id_, "khong_duyet", {"ghi_chu": ly_do.strip(), "han_xu_ly": None}, ly_do)
        self.c.execute("UPDATE ho_so_doi_tuong SET ket_qua='khong_duoc', so_tien=NULL WHERE ho_so_id=?", (id_,))
        self.c.commit()

    # ------------------------------------------------------------ danh mục
    DANH_MUC = {
        "don_vi": ("ten", "loai", "dang_dung"),
        "hinh_thuc": ("ten", "loai", "he_so_ca_nhan", "he_so_tap_the", "can_cu", "dang_dung"),
        "luong_co_so": ("ap_dung_tu", "muc", "can_cu"),
        "can_cu": ("noi_dung", "dung_cho", "thu_tu", "dang_dung"),
        "han_cong_viec": ("tieu_de", "han", "phong_trao_id", "ho_so_id", "da_xong", "ghi_chu"),
    }

    def luu_danh_muc(self, bang: str, d: dict, id_: int | None = None) -> int:
        self.kiem_quyen("sua_du_lieu" if bang == "han_cong_viec" else "danh_muc")
        cot = self.DANH_MUC[bang]
        try:
            if id_ is None:
                id_ = self._them(bang, cot, d)
            else:
                self._sua(bang, cot, id_, d)
        except LOI_TRUNG as e:
            self.c.rollback()
            raise LoiNghiepVu("Dữ liệu bị trùng hoặc thiếu trường bắt buộc.") from e
        self.c.commit()
        return id_
