"""Compact schema cho "Tiếp nhận đối tượng cần bảo vệ khẩn cấp vào cơ sở trợ giúp xã hội" (1.116908, NĐ
335/2026/NĐ-CP, cổng Bộ Y tế — Form.io).

HAI vai:
- ĐỐI TƯỢNG (DoiTuong_*) = CHỦ HỒ SƠ → Phần II data[owner*]. Nguồn: Tờ khai Mẫu số 04 mục I "Thông tin của
  người đề nghị được chăm sóc, nuôi dưỡng", CCCD/thẻ căn cước của đối tượng, Biên bản tiếp nhận.
- NGƯỜI NỘP (NguoiNop_*) = người giám hộ → Phần I data[fullname...]. Nguồn: Mẫu 04 mục II "Thông tin người
  giám hộ" + CCCD của người đó. Không có người giám hộ → mapper dùng đối tượng cho Phần I.

Form CÙNG field-key với 1.116909 (file mapping HTML thật; mỗi key XUẤT HIỆN 1 LẦN → KHÔNG occurrence) nên dùng
chung UI_COMP_BY_NAME. Trường ẩn (organization, taxCode, ownerOrganizationFullname, ownerTaxCode, copyDuLieu3) chỉ
hiện với tổ chức → không điền; data[fax]/data[ownerFax] không có nguồn → không điền.
"""

from app.pipelines.thuc_hien_tro_cap_xa_hoi_nhan_cham_soc_nuoi_duong_hang_thang.process.schema import (  # noqa: F401
    UI_COMP_BY_NAME,
)

