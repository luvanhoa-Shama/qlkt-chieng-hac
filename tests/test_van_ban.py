import json

import docx
from openpyxl import load_workbook

from qlkt.services import van_ban as vb


def _chuan_bi(nv):
    nv.c.execute("INSERT INTO can_cu(noi_dung, thu_tu) VALUES ('Căn cứ văn bản A', 1)")
    nv.c.execute("INSERT INTO can_cu(noi_dung, thu_tu, dung_cho) VALUES ('Căn cứ chỉ cho QĐ', 2, 'quyet_dinh')")
    nv.c.commit()
    a = nv.them_doi_tuong({"loai": "ca_nhan", "ten": "Nguyễn Văn A", "cap_bac": "Đại úy",
                           "chuc_vu": "Phó CHT", "don_vi_cong_tac": "Ban CHQS xã", "so_tai_khoan": "999888"})
    b = nv.them_doi_tuong({"loai": "tap_the", "ten": "Dân quân bản Mẫu"})
    hs = nv.tao_ho_so({"don_vi_id": 1, "hinh_thuc_id": 1, "trich_yeu": "QP", "phong_trao_id": 1,
                       "ttr_dv_so": "08/TTr-BCH", "ttr_dv_ngay": "2026-11-25", "bb_so": "07/BB",
                       "bb_ngay": "2026-11-24", "bb_to_chuc_hop": "Tổ TĐ-KT", "bb_so_du": 3, "bb_tong_so": 3,
                       "bb_ty_le": "100%"})
    nv.them_vao_ho_so(hs, a, "Tốt")
    nv.them_vao_ho_so(hs, b, "Tốt")
    return hs


def _chu(p):
    d = docx.Document(p)
    return "\n".join([x.text for x in d.paragraphs] +
                     [c.text for t in d.tables for r in t.rows for c in r.cells])


def test_ngay_chu():
    assert vb.ngay_chu("2026-02-05") == "ngày 05 tháng 02 năm 2026"
    assert vb.ngay_chu("2026-11-26") == "ngày 26 tháng 11 năm 2026"
    assert vb.ngay_chu(None, "2026-11-01") == "ngày      tháng 11 năm 2026"


def test_to_trinh_va_quyet_dinh(nv, tmp_path):
    hs = _chuan_bi(nv)
    vb.luu_cau_hinh(nv.c, {"nguoi_ky_ttr": "Người Ký Mẫu"})
    nv.trinh(hs, "357/TTr-VHXH", "2026-11-26")
    tt = _chu(vb.sinh_word(nv.c, hs, "to_trinh", tmp_path / "tt.docx"))
    assert "Số: 357/TTr-VHXH" in tt and "ngày 26 tháng 11 năm 2026" in tt
    assert "01 tập thể và 01 cá nhân" in tt
    assert "Căn cứ văn bản A;" in tt and "Căn cứ chỉ cho QĐ" not in tt
    assert "759.000 đồng/cá nhân" in tt and "1.518.000 đồng/tập thể" in tt and "2.277.000" in tt
    assert "Người Ký Mẫu" in tt and "{{" not in tt and "{%" not in tt
    qd = _chu(vb.sinh_word(nv.c, hs, "quyet_dinh", tmp_path / "qd.docx"))
    assert "Số:       /QĐ-UBND" in qd and "Căn cứ chỉ cho QĐ;" in qd
    assert "1. Đại úy Nguyễn Văn A, Phó CHT, Ban CHQS xã." in qd
    assert "1. Dân quân bản Mẫu." in qd and "{{" not in qd
    nv.nhap_quyet_dinh(hs, "10/QĐ-UBND", "2026-11-27", "Chủ Tịch Mẫu")
    qd2 = _chu(vb.sinh_word(nv.c, hs, "quyet_dinh", tmp_path / "qd2.docx"))
    assert "Số: 10/QĐ-UBND" in qd2 and "ngày 27 tháng 11 năm 2026" in qd2 and "Chủ Tịch Mẫu" in qd2


def test_excel_va_lien_thong(nv, tmp_path):
    hs = _chuan_bi(nv)
    nv.trinh(hs, "1/TTr", "2026-11-26")
    nv.nhap_quyet_dinh(hs, "10/QĐ-UBND", "2026-11-27", None)
    ws = load_workbook(vb.xuat_chi_tra(nv.c, hs, tmp_path / "ct.xlsx")).active
    vals = [c for r in ws.iter_rows(values_only=True) for c in r if c is not None]
    assert "999888" in vals and "Đại úy Nguyễn Văn A" in vals
    assert any("Hai triệu hai trăm bảy mươi bảy nghìn đồng" in str(v) for v in vals)
    ws = load_workbook(vb.xuat_danh_sach(nv.c, hs, tmp_path / "ds.xlsx")).active
    vals = [c for r in ws.iter_rows(values_only=True) for c in r if c is not None]
    assert "TẬP THỂ: 01" in vals and "999888" not in vals
    vb.xuat_bao_cao_nam(nv.c, 2026, tmp_path / "bc.xlsx")
    p_csv, p_json = vb.xuat_lien_thong(nv.c, tmp_path, 2026)
    data = json.loads(p_json.read_text(encoding="utf-8"))
    assert data["so_luot"] == 2
    assert "999888" not in p_json.read_text(encoding="utf-8") and "999888" not in p_csv.read_text(encoding="utf-8-sig")
    nk = [r[0] for r in nv.c.execute("SELECT noi_dung FROM nhat_ky WHERE hanh_dong='xuat_file'")]
    assert any("chi_tra" in x for x in nk)
