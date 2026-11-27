"""Tính tiền thưởng và đọc số tiền bằng chữ.

Tiền thưởng = hệ số của hình thức khen thưởng × mức lương cơ sở áp dụng tại ngày
quyết định (hoặc ngày tờ trình nếu chưa có QĐ). Hệ số và mức lương cơ sở lấy từ
CSDL do người dùng nhập, không cài cứng ở đây.
"""
from __future__ import annotations

import sqlite3

# Ghi chú làm tròn: hai mẫu thực tế (0,3 × 2.340.000 = 702.000 và 0,3 × 2.530.000
# = 759.000) đều ra số nguyên nên chưa cần quy tắc làm tròn. Quy tắc làm tròn khi
# ra số lẻ: [CẦN XÁC MINH]; tạm làm tròn đến đồng.


def luong_co_so_tai(conn: sqlite3.Connection, ngay: str) -> int | None:
    """Mức lương cơ sở có hiệu lực tại ngày (yyyy-mm-dd), None nếu chưa khai báo."""
    row = conn.execute(
        "SELECT muc FROM luong_co_so WHERE ap_dung_tu <= ? ORDER BY ap_dung_tu DESC LIMIT 1",
        (ngay,),
    ).fetchone()
    return row["muc"] if row else None


def tinh_tien(he_so: float | None, luong: int | None) -> int | None:
    if he_so is None or luong is None:
        return None
    return int(round(he_so * luong))


_SO = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]


def _doc_ba_so(n: int, day_du: bool) -> str:
    """Đọc số 0..999. day_du=True khi phía trước còn nhóm khác (phải đọc 'không trăm')."""
    tram, chuc, dv = n // 100, (n // 10) % 10, n % 10
    phan: list[str] = []
    if tram or day_du:
        phan += [_SO[tram], "trăm"]
    if chuc == 0:
        if dv and (tram or day_du):
            phan.append("linh")
    elif chuc == 1:
        phan.append("mười")
    else:
        phan += [_SO[chuc], "mươi"]
    if dv:
        if dv == 1 and chuc > 1:
            phan.append("mốt")
        elif dv == 5 and chuc > 0:
            phan.append("lăm")
        elif dv == 4 and chuc > 1:
            phan.append("tư")
        else:
            phan.append(_SO[dv])
    return " ".join(phan)


def doc_so_tien(so: int) -> str:
    """VD: 5608000 -> 'Năm triệu sáu trăm linh tám nghìn đồng'."""
    if so == 0:
        return "Không đồng"
    don_vi = ["", "nghìn", "triệu", "tỷ", "nghìn tỷ", "triệu tỷ"]
    nhom: list[int] = []
    while so > 0:
        nhom.append(so % 1000)
        so //= 1000
    phan: list[str] = []
    for i in range(len(nhom) - 1, -1, -1):
        if nhom[i] == 0:
            continue
        chu = _doc_ba_so(nhom[i], day_du=i < len(nhom) - 1)
        phan.append(f"{chu} {don_vi[i]}".strip())
    kq = " ".join(phan) + " đồng"
    return kq[0].upper() + kq[1:]
