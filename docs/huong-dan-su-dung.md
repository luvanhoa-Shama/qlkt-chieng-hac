# Hướng dẫn cài đặt và sử dụng

Phần mềm quản lý thi đua – khen thưởng, UBND xã Chiềng Hặc. Cài **một máy** tại Phòng Văn hóa – Xã hội (mô hình C).

> Các thông số dưới đây (vai trò, 5 lần sai, 15 phút khóa phiên, 30 bản sao lưu) là **đề xuất mặc định** của bản dựng, chưa phải quy chế của xã. Thay đổi được nếu xã có quy định khác.

## 1. Cài đặt

| Bước | Việc làm |
|---|---|
| 1 | Tải tệp `QLKT-ChiengHac-CaiDat-x.y.z.exe` (Quản trị tải từ GitHub → Actions → lần dựng mới nhất → Artifacts). |
| 2 | Chạy tệp cài. Windows có thể báo "Windows protected your PC" vì bộ cài chưa có chữ ký số → *More info* → *Run anyway*. |
| 3 | Mở phần mềm lần đầu → màn **Cài đặt lần đầu**: tạo tài khoản Quản trị và **mật khẩu khôi phục**. |
| 4 | Ghi mật khẩu khôi phục ra giấy, cho vào phong bì niêm phong, giao Lãnh đạo giữ. Không lưu trong máy, không gửi qua Zalo/email. |
| 5 | **Quản trị → Tài khoản**: tạo tài khoản cho từng người (mật khẩu tạm, giao trực tiếp). |
| 6 | **Danh mục**: nhập thông tin cơ quan, người ký, hình thức khen thưởng và hệ số, mức lương cơ sở, căn cứ pháp lý. |

Yêu cầu máy: Windows 10 (bản 1809 trở lên) hoặc 11, 64-bit. Không cần Internet.

Dữ liệu nằm ở `%LOCALAPPDATA%\QLKT-ChiengHac\` (thư mục `du-lieu` và `sao-luu`). Gỡ cài đặt **không** xóa dữ liệu.

## 2. Vai trò

| Quyền | Quản trị | Thường trực TĐKT | Kế toán | Lãnh đạo |
|---|:-:|:-:|:-:|:-:|
| Xem hồ sơ, lịch sử khen thưởng, báo cáo | ✓ | ✓ | ✓ | ✓ |
| Thêm, sửa, xóa cá nhân/tập thể, phong trào, hồ sơ; nhập Excel | ✓ | ✓ | | |
| Trả lại, trình, nhập quyết định | ✓ | ✓ | | |
| Sinh Tờ trình, QĐ, danh sách, báo cáo, xuất liên thông | ✓ | ✓ | | ✓ |
| Xem, sửa số tài khoản; xuất danh sách chi trả | ✓ | ✓ | ✓ | |
| Sửa danh mục, thông tin cơ quan; xem nhật ký | ✓ | ✓ | | |
| Sao lưu | ✓ | ✓ | ✓ | |
| Khôi phục, quản lý tài khoản, đổi mật khẩu khôi phục | ✓ | | | |

Lãnh đạo thấy số tài khoản dạng `******1234`. Quyền được kiểm tra ở tầng nghiệp vụ, không chỉ ẩn nút.

## 3. Đăng nhập, mật khẩu

- Mật khẩu ít nhất 8 ký tự, có chữ và số. Mật khẩu tạm do Quản trị cấp phải đổi ở lần đăng nhập đầu.
- Sai 5 lần liên tiếp → tài khoản bị khóa; Quản trị vào **Quản trị → Mở khóa** hoặc **Đặt lại mật khẩu**.
- Không thao tác 15 phút → phiên bị khóa, nhập lại mật khẩu để tiếp tục.
- Người chuyển công tác: **Sửa** tài khoản, bỏ chọn *Đang sử dụng* (không xóa, để giữ nhật ký).
- Phải luôn còn ít nhất một tài khoản Quản trị đang dùng.

## 4. Mã hóa dữ liệu

- Tệp CSDL mã hóa AES-256 (SQLCipher). Chép tệp `.db` đi nơi khác cũng không đọc được.
- Khóa giải mã lưu trong `khoa.json`, được bọc hai lớp:
  1. Windows (DPAPI) theo tài khoản đăng nhập Windows: phần mềm tự mở, không phải gõ.
  2. Mật khẩu khôi phục: dùng khi cài lại Windows, đổi máy, đổi tài khoản Windows, hoặc mở bản sao lưu ở máy khác.
- **Mất mật khẩu khôi phục và hỏng máy (hoặc cài lại Windows) = mất dữ liệu.** Không có "cửa sau".

## 5. Sao lưu, khôi phục

| Việc | Cách làm |
|---|---|
| Tự động | Khi mở phần mềm (mỗi ngày một lần) và khi thoát. Giữ 30 bản tự động gần nhất. |
| Sao lưu tay | **Quản trị → Sao lưu ngay**. |
| Ra USB | **Quản trị → Sao lưu ra USB/thư mục khác…** (nên làm hằng tuần, cất USB nơi an toàn). Kèm tệp `khoa-….json`. |
| Khôi phục | **Quản trị → Khôi phục bản đã chọn…** hoặc **từ tệp khác…**. Phần mềm kiểm tra bản sao, sao lưu dữ liệu hiện tại (`qlkt-truoc-khoi-phuc-…`) rồi mới thay. |
| Bản sao từ máy khác | Để tệp `qlkt-….db` và `khoa-….json` cùng thư mục; phần mềm hỏi mật khẩu khôi phục của máy cũ. |

## 6. Đổi máy, cài lại Windows

1. Máy cũ: **Sao lưu ra USB** (hoặc chép cả thư mục `%LOCALAPPDATA%\QLKT-ChiengHac`).
2. Máy mới: cài phần mềm. Cách A: chép thư mục `du-lieu` cũ vào `%LOCALAPPDATA%\QLKT-ChiengHac\` → mở phần mềm → nhập mật khẩu khôi phục. Cách B: mở phần mềm, cài đặt lần đầu (tạo khóa mới) → **Quản trị → Khôi phục từ tệp khác…** chọn bản trên USB → nhập mật khẩu khôi phục của máy cũ.

## 7. Nhật ký

**Danh mục → Nhật ký** ghi: đăng nhập (cả sai), khóa tài khoản, thêm/sửa/xóa, chuyển trạng thái hồ sơ, xuất văn bản, sao lưu, khôi phục. Không sửa, không xóa được; không ghi số tài khoản, mật khẩu.

## 8. Chế độ thử (dữ liệu giả)

`python -m qlkt.app --thu du-lieu/mau.db`: không mã hóa, không đăng nhập. Chỉ để xem thử, không nhập dữ liệu thật.

## Chưa làm / cần quyết định

- Chữ ký số cho bộ cài (để Windows không cảnh báo): cần chứng thư ký mã (có phí) — [CẦN XÁC MINH] xã có nhu cầu không.
- Quy chế quản lý mật khẩu khôi phục, thời hạn lưu bản sao lưu: theo quy định bảo vệ dữ liệu cá nhân của cơ quan — [CẦN XÁC MINH].
