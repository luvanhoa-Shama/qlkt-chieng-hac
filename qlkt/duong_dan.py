"""Nơi lưu dữ liệu.

- Bản cài trên Windows: %LOCALAPPDATA%\\QLKT-ChiengHac\\ (du-lieu, sao-luu). Thư mục theo tài khoản Windows,
  khớp với lớp bảo vệ khóa DPAPI.
- Chạy từ mã nguồn: thư mục hiện tại (du-lieu/, sao-luu/ đã bị .gitignore chặn).
- Biến môi trường QLKT_THU_MUC: đặt thư mục khác (kiểm thử).
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

TEN_UNG_DUNG = "QLKT-ChiengHac"


def thu_muc_goc() -> Path:
    if os.environ.get("QLKT_THU_MUC"):
        return Path(os.environ["QLKT_THU_MUC"])
    if getattr(sys, "frozen", False) and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / TEN_UNG_DUNG
    return Path.cwd()


@dataclass
class MoiTruong:
    du_lieu: Path            # chứa tệp CSDL và khoa.json
    sao_luu: Path
    ten_tep: str = "qlkt.db"

    @property
    def tep_csdl(self) -> Path:
        return self.du_lieu / self.ten_tep

    @classmethod
    def mac_dinh(cls, tep_csdl: str | Path | None = None) -> "MoiTruong":
        if tep_csdl:
            p = Path(tep_csdl).resolve()
            mt = cls(p.parent, p.parent.parent / "sao-luu", p.name)
        else:
            g = thu_muc_goc()
            mt = cls(g / "du-lieu", g / "sao-luu")
        mt.du_lieu.mkdir(parents=True, exist_ok=True)
        mt.sao_luu.mkdir(parents=True, exist_ok=True)
        return mt
