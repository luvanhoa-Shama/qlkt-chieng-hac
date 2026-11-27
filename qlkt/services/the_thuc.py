"""Hoàn thiện thể thức sau khi điền mẫu Word (Phụ lục I NĐ 30/2020/NĐ-CP).

Việc cần làm sau khi render vì phụ thuộc nội dung thật:
- Đường kẻ ngang nét liền dưới tên cơ quan (1/3–1/2 dòng chữ), dưới Tiêu ngữ (bằng dòng chữ),
  dưới trích yếu (1/3–1/2 dòng chữ). Mẫu đánh dấu bằng đoạn "[[KE:tỉ_lệ:số_đoạn]]".
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
from docx.table import _Cell

MAU_KE = re.compile(r"\[\[KE:([\d.]+):(\d+)\]\]")
EMU_PER_PT = 12700

# Times New Roman trên Windows; Liberation Serif (cùng kích thước ký tự) trên Linux
_FONT = {
    (False, False): ["C:/Windows/Fonts/times.ttf", "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"],
    (True, False): ["C:/Windows/Fonts/timesbd.ttf", "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"],
    (False, True): ["C:/Windows/Fonts/timesi.ttf", "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"],
    (True, True): ["C:/Windows/Fonts/timesbi.ttf",
                   "/usr/share/fonts/truetype/liberation/LiberationSerif-BoldItalic.ttf"],
}


@lru_cache(maxsize=32)
def _font(dam: bool, nghieng: bool, co: float):
    try:
        from PIL import ImageFont
    except ImportError:
        return None
    for p in _FONT[(dam, nghieng)]:
        if Path(p).exists():
            return ImageFont.truetype(p, size=int(round(co * 10)))   # đo ở 10× cho chính xác
    return None


def do_rong_pt(p, co_mac_dinh: float = 14) -> float:
    """Độ rộng (pt) của đoạn văn nếu in trên một dòng."""
    tong = 0.0
    for r in p.runs:
        if not r.text:
            continue
        co = r.font.size.pt if r.font.size else co_mac_dinh
        f = _font(bool(r.bold), bool(r.italic), co)
        tong += f.getlength(r.text) / 10 if f else len(r.text) * co * 0.5
    return tong


def _vung_rong_pt(p, doc) -> float:
    cha = p._parent
    if isinstance(cha, _Cell) and cha.width:
        return cha.width / EMU_PER_PT - 10.8   # trừ lề trong ô mặc định (2 × 0,19 cm)
    s = doc.sections[0]
    return (s.page_width - s.left_margin - s.right_margin) / EMU_PER_PT


def _ke_ngang(p, le_trai_pt: float, le_phai_pt: float) -> None:
    for r in list(p.runs):
        r._r.getparent().remove(r._r)
    pf = p.paragraph_format
    pf.left_indent, pf.right_indent, pf.first_line_indent = Pt(le_trai_pt), Pt(le_phai_pt), Pt(0)
    pf.space_before, pf.space_after = Pt(4), Pt(0)
    pf.line_spacing = 1.0
    ppr = p._p.get_or_add_pPr()
    # w:pBdr phải đứng trước các phần tử sau trong w:pPr (thứ tự theo lược đồ OOXML)
    sau_pbdr = {qn(f"w:{t}") for t in ("shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap",
                                       "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi",
                                       "adjustRightInd", "snapToGrid", "spacing", "ind", "contextualSpacing",
                                       "mirrorIndents", "suppressOverlap", "jc", "textDirection", "textAlignment",
                                       "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr",
                                       "pPrChange")}
    bdr = OxmlElement("w:pBdr")
    b = OxmlElement("w:bottom")
    for k, v in (("w:val", "single"), ("w:sz", "6"), ("w:space", "1"), ("w:color", "000000")):
        b.set(qn(k), v)
    bdr.append(b)
    vi_tri = next((x for x in ppr if x.tag in sau_pbdr), None)
    if vi_tri is None:
        ppr.append(bdr)
    else:
        vi_tri.addprevious(bdr)
    # dấu đoạn cỡ 2pt để đường kẻ sát dòng chữ phía trên mà không đè lên chữ (rPr luôn ở cuối pPr)
    rpr = ppr.find(qn("w:rPr"))
    if rpr is None:
        rpr = OxmlElement("w:rPr")
        ppr.append(rpr)
    for k in ("w:sz", "w:szCs"):
        for cu in rpr.findall(qn(k)):
            rpr.remove(cu)
        e = OxmlElement(k); e.set(qn("w:val"), "4"); rpr.append(e)


def _cac_doan(doc):
    yield from doc.paragraphs
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                yield from cell.paragraphs


def hoan_thien(duong_dan: str | Path) -> None:
    doc = Document(str(duong_dan))
    for p in list(_cac_doan(doc)):
        m = MAU_KE.fullmatch(p.text.strip())
        if not m:
            continue
        ti_le, n = float(m.group(1)), int(m.group(2))
        vung = _vung_rong_pt(p, doc)
        # các đoạn có chữ ngay phía trên trong cùng vùng chứa
        anh_em = [x for x in p._parent.paragraphs]
        i = next(k for k, x in enumerate(anh_em) if x._p is p._p)
        tren = [x for x in anh_em[:i] if x.text.strip()][-n:]
        dai_nhat = min(max((do_rong_pt(x) for x in tren), default=vung), vung)
        dai = dai_nhat * ti_le
        le = max((vung - dai) / 2, 0)
        _ke_ngang(p, le, le)
    doc.save(str(duong_dan))
