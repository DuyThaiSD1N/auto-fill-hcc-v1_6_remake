"""Quy tắc bóc tách đặc thù thủ tục "Đăng ký thành lập công ty cổ phần".

Chỉ chứa quy tắc TRÍCH FIELD riêng của thủ tục. KHÔNG lặp lại chuẩn hoá ngày/họ tên/tách địa chỉ —
những thứ đó đã nằm ở QUY TẮC CHUNG của shared compact_agent.
"""

EXTRA_RULES = """
<nguon_giay_to>
Hồ sơ thành lập công ty cổ phần thường gồm nhiều loại giấy. Thứ tự ưu tiên khi các giấy lệch nhau:
1. MẪU 4-CP "Giấy đề nghị đăng ký doanh nghiệp (công ty cổ phần)" là NGUỒN SỐ 1 cho gần như mọi
   field: tên công ty, địa chỉ trụ sở, ngành nghề, vốn điều lệ, cổ phần, thuế, người nộp.
2. MẪU 7-DSCĐ "Danh sách cổ đông sáng lập" là nguồn của BẢNG TÀI SẢN GÓP VỐN (cột 15) và đối chiếu
   số lượng/giá trị cổ phần (cột 9, 10, 11). Mẫu 4-CP KHÔNG có bảng tài sản góp vốn.
3. QUYẾT ĐỊNH THÀNH LẬP và GCN ĐKDN là nguồn BÙ: chỉ dùng cho field mà Mẫu 4-CP bỏ trống hoặc OCR
   không đọc nổi.
4. CCCD/CĂN CƯỚC là nguồn nhân thân NGƯỜI NỘP HỒ SƠ; luôn liệt kê đủ vào Cccd_DanhSach.
5. GIẤY TIẾP NHẬN HỒ SƠ là nguồn của địa chỉ nhận kết quả và có thể bù họ tên/điện thoại người nộp.
❌ KHÔNG lấy số liệu của cổ đông cụ thể (Mẫu 7-DSCĐ từng dòng) làm số liệu của CÔNG TY. Các field
   vốn/cổ phần ở đây là TỔNG của công ty, đọc ở Mẫu 4-CP mục 5, 6, 7.
</nguon_giay_to>

<bang_lap>
Bốn field dạng bảng (Von_NguonVon, Von_TaiSanGopVon, CoPhan_DanhSach, CoPhan_ChaoBan) đều là array.
- `loai` PHẢI dùng ĐÚNG mã đã liệt kê trong mô tả field (vd "pho_thong", "uu_dai_bieu_quyet"), KHÔNG
  trả nhãn tiếng Việt nguyên văn. Không nhận ra dòng thuộc loại nào thì BỎ dòng đó.
- BỎ HẲN dòng "Tổng số"/"Tổng cộng": cổng tự cộng và ô tổng bị disabled, trả về chỉ gây nhiễu.
- Dòng có số 0 hoặc bỏ trống thì BỎ luôn dòng, đừng trả 0 — form đã mặc định 0.
- Mọi số trả dạng SỐ THUẦN, không kèm "đồng"/"%"/dấu phân cách nghìn.
</bang_lap>

<ten_doanh_nghiep>
Tên công ty trên giấy gồm TIỀN TỐ LOẠI HÌNH + TÊN RIÊNG, vd "CÔNG TY CỔ PHẦN QUẢN LÝ VẬN ĐỘNG VIÊN
TRẺ QUỐC GIA". Cổng tách thành hai ô nên phải trả RIÊNG:
- DoanhNghiep_TenLoaiHinh = đúng cụm tiền tố ghi trên giấy ("CÔNG TY CỔ PHẦN" hoặc "CÔNG TY CP").
- DoanhNghiep_TenRieng   = phần CÒN LẠI sau khi bỏ tiền tố ("QUẢN LÝ VẬN ĐỘNG VIÊN TRẺ QUỐC GIA").
❌ TUYỆT ĐỐI KHÔNG để lại tiền tố trong DoanhNghiep_TenRieng — cổng sẽ ghép thành "CÔNG TY CỔ PHẦN
   CÔNG TY CỔ PHẦN ...".
</ten_doanh_nghiep>

<dia_chi_va_khu_vuc>
- TruSo_DiaChi: đọc mục 3 Mẫu 4-CP. Biểu mẫu chỉ có XÃ và TỈNH nên BỎ cấp huyện/quận.
- TruSo_KhuVuc: CHỈ trả khu vực có ô ĐƯỢC TÍCH ở mục 3. Không tích ô nào → BỎ field. Tích nhầm làm
  đổi cơ quan tiếp nhận hồ sơ (khu công nghệ cao phải nộp tới Ban quản lý).
</dia_chi_va_khu_vuc>

<nguoi_dai_dien_phap_luat>
- Người đại diện theo pháp luật đọc ở Mẫu 4-CP mục 8, Điều lệ, và GCN ĐKDN mục "Người đại diện theo
  pháp luật của công ty" (khối này ghi đủ họ tên / giới tính / ngày sinh / số định danh / chức danh /
  địa chỉ liên lạc). Người này THƯỜNG đồng thời là một cổ đông sáng lập — vẫn phải trả RIÊNG bộ field
  NguoiDaiDien_*, không để mapper tự suy từ danh sách cổ đông.
- Công ty cổ phần được phép có NHIỀU người đại diện theo pháp luật. Hồ sơ ghi nhiều người thì trả
  người ĐỨNG ĐẦU danh sách (hoặc người được Điều lệ ghi là Giám đốc/Tổng giám đốc); KHÔNG gộp hai
  người thành một, KHÔNG trộn tên người này với số định danh người kia.
- NguoiDaiDien_QuyenHan: trả nguyên văn đoạn mô tả quyền hạn/chức danh trong Điều lệ. Không có đoạn
  nào mô tả thì BỎ field.
- Điện thoại/Email của người đại diện lấy ở Mẫu 4-CP mục 9.1 (thông tin về Giám đốc/Tổng giám đốc)
  khi mục 8 không ghi.
</nguoi_dai_dien_phap_luat>

<thue>
- Thue_DiaChiNhanThongBao: CHỈ trả khi mục 11.3 kê khai địa chỉ KHÁC trụ sở chính. Mục 11.3 để trống
  (hoặc ghi "như trụ sở chính") → BỎ field; mapper sẽ chọn ô "Giống địa chỉ trụ sở chính".
- Thue_NamTaiChinh: trả object các SỐ. "Áp dụng từ ngày 01/01 đến ngày 31/12" →
  {"ngayBatDau":1,"thangBatDau":1,"ngayKetThuc":31,"thangKetThuc":12}.
- Thue_PhuongPhapGTGT: mục 11.9 chỉ được tích ĐÚNG MỘT ô. Không ô nào tích → BỎ field.
- Thue_NgayBatDauHoatDong: mục 11.4. Hồ sơ ghi "hoạt động ngay từ ngày được cấp GCN" → BỎ field.
</thue>

<nguoi_nop_ho_so>
- NguoiNop_VaiTro: đọc phần ký cuối Mẫu 4-CP. Có kèm VĂN BẢN UỶ QUYỀN và người ký là người được uỷ
  quyền → "Người được ủy quyền". Người đại diện theo pháp luật / chủ tịch HĐQT tự ký → "Người có
  thẩm quyền ký". Không rõ → BỎ field (mapper giữ mặc định của cổng là người có thẩm quyền ký).
- Cccd_DanhSach: liệt kê MỌI thẻ trong hồ sơ, KHÔNG suy vai trò theo thứ tự file. Extension sẽ đối
  chiếu với tài khoản ĐKKD đang đăng nhập để chọn đúng thẻ của người thật sự đang nộp.
- NguoiNop_DiaChiNhanKetQua: CHỈ lấy từ Giấy tiếp nhận hồ sơ mục "Nơi nhận kết quả bản giấy". Không
  có giấy đó → BỎ field (mặc định là nhận trực tiếp, không qua bưu điện).
</nguoi_nop_ho_so>

<output>
Chỉ trả một JSON object: {"fields":{"<field_hop_le>": <value>}}. Chỉ dùng field trong danh sách FIELD
ĐƯỢC PHÉP TRẢ; field không đủ căn cứ thì BỎ HẲN, không trả chuỗi rỗng/0/null; không bịa; không trả
giải thích sau JSON.
</output>
""".strip()
