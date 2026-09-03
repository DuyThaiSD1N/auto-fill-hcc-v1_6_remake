EXTRA_RULES = """
Đây là thủ tục "Chính sách hỗ trợ chi phí học tập cho học sinh, sinh viên" (Bắc Ninh, mã 1.014581).
Hồ sơ thường là MỘT PDF gộp nhiều giấy tờ: Đơn đề nghị (Mẫu 01), Giấy xác nhận cơ sở đào tạo (Mẫu 02),
Bằng tốt nghiệp THCS/THPT, Căn cước công dân, Đơn xin xác nhận ủy quyền nộp hồ sơ, Lời chứng chứng thực
chữ ký. Chỉ cần trích nhân thân của MỘT người: HỌC SINH/SINH VIÊN (HSSV) — chủ hồ sơ.

CÁCH XÁC ĐỊNH HSSV (chủ hồ sơ):
- Là người đứng đơn ở Mẫu 01 "ĐƠN ĐỀ NGHỊ HỖ TRỢ CHI PHÍ HỌC TẬP" (người làm đơn, ký cuối đơn).
- Là người trên Bằng tốt nghiệp THCS/THPT và người được xác nhận đang học ở Mẫu 02.
- Trong "Đơn xin xác nhận ủy quyền nộp hồ sơ trực tuyến": HSSV là "CON TÔI/CHÁU TÔI tên là ..." (người
  được nộp thay), KHÔNG phải "Tên tôi là ..." (người nộp thay).

LOẠI TRỪ TUYỆT ĐỐI (không đưa vào HocSinh_*):
- Người NỘP THAY: cha/mẹ/người giám hộ — trong Đơn ủy quyền là "Tên tôi là"/"tôi", dùng tài khoản VNeID
  của họ để nộp. Cổng tự điền người nộp từ VNeID nên KHÔNG cần trích.
- Cán bộ ký Lời chứng (người chứng thực/tiếp nhận), cán bộ Một cửa.

ƯU TIÊN NGUỒN cho HSSV: (1) thẻ CCCD có họ tên trùng HSSV → (2) Bằng tốt nghiệp / Mẫu 02 → (3) Mẫu 01
→ (4) Đơn ủy quyền (mục "con tôi/cháu tôi"). Ngày cấp và Nơi cấp phải đi theo ĐÚNG thẻ CCCD của HSSV,
không ghép chéo với CCCD người nộp thay.

- HocSinh_HoTen: VIẾT IN HOA.
- HocSinh_SoDinhDanh / HocSinh_NgaySinh / HocSinh_NgayCap / HocSinh_NoiCap: theo CCCD của HSSV.
- HocSinh_SoDienThoai: lấy "Số điện thoại liên hệ" trong Mẫu 01 (các giấy tờ khác thường không có).
- HocSinh_Email: đa số hồ sơ không có → bỏ trống, không bịa.
- HocSinh_ThuongTru: object {quocGia,tinh,xa,diaChi}. Dùng địa chỉ theo ĐỊA GIỚI MỚI trên Mẫu 01/Đơn ủy
  quyền (ví dụ tinh='Bắc Ninh', xa='Phường Bắc Giang'); KHÔNG dùng địa danh cũ trước sáp nhập ghi trên
  CCCD. diaChi là phần chi tiết nhất (số nhà, ngõ, tổ dân phố).

Chỉ trả JSON fields theo schema; KHÔNG trả tên field giao diện (doiTuongKhac...) và không giải thích.
""".strip()
