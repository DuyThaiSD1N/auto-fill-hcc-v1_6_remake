"""Quy tắc trích riêng của thủ tục đăng ký khai sinh (Cổng DVC quốc gia mới)."""

EXTRA_RULES = """<ho_so>
Hồ sơ đăng ký khai sinh: tờ khai đăng ký khai sinh (nếu có), giấy chứng sinh / văn bản người làm chứng / giấy cam
đoan về việc sinh, giấy chứng nhận kết hôn của cha mẹ, CCCD/CMND/hộ chiếu, trích lục khai tử của cha/mẹ, văn bản
xác nhận mang thai hộ, biên bản trẻ bị bỏ rơi, giấy ủy quyền, giấy tờ cá nhân (BHYT, học bạ...) của người được
khai sinh. Khối người nộp trên cổng khóa theo tài khoản → KHÔNG trích người nộp.
</ho_so>

<phan_vai>
- Có khối <phan_vai_da_xac_dinh> phía dưới → con / mẹ / cha theo đúng khối đó.
- Không có khối đó (dự phòng): con = người sau câu "đăng ký khai sinh cho người dưới đây" của tờ khai, hoặc
  "Dự định đặt tên con" trên giấy chứng sinh; mẹ / cha theo dòng "người mẹ" / "người cha" của tờ khai, mẹ trên
  giấy chứng sinh, vợ / chồng trên giấy chứng nhận kết hôn.
</phan_vai>

<con>
1. Nguồn: tờ khai → giấy chứng sinh / giấy cam đoan về việc sinh → CCCD của chính người được khai sinh (người
   đã có hồ sơ, giấy tờ cá nhân). Tên trên giấy chứng sinh bị gạch sửa tay → lấy tên đã sửa khớp tờ khai.
   Ngày sinh: tờ khai và CCCD lệch nhau thì đối chiếu dòng MRZ của CCCD (6 số đầu dòng 2 = yymmdd).
2. Con_NoiSinh: sinh tại cơ sở y tế → diaChi = tên đầy đủ cơ sở y tế nối ", " + phần địa chỉ chi tiết của cơ sở
   đứng trước phường/xã; tinh/xa của cơ sở. Sinh tại nhà/thôn → địa chỉ đó.
3. Con_QueQuan theo dòng "Quê quán" của tờ khai / giấy tờ; không có thì bỏ, không tự suy.
4. Dân tộc / quốc tịch chỉ khi giấy ghi rõ; "Mông" giữ "Mông", biến thể có "H" đứng đầu (Hmông) → "Mông (Hmông)".
</con>

<me_cha>
5. Mỗi người lấy trọn từ giấy tờ của CHÍNH người đó: tờ khai (dòng người mẹ / người cha), giấy chứng nhận kết hôn
   (vợ = mẹ, chồng = cha), CCCD / hộ chiếu của chính họ, trích lục khai tử của chính họ. Không trộn người.
6. Cha/mẹ người nước ngoài: quốc tịch, loại giấy tờ (Hộ chiếu) và số hộ chiếu theo giấy chứng nhận kết hôn / tờ
   khai / hộ chiếu; không gán "Việt Nam". Nơi cư trú vẫn lấy dòng "Nơi cư trú" của người đó trên tờ khai
   (thường là địa chỉ ở Việt Nam) — quốc tịch nước ngoài không phải lý do bỏ nơi cư trú.
7. Ngày sinh chỉ khi đủ ngày-tháng-năm; giấy chỉ ghi năm sinh → bỏ Me_NgaySinh / Cha_NgaySinh.
8. Cha/mẹ ĐÃ CHẾT (nơi cư trú ghi "chết", có trích lục khai tử) → *_DaChet = true và BỎ *_NoiCuTru. Giấy tờ
   tùy thân của người đã chết lấy dòng "Giấy tờ tùy thân" trong khối NGƯỜI CHẾT của trích lục khai tử; KHÔNG lấy
   giấy tờ của người đi khai tử.
9. *_NoiCap chép đúng cơ quan cấp ghi trên giấy; chỉ đổi cách viết của CÙNG cơ quan ("Cục CS QLHC về TTXH" →
   "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; mặt sau CCCD "CỤC TRƯỞNG CỤC CẢNH SÁT..." → cơ quan đó).
   Không ghi → bỏ.
10. *_NoiCuTru: dòng nơi cư trú của chính người đó; không mượn địa chỉ người khác. Dòng "Nơi cư trú" nằm trong
    khối người mẹ / người cha của tờ khai (hoặc trên giấy tờ của chính họ) BẮT BUỘC trả cho người đó, kể cả khi
    trùng từng chữ với địa chỉ người kia — vợ chồng ở chung một nơi là bình thường.
</me_cha>

<dia_chi>
11. Địa chỉ tách {quocGia,tinh,xa,diaChi}: "[chi tiết], [xã], [huyện], [tỉnh]" đếm từ cuối — cuối là tỉnh, áp cuối
    là cấp huyện (bỏ khỏi xa/diaChi, trả riêng ở khóa "huyen"), cụm trước huyện là xã, còn lại là diaChi.
</dia_chi>

<nguoi_yeu_cau>
12. NguoiYeuCau_* chép phần đầu tờ khai (người yêu cầu, giấy tờ tùy thân, dòng quan hệ) — chỉ để đối chiếu với tài
    khoản; không có tờ khai → bỏ.
13. SoLuongBanSao: "Đề nghị cấp bản sao: Có ☑ ... <n> bản" → n; đánh dấu "Không" → 0; không ghi → bỏ.
</nguoi_yeu_cau>

<khong_bia>
14. Giấy tờ không ghi → bỏ field. Không suy diễn, không ghép ngày "01/01".
</khong_bia>"""
