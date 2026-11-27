"""Tạo 2 mẫu Word (docxtpl) trong thư mục mau/: to_trinh.docx, quyet_dinh.docx.

Thể thức theo Phụ lục I Nghị định 30/2020/NĐ-CP (xem docs/the-thuc-nd30.md):
khổ A4; lề trên 2 cm, dưới 2 cm, trái 3 cm, phải 2 cm; Times New Roman; số trang ở giữa lề trên,
không hiện ở trang đầu. Các đường kẻ ngang được tính độ dài khi sinh văn bản (qlkt/services/the_thuc.py),
mẫu chỉ ghi dấu [[KE:tỉ_lệ:số_đoạn_phía_trên]].

Xã có thể mở file mẫu bằng Word để sửa chữ, giữ nguyên các thẻ {{ ... }}, {%p ... %} và [[KE:...]].
Chạy lại script này sẽ GHI ĐÈ mẫu: chỉ chạy khi muốn khôi phục mẫu gốc.
"""
from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

GIUA, DEU = WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.JUSTIFY
CO_ND = 14            # cỡ chữ nội dung (13–14)
SAU_DOAN = 6          # khoảng cách đoạn tối thiểu 6pt
THUT = Cm(1.27)       # lùi đầu dòng 1–1,27 cm
RONG_TRAI, RONG_PHAI = Cm(6.6), Cm(9.4)   # ô 2 (tên cơ quan) và ô 1 (Quốc hiệu)


def tai_lieu() -> Document:
    d = Document()
    s = d.sections[0]
    s.page_height, s.page_width = Cm(29.7), Cm(21)
    s.top_margin = s.bottom_margin = Cm(2)
    s.left_margin, s.right_margin = Cm(3), Cm(2)
    s.header_distance = Cm(1)
    st = d.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(CO_ND)
    rpr = st.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    for k in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(k), "Times New Roman")
    pf = st.paragraph_format
    pf.space_before, pf.space_after, pf.line_spacing = Pt(0), Pt(0), 1.0
    so_trang(s)
    return d


def so_trang(section) -> None:
    """Số trang: chữ số Ả-rập, cỡ 14, đứng, giữa lề trên; không hiện ở trang thứ nhất."""
    section.different_first_page_header_footer = True
    p = section.header.paragraphs[0]
    p.alignment = GIUA
    r = p.add_run()
    r.font.size = Pt(CO_ND)
    for loai, text in (("begin", None), (None, "PAGE"), ("end", None)):
        if loai:
            e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), loai)
        else:
            e = OxmlElement("w:instrText"); e.set(qn("xml:space"), "preserve"); e.text = text
        r._r.append(e)


def doan(cha, *phan, canh=None, thut=False, truoc=0, sau=0, co=None):
    """phan: chuỗi, hoặc (chuỗi, đậm, nghiêng). Trả về paragraph."""
    p = cha.add_paragraph()
    for x in phan:
        text, dam, nghieng = (x, False, False) if isinstance(x, str) else x
        r = p.add_run(text)
        r.bold, r.italic = dam, nghieng
        if co:
            r.font.size = Pt(co)
    if canh is not None:
        p.alignment = canh
    pf = p.paragraph_format
    pf.space_before, pf.space_after = Pt(truoc), Pt(sau)
    if thut:
        pf.first_line_indent = THUT
    return p


def nd(d, *phan, nghieng=False, dam=False, canh=DEU, thut=True, sau=SAU_DOAN, truoc=0):
    """Đoạn nội dung: cỡ 14, căn đều, lùi đầu dòng 1,27 cm, cách đoạn 6pt."""
    phan = [(x, dam, nghieng) if isinstance(x, str) else x for x in phan]
    return doan(d, *phan, canh=canh, thut=thut, sau=sau, truoc=truoc)


def the(d, text):
    """Đoạn chỉ chứa thẻ điều khiển docxtpl ({%p ... %}), sẽ bị xóa khi sinh văn bản."""
    return doan(d, text, co=6)