FIELDS: list[dict] = [
    # === ĐỐI TƯỢNG cần bảo vệ khẩn cấp = chủ hồ sơ ===
    {"name": "DoiTuong_HoTen", "desc": "Họ và tên ĐỐI TƯỢNG được đề nghị chăm sóc, nuôi dưỡng (Tờ khai Mẫu số 04 mục "
        "I.1; mục III \"Họ và tên đối tượng\"; CCCD của đối tượng; Biên bản tiếp nhận phần thông tin đối tượng). Ghi "
        "như trên giấy tờ. KHÔNG lấy tên người giám hộ, người khai, người tiếp nhận tờ khai, người phát hiện hay "
        "đại diện cơ quan/cơ sở trong biên bản."},
    {"name": "DoiTuong_NgaySinh", "desc": "Ngày sinh đối tượng, dd/mm/yyyy — CCCD / Tờ khai mục I.1 / Biên bản tiếp "
        "nhận. Giấy tờ chỉ ghi NĂM sinh thì trả đúng năm (vd \"2013\"), KHÔNG tự thêm ngày/tháng."},
    {"name": "DoiTuong_GioiTinh", "desc": 'Giới tính đối tượng: "Nam" hoặc "Nữ".'},
    {"name": "DoiTuong_SoDinhDanh", "desc": "Số căn cước / số định danh cá nhân của đối tượng (CCCD, thẻ căn cước, "
        "dòng \"Số căn cước/Số định danh cá nhân\" mục I.1 của Tờ khai). Chỉ chữ số."},
    {"name": "DoiTuong_NgayCap", "desc": "Ngày cấp căn cước của đối tượng (mặt sau thẻ hoặc \"ngày cấp\" mục I.1 Tờ "
        "khai), dd/mm/yyyy."},
    {"name": "DoiTuong_NoiCap",
     "desc": 'Nơi cấp căn cước của đối tượng. "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → '
             '"Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới (cấp từ 01/07/2024) ghi '
             '"BỘ CÔNG AN" → "Bộ Công an". Thẻ không in nhãn "Nơi cấp" → lấy ở Tờ khai.'},
    {"name": "DoiTuong_NoiCuTru",
     "desc": 'NƠI CƯ TRÚ đối tượng (Tờ khai mục I.2 "Nơi cư trú"), object {quocGia,tinh,xa,chiTietDuoiXa}. Ưu tiên '
             "Tờ khai (ghi địa giới MỚI sau sáp nhập); CCCD cũ có thể ghi tên CŨ. tinh='Tỉnh/Thành phố …', "
             "xa=phường/xã/đặc khu, chiTietDuoiXa=số nhà/đường/tổ dân phố/khu phố/thôn (KHÔNG kèm xã/huyện/tỉnh). "
             "KHÔNG lấy mục I.3 \"Nơi ở hiện nay\"."},
    {"name": "DoiTuong_NoiOHienNay",
     "desc": 'Nguyên văn mục I.3 "Nơi ở hiện nay" của đối tượng trên Tờ khai (vd "Đang tạm lánh tại nhà bà ngoại – '
             'Số 12, thôn A, xã B, tỉnh C"). Chuỗi văn bản, chép đúng; trống hoặc "như trên" thì bỏ.'},
    {"name": "DoiTuong_DienThoai", "desc": "Số điện thoại đối tượng (Tờ khai mục I.4). Chỉ chữ số; ghi \"Không có\" "
        "hoặc trống thì bỏ — KHÔNG chép số của người giám hộ (mapper xử lý)."},
    {"name": "DoiTuong_Email", "desc": "Email đối tượng nếu giấy tờ có (thường không có → bỏ)."},
    {"name": "DoiTuong_NhomDoiTuong",
     "desc": 'Các ô ĐÃ TÍCH (☒, ☑, ✓, X) ở mục I.7 "Thuộc nhóm đối tượng" của Tờ khai, chép đúng chữ của ô, nhiều ô '
             'thì ngăn cách bằng ";". Các ô của mục: Trẻ em dưới 16 tuổi không có nguồn nuôi dưỡng / Người từ đủ 16 '
             'tuổi không có nguồn nuôi dưỡng đang đi học / Người khuyết tật nặng, đặc biệt nặng / Người nhiễm '
             'HIV/AIDS / Người cao tuổi không có điều kiện sống tại cộng đồng / Đối tượng cần bảo vệ khẩn cấp. '
             "KHÔNG liệt kê ô để trống (☐)."},
    {"name": "DoiTuong_MucDoKhuyetTat",
     "desc": 'Mức độ khuyết tật ĐÃ TÍCH ở mục I.8.a của Tờ khai: "Nhẹ", "Nặng" hoặc "Đặc biệt nặng". Không tích ô '
             "nào thì bỏ."},

    # === NGƯỜI NỘP (Phần I) = người giám hộ ===
    {"name": "NguoiNop_HoTen",
     "desc": 'Họ tên NGƯỜI GIÁM HỘ ở Tờ khai Mẫu số 04 mục II "Thông tin người giám hộ" (thường trùng người ký "NGƯỜI '
             'KHAI"). Mục II để trống → bỏ. KHÔNG lấy "NGƯỜI TIẾP NHẬN TỜ KHAI", người phát hiện hay đại diện cơ '
             "quan/cơ sở trong Biên bản tiếp nhận."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh người giám hộ, dd/mm/yyyy, lấy trong mục II hoặc CCCD riêng khớp "
        "đúng họ tên/số giấy tờ người đó."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính người giám hộ: "Nam"/"Nữ"; không suy từ tên.'},
    {"name": "NguoiNop_SoDinhDanh",
     "desc": "Số căn cước/định danh của người giám hộ trong mục II hoặc CCCD riêng khớp đúng người. Chỉ trả dãy 9 "
             "hoặc 12 chữ số; số thừa/thiếu chữ số thì bỏ, không tự sửa đoán."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp căn cước người giám hộ, dd/mm/yyyy."},
    {"name": "NguoiNop_NoiCap",
     "desc": "Nơi cấp căn cước người giám hộ. Ưu tiên CCCD riêng của người này; không có thì lấy ở mục II Tờ khai. "
             "Chuẩn hóa như DoiTuong_NoiCap."},
    {"name": "NguoiNop_NoiCuTru",
     "desc": "Nơi cư trú người giám hộ (mục II.2), object {quocGia,tinh,xa,chiTietDuoiXa}."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại người giám hộ (mục II.5)."},
    {"name": "NguoiNop_Email", "desc": "Email người giám hộ nếu giấy tờ có."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("DoiTuong_NgaySinh", "DoiTuong_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("DoiTuong_NoiCuTru", "NguoiNop_NoiCuTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"
