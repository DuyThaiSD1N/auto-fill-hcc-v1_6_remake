"""Quy tắc trích riêng của thủ tục đăng ký khai tử có yếu tố nước ngoài (1.001766, cổng Bộ Tư pháp)."""

EXTRA_RULES = """
<procedure>
Thủ tục: Đăng ký khai tử có YẾU TỐ NƯỚC NGOÀI — người chết là người nước ngoài (hoặc chết ở nước ngoài, cư trú cuối
cùng ở nước ngoài). Đầu vào thường gồm: tờ khai đăng ký khai tử (bản giấy, có thể viết tay), CCCD của người yêu cầu,
hộ chiếu / giấy tờ tùy thân nước ngoài của người chết (kèm bản dịch), giấy báo tử hoặc giấy tờ thay thế, văn bản ủy
quyền.
</procedure>

<critical_rules>
1. Trả ONLY các field compact trong schema. Không trả field UI như HoTen, HoVaTenC, NgayMat, loaiDangKy, CapBanSao...
2. Phân vai bằng NỘI DUNG OCR, không dựa vào tên file. Tờ khai là nguồn chính xác định "người yêu cầu" (phần đầu) và
   "người được khai tử" (sau cụm "Đề nghị cơ quan đăng ký khai tử cho người có tên dưới đây").
3. Nhiều giấy tờ tùy thân: dùng tên / số trên tờ khai làm mỏ neo. CCCD trùng người yêu cầu → Requester_*; hộ chiếu /
   giấy tờ của người chết → Deceased_*. Không lấy chữ ký cuối trang làm họ tên nếu phần thông tin chính đã có tên.
4. Có tờ khai thì BẮT BUỘC trả thêm ToKhai_NguoiYeuCau_* và ToKhai_NguoiChet_* CHÉP NGUYÊN VĂN từ tờ khai, kể cả khi
   CCCD ghi khác. Python tự đối chiếu.
5. Không bịa. Ô trên tờ khai bỏ trống hoặc chỉ có dấu chấm → bỏ field đó.
</critical_rules>

<requester_rules>
- Requester_FullName / Requester_IdNumber / Requester_IdIssueDate / Requester_IdIssuePlace theo dòng "Giấy tờ tùy thân"
  của người yêu cầu trên tờ khai, CCCD cùng số bổ sung ô tờ khai thiếu (ngày sinh, ngày cấp, nơi cấp).
  Ví dụ "Thẻ căn cước công dân số 001090012345, Cục Cảnh sát QLHC về TTXH cấp ngày 02/03/2022" →
  Requester_IdType="Căn cước công dân", Requester_IdNumber="001090012345", Requester_IdIssueDate="02/03/2022",
  Requester_IdIssuePlace="Cục Cảnh sát QLHC về TTXH".
- Requester_BirthDate: tờ khai bỏ trống thì lấy ngày sinh trên CCCD của chính người yêu cầu.
- Requester_Relationship lấy từ nhãn "Quan hệ với người đã chết" / "Quan hệ với người được khai tử", chép nguyên văn.
- Requester_Residence lấy từ "Nơi cư trú" của người yêu cầu trên tờ khai; chỉ khi tờ khai không ghi mới lấy nơi thường
  trú trên CCCD.
</requester_rules>

<deceased_rules>
- Deceased_FullName: họ tên người chết theo tờ khai; hộ chiếu ghi Surname + Given names thì ghép HỌ trước TÊN, giữ chữ
  Latin (vd Surname "LI", Given names "MING" → "LI MING").
- Deceased_BirthDate / Deceased_IdIssueDate: hộ chiếu ghi "07 APR 1990" → "07/04/1990".
- Deceased_Nationality: tên nước bằng tiếng Việt (vd "Trung Quốc", "Hàn Quốc", "Lào"), không ghi "CHINESE" / "CHN".
- Deceased_Ethnicity chép ĐÚNG chữ dân tộc trên tờ khai / giấy báo tử (vd "Hán"), không đổi sang dân tộc Việt Nam gần
  nghĩa; không giấy nào ghi → bỏ.
- Deceased_IdType / Deceased_IdNumber / Deceased_IdIssueDate / Deceased_IdIssuePlace theo dòng "Giấy tờ tùy thân" của
  người chết trên tờ khai (thường là Hộ chiếu); thiếu thì lấy trên chính trang hộ chiếu / bản dịch. Số hộ chiếu giữ cả
  chữ lẫn số (vd "EA1234567"). Deceased_IdIssuePlace ưu tiên tên tiếng Việt trên tờ khai (vd "Cục quản lý xuất nhập
  cảnh Trung Quốc") hơn chữ tiếng Anh / tiếng nước ngoài trên hộ chiếu.
- Deceased_Residence lấy từ "Nơi cư trú cuối cùng". Deceased_ResidenceType chỉ trả khi giấy ghi rõ thường trú / tạm trú.
- Deceased_DeathDate và Deceased_DeathTime lấy từ "Đã chết vào lúc" / "Đã tử vong vào lúc". Không lấy ngày lập tờ khai,
  ngày cấp giấy tờ, ngày cấp giấy báo tử. Tờ khai không ghi giờ thì lấy giờ trên giấy báo tử; không có thì bỏ.
- Deceased_DeathPlace bắt buộc lấy từ "Nơi chết" / "Nơi tử vong" khi dòng này có nội dung; không có thì theo địa chỉ cơ
  sở khám bệnh, chữa bệnh báo tử trên giấy báo tử.
- Deceased_DeathCause lấy từ "Nguyên nhân chết" / "Nguyên nhân tử vong".
- Registration_Type CHỈ trả khi giấy ghi / tích rõ loại đăng ký; không có thì bỏ (Python tự tính theo ngày chết).
</deceased_rules>

<death_notice_rules>
- DeathNotice_* dùng cho giấy báo tử / giấy tờ thay giấy báo tử có trong hồ sơ: DeathNotice_Number theo "Số:" của giấy,
  DeathNotice_IssueDate theo dòng ngày ở khối ký của thủ trưởng cơ sở, DeathNotice_IssueAgency = tên cơ sở khám bệnh,
  chữa bệnh / cơ quan cấp. Dòng "Số Giấy báo tử" trên tờ khai để trống → không trả DeathNotice_Number.
</death_notice_rules>

<copy_request_rules>
- "Đề nghị cấp bản sao" tích "Có" → CopyRequest_WantsCopy="Có"; tích "Không" → "Không".
- CopyRequest_Quantity lấy số bản nếu ghi rõ, vd "01 bản" → "1".
</copy_request_rules>

<address_split_rules>
- Mọi địa chỉ trả object {quocGia,tinh,xa,chiTietDuoiXa}.
- Địa chỉ TRONG NƯỚC: quocGia="Việt Nam"; xa = tên phường / xã / thị trấn, bỏ tiền tố; chiTietDuoiXa = thôn, xóm, tổ,
  số nhà, đường. Địa chỉ cũ còn cấp huyện / thành phố thuộc tỉnh thì bỏ cấp đó; không ghi tỉnh thì tinh = tỉnh chứa
  thành phố / huyện đó. Ví dụ "phường Đông Ngàn, thị xã Từ Sơn" → tinh="Bắc Ninh", xa="Đông Ngàn";
  "Xóm 3, xã Nghi Hoa, tỉnh Nghệ An" → tinh="Nghệ An", xa="Nghi Hoa", chiTietDuoiXa="Xóm 3".
- Địa chỉ ở NƯỚC NGOÀI: quocGia = tên nước bằng tiếng Việt (tên nước có thể dính liền cuối địa chỉ, vd "... tỉnh Quảng
  Đông Trung Quốc" → quocGia="Trung Quốc"); tinh = tỉnh / bang; xa = thành phố / quận / huyện; chiTietDuoiXa = phần còn
  lại (số nhà, đường, thôn, tổ, thị trấn). KHÔNG ép vào tỉnh / xã của Việt Nam. Ví dụ "số 8, đường Trường Giang, thị trấn
  Hoa Đông, thành phố Quảng Châu, tỉnh Quảng Đông Trung Quốc" → quocGia="Trung Quốc", tinh="tỉnh Quảng Đông",
  xa="thành phố Quảng Châu", chiTietDuoiXa="số 8, đường Trường Giang, thị trấn Hoa Đông".
- OCR xuống dòng giữa tên địa danh thì ghép lại.
</address_split_rules>

<reminder>
Chỉ trả JSON compact theo schema. Không trả field UI/default. Không tự đoán quốc tịch / dân tộc / số giấy báo tử.
</reminder>
"""
