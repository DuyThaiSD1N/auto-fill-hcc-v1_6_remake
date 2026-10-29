"""Map dữ kiện nguồn → ô Form.io bước 1 cho thủ tục 1.115670 (Lào Cai, cổng iGate mới).

Dữ kiện nhân thân cùng dạng 1.115650 và form bước 1 y hệt → khối người nộp / chủ hồ sơ dùng NGUYÊN mapper của
giao_thue_dat_igate_lao_cai (chọn người nộp theo tài khoản, không ghi ô bị khoá, tổ chức → Doanh nghiệp/Tổ chức + tên +
MST + trụ sở, dom-expect ô (*)). Chủ hồ sơ thủ tục này thường là TỔ CHỨC SAU KHI thay đổi — prompt cổng cũ đã tách tổ
chức cũ (ToChucCu_Ten, đứng tên GCN đã cấp) khỏi chủ hồ sơ.
Riêng thủ tục này: ô "Ghi chú" (data[tenHoSo]) = trích yếu Đơn — cổng cũ ghi vào "Về việc", cổng mới không còn ô đó.
"""

from app.pipelines.dang_ky_bien_dong_chia_tach_to_chuc_lao_cai.process import mapper as _goc
from app.pipelines.giao_thue_dat_igate_lao_cai.process import mapper as _igate


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    out, warnings = _igate.enrich(fields, options)
    trich_yeu = _goc._trich_yeu(_goc._by_name(fields))
    if trich_yeu:
        out.append({"name": "data[tenHoSo]", "comp": "dom-input", "value": trich_yeu})
    return out, warnings
