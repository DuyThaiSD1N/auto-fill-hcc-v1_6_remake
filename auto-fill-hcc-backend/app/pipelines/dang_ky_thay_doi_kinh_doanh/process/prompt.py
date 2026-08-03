"""Quy tắc đọc hồ sơ thay đổi đăng ký hộ kinh doanh."""

EXTRA_RULES = """
Bạn đang trích xuất hồ sơ "Đăng ký thay đổi nội dung đăng ký hộ kinh doanh".

PHÂN BIỆT NGUỒN:
- "Thông báo thay đổi nội dung đăng ký hộ kinh doanh" là nguồn duy nhất để biết NỘI DUNG ĐỀ NGHỊ THAY ĐỔI.
- "Giấy chứng nhận đăng ký hộ kinh doanh" là nguồn trạng thái HIỆN TẠI và mã hộ kinh doanh.
- CCCD/căn cước chỉ là nguồn nhân thân; không dùng CCCD để kết luận người đó là chủ hộ hay người nộp.
- Không coi thông tin hiện tại được nhắc lại ở phần đầu Thông báo là nội dung thay đổi. Chỉ trả DeNghi_* khi mục tương ứng được đánh dấu/kê khai là thay đổi.

QUY TẮC BẮT BUỘC:
1. HoKinhDoanh_MaSo: ưu tiên dãy mã hộ kinh doanh/mã số thuế trên Thông báo; giữ nguyên chữ số, bỏ khoảng trắng.
2. Tên: HienTai_Ten từ GCN. DeNghi_Ten chỉ có khi hồ sơ thật sự đổi tên; không trả lại cùng tên chỉ vì tên xuất hiện ở tiêu đề/thông tin nhận diện.
3. Ngành nghề:
   - HienTai_NganhNghe chỉ gồm ngành trên GCN.
   - DeNghi_NganhNgheBoSung chỉ gồm dòng ở mục bổ sung. Dòng có tên nhưng không có mã vẫn phải giữ với ma="".
   - DeNghi_NganhNgheBaiBo chỉ gồm dòng ở mục bỏ. Mã ngành phải là đúng 4 chữ số; OCR "47 19"/"47.19" -> "4719".
   - Không biến toàn bộ danh sách hiện tại thành danh sách bổ sung/bãi bỏ.
4. Đổi chủ hộ: DeNghi_ChuHo chỉ có khi đúng mục "Đăng ký thay đổi chủ hộ kinh doanh" được kê khai. Các dòng "trước khi thay đổi" và "sau khi thay đổi" phải tách đúng người.
5. Địa chỉ/vốn/thuế: chỉ trả DeNghi_* khi đúng mục thay đổi đó được kê khai. Việc GCN và Thông báo cùng in lại một giá trị không đủ để kết luận thay đổi.
6. NguoiNop: lấy người ký/người nộp ghi trên Thông báo hoặc người được ủy quyền. Nếu không xác định chắc thì để trống; mapper/extension sẽ đối chiếu với thông tin tài khoản sau khi bấm Sao chép.
7. Cccd_DanhSach: liệt kê mọi thẻ căn cước vật lý, mỗi thẻ một object; không suy vai trò từ tên file hoặc thứ tự upload.
8. Địa chỉ object luôn là {quocGia,tinh,xa,diaChi}; diaChi không lặp tỉnh/xã. Không bịa field bị trống.

Không trả tên field UI ctl00$C$...; chỉ trả các field compact trong schema.
"""
