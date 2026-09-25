"""Compact schema cho "Thủ tục cấp thẻ hướng dẫn viên du lịch nội địa" (mã 1.004623, QT-121).

Cổng Bộ VHTTDL `dichvucong.bvhttdl.gov.vn` (nộp về Sở VHTTDL tỉnh) — Angular Material bọc trong
`liz-*`, DOM không có formcontrolname, ô trong eform chỉ có id tự sinh. Form và bảng thành phần hồ sơ
NẰM CHUNG trang. LLM chỉ trả FACT nguồn; `mapper.enrich` suy tất định ra ô UI theo
(section = `.group-header`, name = `<mat-label>`) cho engine `fill-liz.js`.

Hồ sơ chỉ có MỘT người: người đề nghị cấp thẻ (Đơn Mẫu 04). Phần II "Thông tin người nộp hồ sơ" là của
tài khoản đăng nhập — chỉ điền khi số CCCD tài khoản TRÙNG số CCCD trên đơn (xem mapper); khối "Thông
tin ủy quyền" không điền.
Phần IV là nội dung Đơn Mẫu 04 (giới tính, trình độ, ngoại ngữ, email, tên điểm du lịch).

⚑ NHÃN CHƯA ĐỐI CHIẾU ĐƯỢC VỚI DOM GỐC: bản DOM dùng để lập mapping đã bị Google Dịch (vd "Thành phần
hồ sơ" → "Thành phần tin nhắn", "Địa chỉ chi tiết" → "chỉ chi"). Nhãn dưới đây là nhãn khôi phục; mỗi
ô kèm `aliases` là các cách viết khác có thể gặp, engine thử lần lượt rồi mới khớp theo tiền tố. Section
dùng CỤM NGẮN vì engine khớp section theo quan hệ chứa nhau — cụm càng ngắn càng chịu được lệch chữ.
"""

