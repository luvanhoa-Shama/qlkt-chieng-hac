# Phần mềm quản lý thi đua – khen thưởng UBND xã Chiềng Hặc

Ứng dụng desktop chạy offline trên Windows 10/11, cài tại Phòng Văn hóa – Xã hội (cơ quan thường trực TĐKT). Các phòng gửi danh sách đề nghị bằng mẫu Excel qua iOffice; Phòng VH-XH nhập vào phần mềm.

**Quy tắc bắt buộc:** repo này chỉ chứa mã nguồn và dữ liệu giả. Không đưa họ tên, CCCD, số tài khoản hay văn bản thật lên đây. `.gitignore` đã chặn file `.db`, `.xls(x)`, `.doc(x)`.

## Tiến độ
| Bước | Nội dung | Trạng thái |
|---|---|---|
| 1 | Thiết kế CSDL + màn hình mẫu (chỉ xem) | Đang góp ý |
| 2 | Nhập, sửa: đối tượng, phong trào, hồ sơ; nhập từ Excel; trả lại hồ sơ | |
| 3 | Sinh Tờ trình, QĐ (Word), danh sách, DS chi trả (Excel), báo cáo, xuất liên thông | |
| 4 | Đăng nhập, phân quyền, mã hóa, sao lưu, bộ cài .exe | |

## Chạy thử (máy có Python 3.11+)
```
pip install -r requirements-dev.txt
python scripts/tao_du_lieu_mau.py du-lieu/mau.db
python -m qlkt.app du-lieu/mau.db
pytest
```

Thiết kế CSDL: [docs/thiet-ke-csdl.md](docs/thiet-ke-csdl.md). Ảnh màn hình mẫu: [docs/anh-man-hinh](docs/anh-man-hinh).
