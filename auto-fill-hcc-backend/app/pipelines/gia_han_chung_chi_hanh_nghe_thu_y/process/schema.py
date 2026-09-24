"""Compact schema cho "Gia hạn Chứng chỉ hành nghề thú y" (mã 2.001064 — Sở Nông nghiệp và Môi trường,
Form.io trên Cổng DVC quốc gia).

Form giống hệt "Cấp lại Chứng chỉ hành nghề thú y" (Phần I người nộp / Phần II chủ hồ sơ / tờ đơn) nên
DÙNG LẠI hằng số scope tờ đơn + 12 nhãn phạm vi của cap_lai_CCHN_thu_y. Khác biệt:
  - Tờ đơn là Mẫu 02.HNTY (đơn đăng ký GIA HẠN), KHÔNG có ô "Lý do".
  - Hồ sơ thường kèm Giấy khám sức khỏe (có số CCCD + ngày/nơi cấp + giới tính) và bằng tốt nghiệp
    chuyên môn → thêm nguồn nhân thân khi hồ sơ không có CCCD.

Nhóm field:
- NguoiDeNghi_* : nhân thân người đứng đơn (nguồn duy nhất cho Phần II + "Thông tin chung").
- NguoiNop_*    : chỗ để LLM "đỗ" nhân thân người nộp thay, KHÔNG đổ ra form.
- Don_*         : nội dung Đơn đăng ký gia hạn (Mẫu 02.HNTY).
- CCHNCu_*      : Chứng chỉ hành nghề thú y ĐÃ CẤP (số đăng ký + ngày hết hiệu lực).
"""

from app.pipelines.cap_lai_CCHN_thu_y.process.schema import (  # noqa: F401 — tái xuất cho mapper
    DON_SCOPE,
    DON_SCOPE_NEAR,
    DON_SCOPED_FIELDS,
    NGUOI_NOP_MARKERS,
    PHAM_VI_FIELD_KEY,
    PHAM_VI_OPTIONS,
    UI_COMP_BY_NAME as _CAP_LAI_UI_COMP_BY_NAME,
)

_DENGHI_SRC = (
    "CCCD / Đơn đăng ký gia hạn Chứng chỉ hành nghề thú y (Mẫu 02.HNTY) / Giấy khám sức khỏe của NGƯỜI "
    "ĐỀ NGHỊ"
)

