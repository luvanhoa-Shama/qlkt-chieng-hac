# Phần mềm quản lý thi đua – khen thưởng UBND xã Chiềng Hặc

Ứng dụng desktop chạy offline trên Windows 10/11, cài tại Phòng Văn hóa – Xã hội (cơ quan thường trực TĐKT). Các phòng gửi danh sách đề nghị bằng mẫu Excel qua iOffice; Phòng VH-XH nhập vào phần mềm.

**Quy tắc bắt buộc:** repo này chỉ chứa mã nguồn và dữ liệu giả. Không đưa họ tên, CCCD, số tài khoản hay văn bản thật lên đây. `.gitignore` đã chặn file `.db`, `.xls(x)`, `.doc(x)`.

## Tiến độ
| Bước | Nội dung | Trạng thái |
|---|---|---|
| 1 | Thiết kế CSDL + màn hình mẫu (chỉ xem) | Xong |
| 2 | Nhập, sửa: đối tượng, phong trào, hồ sơ; nhập từ Excel; trả lại hồ sơ | Xong |
| 3 | Sinh Tờ trình, QĐ (Word), danh sách, DS chi trả (Excel), báo cáo, xuất liên thông | Đang góp ý |
| 4 | Đăng nhập, phân quyền, mã hóa, sao lưu, bộ cài .exe | Đang góp ý |

## Cài đặt cho người dùng
Tải bộ cài `.exe` (GitHub → Actions → *Dong goi Windows* → Artifacts) và làm theo [docs/huong-dan-su-dung.md](docs/huong-dan-su-dung.md): cài đặt, vai trò, mã hóa, sao lưu, đổi máy.

## Chạy từ mã nguồn (máy có Python 3.11+)
```
pip install -r requirements-dev.txt
python -m qlkt.app                                   # chạy thật: cài đặt lần đầu, mã hóa, đăng nhập
python scripts/tao_du_lieu_mau.py du-lieu/mau.db
python -m qlkt.app --thu du-lieu/mau.db              # chế độ thử: dữ liệu giả, không mã hóa
pytest
```

## Đóng gói
`.github/workflows/dong-goi-windows.yml` chạy trên máy Windows của GitHub: kiểm thử → PyInstaller (`dong-goi/qlkt.spec`) → tự kiểm tra bản đóng gói (`QLKT.exe --kiem-tra`) → Inno Setup (`dong-goi/qlkt.iss`). Chạy khi có PR, khi gắn tag `v*`, hoặc bấm tay (*Run workflow*).

## Quy trình sử dụng (mô hình C)
1. **Phong trào** → chọn phong trào → *Xuất mẫu Excel gửi các phòng* → gửi qua iOffice.
2. Các phòng điền sheet *Thông tin* và *Danh sách*, gửi lại kèm tờ trình.
3. **Hồ sơ đề nghị** → *Nhập hồ sơ từ Excel*: phần mềm báo lỗi từng dòng, nhận ra người đã có, cảnh báo người đã được khen cùng hình thức trong năm.
4. Kiểm tra → *Trả lại bổ sung* (ghi lý do, hạn) hoặc *Trình* (nhập số, ngày TTr VH-XH).
5. Sau khi Chủ tịch ký → *Nhập Quyết định*, bỏ đánh dấu người không có tên trong QĐ. Hồ sơ khóa lại, lịch sử khen thưởng tự cập nhật.

6. Ở mỗi hồ sơ có nút **Xuất**: Tờ trình (Word), Dự thảo QĐ + danh sách (Word), Danh sách đề nghị (Excel), Danh sách chi trả (Excel, có số tài khoản).
7. **Báo cáo**: báo cáo năm (Excel), dữ liệu liên thông CSV/JSON (không chứa số tài khoản).

Văn bản Word là **dự thảo**: rà soát các chỗ `[...]`, căn cứ, rồi trình ký trên iOffice. Mẫu Word nằm ở `mau/`, xã có thể mở bằng Word để sửa chữ (giữ nguyên các thẻ `{{ ... }}`, `{%p ... %}`). Thông tin cơ quan, người ký: **Danh mục → Thông tin cơ quan**.

Bảo mật (bước 4): đăng nhập theo 4 vai trò, CSDL mã hóa AES-256 (SQLCipher), sao lưu tự động. Chi tiết: [docs/huong-dan-su-dung.md](docs/huong-dan-su-dung.md).

Mọi thao tác ghi vào **Danh mục → Nhật ký** (không sửa, không xóa được; số tài khoản không ghi vào nhật ký).

Thiết kế CSDL: [docs/thiet-ke-csdl.md](docs/thiet-ke-csdl.md). Ảnh màn hình mẫu: [docs/anh-man-hinh](docs/anh-man-hinh).
