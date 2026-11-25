"""Map dữ kiện nguồn → ô Form.io bước 1 cho thủ tục 1.115683 (Lào Cai, cổng iGate mới, cấp phường/xã).

Chọn người + phát ô dùng NGUYÊN mapper chung của form "FORM NGUOI NOP" (chuyen_doi_md_sd_dat_igate_lao_cai): theo tài
khoản / theo tờ khai (mở khoá Họ tên/CCCD/Ngày sinh bằng enableInput), chủ hồ sơ điền thẳng từ giấy tờ (cá nhân, hoặc
tổ chức → ChuHS "Doanh nghiệp"/"Tổ chức" + tên + MST), KHÔNG tích "Người nộp hồ sơ là chủ hồ sơ" (mapping đề xuất tích,
nhưng tích là cổng calculateValue chép đè khối chủ hồ sơ — như mọi pipeline iGate Lào Cai), ô (*) thiếu → dom-expect.

⚑ HAI CHẾ ĐỘ NGƯỜI NỘP (`options.submitterMode`, cài đặt "Lấy người nộp theo tờ khai" của extension):
  - theo tài khoản (mặc định): khối người nộp = người trong hồ sơ KHỚP tài khoản đăng nhập; không khớp ai → để trống
    nhân thân khối người nộp + cảnh báo, chỉ điền khối chủ hồ sơ.
  - theo tờ khai (`owner_as_submitter`): người nộp = NGƯỜI SỬ DỤNG ĐẤT mục 1 Đơn Mẫu 30. Khác tài khoản (hoặc không có
    mốc) → Họ tên/CCCD/Ngày sinh phát kèm enableInput (extension bỏ khoá rồi ghi đè) + cảnh báo; trùng tài khoản → để
    ô khoá như cổng đổ. Địa chỉ/SĐT/Email người nộp = của người sử dụng đất (Đơn mục 2–3). Chủ hồ sơ là tổ chức thì
    để trống khối người nộp + cảnh báo (không biết ai đi nộp).
  Đơn không đọc được người sử dụng đất (cá nhân) mà hồ sơ có đúng MỘT thẻ căn cước → lấy thẻ đó + cảnh báo.

Điểm riêng theo mapping 1.115683 (cùng cách xử lý 1.115684, dùng lại `_chuan_hoa` của pipeline đó):
1. Địa chỉ: Tỉnh/Phường-Xã chỉ còn đơn vị hành chính mới → lấy theo Đơn Mẫu 30 mục 2 (nơi thường trú HIỆN TẠI); CCCD/
   GCN in địa danh trước 01/7/2025 → Đơn thắng địa chỉ trên thẻ của chính người sử dụng đất + cảnh báo khi khác nơi.
2. Nơi cấp "Cục Cảnh sát đăng ký, quản lý cư trú và DLQG về dân cư" (thẻ Căn cước từ 01/7/2024) → "Bộ Công An"; "Cục
   CS QLHC về TTXH" giữ nguyên (option có sẵn trên cổng).
3. "Ghi chú" (data[tenHoSo]) = tóm tắt đề nghị gia hạn: thửa, tờ, vị trí, quyết định phê duyệt phương án (mục 5),
   thời hạn đề nghị gia hạn (mục 6).
"""

import re

from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process import mapper as _igate
from app.pipelines.chuyen_doi_md_sd_dat_lao_cai.process import mapper as _goc
from app.pipelines.gia_han_phuong_an_su_dung_dat_ket_hop_da_muc_dich_lao_cai.process.schema import UI_COMP_BY_NAME
from app.pipelines.giao_dat_o_khong_dau_gia_lao_cai.process import mapper as _giao_dat

_TIEU_DE = "Đề nghị gia hạn phương án sử dụng đất kết hợp đa mục đích"