# --- Nhân thân người đứng đơn ---
FIELDS: list[dict] = [
    {"name": "NguoiDeNghi_HoTen", "desc": "Họ và tên NGƯỜI ĐỀ NGHỊ (người đứng tên Đơn, người được gia "
        f"hạn chứng chỉ). Lấy từ {_DENGHI_SRC}, mục 'Tên tôi là' / 'Họ và tên'. Ghi IN HOA, ĐỦ DẤU. Bằng "
        "tốt nghiệp hay in tên không dấu/thiếu dấu → chỉ dùng khi không còn nguồn nào khác."},
    {"name": "NguoiDeNghi_NgaySinh", "desc": "Ngày sinh NGƯỜI ĐỀ NGHỊ, dd/mm/yyyy — CCCD, Đơn (mục 'Ngày "
        "tháng năm sinh'), Giấy khám sức khỏe (mục 'Sinh ngày') hoặc Bằng tốt nghiệp ('Ngày sinh')."},
    {"name": "NguoiDeNghi_SoDinhDanh", "desc": "Số CCCD/căn cước/định danh cá nhân NGƯỜI ĐỀ NGHỊ. Đọc "
        "CCCD (mặt trước/MRZ); không có CCCD thì lấy ở Giấy khám sức khỏe (mục 'Số CMND/CCCD/Hộ chiếu/"
        "định danh CD'). Chỉ chữ số, ưu tiên số 12 chữ số. KHÔNG lấy số hiệu văn bằng, số giấy khám "
        "sức khỏe, số điện thoại. Không có nguồn nào thì BỎ TRỐNG — tuyệt đối không lấy số của người "
        "nộp thay."},
    {"name": "NguoiDeNghi_NgayCapCCCD", "desc": "Ngày cấp CCCD/căn cước của NGƯỜI ĐỀ NGHỊ, dd/mm/yyyy — "
        "mặt sau CCCD hoặc 'Cấp ngày' ngay sau số CCCD trên Giấy khám sức khỏe. ⚠ 'Ngày cấp' đứng ngay "
        "sau dòng 'Bằng cấp chuyên môn' trong Đơn là ngày cấp BẰNG, KHÔNG phải ngày cấp CCCD."},
    {"name": "NguoiDeNghi_GioiTinh", "desc": 'Giới tính NGƯỜI ĐỀ NGHỊ: "Nam" hoặc "Nữ", đọc ở CCCD '
        "(Giới tính / Sex) hoặc ô được đánh dấu ở mục 'Giới tính: Nam ☐ Nữ ☐' của Giấy khám sức khỏe. "
        "KHÔNG suy từ họ tên."},
    {"name": "NguoiDeNghi_NoiCapCCCD", "desc": "Nơi cấp giấy tờ tùy thân NGƯỜI ĐỀ NGHỊ (mặt sau CCCD, hoặc "
        "'Tại' ngay sau ngày cấp CCCD trên Giấy khám sức khỏe). 'CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH "
        "CHÍNH VỀ TRẬT TỰ XÃ HỘI' hay viết tắt 'Cục CS QLHC về TTXH' → \"Cục Cảnh sát quản lý hành chính "
        'về trật tự xã hội"; thẻ Căn cước mới ghi "BỘ CÔNG AN" → "Bộ Công an".'},
    {"name": "NguoiDeNghi_ThuongTru", "desc": "NƠI THƯỜNG TRÚ / nơi cư trú NGƯỜI ĐỀ NGHỊ, object "
        "{quocGia,tinh,xa,diaChi}. Lấy ở CCCD (Nơi thường trú) / Đơn (Địa chỉ thường trú) / Giấy khám "
        "sức khỏe (Chỗ ở hiện tại). tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/đường/thôn/tổ "
        "(KHÔNG kèm phường/xã/tỉnh; giấy tờ chỉ ghi tới phường/xã thì diaChi rỗng). ⛔ KHÔNG lấy dòng "
        "'Tại' hay 'Địa chỉ hành nghề' của Đơn — đó là nơi hành nghề, không phải nơi cư trú."},
    {"name": "NguoiDeNghi_DienThoai", "desc": "Số điện thoại DI ĐỘNG NGƯỜI ĐỀ NGHỊ. Chỉ chữ số; KHÔNG "
        "lấy số bàn. Đơn hay ghi 'ĐT …' ngay sau địa chỉ hành nghề, hoặc mục 'Số điện thoại liên hệ'."},
    # Hai field dưới CHỈ để tách vai, mapper KHÔNG đổ ra form.
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên NGƯỜI NỘP THAY — CHỈ điền khi hồ sơ có CCCD RIÊNG của "
        "người nộp và người đó KHÁC người đứng đơn. Tự nộp → bỏ trống."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/định danh NGƯỜI NỘP THAY, chỉ chữ số. Tự nộp → bỏ trống."},
]

