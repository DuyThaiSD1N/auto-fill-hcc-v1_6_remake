"""Prompt rules đặc thù cho "Đăng ký, cấp GCN cho người nhận chuyển nhượng trong dự án bất động sản" (cổng DVC
Đà Nẵng — Form.io, 1.012787)."""

EXTRA_RULES = """Thủ tục: Đăng ký, cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất cho
NGƯỜI NHẬN CHUYỂN NHƯỢNG quyền sử dụng đất, quyền sở hữu nhà ở, công trình xây dựng trong DỰ ÁN BẤT ĐỘNG SẢN.
Bộ hồ sơ thường gồm: Đơn đăng ký biến động Mẫu số 18 (có thể HAI bản), Hợp đồng mua bán nhà ở / chuyển nhượng
(bên bán = CHỦ ĐẦU TƯ dự án, bên mua = người nhận), các Văn bản sửa đổi bổ sung hợp đồng, Biên bản bàn giao
(+ biên bản điều chỉnh), Giấy chứng nhận đã cấp cho chủ đầu tư, hóa đơn GTGT, giấy nộp tiền NSNN, tờ khai lệ
phí trước bạ, tờ khai thuế sử dụng đất phi nông nghiệp, Giấy xác nhận thông tin cư trú CT07, Giấy chứng nhận
kết hôn, Giấy chứng nhận đăng ký doanh nghiệp của chủ đầu tư; có thể có CCCD, Hợp đồng ủy quyền.

HAI vai — tách RIÊNG:
- CHỦ HỒ SƠ (ChuHoSo_*) = BÊN NHẬN chuyển nhượng / BÊN MUA. Thường là CÁ NHÂN; có thể là TỔ CHỨC.
- NGƯỜI NỘP (NguoiNop_*) = một CÁ NHÂN trực tiếp nộp hồ sơ. CHỈ điền NguoiNop_* khi:
  (1) Có HỢP ĐỒNG/GIẤY ỦY QUYỀN ghi rõ BÊN ĐƯỢC ỦY QUYỀN KÈM SỐ CCCD → NguoiNop = bên được ủy quyền, lấy TRỌN
      nhân thân từ chính giấy ủy quyền/CCCD của người đó.
  (2) Chủ hồ sơ là CÁ NHÂN tự nộp (không ủy quyền) → NguoiNop_* = nhân thân của CHÍNH chủ hồ sơ.
  Chủ hồ sơ là TỔ CHỨC mà KHÔNG có giấy ủy quyền kèm CCCD người đi nộp → ĐỂ TRỐNG toàn bộ NguoiNop_*.

⚠⚠ CHỦ ĐẦU TƯ (bên bán, công ty bất động sản, đứng tên Giấy chứng nhận đã cấp cho chủ đầu tư, Giấy chứng nhận
đăng ký doanh nghiệp) KHÔNG phải chủ hồ sơ, KHÔNG phải người nộp: không lấy tên, mã số doanh nghiệp, địa chỉ,
điện thoại, email, người đại diện (Giám đốc) của công ty này cho ChuHoSo_* / NguoiNop_*. Ghi tên công ty vào
ChuDauTu_Ten.
⚠⚠ ĐƠN MẪU 18 CÓ THỂ CÓ HAI BẢN: bản do CHỦ ĐẦU TƯ ký (mục 1 là công ty, "Đại diện bởi", nội dung kiểu "Thu
hồi và cấp lại cho …") và bản do BÊN NHẬN ký (mục 1 là người mua, "Người viết đơn"). CHỈ lấy thông tin chủ hồ
sơ từ bản do BÊN NHẬN ký; bản của chủ đầu tư bỏ qua.
⚠ VỢ CHỒNG cùng nhận ("Ông … – Bà …", "Cùng vợ là", mục 1a và 1e của Đơn): form chỉ có MỘT chủ hồ sơ →
ChuHoSo_* và NguoiNop_* = người đứng tên ĐẦU TIÊN (thường là người ký Hợp đồng mua bán). TUYỆT ĐỐI KHÔNG ghép
tên người này với CCCD / ngày sinh / ngày cấp của người kia.

NGUỒN ƯU TIÊN cho nhân thân chủ hồ sơ / người nộp tự nộp: (1) CCCD → (2) Giấy xác nhận thông tin cư trú CT07 →
(3) Giấy chứng nhận kết hôn (chỉ họ tên, ngày sinh) → (4) Đơn Mẫu 18 bản bên nhận → (5) Hợp đồng mua bán, Văn
bản sửa đổi bổ sung, Biên bản bàn giao, tờ khai thuế, tờ khai lệ phí trước bạ, hóa đơn.
- Ngày sinh: CCCD / CT07 "Ngày, tháng, năm sinh" / Giấy kết hôn. Chỉ có năm sinh → bỏ.
- Giới tính: CCCD / CT07 "Giới tính". Không có → bỏ (hệ thống tự suy từ số định danh).
- Ngày cấp + nơi cấp CCCD: CCCD / Hợp đồng mua bán ("… cấp ngày 01/02/2023 tại Cục Cảnh sát quản lý hành chính
  về trật tự xã hội") / tờ khai thuế SDĐPNN phần II ô [31] (ngày cấp), [32] (nơi cấp). ⚠ Phần I ô [08] "Ngày
  cấp" / [09] "Nơi cấp" của tờ khai thuế hay bị ghi ĐẢO (ô ngày cấp chứa số CCCD) → KHÔNG dùng phần I.
- Giấy kết hôn cũ ghi số CMND 9 số và địa chỉ cũ → KHÔNG dùng cho số định danh / địa chỉ.

ĐỊA CHỈ (ChuHoSo_DiaChi / NguoiNop_DiaChi): object {quocGia,tinh,xa,diaChi}; tinh='Tỉnh/Thành phố …', xa=
phường/xã, diaChi số nhà/đường/tổ/thôn (KHÔNG kèm phường/xã/tỉnh). Lấy NƠI THƯỜNG TRÚ HIỆN HÀNH (sau sắp xếp
đơn vị hành chính, không còn cấp quận/huyện) theo CCCD → CT07 → Đơn Mẫu 18 bản bên nhận mục 1c. Giấy tờ cũ
(hợp đồng, biên bản, hóa đơn năm trước) ghi địa chỉ có quận/huyện cũ → KHÔNG dùng khi đã có địa chỉ mới.
KHÔNG lấy "Nơi ở hiện tại", "Địa chỉ liên hệ", "Địa chỉ nhận thông báo thuế".

LIÊN HỆ: ChuHoSo_DienThoai / ChuHoSo_Email lấy ở Đơn Mẫu 18 bản bên nhận mục 1d hoặc "Bên mua" trên Hợp
đồng. Số điện thoại chép đúng như giấy tờ, kể cả số quốc tế (00…). KHÔNG lấy SĐT/email của chủ đầu tư.

⚠ NguoiNop_NoiCap: chỉ điền khi giấy tờ GHI RÕ nơi cấp; không ghi → BỎ TRỐNG, không điền mặc định.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