def _la_to_chuc(values: dict) -> bool:
    """Cùng điều kiện tổ chức của mapper chung (enrich_with_warnings)."""
    return _goc._fold(values.get("ChuHoSo_LoaiDoiTuong")) == "to chuc" and bool(_goc._plain(values.get("ChuHoSo_TenToChuc")))


def _chuan_hoa_to_chuc(fields: list[dict]) -> list[dict]:
    """Chủ hồ sơ tổ chức: chỉ đổi nơi cấp C06. Mục 2 Đơn là trụ sở tổ chức, không phải nơi ở của người trên thẻ nên
    không bỏ địa chỉ trên thẻ; cũng không lấy thẻ duy nhất làm người sử dụng đất."""
    out = []
    for field in fields:
        name, value = field.get("name"), field.get("value")
        if name == "ChuHoSo_NoiCap" and value:
            field = {**field, "value": _giao_dat._noi_cap_c06(value)}
        elif name in ("DanhSachCccd", "NguoiTrongGiayTo") and isinstance(value, list):
            field = {**field, "value": [_giao_dat._person_noi_cap(p) if isinstance(p, dict) else p for p in value]}
        out.append(field)
    return out


def _so_quyet_dinh(value) -> str | None:
    text = _goc._plain(value)
    if not text:
        return None
    return re.sub(r"(?i)^(quyết định|qđ)?\s*số\s*:?\s*", "", text).strip() or None


def _co_quan(value) -> str | None:
    text = _goc._plain(value)
    if not text:
        return None
    return re.sub(r"(?i)\b(ủy|uỷ) ban nhân dân\b", "UBND", text)


def _ghi_chu(values: dict) -> str | None:
    so_thua = _goc._plain(values.get("ThuaDat_SoThua"))
    so_to = _goc._plain(values.get("ThuaDat_SoTo"))
    vi_tri = _goc._plain(values.get("ThuaDat_ViTri"))
    if not vi_tri:
        area = values.get("ThuaDat_DiaChi")
        if isinstance(area, dict):
            vi_tri = ", ".join(p for p in (_goc._plain(area.get(k)) for k in ("chiTietDuoiXa", "diaChi", "xa", "tinh"))
                               if p) or None
    so_qd = _so_quyet_dinh(values.get("PhuongAn_SoQuyetDinh"))
    ngay_qd = _goc._full_date(values.get("PhuongAn_NgayQuyetDinh"))
    co_quan = _co_quan(values.get("PhuongAn_CoQuanDuyet"))
    tu = _goc._full_date(values.get("GiaHan_TuNgay"))
    den = _goc._full_date(values.get("GiaHan_DenNgay"))
    if not (so_thua or so_to or vi_tri or so_qd or den):
        return None

    thua = [p for p in (f"thửa đất số {so_thua}" if so_thua else None,
                        f"tờ bản đồ số {so_to}" if so_to else None, vi_tri) if p]
    chu_thich = []
    if so_qd:
        chu_thich.append(f"phương án đã phê duyệt tại Quyết định số {so_qd}"
                         + (f" ngày {ngay_qd}" if ngay_qd else "") + (f" của {co_quan}" if co_quan else ""))
    if den:
        chu_thich.append("đề nghị gia hạn " + (f"từ ngày {tu} " if tu else "") + f"đến hết ngày {den}")
    text = _TIEU_DE + (" – " + ", ".join(thua) if thua else "")
    return text + (f" ({'; '.join(chu_thich)})" if chu_thich else "")


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    if _la_to_chuc(_goc._by_name(fields)):
        fields, warnings = _chuan_hoa_to_chuc(fields), []
    else:
        fields, warnings = _giao_dat._chuan_hoa(fields)
    out, chung = _igate.enrich_with_warnings(fields, options)
    ghi_chu = _ghi_chu(_goc._by_name(fields))
    if ghi_chu:
        out.append({"name": "data[tenHoSo]", "comp": UI_COMP_BY_NAME["data[tenHoSo]"], "value": ghi_chu})
    return out, [*warnings, *chung]
