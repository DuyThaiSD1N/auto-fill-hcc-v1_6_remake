"""Compact schema cho thủ tục 1.010386 — Trình báo mất hộ chiếu phổ thông (thực hiện tại cấp xã).

LLM chỉ trả dữ kiện nguồn đọc từ giấy tờ (tiền tố theo giấy); ô UI ``CongDan__fs*`` / ``CongDan_*`` do mapper dựng
theo file mapping "Mapping_Trinh_bao_mat_ho_chieu_cap_xa_BCA" (sheet "Trình báo mất HC cấp xã - BCA").

Giấy tờ: Đơn trình báo mất hộ chiếu phổ thông (Mẫu TK05, mục 1–9 — nguồn chính của khối Thông tin trình báo) · Tờ khai
đề nghị cấp hộ chiếu phổ thông ở trong nước (Mẫu TK01, có thể có — ngày cấp CCCD, mục 13 hộ chiếu gần nhất) · thẻ CCCD
/ căn cước (có thể có — ngày cấp, nơi cấp).

Cố ý KHÔNG phát:
- Ô khoá cổng tự đổ từ tài khoản VNeID: Họ và tên (``CongDan_tenCongDan``, readonly), Giới tính
  (``CongDan__fs_BCAGioiTinhCd``, disabled), Ngày sinh (``CongDan_ngaySinhCongDan``, readonly), Số ĐDCN/CMND
  (``CongDan_soCmnd``, readonly).
- Nơi tiếp nhận: Tỉnh / Phường-Xã (``CongDan_maTinhThanh`` / ``CongDan_maPhuongXa``, disabled — đã chọn ở bước "Lựa
  chọn DVC"), Cơ quan thực hiện (``CongDan__fs_BCANoiNopHS`` — danh sách chỉ có Công an của xã đã chọn, cổng chọn sẵn).
- Khối tra cứu doanh nghiệp (#form-search-dn, ẩn) — người trình báo là cá nhân.
- Email (*) — giấy tờ không có; cảnh báo nhập tay.
"""

