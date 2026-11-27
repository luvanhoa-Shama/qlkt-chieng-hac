"""Sao lưu, khôi phục CSDL.

- Bản sao lưu là tệp CSDL đã mã hóa bằng cùng khóa (đọc được khi có khoa.json + mật khẩu khôi phục).
- Kèm theo bản sao tệp khóa khoa-<mã>.json (bản thân tệp này đã được bọc bằng DPAPI và mật khẩu khôi phục).
- Tự động: khi mở phần mềm (nếu bản tự động gần nhất cũ hơn 20 giờ) và khi thoát. Giữ 30 bản tự động gần nhất.
- Khôi phục: luôn sao lưu dữ liệu hiện tại trước ("truoc-khoi-phuc"), kiểm tra toàn vẹn bản sao rồi mới thay.
"""
from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from qlkt.bao_mat import khoa as kh
from qlkt.db.database import LOI_CSDL, SaiKhoa, ket_noi, mo_tho

GIU_TU_DONG = 30
CHU_KY_GIO = 20


@dataclass
class ThongTinBanSao:
    duong_dan: Path
    so_ho_so: int
    so_doi_tuong: int
    lan_sua_cuoi: str | None


def _ghi_nhat_ky(conn, nguoi_dung_id, hanh_dong: str, noi_dung: str) -> None:
    conn.execute("INSERT INTO nhat_ky(nguoi_dung_id, hanh_dong, bang, noi_dung) VALUES (?,?,?,?)",
                 (nguoi_dung_id, hanh_dong, "he_thong", noi_dung))
    conn.commit()


def _chep_tep_khoa(thu_muc_du_lieu: Path, thu_muc_dich: Path) -> None:
    nguon = kh.duong_dan_tep(thu_muc_du_lieu)
    if not nguon.exists():
        return
    ma = kh.ma_khoa_trong_tep(nguon)
    dich = thu_muc_dich / f"khoa-{ma}.json"
    if not dich.exists() or dich.read_bytes() != nguon.read_bytes():
        shutil.copy2(nguon, dich)


def sao_luu(conn, khoa: bytes | None, thu_muc: str | Path, loai: str = "tay",
            thu_muc_du_lieu: str | Path | None = None, nguoi_dung_id: int | None = None) -> Path:
    thu_muc = Path(thu_muc)
    thu_muc.mkdir(parents=True, exist_ok=True)
    dich = thu_muc / f"qlkt-{loai}-{datetime.now():%Y%m%d-%H%M%S}.db"
    i = 1
    while dich.exists():
        dich = dich.with_name(f"{dich.stem}-{i}.db"); i += 1
    dst = mo_tho(dich, khoa)
    try:
        conn.backup(dst)
    finally:
        dst.close()
    if thu_muc_du_lieu is not None:
        _chep_tep_khoa(Path(thu_muc_du_lieu), thu_muc)
    _ghi_nhat_ky(conn, nguoi_dung_id, "sao_luu", f"{loai}: {dich.name}")
    if loai == "tu-dong":
        don_dep(thu_muc)
    return dich


def danh_sach(thu_muc: str | Path) -> list[Path]:
    p = Path(thu_muc)
    return sorted(p.glob("qlkt-*.db"), key=lambda x: x.stat().st_mtime, reverse=True) if p.exists() else []


def don_dep(thu_muc: str | Path, giu: int = GIU_TU_DONG) -> None:
    tu_dong = [p for p in danh_sach(thu_muc) if p.name.startswith("qlkt-tu-dong-")]
    for p in tu_dong[giu:]:
        p.unlink(missing_ok=True)


def can_sao_luu_tu_dong(thu_muc: str | Path) -> bool:
    tu_dong = [p for p in danh_sach(thu_muc) if p.name.startswith("qlkt-tu-dong-")]
    return not tu_dong or time.time() - tu_dong[0].stat().st_mtime > CHU_KY_GIO * 3600


