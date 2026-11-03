"""Map dữ kiện nguồn → ô Form.io bước 1 cho thủ tục 1.115689 (Lào Cai, cổng iGate mới — cấp phường/xã).

Chọn người GIỮ NGUYÊN mapper cổng cũ (dang_ky_dat_dai_lan_dau_ho_gia_dinh_lao_cai/process/mapper.py): người nộp theo mốc
tài khoản (khớp số định danh rồi họ tên, bù nhân thân từ chính người đó) hoặc theo tờ khai (bên được ủy quyền → người ký
đơn → chủ hồ sơ cá nhân); chủ hồ sơ phát đủ cả 3 ô địa chỉ. Mapper cổng cũ cùng khuôn với 1.115682/1.115686 (Đối tượng
"Cá nhân"/"Tổ chức") nên phần đổi ô CongDan_*/ChuHoSo_* sang data[...] dùng chung
`su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai.process.mapper.doi_ten_o`.

Cổng cũ ghi ô "Ghi chú" (thửa đất, nguồn gốc, đính kèm thay thế…) ở bước thành phần hồ sơ; cổng mới chỉ còn ô "Ghi chú"
data[tenHoSo] ở bước 1 → chuyển câu đó vào đây.
"""

from app.pipelines.dang_ky_dat_dai_lan_dau_ho_gia_dinh_igate_lao_cai.process.schema import UI_COMP_BY_NAME
from app.pipelines.dang_ky_dat_dai_lan_dau_ho_gia_dinh_lao_cai.process import mapper as _goc
from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai.process.mapper import _dia_chi, doi_ten_o


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    out, warnings = doi_ten_o(_goc, fields, options)
    values = _goc._by_name([{**f, "value": _dia_chi(f.get("value"))} for f in fields])
    ghi_chu = _goc._ghi_chu(values)
    if ghi_chu:
        out.append({"name": "data[tenHoSo]", "comp": UI_COMP_BY_NAME["data[tenHoSo]"], "value": ghi_chu})
    return out, warnings
