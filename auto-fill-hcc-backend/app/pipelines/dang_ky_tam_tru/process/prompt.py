"""Luật riêng của thủ tục Đăng ký tạm trú cho compact agent."""

EXTRA_RULES = """Đầu vào thường gồm:
1. Tờ khai thay đổi thông tin cư trú (Mẫu CT01) — có thể đánh máy hoặc viết tay.
2. Giấy tờ chứng minh chỗ ở hợp pháp: hợp đồng cho thuê/cho mượn/cho ở nhờ (thường viết tay một phần),
   Giấy chứng nhận quyền sử dụng đất, quyền sở hữu nhà ở…
3. Có thể có CCCD/thẻ Căn cước của người đăng ký tạm trú.

<critical_rules>
- Người đăng ký tạm trú là NGƯỜI THUÊ / người được cho mượn, cho ở nhờ (Bên B, "Bên thuê"), KHÔNG phải chủ
  nhà / bên cho thuê (Bên A) và KHÔNG phải người đứng tên Giấy chứng nhận quyền sử dụng đất.
- Thứ tự ưu tiên cho NguoiDangKy_*: CCCD của người đăng ký → Tờ khai CT01 (mục 1–6) → hợp đồng (phần Bên B).
- Không bịa thông tin còn thiếu. Ô để trống, chấm chấm ("……") hoặc gạch ngang là KHÔNG có dữ liệu.
</critical_rules>

<person_rules>
- NguoiDangKy_SoDinhDanh là 12 chữ số. Tờ khai CT01 hay ghi từng chữ số trong ô vuông → ghép liền, bỏ khoảng
  trắng. Hợp đồng có thể ghi nhãn "CMND số" nhưng là số 12 chữ số của thẻ CCCD; chữ viết tay dễ thừa/thiếu
  một chữ số → ưu tiên số trên CCCD/CT01 khi có.
- NguoiDangKy_GioiTinh chỉ "Nam" hoặc "Nữ", lấy từ CCCD hoặc mục 3 Tờ khai CT01.
- NguoiDangKy_SoDienThoai / NguoiDangKy_Email lấy ở mục 5 / mục 6 Tờ khai CT01; để trống nếu dòng chỉ có dấu chấm.
- ChuHo_QuanHe lấy ở mục 8 Tờ khai CT01 "Mối quan hệ với chủ hộ" (chữ có thể bị xuống dòng, vd "Chủ / hộ" → "Chủ hộ").
</person_rules>

<residence_rules>
- Nơi đề nghị đăng ký tạm trú lấy từ mục 10 Tờ khai CT01 ("Nơi đề nghị đăng ký tạm trú"); không có CT01 thì lấy
  địa chỉ căn nhà/phòng cho thuê trong hợp đồng (vd Điều 1 "Trong căn nhà tại địa chỉ…").
- NoiTamTru_DiaChiChiTiet CHỈ gồm phần dưới cấp xã. Ví dụ "Số 12 ngách 3 ngõ 45 phố Hoa Mai, phường Đông Hưng,
  thành phố Hà Nội" → NoiTamTru_DiaChiChiTiet = "Số 12 ngách 3 ngõ 45 phố Hoa Mai", NoiTamTru_Xa = "Phường Đông
  Hưng", NoiTamTru_Tinh = "Thành phố Hà Nội".
- Giấy ghi cả địa giới MỚI và địa giới CŨ (vd "(địa giới hành chính theo giấy tờ chứng minh chỗ ở hợp pháp:
  phường X, quận Y…)") → NoiTamTru_Xa / NoiTamTru_Tinh theo địa giới MỚI.
- NoiDungDeNghi: chép nguyên văn nội dung mục 10 Tờ khai CT01, bỏ chữ "Nội dung đề nghị:" ở đầu.
- ThoiHan_DenNgay: "Thời hạn tạm trú" ở mục 10 CT01, không có thì ngày kết thúc hợp đồng. Hợp đồng chỉ ghi
  một phần ngày (vd "ngày 30 tháng … năm 202…") là CHƯA đủ → để trống.
</residence_rules>

<owner_rules>
- ChuSoHuu_* là CHỦ SỞ HỮU CHỖ Ở hợp pháp (người cho thuê/cho mượn/cho ở nhờ), KHÔNG phải người đăng ký tạm trú.
- Thứ tự nguồn: Tờ khai CT01 ô "Ý KIẾN CỦA CHỦ SỞ HỮU CHỖ Ở HỢP PHÁP" ("(8) Họ và tên", "(8) Số định danh cá nhân")
  → hợp đồng phần "BÊN CHO THUÊ (Bên A)" (Ông/bà, CCCD số) → Giấy chứng nhận quyền sử dụng đất mục I
  ("Ông/Bà: …", "CMND số"/"CCCD số", "Năm sinh").
- ChuSoHuu_SoDinhDanh chỉ nhận số 12 chữ số (nhãn có thể ghi "CMND số" nhưng là số căn cước 12 số).
- ChuSoHuu_NgaySinh: đủ ngày tháng năm thì dd/mm/yyyy; giấy chỉ có năm sinh thì chỉ trả năm (vd "1975"), không bịa ngày.
- Người đăng ký tự là chủ sở hữu (không có bên cho thuê, tên trên GCN trùng người đăng ký) → để trống ChuSoHuu_*.
</owner_rules>"""
