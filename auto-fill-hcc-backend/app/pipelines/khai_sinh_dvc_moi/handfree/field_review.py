"""Bổ sung ô còn trống trên form SurveyJS đăng ký khai sinh (dichvucong.gov.vn/nop-ho-so).

Ô bắt buộc lấy theo chính cổng (isRequired / dấu "*" ở nhãn). Khối người nộp cổng khóa theo tài khoản nên không hỏi.
Chọn Nơi sinh / Quê quán / Nơi cư trú của mẹ, cha xong thì ô Tỉnh / Xã / Địa chỉ hiện ra và được hỏi tiếp ở lượt sau.
Mọi ô ngày là ô lịch (flatpickr) nên chỉ nhận đủ ngày.
"""

PROCEDURE_KEYS = ("khai-sinh-dang-ky-thuong",)

REQUIRED = ()

# Kính gửi / Tại (engine dựng theo cơ quan đã chọn hoặc tài khoản quầy), Ngày / Tháng / Năm lập tờ khai và ngày sinh
# ghi bằng chữ (cổng tự điền theo ngày sinh).
NO_ASK = ("citizenField57", "citizenField29", "citizenField50", "citizenField31", "citizenField32",
          "citizenNgaythangnamsinhbangchu_NgdcKS")

# Bộ ba họ tên + số định danh + ngày sinh của mẹ và của cha cùng tên ô với khối tra cứu CSDL dân cư của khai tử:
# điền xong chờ cổng tra rồi mới tìm ô trống kế tiếp, kẻo hỏi đúng quốc tịch / dân tộc cổng sắp tự đổ.
LOOKUP = ("citizenNDK_HoVaTen", "citizenNDK_SoDinhDanh", "citizenNDK_NgaySinh",
          "citizenNDK_HoVaTenCha", "citizenNDK_SoDinhDanhCha", "citizenNDK_NgaySinhCha")