def ke(cha, ti_le: float, so_doan: int):
    """Dấu đường kẻ ngang: độ dài = tỉ lệ × dòng chữ dài nhất trong so_doan đoạn phía trên."""
    return doan(cha, f"[[KE:{ti_le}:{so_doan}]]", canh=GIUA, co=6)


def bo_vien(bang) -> None:
    pr = bang._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for k in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{k}"); e.set(qn("w:val"), "nil"); b.append(e)
    pr.append(b)


def bang_2_cot(d, rong_trai, rong_phai):
    t = d.add_table(rows=1, cols=2)
    bo_vien(t)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i, w in enumerate((rong_trai, rong_phai)):
        t.columns[i].width = w
        t.cell(0, i).width = w
    return t


def dong_o(cell, text, dam=False, nghieng=False, co=13, dau=False, sau=0):
    p = cell.paragraphs[0] if dau else cell.add_paragraph()
    p.alignment = GIUA
    r = p.add_run(text)
    r.bold, r.italic, r.font.size = dam, nghieng, Pt(co)
    p.paragraph_format.space_after = Pt(sau)
    return p


def dau_van_ban(d, co_quan_tren: tuple[str, bool], co_quan_duoi: str, so: str, ngay_key: str) -> None:
    """Ô 1 Quốc hiệu và Tiêu ngữ; ô 2 tên cơ quan; ô 3 số, ký hiệu; ô 4 địa danh, ngày tháng."""
    t = bang_2_cot(d, RONG_TRAI, RONG_PHAI)
    trai, phai = t.cell(0, 0), t.cell(0, 1)
    # Tên cơ quan chủ quản: in hoa, cỡ 13, đứng (không đậm); tên cơ quan ban hành: in hoa, cỡ 13, đứng, đậm
    dong_o(trai, co_quan_tren[0], dam=co_quan_tren[1], co=13, dau=True)
    dong_o(trai, co_quan_duoi, dam=True, co=13)
    ke(trai, 0.45, 1)                                     # 1/3–1/2 dòng tên cơ quan
    # Số, ký hiệu: "Số" chữ thường, ký hiệu in hoa, cỡ 13, đứng
    p = dong_o(trai, so, co=13)
    p.paragraph_format.space_before = Pt(6)
    # Quốc hiệu: in hoa, cỡ 12–13, đứng, đậm; Tiêu ngữ: cỡ 13–14, đứng, đậm, kẻ ngang bằng độ dài dòng chữ
    dong_o(phai, "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", dam=True, co=12, dau=True)
    dong_o(phai, "Độc lập - Tự do - Hạnh phúc", dam=True, co=13)
    ke(phai, 1, 1)
    # Địa danh, ngày tháng: chữ thường, cỡ 14, nghiêng
    p = dong_o(phai, "{{ dia_danh }}, {{ %s }}" % ngay_key, nghieng=True, co=14)
    p.paragraph_format.space_before = Pt(6)


def ten_loai_trich_yeu(d, ten_loai: str, trich_yeu: str) -> None:
    """Tên loại: in hoa, cỡ 14, đứng, đậm; trích yếu ngay dưới: chữ thường, cỡ 14, đứng, đậm;
    dưới trích yếu kẻ ngang nét liền dài 1/3–1/2 dòng chữ."""
    doan(d, (ten_loai, True, False), canh=GIUA, truoc=18)
    doan(d, (trich_yeu, True, False), canh=GIUA)
    ke(d, 0.4, 1)


