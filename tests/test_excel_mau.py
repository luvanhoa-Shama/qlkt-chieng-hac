from openpyxl import load_workbook

from qlkt.services.excel_mau import DONG_TIEU_DE_DS, doc_mau, nhap_ho_so, xuat_mau


def _dien(path, dong, thong_tin=None):
    wb = load_workbook(path)
    tt = wb["Thông tin"]
    vals = {"don_vi": "Ban Chỉ huy Quân sự xã", "ttr_dv_so": "08/TTr-BCH", "ttr_dv_ngay": "25/11/2026",
            "bb_so": "07/BB", "bb_ngay": "24/11/2026", "bb_so_du": 3, "bb_tong_so": 3, "bb_ty_le": "100%"}
    vals.update(thong_tin or {})
    keys = ["don_vi", "ttr_dv_so", "ttr_dv_ngay", "bb_so", "bb_ngay", "bb_to_chuc_hop", "bb_so_du",
            "bb_tong_so", "bb_ty_le"]
    for i, k in enumerate(keys, start=4):
        tt.cell(i, 2, vals.get(k))
    ds = wb["Danh sách"]
    for i, r in enumerate(dong, start=DONG_TIEU_DE_DS + 1):
        for j, v in enumerate(r, start=1):
            ds.cell(i, j, v)
    wb.save(path)


def test_xuat_dien_nhap(nv, tmp_path):
    p = xuat_mau(tmp_path / "mau.xlsx", {"id": 1, "ten": "Quốc phòng", "nam": 2026, "han_nop_ho_so": "2026-11-30"})
    _dien(p, [
        [1, "Tập thể", None, "Dân quân bản Mẫu", None, "Bản Mẫu", "Xuất sắc", "Người X", None],
        [2, "Cá nhân", "Ông", "Nguyễn Văn A", "Bản đội trưởng", "Bản Mẫu", "Xuất sắc", None, None],
    ])
    kq = doc_mau(p)
    assert kq.loi == []
    assert kq.phong_trao_id == 1 and kq.thong_tin["ttr_dv_ngay"] == "2026-11-25"
    n = nhap_ho_so(nv, kq, 1, "Khen QP 2026")
    assert (n.them_moi, n.da_co) == (2, 0)
    tien = sorted(r[0] for r in nv.c.execute("SELECT so_tien FROM ho_so_doi_tuong"))
    assert tien == [759000, 1518000]
    # Nhập lần 2 cùng người: nhận ra đối tượng đã có
    kq2 = doc_mau(p)
    n2 = nhap_ho_so(nv, kq2, 1, "Khen QP 2026 đợt 2")
    assert (n2.them_moi, n2.da_co) == (0, 2)


def test_bao_loi(nv, tmp_path):
    p = xuat_mau(tmp_path / "mau.xlsx", {"id": 1, "ten": "QP", "nam": 2026})
    _dien(p, [
        [1, "Nhóm", None, "X", None, None, None, None, None],
        [2, "Cá nhân", None, None, None, None, None, None, None],
        [3, "Cá nhân", None, "B", None, "Đv", None, None, None],
        [4, "cá nhân", None, " b ", None, "đv", None, None, None],
    ], {"ttr_dv_ngay": "32/13/2026"})
    loi = " | ".join(doc_mau(p).loi)
    assert "Dòng 4" in loi and "Dòng 5" in loi and "trùng với dòng 6" in loi and "Ngày Tờ trình" in loi


def test_file_khong_dung_mau(tmp_path):
    from openpyxl import Workbook
    p = tmp_path / "la.xlsx"
    Workbook().save(p)
    assert "không đúng mẫu" in doc_mau(p).loi[0]
