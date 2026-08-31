"""Quy tắc bóc tách đặc thù thủ tục "Đăng ký thành lập công ty TNHH hai thành viên trở lên".

Chỉ chứa quy tắc TRÍCH FIELD riêng của thủ tục. KHÔNG lặp lại chuẩn hoá ngày/họ tên/tách địa chỉ —
những thứ đó đã nằm ở QUY TẮC CHUNG của shared compact_agent.
"""

EXTRA_RULES = """
<nguon_giay_to>
Hồ sơ thành lập công ty TNHH hai thành viên trở lên gồm nhiều loại giấy. Thứ tự ưu tiên khi các
giấy lệch nhau:
1. GIẤY ĐỀ NGHỊ ĐĂNG KÝ DOANH NGHIỆP (mẫu theo Nghị định 168/2025/NĐ-CP) là NGUỒN SỐ 1 cho: tên công
   ty, địa chỉ trụ sở, ngành nghề, vốn điều lệ, nguồn vốn, người đại diện theo pháp luật, thuế.
2. DANH SÁCH THÀNH VIÊN là NGUỒN SỐ 1 của ThanhVien_DanhSach (nhân thân, phần vốn góp, tỷ lệ, thời
   hạn góp vốn, địa chỉ liên lạc của từng thành viên).
3. ĐIỀU LỆ CÔNG TY là nguồn của bảng tài sản góp vốn (Điều "Bảng vốn góp") và quyền hạn người đại
   diện theo pháp luật; cũng là nguồn BÙ cho tên công ty, trụ sở, ngành nghề, vốn điều lệ.
4. DANH SÁCH CHỦ SỞ HỮU HƯỞNG LỢI CỦA DOANH NGHIỆP là nguồn ĐỐI CHIẾU nhân thân thành viên (họ tên,
   giới tính, ngày sinh, số định danh, địa chỉ liên lạc) — dùng để bù ô mà Danh sách thành viên mờ.
5. CCCD/CĂN CƯỚC là nguồn nhân thân chuẩn; luôn liệt kê đủ vào Cccd_DanhSach.
6. GIẤY ỦY QUYỀN là nguồn của vai trò + nhân thân NGƯỜI NỘP HỒ SƠ (bên ĐƯỢC ủy quyền).
❌ KHÔNG lấy số liệu của MỘT thành viên làm số liệu của CÔNG TY. Von_DieuLe, Von_NguonVon,
   Von_TaiSanGopVon là TỔNG của công ty; phần góp của từng người thuộc ThanhVien_DanhSach.
</nguon_giay_to>

<ten_doanh_nghiep>
Tên công ty trên giấy gồm TIỀN TỐ LOẠI HÌNH + TÊN RIÊNG, vd "CÔNG TY TNHH DỊCH VỤ VẬN TẢI THƯƠNG
HUYỀN NHI". Cổng tách thành hai ô nên phải trả RIÊNG:
- DoanhNghiep_TenLoaiHinh = đúng cụm tiền tố ghi trên GĐN ("CÔNG TY TNHH" hoặc "CÔNG TY TRÁCH NHIỆM
  HỮU HẠN").
- DoanhNghiep_TenRieng   = phần CÒN LẠI sau khi bỏ tiền tố ("DỊCH VỤ VẬN TẢI THƯƠNG HUYỀN NHI").
❌ TUYỆT ĐỐI KHÔNG để lại tiền tố trong DoanhNghiep_TenRieng — cổng sẽ ghép thành "CÔNG TY TNHH
   CÔNG TY TNHH ...".
⚠ Tiêu đề ĐIỀU LỆ đôi khi ghi nhầm "CÔNG TY TNHH MTV"/"MỘT THÀNH VIÊN" trong khi nội dung có HAI
   thành viên góp vốn. Bám NỘI DUNG THỰC TẾ (Danh sách thành viên + bảng vốn góp) và GĐN, KHÔNG bám
   lỗi đánh máy ở tiêu đề.
</ten_doanh_nghiep>

<bang_lap>
Hai field dạng bảng của công ty (Von_NguonVon, Von_TaiSanGopVon) đều là array.
- `loai` PHẢI dùng ĐÚNG mã đã liệt kê trong mô tả field (vd "tu_nhan", "dong_vn"), KHÔNG trả nhãn
  tiếng Việt nguyên văn. Không nhận ra dòng thuộc loại nào thì BỎ dòng đó.
- BỎ HẲN dòng "Tổng số"/"Tổng cộng": cổng tự cộng và ô tổng bị disabled, trả về chỉ gây nhiễu.
- Dòng có số 0 hoặc bỏ trống thì BỎ luôn dòng, đừng trả 0 — form đã mặc định 0.
- Mọi số trả dạng SỐ THUẦN, không kèm "đồng"/"%"/dấu phân cách nghìn.
</bang_lap>

<thanh_vien>
ThanhVien_DanhSach là array, MỖI THÀNH VIÊN MỘT OBJECT, giữ ĐÚNG thứ tự dòng in trên Danh sách
thành viên (cổng nhập lần lượt từng thành viên một).
- vonGop = phần vốn góp của RIÊNG thành viên đó (VNĐ, số thuần); tyLeSoHuu = tỷ lệ % của riêng người
  đó. Tổng vonGop của các thành viên phải bằng Von_DieuLe — lệch thì đọc lại, đừng tự cân.
- Thời hạn góp vốn ghi dạng "trong vòng 90 ngày kể từ ngày cấp Giấy chứng nhận ĐKDN" → trả
  soNgayGopVon=90 và BỎ ngayGopVonCuThe. Chỉ khi hồ sơ ấn định một NGÀY cụ thể mới trả
  ngayGopVonCuThe (dd/mm/yyyy) và bỏ soNgayGopVon.
- quocTich mặc định đọc từ giấy ("Việt Nam"); danToc đọc từ CCCD/Danh sách thành viên ("Kinh").
- diaChiLienLac lấy cột "Địa chỉ liên lạc" của Danh sách thành viên; không có thì lấy "Nơi thường
  trú" trên CCCD của đúng người đó.
- ghiChu chỉ trả khi cột "Ghi chú" của Danh sách thành viên có chữ; cột "Ghi chú" của Danh sách chủ
  sở hữu hưởng lợi (vd "Trực tiếp") KHÔNG thuộc field này.
❌ KHÔNG gộp hai thành viên thành một object, KHÔNG chia đôi số liệu, KHÔNG suy tỷ lệ khi giấy không
   ghi.
</thanh_vien>

<nguoi_dai_dien_phap_luat>
- Người đại diện theo pháp luật đọc ở GĐN mục 8 và Điều lệ; người này THƯỜNG đồng thời là một trong
  các thành viên góp vốn — vẫn phải trả RIÊNG bộ field NguoiDaiDien_*, không để mapper tự suy.
- NguoiDaiDien_QuyenHan: trả nguyên văn đoạn mô tả quyền hạn/chức danh trong Điều lệ. Không có đoạn
  nào mô tả thì BỎ field.
- Điện thoại/Email của người đại diện lấy ở GĐN mục 9.1 (thông tin về Giám đốc/Tổng giám đốc) khi
  mục 8 không ghi.
</nguoi_dai_dien_phap_luat>

<dia_chi_va_khu_vuc>
- TruSo_DiaChi: đọc GĐN mục 3. Biểu mẫu chỉ có XÃ và TỈNH nên BỎ cấp huyện/quận.
- TruSo_KhuVuc: CHỈ trả khu vực có ô ĐƯỢC TÍCH ở mục 3. Không tích ô nào → BỎ field. Tích nhầm làm
  đổi cơ quan tiếp nhận hồ sơ (khu công nghệ cao phải nộp tới Ban quản lý).
</dia_chi_va_khu_vuc>

<thue>
- Thue_DiaChiNhanThongBao: CHỈ trả khi GĐN mục 9.3 kê khai địa chỉ KHÁC trụ sở chính. Mục 9.3 để
  trống (hoặc ghi "như trụ sở chính") → BỎ field; mapper sẽ chọn "Giống địa chỉ trụ sở chính".
- Thue_NamTaiChinh: trả object các SỐ. "Áp dụng từ ngày 01/01 đến ngày 31/12" →
  {"ngayBatDau":1,"thangBatDau":1,"ngayKetThuc":31,"thangKetThuc":12}.
- Thue_PhuongPhapGTGT: mục 9.9 chỉ được tích ĐÚNG MỘT ô. Không ô nào tích → BỎ field.
- Thue_NgayBatDauHoatDong: mục 9.4. Hồ sơ ghi "hoạt động ngay từ ngày được cấp GCN" → BỎ field.
</thue>

<nguoi_nop_ho_so>
- NguoiNop_VaiTro: hồ sơ CÓ Giấy ủy quyền và người đi nộp là bên ĐƯỢC ủy quyền → "Người được ủy
  quyền". Người đại diện theo pháp luật tự ký, không có giấy ủy quyền → "Người có thẩm quyền ký".
  Không rõ → BỎ field (mapper giữ mặc định của cổng là người có thẩm quyền ký).
- Người nộp hồ sơ có thể là người THỨ BA, không phải thành viên cũng không phải người đại diện theo
  pháp luật. Lấy đúng nhân thân của BÊN ĐƯỢC ỦY QUYỀN trong Giấy ủy quyền, không lấy nhầm bên ủy quyền.
- Cccd_DanhSach: liệt kê MỌI thẻ trong hồ sơ, KHÔNG suy vai trò theo thứ tự file. Extension sẽ đối
  chiếu với tài khoản ĐKKD đang đăng nhập để chọn đúng thẻ của người thật sự đang nộp.
</nguoi_nop_ho_so>

<output>
Chỉ trả một JSON object: {"fields":{"<field_hop_le>": <value>}}. Chỉ dùng field trong danh sách FIELD
ĐƯỢC PHÉP TRẢ; field không đủ căn cứ thì BỎ HẲN, không trả chuỗi rỗng/0/null; không bịa; không trả
giải thích sau JSON.
⚠ Trả JSON NÉN: KHÔNG xuống dòng, KHÔNG thụt lề, không thêm khoảng trắng thừa giữa các khoá. Hồ sơ
loại này dài nên JSON có thụt lề sẽ bị cắt giữa chừng và HỎNG TOÀN BỘ lượt trích.
</output>
""".strip()
