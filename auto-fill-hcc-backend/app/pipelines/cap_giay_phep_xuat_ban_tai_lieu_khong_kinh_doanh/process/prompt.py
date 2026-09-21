EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ có BA thực thể, tách TUYỆT ĐỐI, không được trộn thuộc tính:
   - NGƯỜI NỘP (NguoiNop_*): cá nhân đi nộp, nguồn là CCCD của chính người đó.
   - TỔ CHỨC ĐỀ NGHỊ cấp giấy phép xuất bản (ToChucDeNghi_*): mục 1-2 Đơn Mẫu 04.
   - CƠ SỞ IN (CoSoIn_*): nhà in sẽ in tài liệu, nguồn là Giấy chứng nhận đăng ký doanh nghiệp và
     Giấy phép hoạt động in.
2. ⚑ BẪY LỚN NHẤT: hồ sơ luôn có GCN đăng ký doanh nghiệp, nhưng đó là của CƠ SỞ IN, KHÔNG phải của
   tổ chức đề nghị. Mã số thuế, tên công ty, địa chỉ trụ sở, người đại diện pháp luật trên GCN đó
   chỉ được đưa vào CoSoIn_*. TUYỆT ĐỐI không dùng để điền ToChucDeNghi_*.
3. Tổ chức đề nghị thường là cơ quan nhà nước, đơn vị quân đội/công an, hội, trường học — loại này
   KHÔNG có mã số doanh nghiệp. Khi đó ToChucDeNghi_SoGcnDangKyKinhDoanh, _SoQuyetDinhThanhLap,
   _SoGiayPhepHoatDong, _CoQuanCapGiayTo, _NgayCapGiayTo đều BỎ FIELD — thà thiếu còn hơn điền số
   của nhà in vào.
4. "Giấy phép hoạt động in" là giấy của CƠ SỞ IN do Sở VHTTDL cấp. Nó KHÔNG phải
   ToChucDeNghi_SoGiayPhepHoatDong (field đó chỉ dành cho tổ chức NƯỚC NGOÀI đứng đơn).
5. Người ký Đơn Mẫu 04 là người đại diện của tổ chức đề nghị; người đứng đầu cơ sở in là người khác.
   Không lấy người này thay cho người kia, cũng không mặc định người nộp là một trong hai.
</source_and_role_rules>

<don_mau_04_rules>
6. Đơn Mẫu 04 (Danh mục 3, Phụ lục Nghị định 138/2025/NĐ-CP) có các mục đánh số: 1 tên tổ chức đề
   nghị · 2 địa chỉ, điện thoại · 3 tên tài liệu · 4 xuất xứ, người dịch · 5 hình thức · 6 số trang,
   phụ bản · 7 khuôn khổ, số lượng in · 8 tên và địa chỉ cơ sở in · 9 mục đích xuất bản · 12 nội dung
   tóm tắt · 13 kèm theo đơn. Lấy đúng theo số mục, không đoán theo vị trí dòng.
7. Mục 4 (xuất xứ, người dịch) CHỈ áp dụng cho tài liệu dịch từ tiếng nước ngoài. Tài liệu tiếng Việt
   thì hai field đó BỎ HẲN — đơn để trống là chuyện bình thường, không được suy ra từ nơi in.
8. TaiLieu_TomTatNoiDung và TaiLieu_MucDichXuatBan chép NGUYÊN VĂN câu chữ trong đơn, không tóm tắt
   lại, không viết thay bằng lời của bạn.
</don_mau_04_rules>

<ban_thao_rules>
9. Bản thảo tài liệu là nguồn ĐỐI CHIẾU cho tên tài liệu, hình thức, số trang, khuôn khổ, số lượng
   in, ngôn ngữ. Khi bản thảo và đơn lệch nhau thì LẤY THEO ĐƠN (đơn là văn bản đề nghị chính thức).
10. Dòng "Chịu trách nhiệm xuất bản/Giấy phép xuất bản số …" trên bản thảo là thông tin của giấy phép
    CŨ hoặc dự kiến — không dùng làm số giấy tờ của tổ chức đề nghị.
</ban_thao_rules>

<missing_and_normalization_rules>
11. Chỉ trả ngày khi có ĐỦ ngày-tháng-năm. Chỉ có năm thì bỏ field; TUYỆT ĐỐI không bịa 01/01.
12. Địa chỉ trả về object {quocGia, tinh, xa, diaChi}. Chuỗi viết liền "<số nhà, đường>, <phường>,
    <tỉnh>": lấy cụm CUỐI làm tinh, cụm ngay TRƯỚC làm xa, phần còn lại cho vào diaChi.
13. Số điện thoại/mã số thuế/số định danh chỉ giữ chữ số (mã số thuế có thể có đuôi -001).
14. Giấy tờ không ghi thì BỎ FIELD. Không suy diễn, không lấy giá trị của giấy tờ khác thay thế.
</missing_and_normalization_rules>
""".strip()
