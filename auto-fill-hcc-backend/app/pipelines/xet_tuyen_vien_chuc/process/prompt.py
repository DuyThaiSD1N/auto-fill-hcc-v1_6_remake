"""Procedure-specific compact prompt rules for "Thủ tục xét tuyển Viên chức"."""

EXTRA_RULES = """<critical_rules>
1. Phiếu đăng ký dự tuyển là nguồn chính để xác định CHỦ HỒ SƠ/người đăng ký dự tuyển.
2. Không dùng CCCD người nộp để thay thế chủ hồ sơ nếu phiếu đăng ký đã có thông tin người dự tuyển.
3. Không trả field UI dạng data[...]; chỉ trả field nguồn trong schema.
4. Không bịa. Không chắc field nào thì bỏ field đó.
</critical_rules>

<document_classification>
1. Nhận diện "Phiếu đăng ký dự tuyển" theo tiêu đề/cụm "PHIẾU ĐĂNG KÝ DỰ TUYỂN", "Mẫu số 01",
   "Nghị định số 85/2023/NĐ-CP", "Nghị định số 115/2020/NĐ-CP", hoặc nội dung kê khai dự tuyển viên chức.
2. Nhận diện CCCD/CMND/thẻ căn cước/hộ chiếu độc lập theo tiêu đề giấy tờ định danh, số định danh,
   ngày sinh, giới tính, nơi thường trú và mặt sau ngày cấp/nơi cấp.
3. Tên file chỉ là tín hiệu phụ; OCR là nguồn chính.
</document_classification>

<phieu_dang_ky_extraction>
1. Trích nhóm Phieu_* từ chính Phiếu đăng ký dự tuyển.
2. Phieu_HoTen là họ tên người đăng ký dự tuyển/chủ hồ sơ, không phải người ký thay hay người nộp hộ.
3. Phieu_SoDinhDanh lấy từ dòng số CCCD/CMND/hộ chiếu của người đăng ký dự tuyển.
4. Phieu_HoKhau lấy từ mục "Thông tin về hộ khẩu" hoặc nhãn tương đương như hộ khẩu thường trú.
5. Phieu_DiaChiNhanThongBao lấy từ mục "địa chỉ nhận thông báo"/"địa chỉ liên hệ"; chỉ trích riêng,
   không tự quyết fallback trong LLM.
6. Với địa chỉ object: quocGia mặc định "Việt Nam" nếu là địa chỉ trong nước; tinh là tỉnh/thành phố;
   xa là xã/phường/thị trấn nếu đọc được; diaChi chỉ giữ số nhà/tổ/thôn/bản/khu/xóm, không lặp xã/huyện/tỉnh.
7. Nếu địa chỉ chỉ có một chuỗi dài, vẫn cố tách tỉnh và xã từ cuối chuỗi; bỏ cấp huyện cũ nếu xuất hiện giữa xã và tỉnh.
</phieu_dang_ky_extraction>

<cccd_extraction>
1. Tự gộp mặt trước và mặt sau của cùng một CCCD thành cùng một Person* theo số định danh/MRZ/họ tên.
2. Nếu có một CCCD: trả Person1_*. Nếu có hai CCCD khác nhau: trả Person1_* và Person2_*.
3. Mỗi nhóm Person* phải lấy từ đúng một người, không trộn dữ liệu giữa hai CCCD.
4. Bắt buộc cố đọc Person*_NgayCap từ mặt sau nếu OCR có. Không lấy ngày sinh hay ngày hết hạn làm ngày cấp.
5. Bắt buộc cố đọc Person*_NoiCap từ mặt sau nếu OCR có. Nếu thấy "CỤC TRƯỞNG CỤC CẢNH SÁT..." thì trả
   "Cục Cảnh sát quản lý hành chính về trật tự xã hội". Nếu là thẻ căn cước mới ghi "BỘ CÔNG AN" thì trả "Bộ Công an".
6. Person*_NoiCuTru là địa chỉ trên CCCD, object {quocGia,tinh,xa,diaChi}; diaChi không lặp xã/huyện/tỉnh.
</cccd_extraction>

<role_boundary>
1. LLM không cần quyết định người nộp là ai hay chủ hồ sơ là ai. Python sẽ so sánh Phieu_* với formContext của UI.
2. Vì vậy không được đổi tên Phieu_* thành Person* và không được suy role từ thứ tự upload.
</role_boundary>

<output_examples>
Đúng:
{"fields":{"Phieu_HoTen":"LÒ THỊ XUYÊN","Phieu_SoDinhDanh":"012345678901","Phieu_HoKhau":{"quocGia":"Việt Nam","tinh":"Lai Châu","xa":"Tân Phong","diaChi":"Tổ 9"},"Person1_HoTen":"VŨ ĐÌNH THIẾT","Person1_SoDinhDanh":"040203015844"}}

Sai:
{"fields":{"data[ownerFullname]":"LÒ THỊ XUYÊN","Phieu_HoTen":"VŨ ĐÌNH THIẾT"}}
Lý do sai: trả field UI data[...] và lấy người nộp làm Phieu_HoTen.
</output_examples>"""
