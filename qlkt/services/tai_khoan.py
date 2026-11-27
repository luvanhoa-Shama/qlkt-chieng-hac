"""Tài khoản người dùng: đăng nhập, khóa khi nhập sai, đổi/đặt lại mật khẩu."""
from __future__ import annotations

from dataclasses import dataclass

from qlkt.bao_mat import mat_khau
from qlkt.bao_mat.phan_quyen import VAI_TRO, co_quyen
from qlkt.services.nghiep_vu import LoiNghiepVu

SAI_TOI_DA = 5


@dataclass
class NguoiDung:
    id: int
    ten_dang_nhap: str
    ho_ten: str
    vai_tro: str
    phai_doi_mat_khau: bool

    @property
    def ten_vai_tro(self) -> str:
        return VAI_TRO.get(self.vai_tro, self.vai_tro)


def _ghi(c, nguoi_dung_id, hanh_dong: str, ban_ghi_id=None, noi_dung=None) -> None:
    c.execute("INSERT INTO nhat_ky(nguoi_dung_id, hanh_dong, bang, ban_ghi_id, noi_dung) VALUES (?,?,?,?,?)",
              (nguoi_dung_id, hanh_dong, "nguoi_dung", ban_ghi_id, noi_dung))


def _nd(r) -> NguoiDung:
    return NguoiDung(r["id"], r["ten_dang_nhap"], r["ho_ten"], r["vai_tro"], bool(r["phai_doi_mat_khau"]))


def chua_co_tai_khoan(c) -> bool:
    """Chưa có tài khoản Quản trị nào đang dùng (CSDL mới, hoặc CSDL thử chuyển sang)."""
    return c.execute("SELECT count(*) FROM nguoi_dung WHERE vai_tro='quan_tri' AND dang_dung=1").fetchone()[0] == 0


def _kiem_mat_khau(mk: str) -> None:
    loi = mat_khau.loi_mat_khau(mk)
    if loi:
        raise LoiNghiepVu(loi)


def _chuan_ten(ten: str) -> str:
    ten = (ten or "").strip().lower()
    if not ten or " " in ten:
        raise LoiNghiepVu("Tên đăng nhập không được để trống hoặc có dấu cách.")
    return ten


def tao_quan_tri_dau_tien(c, ten_dang_nhap: str, ho_ten: str, mk: str) -> NguoiDung:
    if not chua_co_tai_khoan(c):
        raise LoiNghiepVu("Đã có tài khoản Quản trị.")
    if not (ho_ten or "").strip():
        raise LoiNghiepVu("Chưa nhập họ tên.")
    _kiem_mat_khau(mk)
    if c.execute("SELECT 1 FROM nguoi_dung WHERE ten_dang_nhap=?", (_chuan_ten(ten_dang_nhap),)).fetchone():
        raise LoiNghiepVu("Tên đăng nhập đã có.")
    cur = c.execute("INSERT INTO nguoi_dung(ten_dang_nhap, ho_ten, mat_khau_hash, vai_tro) VALUES (?,?,?,?)",
                    (_chuan_ten(ten_dang_nhap), ho_ten.strip(), mat_khau.bam(mk), "quan_tri"))
    _ghi(c, cur.lastrowid, "tao_tai_khoan", cur.lastrowid, "Quản trị đầu tiên")
    c.commit()
    return _nd(c.execute("SELECT * FROM nguoi_dung WHERE id=?", (cur.lastrowid,)).fetchone())


def dang_nhap(c, ten_dang_nhap: str, mk: str) -> NguoiDung:
    """Sai 5 lần liên tiếp → khóa tài khoản, Quản trị mở lại. Thông báo không tiết lộ tên có tồn tại hay không."""
    ten = (ten_dang_nhap or "").strip().lower()
    r = c.execute("SELECT * FROM nguoi_dung WHERE ten_dang_nhap=?", (ten,)).fetchone()
    sai = LoiNghiepVu("Tên đăng nhập hoặc mật khẩu không đúng.")
    if r is None:
        mat_khau.bam(mk)   # tốn thời gian như trường hợp có tài khoản
        _ghi(c, None, "dang_nhap_sai", None, "Tên không tồn tại")
        c.commit()
        raise sai
    if not r["dang_dung"]:
        raise LoiNghiepVu("Tài khoản đã ngừng sử dụng. Liên hệ Quản trị.")
    if r["bi_khoa"]:
        raise LoiNghiepVu("Tài khoản đang bị khóa do nhập sai nhiều lần. Liên hệ Quản trị để mở khóa.")
    if not mat_khau.kiem_tra(mk, r["mat_khau_hash"]):
        so = r["so_lan_sai"] + 1
        khoa = so >= SAI_TOI_DA
        c.execute("UPDATE nguoi_dung SET so_lan_sai=?, bi_khoa=? WHERE id=?", (so, int(khoa), r["id"]))
        _ghi(c, r["id"], "khoa_tai_khoan" if khoa else "dang_nhap_sai", r["id"], f"Sai lần {so}")
        c.commit()
        if khoa:
            raise LoiNghiepVu(f"Nhập sai {SAI_TOI_DA} lần. Tài khoản đã bị khóa, liên hệ Quản trị để mở.")
        raise LoiNghiepVu(f"Tên đăng nhập hoặc mật khẩu không đúng (còn {SAI_TOI_DA - so} lần thử).")
    c.execute("UPDATE nguoi_dung SET so_lan_sai=0, dang_nhap_cuoi=datetime('now','localtime') WHERE id=?",
              (r["id"],))
    _ghi(c, r["id"], "dang_nhap", r["id"])
    c.commit()
    return _nd(r)


