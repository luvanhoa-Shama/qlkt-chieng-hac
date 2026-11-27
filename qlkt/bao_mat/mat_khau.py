"""Băm và kiểm tra mật khẩu bằng scrypt (thư viện chuẩn, không cần cài thêm)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re

# N=2^15, r=8, p=1: khoảng 0,1 giây/lần trên máy văn phòng; đủ chậm để chống dò mật khẩu
N, R, P, DO_DAI = 2 ** 15, 8, 1, 32
_BO_NHO = 128 * R * N * 2


def bam(mat_khau: str) -> str:
    muoi = os.urandom(16)
    h = hashlib.scrypt(mat_khau.encode("utf-8"), salt=muoi, n=N, r=R, p=P, dklen=DO_DAI, maxmem=_BO_NHO)
    return "scrypt${}${}${}${}${}".format(N, R, P, base64.b64encode(muoi).decode(), base64.b64encode(h).decode())


def kiem_tra(mat_khau: str, chuoi_bam: str) -> bool:
    try:
        ten, n, r, p, muoi, h = chuoi_bam.split("$")
        if ten != "scrypt":
            return False
        n, r, p = int(n), int(r), int(p)
        tinh = hashlib.scrypt(mat_khau.encode("utf-8"), salt=base64.b64decode(muoi), n=n, r=r, p=p,
                              dklen=len(base64.b64decode(h)), maxmem=128 * r * n * 2)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(tinh, base64.b64decode(h))


def loi_mat_khau(mat_khau: str, toi_thieu: int = 8) -> str | None:
    """Trả về lý do mật khẩu chưa đạt, hoặc None nếu đạt."""
    if len(mat_khau) < toi_thieu:
        return f"Mật khẩu cần ít nhất {toi_thieu} ký tự."
    if not re.search(r"[^\W\d_]", mat_khau) or not re.search(r"\d", mat_khau):
        return "Mật khẩu cần có cả chữ và số."
    return None