FIELDS: list[dict] = [
    # Đơn trình báo mất hộ chiếu phổ thông (Mẫu TK05).
    {"name": "DonTrinhBao_KinhGui", "desc": "Dòng \"Kính gửi\" của đơn, chép nguyên văn tên cơ quan."},
    {"name": "DonTrinhBao_Ho", "desc": "Mục 1 — phần \"Họ\" (vd \"LÝ\"), chép đúng chữ trên giấy."},
    {"name": "DonTrinhBao_ChuDemTen", "desc": "Mục 1 — phần \"Chữ đệm và tên\" (vd \"QUANG BÌNH\"), chép đúng chữ."},
    {"name": "DonTrinhBao_SoDinhDanh", "desc": "Mục 4 — \"Số định danh cá nhân\" (các ô số liền nhau), chỉ chữ số."},
    {"name": "DonTrinhBao_NoiCuTru",
     "desc": "Mục 5 — \"Nơi cư trú hiện tại\", object {quocGia,tinh,xa,chiTietDuoiXa}; chiTietDuoiXa là phần đứng trước "
             "xã/phường (số nhà, đường, tổ dân phố, thôn, bản)."},
    {"name": "DonTrinhBao_DienThoai", "desc": "Mục 6 — Số điện thoại, chỉ chữ số."},
    {"name": "DonTrinhBao_SoHoChieu",
     "desc": "Mục 7 — \"Số hộ chiếu\" bị mất: một chữ cái + 7–8 chữ số (vd \"C1234567\"). Ghi \"không nhớ\" thì trả "
             "\"không nhớ\". Để trống / chấm chấm → bỏ field."},
    {"name": "DonTrinhBao_NgayCapHoChieu",
     "desc": "Mục 7 — \"ngày cấp\" của hộ chiếu bị mất, dd/mm/yyyy. Để trống \"…/…/…\" → bỏ field."},
    {"name": "DonTrinhBao_CoQuanCapHoChieu", "desc": "Mục 7 — \"Cơ quan cấp\" hộ chiếu, chép nguyên văn."},
    {"name": "DonTrinhBao_NgayMat",
     "desc": "Mục 8 — \"Hộ chiếu trên đã bị mất vào hồi … giờ … phút, ngày …\": CHỈ phần ngày, dd/mm/yyyy."},
    {"name": "DonTrinhBao_LyDo",
     "desc": "Mục 9 — \"Hoàn cảnh và lý do cụ thể bị mất hộ chiếu\": chép NGUYÊN VĂN cả đoạn (đến trước dòng \"Làm "
             "tại …\"), giữ đúng chính tả, không tóm tắt."},

    # Tờ khai đề nghị cấp hộ chiếu phổ thông ở trong nước (Mẫu TK01).
    {"name": "ToKhai_Ho", "desc": "Mục 1 — phần \"Họ\", chép đúng chữ trên giấy."},
    {"name": "ToKhai_ChuDemTen", "desc": "Mục 1 — phần \"Chữ đệm và tên\", chép đúng chữ trên giấy."},
    {"name": "ToKhai_SoDinhDanh", "desc": "Mục 4 — \"Số ĐDCN/CMND\" (các ô số liền nhau), chỉ chữ số."},
    {"name": "ToKhai_NgayCap", "desc": "Mục 4 — \"Ngày cấp\" của số ĐDCN/CMND, dd/mm/yyyy."},
    {"name": "ToKhai_DienThoai", "desc": "Mục 7 — Số điện thoại, chỉ chữ số."},
    {"name": "ToKhai_Email", "desc": "Địa chỉ email nếu tờ khai có ghi (có @). Không có → bỏ field."},
    {"name": "ToKhai_ThuongTru",
     "desc": "Mục 8 — Địa chỉ thường trú, object {quocGia,tinh,xa,chiTietDuoiXa}; chiTietDuoiXa là phần đứng trước "
             "xã/phường (số nhà, tổ dân phố, thôn, bản)."},
    {"name": "ToKhai_HoChieuCu_So",
     "desc": "Mục 13 — \"Hộ chiếu phổ thông lần gần nhất (nếu có) số\": một chữ cái + 7–8 chữ số. Trống → bỏ field."},
    {"name": "ToKhai_HoChieuCu_NgayCap", "desc": "Mục 13 — \"cấp ngày\" của hộ chiếu gần nhất, dd/mm/yyyy."},
    {"name": "ToKhai_NoiDungDeNghi", "desc": "Mục 14 — \"Nội dung đề nghị\", chép nguyên văn cả dòng."},

    # Thẻ CCCD / căn cước của người trình báo.
    {"name": "Cccd_HoTen", "desc": "Họ, chữ đệm và tên trên thẻ căn cước/CCCD."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh cá nhân / số CCCD trên thẻ, chỉ chữ số."},
    {"name": "Cccd_NgayCap",
     "desc": "Ngày cấp thẻ (\"Ngày, tháng, năm cấp / Date of issue\" hoặc \"Ngày, tháng, năm\" mặt sau), dd/mm/yyyy. "
             "KHÔNG lấy ngày hết hạn / \"Có giá trị đến\"."},
    {"name": "Cccd_NoiCap",
     "desc": 'Cơ quan cấp in mặt sau: "BỘ CÔNG AN" → "Bộ Công an"; "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ '
             'TRẬT TỰ XÃ HỘI" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội".'},
    {"name": "Cccd_NoiThuongTru",
     "desc": "Nơi thường trú / Nơi cư trú / Place of residence trên thẻ, object {quocGia,tinh,xa,chiTietDuoiXa}."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("DonTrinhBao_NgayCapHoChieu", "DonTrinhBao_NgayMat", "ToKhai_NgayCap", "ToKhai_HoChieuCu_NgayCap",
              "Cccd_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("DonTrinhBao_NoiCuTru", "ToKhai_ThuongTru", "Cccd_NoiThuongTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô form theo file mapping (name trong DOM), đúng thứ tự trên form. <select> bootstrap-select → dom-select; ô ngày
# form-builder (input text + icon lịch, định dạng cố định Ngày/Tháng/Năm) nhận gõ chữ như mẫu con dấu → dom-input;
# textarea → dom-input. Tỉnh trước Phường/Xã vì danh mục xã nạp qua API theo tỉnh.
UI_COMP_BY_NAME = {
    "CongDan__fsNgayCapCMND": "dom-input",          # 6. Ngày cấp ĐDCN/CMND (*)
    "CongDan__fsNoiCapCMND": "dom-input",           # 7. Nơi cấp CMND/CCCD (*) — ô chữ
    "CongDan_diDong": "dom-input",                  # 8. Số điện thoại (*)
    "CongDan_email": "dom-input",                   # 9. Email (*)
    "CongDan__fs_BCATinhTamTru": "dom-select",      # 10. Địa chỉ nơi cư trú hiện nay — Tỉnh/Thành phố (*)
    "CongDan__fs_BCAXaTamTru": "dom-select",        # 11. Phường/Xã (*) — nạp theo tỉnh
    "CongDan__fs_BCADiaChiTamTru": "dom-input",     # 12. Địa chỉ chi tiết (*)
    "CongDan__fs_BCASoHoChieu": "dom-input",        # 13. Số hộ chiếu bị mất
    "CongDan__fs_BCANgayCapHoChieu": "dom-input",   # 14. Ngày cấp hộ chiếu
    "CongDan__fs_BCACoQuanCap": "dom-input",        # 15. Cơ quan cấp hộ chiếu
    "CongDan__fs_BCAThoiGianMatHC": "dom-input",    # 16. Thời gian mất hộ chiếu (chỉ ngày)
    "CongDan__fs_BCALyDoMatHC": "dom-input",        # 17. Hoàn cảnh và lý do cụ thể mất hộ chiếu (*) — textarea
}

# Ô có danh sách nạp chậm qua API → extension chờ thêm tới waitMs (ms) rồi thử lại (như thị thực 1.001194).
WAIT_MS = {
    "CongDan__fs_BCAXaTamTru": 8000,
}