def doi_mat_khau(c, nguoi_dung_id: int, mk_cu: str, mk_moi: str) -> None:
    r = c.execute("SELECT * FROM nguoi_dung WHERE id=?", (nguoi_dung_id,)).fetchone()
    if r is None or not mat_khau.kiem_tra(mk_cu, r["mat_khau_hash"]):
        raise LoiNghiepVu("Mật khẩu hiện tại không đúng.")
    if mk_moi == mk_cu:
        raise LoiNghiepVu("Mật khẩu mới phải khác mật khẩu cũ.")
    _kiem_mat_khau(mk_moi)
    c.execute("UPDATE nguoi_dung SET mat_khau_hash=?, phai_doi_mat_khau=0 WHERE id=?",
              (mat_khau.bam(mk_moi), nguoi_dung_id))
    _ghi(c, nguoi_dung_id, "doi_mat_khau", nguoi_dung_id)
    c.commit()


# ------------------------------------------------------------ Quản trị
def _kiem_quan_tri(c, nguoi_thuc_hien: int | None) -> None:
    if nguoi_thuc_hien is None:
        return
    r = c.execute("SELECT vai_tro FROM nguoi_dung WHERE id=?", (nguoi_thuc_hien,)).fetchone()
    if r is None or not co_quyen(r["vai_tro"], "nguoi_dung"):
        raise LoiNghiepVu("Chỉ Quản trị được quản lý tài khoản.")


def _con_quan_tri_khac(c, tru_id: int) -> bool:
    return c.execute("SELECT count(*) FROM nguoi_dung WHERE vai_tro='quan_tri' AND dang_dung=1 AND bi_khoa=0 "
                     "AND id<>?", (tru_id,)).fetchone()[0] > 0


def them_nguoi_dung(c, nguoi_thuc_hien: int | None, ten_dang_nhap: str, ho_ten: str, vai_tro: str,
                    mk_tam: str) -> int:
    """Mật khẩu tạm: người dùng phải đổi ở lần đăng nhập đầu."""
    _kiem_quan_tri(c, nguoi_thuc_hien)
    if vai_tro not in VAI_TRO:
        raise LoiNghiepVu("Vai trò không hợp lệ.")
    if not (ho_ten or "").strip():
        raise LoiNghiepVu("Chưa nhập họ tên.")
    ten = _chuan_ten(ten_dang_nhap)
    if c.execute("SELECT 1 FROM nguoi_dung WHERE ten_dang_nhap=?", (ten,)).fetchone():
        raise LoiNghiepVu("Tên đăng nhập đã có.")
    _kiem_mat_khau(mk_tam)
    cur = c.execute("INSERT INTO nguoi_dung(ten_dang_nhap, ho_ten, mat_khau_hash, vai_tro, phai_doi_mat_khau) "
                    "VALUES (?,?,?,?,1)", (ten, ho_ten.strip(), mat_khau.bam(mk_tam), vai_tro))
    _ghi(c, nguoi_thuc_hien, "tao_tai_khoan", cur.lastrowid, f"{ten}; vai_tro={vai_tro}")
    c.commit()
    return cur.lastrowid


def sua_nguoi_dung(c, nguoi_thuc_hien: int | None, id_: int, ho_ten: str, vai_tro: str, dang_dung: bool) -> None:
    _kiem_quan_tri(c, nguoi_thuc_hien)
    if vai_tro not in VAI_TRO:
        raise LoiNghiepVu("Vai trò không hợp lệ.")
    r = c.execute("SELECT * FROM nguoi_dung WHERE id=?", (id_,)).fetchone()
    if r is None:
        raise LoiNghiepVu("Không tìm thấy tài khoản.")
    if r["vai_tro"] == "quan_tri" and (vai_tro != "quan_tri" or not dang_dung) and not _con_quan_tri_khac(c, id_):
        raise LoiNghiepVu("Phải còn ít nhất một tài khoản Quản trị đang dùng.")
    c.execute("UPDATE nguoi_dung SET ho_ten=?, vai_tro=?, dang_dung=? WHERE id=?",
              (ho_ten.strip(), vai_tro, int(dang_dung), id_))
    _ghi(c, nguoi_thuc_hien, "sua_tai_khoan", id_, f"vai_tro={vai_tro}; dang_dung={int(dang_dung)}")
    c.commit()


def dat_lai_mat_khau(c, nguoi_thuc_hien: int | None, id_: int, mk_tam: str) -> None:
    """Đặt mật khẩu tạm và mở khóa; người dùng phải đổi khi đăng nhập."""
    _kiem_quan_tri(c, nguoi_thuc_hien)
    _kiem_mat_khau(mk_tam)
    c.execute("UPDATE nguoi_dung SET mat_khau_hash=?, phai_doi_mat_khau=1, so_lan_sai=0, bi_khoa=0 WHERE id=?",
              (mat_khau.bam(mk_tam), id_))
    _ghi(c, nguoi_thuc_hien, "dat_lai_mat_khau", id_)
    c.commit()


def mo_khoa(c, nguoi_thuc_hien: int | None, id_: int) -> None:
    _kiem_quan_tri(c, nguoi_thuc_hien)
    c.execute("UPDATE nguoi_dung SET so_lan_sai=0, bi_khoa=0 WHERE id=?", (id_,))
    _ghi(c, nguoi_thuc_hien, "mo_khoa_tai_khoan", id_)
    c.commit()
