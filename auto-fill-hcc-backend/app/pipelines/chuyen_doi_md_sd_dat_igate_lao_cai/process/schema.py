"""Compact schema cho thủ tục 1.115651 — Lào Cai, cổng iGate MỚI (Form.io).

"Chuyển mục đích sử dụng đất; chuyển hình thức sử dụng đất; gia hạn sử dụng đất khi hết thời hạn sử dụng đất;
điều chỉnh thời hạn sử dụng đất của dự án đầu tư đối với trường hợp quy định tại khoản 1 Điều 175 Luật Đất đai".

Lào Cai chuyển từ eForm cũ (dichvucong.laocai.gov.vn, ô CongDan_*/ChuHoSo_*) sang nền iGate/Form.io dùng chung với
Lâm Đồng, Ninh Bình, Đà Nẵng… (đang chạy thử ở dichvucongtest.laocai.gov.vn/vi/padsvc/apply-online/<id>). Bước 1
"Thông tin hồ sơ" là form "FORM NGUOI NOP" (machineName hccmauchungbgd): khối NGƯỜI NỘP + khối CHỦ HỒ SƠ, không có
khối thông tin chi tiết riêng của thủ tục ("Không có thông tin chi tiết cần nhập").

Dữ kiện nguồn giữ NGUYÊN schema của pipeline cổng cũ (chuyen_doi_md_sd_dat_lao_cai) — giấy tờ không đổi theo cổng;
chỉ bảng ô UI dưới đây là mới (đối chiếu bản crawl cây component Form.io của trang).
"""

from app.pipelines.chuyen_doi_md_sd_dat_lao_cai.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

__all__ = ["ALIASES", "ALLOWED", "COMPACT_COMP_BY_NAME", "FIELDS", "UI_COMP_BY_NAME", "UI_ALIASES"]

# Ô UI Form.io (name = data[<key>]). Choices.js select → dom-select (khớp theo NHÃN option), datetime → dom-date.
#
# KHÔNG khai (cổng khoá hoặc tự tính, ghi vào là engine báo "không điền được"):
#   data[fullname], data[identityNumber], data[birthday] — logic "checkProtected": disabled khi URL có apply-online,
#       cổng đổ từ tài khoản VNeID;
#   data[organization], data[taxCode] — disabled + hidden;
#   data[chonDoiTuong] — disabled, calculateValue: có data.organization → "2" (Tổ chức/DN), không → "1" (Cá nhân);
#   data[isOwnerDossier] + nút data[copyDuLieu3] — tích là mọi ô chủ hồ sơ calculateValue chép từ khối người nộp
#       (đè lên chủ hồ sơ đã điền) → KHÔNG tích, chủ hồ sơ điền thẳng từ giấy tờ;
#   data[ownerNation] — mặc định Việt Nam; data[fax]/data[ownerFax], data[tenHoSo] (Ghi chú) — không có nguồn.
UI_COMP_BY_NAME = {
    # Khối NGƯỜI NỘP. Họ tên/CCCD/ngày sinh cổng đổ từ tài khoản và khoá; các ô dưới đây cổng để trống (bản crawl
    # sau đăng nhập: Phường/Xã, địa chỉ, SĐT đều rỗng) dù Tỉnh, Phường/Xã, Địa chỉ, SĐT là (*).
    "data[gender]": "dom-select",            # Nam "1" / Nữ "0", mặc định Nam; ẩn khi có data.organization
    "data[identityDate]": "dom-date",
    "data[idIssuePlace]": "dom-select",      # chỉ 2 option: "Bộ Công An" / "Cục Cảnh sát quản lý hành chính về TTXH"
    "data[email]": "dom-input",
    "data[phoneNumber]": "dom-input",        # (*)
    "data[province]": "dom-select",          # (*) đổi tỉnh là calculateValue reset Phường/Xã → tỉnh phát TRƯỚC
    "data[district]": "dom-select",          # (*) nhãn "Phường/Xã" (địa chỉ 2 cấp)
    "data[address]": "dom-input",            # (*)
    # Khối CHỦ HỒ SƠ. ChuHS là DRIVER: Cá nhân "1" / Doanh nghiệp "2" / Tổ chức "3" — 2|3 ẩn họ tên/CCCD/giới tính
    # (2 ẩn thêm ngày sinh + nơi cấp), khác 1 mới hiện tên tổ chức + MST → phát TRƯỚC.
    "data[ChuHS]": "dom-select",
    "data[ownerOrganizationFullname]": "dom-input",   # (*) khi ChuHS ≠ 1
    "data[ownerTaxCode]": "dom-input",                # (*) khi ChuHS ≠ 1
    # ownerFullname/ownerIdentityNumber/ownerIdentityDate/ownerGender: calculateValue chép từ người nộp nhưng
    # allowCalculateOverride=true → ghi đè được (mở trang đã thấy họ tên tài khoản nằm sẵn ở ô chủ hồ sơ).
    "data[ownerFullname]": "dom-input",               # (*)
    "data[ownerIdentityNumber]": "dom-input",         # (*)
    "data[ownerIdentityDate]": "dom-date",
    "data[ownerIdentityAgency22]": "dom-select",      # cùng 2 option như idIssuePlace
    "data[ownerBirthday]": "dom-date",
    "data[ownerGender]": "dom-select",                # (*)
    "data[ownerPhoneNumber]": "dom-input",            # (*)
    "data[ownerEmail]": "dom-input",
    "data[ownerProvince]": "dom-select",              # (*)
    "data[ownerDistrict]": "dom-select",              # (*)
    "data[ownerAddress]": "dom-input",                # (*)
}

UI_ALIASES: dict[str, list[str]] = {}
