"""Procedure-specific compact prompt rules for "Thi tuyển công chức"."""

EXTRA_RULES = """<critical_rules>
1. Phiếu đăng ký dự tuyển theo Mẫu số 01 hoặc Mẫu số 02 là nguồn chính cho toàn bộ Phieu_*.
2. Không trả field UI dạng data[...]; chỉ trả field nguồn trong schema.
3. Không dùng schema ngắn của xét tuyển viên chức. Thủ tục này cần trích cả vị trí dự tuyển,
   thông tin cá nhân, văn bằng chứng chỉ, ưu tiên và nguyện vọng.
4. Không bịa. Nếu một ô/bảng trong phiếu trống thì bỏ field hoặc trả mảng rỗng; không tự thêm dữ liệu.
</critical_rules>

<document_classification>
1. Nhận diện Phiếu đăng ký dự tuyển công chức theo các cụm: "PHIẾU ĐĂNG KÝ DỰ TUYỂN",
   "PHIẾU ĐĂNG KÝ THI TUYỂN CÔNG CHỨC", "Mẫu số 01", "Mẫu số 02",
   "Nghị định số 170/2025/NĐ-CP", "thi tuyển công chức", hoặc nội dung
   "vị trí việc làm dự tuyển", "cơ quan, tổ chức, đơn vị dự tuyển".
2. Nếu có CCCD/CMND/hộ chiếu riêng, chỉ trích vào Person1_* để bổ sung ngày cấp/nơi cấp/nơi cư trú;
   không thay thế Phieu_* nếu phiếu đã có thông tin ứng viên.
3. Tên file chỉ là tín hiệu phụ; OCR là nguồn chính.
</document_classification>

<phieu_dang_ky_extraction>
1. Phieu_ViTriViecLam lấy từ dòng "Vị trí việc làm dự tuyển".
2. Phieu_CoQuanDuTuyen lấy từ dòng "Cơ quan, tổ chức, đơn vị dự tuyển".
3. Phieu_HoTen, Phieu_NgaySinh, Phieu_GioiTinh, Phieu_SoDinhDanh, Phieu_NgayCap,
   Phieu_NoiCap, Phieu_TonGiao, Phieu_DanToc, Phieu_DienThoai, Phieu_Email lấy từ Mục I.
4. Địa chỉ Phieu_QueQuan, Phieu_NoiThuongTru, Phieu_NoiOHienTai phải là object
   {quocGia,tinh,xa,diaChi}. quocGia mặc định "Việt Nam"; tinh giữ đủ "Tỉnh ..."/"Thành phố ...";
   xa giữ đủ "Xã ..."/"Phường ..."; diaChi chỉ giữ thôn/bản/tổ/số nhà/đường, không lặp xã/huyện/tỉnh.
5. Khi tách địa chỉ nhiều phần, phần tỉnh/thành phố là đơn vị hành chính cấp tỉnh ở cuối chuỗi;
   phần xã/phường/thị trấn là đơn vị hành chính cấp xã ngay trước tỉnh hoặc phần có tiền tố
   "xã", "phường", "thị trấn", "TT". Chỉ các phần còn lại trước cấp xã mới được đưa vào diaChi.
6. Nếu địa chỉ chỉ có 2 phần và phần đầu là xã/phường/thị trấn, đặt phần đầu vào xa,
   phần sau vào tinh, và để diaChi rỗng; không đưa xã/phường/thị trấn vào diaChi.
7. Phieu_NoiDungKhac chỉ lấy nội dung phát sinh riêng ở Mục VI nếu thí sinh có ghi thêm yêu cầu/nội dung khác.
   Không lấy đoạn cam đoan pháp lý mặc định bắt đầu bằng "Tôi xin cam đoan...", chữ ký, hướng dẫn hoặc chú thích cuối mẫu.
   Nếu Mục VI không có nội dung riêng ngoài cam đoan mặc định thì bỏ field này.
8. Phieu_TinhTrangSucKhoe, Phieu_ChieuCao, Phieu_CanNang, Phieu_TrinhDoVanHoa,
   Phieu_TrinhDoChuyenMon lấy đúng từ Mục I.
</phieu_dang_ky_extraction>

<tables>
1. Phieu_VanBangChungChi là mảng tất cả dòng trong bảng "II. Văn bằng, chứng chỉ";
   mỗi item có đúng các key: tenTruong, ngayCap, trinhDo, soHieu, chuyenNganh, nganh, hinhThuc, xepLoai.
2. Không được chỉ lấy dòng đầu nếu OCR có nhiều dòng văn bằng/chứng chỉ.
3. Phieu_QuaTrinhCongTac là mảng dòng trong bảng "III. Quá trình công tác"; nếu không có thì bỏ field.
4. Phieu_ThuTuUuTien là mảng dòng trong mục "V. Thứ tự ưu tiên"; mỗi item có tenCoQuan và nguyenVong.
5. Ngày trong bảng dùng dd/mm/yyyy, ví dụ "29/03/2018".
</tables>

<priority_and_confirmation>
1. Phieu_NgoaiNgu lấy từ dòng ngoại ngữ thi nếu có, để trống thì bỏ field.
2. Phieu_CoDoiTuongUuTien chỉ trả "Có" hoặc "Không".
3. Phieu_DoiTuongUuTien lấy nguyên nội dung ưu tiên, ví dụ "Là người dân tộc thiểu số, sinh viên cử tuyển".
4. Phieu_DiemUuTien chỉ trả số điểm.
5. Không cần trích checkbox xác nhận hình thức nhận thông báo; Python sẽ tự tick XacNhan.
</priority_and_confirmation>

<cccd_extraction>
1. Nếu OCR có CCCD/CMND độc lập, trả Person1_* theo đúng người trên giấy tờ.
2. Person1_NgayCap không được lấy ngày sinh/ngày hết hạn. Nếu thấy "Công an tỉnh ..." thì giữ đúng.
3. Person1_NoiCuTru là object {quocGia,tinh,xa,diaChi}.
</cccd_extraction>

<output_examples>
Đúng:
{"fields":{"Phieu_HoTen":"Vàng Thị Thu","Phieu_SoDinhDanh":"012194003716","Phieu_NoiThuongTru":{"quocGia":"Việt Nam","tinh":"Tỉnh Hưng Yên","xa":"Xã Hưng Hà","diaChi":"Thôn Đồng Hàn"},"Phieu_VanBangChungChi":[{"tenTruong":"ĐH Kinh tế Quốc dân","ngayCap":"29/03/2018","trinhDo":"Cử nhân","soHieu":"0700-MT56","chuyenNganh":"Kinh tế - Quản lý tài nguyên và môi trường","nganh":"Kinh tế","hinhThuc":"Chính quy","xepLoai":"Khá"}]}}

Sai:
{"fields":{"data[fullname]":"Vàng Thị Thu","DataGrid[0].tenTruong":"ĐH Kinh tế Quốc dân"}}
Lý do sai: trả field UI/data grid UI thay vì field nguồn Phieu_*.
</output_examples>"""
