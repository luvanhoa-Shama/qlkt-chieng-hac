"""Tạo 2 mẫu Word (docxtpl) trong thư mục mau/: to_trinh.docx, quyet_dinh.docx.

Bố cục theo mẫu Tờ trình, Quyết định của UBND xã Chiềng Hặc (thể thức NĐ 30/2020/NĐ-CP).
Xã có thể mở file mẫu bằng Word để sửa chữ, giữ nguyên các thẻ {{ ... }} và {%p ... %}.
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

GIUA, DEU, PHAI = WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.JUSTIFY, WD_ALIGN_PARAGRAPH.RIGHT


def tai_lieu() -> Document:
    d = Document()
    s = d.sections[0]
    s.page_height, s.page_width = Cm(29.7), Cm(21)
    s.top_margin = s.bottom_margin = Cm(2)
    s.left_margin, s.right_margin = Cm(3), Cm(2)
    st = d.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(14)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    st.paragraph_format.space_after = Pt(0)
    return d


def doan(cha, text: str = "", *, dam=False, nghieng=False, co=None, canh=None, thut=False,
         truoc=0, sau=0, gian=None):
    p = cha.add_paragraph()
    if text:
        r = p.add_run(text)
        r.bold, r.italic = dam, nghieng
        if co:
            r.font.size = Pt(co)
    if canh is not None:
        p.alignment = canh
    pf = p.paragraph_format
    pf.space_before, pf.space_after = Pt(truoc), Pt(sau)
    if thut:
        pf.first_line_indent = Cm(1.27)
    if gian:
        pf.line_spacing = gian
    return p


def bo_vien(bang) -> None:
    tbl = bang._tbl
    pr = tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for k in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{k}")
        e.set(qn("w:val"), "nil")
        b.append(e)
    pr.append(b)


def o(cell, *dong):
    """Ghi các dòng vào ô: mỗi dòng (text, đậm, nghiêng, cỡ)."""
    cell.paragraphs[0].text = ""
    first = True
    for text, dam, nghieng, co in dong:
        p = cell.paragraphs[0] if first else cell.add_paragraph()
        first = False
        p.alignment = GIUA
        r = p.add_run(text)
        r.bold, r.italic, r.font.size = dam, nghieng, Pt(co)


def dau_van_ban(d, trai: list, so: str, ngay: str = "ngay_van_ban") -> None:
    t = d.add_table(rows=1, cols=2)
    bo_vien(t)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.columns[0].width, t.columns[1].width = Cm(6.5), Cm(9.5)
    t.cell(0, 0).width, t.cell(0, 1).width = Cm(6.5), Cm(9.5)
    o(t.cell(0, 0), *trai, ("――――", False, False, 13), (so, False, False, 13))
    o(t.cell(0, 1), ("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", True, False, 12),
      ("Độc lập - Tự do - Hạnh phúc", True, False, 13), ("――――――――――――", False, False, 13),
      ("{{ dia_danh }}, {{ %s }}" % ngay, False, True, 14))


def cuoi_van_ban(d, noi_nhan_key: str, quyen_ky_key: str, nguoi_ky_key: str) -> None:
    t = d.add_table(rows=1, cols=2)
    bo_vien(t)
    t.cell(0, 0).width, t.cell(0, 1).width = Cm(8), Cm(8)
    c = t.cell(0, 0)
    p = c.paragraphs[0]
    r = p.add_run("Nơi nhận:"); r.bold, r.italic, r.font.size = True, True, Pt(12)
    doan(c, f"{{%p for x in {noi_nhan_key} %}}", co=11)
    doan(c, "{{ x }}", co=11)
    doan(c, "{%p endfor %}", co=11)
    c = t.cell(0, 1)
    c.paragraphs[0].text = ""
    doan(c, f"{{%p for x in {quyen_ky_key} %}}", co=14)
    doan(c, "{{ x }}", dam=True, co=14, canh=GIUA)
    doan(c, "{%p endfor %}", co=14)
    for _ in range(4):
        doan(c, "")
    doan(c, f"{{{{ {nguoi_ky_key} }}}}", dam=True, canh=GIUA)


def lap_can_cu(d, key: str) -> None:
    doan(d, f"{{%p for cc in {key} %}}")
    doan(d, "{{ cc }}", nghieng=True, canh=DEU, thut=True, sau=6)
    doan(d, "{%p endfor %}")


def to_trinh(path: Path) -> None:
    d = tai_lieu()
    dau_van_ban(d, [("{{ co_quan_chu_quan }}", False, False, 13), ("{{ ten_phong }}", True, False, 13)],
                "Số: {{ so_ttr }}")
    doan(d, "TỜ TRÌNH", dam=True, canh=GIUA, truoc=12)
    doan(d, "Đề nghị tặng {{ hinh_thuc }} cho {{ doi_tuong_cum }}", dam=True, canh=GIUA)
    doan(d, "{{ noi_dung_khen }}", dam=True, canh=GIUA)
    doan(d, "――――――", canh=GIUA, sau=6)
    doan(d, "Kính gửi: {{ kinh_gui }}.", canh=GIUA, sau=12)
    lap_can_cu(d, "can_cu_ttr")
    doan(d, "{{ cau_xet }}", canh=DEU, thut=True, sau=6)
    doan(d, "{{ ten_phong_thuong }} kính trình {{ kinh_gui }} xem xét, quyết định tặng {{ hinh_thuc }} "
            "với các nội dung như sau:", canh=DEU, thut=True, sau=6)
    doan(d, "I. TÓM TẮT HỒ SƠ ĐỀ NGHỊ", dam=True, thut=True, sau=6)
    doan(d, "{{ don_vi }} đề nghị tặng {{ hinh_thuc }} cho {{ doi_tuong_cum }} {{ noi_dung_khen }}."
            "{{ cau_hop_xet }}", canh=DEU, thut=True, sau=6)
    doan(d, "Hồ sơ gồm: {{ thanh_phan_ho_so }}.", canh=DEU, thut=True, sau=6)
    doan(d, "II. NỘI DUNG CHÍNH CỦA DỰ THẢO QUYẾT ĐỊNH", dam=True, thut=True, sau=6)
    doan(d, "Dự thảo Quyết định của {{ nguoi_quyet_dinh }} gồm 03 điều và danh sách kèm theo:",
         canh=DEU, thut=True, sau=6)
    doan(d, "Điều 1. Tặng {{ hinh_thuc }} cho {{ doi_tuong_cum }} {{ noi_dung_khen }}.",
         canh=DEU, thut=True, sau=6)
    doan(d, "Điều 2. {{ dieu_2 }}", canh=DEU, thut=True, sau=6)
    doan(d, "Dự kiến tiền thưởng: {{ du_kien_tien }}; tổng cộng {{ tong_tien }} đồng.",
         canh=DEU, thut=True, sau=6)
    doan(d, "Điều 3. Hiệu lực thi hành và trách nhiệm thi hành của {{ thi_hanh }}, các tập thể và cá nhân "
            "có tên tại Điều 1.", canh=DEU, thut=True, sau=6)
    doan(d, "III. Ý KIẾN THẨM ĐỊNH CỦA {{ ten_phong }}", dam=True, thut=True, sau=6)
    doan(d, "1. Thẩm quyền: {{ tham_quyen }}", canh=DEU, thut=True, sau=6)
    doan(d, "2. Mức tiền thưởng: {{ cau_muc_thuong }}", canh=DEU, thut=True, sau=6)
    doan(d, "Trên cơ sở hồ sơ được hoàn thiện, {{ ten_phong_thuong }} nhận thấy các tập thể, cá nhân được đề "
            "nghị đều thuộc đối tượng khen thưởng của cấp xã và đề nghị {{ kinh_gui }} xem xét, quyết định.",
         canh=DEU, thut=True, sau=6)
    doan(d, "IV. HỒ SƠ KÈM THEO", dam=True, thut=True, sau=6)
    doan(d, "{%p for x in ho_so_kem_theo %}")
    doan(d, "{{ loop.index }}. {{ x }}{{ ';' if not loop.last else '.' }}", canh=DEU, thut=True)
    doan(d, "{%p endfor %}")
    doan(d, "{{ ten_phong_thuong }} kính trình {{ kinh_gui }} xem xét, quyết định./.",
         canh=DEU, thut=True, truoc=6, sau=12)
    cuoi_van_ban(d, "noi_nhan_ttr", "quyen_ky_ttr", "nguoi_ky_ttr")
    d.save(path)


def quyet_dinh(path: Path) -> None:
    d = tai_lieu()
    dau_van_ban(d, [("ỦY BAN NHÂN DÂN", True, False, 13), ("{{ ten_xa_hoa }}", True, False, 13)],
                "Số: {{ so_qd }}", ngay="ngay_qd")
    doan(d, "QUYẾT ĐỊNH", dam=True, canh=GIUA, truoc=12)
    doan(d, "Tặng {{ hinh_thuc }} cho {{ doi_tuong_cum }}", dam=True, canh=GIUA)
    doan(d, "{{ noi_dung_khen }}", dam=True, canh=GIUA)
    doan(d, "――――――", canh=GIUA, sau=6)
    doan(d, "{{ nguoi_quyet_dinh_hoa }}", dam=True, canh=GIUA, sau=12)
    lap_can_cu(d, "can_cu_qd")
    doan(d, "{{ cau_xet_qd }}", nghieng=True, canh=DEU, thut=True, sau=6)
    doan(d, "QUYẾT ĐỊNH:", dam=True, canh=GIUA, truoc=6, sau=6)
    doan(d, "Điều 1. Tặng {{ hinh_thuc }} cho {{ doi_tuong_cum }} {{ noi_dung_khen }}.",
         canh=DEU, thut=True, sau=6)
    doan(d, "(Có danh sách kèm theo)", nghieng=True, canh=GIUA, sau=6)
    doan(d, "Điều 2. {{ dieu_2 }}", canh=DEU, thut=True, sau=6)
    doan(d, "Điều 3. {{ thi_hanh_qd }}; các tập thể và cá nhân có tên tại Điều 1 chịu trách nhiệm thi "
            "hành Quyết định này./.", canh=DEU, thut=True, sau=12)
    cuoi_van_ban(d, "noi_nhan_qd", "quyen_ky_qd", "nguoi_ky_qd")
    p = doan(d, "")
    p.add_run().add_break(WD_BREAK.PAGE)
    doan(d, "DANH SÁCH", dam=True, canh=GIUA)
    doan(d, "{{ hoa_dau(doi_tuong_cum_chung) }} được tặng {{ hinh_thuc }} {{ noi_dung_khen }}", dam=True, canh=GIUA)
    doan(d, "(Kèm theo Quyết định số {{ so_qd }} {{ ngay_qd }} của {{ nguoi_quyet_dinh }})",
         nghieng=True, canh=GIUA, sau=12)
    doan(d, "{%p if tap_the %}")
    doan(d, "I. TẬP THỂ ({{ '%02d' % tap_the|length }})", dam=True, sau=6)
    doan(d, "{%p for x in tap_the %}")
    doan(d, "{{ loop.index }}. {{ x }}{{ ';' if not loop.last else '.' }}", canh=DEU, thut=True)
    doan(d, "{%p endfor %}")
    doan(d, "{%p endif %}")
    doan(d, "{%p if ca_nhan %}")
    doan(d, "{{ 'II' if tap_the else 'I' }}. CÁ NHÂN ({{ '%02d' % ca_nhan|length }})", dam=True, truoc=6, sau=6)
    doan(d, "{%p for x in ca_nhan %}")
    doan(d, "{{ loop.index }}. {{ x }}{{ ';' if not loop.last else '.' }}", canh=DEU, thut=True)
    doan(d, "{%p endfor %}")
    doan(d, "{%p endif %}")
    doan(d, "(Danh sách này có {{ doi_tuong_cum }})", nghieng=True, canh=GIUA, truoc=12)
    d.save(path)


if __name__ == "__main__":
    ra = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "mau")
    ra.mkdir(parents=True, exist_ok=True)
    to_trinh(ra / "to_trinh.docx")
    quyet_dinh(ra / "quyet_dinh.docx")
    print("Đã tạo mẫu trong", ra)
