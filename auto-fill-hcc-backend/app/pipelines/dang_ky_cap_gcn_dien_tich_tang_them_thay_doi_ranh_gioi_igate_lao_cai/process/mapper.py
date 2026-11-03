"""Map dữ kiện nguồn → ô Form.io bước 1 cho thủ tục 1.115693 (Lào Cai, cổng iGate mới — cấp phường/xã).

Chọn người GIỮ NGUYÊN mapper cổng cũ (dang_ky_cap_gcn_dien_tich_tang_them_thay_doi_ranh_gioi/process/mapper.py): người nộp theo
mốc tài khoản (chỉ điền khi hồ sơ có giấy tờ của CHÍNH người đăng nhập) hoặc theo tờ khai; chủ hồ sơ = người sử dụng
đất đứng tên mục 1.1 của Đơn, phát đủ cả 3 ô địa chỉ; cảnh báo nơi thường trú trùng địa chỉ thửa, số định danh sai độ
dài. Mapper cổng cũ cùng khuôn với 1.115682/1.115686/1.115689/1.115690 (Đối tượng "Cá nhân"/"Tổ chức") nên phần đổi ô
CongDan_*/ChuHoSo_* sang data[...] dùng chung `su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai.process.mapper.doi_ten_o`.
"""

from app.pipelines.dang_ky_cap_gcn_dien_tich_tang_them_thay_doi_ranh_gioi.process import mapper as _goc
from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai.process.mapper import doi_ten_o


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    return doi_ten_o(_goc, fields, options)
