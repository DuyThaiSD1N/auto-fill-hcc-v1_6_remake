"""Prompt rules đặc thù cho "Thực hiện, điều chỉnh, thôi hưởng trợ cấp xã hội hàng tháng, hỗ trợ kinh
phí chăm sóc, nuôi dưỡng hàng tháng" (Form.io — cổng Bộ Y tế)."""

EXTRA_RULES = """Thủ tục: Thực hiện, điều chỉnh, thôi hưởng trợ cấp xã hội hàng tháng, hỗ trợ kinh phí
chăm sóc, nuôi dưỡng hàng tháng (theo Nghị định 20/2021/NĐ-CP). Đầu vào gồm: Tờ khai đề nghị trợ giúp xã
hội (Mẫu số 1a/1b/1c/1d/1đ) hoặc Tờ khai nhận chăm sóc, nuôi dưỡng (Mẫu 2a/2b/03), CCCD của đối tượng
và/hoặc người nộp, và có thể có: Giấy xác nhận khuyết tật, Biên bản giám định y khoa, Giấy khai sinh (đối
tượng là trẻ em), Giấy xác nhận cư trú, Giấy tờ xác nhận nhiễm HIV / đang mang thai.

CÓ THỂ CÓ 2 NGƯỜI — tách RIÊNG, KHÔNG lẫn:
- ĐỐI TƯỢNG hưởng trợ cấp (DoiTuong_*) = CHỦ HỒ SƠ = người khuyết tật / trẻ em / người cao tuổi / người
  đơn thân nghèo... đứng tên hồ sơ. Đây là đối tượng chính — trích toàn bộ nhân thân (họ tên/ngày sinh/
  giới tính/số định danh/ngày-nơi cấp/thường trú/điện thoại) của NGƯỜI NÀY.
  · Nếu đối tượng là TRẺ EM (Mẫu 1a trẻ dưới 3 tuổi/trẻ mồ côi, hoặc con của người đơn thân/NKT): trẻ
    KHÔNG có CCCD → lấy họ tên/ngày sinh/giới tính từ Giấy khai sinh; DoiTuong_SoDinhDanh để trống.
- NGƯỜI NỘP HỒ SƠ (NguoiNop_*) = NGƯỜI KHAI THAY được ghi trực tiếp trên tờ khai. Nhận diện bằng block
  "Thông tin người khai thay", thường gồm "Giấy CMND hoặc Căn cước công dân số", "Mối quan hệ với đối
  tượng", "Địa chỉ" và họ tên gần chữ ký. Khi block có GHI RÕ họ tên người khai thay thì BẮT BUỘC trả NguoiNop_HoTen
  và mọi NguoiNop_* đọc chắc chắn được trong chính block đó. Không có hoặc block để trống
  thì bỏ toàn bộ NguoiNop_*; mapper sẽ dùng đối tượng cho Phần I. Không sử dụng tên tài khoản/người làm
  thủ tục từ cổng.

NGUỒN DỮ LIỆU (NguoiNop_*):
- Ưu tiên đúng block "Thông tin người khai thay" trên Tờ khai. NguoiNop_ThuongTru lấy từ dòng "Địa chỉ"
  của block này, không lấy hộ khẩu/nơi ở của đối tượng.
- Nếu có CCCD/CMND riêng của người khai thay, chỉ dùng bổ sung field còn thiếu khi họ tên hoặc số giấy tờ
  khớp block người khai thay. Không coi mọi CCCD khác đối tượng là của người khai thay.
- NguoiNop_SoDinhDanh chỉ trả khi sau chuẩn hóa còn đúng 9 hoặc 12 chữ số. Số thừa/thiếu chữ số thì bỏ,
  tuyệt đối không tự xóa/chèn chữ số để đoán.
- Không lấy "Cá nhân/hộ gia đình đang trực tiếp chăm sóc, nuôi dưỡng", vợ/chồng/cha/mẹ/con được nhắc trong
  nội dung, người đỡ đầu, cán bộ tiếp nhận hoặc người ký xác nhận làm NguoiNop_*.
- Field không có trong block hoặc CCCD riêng khớp đúng người thì bỏ; không sao DoiTuong_* sang NguoiNop_*.

NGUỒN DỮ LIỆU (DoiTuong_*):
- Họ tên/ngày sinh/giới tính/số định danh/ngày cấp: ưu tiên CCCD của đối tượng; Tờ khai / Giấy xác nhận
  khuyết tật / Biên bản giám định y khoa / Giấy khai sinh bổ sung.
- Nơi cấp: CCCD gắn chip không in nhãn "Nơi cấp" riêng → lấy ở Tờ khai. Chuẩn hóa tên cơ quan.
- DoiTuong_ThuongTru (nơi thường trú/hộ khẩu): tách object {tinh,xa,diaChi}; ưu tiên Tờ khai (địa giới
  MỚI sau sáp nhập); diaChi CHỈ chi tiết (số nhà/đường/tổ dân phố/thôn), KHÔNG kèm phường/xã/huyện/tỉnh.
- DoiTuong_GhiChu: dạng tật + MỨC ĐỘ khuyết tật (vd "Khuyết tật vận động, mức độ Nặng") lấy ở Giấy xác
  nhận khuyết tật / Biên bản giám định / Tờ khai; hoặc diện đối tượng bảo trợ. Không có thì bỏ.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
