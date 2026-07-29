"""Compact schema cho "[Bắc Ninh] Giao/thuê/chuyển mục đích SDĐ" (Đơn Mẫu 01/02).

LLM trả FACT nguồn từ Đơn đề nghị (công dân đã khai) + CCCD (nếu có). UI field điền vào
e-form Bắc Ninh được `mapper.enrich` suy ra tất định:
  - Thân đơn (Phần II): ô `element_<id>` khớp theo NHÃN → name = CỐT NHÃN, comp bn-*.
  - Người nhận kết quả (Phần IV): field tên CỐ ĐỊNH `nhanTaiNha*` → name = ĐÚNG NAME, comp bn-*.
Engine `fill-bacninh.js` thử khớp theo NAME trước, không có thì khớp theo NHÃN.
"""

FIELDS: list[dict] = [
    {"name": "Don_LoaiDon",
     "desc": 'Tên/tiêu đề đơn (dòng "ĐƠN ĐỀ NGHỊ ..."), vd "ĐƠN ĐỀ NGHỊ CHUYỂN MỤC ĐÍCH SỬ DỤNG ĐẤT".'},
    {"name": "Don_KinhGui",
     "desc": 'Nơi nhận ở dòng "Kính gửi:" của đơn, vd "Chủ tịch UBND phường Song Liễu". Bỏ ký hiệu "(2)".'},
    {"name": "Don_NguoiDeNghi", "desc": 'Họ tên/tổ chức người đề nghị (mục "1. Người đề nghị").'},
    {"name": "Don_DiaChiTruSo",
     "desc": 'Địa chỉ/trụ sở chính người đề nghị (mục 2) — CHUỖI MỘT DÒNG, giữ ĐỦ tổ/thôn + phường/xã '
             '+ tỉnh. KHÔNG trả object.'},
    {"name": "Don_SoDienThoai",
     "desc": 'Số điện thoại/thông tin liên hệ (mục "3. Địa chỉ liên hệ (điện thoại, fax, email)"). '
             'Ưu tiên số điện thoại.'},
    {"name": "Don_DiaDiemThuaDat",
     "desc": 'Địa điểm thửa đất/khu đất (mục 4), có thể kèm số thửa/tờ bản đồ. CHUỖI MỘT DÒNG, giữ đủ '
             'phường/xã, tỉnh. KHÔNG trả object.'},
    {"name": "Don_DienTichDat", "desc": 'Diện tích đất (m2) ở mục 5 (số, vd "402,0").'},
    {"name": "Don_DienTichLuaA", "desc": 'a) Diện tích đất chuyên trồng lúa phải nộp tiền (m2), nếu có. Bỏ nếu trống.'},
    {"name": "Don_DienTichLuaB", "desc": 'b) Diện tích đất phải bóc tách tầng đất mặt (m2), nếu có. Bỏ nếu trống.'},
    {"name": "Don_DienTichRung", "desc": '6. Diện tích rừng (m2), nếu có. Bỏ nếu trống.'},
    {"name": "Don_MucDich", "desc": '7. Mục đích sử dụng đất đề nghị chuyển sang (vd "Đất ở tại đô thị (ODT)").'},
    {"name": "Don_ThoiHan", "desc": '8. Thời hạn sử dụng đất đề nghị (vd "Lâu dài").'},
    {"name": "Don_CamKet", "desc": 'Các cam kết khác (nếu có). Bỏ nếu trống.'},
    {"name": "Don_TaiLieuKem", "desc": 'Tài liệu gửi kèm liệt kê trên đơn (nếu có). Bỏ nếu trống.'},

    {"name": "Cccd_SoDinhDanh",
     "desc": 'Số định danh/CCCD của người đề nghị (từ CCCD hoặc dòng "CCCD số/Số:" trên đơn). Dùng cho '
             'ô "Số căn cước công dân" của người nhận kết quả.'},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}

# ---- UI: ô thân đơn (Phần II) — khớp theo NHÃN (title). name = cốt nhãn. ----
UI_LABEL_LOAIDON = "ĐƠN ĐỀ NGHỊ"
UI_LABEL_KINHGUI = "Kính gửi"
UI_LABEL_NGUOIDN = "1. Người đề nghị"
UI_LABEL_DIACHITS = "2. Địa chỉ/trụ sở chính"
UI_LABEL_DIACHILH = "3. Địa chỉ liên hệ"
UI_LABEL_DIADIEM = "4. Địa điểm thửa đất"
UI_LABEL_DIENTICH = "5. Diện tích đất"
UI_LABEL_LUAA = "a) Diện tích đất chuyên trồng lúa"
UI_LABEL_LUAB = "b) Diện tích đất phải bóc tách"
UI_LABEL_RUNG = "6. Diện tích rừng"
UI_LABEL_MUCDICH = "7. Để sử dụng vào mục đích"
UI_LABEL_THOIHAN = "8. Thời hạn sử dụng đất"
UI_LABEL_CAMKET = "Các cam kết khác"
UI_LABEL_TAILIEU = "11. Tài liệu gửi kèm"

# ---- UI: người nhận kết quả (Phần IV) — khớp theo NAME (field cố định của cổng) ----
UI_NAME_NN_HOTEN = "nhanTaiNhahoTen"
UI_NAME_NN_CCCD = "nhanTaiNhasoCCCD"
UI_NAME_NN_SDT = "nhanTaiNhasoDienThoai"
UI_NAME_NN_DIACHI = "nhanTaiNhadiaChi"

UI_COMP_BY_NAME = {
    UI_LABEL_LOAIDON: "bn-input",
    UI_LABEL_KINHGUI: "bn-input",
    UI_LABEL_NGUOIDN: "bn-input",
    UI_LABEL_DIACHITS: "bn-input",
    UI_LABEL_DIACHILH: "bn-input",
    UI_LABEL_DIADIEM: "bn-input",
    UI_LABEL_DIENTICH: "bn-input",
    UI_LABEL_LUAA: "bn-input",
    UI_LABEL_LUAB: "bn-input",
    UI_LABEL_RUNG: "bn-input",
    UI_LABEL_MUCDICH: "bn-input",
    UI_LABEL_THOIHAN: "bn-input",
    UI_LABEL_CAMKET: "bn-input",
    UI_LABEL_TAILIEU: "bn-input",
    UI_NAME_NN_HOTEN: "bn-input",
    UI_NAME_NN_CCCD: "bn-input",
    UI_NAME_NN_SDT: "bn-input",
    UI_NAME_NN_DIACHI: "bn-input",
}
