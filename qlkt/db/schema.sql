-- CSDL phần mềm quản lý thi đua – khen thưởng UBND xã Chiềng Hặc
-- SQLite. Phiên bản lược đồ: 1
PRAGMA foreign_keys = ON;

-- ===== HỆ THỐNG =====
CREATE TABLE IF NOT EXISTS cau_hinh (
    khoa        TEXT PRIMARY KEY,
    gia_tri     TEXT
);

CREATE TABLE IF NOT EXISTS nguoi_dung (
    id              INTEGER PRIMARY KEY,
    ten_dang_nhap   TEXT NOT NULL UNIQUE,
    ho_ten          TEXT NOT NULL,
    mat_khau_hash   TEXT NOT NULL,
    -- quan_tri | thuong_truc | ke_toan | lanh_dao
    vai_tro         TEXT NOT NULL CHECK (vai_tro IN ('quan_tri','thuong_truc','ke_toan','lanh_dao')),
    so_lan_sai      INTEGER NOT NULL DEFAULT 0,
    bi_khoa         INTEGER NOT NULL DEFAULT 0,
    tao_luc         TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- Nhật ký: ai làm gì, lúc nào. Không cho sửa/xóa (xem trigger bên dưới).
CREATE TABLE IF NOT EXISTS nhat_ky (
    id              INTEGER PRIMARY KEY,
    thoi_gian       TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    nguoi_dung_id   INTEGER REFERENCES nguoi_dung(id),
    hanh_dong       TEXT NOT NULL,      -- them | sua | xoa | dang_nhap | xuat_file | sao_luu ...
    bang            TEXT,
    ban_ghi_id      INTEGER,
    noi_dung        TEXT                -- mô tả thay đổi (không ghi số tài khoản)
);
CREATE TRIGGER IF NOT EXISTS nhat_ky_khong_sua BEFORE UPDATE ON nhat_ky
BEGIN SELECT RAISE(ABORT, 'Không được sửa nhật ký'); END;
CREATE TRIGGER IF NOT EXISTS nhat_ky_khong_xoa BEFORE DELETE ON nhat_ky
BEGIN SELECT RAISE(ABORT, 'Không được xóa nhật ký'); END;

-- ===== DANH MỤC =====
-- Đơn vị đề nghị: 5 phòng chuyên môn, Ban CHQS, Công an xã, MTTQ, trường học, thôn/bản...
CREATE TABLE IF NOT EXISTS don_vi (
    id          INTEGER PRIMARY KEY,
    ten         TEXT NOT NULL UNIQUE,
    loai        TEXT NOT NULL DEFAULT 'khac',   -- phong_chuyen_mon | doan_the | truong_hoc | ban | khac
    dang_dung   INTEGER NOT NULL DEFAULT 1
);

-- Hình thức khen thưởng và hệ số tiền thưởng (× mức lương cơ sở).
-- Hệ số do người dùng nhập theo văn bản hiện hành, không cài cứng trong code.
CREATE TABLE IF NOT EXISTS hinh_thuc (
    id              INTEGER PRIMARY KEY,
    ten             TEXT NOT NULL UNIQUE,       -- VD: Giấy khen của Chủ tịch UBND xã
    loai            TEXT NOT NULL DEFAULT 'khen_thuong' CHECK (loai IN ('khen_thuong','danh_hieu')),
    he_so_ca_nhan   REAL,
    he_so_tap_the   REAL,
    can_cu          TEXT,                        -- điều, khoản quy định mức thưởng
    dang_dung       INTEGER NOT NULL DEFAULT 1
);

-- Mức lương cơ sở theo thời điểm áp dụng (tiền thưởng tính theo mức tại ngày quyết định).
CREATE TABLE IF NOT EXISTS luong_co_so (
    id          INTEGER PRIMARY KEY,
    ap_dung_tu  TEXT NOT NULL UNIQUE,           -- yyyy-mm-dd
    muc         INTEGER NOT NULL,               -- đồng/tháng
    can_cu      TEXT
);

-- Căn cứ pháp lý dùng khi sinh tờ trình/quyết định (người dùng tự cập nhật).
CREATE TABLE IF NOT EXISTS can_cu (
    id          INTEGER PRIMARY KEY,
    noi_dung    TEXT NOT NULL,
    dung_cho    TEXT NOT NULL DEFAULT 'ca_hai' CHECK (dung_cho IN ('to_trinh','quyet_dinh','ca_hai')),
    thu_tu      INTEGER NOT NULL DEFAULT 0,
    dang_dung   INTEGER NOT NULL DEFAULT 1
);

-- ===== ĐỐI TƯỢNG =====
CREATE TABLE IF NOT EXISTS doi_tuong (
    id              INTEGER PRIMARY KEY,
    loai            TEXT NOT NULL CHECK (loai IN ('ca_nhan','tap_the')),
    ten             TEXT NOT NULL,              -- họ tên cá nhân hoặc tên tập thể
    danh_xung       TEXT CHECK (danh_xung IN ('Ông','Bà') OR danh_xung IS NULL),   -- cá nhân
    cap_bac         TEXT,                       -- chỉ lực lượng vũ trang: Đại úy, Thiếu tá...
    nam_sinh        INTEGER,
    gioi_tinh       TEXT CHECK (gioi_tinh IN ('Nam','Nữ') OR gioi_tinh IS NULL),
    chuc_vu         TEXT,
    don_vi_cong_tac TEXT,
    don_vi_id       INTEGER REFERENCES don_vi(id),
    nguoi_dai_dien  TEXT,                       -- tập thể: người nhận tiền thưởng
    -- Dữ liệu nhạy cảm: sẽ mã hóa ở bước 4, chỉ thường trực/kế toán xem được
    so_tai_khoan    TEXT,
    ngan_hang       TEXT,
    ghi_chu         TEXT,
    da_xoa          INTEGER NOT NULL DEFAULT 0,
    tao_luc         TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS ix_doi_tuong_ten ON doi_tuong(ten);

-- ===== PHONG TRÀO & HỒ SƠ =====
CREATE TABLE IF NOT EXISTS phong_trao (
    id              INTEGER PRIMARY KEY,
    ten             TEXT NOT NULL,              -- VD: công tác quân sự, quốc phòng địa phương
    nam             INTEGER NOT NULL,
    ngay_phat_dong  TEXT,
    han_nop_ho_so   TEXT,
    mo_ta           TEXT,
    da_xoa          INTEGER NOT NULL DEFAULT 0
);

-- Một hồ sơ = một tờ trình của đơn vị đề nghị, đi đến một quyết định.
CREATE TABLE IF NOT EXISTS ho_so (
    id              INTEGER PRIMARY KEY,
    phong_trao_id   INTEGER REFERENCES phong_trao(id),
    don_vi_id       INTEGER NOT NULL REFERENCES don_vi(id),
    hinh_thuc_id    INTEGER NOT NULL REFERENCES hinh_thuc(id),
    trich_yeu       TEXT NOT NULL,
    -- Tờ trình của đơn vị đề nghị
    ttr_dv_so       TEXT,
    ttr_dv_ngay     TEXT,
    -- Biên bản họp xét
    bb_so           TEXT,
    bb_ngay         TEXT,
    bb_to_chuc_hop  TEXT,                       -- VD: Tổ TĐ-KT Ban CHQS xã
    bb_so_du        INTEGER,
    bb_tong_so      INTEGER,
    bb_ty_le        TEXT,                       -- VD: 100%
    -- Tờ trình của Phòng VH-XH
    ttr_vhxh_so     TEXT,
    ttr_vhxh_ngay   TEXT,
    -- Quyết định
    qd_so           TEXT,
    qd_ngay         TEXT,
    qd_nguoi_ky     TEXT,
    -- tiep_nhan | tra_lai | da_trinh | da_co_qd | khong_duyet
    trang_thai      TEXT NOT NULL DEFAULT 'tiep_nhan'
                    CHECK (trang_thai IN ('tiep_nhan','tra_lai','da_trinh','da_co_qd','khong_duyet')),
    ly_do_tra_lai   TEXT,
    han_xu_ly       TEXT,
    ghi_chu         TEXT,
    da_xoa          INTEGER NOT NULL DEFAULT 0,
    tao_luc         TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS ix_ho_so_trang_thai ON ho_so(trang_thai);

-- Danh sách tập thể, cá nhân trong hồ sơ; sau khi có QĐ đây chính là lịch sử khen thưởng.
CREATE TABLE IF NOT EXISTS ho_so_doi_tuong (
    id              INTEGER PRIMARY KEY,
    ho_so_id        INTEGER NOT NULL REFERENCES ho_so(id),
    doi_tuong_id    INTEGER NOT NULL REFERENCES doi_tuong(id),
    thu_tu          INTEGER NOT NULL DEFAULT 0,
    tom_tat_thanh_tich TEXT,
    ket_qua         TEXT NOT NULL DEFAULT 'de_nghi' CHECK (ket_qua IN ('de_nghi','duoc_khen','khong_duoc')),
    so_tien         INTEGER,                    -- tính tự động, cho phép sửa tay
    UNIQUE (ho_so_id, doi_tuong_id)
);

CREATE TABLE IF NOT EXISTS tep_dinh_kem (
    id          INTEGER PRIMARY KEY,
    ho_so_id    INTEGER NOT NULL REFERENCES ho_so(id),
    loai        TEXT NOT NULL,                  -- to_trinh_dv | bien_ban | bao_cao_thanh_tich | to_trinh_vhxh | quyet_dinh | khac
    ten_tep     TEXT NOT NULL,
    duong_dan   TEXT NOT NULL,                  -- đường dẫn tương đối trong thư mục dữ liệu
    them_luc    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- Hạn công việc (hạn nộp, hạn báo cáo...) để cảnh báo trên màn hình Tổng quan.
CREATE TABLE IF NOT EXISTS han_cong_viec (
    id              INTEGER PRIMARY KEY,
    tieu_de         TEXT NOT NULL,
    han             TEXT NOT NULL,
    phong_trao_id   INTEGER REFERENCES phong_trao(id),
    ho_so_id        INTEGER REFERENCES ho_so(id),
    da_xong         INTEGER NOT NULL DEFAULT 0,
    ghi_chu         TEXT
);

-- Lịch sử khen thưởng (chỉ các lượt đã có quyết định).
CREATE VIEW IF NOT EXISTS v_lich_su_khen_thuong AS
SELECT hd.doi_tuong_id, dt.loai, dt.ten, dt.chuc_vu, dt.don_vi_cong_tac,
       ht.ten AS hinh_thuc, hs.trich_yeu, hs.qd_so, hs.qd_ngay,
       CAST(substr(hs.qd_ngay,1,4) AS INTEGER) AS nam, hd.so_tien
FROM ho_so_doi_tuong hd
JOIN ho_so hs   ON hs.id = hd.ho_so_id AND hs.da_xoa = 0
JOIN doi_tuong dt ON dt.id = hd.doi_tuong_id
JOIN hinh_thuc ht ON ht.id = hs.hinh_thuc_id
WHERE hs.trang_thai = 'da_co_qd' AND hd.ket_qua = 'duoc_khen';