def cuoi_van_ban(d, noi_nhan_key: str, quyen_ky_key: str, nguoi_ky_key: str) -> None:
    """Nơi nhận: 'Nơi nhận:' cỡ 12 nghiêng đậm, liệt kê cỡ 11 đứng.
    Quyền hạn, chức vụ: in hoa, cỡ 14, đứng, đậm; họ tên: chữ thường, cỡ 14, đứng, đậm."""
    t = bang_2_cot(d, Cm(8), Cm(8))
    c = t.cell(0, 0)
    p = c.paragraphs[0]
    r = p.add_run("Nơi nhận:"); r.bold, r.italic, r.font.size = True, True, Pt(12)
    the(c, f"{{%p for x in {noi_nhan_key} %}}")
    doan(c, "{{ x }}", co=11)
    the(c, "{%p endfor %}")
    c = t.cell(0, 1)
    the(c, f"{{%p for x in {quyen_ky_key} %}}")
    doan(c, ("{{ x }}", True, False), canh=GIUA, co=14)
    the(c, "{%p endfor %}")
    for _ in range(4):
        doan(c, "", co=14)
    doan(c, (f"{{{{ {nguoi_ky_key} }}}}", True, False), canh=GIUA, co=14)
    # Xóa đoạn trống mặc định đầu ô phải
    c.paragraphs[0]._element.getparent().remove(c.paragraphs[0]._element)


def can_cu(d, key: str) -> None:
    """Căn cứ ban hành: chữ thường, cỡ 14, nghiêng; mỗi căn cứ một dòng, kết thúc ';', dòng cuối '.'."""
    the(d, f"{{%p for cc in {key} %}}")
    nd(d, "{{ cc }}", nghieng=True)
    the(d, "{%p endfor %}")


def to_trinh(path: Path) -> None:
    d = tai_lieu()
    dau_van_ban(d, ("{{ co_quan_chu_quan }}", False), "{{ ten_phong }}", "Số: {{ so_ttr }}", "ngay_van_ban")
    ten_loai_trich_yeu(d, "TỜ TRÌNH", "Đề nghị tặng {{ hinh_thuc }} cho {{ doi_tuong_cum }} {{ noi_dung_khen }}")
    doan(d, "Kính gửi: {{ kinh_gui }}.", canh=GIUA, truoc=6, sau=12)
    can_cu(d, "can_cu_ttr")
    nd(d, "{{ ten_phong_thuong }} kính trình {{ kinh_gui }} xem xét, quyết định tặng {{ hinh_thuc }} "
          "với các nội dung như sau:")
    nd(d, "I. TÓM TẮT HỒ SƠ ĐỀ NGHỊ", dam=True)
    nd(d, "{{ don_vi }} đề nghị tặng {{ hinh_thuc }} cho {{ doi_tuong_cum }} {{ noi_dung_khen }}."
          "{{ cau_hop_xet }}")
    nd(d, "Hồ sơ gồm: {{ thanh_phan_ho_so }}.")
    nd(d, "II. NỘI DUNG CHÍNH CỦA DỰ THẢO QUYẾT ĐỊNH", dam=True)
    nd(d, "Dự thảo Quyết định của {{ nguoi_quyet_dinh }} gồm 03 điều và danh sách kèm theo:")
    nd(d, ("Điều 1. ", True, False), "Tặng {{ hinh_thuc }} cho {{ doi_tuong_cum }} {{ noi_dung_khen }}.")
    nd(d, ("Điều 2. ", True, False), "{{ dieu_2 }}")
    nd(d, "Dự kiến tiền thưởng: {{ du_kien_tien }}; tổng cộng {{ tong_tien }} đồng.")
    nd(d, ("Điều 3. ", True, False), "Hiệu lực thi hành và trách nhiệm thi hành của {{ thi_hanh }}, các tập "
                                     "thể và cá nhân có tên tại Điều 1.")
    nd(d, "III. Ý KIẾN THẨM ĐỊNH CỦA {{ ten_phong }}", dam=True)
    nd(d, "1. Thẩm quyền: {{ tham_quyen }}")
    nd(d, "2. Mức tiền thưởng: {{ cau_muc_thuong }}")
    nd(d, "Trên cơ sở hồ sơ được hoàn thiện, {{ ten_phong_thuong }} nhận thấy các tập thể, cá nhân được đề "
          "nghị đều thuộc đối tượng khen thưởng của cấp xã và đề nghị {{ kinh_gui }} xem xét, quyết định.")
    nd(d, "IV. HỒ SƠ KÈM THEO", dam=True)
    the(d, "{%p for x in ho_so_kem_theo %}")
    nd(d, "{{ loop.index }}. {{ x }}{{ ';' if not loop.last else '.' }}")
    the(d, "{%p endfor %}")
    nd(d, "{{ ten_phong_thuong }} kính trình {{ kinh_gui }} xem xét, quyết định./.", sau=12)
    cuoi_van_ban(d, "noi_nhan_ttr", "quyen_ky_ttr", "nguoi_ky_ttr")
    d.save(path)


