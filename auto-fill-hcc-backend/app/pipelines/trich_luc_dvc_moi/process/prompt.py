"""Quy tắc trích riêng của thủ tục cấp bản sao trích lục hộ tịch (Cổng DVC quốc gia mới)."""

EXTRA_RULES = """<ho_so>
Hồ sơ cấp bản sao trích lục hộ tịch / bản sao giấy khai sinh: tờ khai cấp bản sao (nếu có), giấy ủy quyền,
CCCD/CMND, và giấy hộ tịch đã đăng ký trước đây (giấy khai sinh / trích lục khai sinh, giấy chứng nhận
kết hôn / trích lục kết hôn, trích lục khai tử), đôi khi chỉ có giấy chứng sinh hoặc tờ khai cư trú CT01.
Khối người nộp trên cổng đã khóa theo tài khoản → KHÔNG trích người nộp.
</ho_so>

<phan_vai>
- Có khối <phan_vai_da_xac_dinh> phía dưới → người được cấp và loại trích lục theo đúng khối đó.
- Không có khối đó (dự phòng): người được cấp = người sau câu "cho người có tên dưới đây" trên tờ khai;
  không có tờ khai thì là người được đăng ký trên giấy hộ tịch chính (giấy khai sinh → con; khai tử →
  người chết; kết hôn → người chồng).
</phan_vai>

<nguoi_duoc_cap>
1. Thứ tự nguồn: khối người được cấp trên TỜ KHAI → giấy hộ tịch của chính người đó → CCCD/căn cước
   của chính người đó (chỉ bù ô còn thiếu). Số, ngày cấp, nơi cấp giấy tờ tùy thân đi NGUYÊN CỤM từ
   MỘT giấy tờ; người có cả căn cước 12 số lẫn CMND 9 số thì lấy cụm của thẻ 12 số.
2. GIẤY KHAI SINH: dòng "Giấy tờ tùy thân: ... số ... cấp ngày ..." là của NGƯỜI ĐI KHAI SINH (cha/mẹ/
   người thân) → KHÔNG đưa vào NguoiDuocCap_LoaiGiayTo/SoGiayTo/NgayCap/NoiCap. Giấy khai sinh chỉ có
   "Số định danh cá nhân" của trẻ → chỉ trả NguoiDuocCap_SoDinhDanh. Dòng này để trống → bỏ.
3. TRÍCH LỤC KHAI TỬ: người được cấp đã chết, không có thẻ trong hồ sơ; giấy tờ tùy thân của họ chỉ là
   dòng in trong block NGƯỜI CHẾT ("Giấy tờ tùy thân: ... số ..., ... cấp ngày ...") → lấy đủ cụm đó.
   KHÔNG lấy của người đi khai tử. Mọi CCCD kèm trích lục khai tử là của người khác.
4. GIẤY CHỨNG NHẬN KẾT HÔN: chỉ lấy cột của đúng người được cấp; giới tính theo vai (chồng = Nam,
   vợ = Nữ); không trộn cột vợ/chồng.
5. GIẤY CHỨNG SINH: họ tên ở "Dự định đặt tên con", ngày sinh trong "Đã sinh con ... ngày ...", giới tính
   ở "Giới tính của con"; không lấy thông tin của mẹ. CT01: người ở mục 1/2/3, không lấy chủ hộ.
6. Dân tộc giữ nguyên chữ trên giấy. "Mông" giữ "Mông"; chỉ biến thể có "H" đứng đầu (Hmông, H'Mông)
   mới trả "Mông (Hmông)".
7. NguoiDuocCap_NoiCuTru CHỈ lấy dòng thuộc CHÍNH người được cấp: khối người được cấp trên tờ khai, CCCD của
   chính họ, "Nơi cư trú cuối cùng" của người chết trên trích lục khai tử. Dòng "Nơi cư trú" trên GIẤY KHAI
   SINH nằm trong khối cha/mẹ → của cha/mẹ, KHÔNG lấy cho con. Không có dòng của chính họ → bỏ field.
   Dòng "Nơi cư trú" trong khối sau "cho người có tên dưới đây" của tờ khai LÀ của người được cấp: BẮT BUỘC
   trả, kể cả khi trùng từng chữ với nơi cư trú của người yêu cầu (cùng hộ là bình thường).
   Nơi cư trú tách {quocGia,tinh,xa,diaChi}: chuỗi "[chi tiết], [xã], [huyện], [tỉnh]" đếm từ cuối —
   cuối là tỉnh, áp cuối là cấp huyện (bỏ khỏi xa/diaChi, trả riêng ở khóa "huyen"), cụm trước huyện là xã,
   còn lại là diaChi. Tỉnh Hồ Chí Minh luôn trả "Thành phố Hồ Chí Minh".
8. NguoiDuocCap_NoiCap chép đúng cơ quan cấp ghi trên giấy. Chỉ đổi cách viết của CÙNG một cơ quan:
   "Cục CS QLHC về trật tự xã hội" / "Cục CSQLHC về TTXH" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội".
   CMND 9 số do Công an tỉnh cấp ("CA <tỉnh>") → giữ nguyên, TUYỆT ĐỐI không đổi thành Cục Cảnh sát/Bộ Công an.
   Giấy không ghi cơ quan cấp → bỏ field.
</nguoi_duoc_cap>

<giay_to_ho_tich>
9. GiayTo_LoaiSuKien CHỈ khi giấy tờ GHI RÕ loại: mục (4) tờ khai / giấy ủy quyền ghi tên loại trích lục
   (vd "Giấy khai sinh", "Trích lục khai tử"), hoặc hồ sơ có chính giấy hộ tịch loại đó của người được cấp.
   Mục (4) chỉ ghi "Bản sao" / để trống và không có giấy hộ tịch → BỎ field; KHÔNG suy loại từ tuổi, từ
   "Số chứng nhận", từ việc người được cấp còn sống hay không. Các field GiayTo_* còn lại ưu tiên khối "Đã đăng ký tại ..." của tờ khai, thiếu thì lấy trên
   CHÍNH giấy hộ tịch cùng loại và cùng người được cấp. Giấy khác loại hoặc khác người không phải nguồn.
10. GiayTo_CoQuanDangKy: nhãn "Đã đăng ký tại" / "Nơi đăng ký"; giấy khai sinh, trích lục thường không có
    nhãn → lấy cơ quan ở tiêu đề đầu văn bản hoặc khối ký tên cuối ("TM. UBND PHƯỜNG ..."). "UBND" viết
    thành "Ủy ban nhân dân", ghép kèm cấp tỉnh nếu giấy có.
11. GiayTo_So: dòng "Số: <mã>/<năm>" sát tiêu đề GIẤY KHAI SINH / TRÍCH LỤC, giữ nguyên mã và năm. Không
    lấy số CCCD, số định danh, số trang.
12. GiayTo_QuyenSo chỉ khi nhãn "Quyển số" có giá trị thật. "Số bộ", "sổ bộ", "số hiệu" không phải quyển số.
13. GiayTo_NgayDangKy: trên tờ khai lấy ngày theo mẫu "ngày D tháng M năm Y" đứng ngay trước "số ... Quyển
    số" trong mục "Đã đăng ký tại" (ngày ghi kèm chữ khác như "Số chứng nhận ngày ..." không phải ngày đăng ký
    khi mẫu đã có ngày); trên giấy hộ tịch lấy "Ngày, tháng, năm đăng ký" / "Ngày đăng ký" / ngày ở nơi ký.
    Đủ ngày-tháng-năm thì bắt buộc trả.
14. Trang CHỨNG THỰC ("Số chứng thực: ... quyển số ... SCT", ngày chứng thực) là sổ chứng thực → KHÔNG
    lấy làm GiayTo_So / GiayTo_QuyenSo / GiayTo_NgayDangKy / GiayTo_CoQuanDangKy.
15. SoLuongBanSao: cụm chữ số ngay trước chữ "bản" ở mục số lượng; dấu chấm/phẩy xen giữa chữ số là nhiễu
    OCR. Không ghi thì bỏ, không tự mặc định.
</giay_to_ho_tich>

<khong_bia>
16. Ngày chỉ trả khi đủ ngày-tháng-năm. Giấy tờ không ghi → bỏ field. Không suy diễn.
</khong_bia>"""
