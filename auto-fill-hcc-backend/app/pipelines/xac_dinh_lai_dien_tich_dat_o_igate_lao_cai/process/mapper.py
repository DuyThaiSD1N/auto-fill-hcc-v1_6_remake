"""Map dữ kiện nguồn → ô Form.io bước 1 cho thủ tục 1.115685 (Lào Cai, cổng iGate mới — cấp phường/xã).

Chọn người GIỮ NGUYÊN mapper cổng cũ (xac_dinh_lai_dien_tich_dat_o/process/mapper.py): chủ hồ sơ = người sử dụng đất
đứng tên Đơn; người nộp chỉ điền khi hồ sơ có giấy tờ của CHÍNH người đăng nhập (chủ hồ sơ tự nộp hoặc người được ủy
quyền); giữ các cảnh báo nghiệp vụ (GCN cấp từ 01/7/2004 trở đi, Đơn không theo Mẫu số 24, địa chỉ thửa lệch tỉnh do ĐVHC
cũ, số định danh sai độ dài).

Mapper cổng cũ cùng khuôn với 1.115682 nên phần đổi ô CongDan_*/ChuHoSo_* sang data[...] dùng chung
`su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai.process.mapper.doi_ten_o` (khoá ô người nộp theo tài khoản, nơi cấp 2
option, ChuHS 3 lựa chọn, lệch tờ khai thì bỏ trống khối người nộp, dom-expect ô (*) thiếu). Bảng thành phần cổng mới
vẫn là Đơn Mẫu số 24 nên giữ nguyên cảnh báo sai mẫu của cổng cũ.
"""

from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai.process.mapper import doi_ten_o
from app.pipelines.xac_dinh_lai_dien_tich_dat_o.process import mapper as _goc


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    return doi_ten_o(_goc, fields, options)
