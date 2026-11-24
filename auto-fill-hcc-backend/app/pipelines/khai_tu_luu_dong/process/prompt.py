"""Quy tắc trích riêng của thủ tục đăng ký khai tử lưu động (1.000419, cổng Bộ Tư pháp)."""

EXTRA_RULES = """
<procedure>
Thủ tục: Đăng ký khai tử LƯU ĐỘNG — cán bộ hộ tịch đến tận nơi đăng ký khai tử (người yêu cầu già yếu, ở vùng xa...).
Tờ khai giống tờ khai đăng ký khai tử thường, có thể có ghi chú tay "Khai tử lưu động". Đầu vào thường gồm: tờ khai
đăng ký khai tử (bản giấy, có thể viết tay), CCCD của người yêu cầu, giấy báo tử hoặc giấy tờ thay thế giấy báo tử (có
thể không có khi người chết đã lâu), giấy tờ khác.
</procedure>

<critical_rules>
1. Trả ONLY các field compact trong schema. Không trả field UI như HoTen, HoVaTenC, NgayMat, loaiDangKy, SoLuong...
2. Phân vai bằng NỘI DUNG OCR, không dựa vào tên file. Tờ khai là nguồn chính xác định "người yêu cầu" (phần đầu) và
   "người được khai tử" (sau cụm "Đề nghị cơ quan đăng ký khai tử cho người có tên dưới đây").
3. Nhiều giấy tờ tùy thân: dùng tên / số trên tờ khai làm mỏ neo. CCCD trùng người yêu cầu → Requester_*; giấy tờ của
   người chết → Deceased_*. Không lấy chữ ký cuối trang làm họ tên nếu phần thông tin chính đã có tên.
4. Có tờ khai thì BẮT BUỘC trả thêm ToKhai_NguoiYeuCau_* và ToKhai_NguoiChet_* CHÉP NGUYÊN VĂN từ tờ khai, kể cả khi
   CCCD ghi khác. Python tự đối chiếu.
5. Không bịa. Ô trên tờ khai bỏ trống hoặc chỉ có dấu chấm → bỏ field đó (vd dòng "Giấy tờ tùy thân" của người chết
   bỏ trống → không trả Deceased_Id*).
</critical_rules>

<requester_rules>
- Requester_FullName / Requester_IdNumber / Requester_IdIssueDate / Requester_IdIssuePlace theo dòng "Giấy tờ tùy thân"
  của người yêu cầu trên tờ khai, CCCD cùng số bổ sung ô tờ khai thiếu (ngày cấp, nơi cấp).
  Ví dụ "Thẻ căn cước công dân số 001090012345, Cục Cảnh sát QLHC về TTXH cấp ngày 02/03/2022" →
  Requester_IdType="Căn cước công dân", Requester_IdNumber="001090012345", Requester_IdIssueDate="02/03/2022",
  Requester_IdIssuePlace="Cục Cảnh sát QLHC về TTXH".
- Requester_Relationship lấy từ nhãn "Quan hệ với người đã chết" / "Quan hệ với người được khai tử", chép nguyên văn.
- Requester_Residence lấy từ "Nơi cư trú" của người yêu cầu trên tờ khai; chỉ khi tờ khai không ghi mới lấy nơi thường
  trú trên CCCD.
</requester_rules>

<deceased_rules>
- Deceased_FullName: họ tên người chết theo tờ khai / giấy báo tử.
- Deceased_BirthDate: tờ khai chỉ ghi năm (vd "1930") thì trả đúng "1930", không tự thêm ngày tháng.
- Deceased_Ethnicity / Deceased_Nationality chép đúng chữ trên tờ khai / giấy báo tử; không giấy nào ghi → bỏ.
- Deceased_Residence lấy từ "Nơi cư trú cuối cùng". Deceased_ResidenceType chỉ trả khi giấy ghi rõ thường trú / tạm trú.
- Deceased_DeathDate và Deceased_DeathTime lấy từ "Đã chết vào lúc" / "Đã tử vong vào lúc". Không lấy ngày lập tờ khai
  ("Làm tại ..., ngày ..."), ngày cấp giấy tờ, ngày cấp giấy báo tử. Người chết đã lâu thì năm chết có thể cách xa hiện
  tại hàng chục năm — vẫn chép đúng. Tờ khai không ghi giờ thì lấy giờ trên giấy báo tử; không có thì bỏ.
- Deceased_DeathPlace bắt buộc lấy từ "Nơi chết" / "Nơi tử vong" khi dòng này có nội dung; không có thì theo địa chỉ cơ
  sở khám bệnh, chữa bệnh báo tử trên giấy báo tử.
- Deceased_DeathCause lấy từ "Nguyên nhân chết" / "Nguyên nhân tử vong", chép nguyên văn.
- Registration_Type CHỈ trả khi giấy ghi / tích rõ loại đăng ký (đúng hạn / quá hạn / người chết đã lâu). Ghi chú tay
  "Khai tử lưu động" KHÔNG phải loại đăng ký → bỏ (Python tự tính theo ngày chết).
</deceased_rules>

<death_notice_rules>
- DeathNotice_* dùng cho giấy báo tử / giấy tờ thay giấy báo tử có trong hồ sơ: DeathNotice_Number theo "Số:" của giấy,
  DeathNotice_IssueDate theo dòng ngày ở khối ký của thủ trưởng cơ sở, DeathNotice_IssueAgency = tên cơ sở khám bệnh,
  chữa bệnh / cơ quan cấp. Dòng "Số Giấy báo tử/Giấy tờ thay thế Giấy báo tử" trên tờ khai để trống và hồ sơ không có
  giấy báo tử → không trả DeathNotice_*.
</death_notice_rules>

<copy_request_rules>
- "Đề nghị cấp bản sao" tích "Có" (☒ / ☑ / x cạnh chữ Có) → CopyRequest_WantsCopy="Có"; tích "Không" → "Không".
- CopyRequest_Quantity lấy số bản nếu ghi rõ, vd "Số lượng: 01 bản" → "1".
</copy_request_rules>

<address_split_rules>
- Mọi địa chỉ trả object {quocGia,tinh,xa,chiTietDuoiXa}.
- Địa chỉ TRONG NƯỚC: quocGia="Việt Nam"; xa = tên phường / xã / thị trấn, bỏ tiền tố; chiTietDuoiXa = thôn, xóm, tổ
  dân phố (TDP), số nhà, đường. Địa chỉ cũ còn cấp huyện / thành phố thuộc tỉnh thì bỏ cấp đó; không ghi tỉnh thì tinh =
  tỉnh chứa thành phố / huyện đó. Ví dụ "TDP Đông, phường Đông Ngàn, thị xã Từ Sơn" → tinh="Bắc Ninh", xa="Đông Ngàn",
  chiTietDuoiXa="TDP Đông"; "Xóm 3, xã Nghi Hoa, tỉnh Nghệ An" → tinh="Nghệ An", xa="Nghi Hoa", chiTietDuoiXa="Xóm 3".
- Địa chỉ ở NƯỚC NGOÀI: quocGia = tên nước bằng tiếng Việt; tinh / xa theo địa danh nước đó, không ép vào Việt Nam.
- OCR xuống dòng giữa tên địa danh thì ghép lại.
</address_split_rules>

<reminder>
Chỉ trả JSON compact theo schema. Không trả field UI/default. Không tự đoán dân tộc / số giấy báo tử / loại đăng ký.
</reminder>
"""
