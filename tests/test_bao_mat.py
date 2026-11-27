import sys

import pytest

from qlkt.bao_mat import khoa as kh
from qlkt.bao_mat import mat_khau
from qlkt.bao_mat.phan_quyen import che_stk
from qlkt.db.database import SaiKhoa, ket_noi, la_tep_chua_ma_hoa, ma_hoa_tep, mo_tho
from qlkt.services import sao_luu, tai_khoan
from qlkt.services.nghiep_vu import LoiNghiepVu, NghiepVu


def test_mat_khau():
    h = mat_khau.bam("abc12345")
    assert h.startswith("scrypt$") and "abc12345" not in h
    assert mat_khau.kiem_tra("abc12345", h)
    assert not mat_khau.kiem_tra("abc12346", h)
    assert not mat_khau.kiem_tra("x", "rác")
    assert mat_khau.loi_mat_khau("ngan1")
    assert mat_khau.loi_mat_khau("chuacoso")
    assert mat_khau.loi_mat_khau("12345678")
    assert mat_khau.loi_mat_khau("Hặcchiềng9") is None


def test_khoa_hai_lop(tmp_path):
    k = kh.tao_khoa(tmp_path, "khoi phuc 2026 xa")
    assert len(k) == 32 and kh.mo_khoa(tmp_path) == k
    noi_dung = (tmp_path / "khoa.json").read_text()
    assert k.hex() not in noi_dung
    with pytest.raises(kh.LoiKhoa):
        kh.tao_khoa(tmp_path, "khac")            # không tạo đè
    with pytest.raises(kh.LoiKhoa):
        kh.mo_bang_mat_khau_khoi_phuc(tmp_path, "sai mat khau 1")
    assert kh.mo_bang_mat_khau_khoi_phuc(tmp_path, "khoi phuc 2026 xa") == k
    kh.doi_mat_khau_khoi_phuc(tmp_path, k, "mat khau moi 2027")
    assert kh.mo_bang_mat_khau_khoi_phuc(tmp_path, "mat khau moi 2027") == k


@pytest.mark.skipif(sys.platform == "win32", reason="Trên Windows lớp máy là DPAPI")
def test_doi_may_can_mat_khau_khoi_phuc(tmp_path, monkeypatch):
    k = kh.tao_khoa(tmp_path, "khoi phuc 2026 xa")
    monkeypatch.setenv("QLKT_KHOA_MAY", str(tmp_path / "may-khac.key"))   # như chép sang máy khác
    with pytest.raises(kh.LoiKhoa):
        kh.mo_khoa(tmp_path)
    assert kh.mo_bang_mat_khau_khoi_phuc(tmp_path, "khoi phuc 2026 xa") == k
    assert kh.mo_khoa(tmp_path) == k          # đã bọc lại cho "máy" mới


def test_csdl_ma_hoa(tmp_path):
    k = kh.tao_khoa(tmp_path, "khoi phuc 2026 xa")
    c = ket_noi(tmp_path / "qlkt.db", k)
    c.execute("INSERT INTO doi_tuong(loai, ten, so_tai_khoan) VALUES ('ca_nhan', 'Nguyễn Văn Giả', '9704001234')")
    c.commit(); c.close()
    du_lieu = (tmp_path / "qlkt.db").read_bytes()
    assert not la_tep_chua_ma_hoa(tmp_path / "qlkt.db")
    assert b"9704001234" not in du_lieu and "Nguyễn".encode() not in du_lieu
    with pytest.raises(SaiKhoa):
        mo_tho(tmp_path / "qlkt.db", b"\x01" * 32)
    assert ket_noi(tmp_path / "qlkt.db", k).execute("SELECT ten FROM doi_tuong").fetchone()[0] == "Nguyễn Văn Giả"


def test_chuyen_csdl_cu_sang_ma_hoa(tmp_path):
    c = ket_noi(tmp_path / "cu.db")
    c.execute("INSERT INTO don_vi(ten) VALUES ('Phòng Văn hóa - Xã hội')"); c.commit(); c.close()
    assert la_tep_chua_ma_hoa(tmp_path / "cu.db")
    k = b"\x02" * 32
    ma_hoa_tep(tmp_path / "cu.db", tmp_path / "moi.db", k)
    assert not la_tep_chua_ma_hoa(tmp_path / "moi.db")
    assert ket_noi(tmp_path / "moi.db", k).execute("SELECT ten FROM don_vi").fetchone()[0] == "Phòng Văn hóa - Xã hội"