# --- Nội dung Đơn đăng ký gia hạn Mẫu 02.HNTY ---
FIELDS += [
    {"name": "Don_KinhGui", "desc": "Nơi nhận đơn — mục 'Kính gửi' của Đơn (vd 'Chi cục Chăn nuôi và "
        "Thú y tỉnh …'). Chép nguyên văn, bỏ chữ 'Kính gửi:'."},
    {"name": "Don_LaNguoiNuocNgoai", "desc": "Người đứng đơn có phải NGƯỜI NƯỚC NGOÀI không: trả 'Có' "
        "CHỈ khi giấy tờ thể hiện rõ quốc tịch nước ngoài hoặc dùng hộ chiếu nước ngoài; công dân Việt "
        "Nam (có CCCD / số định danh 12 số) → 'Không'."},
    {"name": "Don_BangCapChuyenMon", "desc": "Bằng cấp chuyên môn ghi ở mục 'Bằng cấp chuyên môn' của Đơn "
        "(vd 'Cao đẳng', 'Bác sĩ thú y'). Chép theo Đơn, CHỈ lấy tên bằng, KHÔNG kèm ngày cấp/nơi cấp. "
        "Đơn không ghi thì lấy trình độ + ngành trên văn bằng (vd 'Cao đẳng Chăn nuôi - Thú y')."},
    {"name": "Don_PhamViHanhNghe", "desc": "Phạm vi hành nghề được ĐÁNH DẤU (☑/x/✓) trong danh sách của "
        "Đơn (mục 'Đã được cấp Chứng chỉ hành nghề thú y' hoặc 'Nay đề nghị … cấp Chứng chỉ hành nghề'), "
        "vd 'Buôn bán thuốc thú y dùng trong thú y cho động vật trên cạn'. Chép NGUYÊN VĂN, ĐẦY ĐỦ cả đuôi "
        "'trên cạn' / 'thủy sản'; nhiều dòng được tích thì ngăn cách bằng dấu ';'. KHÔNG liệt kê dòng "
        "không được tích."},
    {"name": "Don_DiaDiem", "desc": "Địa danh nơi lập ĐƠN — phần '……, ngày … tháng … năm …' cuối Đơn "
        "(KHÔNG lấy của Giấy khám sức khỏe hay văn bằng). Chỉ lấy tên địa danh (vd 'Lai Châu')."},
    {"name": "Don_NgayLamDon", "desc": "Ngày lập ĐƠN ở dòng '……, ngày … tháng … năm …' cuối Đơn, dd/mm/yyyy "
        "(KHÔNG lấy ngày khám sức khỏe hay ngày cấp bằng)."},
    {"name": "Don_NguoiLamDon", "desc": "Họ tên NGƯỜI ĐỨNG ĐƠN ký ở cuối Đơn (ký, ghi rõ họ tên). Thường "
        "trùng NguoiDeNghi_HoTen."},
]

# --- Chứng chỉ hành nghề thú y ĐÃ CẤP (bản sắp hết hạn) ---
FIELDS += [
    {"name": "CCHNCu_SoDangKy", "desc": "SỐ ĐĂNG KÝ (số hiệu) của Chứng chỉ hành nghề thú y ĐÃ CẤP cần gia "
        "hạn, vd '123/CCHN-TY'. Ô trên form đã in sẵn đuôi '-CCHNTY' → chỉ lấy PHẦN SỐ đứng trước. Lấy ở "
        "bản chụp Chứng chỉ cũ hoặc Đơn nếu có ghi. ⛔ KHÔNG lấy 'Số hiệu' / 'Số vào sổ' của BẰNG TỐT "
        "NGHIỆP, số Giấy khám sức khỏe, số của đơn. Không có chứng chỉ cũ → BỎ TRỐNG."},
    {"name": "CCHNCu_NgayHetHan", "desc": "Ngày HẾT HIỆU LỰC của Chứng chỉ hành nghề thú y đã cấp — dòng "
        "'Chứng chỉ có giá trị đến ngày …' trên Chứng chỉ cũ, dd/mm/yyyy. KHÔNG nhầm với ngày cấp chứng "
        "chỉ, ngày hết hạn CCCD hay ngày cấp bằng. Không có chứng chỉ cũ → BỎ TRỐNG."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["NguoiDeNghi_NgaySinh"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiDeNghi_NgayCapCCCD"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiDeNghi_ThuongTru"] = "x-select-area"
COMPACT_COMP_BY_NAME["Don_NgayLamDon"] = "x-date"
COMPACT_COMP_BY_NAME["CCHNCu_NgayHetHan"] = "x-date"

# ---- UI Form.io fields (data[...]) — đúng bộ ô của form cấp lại, chỉ BỎ data[lyDo] (Mẫu 02.HNTY không
# có ô lý do). Xem chú thích từng ô ở cap_lai_CCHN_thu_y.process.schema.
UI_COMP_BY_NAME = {name: comp for name, comp in _CAP_LAI_UI_COMP_BY_NAME.items() if name != "data[lyDo]"}
