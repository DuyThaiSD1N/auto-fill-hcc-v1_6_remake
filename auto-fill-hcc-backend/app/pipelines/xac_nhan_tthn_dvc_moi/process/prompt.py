"""Quy tắc trích riêng của thủ tục cấp Giấy xác nhận tình trạng hôn nhân (Cổng DVC quốc gia mới)."""

EXTRA_RULES = """<ho_so>
Hồ sơ cấp Giấy XNTTHN: tờ khai, CCCD/CMND/hộ chiếu, giấy ủy quyền, giấy XNTTHN đã cấp trước đây, bản án / quyết định
ly hôn, giấy chứng tử / trích lục khai tử của vợ/chồng, giấy chứng nhận kết hôn. Khối người nộp trên cổng khóa theo tài
khoản → KHÔNG trích người nộp, trừ số điện thoại (xem <nguoi_nop>).
</ho_so>

<nguoi_duoc_cap>
1. Người được cấp theo đúng khối <nguoi_duoc_cap> đã chốt ở bước phân vai. Người được khai tử trên giấy chứng tử /
   trích lục khai tử / giấy báo tử là người ĐÃ CHẾT, không bao giờ là người được cấp: hồ sơ chỉ có thẻ CCCD của một
   người + giấy khai tử của người khác → NguoiDuocCap_* lấy theo thẻ CCCD, KHÔNG lấy họ tên, ngày sinh, số định danh
   của người chết.
2. Nguồn họ tên, ngày sinh, số định danh: thẻ CCCD/căn cước CỦA CHÍNH người đó (bản in đáng tin hơn chữ viết tay) →
   tờ khai (khối sau câu "Đề nghị cấp...") → giấy XNTTHN cũ / giấy ủy quyền. Số trên tờ khai lệch vài chữ số so với
   thẻ của chính người đó → lấy theo thẻ. KHÔNG lấy số, ngày sinh từ thẻ của người khác (người nộp hộ, vợ/chồng).
3. Giới tính, quốc tịch, giấy tờ tùy thân (loại, số, ngày cấp, nơi cấp) cùng nguồn như mục 2: thẻ của CHÍNH người được
   cấp trước, rồi tới dòng "Giấy tờ tùy thân" ở khối người được cấp trên tờ khai. Nơi cấp chép đúng chữ; "Cục CS QLHC về
   TTXH" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; căn cước mới "BỘ CÔNG AN" → "Bộ Công an". Dân tộc: thẻ
   căn cước mẫu mới thường không in → trả theo TỪNG nguồn, mỗi nguồn một field: dòng "Dân tộc" ở khối người được cấp
   trên tờ khai (hay chung dòng với giới tính, kẹp số chú thích: "Giới tính: (2) Nữ Dân tộc: (2) Kinh" → Kinh) hoặc
   thẻ CMND cũ → NguoiDuocCap_DanToc; giấy tờ khác của chính người đó → GiayToKhac_DanToc. Không giấy nào ghi → bỏ.
4. NguoiDuocCap_NoiCuTru = nơi cư trú HIỆN TẠI: dòng "Nơi cư trú" ở khối người được cấp trên tờ khai → nơi thường trú
   in trên thẻ của chính người đó. KHÔNG lấy địa chỉ trong dòng tình trạng hôn nhân (địa chỉ vợ/chồng, địa chỉ cũ),
   KHÔNG lấy "Nơi chết"/"Nơi thường trú cuối cùng" trên giấy chứng tử.
</nguoi_duoc_cap>

<nguoi_nop>
- NguoiNop_SoDienThoai: CHỈ khi <nguoi_nop> ghi "Có trong hồ sơ: Có". Lấy số điện thoại của CHÍNH người nộp ở:
  (a) dòng "Số điện thoại" in trong khối người yêu cầu của tờ khai, khi người yêu cầu là người nộp;
  (b) số viết tay cạnh / dưới tên, chữ ký của người nộp ("SĐT", "ĐT", hoặc chỉ một dãy số 10 chữ số);
  (c) dòng "Số điện thoại"/"ĐT" trong đơn do chính người nộp đứng tên.
  Chép đủ chữ số. Số của người khác, cơ quan, cán bộ xác nhận → bỏ.
- NguoiYeuCau_* chép khối người yêu cầu của tờ khai (họ tên, số giấy tờ, dòng quan hệ) — chỉ để đối chiếu với tài
  khoản; tờ khai ghi người yêu cầu khác tài khoản vẫn chép đúng tờ khai.
</nguoi_nop>

<tinh_trang_hon_nhan>
- TinhTrangHonNhan = MỘT mã chữ dưới đây, đọc theo NỘI DUNG CẢ dòng "Tình trạng hôn nhân" trên TỜ KHAI (không có tờ
  khai thì theo dòng tình trạng trên giấy XNTTHN cũ; không có cả hai → bỏ). Số chú thích in sẵn trên mẫu như "(4)"
  KHÔNG phải mã.
  "co_vo_chong" = HIỆN TẠI đang có vợ/chồng — kể cả đã ly hôn/góa rồi kết hôn lại ("hiện tại đã kết hôn với ...").
  "chua_ket_hon" = chưa từng kết hôn: dòng KHÔNG nhắc ly hôn hay vợ/chồng chết.
  "ly_hon" = đã kết hôn nhưng ĐÃ LY HÔN, hiện tại chưa kết hôn lại.
  "goa" = vợ/chồng ĐÃ CHẾT, hiện tại chưa kết hôn lại.
  "khoang_thoi_gian" = xin xác nhận chưa đăng ký kết hôn TỪ ngày ... ĐẾN ngày ... đã qua VÀ HIỆN TẠI ĐANG CÓ vợ/chồng.
  Dòng ghi một khoảng thời gian ("trong thời gian cư trú tại ... từ ... đến ...") mà hiện tại VẪN chưa kết hôn →
  "chua_ket_hon", không phải "khoang_thoi_gian".
  "khac" = không thuộc các trường hợp trên → kèm TinhTrangHonNhan_NoiDung chép đúng dòng đó.
- Đuôi "hiện tại chưa đăng ký kết hôn với ai" có ở cả chua_ket_hon, ly_hon, goa → quyết định theo phần ĐẦU dòng: có ly
  hôn → "ly_hon", có vợ/chồng đã chết → "goa", không nhắc gì → "chua_ket_hon".
- ly_hon/goa vẫn trả kèm giấy tờ ly hôn / khai tử đọc được; co_vo_chong có ly hôn/góa trước đó thì trả kèm cả giấy tờ
  đó lẫn Marriage_*.
- Không suy luận tình trạng hôn nhân từ CCCD vì CCCD không chứa dữ liệu này.

KHOẢNG THỜI GIAN CHƯA ĐĂNG KÝ KẾT HÔN:
- Dạng thường gặp: "Từ ngày 01 tháng 01 năm 2025 đến ngày 13 tháng 12 năm 2025. Tôi chưa đăng ký kết hôn với ai. Hiện
  tại đã kết hôn với ...", "Từ 27-4-2016 tới 14-9-2016 chưa đăng ký kết hôn với ai."
- Period_TuNgay = ngày sau "Từ (ngày)"; Period_DenNgay = ngày sau "đến/tới (ngày)". dd/mm/yyyy, ghép đủ ngày + tháng
  + năm dù viết tách chữ hay gạch chéo. Chữ "ngày" có thể vắng.
- BẮT BUỘC trả Period_* KỂ CẢ khi cùng dòng còn khai ly hôn hoặc vợ/chồng đã chết; mốc bắt đầu hay trùng ngày bản án
  ly hôn — MỘT ngày được phép nằm ở cả hai field.
- Period_* CHỈ lấy từ TỜ KHAI. Ngày chết, ngày ly hôn, ngày đăng ký kết hôn KHÔNG phải Period. Có "Từ ..." mà không có
  "đến/tới ..." → Period_DenNgay để trống.
</tinh_trang_hon_nhan>

<giay_khai_tu>
- DeathCert_* lấy từ tài liệu khai tử thật của VỢ/CHỒNG (giấy chứng tử, trích lục khai tử, giấy báo tử), HOẶC từ dòng
  tình trạng hôn nhân trên tờ khai / giấy XNTTHN cũ ("Theo giấy chứng tử số <N> do <CQ> cấp ngày <D>").
- Cổng hỏi Số / Ngày cấp / Cơ quan cấp của CHÍNH TỜ GIẤY ĐANG NỘP:
  + DeathCert_Number = số ở nhãn "Số:" ĐẦU trang, GIỮ NGUYÊN hậu tố ("167/TLKT-BS"). KHÔNG lấy số ở dòng thân "Đã
    được đăng ký khai tử tại ... Số: <N> ngày <D>" (số đăng ký gốc trong sổ), trừ khi đầu trang không có số nào.
  + DeathCert_Date = ngày cấp/ký chính tài liệu (dòng địa danh + ngày đầu văn bản hoặc khối ký). KHÔNG lấy ngày chết,
    ngày sinh. Số và ngày phải CÙNG một nguồn.
  + DeathCert_Agency = cơ quan cấp/ký chính tài liệu (khối "UBND XÃ ..."); "UBND" → "Ủy ban nhân dân".
- Hồ sơ kèm giấy thật thì lấy theo giấy thật; tờ khai chỉ bù field giấy thật không đọc được.
</giay_khai_tu>

<ban_an_ly_hon>
- HAI nhóm field, mỗi nhóm đúng MỘT nguồn. Hồ sơ có cả hai nguồn thì trả CẢ HAI nhóm, kể cả khi chúng ghi khác nhau
  (người dân hay chép nhầm năm, cơ quan lên tờ khai — Python tự chọn):
  + BanAn_Number/Date/Agency: CHỈ đọc từ VĂN BẢN quyết định/bản án ly hôn của Tòa án kèm trong hồ sơ. Hồ sơ không kèm
    văn bản đó → bỏ cả nhóm.
  + DivorceDecision_Number/Date/Agency: CHỈ đọc từ dòng tình trạng hôn nhân trên TỜ KHAI / giấy XNTTHN cũ. Không có
    dòng đó → bỏ cả nhóm.
- BanAn_Number: số ở nhãn "Số:" NGAY ĐẦU văn bản. KHÔNG lấy số ở cụm DẪN CHIẾU ("Tại quyết định số ...", "theo bản án
  số ..."), số thụ lý, số biên lai, số án phí.
- BanAn_Date: ngày ban hành ở dòng địa danh + ngày đầu văn bản, hoặc nhãn "Ngày:" ngay dưới "Bản án số:"/"Quyết định
  số:". Không lấy ngày hòa giải, ngày thụ lý, ngày hiệu lực.
- BanAn_Agency: cơ quan ban hành; "TAND" → "Tòa án nhân dân".
- DivorceDecision_*: dòng tờ khai ghi đã ly hôn theo bản án/quyết định số <N> của/do <CQ> ... ngày <D> → trả ĐỦ ba
  field, giữ nguyên số và ký hiệu. <D> là ngày gắn với việc ly hôn trên chính dòng đó, không phải ngày đăng ký kết hôn.
</ban_an_ly_hon>

<giay_ket_hon>
- Nguồn Marriage_*: (1) GIẤY CHỨNG NHẬN KẾT HÔN thật; (2) dòng tình trạng hôn nhân trên tờ khai khi ghi rõ hiện tại
  đang có vợ/chồng.
- Marriage_SpouseName = họ tên vợ/chồng HIỆN TẠI (sau "đang có chồng là", "đang có vợ là", "hiện tại đã kết hôn với",
  "đã kết hôn với ông/bà"), KỂ CẢ khi phía trước còn khai ly hôn/góa. Chỉ họ tên.
- Giấy chứng nhận kết hôn in HAI CỘT (trái VỢ, phải CHỒNG): người vợ/chồng là người KHÔNG phải người được cấp.
- Marriage_Number/Date/Agency chỉ trả khi giấy kết hôn hoặc tờ khai ghi rõ; không lấy số/ngày cấp CCCD.
- Giấy ly hôn/khai tử không phải nguồn Marriage_*. Cuộc hôn nhân MỚI đăng ký sau ngày ly hôn/ngày chết thì vẫn trả
  Marriage_* — đó là hôn nhân hiện tại.
</giay_ket_hon>

<giay_xntthn_cu>
Giấy XNTTHN cũ NHẮC LẠI tình trạng hôn nhân + giấy tờ liên quan: dòng "... chồng/vợ đã chết (theo Giấy chứng tử / Trích
lục khai tử số <N> do <CQ> cấp ngày <D>)" → DeathCert_*; "... đã ly hôn (Bản án/Quyết định ly hôn số <N> ngày <D> của
<CQ>)" → DivorceDecision_*. Nhân thân người được cấp in ở khối "XÁC NHẬN" → nguồn NguoiDuocCap_* khi không có thẻ.
</giay_xntthn_cu>

<ket_hon_voi>
KetHonVoi_* CHỈ khi <muc_dich> có Loại là ket_hon_co_quan_dai_dien hoặc ket_hon_nuoc_ngoai VÀ giấy tờ ghi thông tin
người dự định kết hôn (dòng mục đích, giấy tờ của người đó). Không có → bỏ, không suy đoán.
</ket_hon_voi>

<so_luong>
SoLuongBanSao: số bản sao giấy XNTTHN tờ khai đề nghị (số nguyên). Tờ khai không ghi → bỏ.
</so_luong>

<dia_chi>
Địa chỉ tách {quocGia,tinh,xa,diaChi}: "[chi tiết], [xã], [huyện], [tỉnh]" đếm từ cuối — cuối là tỉnh, áp cuối là cấp
huyện (bỏ khỏi xa/diaChi, trả riêng ở khóa "huyen"), cụm trước huyện là xã, còn lại là diaChi.
Thẻ CCCD hay in nơi thường trú HAI dòng: "Nơi thường trú: Khu A" / "B, Thành phố C, D" → đọc liền thành "Khu A, B,
Thành phố C, D": xa = B, huyen = Thành phố C, diaChi = Khu A. Cụm cạnh nhãn ở dòng đầu là thôn/khu/tổ, không phải xã.
</dia_chi>

<khong_bia>
Giấy tờ không ghi → bỏ field. Không suy diễn.
</khong_bia>"""
