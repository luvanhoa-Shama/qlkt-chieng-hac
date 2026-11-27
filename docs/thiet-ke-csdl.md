# Thiết kế CSDL (bước 1)

Mô hình C: phần mềm cài 1 máy tại Phòng VH-XH; các phòng gửi danh sách bằng mẫu Excel qua iOffice. CSDL là 1 file SQLite (`du-lieu/qlkt.db`). Lược đồ đầy đủ: [`qlkt/db/schema.sql`](../qlkt/db/schema.sql).

## Các bảng

| Bảng | Chứa gì | Ghi chú |
|---|---|---|
| `don_vi` | Đơn vị đề nghị: 5 phòng, Ban CHQS, Công an, MTTQ, trường, bản... | |
| `hinh_thuc` | Hình thức khen thưởng / danh hiệu, **hệ số** tiền thưởng cá nhân, tập thể | Người dùng nhập theo văn bản hiện hành |
| `luong_co_so` | Mức lương cơ sở theo ngày áp dụng | Tiền thưởng tính theo mức tại ngày QĐ |
| `can_cu` | Căn cứ pháp lý dùng khi sinh tờ trình, QĐ | Người dùng tự cập nhật khi luật thay đổi |
| `doi_tuong` | Cá nhân, tập thể | Số tài khoản: mã hóa ở bước 4 |
| `phong_trao` | Phong trào / đợt thi đua, hạn nộp | |
| `ho_so` | 1 hồ sơ = TTr đơn vị → biên bản họp → TTr VH-XH → QĐ | Trạng thái: Mới tiếp nhận, Trả lại, Đã trình, Đã có QĐ, Không duyệt |
| `ho_so_doi_tuong` | Danh sách trong hồ sơ, thành tích, kết quả, tiền thưởng | Sau khi có QĐ đây là lịch sử khen thưởng |
| `tep_dinh_kem` | File scan tờ trình, biên bản, QĐ | |
| `han_cong_viec` | Hạn nộp, hạn báo cáo | Cảnh báo ở màn Tổng quan |
| `nguoi_dung` | Tài khoản: Quản trị, Thường trực, Kế toán, Lãnh đạo | Mật khẩu băm ở bước 4 |
| `nhat_ky` | Ai làm gì, lúc nào | Không sửa, không xóa được (trigger) |
| `v_lich_su_khen_thuong` | View: các lượt đã được khen theo QĐ | Dùng cho tra cứu, báo cáo, xuất liên thông |

## Quy tắc tiền thưởng
`tiền = hệ số (cá nhân/tập thể) × lương cơ sở tại ngày QĐ`. Kiểm tra với 2 mẫu thật của xã: 0,3 × 2.340.000 = 702.000 và 0,3 × 2.530.000 = 759.000; tập thể gấp đôi. Hệ số và ngày áp dụng lương cơ sở trong dữ liệu mẫu chỉ để thử: [CẦN XÁC MINH] trước khi dùng thật.

## Vai trò (mô hình C)
| Vai trò | Quyền |
|---|---|
| Quản trị | Tài khoản, danh mục, sao lưu/khôi phục |
| Thường trực TĐKT | Toàn bộ nghiệp vụ |
| Kế toán | Xem danh sách chi trả, số tài khoản |
| Lãnh đạo | Chỉ xem, báo cáo |