@pytest.fixture
def c(tmp_path):
    return ket_noi(tmp_path / "tk.db")


def test_dang_nhap_va_khoa(c):
    qt = tai_khoan.tao_quan_tri_dau_tien(c, "QuanTri", "Quản trị", "quantri123")
    assert qt.ten_dang_nhap == "quantri" and qt.vai_tro == "quan_tri"
    with pytest.raises(LoiNghiepVu):
        tai_khoan.tao_quan_tri_dau_tien(c, "x", "x", "abc12345")
    assert tai_khoan.dang_nhap(c, "QUANTRI", "quantri123").id == qt.id
    tt = tai_khoan.them_nguoi_dung(c, qt.id, "thuongtruc", "Cán bộ TT", "thuong_truc", "tam12345")
    for i in range(tai_khoan.SAI_TOI_DA - 1):
        with pytest.raises(LoiNghiepVu, match="còn"):
            tai_khoan.dang_nhap(c, "thuongtruc", "sai")
    with pytest.raises(LoiNghiepVu, match="khóa"):
        tai_khoan.dang_nhap(c, "thuongtruc", "sai")
    with pytest.raises(LoiNghiepVu, match="khóa"):
        tai_khoan.dang_nhap(c, "thuongtruc", "tam12345")     # đúng mật khẩu vẫn không vào khi đã khóa
    with pytest.raises(LoiNghiepVu):
        tai_khoan.mo_khoa(c, tt, tt)                          # không phải quản trị
    tai_khoan.mo_khoa(c, qt.id, tt)
    nd = tai_khoan.dang_nhap(c, "thuongtruc", "tam12345")
    assert nd.phai_doi_mat_khau
    tai_khoan.doi_mat_khau(c, tt, "tam12345", "moi12345")
    assert not tai_khoan.dang_nhap(c, "thuongtruc", "moi12345").phai_doi_mat_khau
    with pytest.raises(LoiNghiepVu, match="không đúng"):
        tai_khoan.dang_nhap(c, "khongco", "abc")
    hd = [r[0] for r in c.execute("SELECT hanh_dong FROM nhat_ky")]
    assert "khoa_tai_khoan" in hd and "dang_nhap" in hd and "mo_khoa_tai_khoan" in hd
    assert not any("tam12345" in (r[0] or "") for r in c.execute("SELECT noi_dung FROM nhat_ky"))


def test_con_it_nhat_mot_quan_tri(c):
    qt = tai_khoan.tao_quan_tri_dau_tien(c, "quantri", "Quản trị", "quantri123")
    with pytest.raises(LoiNghiepVu, match="ít nhất một"):
        tai_khoan.sua_nguoi_dung(c, qt.id, qt.id, "Quản trị", "thuong_truc", True)
    q2 = tai_khoan.them_nguoi_dung(c, qt.id, "quantri2", "QT 2", "quan_tri", "tam12345")
    tai_khoan.sua_nguoi_dung(c, qt.id, qt.id, "Quản trị", "thuong_truc", True)
    with pytest.raises(LoiNghiepVu):
        tai_khoan.sua_nguoi_dung(c, q2, q2, "QT 2", "quan_tri", False)


def test_phan_quyen_nghiep_vu(c):
    qt = tai_khoan.tao_quan_tri_dau_tien(c, "quantri", "Quản trị", "quantri123")
    ld = tai_khoan.them_nguoi_dung(c, qt.id, "lanhdao", "Lãnh đạo", "lanh_dao", "tam12345")
    kt = tai_khoan.them_nguoi_dung(c, qt.id, "ketoan", "Kế toán", "ke_toan", "tam12345")
    tt = tai_khoan.them_nguoi_dung(c, qt.id, "thuongtruc", "TT", "thuong_truc", "tam12345")
    dt = NghiepVu(c, tt).them_doi_tuong({"loai": "ca_nhan", "ten": "Lò Văn Giả", "so_tai_khoan": "111"})
    with pytest.raises(LoiNghiepVu, match="không có quyền"):
        NghiepVu(c, ld).them_doi_tuong({"loai": "ca_nhan", "ten": "X"})
    with pytest.raises(LoiNghiepVu, match="không có quyền"):
        NghiepVu(c, ld).sua_doi_tuong(dt, {"so_tai_khoan": "999"})
    with pytest.raises(LoiNghiepVu, match="không có quyền"):
        NghiepVu(c, kt).luu_danh_muc("don_vi", {"ten": "X"})
    # kế toán: sửa số tài khoản được, các trường khác bị bỏ qua
    NghiepVu(c, kt).sua_doi_tuong(dt, {"ten": "Đổi tên", "so_tai_khoan": "222", "ngan_hang": "NH Giả"})
    r = c.execute("SELECT ten, so_tai_khoan, ngan_hang FROM doi_tuong WHERE id=?", (dt,)).fetchone()
    assert tuple(r) == ("Lò Văn Giả", "222", "NH Giả")
    assert che_stk("9704001234") == "******1234" and che_stk(None) == ""


