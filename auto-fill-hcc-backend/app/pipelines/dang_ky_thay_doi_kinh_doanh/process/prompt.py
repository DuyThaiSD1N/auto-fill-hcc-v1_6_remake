"""Quy tắc đọc hồ sơ thay đổi đăng ký hộ kinh doanh."""

EXTRA_RULES = """
Bạn đang trích xuất hồ sơ "Đăng ký thay đổi nội dung đăng ký hộ kinh doanh".

PHÂN BIỆT NGUỒN:
- "Thông báo thay đổi nội dung đăng ký hộ kinh doanh" là nguồn duy nhất để biết NỘI DUNG ĐỀ NGHỊ THAY ĐỔI.
- "Giấy chứng nhận đăng ký hộ kinh doanh" là nguồn trạng thái HIỆN TẠI và mã hộ kinh doanh.
- CCCD/căn cước chỉ là nguồn nhân thân; không dùng CCCD để kết luận người đó là chủ hộ hay người nộp.
- Không coi thông tin hiện tại được nhắc lại ở phần đầu Thông báo là nội dung thay đổi. Chỉ trả DeNghi_* khi mục tương ứng được đánh dấu/kê khai là thay đổi.

QUY TẮC BẮT BUỘC:
1. HoKinhDoanh_MaSo:
   ⛔ ANTI-PATTERN — SAI TUYỆT ĐỐI:
     Số định danh cá nhân / CCCD / CMND (xuất hiện cạnh nhãn "Số/No", "Số định danh",
     "Số CMND" trên thẻ căn cước hoặc trong tờ khai cá nhân) KHÔNG BAO GIỜ là mã số
     hộ kinh doanh — dù số đó đứng ở đâu trong hồ sơ.
     Nếu hồ sơ KHÔNG có tài liệu kinh doanh ghi nhãn "Mã số hộ kinh doanh" / "MST" / "Số đăng ký"
     → HoKinhDoanh_MaSo = "" (TRỐNG hoàn toàn, không điền bất cứ con số nào).
   ✅ Nguồn HỢP LỆ DUY NHẤT:
     * Thông báo thay đổi hoặc GCN đăng ký HKD có NHÃN RÕ "Mã số hộ kinh doanh" / "MST".
     * Giấy đề nghị đăng ký hộ kinh doanh nếu có in mã số.
   Giữ nguyên chữ số, bỏ khoảng trắng và dấu gạch ngang khi lấy mã.
2. Tên: HienTai_Ten từ GCN. DeNghi_Ten chỉ có khi hồ sơ thật sự đổi tên; không trả lại cùng tên chỉ vì tên xuất hiện ở tiêu đề/thông tin nhận diện.
3. Ngành nghề:
   - HienTai_NganhNghe chỉ gồm ngành trên GCN.
   - DeNghi_NganhNgheBoSung chỉ gồm dòng ở mục bổ sung. Dòng có tên nhưng không có mã vẫn phải giữ với ma="".
   - DeNghi_NganhNgheBaiBo chỉ gồm dòng ở mục bỏ. Mã ngành phải là đúng 4 chữ số; OCR "47 19"/"47.19" -> "4719".
   - Không biến toàn bộ danh sách hiện tại thành danh sách bổ sung/bãi bỏ.
4. Đổi chủ hộ: DeNghi_ChuHo chỉ có khi đúng mục "Đăng ký thay đổi chủ hộ kinh doanh" được kê khai. Các dòng "trước khi thay đổi" và "sau khi thay đổi" phải tách đúng người.
5. Địa chỉ/vốn/thuế: chỉ trả DeNghi_* khi đúng mục thay đổi đó được kê khai. Việc GCN và Thông báo cùng in lại một giá trị không đủ để kết luận thay đổi.
6. NguoiNop: lấy người ký/người nộp ghi trên Thông báo hoặc người được ủy quyền. Nếu không xác định chắc thì để trống; mapper/extension sẽ đối chiếu với thông tin tài khoản sau khi bấm Sao chép.
   - ĐỊA CHỈ NguoiNop: Sau khi xác định người nộp (qua họ tên hoặc số định danh), TÌM trong Cccd_DanhSach
     xem có thẻ CCCD nào khớp với người đó không. Nếu có → BẮT BUỘC lấy diaChi từ "Nơi thường trú"
     trên thẻ CCCD đó điền vào NguoiNop.diaChi.
   - Ví dụ: Thông báo ký bởi "NGUYỄN VĂN A" (khác chủ hộ); hồ sơ có CCCD của người này
     ghi "Nơi thường trú: Tổ 1, Phường X, Quận Y, Thành phố Z" → NguoiNop.diaChi =
     {quocGia:"Việt Nam", tinh:"Thành phố Z", xa:"Phường X", diaChi:"Tổ 1"}.
   - KHÔNG lấy địa chỉ từ Quê quán, từ GCN hay từ phần chủ hộ cho NguoiNop khi đã có CCCD khớp.
7. Cccd_DanhSach: liệt kê mọi thẻ căn cước vật lý, mỗi thẻ một object; không suy vai trò từ tên file hoặc thứ tự upload.
   
   ⚠️⚠️⚠️ ĐỊA CHỈ TỪ CCCD - QUY TẮC BẮT BUỘC - CỰC KỲ QUAN TRỌNG ⚠️⚠️⚠️
   
   KHI ĐỌC ĐỊA CHỈ TỪ CCCD, BẠN PHẢI:
   
   ✅ CHỈ LẤY TỪ DÒNG "Nơi thường trú / Place of residence"
   ❌ TUYỆT ĐỐI KHÔNG LẤY TỪ "Quê quán / Place of origin"
   
   VÍ DỤ CỤ THỂ - CCCD CÓ 2 DÒNG:
   - Dòng "Quê quán": "Xã A, Huyện B, Tỉnh C"  ← BỎ QUA, KHÔNG LẤY
   - Dòng "Nơi thường trú": "Tổ D, Phường E, Quận F, Thành phố G"  ← LẤY DÒNG NÀY
   
   → Output ĐÚNG:
   {
     "tinh": "Thành phố G",  ← từ "Nơi thường trú"
     "xa": "Phường E",
     "diaChi": "Tổ D"
   }
   
   → Output SAI (TUYỆT ĐỐI TRÁNH):
   {
     "tinh": "Tỉnh C",  ← SAI vì lấy từ "Quê quán"
     "xa": "Xã A"
   }
   
   CÁCH PHÂN BIỆT TRÊN CCCD:
   - Trên CCCD tiếng Việt: Tìm dòng BẮT ĐẦU bằng "Nơi thường trú"
   - Trên CCCD song ngữ: Tìm dòng có "Place of residence" (không phải "Place of origin")
   - Dòng "Nơi thường trú" LUÔN Ở DƯỚI dòng "Quê quán"
8. Địa chỉ object luôn là {quocGia,tinh,xa,diaChi}; diaChi không lặp tỉnh/xã. Không bịa field bị trống.

⚠️ PHÁT HIỆN NHIỀU CCCD/GIẤY TỜ TÙY THÂN TRONG HỒ SƠ:

**HasMultipleCCCD**: Đếm số CCCD/CMND/giấy tùy thân trong hồ sơ.
- Nếu CHỈ có 1 CCCD → trả HasMultipleCCCD = false
- Nếu có 2+ CCCD → trả HasMultipleCCCD = true

**⚠️ QUY TẮC BẮT BUỘC KHI CÓ 2+ CCCD:**
Khi phát hiện HasMultipleCCCD = true, BẮT BUỘC phải:
1. Xác định CCCD nào là của CHỦ HỘ (so với Thông báo hoặc GCN)
2. Xác định CCCD còn lại là của ai
- 📄 GIẤY ỦY QUYỀN — NGUỒN NHÂN THÂN CỦA NGƯỜI NỘP THAY:
  + Nhận diện qua tiêu đề "GIẤY ỦY QUYỀN"/"VĂN BẢN ỦY QUYỀN" và hai mục "Bên ủy quyền" / "Bên được ủy quyền".
  + "Bên ủy quyền" (người giao việc, thường là chủ hộ) → UyQuyen_NguoiUyQuyen_HoTen, UyQuyen_NguoiUyQuyen_SoDinhDanh.
  + "Bên được ủy quyền" (NGƯỜI ĐI NỘP HỒ SƠ THAY) → UyQuyen_NguoiDuocUyQuyen_HoTen, _SoDinhDanh,
    _GioiTinh, _NgaySinh, _DienThoai, _DiaChi. Trả UyQuyen_CoGiayUyQuyen = true.
  + Người nộp thay RẤT HAY chỉ xuất hiện trong giấy ủy quyền, hồ sơ KHÔNG kèm CCCD của họ.
    Khi đó VẪN PHẢI điền đủ nhóm UyQuyen_NguoiDuocUyQuyen_* từ chính giấy ủy quyền.
  + Nếu hồ sơ CÓ CCCD của bên được ủy quyền: ưu tiên nhân thân + "Nơi thường trú" trên THẺ;
    giấy ủy quyền chỉ bù các field thẻ không có (vd số điện thoại).
  + ⛔ KHÔNG đưa người chỉ có trong giấy ủy quyền vào Cccd_DanhSach — danh sách đó CHỈ dành cho thẻ
    căn cước vật lý. Nhân thân của họ đi qua nhóm UyQuyen_* .
  + UyQuyen_NguoiDuocUyQuyen_DiaChi tách chuẩn {quocGia,tinh,xa,diaChi} và BỎ cấp huyện:
    "Thôn Lạc Lâm, Xã Ka Đô, Tỉnh Lâm Đồng" → diaChi="Thôn Lạc Lâm", xa="Ka Đô", tinh="Lâm Đồng".
  + KHÔNG suy ai đang nộp hồ sơ từ giấy ủy quyền — hệ thống tự đối chiếu nhân thân này với tài khoản
    đăng nhập trên cổng (khớp số định danh hoặc họ tên) y như cách đối chiếu CCCD.

3. Nếu CCCD còn lại KHÁC chủ hộ (khác cả số và tên) → ĐIỀN ĐẦY ĐỦ các field UyQuyen_*
4. KHÔNG ĐƯỢC bỏ trống các field UyQuyen_* khi đã xác định có người ủy quyền

**KHI CÓ 2+ CCCD - LOGIC XÁC ĐỊNH CHỦ HỘ VÀ NGƯỜI ỦY QUYỀN:**

+ **BƯỚC 1 - XÁC ĐỊNH AI LÀ CHỦ HỘ:**
  Ưu tiên xác định theo THÔNG BÁO THAY ĐỔI hoặc GIẤY CHỨNG NHẬN:
  - Đọc họ tên và số CCCD của CHỦ HỘ từ Thông báo hoặc GCN (phần "Chủ hộ kinh doanh")
  - So sánh với CÁC CCCD trong hồ sơ:
    * CCCD nào có SỐ ĐỊNH DANH KHỚP với số CCCD trên Thông báo/GCN → ĐÓ LÀ CHỦ HỘ
    * Nếu không khớp số, so sánh HỌ TÊN: CCCD nào khớp tên → ĐÓ LÀ CHỦ HỘ
  - CCCD còn lại → là NGƯỜI ĐƯỢC ỦY QUYỀN (người đi nộp hồ sơ thay)

+ **BƯỚC 2 - ĐIỀN THÔNG TIN CHỦ HỘ:**
  - Lấy từ CCCD của CHỦ HỘ (đã xác định ở bước 1)
  - Nếu có mục thay đổi chủ hộ: dùng thông tin CHỦ HỘ MỚI

+ **BƯỚC 3 - ĐIỀN THÔNG TIN NGƯỜI ỦY QUYỀN:**
  - Nếu CCCD còn lại có CẢ số định danh VÀ họ tên KHÁC với chủ hộ:
    → ĐÓ LÀ NGƯỜI ĐƯỢC ỦY QUYỀN
    → BẮT BUỘC điền ĐẦY ĐỦ:
      * UyQuyen_NguoiDuocUyQuyen_HoTen (từ CCCD người ủy quyền)
      * UyQuyen_NguoiDuocUyQuyen_SoDinhDanh (từ CCCD người ủy quyền)
      * UyQuyen_NguoiDuocUyQuyen_GioiTinh (từ CCCD người ủy quyền)
      * UyQuyen_NguoiDuocUyQuyen_NgaySinh (từ CCCD người ủy quyền)
      * UyQuyen_NguoiDuocUyQuyen_DiaChi (từ CCCD người ủy quyền - BẮT BUỘC lấy "Nơi thường trú", KHÔNG lấy "Quê quán")
      * UyQuyen_NguoiUyQuyen_HoTen = tên CHỦ HỘ (từ Thông báo/GCN)
      * UyQuyen_NguoiUyQuyen_SoDinhDanh = số CCCD CHỦ HỘ (từ Thông báo/GCN)
      * UyQuyen_CoGiayUyQuyen = true (nếu có giấy ủy quyền văn bản) hoặc false (chỉ có 2 CCCD)
  
  - Nếu CCCD còn lại có số CCCD KHỚP HOẶC họ tên KHỚP với CHỦ HỘ:
    → Coi như CÙNG NGƯỜI (chủ hộ có 2 CCCD cũ/mới, hoặc chủ hộ tự nộp)
    → KHÔNG điền các field UyQuyen_*
    → Trả UyQuyen_CoGiayUyQuyen = false

+ **LƯU Ý QUAN TRỌNG:**
  - So sánh HỌ TÊN phải chuẩn hóa (bỏ dấu, chữ thường, bỏ khoảng trắng thừa)
  - Ví dụ: "NGUYỄN VĂN A" = "Nguyen Van A" = "nguyễn văn a"
  - PHẢI điền ĐẦY ĐỦ thông tin người ủy quyền, KHÔNG được bỏ field nào

+ **VÍ DỤ CỤ THỂ:**
  
  INPUT HỒ SƠ:
  - Thông báo: Chủ hộ "TRẦN VĂN A", CCCD: 001234567890
  - CCCD 1: Số 001234567890, tên "TRẦN VĂN A", sinh 01/01/1980, Nam, nơi thường trú "123 Nguyễn Văn Linh, Phường 1, TP.HCM"
  - CCCD 2: Số 098765432109, tên "NGUYỄN THỊ B", sinh 15/05/1985, Nữ, nơi thường trú "456 Lê Lợi, Phường 2, Hà Nội"
  
  PHÂN TÍCH:
  1. Chủ hộ là "TRẦN VĂN A" (001234567890) theo Thông báo
  2. CCCD 2 (098765432109 "NGUYỄN THỊ B") ≠ CCCD chủ hộ → NGƯỜI ỦY QUYỀN
  3. Điền đầy đủ thông tin ủy quyền
  
  OUTPUT:
  {
    "HasMultipleCCCD": true,
    "UyQuyen_CoGiayUyQuyen": false,
    "UyQuyen_NguoiUyQuyen_HoTen": "TRẦN VĂN A",
    "UyQuyen_NguoiUyQuyen_SoDinhDanh": "001234567890",
    "UyQuyen_NguoiDuocUyQuyen_HoTen": "NGUYỄN THỊ B",
    "UyQuyen_NguoiDuocUyQuyen_SoDinhDanh": "098765432109",
    "UyQuyen_NguoiDuocUyQuyen_GioiTinh": "Nữ",
    "UyQuyen_NguoiDuocUyQuyen_NgaySinh": "15/05/1985",
    "UyQuyen_NguoiDuocUyQuyen_DiaChi": {
      "quocGia": "Việt Nam",
      "tinh": "Hà Nội",
      "xa": "Phường 2",
      "diaChi": "456 Lê Lợi"
    }
  }

Không trả tên field UI ctl00$C$...; chỉ trả các field compact trong schema.
"""
