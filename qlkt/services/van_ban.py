"""Sinh văn bản (Word) và danh sách, báo cáo (Excel) từ hồ sơ.

Văn bản sinh ra là DỰ THẢO để cán bộ rà soát, chỉnh sửa trước khi trình ký trên iOffice.
Các chỗ cần cán bộ tự điền được đánh dấu "[...]".
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

from docxtpl import DocxTemplate
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, Side

from qlkt.services.nghiep_vu import ten_hien_thi
from qlkt.services.the_thuc import hoan_thien
from qlkt.services.tien_thuong import doc_so_tien

# Mặc định cấu hình cơ quan (người dùng sửa ở Danh mục → Thông tin cơ quan).
# Không để sẵn họ tên người ký: cán bộ tự nhập.
MAC_DINH = {
    "co_quan_chu_quan": "UBND XÃ CHIỀNG HẶC",
    "ten_phong": "PHÒNG VĂN HÓA - XÃ HỘI",
    "ten_phong_thuong": "Phòng Văn hóa - Xã hội",
    "ky_hieu_ttr": "TTr-VHXH",
    "ten_xa": "Chiềng Hặc",
    "ky_hieu_qd": "QĐ-UBND",
    "quyen_ky_ttr": "KT. TRƯỞNG PHÒNG\nPHÓ TRƯỞNG PHÒNG",
    "nguoi_ky_ttr": "",
    "quyen_ky_qd": "CHỦ TỊCH",
    "nguoi_ky_qd": "",
    "noi_nhan_ttr": "- Như trên;\n- Lưu: VT, VHXH.",
    "noi_nhan_qd": "- Thường trực Đảng ủy;\n- Thường trực HĐND xã;\n- Lãnh đạo UBND xã;\n"
                   "- Như Điều 3 (t/h);\n- Lưu: VT, VHXH.",
    "thi_hanh_qd": "Chánh Văn phòng HĐND và UBND xã; Trưởng phòng Văn hóa - Xã hội; Trưởng phòng Kinh tế; "
                   "các cơ quan, đơn vị có liên quan",
    "nguon_kinh_phi": "nguồn kinh phí thi đua, khen thưởng của xã",
    "nguoi_lap_chi_tra": "",
    "ke_toan": "",
    "truong_phong": "",
}
NHAN_CAU_HINH = {
    "co_quan_chu_quan": "Cơ quan chủ quản (dòng 1 góc trái Tờ trình)",
    "ten_phong": "Tên phòng (dòng 2, in hoa)",
    "ten_phong_thuong": "Tên phòng (viết thường, dùng trong câu)",
    "ky_hieu_ttr": "Ký hiệu Tờ trình",
    "ten_xa": "Tên xã (địa danh)",
    "ky_hieu_qd": "Ký hiệu Quyết định",
    "quyen_ky_ttr": "Quyền hạn, chức vụ ký Tờ trình (mỗi dòng một dòng in)",
    "nguoi_ky_ttr": "Họ tên người ký Tờ trình",
    "quyen_ky_qd": "Quyền hạn, chức vụ ký Quyết định",
    "nguoi_ky_qd": "Họ tên người ký Quyết định",
    "noi_nhan_ttr": "Nơi nhận Tờ trình",
    "noi_nhan_qd": "Nơi nhận Quyết định",
    "thi_hanh_qd": "Thành phần thi hành (Điều 3 QĐ)",
    "nguon_kinh_phi": "Nguồn kinh phí khen thưởng",
    "nguoi_lap_chi_tra": "Người lập danh sách chi trả",
    "ke_toan": "Kế toán",
    "truong_phong": "Trưởng phòng (ký danh sách chi trả)",
}
CHO_DIEN = "[...]"


def thu_muc_mau() -> Path:
    # Khi đóng gói bằng PyInstaller, mẫu nằm trong sys._MEIPASS/mau
    goc = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return goc / "mau"


def doc_cau_hinh(c: sqlite3.Connection) -> dict:
    ch = dict(MAC_DINH)
    for r in c.execute("SELECT khoa, gia_tri FROM cau_hinh"):
        if r[0] in ch and r[1] is not None:
            ch[r[0]] = r[1]
    return ch


def luu_cau_hinh(c: sqlite3.Connection, d: dict) -> None:
    for k, v in d.items():
        if k in MAC_DINH:
            c.execute("INSERT INTO cau_hinh(khoa, gia_tri) VALUES (?, ?) "
                      "ON CONFLICT(khoa) DO UPDATE SET gia_tri=excluded.gia_tri", (k, v or ""))
    c.execute("INSERT INTO nhat_ky(hanh_dong, bang, noi_dung) VALUES ('sua', 'cau_hinh', ?)",
              (", ".join(sorted(d)),))
    c.commit()


def ngay_chu(iso: str | None, thang_mac_dinh: str | None = None) -> str:
    """'2026-02-05' -> 'ngày 05 tháng 02 năm 2026' (NĐ 30: ngày < 10 và tháng 1, 2 thêm số 0).
    Chưa có ngày -> 'ngày      tháng 11 năm 2026' để điền tay."""
    if not iso:
        hn = date.fromisoformat(thang_mac_dinh) if thang_mac_dinh else date.today()
        th = f"{hn.month:02d}" if hn.month <= 2 else str(hn.month)
        return f"ngày      tháng {th} năm {hn.year}"
    d = date.fromisoformat(iso[:10])
    th = f"{d.month:02d}" if d.month <= 2 else str(d.month)
    return f"ngày {d.day:02d} tháng {th} năm {d.year}"


def so_ky_hieu(s: str | None) -> str | None:
    """NĐ 30: số văn bản nhỏ hơn 10 ghi thêm số 0 phía trước ('8/TTr-VHXH' -> '08/TTr-VHXH')."""
    if not s:
        return s
    m = re.match(r"\s*(\d+)(.*)", s)
    return f"{int(m.group(1)):02d}{m.group(2)}" if m else s.strip()


def ngay_so(iso: str | None) -> str:
    return datetime.fromisoformat(iso).strftime("%d/%m/%Y") if iso else CHO_DIEN


def tien(so: int | None) -> str:
    return "" if so is None else f"{so:,}".replace(",", ".")


def he_so_chu(x: float | None) -> str:
    return CHO_DIEN if x is None else (f"{x:g}").replace(".", ",")


def cum_doi_tuong(n_tt: int, n_cn: int) -> str:
    phan = []
    if n_tt:
        phan.append(f"{n_tt:02d} tập thể")
    if n_cn:
        phan.append(f"{n_cn:02d} cá nhân")
    return " và ".join(phan) or CHO_DIEN


def _hoa_dau(s: str) -> str:
    return s[:1].upper() + s[1:]


def ngu_canh(c: sqlite3.Connection, ho_so_id: int) -> dict:
    hs = c.execute("SELECT hs.*, d.ten dv, ht.ten ht, ht.he_so_ca_nhan, ht.he_so_tap_the, ht.can_cu ht_can_cu, "
                   "pt.ten pt, pt.nam pt_nam FROM ho_so hs JOIN don_vi d ON d.id=hs.don_vi_id "
                   "JOIN hinh_thuc ht ON ht.id=hs.hinh_thuc_id LEFT JOIN phong_trao pt ON pt.id=hs.phong_trao_id "
                   "WHERE hs.id=?", (ho_so_id,)).fetchone()
    ch = doc_cau_hinh(c)
    co_qd = hs["trang_thai"] == "da_co_qd"
    dong = c.execute("SELECT hd.*, dt.* , hd.id AS dong_id FROM ho_so_doi_tuong hd "
                     "JOIN doi_tuong dt ON dt.id=hd.doi_tuong_id WHERE hd.ho_so_id=? "
                     + ("AND hd.ket_qua='duoc_khen' " if co_qd else "AND hd.ket_qua!='khong_duoc' ")
                     + "ORDER BY dt.loai DESC, hd.thu_tu, hd.id", (ho_so_id,)).fetchall()
    tt = [d for d in dong if d["loai"] == "tap_the"]
    cn = [d for d in dong if d["loai"] == "ca_nhan"]
    tong = sum(d["so_tien"] or 0 for d in dong)
    pt_ten = (hs["pt"][:1].lower() + hs["pt"][1:]) if hs["pt"] else None
    noi_dung = hs["noi_dung_khen"] or (f"có thành tích xuất sắc trong {pt_ten} năm {hs['pt_nam']}"
                                       if pt_ten else CHO_DIEN)
    ngay_ttr = hs["ttr_vhxh_ngay"]
    ten_xa = ch["ten_xa"]
    nguoi_qd = f"Chủ tịch Ủy ban nhân dân xã {ten_xa}"

    def mo_ta(d) -> str:
        if d["loai"] == "tap_the":
            return d["ten"]
        chuc = ", ".join(x for x in (d["chuc_vu"], d["don_vi_cong_tac"]) if x)
        return ten_hien_thi(d) + (f", {chuc}" if chuc else "")

    muc_cn = next((d["so_tien"] for d in cn if d["so_tien"]), None)
    muc_tt = next((d["so_tien"] for d in tt if d["so_tien"]), None)
    du_kien = "; ".join(x for x in (f"{tien(muc_tt)} đồng/tập thể" if muc_tt else "",
                                     f"{tien(muc_cn)} đồng/cá nhân" if muc_cn else "") if x) or CHO_DIEN
    luong = None
    if muc_cn and hs["he_so_ca_nhan"]:
        luong = round(muc_cn / hs["he_so_ca_nhan"])
    elif muc_tt and hs["he_so_tap_the"]:
        luong = round(muc_tt / hs["he_so_tap_the"])
    can_cu_tien = hs["ht_can_cu"] or CHO_DIEN
    nam = (hs["qd_ngay"] or ngay_ttr or hs["ttr_dv_ngay"] or date.today().isoformat())[:4]

    can_cu = c.execute("SELECT noi_dung, dung_cho FROM can_cu WHERE dang_dung=1 ORDER BY thu_tu, id").fetchall()
    cc_ttr = [x["noi_dung"].rstrip(";.") + ";" for x in can_cu if x["dung_cho"] in ("ca_hai", "to_trinh")]
    cc_qd = [x["noi_dung"].rstrip(";.") + ";" for x in can_cu if x["dung_cho"] in ("ca_hai", "quyet_dinh")]
    if not cc_ttr:
        cc_ttr = [f"Căn cứ {CHO_DIEN} (chưa khai báo căn cứ ở Danh mục);"]
    if not cc_qd:
        cc_qd = [f"Căn cứ {CHO_DIEN} (chưa khai báo căn cứ ở Danh mục);"]

    ttr_dv = (f"Tờ trình số {hs['ttr_dv_so']} {ngay_chu(hs['ttr_dv_ngay'])}" if hs["ttr_dv_so"]
              else f"Tờ trình số {CHO_DIEN}")
    bb = (f" và Biên bản số {hs['bb_so']} {ngay_chu(hs['bb_ngay'])} của {hs['bb_to_chuc_hop'] or CHO_DIEN}"
          if hs["bb_so"] else "")
    hop_xet = ""
    if hs["bb_ngay"]:
        hop_xet = (f" Danh sách đã được {hs['bb_to_chuc_hop'] or CHO_DIEN} họp xét ngày {ngay_so(hs['bb_ngay'])}"
                   + (f", có {hs['bb_so_du']:02d}/{hs['bb_tong_so']:02d} thành viên dự họp"
                      if hs["bb_so_du"] and hs["bb_tong_so"] else "")
                   + (f" và biểu quyết nhất trí {hs['bb_ty_le']}" if hs["bb_ty_le"] else "") + ".")
    thanh_phan = [f"{ttr_dv} của {hs['dv']} kèm danh sách đề nghị"]
    if hs["bb_so"]:
        thanh_phan.append(f"Biên bản số {hs['bb_so']} {ngay_chu(hs['bb_ngay'])}")
    so_ttr_vhxh = so_ky_hieu(hs["ttr_vhxh_so"]) if hs["ttr_vhxh_so"] else f"      /{ch['ky_hieu_ttr']}"
    ten_phong_cau = ch["ten_phong_thuong"][:1].lower() + ch["ten_phong_thuong"][1:]
    # Căn cứ ban hành: mỗi căn cứ một dòng, kết thúc ";", dòng cuối kết thúc "."
    cc_ttr.append(f"Xét {ttr_dv} của {hs['dv']} về việc đề nghị tặng {hs['ht']}{bb}.")
    cc_qd += [f"Xét đề nghị của {hs['dv']} tại {ttr_dv};",
              f"Theo đề nghị của Trưởng {ten_phong_cau} tại Tờ trình số {so_ttr_vhxh.strip()} "
              f"{ngay_chu(ngay_ttr, hs['ttr_dv_ngay'])}."]
    cum = cum_doi_tuong(len(tt), len(cn))

    return {
        **ch,
        "hoa_dau": _hoa_dau,
        "dia_danh": ten_xa,
        "ten_xa_hoa": f"XÃ {ten_xa.upper()}",
        "kinh_gui": nguoi_qd,
        "nguoi_quyet_dinh": nguoi_qd,
        "nguoi_quyet_dinh_hoa": f"CHỦ TỊCH ỦY BAN NHÂN DÂN XÃ {ten_xa.upper()}",
        "so_ttr": so_ttr_vhxh,
        "so_qd": so_ky_hieu(hs["qd_so"]) if co_qd else f"      /{ch['ky_hieu_qd']}",
        "ngay_van_ban": ngay_chu(ngay_ttr, hs["ttr_dv_ngay"]),
        "ngay_qd": ngay_chu(hs["qd_ngay"] if co_qd else None),
        "hinh_thuc": hs["ht"],
        "don_vi": hs["dv"],
        "doi_tuong_cum": cum,
        "doi_tuong_cum_chung": ("tập thể, cá nhân" if tt and cn else "tập thể" if tt else "cá nhân"),
        "noi_dung_khen": noi_dung,
        "can_cu_ttr": cc_ttr,
        "can_cu_qd": cc_qd,
        "cau_hop_xet": hop_xet,
        "thanh_phan_ho_so": "; ".join(thanh_phan),
        "dieu_2": (f"Mức tiền thưởng kèm theo {hs['ht']} thực hiện theo quy định tại {can_cu_tien}. "
                   f"Kinh phí khen thưởng được trích từ {ch['nguon_kinh_phi']} năm {nam}."),
        "du_kien_tien": du_kien,
        "tong_tien": tien(tong),
        "tong_tien_chu": doc_so_tien(tong) if tong else "",
        "thi_hanh": ch["thi_hanh_qd"].replace(";", ","),
        "thi_hanh_qd": ch["thi_hanh_qd"],
        "tham_quyen": f"{CHO_DIEN} (cán bộ ghi ý kiến thẩm định về thẩm quyền và căn cứ)",
        "cau_muc_thuong": (f"Cá nhân được thưởng {he_so_chu(hs['he_so_ca_nhan'])} lần mức lương cơ sở; tập thể "
                           f"được thưởng {he_so_chu(hs['he_so_tap_the'])} lần mức lương cơ sở. Với mức lương cơ sở "
                           f"{tien(luong) if luong else CHO_DIEN} đồng/tháng, mức thưởng là {du_kien} "
                           f"({can_cu_tien})."),
        "ho_so_kem_theo": [f"Dự thảo Quyết định tặng {hs['ht']} và danh sách kèm theo",
                           f"{ttr_dv} của {hs['dv']} kèm danh sách đề nghị"]
                          + ([f"Biên bản số {hs['bb_so']} {ngay_chu(hs['bb_ngay'])}"
                              f" của {hs['bb_to_chuc_hop'] or CHO_DIEN}"] if hs["bb_so"] else [])
                          + ["Báo cáo tóm tắt thành tích của tập thể, cá nhân"],
        "noi_nhan_ttr": ch["noi_nhan_ttr"].splitlines(),
        "noi_nhan_qd": ch["noi_nhan_qd"].splitlines(),
        "quyen_ky_ttr": ch["quyen_ky_ttr"].splitlines(),
        "quyen_ky_qd": ch["quyen_ky_qd"].splitlines(),
        "nguoi_ky_ttr": ch["nguoi_ky_ttr"] or CHO_DIEN,
        "nguoi_ky_qd": (hs["qd_nguoi_ky"] if co_qd and hs["qd_nguoi_ky"] else ch["nguoi_ky_qd"]) or CHO_DIEN,
        "tap_the": [mo_ta(d) for d in tt],
        "ca_nhan": [mo_ta(d) for d in cn],
        # dùng cho Excel
        "_hs": hs, "_tt": tt, "_cn": cn, "_tong": tong, "_nam": nam,
    }


def _ghi_nhat_ky(c: sqlite3.Connection, ho_so_id: int | None, noi_dung: str) -> None:
    c.execute("INSERT INTO nhat_ky(hanh_dong, bang, ban_ghi_id, noi_dung) VALUES ('xuat_file', 'ho_so', ?, ?)",
              (ho_so_id, noi_dung))
    c.commit()


def sinh_word(c: sqlite3.Connection, ho_so_id: int, loai: str, duong_dan: str | Path) -> Path:
    """loai: 'to_trinh' | 'quyet_dinh'."""
    mau = thu_muc_mau() / f"{loai}.docx"
    tpl = DocxTemplate(str(mau))
    nc = {k: v for k, v in ngu_canh(c, ho_so_id).items() if not k.startswith("_")}
    tpl.render(nc, autoescape=True)
    duong_dan = Path(duong_dan)
    tpl.save(str(duong_dan))
    hoan_thien(duong_dan)
    _ghi_nhat_ky(c, ho_so_id, f"{loai}: {duong_dan.name}")
    return duong_dan


# ---------------------------------------------------------------- Excel
VIEN = Border(*(Side(style="thin"),) * 4)
TNR = "Times New Roman"


def _o(ws, r, col, v, dam=False, nghieng=False, canh="left", vien=True, co=12, wrap=True):
    cell = ws.cell(r, col, v)
    cell.font = Font(name=TNR, bold=dam, italic=nghieng, size=co)
    cell.alignment = Alignment(horizontal=canh, vertical="center", wrap_text=wrap)
    if vien:
        cell.border = VIEN
    return cell


def _tieu_de(ws, r, text, ncot, dam=True, nghieng=False, co=13):
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=ncot)
    _o(ws, r, 1, text, dam=dam, nghieng=nghieng, canh="center", vien=False, co=co)


def _vua_trang(ws, ngang: bool = True) -> None:
    ws.page_setup.orientation = "landscape" if ngang else "portrait"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True


def xuat_danh_sach(c: sqlite3.Connection, ho_so_id: int, duong_dan: str | Path) -> Path:
    nc = ngu_canh(c, ho_so_id)
    wb = Workbook()
    ws = wb.active
    ws.title = "Danh sách"
    rong = [6, 32, 34, 45, 14]
    for i, w in enumerate(rong, start=1):
        ws.column_dimensions[chr(64 + i)].width = w
    _tieu_de(ws, 1, "DANH SÁCH", 5)
    _tieu_de(ws, 2, f"Đề nghị tặng {nc['hinh_thuc']} cho {nc['doi_tuong_cum_chung']} {nc['noi_dung_khen']}", 5)
    ws.row_dimensions[2].height = 36
    _tieu_de(ws, 3, f"(Kèm theo Tờ trình số {nc['so_ttr'].strip()} {nc['ngay_van_ban']} của "
                    f"{nc['ten_phong_thuong']})", 5, dam=False, nghieng=True, co=12)
    r = 5
    for j, h in enumerate(["STT", "Họ và tên / Tên tập thể", "Chức vụ, đơn vị công tác", "Tóm tắt thành tích",
                           "Ghi chú"], start=1):
        _o(ws, r, j, h, dam=True, canh="center")
    for nhom, ds in (("A", nc["_tt"]), ("B", nc["_cn"])):
        if not ds:
            continue
        r += 1
        _o(ws, r, 1, nhom, dam=True, canh="center")
        _o(ws, r, 2, f"{'TẬP THỂ' if nhom == 'A' else 'CÁ NHÂN'}: {len(ds):02d}", dam=True)
        for j in (3, 4, 5):
            _o(ws, r, j, None)
        for i, d in enumerate(ds, start=1):
            r += 1
            _o(ws, r, 1, i, canh="center")
            _o(ws, r, 2, ten_hien_thi(d))
            _o(ws, r, 3, ", ".join(x for x in (d["chuc_vu"], d["don_vi_cong_tac"]) if x))
            _o(ws, r, 4, d["tom_tat_thanh_tich"])
            _o(ws, r, 5, None)
    _vua_trang(ws)
    ws.print_title_rows = "5:5"
    duong_dan = Path(duong_dan)
    wb.save(duong_dan)
    _ghi_nhat_ky(c, ho_so_id, f"danh_sach: {duong_dan.name}")
    return duong_dan


def xuat_chi_tra(c: sqlite3.Connection, ho_so_id: int, duong_dan: str | Path) -> Path:
    """Danh sách chi trả tiền thưởng (có số tài khoản: dữ liệu cá nhân, chỉ gửi kế toán)."""
    nc = ngu_canh(c, ho_so_id)
    wb = Workbook()
    ws = wb.active
    ws.title = "Chi trả"
    for i, w in enumerate([6, 32, 36, 14, 22, 14], start=1):
        ws.column_dimensions[chr(64 + i)].width = w
    _tieu_de(ws, 1, "DANH SÁCH CHI TRẢ TIỀN THƯỞNG", 6)
    _tieu_de(ws, 2, f"Tặng {nc['hinh_thuc']} cho {nc['doi_tuong_cum_chung']} {nc['noi_dung_khen']}", 6)
    ws.row_dimensions[2].height = 36
    hs = nc["_hs"]
    qd = (f"(Kèm theo Quyết định số {hs['qd_so']} {ngay_chu(hs['qd_ngay'])})" if hs["qd_so"]
          else "(Dự kiến – chưa có Quyết định)")
    _tieu_de(ws, 3, qd, 6, dam=False, nghieng=True, co=12)
    r = 4
    tong_dong = []
    for tieu_de_nhom, ds, cot in (("I. TẬP THỂ", nc["_tt"], ["STT", "Tên tập thể", "", "Số tiền",
                                                              "Người đại diện", "Ghi chú"]),
                                  ("II. CÁ NHÂN", nc["_cn"], ["STT", "Họ và tên", "Chức vụ, đơn vị công tác",
                                                               "Số tiền", "Số tài khoản", "Ngân hàng"])):
        if not ds:
            continue
        r += 1
        _o(ws, r, 1, tieu_de_nhom, dam=True, vien=False, wrap=False)
        r += 1
        for j, h in enumerate(cot, start=1):
            _o(ws, r, j, h, dam=True, canh="center")
        if ds[0]["loai"] == "tap_the":
            ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=3)
        for i, d in enumerate(ds, start=1):
            r += 1
            if d["loai"] == "tap_the":
                ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=3)
            _o(ws, r, 1, i, canh="center")
            _o(ws, r, 2, ten_hien_thi(d) if d["loai"] == "ca_nhan" else d["ten"])
            if d["loai"] == "ca_nhan":
                _o(ws, r, 3, ", ".join(x for x in (d["chuc_vu"], d["don_vi_cong_tac"]) if x))
            _o(ws, r, 4, d["so_tien"], canh="right").number_format = "#,##0"
            if d["loai"] == "tap_the":
                _o(ws, r, 5, d["nguoi_dai_dien"])
                _o(ws, r, 6, None)
            else:
                _o(ws, r, 5, d["so_tai_khoan"]).number_format = "@"
                _o(ws, r, 6, d["ngan_hang"])
            tong_dong.append(r)
    r += 1
    _o(ws, r, 2, "Tổng cộng", dam=True)
    _o(ws, r, 4, f"=SUM({','.join(f'D{x}' for x in tong_dong)})" if tong_dong else 0,
       dam=True, canh="right").number_format = "#,##0"
    r += 1
    _tieu_de(ws, r, f"Tổng số tiền bằng chữ: {nc['tong_tien_chu']}", 6, dam=False, nghieng=True, co=12)
    r += 1
    _tieu_de(ws, r, f"{nc['dia_danh']}, {ngay_chu(None)}", 6, dam=False, nghieng=True, co=12)
    ws.cell(r, 1).alignment = Alignment(horizontal="right")
    r += 1
    for col, (cv, ten) in zip((2, 3, 5), (("NGƯỜI LẬP", nc["nguoi_lap_chi_tra"]), ("KẾ TOÁN", nc["ke_toan"]),
                                          ("TRƯỞNG PHÒNG", nc["truong_phong"]))):
        _o(ws, r, col, cv, dam=True, canh="center", vien=False)
        _o(ws, r + 4, col, ten or CHO_DIEN, dam=True, canh="center", vien=False)
    _vua_trang(ws)
    duong_dan = Path(duong_dan)
    wb.save(duong_dan)
    _ghi_nhat_ky(c, ho_so_id, f"chi_tra (có số tài khoản): {duong_dan.name}")
    return duong_dan


def xuat_bao_cao_nam(c: sqlite3.Connection, nam: int, duong_dan: str | Path) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "Tổng hợp"
    for i, w in enumerate([6, 40, 12, 12, 18], start=1):
        ws.column_dimensions[chr(64 + i)].width = w
    _tieu_de(ws, 1, f"TỔNG HỢP KẾT QUẢ KHEN THƯỞNG NĂM {nam}", 5)
    r = 3
    for j, h in enumerate(["STT", "Hình thức", "Tập thể", "Cá nhân", "Tiền thưởng (đồng)"], start=1):
        _o(ws, r, j, h, dam=True, canh="center")
    rs = c.execute("SELECT hinh_thuc, SUM(loai='tap_the') tt, SUM(loai='ca_nhan') cn, COALESCE(SUM(so_tien),0) t "
                   "FROM v_lich_su_khen_thuong WHERE nam=? GROUP BY hinh_thuc ORDER BY hinh_thuc", (nam,)).fetchall()
    for i, x in enumerate(rs, start=1):
        r += 1
        for j, v in enumerate([i, x["hinh_thuc"], x["tt"], x["cn"], x["t"]], start=1):
            _o(ws, r, j, v, canh="left" if j == 2 else "center").number_format = "#,##0"
    r += 1
    _o(ws, r, 2, "Cộng", dam=True)
    for j, k in ((3, "tt"), (4, "cn"), (5, "t")):
        _o(ws, r, j, sum(x[k] for x in rs), dam=True, canh="center").number_format = "#,##0"

    ct = wb.create_sheet("Chi tiết")
    cot = ["STT", "Loại", "Tên", "Chức vụ", "Đơn vị công tác", "Hình thức", "Số QĐ", "Ngày QĐ", "Nội dung",
           "Tiền thưởng"]
    for j, (h, w) in enumerate(zip(cot, [6, 10, 30, 22, 28, 28, 16, 12, 40, 14]), start=1):
        _o(ct, 1, j, h, dam=True, canh="center")
        ct.column_dimensions[chr(64 + j)].width = w
    for i, x in enumerate(c.execute("SELECT v.*, dt.danh_xung, dt.cap_bac FROM v_lich_su_khen_thuong v "
                                    "JOIN doi_tuong dt ON dt.id=v.doi_tuong_id WHERE nam=? "
                                    "ORDER BY qd_ngay, v.loai DESC, ten", (nam,)), start=1):
        vals = [i, "Tập thể" if x["loai"] == "tap_the" else "Cá nhân", ten_hien_thi(x), x["chuc_vu"],
                x["don_vi_cong_tac"], x["hinh_thuc"], x["qd_so"], ngay_so(x["qd_ngay"]), x["trich_yeu"], x["so_tien"]]
        for j, v in enumerate(vals, start=1):
            _o(ct, i + 1, j, v).number_format = "#,##0" if j == 10 else "General"
    _vua_trang(ws, ngang=False)
    _vua_trang(ct)
    duong_dan = Path(duong_dan)
    wb.save(duong_dan)
    _ghi_nhat_ky(c, None, f"bao_cao_nam {nam}: {duong_dan.name}")
    return duong_dan


# Trường xuất liên thông. Định dạng chính thức của CSDL TĐKT Bộ Nội vụ: [CHƯA CÓ DỮ LIỆU];
# khi có hướng dẫn sẽ ánh xạ lại. KHÔNG xuất số tài khoản, ngân hàng, năm sinh.
TRUONG_LIEN_THONG = ["ma_luot", "loai_doi_tuong", "ten", "danh_xung", "cap_bac", "chuc_vu", "don_vi_cong_tac",
                     "hinh_thuc", "noi_dung", "so_quyet_dinh", "ngay_quyet_dinh", "co_quan_quyet_dinh",
                     "so_tien"]


def xuat_lien_thong(c: sqlite3.Connection, thu_muc: str | Path, nam: int | None = None) -> tuple[Path, Path]:
    ten_xa = doc_cau_hinh(c)["ten_xa"]
    sql = ("SELECT hd.id ma_luot, dt.loai, dt.ten, dt.danh_xung, dt.cap_bac, dt.chuc_vu, dt.don_vi_cong_tac, "
           "ht.ten hinh_thuc, COALESCE(hs.noi_dung_khen, hs.trich_yeu) noi_dung, hs.qd_so, hs.qd_ngay, hd.so_tien "
           "FROM ho_so_doi_tuong hd JOIN ho_so hs ON hs.id=hd.ho_so_id AND hs.da_xoa=0 "
           "JOIN doi_tuong dt ON dt.id=hd.doi_tuong_id JOIN hinh_thuc ht ON ht.id=hs.hinh_thuc_id "
           "WHERE hs.trang_thai='da_co_qd' AND hd.ket_qua='duoc_khen'"
           + (" AND substr(hs.qd_ngay,1,4)=?" if nam else "") + " ORDER BY hs.qd_ngay, hd.id")
    rows = [{
        "ma_luot": r["ma_luot"], "loai_doi_tuong": "tap_the" if r["loai"] == "tap_the" else "ca_nhan",
        "ten": r["ten"], "danh_xung": r["danh_xung"], "cap_bac": r["cap_bac"], "chuc_vu": r["chuc_vu"],
        "don_vi_cong_tac": r["don_vi_cong_tac"], "hinh_thuc": r["hinh_thuc"], "noi_dung": r["noi_dung"],
        "so_quyet_dinh": r["qd_so"], "ngay_quyet_dinh": r["qd_ngay"],
        "co_quan_quyet_dinh": f"Chủ tịch UBND xã {ten_xa}", "so_tien": r["so_tien"],
    } for r in c.execute(sql, (str(nam),) if nam else ())]
    thu_muc = Path(thu_muc)
    thu_muc.mkdir(parents=True, exist_ok=True)
    hau_to = f"-{nam}" if nam else ""
    p_csv, p_json = thu_muc / f"lien-thong-khen-thuong{hau_to}.csv", thu_muc / f"lien-thong-khen-thuong{hau_to}.json"
    with open(p_csv, "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig để Excel đọc đúng tiếng Việt
        w = csv.DictWriter(f, fieldnames=TRUONG_LIEN_THONG)
        w.writeheader()
        w.writerows(rows)
    p_json.write_text(json.dumps({"don_vi": f"UBND xã {ten_xa}", "xuat_luc": datetime.now().isoformat(timespec="seconds"),
                                  "phien_ban": "1", "ghi_chu": "Định dạng nội bộ; chưa theo chuẩn CSDL TĐKT quốc gia",
                                  "so_luot": len(rows), "du_lieu": rows}, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    _ghi_nhat_ky(c, None, f"lien_thong {len(rows)} lượt: {p_json.name}")
    return p_csv, p_json
