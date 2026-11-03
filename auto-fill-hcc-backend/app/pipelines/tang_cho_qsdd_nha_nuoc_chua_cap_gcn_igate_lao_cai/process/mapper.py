"""Map dữ kiện nguồn → ô Form.io bước 1 cho thủ tục 1.115690 (Lào Cai, cổng iGate mới — cấp phường/xã).

Chọn người GIỮ NGUYÊN mapper cổng cũ (tang_cho_qsdd_nha_nuoc_chua_cap_gcn/process/mapper.py): người nộp theo mốc tài
khoản (chỉ điền khi hồ sơ có giấy tờ của CHÍNH người đăng nhập — người tặng cho hoặc người được uỷ quyền) hoặc theo tờ
khai; chủ hồ sơ = người tặng cho, phát đủ cả 3 ô địa chỉ; giới tính suy từ CCCD 12 số. Mapper cổng cũ cùng khuôn với
1.115682/1.115686/1.115689 (Đối tượng "Cá nhân"/"Tổ chức") nên phần đổi ô CongDan_*/ChuHoSo_* sang data[...] dùng chung
`su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai.process.mapper.doi_ten_o`.
"""

from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai.process.mapper import doi_ten_o
from app.pipelines.tang_cho_qsdd_nha_nuoc_chua_cap_gcn.process import mapper as _goc


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    return doi_ten_o(_goc, fields, options)