def kiem_tra_ban_sao(duong_dan: str | Path, khoa: bytes | None) -> ThongTinBanSao:
    """Mở thử, kiểm tra toàn vẹn. Sai khóa → SaiKhoa; hỏng/không phải CSDL phần mềm → ValueError."""
    conn = mo_tho(duong_dan, khoa)
    try:
        kq = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if kq != "ok":
            raise ValueError(f"Bản sao lưu bị hỏng: {kq}")
        bang = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"ho_so", "doi_tuong", "nhat_ky"} <= bang:
            raise ValueError("Tệp này không phải CSDL của phần mềm.")
        return ThongTinBanSao(Path(duong_dan),
                              conn.execute("SELECT count(*) FROM ho_so WHERE da_xoa=0").fetchone()[0],
                              conn.execute("SELECT count(*) FROM doi_tuong WHERE da_xoa=0").fetchone()[0],
                              conn.execute("SELECT max(thoi_gian) FROM nhat_ky").fetchone()[0])
    except LOI_CSDL as e:
        raise ValueError(f"Không đọc được bản sao lưu: {e}") from e
    finally:
        conn.close()


def tim_khoa_cho_ban_sao(ban_sao: str | Path, mat_khau_khoi_phuc: str) -> bytes:
    """Bản sao lưu từ máy/lần cài khác: thử các tệp khoa-*.json cạnh bản sao với mật khẩu khôi phục."""
    thu_muc = Path(ban_sao).parent
    tep = sorted(thu_muc.glob("khoa-*.json")) + ([thu_muc / kh.TEN_TEP] if (thu_muc / kh.TEN_TEP).exists() else [])
    if not tep:
        raise kh.LoiKhoa("Không thấy tệp khoa-….json cạnh bản sao lưu.")
    for t in tep:
        try:
            k = kh.mo_bang_mat_khau_khoi_phuc(t, mat_khau_khoi_phuc, bao_lai_may=False)
        except kh.LoiKhoa:
            continue
        try:
            mo_tho(ban_sao, k).close()
            return k
        except SaiKhoa:
            continue
    raise kh.LoiKhoa("Mật khẩu khôi phục không mở được bản sao lưu này.")


def khoi_phuc(conn, khoa: bytes | None, tep_csdl: str | Path, ban_sao: str | Path,
              thu_muc_sao_luu: str | Path, khoa_ban_sao: bytes | None = None,
              thu_muc_du_lieu: str | Path | None = None, nguoi_dung_id: int | None = None):
    """Thay CSDL hiện tại bằng bản sao lưu. Trả về kết nối mới (kết nối cũ đã đóng)."""
    khoa_ban_sao = khoa if khoa_ban_sao is None else khoa_ban_sao
    tt = kiem_tra_ban_sao(ban_sao, khoa_ban_sao)
    truoc = sao_luu(conn, khoa, thu_muc_sao_luu, "truoc-khoi-phuc", thu_muc_du_lieu, nguoi_dung_id)
    tep_csdl = Path(tep_csdl)
    tam = tep_csdl.with_name(tep_csdl.name + ".khoi-phuc")
    tam.unlink(missing_ok=True)
    shutil.copy2(ban_sao, tam)
    if khoa_ban_sao != khoa:   # bản sao dùng khóa khác: đổi sang khóa của máy này
        t = mo_tho(tam, khoa_ban_sao)
        t.execute(f"PRAGMA rekey = \"x'{khoa.hex()}'\"")
        t.close()
    conn.close()
    for duoi in ("-wal", "-shm"):
        Path(str(tep_csdl) + duoi).unlink(missing_ok=True)
    os.replace(tam, tep_csdl)
    moi = ket_noi(tep_csdl, khoa)
    _ghi_nhat_ky(moi, nguoi_dung_id, "khoi_phuc",
                 f"Từ {Path(ban_sao).name} ({tt.so_ho_so} hồ sơ); bản trước khôi phục: {truoc.name}")
    return moi
