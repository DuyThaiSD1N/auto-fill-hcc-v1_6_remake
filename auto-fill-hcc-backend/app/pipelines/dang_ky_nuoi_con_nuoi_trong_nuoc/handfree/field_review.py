"""Bổ sung ô còn trống trên tờ khai đăng ký nuôi con nuôi trong nước sau khi điền (chat/field_review)."""

PROCEDURE_KEYS = ("dang-ky-nuoi-con-nuoi-trong-nuoc",)

# Khối chứa thông tin một người — ô con không có thẻ x-* riêng, dropdown không có name: vợ chồng cùng nhận
# (VoChongNhanNuoi_*), người đơn thân (NguoiDonThanNhanNuoi: tích Cha / Mẹ nuôi → MeNuoi / ChaNuoi), nơi trẻ đang sống
# (hienSongTai_*). Dropdown không tên mang khóa "<khối>#<nhãn>".
NESTED = (
    "VoChongNhanNuoi_Me", "VoChongNhanNuoi_Cha", "NguoiDonThanNhanNuoi", "MeNuoi", "ChaNuoi",
    "hienSongTai_OngBa", "hienSongTai_CSNuoiDuong",
)

# I. Người yêu cầu (cổng đổ sẵn từ tài khoản, còn trống mới hỏi): họ tên, giấy tờ tùy thân, nơi cư trú. II. Con nuôi:
# nhân thân, nơi cư trú, nơi sinh, đối tượng; trường hợp nhận nuôi và nơi trẻ đang sống. III/IV. Mẹ / cha nuôi: họ
# tên, năm sinh, dân tộc, quốc tịch — chỉ ô của khối đang hiện mới được đếm, nên khai cả hai trường hợp.
# Ô cổng chấm đỏ khi bấm Xem trước vẫn được extension gộp thêm vào danh sách bắt buộc.
REQUIRED = (
    "HoVaTenC", "LoaiGiayToDinhDanhC", "SoDinhDanhC", "NgayCapDDC", "NoiCapDDC", "TT_TinhThanhC", "TT_PhuongXaC",
    "HoVaTenCN", "NgaySinhCN", "GioiTinhCN", "DanTocCN", "QuocTichCN", "NoiCuTruCN_TrongNuoc", "NoiSinhCN_TrongNuoc",
    "ncDoiTuong", "truongHopNhanNuoi", "ChonNguoiDonThanNhanNuoi", "hienSongTai",
    "HoVaTenM", "NgaySinhM", "VoChongNhanNuoi_Me#Dân tộc", "VoChongNhanNuoi_Me#Quốc tịch",
    "MeNuoi#Dân tộc", "MeNuoi#Quốc tịch",
    "HoVaTenCha", "NgaySinhCha", "VoChongNhanNuoi_Cha#Dân tộc", "VoChongNhanNuoi_Cha#Quốc tịch",
    "ChaNuoi#Dân tộc", "ChaNuoi#Quốc tịch",
)

# Ô tích Cha / Mẹ nuôi của trường hợp đơn thân nằm sau tiêu đề mục IV nhưng là lựa chọn chung; (27) nơi đăng ký trước
# đây, (28) giấy tờ nước ngoài, (29) bản sao là yêu cầu chung của hồ sơ → hỏi không kèm tên phần.
NO_SECTION = (
    "ChonNguoiDonThanNhanNuoi", "TenCQDKNhanChaMe", "TenQuocGiaDK", "GiayToCMThayDoiHT", "SoThayDoiHT",
    "NgayThangCapHT", "CQCapHT", "QuocGiaHT", "CapBanSao", "SoLuong",
)

# Ô "Ngày, tháng, năm sinh" của mẹ / cha nuôi là ô chữ ("Điền năm"): nhận đủ ngày, tháng-năm hoặc chỉ năm.
TEXT_DATES = ("NgaySinhM", "NgaySinhCha")
