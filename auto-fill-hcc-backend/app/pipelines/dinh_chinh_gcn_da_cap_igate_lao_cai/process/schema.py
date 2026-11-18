"""Compact schema cho thủ tục 1.115686 — Lào Cai, cổng iGate MỚI (Form.io), cấp phường/xã.

Dữ kiện nguồn giữ schema pipeline cổng cũ (dinh_chinh_gcn_da_cap_lao_cai): CCCD, người trong giấy tờ, bên được ủy quyền,
khối ChuHoSo_*/NguoiNop_*, nội dung đính chính, số hiệu GCN, thửa đất, người đồng sử dụng — thêm Don_KinhGui cho ô
"Kính gửi" của Đơn Mẫu 24 trên cổng mới.

Bước 1 "Thông tin hồ sơ" (crawl 18/11/2026, dichvucongtest, UBND Phường Yên Bái, apply-online 6aa4cbe1…a768) có HAI
form Form.io nối nhau:
  1. "FORM NGUOI NOP" (bgdvbcc) — bảng ô chung của su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai + ô "Ghi chú"
     data[tenHoSo];
  2. eForm "HCC 1.115661 Mau so 24" (Đơn đăng ký biến động đất đai) — Kính gửi, mục 1 a)–d) người sử dụng đất, mục 2
     nội dung biến động, mục 3 giấy tờ kèm (2)/(3), tỉnh + ngày ký, người viết đơn.
⚠ Form 2 dùng LẠI tên ô data[fullname]/data[identityNumber]/data[address]/data[phoneNumber]/data[email] của form 1 →
mapper ghim occurrence 0 (người nộp) / 1 (Đơn). Không ghim thì extension chọn ô ĐẦU TIÊN KHÔNG disabled — họ tên/CCCD
người nộp đang khoá nên ô của Đơn bị ghi nhầm.
"""

from app.pipelines.dinh_chinh_gcn_da_cap_lao_cai.process.schema import ALIASES
from app.pipelines.dinh_chinh_gcn_da_cap_lao_cai.process.schema import COMPACT_COMP_BY_NAME as _COMPACT_GOC
from app.pipelines.dinh_chinh_gcn_da_cap_lao_cai.process.schema import FIELDS as _FIELDS_GOC
from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai.process.schema import UI_ALIASES
from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai.process.schema import UI_COMP_BY_NAME as _UI_CHUNG

__all__ = ["ALIASES", "ALLOWED", "COMPACT_COMP_BY_NAME", "FIELDS", "UI_COMP_BY_NAME", "UI_ALIASES", "UI_DON_MAU_24"]

FIELDS: list[dict] = [
    *_FIELDS_GOC,
    {
        "name": "Don_KinhGui",
        "desc": "Cơ quan ghi sau chữ 'Kính gửi:' ở đầu Đơn đăng ký biến động (Mẫu số 24), chép NGUYÊN VĂN (vd 'Chi "
                "nhánh Văn phòng đăng ký đất đai khu vực Yên Bái', 'UBND phường Yên Bái'). Đơn để trống/viết chấm "
                "chấm thì BỎ FIELD, không tự suy.",
    },
]
ALLOWED = {field["name"] for field in FIELDS}
COMPACT_COMP_BY_NAME = {**_COMPACT_GOC, "Don_KinhGui": "x-input"}

# Ô của eForm Đơn Mẫu 24 (form thứ 2 của bước 1). Ô trùng tên form người nộp phát kèm occurrence 1.
UI_DON_MAU_24 = {
    "data[kinhGui]": "dom-input",           # (*) "Kính gửi:" — cơ quan tiếp nhận
    "data[fullname]": "dom-input",          # (*) a) Tên — người sử dụng đất (cổng đổ sẵn họ tên TÀI KHOẢN)
    "data[identityNumber]": "dom-input",    # (*) b) Giấy tờ nhân thân/pháp nhân (cổng đổ sẵn CCCD tài khoản)
    "data[address]": "dom-input",           # (*) c) Địa chỉ
    "data[phoneNumber]": "dom-input",       # d) Điện thoại liên hệ (nếu có)
    "data[email]": "dom-input",             # Hộp thư điện tử (nếu có)
    "data[noiDungBienDong]": "dom-input",   # (*) textarea mục 2 "Nội dung biến động"
    "data[giayToKem2]": "dom-input",        # mục 3 (2) — (1) "Giấy chứng nhận đã cấp" in sẵn
    "data[giayToKem3]": "dom-input",        # mục 3 (3)
    "data[ngayHtTinh]": "dom-select",       # tỉnh nơi ký đơn (option "Tỉnh Lào Cai"…)
    "data[nguoiKy]": "dom-input",           # họ tên người viết đơn dưới chữ ký
}
# data[ngayHt] (", ngày dd tháng mm năm yyyy") cổng tự tính → không khai.

UI_COMP_BY_NAME = {**_UI_CHUNG, "data[tenHoSo]": "dom-input", **UI_DON_MAU_24}