def quyet_dinh(path: Path) -> None:
    d = tai_lieu()
    dau_van_ban(d, ("ỦY BAN NHÂN DÂN", True), "{{ ten_xa_hoa }}", "Số: {{ so_qd }}", "ngay_qd")
    ten_loai_trich_yeu(d, "QUYẾT ĐỊNH", "Tặng {{ hinh_thuc }} cho {{ doi_tuong_cum }} {{ noi_dung_khen }}")
    # Thẩm quyền ban hành: in hoa, cỡ 14, đứng, đậm, căn giữa
    doan(d, ("{{ nguoi_quyet_dinh_hoa }}", True, False), canh=GIUA, truoc=6, sau=12)
    can_cu(d, "can_cu_qd")
    doan(d, ("QUYẾT ĐỊNH:", True, False), canh=GIUA, truoc=6, sau=12)
    nd(d, ("Điều 1. ", True, False), "Tặng {{ hinh_thuc }} cho {{ doi_tuong_cum }} {{ noi_dung_khen }}.")
    nd(d, "(Có danh sách kèm theo)", nghieng=True, canh=GIUA, thut=False)
    nd(d, ("Điều 2. ", True, False), "{{ dieu_2 }}")
    nd(d, ("Điều 3. ", True, False), "{{ thi_hanh_qd }}; các tập thể và cá nhân có tên tại Điều 1 chịu trách "
                                     "nhiệm thi hành Quyết định này./.", sau=12)
    cuoi_van_ban(d, "noi_nhan_qd", "quyen_ky_qd", "nguoi_ky_qd")
    p = doan(d, "")
    p.add_run().add_break(WD_BREAK.PAGE)
    # Danh sách kèm theo: tiêu đề in hoa đậm, tên chữ thường đậm, dòng "Kèm theo" nghiêng, kẻ ngang bên dưới
    doan(d, ("DANH SÁCH", True, False), canh=GIUA)
    doan(d, ("{{ hoa_dau(doi_tuong_cum_chung) }} được tặng {{ hinh_thuc }} {{ noi_dung_khen }}", True, False),
         canh=GIUA)
    doan(d, ("(Kèm theo Quyết định số {{ so_qd }} {{ ngay_qd }} của {{ nguoi_quyet_dinh }})", False, True),
         canh=GIUA)
    ke(d, 0.4, 1)
    doan(d, "", sau=6)
    the(d, "{%p if tap_the %}")
    nd(d, "I. TẬP THỂ ({{ '%02d' % tap_the|length }})", dam=True, thut=False)
    the(d, "{%p for x in tap_the %}")
    nd(d, "{{ loop.index }}. {{ x }}{{ ';' if not loop.last else '.' }}")
    the(d, "{%p endfor %}")
    the(d, "{%p endif %}")
    the(d, "{%p if ca_nhan %}")
    nd(d, "{{ 'II' if tap_the else 'I' }}. CÁ NHÂN ({{ '%02d' % ca_nhan|length }})", dam=True, thut=False)
    the(d, "{%p for x in ca_nhan %}")
    nd(d, "{{ loop.index }}. {{ x }}{{ ';' if not loop.last else '.' }}")
    the(d, "{%p endfor %}")
    the(d, "{%p endif %}")
    nd(d, "(Danh sách này có {{ doi_tuong_cum }})", nghieng=True, canh=GIUA, thut=False, truoc=6)
    d.save(path)


if __name__ == "__main__":
    ra = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "mau")
    ra.mkdir(parents=True, exist_ok=True)
    to_trinh(ra / "to_trinh.docx")
    quyet_dinh(ra / "quyet_dinh.docx")
    print("Đã tạo mẫu trong", ra)
