"""Tạo CSDL chứa DỮ LIỆU GIẢ để xem thử giao diện.

Họ tên, số văn bản, số tiền ở đây đều là giả (Nguyễn Văn A, Trần Thị B...).
Không dùng file này cho dữ liệu thật.

Chạy: python scripts/tao_du_lieu_mau.py du-lieu/mau.db
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qlkt.db.database import ket_noi  # noqa: E402
from qlkt.services.tien_thuong import luong_co_so_tai, tinh_tien  # noqa: E402


def tao(duong_dan: Path) -> None:
    duong_dan.parent.mkdir(parents=True, exist_ok=True)
    if duong_dan.exists():
        duong_dan.unlink()
    c = ket_noi(duong_dan)

    don_vi = ["Văn phòng HĐND và UBND xã", "Phòng Kinh tế", "Phòng Văn hóa - Xã hội",
              "Ban Chỉ huy Quân sự xã", "Công an xã", "Trường TH Mẫu A", "Bản Mẫu 1"]
    for ten in don_vi:
        c.execute("INSERT INTO don_vi(ten, loai) VALUES (?, 'khac')", (ten,))

    # Hệ số và mức lương cơ sở: GIÁ TRỊ MẪU để thử. Người dùng nhập lại theo văn bản hiện hành.
    c.execute("INSERT INTO hinh_thuc(ten, he_so_ca_nhan, he_so_tap_the, can_cu) VALUES "
              "('Giấy khen của Chủ tịch UBND xã', 0.3, 0.6, '[CẦN XÁC MINH]')")
    c.execute("INSERT INTO hinh_thuc(ten, loai) VALUES ('Lao động tiên tiến', 'danh_hieu')")
    c.execute("INSERT INTO luong_co_so(ap_dung_tu, muc, can_cu) VALUES ('2024-07-01', 2340000, 'mẫu')")
    c.execute("INSERT INTO luong_co_so(ap_dung_tu, muc, can_cu) VALUES ('2026-10-01', 2530000, 'mẫu')")

    c.execute("INSERT INTO phong_trao(ten, nam, han_nop_ho_so) VALUES "
              "('Công tác quân sự, quốc phòng địa phương', 2026, '2026-11-30')")
    c.execute("INSERT INTO phong_trao(ten, nam, han_nop_ho_so) VALUES "
              "('Toàn dân bảo vệ an ninh Tổ quốc', 2026, '2026-08-15')")
    c.execute("INSERT INTO phong_trao(ten, nam, han_nop_ho_so) VALUES "
              "('Tổng kết năm học 2025-2026', 2026, '2026-12-10')")

    ca_nhan = [
        ("Đại úy", "Nguyễn Văn A", "Phó Chỉ huy trưởng", "Ban Chỉ huy Quân sự xã", 4),
        ("Ông", "Trần Văn B", "Bản đội trưởng", "Bản Mẫu 1", 4),
        ("Bà", "Lê Thị C", "Cán bộ", "Công an xã", 5),
        ("Ông", "Phạm Văn D", "Chuyên viên", "Phòng Kinh tế", 2),
        ("Bà", "Hoàng Thị E", "Hiệu trưởng", "Trường TH Mẫu A", 6),
    ]
    for dx, ten, cv, dv, dvid in ca_nhan:
        cap_bac = None if dx in ("Ông", "Bà") else dx
        c.execute("INSERT INTO doi_tuong(loai, danh_xung, cap_bac, ten, chuc_vu, don_vi_cong_tac, don_vi_id) "
                  "VALUES ('ca_nhan', ?, ?, ?, ?, ?, ?)", ("Ông" if cap_bac else dx, cap_bac, ten, cv, dv, dvid))
    tap_the = [("Ban Chỉ huy Quân sự xã", 4, "Người đại diện A"),
               ("Tập thể Dân quân Bản Mẫu 1", 7, "Người đại diện B"),
               ("Công an xã", 5, "Người đại diện C")]
    for ten, dvid, dd in tap_the:
        c.execute("INSERT INTO doi_tuong(loai, ten, don_vi_cong_tac, don_vi_id, nguoi_dai_dien) "
                  "VALUES ('tap_the', ?, 'xã', ?, ?)", (ten, dvid, dd))

    ho_so = [
        # phong_trao, don_vi, trich_yeu, ttr_dv, ngay_dv, ttr_vhxh, ngay_vhxh, qd_so, qd_ngay, trang_thai, han
        (2, 5, "Khen thưởng phong trào toàn dân bảo vệ ANTQ năm 2026", "01/TTr-CA", "2026-08-05",
         "100/TTr-VHXH", "2026-08-08", "200/QĐ-UBND", "2026-08-12", "da_co_qd", None),
        (1, 4, "Khen thưởng công tác quân sự, quốc phòng địa phương năm 2026", "02/TTr-BCH", "2026-11-25",
         "101/TTr-VHXH", "2026-11-26", None, None, "da_trinh", "2026-12-02"),
        (3, 6, "Khen thưởng tổng kết năm học 2025-2026", "03/TTr-TH", "2026-11-20",
         None, None, None, None, "tra_lai", "2026-11-28"),
        (None, 2, "Khen thưởng cán bộ Phòng Kinh tế năm 2026", None, None,
         None, None, None, None, "tiep_nhan", "2026-12-05"),
    ]
    for pt, dv, ty, a, b, d, e, f, g, tt, han in ho_so:
        c.execute("INSERT INTO ho_so(phong_trao_id, don_vi_id, hinh_thuc_id, trich_yeu, ttr_dv_so, ttr_dv_ngay, "
                  "ttr_vhxh_so, ttr_vhxh_ngay, qd_so, qd_ngay, trang_thai, han_xu_ly, "
                  "bb_so, bb_ngay, bb_so_du, bb_tong_so, bb_ty_le, ly_do_tra_lai) "
                  "VALUES (?,?,1,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (pt, dv, ty, a, b, d, e, f, g, tt, han,
                   *(("01/BB", b, 3, 3, "100%") if b else (None,) * 5),
                   "Thiếu báo cáo tóm tắt thành tích" if tt == "tra_lai" else None))

    def them(hs_id, dt_id, ket_qua, thanh_tich):
        hs = c.execute("SELECT * FROM ho_so WHERE id=?", (hs_id,)).fetchone()
        dt = c.execute("SELECT loai FROM doi_tuong WHERE id=?", (dt_id,)).fetchone()
        ht = c.execute("SELECT * FROM hinh_thuc WHERE id=?", (hs["hinh_thuc_id"],)).fetchone()
        ngay = hs["qd_ngay"] or hs["ttr_vhxh_ngay"] or hs["ttr_dv_ngay"] or "2026-11-27"
        he_so = ht["he_so_ca_nhan"] if dt["loai"] == "ca_nhan" else ht["he_so_tap_the"]
        c.execute("INSERT INTO ho_so_doi_tuong(ho_so_id, doi_tuong_id, ket_qua, tom_tat_thanh_tich, so_tien) "
                  "VALUES (?,?,?,?,?)", (hs_id, dt_id, ket_qua, thanh_tich,
                                         tinh_tien(he_so, luong_co_so_tai(c, ngay))))

    them(1, 3, "duoc_khen", "Hoàn thành xuất sắc nhiệm vụ (mẫu)")
    them(1, 8, "duoc_khen", "Hoàn thành xuất sắc nhiệm vụ (mẫu)")
    for dt in (1, 2, 6, 7):
        them(2, dt, "de_nghi", "Có thành tích xuất sắc (mẫu)")
    them(3, 5, "de_nghi", "Có thành tích (mẫu)")
    them(4, 4, "de_nghi", "Có thành tích (mẫu)")

    c.execute("INSERT INTO han_cong_viec(tieu_de, han, phong_trao_id) VALUES "
              "('Hạn các đơn vị nộp hồ sơ tổng kết năm học', '2026-12-10', 3)")
    c.execute("INSERT INTO han_cong_viec(tieu_de, han) VALUES "
              "('Báo cáo công tác TĐKT năm 2026 gửi cấp trên (mẫu)', '2026-12-15')")
    c.execute("INSERT INTO han_cong_viec(tieu_de, han, ho_so_id) VALUES "
              "('Trường TH Mẫu A bổ sung hồ sơ', '2026-11-28', 3)")
    c.execute("INSERT INTO nguoi_dung(ten_dang_nhap, ho_ten, mat_khau_hash, vai_tro) VALUES "
              "('thuongtruc', 'Cán bộ thường trực (mẫu)', 'chua-dat', 'thuong_truc')")
    c.commit()
    c.close()


if __name__ == "__main__":
    tao(Path(sys.argv[1] if len(sys.argv) > 1 else "du-lieu/mau.db"))
    print("Đã tạo CSDL mẫu (dữ liệu giả).")
