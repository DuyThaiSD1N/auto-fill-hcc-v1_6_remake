"""Field thật của biểu mẫu liên thông khai tử (lienthong.dichvucong.gov.vn, Angular).

Không có FIELDS compact riêng: cùng bộ giấy tờ với "khai-tu" (tờ khai, giấy báo tử, CCCD) nên
phần trích xuất dùng nguyên schema/prompt của app.pipelines.khai_tu.process.

Nguồn tên field: bảng mapping BA "126_Liên thông khai tử- Quảng ngãi" và DOM bước 02 "Kê khai".
Comp theo engine content/fill-angular.js của extension:
- "select": app-input type="select" (mat-select hoặc ng-select), khớp option theo nhãn.
- "date": ô ngày thường (app-input type="date").
- "ngaysinh": ô có mat-select ĐỊNH DẠNG (Ngày/Tháng/Năm · Ngày/Tháng/Năm giờ:phút · Tháng/Năm · Năm)
  rồi mới tới ô ngày. Backend gửi chuỗi "dd/mm/yyyy", "dd/mm/yyyy HH:MM", "mm/yyyy" hoặc "yyyy";
  extension tự chọn định dạng tương ứng và điền thêm ô giờ/phút khi có.
- "diachi": {tinh, xa, diaChi}, extension chọn lần lượt Tỉnh → Phường/Xã → gõ Chi tiết.
- "raw": input số lượng bản sao (component input-type-number).
- "sao-tu-o": không có dữ liệu từ giấy tờ; extension đọc giá trị của một ô khác đang có sẵn trên
  trang rồi điền sang. Ô nào dùng được cả hai cách thì khai tuple (comp khi có giấy tờ, comp khi sao).
"""

UI_COMP_BY_NAME = {
    # I. Người yêu cầu (BA dòng 1-12): cổng đã đổ sẵn từ tài khoản đăng nhập (CSDL dân cư) nên KHÔNG
    # ghi đè bằng dữ liệu OCR — chỉ chọn quan hệ với người chết, ô này cổng để trống.
    "NycQuanHe": "select",
    # II. Người được khai tử.
    "NdktHo": "text",
    "NdktChuDem": "text",
    "NdktTen": "text",
    "NdktNgaySinh": "ngaysinh",
    "NdktGioiTinh": "select",
    "NdktSoGiayto": "text",
    "NdktNgayCapGiayTo": "date",
    "NdktNoiCapGiayTo": "text",
    "NdktMaQuoctich": "select",
    "NdktMaDantoc": "select",
    # Nơi cư trú cuối cùng + thời gian chết.
    "NctccLoaiCutru": "select",
    "NctccMaQuocgia": "select",
    "NctccDiaChi": "diachi",
    "NctccNgayChet": "ngaysinh",
    # Nơi chết + nguyên nhân.
    "NoichetMaQuocgia": "select",
    "NoichetDiachi": "diachi",
    "NguyenNhanChet": "select",
    # Giấy báo tử / giấy thay thế giấy báo tử.
    "GbtLoaiGiayto": "select",
    "GbtSogiayto": "text",
    "GbtNgaycap": "date",
    "GbtNoicap": "text",
    # Đề nghị cấp bản sao: radio value "1" = Có, "0" = Không.
    "CapBanSao": "radio",
    "BanSaoSoluong": "raw",
    # III. Chủ hộ, phần xóa đăng ký thường trú (BA dòng 47-49). Họ tên + số định danh lấy từ chính
    # khối người yêu cầu trên trang (BA ghi giá trị là của người yêu cầu). KHÔNG tự tick ô
    # "Là người kê khai": chủ hộ là dữ kiện hộ khẩu, giấy tờ trong hồ sơ không nói.
    "XoaChuhoHoten": "sao-tu-o",
    "XoaChuhoGiayto": "sao-tu-o",
    "XoaChuhoQuanhe": "select",
    # IV. Người nhận mai táng phí (BA dòng 84-95, 100, 106). Tick "Là người yêu cầu" để cổng tự
    # chuyển toàn bộ danh tính người nhận sang (chính xác hơn gõ lại từ OCR); cán bộ bỏ tick khi
    # người nhận là người khác. Nhánh "Hưởng theo luật BHXH" BA đã bỏ khỏi phạm vi.
    "CanhanIsNyc": "checkbox",
    "NnmtpQqMaQuocgia": "select",
    "NnmtpQuanheNguoichet": "select",
    # Quê quán người có công từ trần (BA dòng 106): chỉ có ở nhánh "Người có công".
    "NccQqMaQuocgia": "select",
}
