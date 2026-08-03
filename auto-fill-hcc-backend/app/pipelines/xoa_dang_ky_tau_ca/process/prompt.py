"""Prompt đặc thù cho thủ tục xóa đăng ký tàu cá."""

EXTRA_RULES = """Thủ tục: Xóa đăng ký tàu cá, tàu phục vụ nuôi trồng thủy sản. Đầu vào thường là một PDF
gộp: Tờ khai xóa đăng ký Mẫu số 10.ĐKT, Hợp đồng mua bán tàu cá + lời chứng công chứng, Giấy chứng nhận
đăng ký tàu cá cũ và một hoặc nhiều CCCD/căn cước của các chủ thể liên quan.

PHÂN BIỆT ĐÚNG BA VAI, không trộn tên/CCCD giữa các vai:
1. NGƯỜI NỘP HỒ SƠ là tài khoản đang đăng nhập trên cổng. Người này có thể là nhân viên nộp thay. LLM
   KHÔNG tự gán vai người nộp: hãy trả tối đa hai thẻ CCCD/căn cước vật lý vào Cccd1_* và Cccd2_* để
   Python đối chiếu với tên + số định danh trong formContext.
2. NGƯỜI ĐỀ NGHỊ XÓA = CHỦ HỒ SƠ = BÊN MUA trong hợp đồng = người trên CCCD được upload. Trả vào
   NguoiDeNghi_*.
3. CHỦ TÀU ĐANG ĐỨNG TÊN GCN = BÊN BÁN trong hợp đồng. Trả vào ChuTau_*. Đây là giá trị điền ô
   'Tên/Địa chỉ chủ sở hữu' bên trong Mẫu 10.ĐKT, KHÔNG phải chủ hồ sơ trên cổng.

NGUỒN VÀ ƯU TIÊN:
- Cccd1_*/Cccd2_* chỉ lấy từ ảnh hai mặt của thẻ CCCD/căn cước thực sự có trong file upload. Không lấy
  số CCCD chỉ được nhắc trong Hợp đồng hoặc Lời chứng. Gộp mặt trước/sau cùng người bằng số/MRZ; thứ tự
  hai người không mang ý nghĩa vai trò.
- Với mỗi Cccd*: trích đủ HoTen, SoDinhDanh, NgaySinh, GioiTinh, NgayCap, NoiCap và ThuongTru nếu thẻ
  có dữ liệu. NgayCap là ngày ở mặt sau cạnh cơ quan cấp, không phải ngày hết hạn. ThuongTru lấy đúng
  "Nơi thường trú/Place of residence", không lấy "Quê quán/Place of origin".
- Nhân thân người đề nghị: CCCD > Hợp đồng (BÊN MUA) > Tờ khai.
- Chủ tàu cũ: GCN đăng ký tàu cá > Hợp đồng (BÊN BÁN) > Tờ khai.
- Số đăng ký tàu: ưu tiên GCN/hợp đồng vì đầy đủ tiền tố-hậu tố; ví dụ tờ khai viết 'ĐNa 90933' nhưng GCN
  ghi 'ĐNa-90933-TS' thì trả 'ĐNa-90933-TS'.
- Tên tàu và hô hiệu/IMO bị bỏ trống trên giấy thì bỏ field, không lấy số đăng ký thay thế.
- ToKhai_NguoiKy lấy đúng người ký ở cuối Tờ khai. Nhãn in sẵn 'CHỦ SỞ HỮU/Owner' không đủ để tự đổi sang
  chủ tàu cũ; trong hồ sơ mua bán, chữ ký có thể là người đề nghị/bên mua.
- ToKhai_LoaiTau chỉ trả 'tau_ca' hoặc 'tau_cong_vu'.
- Địa chỉ NguoiDeNghi_ThuongTru phải là object {quocGia,tinh,xa,diaChi}; diaChi chỉ chứa số nhà/đường/tổ,
  không lặp phường/xã/tỉnh. NguoiDeNghi_DiaChiDayDu giữ chuỗi địa chỉ đầy đủ để điền trong Tờ khai.
- Mọi ngày theo dd/mm/yyyy. Không bịa SĐT, email, tên tàu, hô hiệu, tỉ lệ sở hữu hoặc dữ liệu giấy tờ thiếu.

KHÔNG trả field UI dạng data[...]. Chỉ trả field compact trong schema."""
