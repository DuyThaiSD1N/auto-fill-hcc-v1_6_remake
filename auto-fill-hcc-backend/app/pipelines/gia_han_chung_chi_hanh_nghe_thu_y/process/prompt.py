"""Prompt rules đặc thù cho "Gia hạn Chứng chỉ hành nghề thú y" (Form.io — Cổng DVC quốc gia)."""

EXTRA_RULES = """Thủ tục: Gia hạn Chứng chỉ hành nghề thú y (mã 2.001064). Đầu vào có thể gồm: Đơn đăng ký
gia hạn Chứng chỉ hành nghề thú y (Mẫu 02.HNTY — hồ sơ cũ có thể dùng mẫu 'ĐƠN ĐĂNG KÝ CẤP CHỨNG CHỈ
HÀNH NGHỀ THÚ Y', xử lý y như nhau), GIẤY KHÁM SỨC KHỎE, BẰNG TỐT NGHIỆP / văn bằng chuyên môn (thường là
bản sao chứng thực), bản chụp CHỨNG CHỈ HÀNH NGHỀ THÚ Y ĐÃ CẤP, CCCD của người đề nghị, có thể có thêm
CCCD của người nộp thay.

Form online có mục "Thông tin người nộp hồ sơ" (cổng tự đổ tài khoản đăng nhập, ta KHÔNG động vào) và
mục "Thông tin chủ hồ sơ" — chủ hồ sơ mới là người đứng đơn.
- NGƯỜI ĐỀ NGHỊ (NguoiDeNghi_*) = người đứng tên Đơn = người được gia hạn chứng chỉ = CHỦ HỒ SƠ trên
  form. Đây là người CHÍNH, trích ĐẦY ĐỦ nhân thân của họ, gồm cả giới tính và nơi cấp giấy tờ.
- NguoiNop_* CHỈ dùng khi có người KHÁC nộp thay VÀ hồ sơ có CCCD riêng của người nộp; điền để tách bạch,
  KHÔNG bao giờ dùng làm nhân thân người đề nghị. Tự nộp → bỏ trống. Xem khối <nguoi_nop_context> ở cuối
  (nếu có).

⚠ KHÔNG lấy nhân thân trên CCCD người nộp thay làm NguoiDeNghi_* — chứng chỉ cấp cho NGƯỜI ĐỨNG TÊN ĐƠN.

NGUỒN NHÂN THÂN (NguoiDeNghi_*), theo thứ tự ưu tiên: (1) CCCD; (2) Đơn (Tên tôi là, Ngày tháng năm
sinh, Địa chỉ thường trú, số điện thoại); (3) Giấy khám sức khỏe (Họ và tên, Giới tính, Sinh ngày, Số
CMND/CCCD/định danh + Cấp ngày + Tại, Chỗ ở hiện tại); (4) Bằng tốt nghiệp (chỉ họ tên, ngày sinh).
- Hồ sơ KHÔNG có CCCD → số định danh, ngày cấp, nơi cấp lấy từ dòng CCCD ghi tay trên Giấy khám sức khỏe.
- Bằng tốt nghiệp hay in họ tên không dấu / sai dấu → ưu tiên họ tên của CCCD / Đơn / Giấy khám sức khỏe.
- ThuongTru tách object {quocGia,tinh,xa,diaChi}; diaChi chỉ phần chi tiết (số nhà/đường/thôn/tổ). Địa
  chỉ chỉ ghi 'Phường X - Tỉnh Y' thì xa='Phường X', tinh='Tỉnh Y', diaChi=''. ⛔ KHÔNG lấy dòng 'Tại' hay
  'Địa chỉ hành nghề' trong Đơn làm nơi cư trú.
⚠ Trong Đơn, dòng "Ngày cấp" nằm NGAY SAU "Bằng cấp chuyên môn" là ngày cấp BẰNG, KHÔNG phải ngày cấp
CCCD.

NỘI DUNG ĐƠN (Don_*):
- Don_KinhGui = mục 'Kính gửi' chép nguyên văn.
- Don_LaNguoiNuocNgoai = 'Có' CHỈ khi giấy tờ thể hiện rõ quốc tịch nước ngoài / hộ chiếu nước ngoài;
  có CCCD Việt Nam → 'Không'.
- Don_BangCapChuyenMon = theo mục 'Bằng cấp chuyên môn' của Đơn (vd 'Cao đẳng'), KHÔNG kèm ngày/nơi cấp.
- Don_PhamViHanhNghe = dòng phạm vi hành nghề ĐƯỢC ĐÁNH DẤU (☑/x/✓) trong danh sách của Đơn. Chép
  NGUYÊN VĂN và ĐỦ ĐUÔI ('… cho động vật trên cạn' / '… cho động vật thủy sản'), vì hệ thống phải khớp
  đúng dòng để tự tích trên form. Nhiều dòng được tích thì ngăn cách bằng ';'. KHÔNG liệt kê dòng không
  được tích, KHÔNG rút gọn.
- Don_DiaDiem + Don_NgayLamDon = địa danh và ngày ở dòng '……, ngày … tháng … năm …' CUỐI ĐƠN (Giấy khám
  sức khỏe và văn bằng cũng có dòng này — KHÔNG lấy của chúng).
- Don_NguoiLamDon = họ tên người ký cuối đơn.

CHỨNG CHỈ HÀNH NGHỀ CŨ (CCHNCu_*): chỉ trích khi hồ sơ CÓ bản chụp chứng chỉ hành nghề thú y đã cấp hoặc
Đơn ghi lại. CCHNCu_SoDangKy = số đăng ký/số hiệu CHỨNG CHỈ; CCHNCu_NgayHetHan = dòng 'Chứng chỉ có giá
trị đến ngày …'. ⛔ 'Số hiệu' / 'Số vào sổ gốc' của BẰNG TỐT NGHIỆP và 'Số …/GKSK' của Giấy khám sức khỏe
KHÔNG phải số chứng chỉ. Hồ sơ không có chứng chỉ cũ thì BỎ TRỐNG cả hai — cán bộ sẽ nhập tay.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
