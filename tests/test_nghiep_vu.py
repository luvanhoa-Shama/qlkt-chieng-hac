import pytest

from qlkt.services.nghiep_vu import LoiNghiepVu


def _ho_so(nv, **kw):
    return nv.tao_ho_so({"don_vi_id": 1, "hinh_thuc_id": 1, "trich_yeu": "Khen QP 2026",
                         "phong_trao_id": 1, "ttr_dv_ngay": "2026-08-01", **kw})


def test_them_doi_tuong_chan_trung(nv):
    nv.them_doi_tuong({"loai": "ca_nhan", "ten": "Nguyễn Văn A", "don_vi_cong_tac": "Công an xã"})
    with pytest.raises(LoiNghiepVu):
        nv.them_doi_tuong({"loai": "ca_nhan", "ten": "  nguyễn  văn a ", "don_vi_cong_tac": "công an xã"})
    # Trùng tên nhưng khác đơn vị: cho phép
    nv.them_doi_tuong({"loai": "ca_nhan", "ten": "Nguyễn Văn A", "don_vi_cong_tac": "Trường TH"})


def test_bat_buoc_ten(nv):
    with pytest.raises(LoiNghiepVu):
        nv.them_doi_tuong({"loai": "ca_nhan", "ten": " "})


def test_luong_ho_so_day_du(nv):
    a = nv.them_doi_tuong({"loai": "ca_nhan", "ten": "A"})
    b = nv.them_doi_tuong({"loai": "tap_the", "ten": "Tập thể B"})
    hs = _ho_so(nv)
    nv.them_vao_ho_so(hs, a, "tốt")
    nv.them_vao_ho_so(hs, b)
    # Lương cơ sở tại ngày tờ trình đơn vị (8/2026)
    tien = [r[0] for r in nv.c.execute("SELECT so_tien FROM ho_so_doi_tuong ORDER BY id")]
    assert tien == [702000, 1404000]
    with pytest.raises(LoiNghiepVu):
        nv.nhap_quyet_dinh(hs, "1/QĐ", "2026-11-26", "X")  # chưa trình
    nv.tra_lai(hs, "Thiếu biên bản")
    nv.nhan_lai_bo_sung(hs)
    nv.trinh(hs, "357/TTr-VHXH", "2026-11-26")
    dong_b = nv.c.execute("SELECT id FROM ho_so_doi_tuong WHERE doi_tuong_id=?", (b,)).fetchone()[0]
    nv.nhap_quyet_dinh(hs, "10/QĐ-UBND", "2026-11-27", "Chủ tịch", khong_duoc_ids={dong_b})
    rows = nv.c.execute("SELECT ket_qua, so_tien FROM ho_so_doi_tuong ORDER BY id").fetchall()
    assert [tuple(r) for r in rows] == [("duoc_khen", 759000), ("khong_duoc", None)]
    ls = nv.c.execute("SELECT ten, nam FROM v_lich_su_khen_thuong").fetchall()
    assert [tuple(r) for r in ls] == [("A", 2026)]
    # Đã có QĐ: không sửa, không xóa được
    with pytest.raises(LoiNghiepVu):
        nv.sua_ho_so(hs, {"trich_yeu": "khác"})
    with pytest.raises(LoiNghiepVu):
        nv.xoa_ho_so(hs)
    with pytest.raises(LoiNghiepVu):
        nv.xoa_doi_tuong(a)


def test_canh_bao_khen_trung_nam(nv):
    a = nv.them_doi_tuong({"loai": "ca_nhan", "ten": "A"})
    hs1 = _ho_so(nv)
    nv.them_vao_ho_so(hs1, a)
    nv.trinh(hs1, "1/TTr", "2026-08-02")
    nv.nhap_quyet_dinh(hs1, "1/QĐ", "2026-08-05", None)
    hs2 = _ho_so(nv, ttr_dv_ngay="2026-11-01")
    cb = nv.them_vao_ho_so(hs2, a)
    assert cb and "1/QĐ" in cb
    with pytest.raises(LoiNghiepVu):
        nv.them_vao_ho_so(hs2, a)


def test_trinh_can_danh_sach_va_so(nv):
    hs = _ho_so(nv)
    with pytest.raises(LoiNghiepVu):
        nv.trinh(hs, "1/TTr", "2026-11-01")
    with pytest.raises(LoiNghiepVu):
        nv.tra_lai(hs, "")


def test_nhat_ky_an_so_tai_khoan(nv):
    nv.them_doi_tuong({"loai": "ca_nhan", "ten": "A", "so_tai_khoan": "123456789"})
    nd = " ".join(r[0] or "" for r in nv.c.execute("SELECT noi_dung FROM nhat_ky"))
    assert "123456789" not in nd and "so_tai_khoan=***" in nd
