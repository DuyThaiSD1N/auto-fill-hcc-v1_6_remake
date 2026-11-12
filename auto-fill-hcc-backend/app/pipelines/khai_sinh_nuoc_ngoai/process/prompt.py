"""Quy tắc trích riêng của thủ tục đăng ký khai sinh có yếu tố nước ngoài (Cổng DVC quốc gia mới).

Nền là quy tắc của khai sinh 1.001193 (cùng tờ khai); khối <yeu_to_nuoc_ngoai> đè lên chỗ khác biệt.
"""

from app.pipelines.khai_sinh_dvc_moi.process.prompt import EXTRA_RULES as _BASE_RULES

EXTRA_RULES = _BASE_RULES + """

<yeu_to_nuoc_ngoai>
Hồ sơ có YẾU TỐ NƯỚC NGOÀI: cha và/hoặc mẹ là người nước ngoài, hoặc trẻ sinh ở nước ngoài. Ngoài giấy tờ khai sinh
thường còn có: hộ chiếu, giấy tờ tùy thân nước ngoài kèm bản dịch công chứng, văn bản thỏa thuận của cha mẹ về việc
lựa chọn quốc tịch cho con, giấy xác nhận quốc tịch của cơ quan nước ngoài (đại sứ quán, lãnh sự quán), kết quả
phân tích ADN, giấy tờ nước ngoài xác nhận việc sinh. Khối này ĐÈ các quy tắc phía trên khi khác nhau.
15. Con_HoTen chép ĐÚNG dòng họ tên người được khai sinh trên tờ khai, giữ cả phần phiên âm trong ngoặc nếu tờ khai
    ghi (vd "LI MING (LÝ MINH)"). Không có tờ khai → theo văn bản thỏa thuận quốc tịch / giấy chứng sinh.
16. Con_QuocTich theo văn bản thỏa thuận lựa chọn quốc tịch → giấy xác nhận quốc tịch của cơ quan nước ngoài →
    tờ khai. KHÔNG tự gán "Việt Nam"; không giấy nào ghi → bỏ.
17. Dân tộc của người nước ngoài chép đúng chữ trên giấy (vd "Hán"); không đổi sang dân tộc Việt Nam gần nghĩa.
18. Cha/mẹ người nước ngoài: *_LoaiGiayTo / *_SoGiayTo theo dòng "Giấy tờ tùy thân" của người đó trên tờ khai
    (thường là Hộ chiếu); *_NgayCap / *_NoiCap lấy trên CHÍNH giấy tờ đó (trang hộ chiếu, bản dịch hộ chiếu), không
    lấy của thẻ cư dân / CMND nước ngoài khi tờ khai khai hộ chiếu. *_SoDinhDanh CHỈ là số định danh 12 chữ số của
    Việt Nam — số thẻ cư dân / CMND nước ngoài (vd 18 chữ số) KHÔNG trả ở đây.
19. Địa chỉ ở NƯỚC NGOÀI (nơi sinh, quê quán, nơi cư trú): quocGia = tên nước bằng tiếng Việt (vd "Trung Quốc",
    "Hàn Quốc"); tinh = tỉnh / bang; xa = thành phố / quận / huyện; chiTietDuoiXa = phần còn lại (số nhà, đường,
    thôn, tổ). KHÔNG ép vào tỉnh / xã của Việt Nam. Ví dụ "Thành phố Quảng Châu, tỉnh Quảng Đông, Trung Quốc" →
    quocGia="Trung Quốc", tinh="Tỉnh Quảng Đông", xa="Thành phố Quảng Châu".
20. *_NoiCuTru của cha / mẹ người nước ngoài: lấy dòng nơi cư trú (thường trú / tạm trú) của người đó trên TỜ KHAI;
    tờ khai ghi địa chỉ ở Việt Nam thì quocGia="Việt Nam" dù quốc tịch nước ngoài. Tờ khai và giấy khác (giấy chứng
    sinh, giấy kết hôn, giấy tờ nước ngoài) ghi khác nhau → theo tờ khai. Không có tờ khai → giấy tờ mới nhất.
21. *_LoaiCuTru theo NHÃN dòng nơi cư trú của người đó trên tờ khai ("Nơi tạm trú" → "Tạm trú").
</yeu_to_nuoc_ngoai>"""
