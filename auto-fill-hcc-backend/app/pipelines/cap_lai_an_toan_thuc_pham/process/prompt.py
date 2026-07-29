"""Procedure-specific compact prompt rules for ATTP certificate reissue."""

EXTRA_RULES = """<critical_rules>
1. Chỉ trả field nguồn trong schema. Không trả field UI dạng data[...].
2. Đơn đề nghị cấp lại là nguồn chính cho số/ngày GCN cũ, tên cơ sở, lý do cấp lại, ngày đơn, kính gửi và người ký.
3. Khi có nhiều GCN ATTP trong hồ sơ, ưu tiên GCN được nhắc trực tiếp trong Đơn đề nghị cấp lại. Không lấy nhầm GCN chuỗi hoặc GCN cấp lại mới hơn làm GCNCu_* nếu đơn đã ghi GCN cũ.
4. Giấy ủy quyền chỉ dùng để xác định bên ủy quyền/bên được ủy quyền; không dùng tên file để quyết định vai trò.
5. Không bịa. Không chắc field nào thì bỏ field đó.
</critical_rules>

<document_classification>
1. Nhận diện Đơn đề nghị cấp lại theo tiêu đề "ĐƠN ĐỀ NGHỊ", "Cấp lại Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm", các dòng "Kính gửi", "Tên cơ sở", "Giấy chứng nhận cũ đã được cấp số", "Lý do xin cấp lại".
2. Nhận diện GCN ATTP cũ theo tiêu đề "GIẤY CHỨNG NHẬN CƠ SỞ ĐỦ ĐIỀU KIỆN AN TOÀN THỰC PHẨM" và số cấp dạng ".../GCNATTP-...". Nếu tên file hoặc nội dung có chữ "cũ" thì đó là ứng viên GCNCu mạnh.
3. Nhận diện GCN ATTP chuỗi/cấp lại nhưng không ưu tiên cho GCNCu_* nếu đơn đã nêu GCN cũ.
4. Nhận diện Bản thuyết minh CSVC theo tiêu đề "BẢN THUYẾT MINH", các mục "Đại diện cơ sở", "Địa chỉ văn phòng", "Địa chỉ cơ sở kinh doanh", "Điện thoại".
5. Nhận diện Giấy ủy quyền theo tiêu đề "GIẤY ỦY QUYỀN", các mục "Bên ủy quyền", "Bên được ủy quyền".
6. Nhận diện giấy đăng ký doanh nghiệp/chi nhánh/địa điểm kinh doanh theo "GIẤY CHỨNG NHẬN ĐĂNG KÝ...", "Mã số doanh nghiệp", "Mã số chi nhánh", "Địa điểm kinh doanh".
</document_classification>

<don_cap_lai_extraction>
1. DonCapLai_DiaDanh và DonCapLai_NgayDon lấy từ dòng địa danh/ngày ở đầu đơn, ví dụ "Lai Châu, ngày 15 tháng 9 năm 2025" -> DiaDanh "Lai Châu", NgayDon "15/09/2025".
2. DonCapLai_KinhGui giữ đủ các cơ quan trong phần "Kính gửi", nối bằng "; " nếu có nhiều dòng.
3. DonCapLai_TenCoSo lấy từ dòng "Tên cơ sở". Nếu sau tên có "Địa chỉ:" thì tách phần trước làm tên, phần sau làm DonCapLai_DiaChiCoSo.
4. DonCapLai_GCNCuSo lấy từ cụm "Giấy chứng nhận cũ đã được cấp số". Giữ đúng số đầy đủ như "05/2022/GCNATTP-SCT".
5. DonCapLai_NgayCapGCNCu lấy từ "ngày cấp" gắn với GCN cũ, không lấy ngày đơn, ngày ký số hoặc ngày hết hạn.
6. DonCapLai_LyDoCapLai lấy nguyên lý do sau nhãn "Lý do xin cấp lại Giấy chứng nhận".
7. DonCapLai_NguoiKy lấy họ tên dưới phần "ĐẠI DIỆN CƠ SỞ" hoặc chữ ký cuối đơn, không lấy tên người ký số của Sở.
8. DonCapLai_NoiDungYeuCau chỉ trả khi đọc được nội dung đề nghị cấp lại; nếu chỉ có tiêu đề đơn thì có thể trả "Đề nghị cấp lại Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm".
</don_cap_lai_extraction>

<facility_extraction>
1. CoSo_TenCoSo ưu tiên theo thứ tự: DonCapLai_TenCoSo, giấy đăng ký địa điểm/chi nhánh/doanh nghiệp, GCN ATTP cũ, bản thuyết minh.
2. CoSo_MaSoThue lấy từ giấy đăng ký hoặc dòng "Giấy chứng nhận đăng ký kinh doanh" trong giấy tập huấn/thuyết minh nếu có; giữ cả hậu tố chi nhánh như "0104918404-094".
3. CoSo_DiaChi ưu tiên địa chỉ cơ sở kinh doanh/địa điểm kinh doanh; không thay bằng địa chỉ văn phòng nếu đã có địa chỉ cơ sở.
4. CoSo_DienThoai có thể là số bàn hoặc di động; giữ số rõ ràng, bỏ dấu chấm/khoảng trắng nếu OCR tách.
5. Nếu tài liệu ghi cả địa chỉ cũ và địa chỉ "nay là", giữ chuỗi địa chỉ đầy đủ hoặc địa chỉ hiện tại đọc chắc chắn; không tự sửa tên phường nếu không chắc.
6. Nếu chủ hồ sơ là cơ sở/doanh nghiệp/chi nhánh/địa điểm kinh doanh, CCCD của người đại diện chỉ là dữ liệu người đại diện; không biến nó thành mã định danh của chính chủ hồ sơ.
</facility_extraction>

<authorization_rules>
1. UyQuyen_BenUyQuyen_* lấy từ mục "I. BÊN ỦY QUYỀN"; đây thường là người đứng đầu/đại diện cơ sở.
2. UyQuyen_BenDuocUyQuyen_* lấy từ mục "II. BÊN ĐƯỢC ỦY QUYỀN"; đây thường là người có thể nộp hồ sơ thay.
3. Ngày cấp/nơi cấp của mỗi bên phải lấy trong cùng dòng hoặc cùng mục với người đó, không trộn giữa hai bên.
</authorization_rules>

<gcn_old_rules>
1. GCNCu_SoCap lấy từ dòng "Số cấp" trên GCN cũ. Nếu số tách dòng như "05" và "/2022/GCNATTP-SCT", ghép thành "05/2022/GCNATTP-SCT".
2. GCNCu_NgayCap lấy từ ngày ký/cấp GCN, không lấy ngày hết hạn.
3. GCNCu_TenCoSo, GCNCu_DiaChiCoSo, GCNCu_DienThoai lấy từ nội dung chứng nhận cơ sở/địa điểm kinh doanh.
4. GCNCu_ChuCoSoHoTen và GCNCu_SoDinhDanhChuCoSo lấy từ dòng "Người đại diện", "Chủ cơ sở" nếu có.
</gcn_old_rules>

<address_and_date_rules>
1. Ngày tháng trả dd/mm/yyyy. "ngày 15 tháng 9 năm 2025" -> "15/09/2025".
2. Địa chỉ object nếu dùng phải có dạng {quocGia,tinh,xa,diaChi}; diaChi không lặp xã/huyện/tỉnh.
3. Với địa chỉ cơ sở/chủ hồ sơ dạng input text, có thể trả chuỗi đầy đủ để Python điền nguyên văn.
</address_and_date_rules>

<output_examples>
Đúng:
{"fields":{"DonCapLai_DiaDanh":"Lai Châu","DonCapLai_NgayDon":"15/09/2025","DonCapLai_KinhGui":"Ủy ban nhân dân tỉnh Lai Châu; Sở Công Thương tỉnh Lai Châu","DonCapLai_TenCoSo":"ĐỊA ĐIỂM KINH DOANH WINMART + LCU 01 - CHI NHÁNH LAI CHÂU - CÔNG TY CỔ PHẦN DỊCH VỤ THƯƠNG MẠI TỔNG HỢP WINCOMMERCE","DonCapLai_GCNCuSo":"05/2022/GCNATTP-SCT","DonCapLai_NgayCapGCNCu":"08/09/2022","DonCapLai_LyDoCapLai":"Hết hạn Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm","DonCapLai_NguoiKy":"PHAN NGUYÊN TRỌNG HUY","ThuyetMinh_DienThoai":"02471066866"}}

Sai:
{"fields":{"data[GCNCuSo]":"6088/GCNATTP-UBND","DonCapLai_GCNCuSo":"11/2023/GCNATTP-SCT"}}
Lý do sai: trả field UI và lấy nhầm GCN chuỗi/cấp lại thay vì GCN cũ được nêu trong đơn.
</output_examples>

<reminder>
Chỉ trả JSON với field nguồn hợp lệ. Đơn đề nghị cấp lại là nguồn ưu tiên cho các trường cấp lại; giấy tờ phụ chỉ fallback khi đơn thiếu.
</reminder>"""
