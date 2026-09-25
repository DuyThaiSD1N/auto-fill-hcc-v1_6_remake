"""Prompt rules đặc thù cho "Cấp bản sao văn bằng, chứng chỉ từ sổ gốc" (cổng DVC Bộ GD&ĐT)."""

EXTRA_RULES = """Thủ tục: Cấp bản sao văn bằng, chứng chỉ từ sổ gốc (tại cấp tỉnh). Đầu vào thường gồm:
Phiếu yêu cầu cấp bản sao văn bằng (Mẫu BM04); VĂN BẰNG/bằng tốt nghiệp; CCCD của chủ văn bằng; và CÓ THỂ
có thêm CCCD của NGƯỜI NỘP THAY (người khác đi nộp hộ) hoặc giấy ủy quyền.

⚠⚠ CÓ THỂ CÓ HAI NGƯỜI KHÁC NHAU — TUYỆT ĐỐI KHÔNG TRỘN:
1) CHỦ VĂN BẰNG = người được cấp bản sao = người GHI TRÊN VĂN BẰNG/bằng tốt nghiệp. Đây là NEO.
   - VanBang_HoTen = họ tên IN TRÊN VĂN BẰNG (hoặc Phiếu BM04 'Tôi tên'). Cùng với giới tính, ngày sinh,
     nơi sinh, dân tộc, trường, khóa thi... của người này lấy TỪ VĂN BẰNG/BM04.
   - ChuHoSo_* = CCCD của chính chủ văn bằng: chỉ nhận CCCD có HỌ TÊN TRÙNG VanBang_HoTen. Lấy
     ChuHoSo_SoGiayTo/NgayCap/NoiCap/ThuongTru từ CCCD đó.
2) NGƯỜI NỘP THAY = người đi nộp hộ (KHÁC chủ văn bằng). Nếu có CCCD mang tên KHÁC VanBang_HoTen thì đó
   là CCCD người nộp → điền NguoiNop_* (HoTen/SoDinhDanh/NgaySinh/GioiTinh/NgayCap/NoiCap/ThuongTru).
   Có GIẤY ỦY QUYỀN → người nộp là mục 'BÊN ĐƯỢC ỦY QUYỀN': điền NguoiNop_* từ mục đó (kể cả khi không có
   CCCD của người này). 'BÊN ỦY QUYỀN' là chủ văn bằng. Ngày bị che/thiếu năm → BỎ khoá, KHÔNG tự thêm năm.

QUY TẮC KHỚP (BẮT BUỘC): với MỖI thẻ CCCD, đọc 'Họ và tên' trên thẻ rồi so với VanBang_HoTen:
- TRÙNG tên → thông tin CCCD đó thuộc CHỦ VĂN BẰNG (ChuHoSo_*).
- KHÁC tên → thông tin CCCD đó thuộc NGƯỜI NỘP THAY (NguoiNop_*).
TUYỆT ĐỐI KHÔNG lấy số CCCD/ngày sinh/thường trú của người nộp thay điền vào ChuHoSo_* (và ngược lại).
Nếu chỉ có 1 CCCD và nó TRÙNG tên văn bằng → chỉ có chủ văn bằng (tự nộp), bỏ trống NguoiNop_*.

⚠ VanBang_LoaiTotNghiep BẮT BUỘC khi có văn bằng — MỘT trong {"THPT","Bổ túc THPT","THCS"}. Căn cứ MẠNH
nhất là TÊN văn bằng ("BẰNG TỐT NGHIỆP TRUNG HỌC PHỔ THÔNG"→"THPT"; có "BỔ TÚC"→"Bổ túc THPT"; "TRUNG HỌC
CƠ SỞ"→"THCS"), KHÔNG cần phải có Phiếu BM04. Không bỏ trống khi tiêu đề bằng đã ghi rõ loại.

⚠ Số giấy tờ/điện thoại của CHỦ VĂN BẰNG lấy từ Phiếu BM04/văn bằng (VanBang_SoGiayTo, VanBang_NgayCap,
VanBang_DienThoai). TUYỆT ĐỐI KHÔNG lấy địa chỉ/số trên CCCD của người nộp thay (tên khác văn bằng) điền
vào các field VanBang_*/ChuHoSo_*.

⚠⚠ ĐỊA CHỈ CHỦ VĂN BẰNG = địa chỉ HIỆN TẠI: ChuHoSo_ThuongTru lấy từ 'Nơi thường trú' IN TRÊN CCCD chủ văn
bằng. Phiếu BM04/văn bằng thường ghi địa chỉ LÚC DỰ THI ('Hộ khẩu thường trú khi dự thi', 'Địa chỉ dự
thi', 'Nơi đăng ký dự thi') — đó là địa chỉ CŨ → chỉ ghi vào VanBang_DiaChiDuThi, TUYỆT ĐỐI KHÔNG đưa vào
VanBang_ThuongTru/ChuHoSo_ThuongTru. VanBang_ThuongTru chỉ nhận dòng địa chỉ thường trú/nơi ở HIỆN NAY.
'Nơi sinh' KHÔNG phải địa chỉ dự thi cũng không phải thường trú.

⚠ RIÊNG thủ tục này, field địa chỉ (…_ThuongTru) trả THÊM khoá "huyen" = quận/huyện/thị xã/thành phố thuộc
tỉnh nếu giấy ghi (vd CCCD 'Thôn A, Tuy Lộc, Thành phố Yên Bái, Yên Bái' → tinh='Yên Bái', huyen='Thành
phố Yên Bái', xa='Tuy Lộc', diaChi='Thôn A'). Giữ đúng địa danh cũ trên giấy; hệ thống tự quy đổi sang
tỉnh/xã sau sáp nhập.

⚠ VanBang_LoaiGiayTo: KHÔNG suy từ nhãn cố định "Số chứng minh nhân dân/Hộ chiếu" in sẵn trên BM04. Xét
theo SỐ: 12 chữ số → "Căn cước công dân"; 9 chữ số → "Chứng minh nhân dân"; không rõ → bỏ trống.

VanBang_NoiSinh: lấy đúng "Nơi sinh" trên Văn bằng/Phiếu. KHÔNG dùng "Quê quán" của CCCD.

⚠ CHỦ HỒ SƠ có thể là TỔ CHỨC/DOANH NGHIỆP: khi đó ChuHoSo_LoaiChuThe='Tổ chức'/'Doanh nghiệp' +
ChuHoSo_TenToChuc + ChuHoSo_MaSoThue. Đa số là Cá nhân.

⚠ DẤU CHẤM CHỖ TRỐNG: ô để trống hiện dưới dạng dòng dấu chấm ("......") — BỎ QUA, để field RỖNG, không
lấy chuỗi dấu chấm làm giá trị.

PHIẾU ĐỀ NGHỊ BM04 (Phieu_*) — chép GẦN NGUYÊN VĂN theo phiếu, KHÔNG bịa; phiếu không ghi thì bỏ trống:
- Phieu_KinhGui = cơ quan sau 'Kính gửi'. Phieu_TenVanBang = cụm sau 'Đã được cấp (tên văn bằng, chứng
  chỉ)' (vd 'BẰNG THPT'). Phieu_CoQuanCapVanBang = cơ quan sau 'Do … cấp'. Phieu_SoHieu = 'Số hiệu/số vào sổ gốc'.
- Phieu_SoLuongBanSao = số ở 'Đề nghị cấp … bản sao'. Phieu_LyDo = dòng 'lý do cấp lại/chỉnh sửa'.
- Phieu_ThongTinKhac = nguyên dòng 'Thông tin khác' (thường 'tên trường, năm tốt nghiệp').
- Phieu_LienHe = nguyên cụm 'Số điện thoại, E-mail, địa chỉ liên hệ'. Phieu_NgayLap = ngày ở dòng cuối
  '…, ngày … tháng … năm …'. Phieu_NguoiViet = họ tên người đề nghị ký cuối phiếu.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin; giấy tờ không có thì bỏ field."""