FIELDS: list[dict] = [
    # ---- NGƯỜI ĐỀ NGHỊ CẤP THẺ (Đơn Mẫu 04; đối chiếu Chứng chỉ nghiệp vụ, Văn bằng, CCCD nếu có) ----
    {
        "name": "NguoiDeNghi_HoTen",
        "desc": "Họ và tên người đề nghị cấp thẻ — dòng 'Họ và tên (chữ in hoa)' Đơn Mẫu 04; đối chiếu "
                "'Cấp cho Ông/Bà' trên Chứng chỉ nghiệp vụ, 'Cho' trên văn bằng. Viết có dấu như bản tiếng "
                "Việt, KHÔNG lấy bản tiếng Anh không dấu ('Upon').",
    },
    {
        "name": "NguoiDeNghi_NgaySinh",
        "desc": "Ngày sinh người đề nghị, dd/mm/yyyy. Nguồn: Đơn 04 → Chứng chỉ nghiệp vụ → CCCD → văn "
                "bằng (bản tiếng Anh ghi dạng '16 November 2004'). Chỉ trả khi đọc được ĐỦ ngày-tháng-năm.",
    },
    {
        "name": "NguoiDeNghi_GioiTinh",
        "desc": "Giới tính ở Đơn 04 ('Giới tính: □ Nam  ☑ Nữ') hoặc CCCD: 'Nam' hoặc 'Nữ'. Chỉ trả khi ô "
                "được đánh dấu rõ hoặc CCCD ghi rõ.",
    },
    {
        "name": "NguoiDeNghi_SoDinhDanh",
        "desc": "Số định danh cá nhân/CMND của người đề nghị (Đơn 04, Chứng chỉ nghiệp vụ, CCCD). Chỉ chữ "
                "số, chép ĐỦ các chữ số đọc được; số bị che/mờ một phần thì chép phần đọc được, KHÔNG bù.",
    },
    {"name": "NguoiDeNghi_NgayCap", "desc": "Ngày cấp CCCD/số định danh (dòng 'Ngày cấp' trên Chứng chỉ nghiệp vụ hoặc mặt sau CCCD), dd/mm/yyyy."},
    {"name": "NguoiDeNghi_NoiCap", "desc": "Nơi cấp CCCD (dòng 'Nơi cấp' trên Chứng chỉ nghiệp vụ, hoặc cơ quan cấp in trên CCCD: 'Bộ Công an' / 'Cục Cảnh sát quản lý hành chính về trật tự xã hội')."},
    {"name": "NguoiDeNghi_DienThoai", "desc": "Điện thoại ở Đơn 04, chỉ chữ số, chép đủ các chữ số đọc được."},
    {"name": "NguoiDeNghi_Email", "desc": "Email ở Đơn 04, nguyên văn. Phần tên hộp thư bị che thì bỏ field."},
    {
        "name": "NguoiDeNghi_DiaChi",
        "desc": "Địa chỉ liên lạc ở Đơn 04; đơn để trống thì lấy nơi cư trú/nơi thường trú trên CCCD. "
                "Object {tinh,xa,diaChi}. KHÔNG lấy nơi lập đơn ('Phong Nha, ngày…'), nơi chứng thực hay "
                "địa chỉ trường học thay cho địa chỉ liên lạc.",
    },
    {
        "name": "NguoiDeNghi_TrinhDoChuyenMon",
        "desc": "Dòng 'Trình độ chuyên môn nghiệp vụ' ở Đơn 04, chép nguyên văn (vd 'Đại học', 'Cao đẳng').",
    },
    {
        "name": "NguoiDeNghi_TrinhDoNgoaiNgu",
        "desc": "Dòng 'Trình độ ngoại ngữ' ở Đơn 04 (chỉ áp dụng thẻ quốc tế). Dòng chấm/để trống thì bỏ field.",
    },
    {
        "name": "NguoiDeNghi_TenDiemDuLich",
        "desc": "Tên điểm du lịch (chỉ khi đề nghị thẻ hướng dẫn viên TẠI ĐIỂM). Nằm trong câu đề nghị "
                "'…kính đề nghị Sở … cấp thẻ hướng dẫn viên du lịch tại điểm <TÊN ĐIỂM> cho tôi' — chỉ chép "
                "phần <TÊN ĐIỂM> (vd 'Khu du lịch Hồ Xanh'), bỏ 'tại điểm' và 'cho tôi'. Phần 'Hướng dẫn "
                "ghi' in sẵn cuối đơn KHÔNG phải giá trị — đơn không ghi tên điểm cụ thể thì bỏ field.",
    },
    {
        "name": "Don_LoaiThe",
        "desc": "Loại thẻ ghi ở tiêu đề Đơn 04 'Cấp thẻ hướng dẫn viên du lịch …': 'nội địa', 'quốc tế' "
                "hoặc 'tại điểm'.",
    },
    {"name": "Don_CoQuanNhan", "desc": "Cơ quan ở dòng 'Kính gửi' của Đơn 04 (vd 'Sở Văn hóa, Thể thao và Du lịch tỉnh …')."},

    # ---- VĂN BẰNG + CHỨNG CHỈ NGHIỆP VỤ (chỉ để đối chiếu điều kiện, không có ô riêng) ----
    {
        "name": "VanBang_TrinhDo",
        "desc": "Trình độ của văn bằng tốt nghiệp: 'Trung cấp', 'Cao đẳng', 'Đại học', 'Thạc sĩ' hoặc "
                "'Tiến sĩ' (Bằng cử nhân/kỹ sư → 'Đại học'). Không có văn bằng thì bỏ field.",
    },
    {
        "name": "VanBang_ChuyenNganh",
        "desc": "Ngành/chuyên ngành ghi trên văn bằng tốt nghiệp (vd 'Luật', 'Hướng dẫn du lịch', 'Quản trị "
                "dịch vụ du lịch và lữ hành'), chép nguyên văn phần tiếng Việt.",
    },
    {
        "name": "ChungChi_Ten",
        "desc": "Tên chứng chỉ nghiệp vụ hướng dẫn du lịch (vd 'Chứng chỉ nghiệp vụ hướng dẫn du lịch nội "
                "địa'), nguyên văn. Hồ sơ không có chứng chỉ thì bỏ field.",
    },
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _n in ("NguoiDeNghi_NgaySinh", "NguoiDeNghi_NgayCap"):
    COMPACT_COMP_BY_NAME[_n] = "x-date"
COMPACT_COMP_BY_NAME["NguoiDeNghi_DiaChi"] = "x-select-area"

# ---- UI fields cho engine fill-liz.js — khớp (section, mat-label) ----
# Section là CỤM NGẮN: engine chấp nhận header chứa cụm này (hoặc ngược lại).
S_NOP = "Thông tin người nộp hồ sơ"
S_THE = "thẻ hướng dẫn"

# comp: liz-input (text/textarea) | liz-date (datepicker dd/mm/yyyy) | liz-select (mat-select overlay).
# Cố ý BỎ các ô cổng render `disabled` ở Phần II (Tên người nộp, CMND/Hộ chiếu/MST) — cổng tự điền từ
# tài khoản định danh, engine bơm vào cũng bị chặn. Phần I (cơ quan, lĩnh vực, thủ tục, dịch vụ công)
# cổng chọn sẵn; Phần V lệ phí cổng tự tính — không khai.
UI_FIELDS: list[tuple[str, str, str, tuple[str, ...]]] = [
    (S_NOP, "Ngày sinh", "liz-date", ()),
    (S_NOP, "Ngày cấp", "liz-date", ()),
    (S_NOP, "Nơi cấp", "liz-input", ()),
    (S_NOP, "Số điện thoại", "liz-input", ("Điện thoại",)),
    (S_NOP, "Email", "liz-input", ("E-mail",)),
    (S_NOP, "Địa chỉ hành chính", "liz-select", ()),
    (S_NOP, "Địa chỉ chi tiết", "liz-input", ("Địa chỉ",)),

    (S_THE, "Giới tính", "liz-select", ()),
    (S_THE, "Trình độ chuyên môn nghiệp vụ", "liz-input",
     ("Trình độ chuyên môn, nghiệp vụ", "Trình độ chuyên môn")),
    (S_THE, "Trình độ ngoại ngữ (đối với người đề nghị cấp thẻ HDV du lịch quốc tế)", "liz-input",
     ("Trình độ ngoại ngữ",)),
    (S_THE, "Email", "liz-input", ("E-mail",)),
    (S_THE, "Tên điểm du lịch đối với trường hợp cấp thẻ hướng dẫn viên du lịch tại điểm", "liz-input",
     ("Tên điểm du lịch",)),
]

COMP_BY_UI = {(s, l): c for s, l, c, _a in UI_FIELDS}
ALIASES_BY_UI = {(s, l): list(a) for s, l, _c, a in UI_FIELDS}
