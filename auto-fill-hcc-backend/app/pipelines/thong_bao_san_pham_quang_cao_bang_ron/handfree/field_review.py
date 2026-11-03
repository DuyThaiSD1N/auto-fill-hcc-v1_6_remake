"""Bổ sung ô còn trống trên trang nộp thông báo sản phẩm quảng cáo trên bảng quảng cáo, băng-rôn (form liz, cổng Bộ
VHTTDL dichvucong.bvhttdl.gov.vn — content/liz/field-review.js)."""

PROCEDURE_KEYS = ("thong-bao-san-pham-quang-cao-bang-ron",)

# Cổng gắn dấu * cho ô bắt buộc (extension đọc thẳng); khối thông báo sản phẩm không ô nào có dấu * nhưng thiếu nội
# dung, địa điểm, thời gian, số lượng thì Sở không tiếp nhận → hỏi như ô bắt buộc. Tên = nhãn ô trên trang.
REQUIRED = ("Nội dung trên bảng quảng cáo, băng-rôn", "Địa điểm thực hiện", "Từ ngày thực hiện", "Đến ngày thực hiện",
            "Số lượng")

# Ô khung của trang (thuộc tính name): CCCD nhân viên tư vấn, ghi chú, 5 ô biên lai (nhập một thì phải đủ cả năm) không
# phải thông tin trên giấy tờ của công dân.
NO_ASK = ("cccd_tu_van", "description", "receipt_name", "receipt_id_card", "receipt_address", "receipt_phone",
          "receipt_email")
