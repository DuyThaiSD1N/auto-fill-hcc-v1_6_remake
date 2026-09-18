"""Compact schema cho "[Bắc Ninh] Cấp đổi Giấy chứng nhận QSDĐ, QSH tài sản gắn liền với đất".

LLM chỉ trả FACT nguồn từ CCCD người yêu cầu + Đơn đăng ký biến động (Mẫu số 18). UI field
điền vào e-form Bắc Ninh được `mapper.enrich` suy ra tất định.

Cấu trúc = ĐƠN Mẫu 18 (giống dinh_chinh_sai_sot_bac_ninh) + khối NGƯỜI NHẬN KẾT QUẢ (giống
thu_hoi_gcn_cap_sai_bac_ninh). Ô đơn khớp theo NHÃN (title đã fold); ô người nhận khớp theo NAME.
"""

FIELDS: list[dict] = [
    # CCCD/CMND người nộp hồ sơ (người sử dụng đất đứng đơn = người nhận kết quả khi tự nộp).
    {"name": "Cccd_HoTen", "desc": "Họ và tên người nộp hồ sơ (người sử dụng đất đứng đơn) — lấy từ CCCD "
        "hoặc mục a) Tên của Đơn Mẫu 18. Ghi như trên Giấy chứng nhận đã cấp."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh/CCCD/CMND của người đứng đơn; đọc mặt trước, MRZ mặt "
        "sau, hoặc dòng 'CCCD số' trong Đơn."},
    {"name": "Cccd_NgayCap", "desc": "Ngày cấp CCCD/CMND (mặt sau), dd/mm/yyyy. Chỉ có nếu upload CCCD."},
    {"name": "Cccd_NoiCap",
     "desc": 'Nơi cấp CCCD/CMND (mặt sau). "CỤC TRƯỞNG CỤC CẢNH SÁT..." → "Cục Cảnh sát quản lý hành '
             'chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → "Bộ Công an". Chỉ có nếu upload CCCD.'},

    # Địa chỉ người đứng đơn — CHUỖI 1 DÒNG (NGOẠI LỆ quy tắc địa chỉ chung, xem prompt).
    {"name": "Don_DiaChi",
     "desc": "Địa chỉ người đứng đơn — CHUỖI MỘT DÒNG (string), chép NGUYÊN VĂN dòng 'c) Địa chỉ' của Đơn "
             "Mẫu 18. PHẢI giữ ĐỦ tổ dân phố/thôn + phường/xã + tỉnh "
             '(vd "Bản Nậm Dòn, xã Nậm Hàng, tỉnh Lai Châu"). KHÔNG trả object, KHÔNG bỏ phường/xã.'},

    # Đơn đăng ký biến động đất đai (Mẫu số 18) — do công dân tự khai.
    {"name": "Don_KinhGui",
     "desc": 'Cơ quan nhận đơn ghi ở dòng "Kính gửi:" đầu Đơn Mẫu 18 (vd "Chi nhánh VP ĐKĐĐ ..."). '
             'Bỏ ký hiệu chú thích "(1)" ở cuối.'},
    {"name": "Don_DienThoai", "desc": "Số điện thoại liên hệ ghi trên Đơn Mẫu 18 (mục d) nếu có. Chỉ chữ số; "
        "không lấy số điện thoại bàn."},
    {"name": "Don_NoiDungBienDong",
     "desc": 'Nội dung biến động ghi ở mục 2 của Đơn Mẫu số 18, NGUYÊN VĂN — với thủ tục này thường là '
             '"Cấp đổi giấy chứng nhận quyền sử dụng đất". Không tự bịa.'},
    {"name": "Don_GiayTo2",
     "desc": 'Giấy tờ liên quan (2) liệt kê ở mục 3 Đơn Mẫu 18 (dòng "(2) ..."). Bỏ nếu trống. KHÔNG lấy '
             "dòng (1) Giấy chứng nhận đã cấp (dòng in sẵn)."},
    {"name": "Don_GiayTo3",
     "desc": 'Giấy tờ liên quan (3) liệt kê ở mục IV Đơn Mẫu 18 (dòng "(3) ..."). Bỏ nếu trống.'},
    {"name": "Don_MaSoThue", "desc": "Mã số thuế ghi trên Đơn Mẫu 18 (mục '- Mã số thuế (nếu có)'). "
        "Chỉ chữ số. Bỏ nếu đơn để trống."},
    {"name": "Don_Email", "desc": "Hộp thư điện tử ghi trên Đơn Mẫu 18. Bỏ nếu đơn để trống."},
    {"name": "Don_ThanhVienHo",
     "desc": 'Mục V(1) "Thành viên hộ gia đình" của Đơn Mẫu 18 — chép NGUYÊN VĂN họ tên người dân viết '
             '(nhiều người thì giữ nguyên cách liệt kê). Bỏ nếu trống.'},
    {"name": "Don_TinhTrangTranhChap",
     "desc": 'Mục V(2) "Tình trạng tranh chấp đất đai" — chép NGUYÊN VĂN (vd "không"). Bỏ nếu trống.'},
    {"name": "Don_ThayDoiRanhGioi",
     "desc": 'Mục V(3) "Sự thay đổi ranh giới so với ranh giới được cấp Giấy chứng nhận" — chép NGUYÊN '
             'VĂN. Bỏ nếu trống.'},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["Cccd_NgayCap"] = "x-date"

# ---- UI thân đơn (khớp NHÃN = thuộc tính `title` của chính input, đã fold dấu) ----
# ⚠ Cổng ĐÃ ĐỔI BIỂU MẪU Đơn Mẫu 18: nhãn cũ đánh số "a) b) c) d)" và "2. Nội dung biến động" KHÔNG
# còn; nhãn mới dùng gạch đầu dòng và số La Mã. Các hằng dưới đây là title NGUYÊN VĂN lấy từ trang
# thật (thongtin/cấp đổi bắc ninh) — FE `findElementByLabel` ưu tiên khớp CHÍNH XÁC nên sai một ký tự
# là trượt cả ô. Ô đơn ở thủ tục này KHÔNG có class `eform-element-<Key>` ngữ nghĩa (chỉ có
# `eform-element-text`) nên nhãn là đường khớp duy nhất.
L_KINHGUI = "kính"
L_TEN = "- Tên(2)"
L_GIAYTO = "- Giấy tờ nhân thân/pháp nhân"
L_DIACHI = "- Địa chỉ"
L_MST = "- Mã số thuế (nếu có)"
L_DIENTHOAI = "- Điện thoại liên hệ (nếu có)"
L_EMAIL = "Hộp thư điện tử (nếu có)"
L_NOIDUNG = "II. Nội dung biến động(3)"
# Mục IV giấy tờ liên quan: nhãn ô chỉ là "(2)"/"(3)" → engine khớp CHÍNH XÁC (exact) nên không dính
# nhầm "(2) Tình trạng tranh chấp đất đai" / "(3) Sự thay đổi ranh giới…" của mục V.
L_GIAYTO2 = "(2)"
L_GIAYTO3 = "(3)"
# Mục V - Cam kết của chủ sử dụng đất.
L_THANHVIEN = "(1) Thành viên hộ gia đình (5)"
L_TRANHCHAP = "(2) Tình trạng tranh chấp đất đai"
L_RANHGIOI = "(3) Sự thay đổi ranh giới so với ranh giới được cấp Giấy chứng nhận"

# ---- Người nhận kết quả (khớp NAME — id DOM là _org_bn_hoso_noptructuyen_<name>) ----
N_HOTEN = "nhanTaiNhahoTen"
N_CCCD = "nhanTaiNhasoCCCD"
N_SDT = "nhanTaiNhasoDienThoai"
N_DIACHI = "nhanTaiNhadiaChi"

# comp: bn-input (input text), bn-textarea (ô nhiều dòng). FE điền theo NHÃN/NAME.
UI_COMP_BY_NAME = {
    L_KINHGUI: "bn-input",
    L_TEN: "bn-input",
    L_GIAYTO: "bn-input",
    L_DIACHI: "bn-input",
    L_MST: "bn-input",
    L_DIENTHOAI: "bn-input",
    L_EMAIL: "bn-input",
    L_NOIDUNG: "bn-textarea",
    L_GIAYTO2: "bn-input",
    L_GIAYTO3: "bn-input",
    L_THANHVIEN: "bn-input",
    L_TRANHCHAP: "bn-input",
    L_RANHGIOI: "bn-input",
    N_HOTEN: "bn-input",
    N_CCCD: "bn-input",
    N_SDT: "bn-input",
    N_DIACHI: "bn-input",
}
