"""Map dữ kiện nguồn → ô Form.io bước 1 cho thủ tục 1.115652 (Lào Cai, cổng iGate mới).

Dữ kiện cùng dạng 1.115650 và form bước 1 y hệt → khối người nộp / chủ hồ sơ dùng NGUYÊN mapper của
giao_thue_dat_igate_lao_cai (chọn người nộp theo tài khoản, không ghi ô bị khoá, tổ chức → trụ sở, dom-expect ô (*)).
Riêng thủ tục này thêm:
  • ô "Ghi chú" (data[tenHoSo]) = trích yếu hồ sơ — cổng cũ ghi vào "Về việc", cổng mới không còn ô đó;
  • cảnh báo khi địa chỉ chủ hồ sơ ghi theo xã/phường CŨ (quyết định gốc hay ghi địa danh trước sáp nhập).
"""

from app.pipelines.dieu_chinh_giao_dat_lao_cai.process import mapper as _goc
from app.pipelines.giao_thue_dat_igate_lao_cai.process import mapper as _igate


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    out, warnings = _igate.enrich(fields, options)
    values = _goc._by_name(fields)

    trich_yeu = _goc._trich_yeu(values)
    if trich_yeu:
        out.append({"name": "data[tenHoSo]", "comp": "dom-input", "value": trich_yeu})

    chs_area = _igate._area(values.get("ChuHoSo_NoiCuTru"))
    if chs_area and _goc._plain(chs_area.get("tinh")) and not _goc._plain(chs_area.get("xa")):
        warnings.append(
            "Địa chỉ chủ hồ sơ ghi theo đơn vị hành chính CŨ (trước sáp nhập) nên không khớp danh mục hiện hành — "
            "cán bộ chọn tay ô Phường/Xã của khối chủ hồ sơ."
        )
    return out, warnings
