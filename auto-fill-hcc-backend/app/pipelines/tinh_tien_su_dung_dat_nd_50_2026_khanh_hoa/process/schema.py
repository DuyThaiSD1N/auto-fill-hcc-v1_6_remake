"""Compact schema cho "Khánh Hòa - Thủ tục tính hoặc tính lại tiền sử dụng đất theo quy định tại các điểm a, b, c và d
khoản 2 Điều 12 Nghị định số 50/2026/NĐ-CP" (1.115148).

Facts nguồn (chủ hồ sơ từ Đơn + CCCD, người nộp thay, tổ chức, thửa đất) DÙNG CHUNG với bản Lâm Đồng: cùng thủ tục, cùng
bộ giấy (bộ mẫu của file mapping cũng là Đơn đề nghị cấp giấy phép xây dựng Mẫu số 01 + CCCD). Chỉ form cổng khác.

Form bước 1 "Thông tin hồ sơ" cổng iGate Khánh Hòa (file "Mapping_HoSo_NopTrucTuyen", 24/11/2026) — KHÁC template ba khối
của các thủ tục đất đai Khánh Hòa (không có province1/village1, Phần III thửa đất):
  Chủ hồ sơ  → data[ownerFullname], ownerIdentityNumber, ownerBirthday, ownerPhoneNumber, ownerAddress (MỘT ô chữ gộp cả
               địa chỉ), checkbox data[isOwnerDossier] "Người nộp hồ sơ đồng thời là chủ hồ sơ".
  Người nộp  → data[fullname], birthday, gender, email, phoneNumber, identityNumber, identityDate, identityAgency (select
               "Bộ Công An" / "Cục cảnh sát quản lý hành chính về trật tự xã hội"), noidungyeucaugiaiquyet, chonDoiTuong,
               nation, province, district (nhãn "Phường/xã"), address.
Không khai: radio data[CaNhan_ToChuc] (key có hậu tố ngẫu nhiên như các form Khánh Hòa khác), panel tổ chức thongtinTC
(chỉ hiện khi chọn "Tổ chức", nhiều ô ẩn chưa có nhãn), Bưu chính công ích, Ghi chú, Hình thức nộp (chonDoiTuong1, cổng
để sẵn "Trực tuyến"), các ô formio-hidden (village, noiCapLabel, is2Cap…). eForm "Thông tin chi tiết" rỗng.
"""

from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_lam_dong.process.schema import (  # noqa: F401
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

UI_COMP_BY_NAME = {
    # Chủ hồ sơ.
    "data[ownerFullname]": "dom-input",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerBirthday]": "dom-date",
    "data[ownerPhoneNumber]": "dom-input",
    "data[ownerAddress]": "dom-input",
    "data[isOwnerDossier]": "dom-checkbox",
    # Người nộp hồ sơ.
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[email]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[noidungyeucaugiaiquyet]": "dom-input",
    "data[chonDoiTuong]": "dom-select",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",  # nhãn "Phường/xã" (mô hình 2 cấp)
    "data[address]": "dom-input",
}
