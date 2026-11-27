"""Vai trò và quyền. Kiểm tra ở tầng nghiệp vụ (không chỉ ẩn nút trên giao diện)."""
from __future__ import annotations

VAI_TRO = {
    "quan_tri": "Quản trị hệ thống",
    "thuong_truc": "Thường trực TĐKT (Phòng VH-XH)",
    "ke_toan": "Kế toán",
    "lanh_dao": "Lãnh đạo (chỉ xem)",
}

MO_TA_QUYEN = {
    "xem": "Xem dữ liệu",
    "sua_du_lieu": "Thêm, sửa, xóa cá nhân/tập thể, phong trào, hồ sơ",
    "luong_ho_so": "Trả lại, trình, nhập quyết định",
    "xuat_van_ban": "Sinh Tờ trình, Quyết định, danh sách, báo cáo, xuất liên thông",
    "xem_stk": "Xem số tài khoản",
    "sua_stk": "Sửa số tài khoản, ngân hàng",
    "xuat_chi_tra": "Xuất danh sách chi trả (có số tài khoản)",
    "danh_muc": "Sửa danh mục, thông tin cơ quan",
    "nguoi_dung": "Quản lý tài khoản người dùng",
    "sao_luu": "Sao lưu dữ liệu",
    "khoi_phuc": "Khôi phục dữ liệu từ bản sao lưu",
    "nhat_ky": "Xem nhật ký",
}

QUYEN = {
    "quan_tri": set(MO_TA_QUYEN),
    "thuong_truc": {"xem", "sua_du_lieu", "luong_ho_so", "xuat_van_ban", "xem_stk", "sua_stk", "xuat_chi_tra",
                    "danh_muc", "sao_luu", "nhat_ky"},
    "ke_toan": {"xem", "xem_stk", "sua_stk", "xuat_chi_tra", "sao_luu"},
    "lanh_dao": {"xem", "xuat_van_ban"},
}


class KhongDuQuyen(Exception):
    pass


def co_quyen(vai_tro: str | None, quyen: str) -> bool:
    """vai_tro None = chạy nội bộ (kịch bản, kiểm thử): đủ quyền."""
    if vai_tro is None:
        return True
    return quyen in QUYEN.get(vai_tro, set())


def che_stk(stk: str | None) -> str:
    """Hiện 4 số cuối: ******1234."""
    if not stk:
        return ""
    s = str(stk)
    return "*" * max(len(s) - 4, 0) + s[-4:]
