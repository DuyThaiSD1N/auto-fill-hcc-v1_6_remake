"""[Lào Cai] Đăng ký, cấp Giấy chứng nhận đối với thửa đất có DIỆN TÍCH TĂNG THÊM do thay đổi ranh
giới so với Giấy chứng nhận đã cấp — trường hợp thửa đất gốc ĐÃ có Giấy chứng nhận và phần diện tích
tăng thêm CHƯA ĐƯỢC CẤP Giấy chứng nhận (mã 1.115693).

Đây là thủ tục SONG SINH với 1.115694 (`dk_giay_cn_thua_dat_dien_tich_tang_them`): cùng một câu tiêu
đề cho tới chữ "…thửa đất gốc đã có Giấy chứng nhận,", chỉ khác vế cuối:

  • 1.115693 (thủ tục này): "phần diện tích đất tăng thêm CHƯA ĐƯỢC CẤP Giấy chứng nhận"
    → đất tăng thêm là đất người dân đang sử dụng ổn định, chưa ai được cấp giấy. Chứng minh bằng
      BIÊN BẢN LÀM VIỆC xác nhận ranh giới + ý kiến các hộ giáp ranh, không có hợp đồng mua bán.
  • 1.115694: "phần diện tích đất tăng thêm do NHẬN CHUYỂN QUYỀN sử dụng một phần thửa đất ĐÃ ĐƯỢC
    CẤP Giấy chứng nhận" → có hợp đồng chuyển nhượng + chứng từ thanh toán.

Hai vế cuối loại trừ nhau nên nhận diện bằng `textIncludes` thường là đủ (xem registry).
"""
