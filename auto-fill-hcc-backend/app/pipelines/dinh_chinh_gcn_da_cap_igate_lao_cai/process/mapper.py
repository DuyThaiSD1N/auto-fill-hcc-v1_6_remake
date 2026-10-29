"""Map dữ kiện nguồn → ô Form.io bước 1 cho thủ tục 1.115686 (Lào Cai, cổng iGate mới — cấp phường/xã).

Chọn người GIỮ NGUYÊN mapper cổng cũ (dinh_chinh_gcn_da_cap_lao_cai/process/mapper.py): người nộp theo mốc tài khoản
(CCCD → người trong giấy tờ → bên được ủy quyền → khối phẳng) hoặc theo tờ khai; chủ hồ sơ = người đứng tên Đơn, phát đủ
cả 3 ô địa chỉ. Mapper cổng cũ cùng khuôn với 1.115682 nên phần đổi ô CongDan_*/ChuHoSo_* sang data[...] dùng chung
`su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai.process.mapper.doi_ten_o`.

Cổng cũ điền ô "Về việc" (tên thủ tục + nội dung đính chính + số hiệu GCN) và "Ghi chú" (thửa đất, người đồng sử dụng)
ở bước thành phần hồ sơ. Cổng mới chỉ còn ô "Ghi chú" data[tenHoSo] ở bước 1 → ghép hai câu đó vào đây.
"""

from app.pipelines.dinh_chinh_gcn_da_cap_igate_lao_cai.process.schema import UI_COMP_BY_NAME
from app.pipelines.dinh_chinh_gcn_da_cap_lao_cai.process import mapper as _goc
from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai.process.mapper import _dia_chi, doi_ten_o


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    out, warnings = doi_ten_o(_goc, fields, options)
    values = _goc._by_name([{**f, "value": _dia_chi(f.get("value"))} for f in fields])
    ghi_chu = " ".join(x for x in (_goc._ve_viec(values), _goc._ghi_chu(values)) if x)
    if ghi_chu:
        out.append({"name": "data[tenHoSo]", "comp": UI_COMP_BY_NAME["data[tenHoSo]"], "value": ghi_chu})
    return out, warnings
