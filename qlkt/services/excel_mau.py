"""Mẫu Excel gửi các phòng và nhập hồ sơ từ mẫu đã điền.

Quy trình (mô hình C): Phòng VH-XH xuất mẫu cho từng phong trào → gửi các phòng qua
iOffice → phòng điền và gửi lại kèm tờ trình → VH-XH nhập vào phần mềm.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

from qlkt.services.nghiep_vu import LoiNghiepVu, NghiepVu, chuan_hoa

PHIEN_BAN_MAU = "1"
SHEET_TT, SHEET_DS, SHEET_META = "Thông tin", "Danh sách", "_meta"

# (khóa, nhãn, ghi chú hướng dẫn)
O_THONG_TIN = [
    ("don_vi", "Đơn vị đề nghị", "Tên phòng/đơn vị"),
    ("ttr_dv_so", "Số Tờ trình của đơn vị", "VD: 08/TTr-BCH"),
    ("ttr_dv_ngay", "Ngày Tờ trình", "dd/mm/yyyy"),
    ("bb_so", "Số Biên bản họp xét", ""),
    ("bb_ngay", "Ngày họp xét", "dd/mm/yyyy"),
    ("bb_to_chuc_hop", "Tổ/Hội đồng họp xét", ""),
    ("bb_so_du", "Số thành viên dự họp", "số"),
    ("bb_tong_so", "Tổng số thành viên", "số"),
    ("bb_ty_le", "Tỷ lệ biểu quyết nhất trí", "VD: 100%"),
]
COT_DS = [
    ("stt", "STT", 6), ("loai", "Loại (Tập thể/Cá nhân)", 14), ("danh_xung", "Danh xưng/Cấp bậc", 14),
    ("ten", "Họ và tên / Tên tập thể", 30), ("chuc_vu", "Chức vụ", 22),
    ("don_vi_cong_tac", "Đơn vị công tác", 28), ("thanh_tich", "Tóm tắt thành tích", 45),
    ("nguoi_dai_dien", "Người đại diện (tập thể)", 22), ("ghi_chu", "Ghi chú", 18),
]
DONG_TIEU_DE_DS = 3
VIEN = Border(*(Side(style="thin", color="999999"),) * 4)
NEN_TIEU_DE = PatternFill("solid", fgColor="DCE6F1")


def ngay_iso(gia_tri) -> str | None:
    """Đọc ngày từ ô Excel (kiểu ngày hoặc chuỗi dd/mm/yyyy). Sai định dạng → ValueError."""
    if gia_tri in (None, ""):
        return None
    if isinstance(gia_tri, (datetime, date)):
        return gia_tri.strftime("%Y-%m-%d")
    m = re.fullmatch(r"\s*(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\s*", str(gia_tri))
    if not m:
        raise ValueError(f"Ngày không đúng dạng dd/mm/yyyy: {gia_tri}")
    d, mth, y = map(int, m.groups())
    return date(y, mth, d).isoformat()


def xuat_mau(duong_dan: str | Path, phong_trao: dict, ten_don_vi: str = "") -> Path:
    """phong_trao: dict có id, ten, nam, han_nop_ho_so."""
    wb = Workbook()
    tt = wb.active
    tt.title = SHEET_TT
    tt["A1"] = f"HỒ SƠ ĐỀ NGHỊ KHEN THƯỞNG – {phong_trao['ten']} năm {phong_trao['nam']}".upper()
    tt["A1"].font = Font(bold=True, size=13)
    han = phong_trao.get("han_nop_ho_so")
    tt["A2"] = ("Hạn gửi Phòng VH-XH: " + datetime.fromisoformat(han).strftime("%d/%m/%Y")) if han else ""
    tt["A2"].font = Font(italic=True, color="C00000")
    for i, (_, nhan, hd) in enumerate(O_THONG_TIN, start=4):
        tt.cell(i, 1, nhan).font = Font(bold=True)
        c = tt.cell(i, 2, ten_don_vi if i == 4 else None)
        c.border = VIEN
        tt.cell(i, 3, hd).font = Font(italic=True, color="808080")
    tt.column_dimensions["A"].width = 32
    tt.column_dimensions["B"].width = 40
    tt.column_dimensions["C"].width = 20
    tt.cell(len(O_THONG_TIN) + 6, 1, "Điền danh sách ở sheet \"Danh sách\". Không sửa tên sheet và dòng tiêu đề.")

    ds = wb.create_sheet(SHEET_DS)
    ds["A1"] = "DANH SÁCH ĐỀ NGHỊ KHEN THƯỞNG"
    ds["A1"].font = Font(bold=True, size=13)
    for j, (_, nhan, rong) in enumerate(COT_DS, start=1):
        c = ds.cell(DONG_TIEU_DE_DS, j, nhan)
        c.font = Font(bold=True)
        c.fill = NEN_TIEU_DE
        c.border = VIEN
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        ds.column_dimensions[c.column_letter].width = rong
    ds.freeze_panes = ds.cell(DONG_TIEU_DE_DS + 1, 1)
    dv = DataValidation(type="list", formula1='"Tập thể,Cá nhân"', allow_blank=True)
    dv.add(f"B{DONG_TIEU_DE_DS + 1}:B{DONG_TIEU_DE_DS + 500}")
    ds.add_data_validation(dv)

    meta = wb.create_sheet(SHEET_META)
    meta["A1"], meta["B1"] = "phien_ban_mau", PHIEN_BAN_MAU
    meta["A2"], meta["B2"] = "phong_trao_id", phong_trao["id"]
    meta.sheet_state = "hidden"
    duong_dan = Path(duong_dan)
    wb.save(duong_dan)
    return duong_dan


@dataclass
class KetQuaDoc:
    phong_trao_id: int | None = None
    thong_tin: dict = field(default_factory=dict)
    dong: list[dict] = field(default_factory=list)
    loi: list[str] = field(default_factory=list)


def doc_mau(duong_dan: str | Path) -> KetQuaDoc:
    kq = KetQuaDoc()
    try:
        wb = load_workbook(duong_dan, data_only=True)
    except Exception as e:  # noqa: BLE001 - file hỏng, sai định dạng
        kq.loi.append(f"Không mở được file: {e}")
        return kq
    if SHEET_TT not in wb.sheetnames or SHEET_DS not in wb.sheetnames:
        kq.loi.append("File không đúng mẫu của phần mềm (thiếu sheet \"Thông tin\" hoặc \"Danh sách\").")
        return kq
    if SHEET_META in wb.sheetnames:
        v = wb[SHEET_META]["B2"].value
        kq.phong_trao_id = int(v) if v not in (None, "") else None

    tt = wb[SHEET_TT]
    for i, (khoa, nhan, _) in enumerate(O_THONG_TIN, start=4):
        v = tt.cell(i, 2).value
        try:
            if khoa.endswith("_ngay"):
                v = ngay_iso(v)
            elif khoa in ("bb_so_du", "bb_tong_so") and v not in (None, ""):
                v = int(v)
            elif v is not None:
                v = str(v).strip() or None
        except (ValueError, TypeError):
            kq.loi.append(f"Sheet Thông tin – \"{nhan}\": giá trị không hợp lệ ({v}).")
            v = None
        kq.thong_tin[khoa] = v
    if not kq.thong_tin.get("don_vi"):
        kq.loi.append("Sheet Thông tin: chưa ghi Đơn vị đề nghị.")

    ds = wb[SHEET_DS]
    tieu_de = [ds.cell(DONG_TIEU_DE_DS, j).value for j in range(1, len(COT_DS) + 1)]
    if tieu_de != [n for _, n, _ in COT_DS]:
        kq.loi.append("Sheet Danh sách: dòng tiêu đề đã bị sửa, không đúng mẫu.")
        return kq
    for r in range(DONG_TIEU_DE_DS + 1, ds.max_row + 1):
        gia_tri = {k: ds.cell(r, j).value for j, (k, _, _) in enumerate(COT_DS, start=1)}
        if all(v in (None, "") for k, v in gia_tri.items() if k != "stt"):
            continue
        d = {k: (str(v).strip() if v is not None else None) or None for k, v in gia_tri.items()}
        loai = chuan_hoa(d["loai"])
        if loai in ("tập thể", "tap the"):
            d["loai"] = "tap_the"
        elif loai in ("cá nhân", "ca nhan"):
            d["loai"] = "ca_nhan"
        else:
            kq.loi.append(f"Dòng {r}: cột Loại phải là \"Tập thể\" hoặc \"Cá nhân\".")
            continue
        if not d["ten"]:
            kq.loi.append(f"Dòng {r}: chưa có họ tên / tên tập thể.")
            continue
        d["dong_excel"] = r
        kq.dong.append(d)
    da_gap: dict[tuple, int] = {}
    for d in kq.dong:
        khoa = (d["loai"], chuan_hoa(d["ten"]), chuan_hoa(d["don_vi_cong_tac"]))
        if khoa in da_gap:
            kq.loi.append(f"Dòng {d['dong_excel']}: trùng với dòng {da_gap[khoa]} ({d['ten']}).")
        da_gap.setdefault(khoa, d["dong_excel"])
    if not kq.dong and not kq.loi:
        kq.loi.append("Sheet Danh sách chưa có dòng nào.")
    return kq


@dataclass
class KetQuaNhap:
    ho_so_id: int
    them_moi: int = 0
    da_co: int = 0
    canh_bao: list[str] = field(default_factory=list)


def nhap_ho_so(nv: NghiepVu, kq: KetQuaDoc, hinh_thuc_id: int, trich_yeu: str,
               han_xu_ly: str | None = None) -> KetQuaNhap:
    """Tạo hồ sơ từ kết quả đọc mẫu. Chỉ gọi khi kq.loi rỗng."""
    if kq.loi:
        raise LoiNghiepVu("File còn lỗi, chưa nhập được.")
    c = nv.c
    ten_dv = kq.thong_tin["don_vi"]
    dv = next((r for r in c.execute("SELECT * FROM don_vi") if chuan_hoa(r["ten"]) == chuan_hoa(ten_dv)), None)
    dv_id = dv["id"] if dv else nv.luu_danh_muc("don_vi", {"ten": ten_dv, "loai": "khac"})
    tt = {k: v for k, v in kq.thong_tin.items() if k != "don_vi"}
    ho_so_id = nv.tao_ho_so({**tt, "phong_trao_id": kq.phong_trao_id, "don_vi_id": dv_id,
                             "hinh_thuc_id": hinh_thuc_id, "trich_yeu": trich_yeu, "han_xu_ly": han_xu_ly})
    ket_qua = KetQuaNhap(ho_so_id)
    for d in kq.dong:
        cu = nv.tim_doi_tuong_trung(d["loai"], d["ten"], d["don_vi_cong_tac"])
        if cu:
            dt_id = cu["id"]
            ket_qua.da_co += 1
            # cập nhật chức vụ mới nếu mẫu ghi khác
            if d["chuc_vu"] and d["chuc_vu"] != cu["chuc_vu"]:
                nv.sua_doi_tuong(dt_id, {"chuc_vu": d["chuc_vu"]})
        else:
            dt_id = nv.them_doi_tuong({k: d[k] for k in ("loai", "ten", "danh_xung", "chuc_vu",
                                                          "don_vi_cong_tac", "nguoi_dai_dien", "ghi_chu")}
                                      | {"don_vi_id": dv_id})
            ket_qua.them_moi += 1
        cb = nv.them_vao_ho_so(ho_so_id, dt_id, d["thanh_tich"])
        if cb:
            ket_qua.canh_bao.append(f"{d['ten']}: {cb}")
    return ket_qua
