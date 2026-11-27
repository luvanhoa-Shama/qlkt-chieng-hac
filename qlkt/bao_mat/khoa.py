"""Khóa mã hóa CSDL.

- Khóa dữ liệu: 32 byte ngẫu nhiên, dùng cho SQLCipher (mã hóa toàn bộ tệp CSDL).
- Lưu trong tệp khoa.json, được bọc hai lớp độc lập:
  1. "may": Windows DPAPI theo tài khoản Windows đang dùng → mở tự động, không phải gõ gì.
     Chép tệp CSDL + khoa.json sang máy khác hoặc tài khoản Windows khác thì lớp này không mở được.
  2. "khoi_phuc": mật khẩu khôi phục (scrypt + AES-GCM) do Quản trị đặt khi cài lần đầu,
     dùng khi cài lại Windows, đổi máy, hoặc khôi phục bản sao lưu trên máy khác.
- Ngoài Windows (máy phát triển, kiểm thử): lớp "may" dùng tệp khóa trong thư mục người dùng.
  Chế độ này chỉ để phát triển, không dùng khi triển khai.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

TEN_TEP = "khoa.json"
_ENTROPY = b"QLKT-ChiengHac-v1"
_KDF = {"n": 2 ** 17, "r": 8, "p": 1}


class LoiKhoa(Exception):
    pass


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode()


def _ub64(s: str) -> bytes:
    return base64.b64decode(s)


def ma_khoa(khoa: bytes) -> str:
    """Mã nhận diện khóa (không lộ khóa), để biết bản sao lưu dùng khóa nào."""
    return hashlib.sha256(b"qlkt-id" + khoa).hexdigest()[:16]


# ------------------------------------------------------------------ lớp "máy"
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    class _BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    def _dpapi(du_lieu: bytes, bao: bool) -> bytes:
        crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
        buf_vao = ctypes.create_string_buffer(du_lieu, len(du_lieu))   # giữ tham chiếu đến hết hàm
        buf_ent = ctypes.create_string_buffer(_ENTROPY, len(_ENTROPY))
        vao = _BLOB(len(du_lieu), ctypes.cast(buf_vao, ctypes.POINTER(ctypes.c_char)))
        ent = _BLOB(len(_ENTROPY), ctypes.cast(buf_ent, ctypes.POINTER(ctypes.c_char)))
        ra = _BLOB()
        ham = crypt32.CryptProtectData if bao else crypt32.CryptUnprotectData
        # 0x1 = CRYPTPROTECT_UI_FORBIDDEN
        if not ham(ctypes.byref(vao), None, ctypes.byref(ent), None, None, 0x1, ctypes.byref(ra)):
            raise LoiKhoa("Windows không mở được khóa (tài khoản Windows hoặc máy đã thay đổi).")
        try:
            return ctypes.string_at(ra.pbData, ra.cbData)
        finally:
            kernel32.LocalFree(ra.pbData)

    def _bao_may(khoa: bytes) -> dict:
        return {"kieu": "dpapi", "du_lieu": _b64(_dpapi(khoa, True))}

    def _mo_may(d: dict) -> bytes:
        if d.get("kieu") != "dpapi":
            raise LoiKhoa("Khóa được tạo ngoài Windows.")
        return _dpapi(_ub64(d["du_lieu"]), False)
else:
    def _khoa_tep() -> bytes:
        p = Path(os.environ.get("QLKT_KHOA_MAY") or Path.home() / ".config" / "qlkt" / "may.key")
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(os.urandom(32))
            os.chmod(p, 0o600)
        return p.read_bytes()

    def _bao_may(khoa: bytes) -> dict:
        nonce = os.urandom(12)
        return {"kieu": "tep", "nonce": _b64(nonce), "du_lieu": _b64(AESGCM(_khoa_tep()).encrypt(nonce, khoa, _ENTROPY))}

    def _mo_may(d: dict) -> bytes:
        if d.get("kieu") != "tep":
            raise LoiKhoa("Khóa được tạo trên Windows, máy này không mở được.")
        try:
            return AESGCM(_khoa_tep()).decrypt(_ub64(d["nonce"]), _ub64(d["du_lieu"]), _ENTROPY)
        except InvalidTag as e:
            raise LoiKhoa("Không mở được khóa trên máy này.") from e


# ------------------------------------------------------------------ lớp "khôi phục"
def _khoa_tu_mat_khau(mk: str, muoi: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(mk.encode("utf-8"), salt=muoi, n=n, r=r, p=p, dklen=32, maxmem=128 * r * n * 2)


def _bao_khoi_phuc(khoa: bytes, mk: str) -> dict:
    muoi, nonce = os.urandom(16), os.urandom(12)
    k = _khoa_tu_mat_khau(mk, muoi, **_KDF)
    return {"kdf": "scrypt", **_KDF, "muoi": _b64(muoi), "nonce": _b64(nonce),
            "du_lieu": _b64(AESGCM(k).encrypt(nonce, khoa, _ENTROPY))}


def _mo_khoi_phuc(d: dict, mk: str) -> bytes:
    k = _khoa_tu_mat_khau(mk, _ub64(d["muoi"]), d["n"], d["r"], d["p"])
    try:
        return AESGCM(k).decrypt(_ub64(d["nonce"]), _ub64(d["du_lieu"]), _ENTROPY)
    except InvalidTag as e:
        raise LoiKhoa("Mật khẩu khôi phục không đúng.") from e


# ------------------------------------------------------------------ tệp khoa.json
def duong_dan_tep(thu_muc: str | Path) -> Path:
    p = Path(thu_muc)
    return p if p.suffix == ".json" else p / TEN_TEP


def co_tep_khoa(thu_muc: str | Path) -> bool:
    return duong_dan_tep(thu_muc).exists()


def _doc(thu_muc) -> dict:
    try:
        return json.loads(duong_dan_tep(thu_muc).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise LoiKhoa(f"Không đọc được tệp khóa: {e}") from e


def _ghi(thu_muc, khoa: bytes, may: dict, khoi_phuc: dict) -> None:
    p = duong_dan_tep(thu_muc)
    tam = p.with_suffix(".tmp")
    tam.write_text(json.dumps({"phien_ban": 1, "ma_khoa": ma_khoa(khoa), "may": may, "khoi_phuc": khoi_phuc},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tam, p)


def tao_khoa(thu_muc: str | Path, mat_khau_khoi_phuc: str) -> bytes:
    if co_tep_khoa(thu_muc):
        raise LoiKhoa("Đã có tệp khóa, không tạo đè.")
    khoa = os.urandom(32)
    _ghi(thu_muc, khoa, _bao_may(khoa), _bao_khoi_phuc(khoa, mat_khau_khoi_phuc))
    return khoa


def mo_khoa(thu_muc: str | Path) -> bytes:
    """Mở tự động bằng lớp "máy". Lỗi → cần mật khẩu khôi phục."""
    d = _doc(thu_muc)
    khoa = _mo_may(d["may"])
    if ma_khoa(khoa) != d.get("ma_khoa"):
        raise LoiKhoa("Tệp khóa bị hỏng.")
    return khoa


def mo_bang_mat_khau_khoi_phuc(thu_muc: str | Path, mk: str, bao_lai_may: bool = True) -> bytes:
    """Mở bằng mật khẩu khôi phục; mặc định bọc lại lớp "máy" để lần sau mở tự động."""
    d = _doc(thu_muc)
    khoa = _mo_khoi_phuc(d["khoi_phuc"], mk)
    if bao_lai_may:
        _ghi(thu_muc, khoa, _bao_may(khoa), d["khoi_phuc"])
    return khoa


def doi_mat_khau_khoi_phuc(thu_muc: str | Path, khoa: bytes, mk_moi: str) -> None:
    d = _doc(thu_muc)
    if d.get("ma_khoa") != ma_khoa(khoa):
        raise LoiKhoa("Khóa không khớp tệp khóa.")
    _ghi(thu_muc, khoa, d["may"], _bao_khoi_phuc(khoa, mk_moi))


def ma_khoa_trong_tep(thu_muc: str | Path) -> str | None:
    return _doc(thu_muc).get("ma_khoa")