def test_sao_luu_khoi_phuc(tmp_path):
    k = kh.tao_khoa(tmp_path, "khoi phuc 2026 xa")
    tep = tmp_path / "qlkt.db"
    c = ket_noi(tep, k)
    c.execute("INSERT INTO don_vi(ten) VALUES ('A')"); c.commit()
    assert sao_luu.can_sao_luu_tu_dong(tmp_path / "sl")
    b = sao_luu.sao_luu(c, k, tmp_path / "sl", "tu-dong", tmp_path)
    assert not sao_luu.can_sao_luu_tu_dong(tmp_path / "sl")
    assert list((tmp_path / "sl").glob("khoa-*.json"))
    assert not la_tep_chua_ma_hoa(b)
    c.execute("INSERT INTO don_vi(ten) VALUES ('B')"); c.commit()
    c = sao_luu.khoi_phuc(c, k, tep, b, tmp_path / "sl", thu_muc_du_lieu=tmp_path)
    assert [r[0] for r in c.execute("SELECT ten FROM don_vi")] == ["A"]
    ten = [p.name for p in sao_luu.danh_sach(tmp_path / "sl")]
    assert any(t.startswith("qlkt-truoc-khoi-phuc-") for t in ten)
    assert "khoi_phuc" in [r[0] for r in c.execute("SELECT hanh_dong FROM nhat_ky")]
    with pytest.raises((ValueError, SaiKhoa)):     # tệp không phải CSDL
        sao_luu.kiem_tra_ban_sao(tmp_path / "khoa.json", k)


def test_khoi_phuc_ban_sao_may_khac(tmp_path):
    (tmp_path / "a").mkdir(); (tmp_path / "b").mkdir()
    ka = kh.tao_khoa(tmp_path / "a", "mat khau may A 1")
    ca = ket_noi(tmp_path / "a" / "qlkt.db", ka)
    ca.execute("INSERT INTO don_vi(ten) VALUES ('Từ máy A')"); ca.commit()
    b = sao_luu.sao_luu(ca, ka, tmp_path / "usb", "tay", tmp_path / "a")
    kb = kh.tao_khoa(tmp_path / "b", "mat khau may B 1")
    cb = ket_noi(tmp_path / "b" / "qlkt.db", kb)
    with pytest.raises(SaiKhoa):
        sao_luu.kiem_tra_ban_sao(b, kb)
    with pytest.raises(kh.LoiKhoa):
        sao_luu.tim_khoa_cho_ban_sao(b, "sai mat khau 1")
    k_bs = sao_luu.tim_khoa_cho_ban_sao(b, "mat khau may A 1")
    cb = sao_luu.khoi_phuc(cb, kb, tmp_path / "b" / "qlkt.db", b, tmp_path / "b-sl", k_bs)
    assert cb.execute("SELECT ten FROM don_vi").fetchone()[0] == "Từ máy A"
    cb.close()
    assert ket_noi(tmp_path / "b" / "qlkt.db", kb)   # đã chuyển sang khóa của máy B


def test_don_dep_giu_so_ban(tmp_path):
    c = ket_noi(tmp_path / "x.db")
    for _ in range(5):
        sao_luu.sao_luu(c, None, tmp_path / "sl", "tu-dong")
    sao_luu.don_dep(tmp_path / "sl", giu=2)
    assert len(sao_luu.danh_sach(tmp_path / "sl")) == 2
