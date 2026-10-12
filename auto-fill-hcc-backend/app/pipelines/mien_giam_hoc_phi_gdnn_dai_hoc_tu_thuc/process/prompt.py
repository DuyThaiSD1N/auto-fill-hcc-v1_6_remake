"""Prompt rules đặc thù cho "Đề nghị miễn, giảm học phí trong cơ sở GDNN, GDĐH tư thục…" (mã 1.014335)."""

EXTRA_RULES = """Thủ tục: ĐỀ NGHỊ MIỄN, GIẢM HỌC PHÍ trong cơ sở giáo dục nghề nghiệp, cơ sở giáo dục đại học tư thục và
thuộc tổ chức kinh tế, doanh nghiệp nhà nước (mã 1.014335, Nghị định 238/2025/NĐ-CP) — cổng DVC Bộ GD&ĐT. Đầu vào
thường gồm: Đơn đề nghị chi trả tiền miễn, giảm học phí (Phụ lục IV); Giấy xác nhận của trường (mẫu Phụ lục V và/hoặc
mẫu riêng của trường); Dự toán kinh phí cấp bù (Phụ lục VI); CCCD sinh viên (bản sao chứng thực); Giấy khai sinh;
Bằng tốt nghiệp; có thể có CCCD của cha/mẹ nộp thay và Giấy tiếp nhận hồ sơ và hẹn trả kết quả.

⚠⚠ HAI NGƯỜI KHÁC NHAU — KHÔNG TRỘN:
1) SINH VIÊN (SinhVien_*) = người được miễn, giảm học phí = CHỦ HỒ SƠ = người đứng tên Đơn PL IV ('Họ và tên',
   'Người làm đơn') và được trường xác nhận. Đây là NEO. Nhân thân lấy từ CCCD/Giấy khai sinh của CHÍNH người này.
2) NGƯỜI NỘP (NguoiNop_*) = người đăng nhập VNeID. Có khối <nguoi_nop_context> thì làm ĐÚNG theo khối đó (lấy từ
   thẻ CCCD được chỉ định, hoặc bỏ trống). Không có khối đó: CHỈ khi có CCCD mang tên KHÁC sinh viên (thường cha/mẹ)
   hoặc Giấy tiếp nhận hồ sơ ghi 'Cá nhân/Tổ chức/Doanh nghiệp' là người khác. Không có → bỏ trống NguoiNop_*.
TUYỆT ĐỐI KHÔNG lấy cha/mẹ trong Giấy khai sinh làm NguoiNop_* (chỉ ghi vào KhaiSinh_HoTenCha/Me).

ĐỊA CHỈ (object, tách tinh/huyen/xa/diaChi):
- SinhVien_ThuongTru = 'Nơi thường trú (ghi đầy đủ)' trên Đơn PL IV / 'Hộ khẩu thường trú' trên Giấy xác nhận
  (địa danh HIỆN HÀNH). SinhVien_ThuongTruCCCD = 'Nơi thường trú' IN TRÊN CCCD (có thể là địa danh cũ). Trả CẢ HAI
  nếu có.
- SinhVien_NoiSinh: ƯU TIÊN 'Nơi sinh' trên GIẤY KHAI SINH. Đơn PL IV hay ghi nhầm QUÊ QUÁN vào ô Nơi sinh → có Giấy
  khai sinh thì KHÔNG lấy theo Đơn. Nơi sinh là bệnh viện/trạm y tế không ghi phường/xã → diaChi=tên cơ sở, xa rỗng.

ĐƠN PL IV (Don_*) — chép GẦN NGUYÊN VĂN, KHÔNG bịa: Don_KinhGui (cơ sở giáo dục sau 'Kính gửi'), Don_Lop,
Don_NienKhoa ('Khóa', dạng năm '2024 - 2027'), Don_Khoa ('Khoa', tên khoa), Don_HoTenChaMe, Don_DoiTuong (nguyên
câu 'Thuộc đối tượng'), Don_NgayLam. Giấy xác nhận: Truong_Ten, GiayXacNhan_DoiTuong.
'Khóa thi' trên Bằng tốt nghiệp KHÔNG phải Don_NienKhoa.

CCCD bản sao chứng thực: ngày/số/cơ quan ở khối 'Chứng thực bản sao đúng với bản chính' là của VĂN PHÒNG CÔNG
CHỨNG/UBND chứng thực — KHÔNG lấy làm ngày cấp/nơi cấp CCCD. Ngày cấp CCCD ở mặt sau ('Ngày, tháng, năm').

⚠ DẤU CHẤM CHỖ TRỐNG ('……') trên mẫu đơn là ô trống → bỏ field, không lấy chuỗi dấu chấm.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
