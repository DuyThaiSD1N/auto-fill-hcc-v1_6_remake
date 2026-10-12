"""Prompt rules đặc thù cho "Thông báo phát triển nguồn điện mặt trời mái nhà tự sản xuất, tự tiêu thụ" (1.115377)."""

EXTRA_RULES = """<critical_rules>
1. Chỉ trả field nguồn trong schema. KHÔNG trả field UI dạng data[...].
2. Nguồn chính là "THÔNG BÁO Phát triển nguồn điện mặt trời mái nhà tự sản xuất, tự tiêu thụ có đấu nối với
   hệ thống điện quốc gia tại cấp điện áp hạ áp" (Mẫu số 01 Phụ lục III, NĐ 243/2026/NĐ-CP), thường VIẾT TAY
   trên mẫu in sẵn. Chép phần viết tay; dòng in sẵn (vd "2. Vị trí lắp đặt: Trên mái nhà", "a) Kết cấu: Hệ
   khung, mái bê tông") thì chép phần sau dấu hai chấm.
3. KHÔNG bịa, KHÔNG tự bù chữ số. Chữ viết tay dễ nhầm 0/6, 1/7: chép đúng nét đọc được; không chắc thì bỏ field.
</critical_rules>

<nhieu_ban_thong_bao>
Hồ sơ có thể có HAI bản Thông báo Mẫu 01 (vd một bản đứng tên cá nhân, một bản đứng tên hộ kinh doanh / doanh
nghiệp). Chọn bản có NGÀY LẬP MUỘN NHẤT và lấy MỌI field TB_* từ CÙNG bản đó, không trộn hai bản.
</nhieu_ban_thong_bao>

<thong_bao>
- TB_Ten = dòng "a) Tên:" mục I.1. TB_TenCamKet = tên ở câu "Hộ …… cam kết" mục II. TB_NguoiKy = họ tên dưới
  chữ ký cuối văn bản. Ba chỗ này có thể giống nhau, vẫn trả đủ cả ba.
- TB_SoDinhDanh chỉ lấy ở dòng "Số định danh cá nhân/CCCD (đối với cá nhân)"; TB_MaSoDoanhNghiep chỉ lấy ở
  dòng "Mã số doanh nghiệp (đối với tổ chức)". Dòng nào bỏ trống thì bỏ field đó.
- TB_DiaChi: dòng "c) Địa chỉ" thường viết liền "số nhà đường – phường – thành phố" → tách vào object.
- TB_CongSuatPV / TB_LuuTru / TB_Inverter: chỉ phần số viết vào chỗ chấm, KHÔNG đổi đơn vị.
- TB_PhuongAn: bảng mục 5 có hai ô; dấu "x" nằm ở cột trái của dòng được chọn. Dòng "Đồng ý bán…" → "5.1",
  dòng "Không bán…" → "5.2".
</thong_bao>

<ban_ve>
Bản vẽ thiết kế/hoàn công (khung tên có "Chủ đầu tư/INVESTOR", "TÊN BẢN VẼ/DRAWING NAME", "GHI CHÚ"):
- BanVe_ChuDauTu = tên ở mục "Chủ đầu tư/INVESTOR". Tên công ty, địa chỉ, website, điện thoại ở khung tên là
  của ĐƠN VỊ THIẾT KẾ → KHÔNG dùng cho bất kỳ field nào.
- OCR khung tên hay tách nhãn và giá trị xa nhau: chủ đầu tư thường là tên hộ/cá nhân/doanh nghiệp đứng gần
  tên dự án và địa chỉ công trình, KHÔNG phải tên người vẽ/kiểm tra/giám đốc.
- BanVe_CongSuatPV / BanVe_LuuTru / BanVe_Inverter lấy ở phần GHI CHÚ hoặc sơ đồ nguyên lý.
</ban_ve>

<khong_dung>
Giấy tiếp nhận hồ sơ và hẹn trả kết quả, Phiếu kiểm soát quá trình giải quyết, Thông báo của UBND về việc lắp
đặt (văn bản trả kết quả), C/O, chứng nhận chất lượng thiết bị, Giấy chứng nhận quyền sử dụng đất: KHÔNG lấy
field nào từ các giấy này.
</khong_dung>

<reminder>Chỉ trả JSON field nguồn hợp lệ. Lấy mọi TB_* từ cùng một bản Thông báo; không bù chữ số; không lấy
thông tin đơn vị thiết kế làm chủ đầu tư.</reminder>"""
