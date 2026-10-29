"""Map dữ kiện nguồn → ô Form.io bước 1 cho thủ tục 1.115682 (Lào Cai, cổng iGate mới — cấp phường/xã).

Chọn người GIỮ NGUYÊN mapper cổng cũ (su_dung_dat_ket_hop_da_muc_dich_cap_xa/process/mapper.py):
  • Chủ hồ sơ = người sử dụng đất (cá nhân, hoặc tổ chức có tên/MST); địa chỉ = nơi thường trú, KHÔNG lấy địa chỉ thửa.
  • Người nộp chỉ điền khi hồ sơ có giấy tờ của CHÍNH người đăng nhập (chủ hồ sơ tự nộp hoặc bên được uỷ quyền); cán bộ
    nộp thay mà không có giấy tờ của mình → để trống + cảnh báo. Bổ khuyết chéo chỉ khi hai khối là một người.
  • Giữ các cảnh báo nghiệp vụ: lệch diện tích kết hợp Đơn/Thuyết minh, vượt 50% diện tích thửa, nơi thường trú trùng
    khít địa chỉ thửa đất, số định danh sai độ dài.
Ở đây ĐỔI TÊN ô CongDan_* / ChuHoSo_* sang data[...]:
  • Họ tên / CCCD / Ngày sinh / Dân tộc / Tên đơn vị + MST người nộp: cổng mới KHOÁ theo tài khoản hoặc ẩn.
  • Nơi cấp: chỉ 2 option (Bộ Công An / Cục CS QLHC về TTXH) → nơi cấp khác để trống + cảnh báo.
  • Đối tượng "Cá nhân" giữ nguyên; "Tổ chức" → "Doanh nghiệp" (công ty, HTX…) hoặc "Tổ chức" theo tên.
  • Lệnh XOÁ ô nhân thân tài khoản của chế độ theo tờ khai (_shared/lao_cai_nguoi_nop) bỏ đi: cổng mới không đổ sẵn.
  • Đơn theo QĐ 47/2026 là Mẫu số 20 (cổng cũ ghi Mẫu số 13 của NĐ 102) → không cảnh báo sai mẫu với Mẫu 20.
`doi_ten_o(goc, …)` là phần đổi tên ô, dùng chung với 1.115685 (xac_dinh_lai_dien_tich_dat_o_igate_lao_cai) vì mapper
cổng cũ của hai thủ tục cùng một khuôn.
Theo tờ khai mà người theo tờ khai KHÁC tài khoản → bỏ trống khối người nộp + cảnh báo. Ô (*) thiếu → dom-expect. KHÔNG
tích "Người nộp hồ sơ là chủ hồ sơ".
"""

import re

from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process import mapper as _igate
from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_cap_xa.process import mapper as _goc
from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai.process.schema import UI_COMP_BY_NAME

_TEN_O = {
    "CongDan_gioiTinhCongDan": "data[gender]",
    "CongDan_ngayCapCmnd": "data[identityDate]",
    "CongDan_noiCapCmnd": "data[idIssuePlace]",
    "CongDan_maTinhThanh": "data[province]",
    "CongDan_maPhuongXa": "data[district]",
    "CongDan_diaChi": "data[address]",
    "CongDan_diDong": "data[phoneNumber]",
    "CongDan_email": "data[email]",
    "CongDan_fax": "data[fax]",
    "ChuHoSo_maDoiTuongNopHS": "data[ChuHS]",
    "ChuHoSo_tenCoQuanToChucCHS": "data[ownerOrganizationFullname]",
    "ChuHoSo_maSoThueChuHoSo": "data[ownerTaxCode]",
    "ChuHoSo_tenChuHoSo": "data[ownerFullname]",
    "ChuHoSo_soCMNDChuHoSo": "data[ownerIdentityNumber]",
    "ChuHoSo_ngaySinhChuHoSo": "data[ownerBirthday]",
    "ChuHoSo_gioiTinhChuHoSo": "data[ownerGender]",
    "ChuHoSo_ngayCapCMNDCHS": "data[ownerIdentityDate]",
    "ChuHoSo_noiCapCMNDCHS": "data[ownerIdentityAgency22]",
    "ChuHoSo_maTinhThanhCHS": "data[ownerProvince]",
    "ChuHoSo_maPhuongXaCHS": "data[ownerDistrict]",
    "ChuHoSo_diaChiChuHoSo": "data[ownerAddress]",
    "ChuHoSo_diDongLienLacCHS": "data[ownerPhoneNumber]",
    "ChuHoSo_emailChuHoSo": "data[ownerEmail]",
    "ChuHoSo_faxChuHoSo": "data[ownerFax]",
}
_NOI_CAP = {"CongDan_noiCapCmnd", "ChuHoSo_noiCapCMNDCHS"}
_GIOI_TINH = {"CongDan_gioiTinhCongDan", "ChuHoSo_gioiTinhChuHoSo"}

_EXPECT_NGUOI_NOP = ("data[province]", "data[district]", "data[address]", "data[phoneNumber]")
_EXPECT_CA_NHAN = ("data[ownerFullname]", "data[ownerIdentityNumber]", "data[ownerGender]")
_EXPECT_TO_CHUC = ("data[ownerOrganizationFullname]", "data[ownerTaxCode]")
_EXPECT_DIA_CHI_CHU = ("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", "data[ownerPhoneNumber]")

_CAU_READONLY = re.compile(r' Hai ô "Họ và tên" và "Số Căn cước" của khối người nộp.*?Số Căn cước\)\.')


def _dia_chi(value):
    """_goc._area đọc khoá diaChi; schema mô tả chiTietDuoiXa → chép sang diaChi ở mọi object địa chỉ."""
    if isinstance(value, list):
        return [_dia_chi(item) for item in value]
    if not isinstance(value, dict):
        return value
    value = {key: _dia_chi(item) for key, item in value.items()}
    if not value.get("diaChi") and value.get("chiTietDuoiXa"):
        value["diaChi"] = value["chiTietDuoiXa"]
    return value


def _cung_nguoi(so_a, ten_a, so_b, ten_b) -> bool:
    so_a, so_b = _goc._digits(so_a), _goc._digits(so_b)
    if so_a and so_b:
        return so_a == so_b
    return bool(_goc._fold(ten_a)) and _goc._fold(ten_a) == _goc._fold(ten_b)


def _gioi_tinh(value) -> str | None:
    return {"nam": "Nam", "nu": "Nữ"}.get(_goc._fold(value))


def _sua_canh_bao(warning: str) -> str:
    warning = _CAU_READONLY.sub(" Họ tên/Số CCCD/Ngày sinh người nộp do cổng KHOÁ theo tài khoản đăng nhập.", warning)
    return re.sub(r"Nút \"Người nộp là chủ hồ sơ\" của cổng KHÔNG sao chép\s+địa chỉ, cán bộ", "Cán bộ", warning)


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    out, warnings = doi_ten_o(_goc, fields, options)
    # Đơn Mẫu số 20 (QĐ 47/2026/QĐ-UBND) là mẫu đúng của cổng mới — bỏ cảnh báo "không phải Mẫu số 13".
    values = _goc._by_name(fields)
    if "20" in re.sub(r"\D", " ", str(values.get("Don_MauSo") or "")).split():
        warnings = [w for w in warnings if not w.startswith("Đơn trong hồ sơ in tiêu đề")]
    return out, [w.replace("Đơn Mẫu số 13", "Đơn đề nghị") for w in warnings]


def doi_ten_o(goc, fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    """Chạy mapper cổng cũ `goc` (họ 1.115682/1.115685: ChuHoSo_maDoiTuongNopHS = "Cá nhân"/"Tổ chức") rồi đổi
    ô CongDan_*/ChuHoSo_* sang data[...] của "FORM NGUOI NOP"."""
    fields = [{**f, "value": _dia_chi(f.get("value"))} for f in fields]
    old, warnings = goc.enrich(fields, options)
    old_values = {f["name"]: f.get("value") for f in old if not f.get("clear")}
    ctx = (options or {}).get("formContext") or {}
    ctx_id = ctx.get("applicantIdentityNumber") or ctx.get("identityNumber")
    ctx_name = ctx.get("applicantFullname")
    theo_to_khai = str((options or {}).get("submitterMode") or "") == "owner_as_submitter"

    # Theo tờ khai: cổng cũ ghi đè Họ tên/CCCD người nộp; cổng mới khoá theo tài khoản → lệch thì không điền khối này.
    bo_nguoi_nop = False
    to_khai_ten, to_khai_so = old_values.get("CongDan_tenCongDan"), old_values.get("CongDan_soCmnd")
    if theo_to_khai and to_khai_ten and (_goc._digits(ctx_id) or _goc._fold(ctx_name)) and not _cung_nguoi(
        to_khai_so, to_khai_ten, ctx_id, ctx_name
    ):
        bo_nguoi_nop = True
        warnings = [w for w in warnings if "theo TỜ KHAI" not in w]
        warnings.append(
            "Bật \"Lấy người nộp theo tờ khai\" nhưng tài khoản đang đăng nhập là " + (ctx_name or "người khác")
            + ", không phải " + to_khai_ten + ". Cổng mới KHOÁ Họ tên/Số CCCD/Ngày sinh người nộp theo tài khoản "
            "nên không sửa được — đăng nhập đúng tài khoản người đi nộp. Trợ lý để trống phần còn lại của khối "
            "người nộp."
        )
    warnings = [_sua_canh_bao(w) for w in warnings]

    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value) -> None:
        if name in seen or value in (None, ""):
            return
        out.append({"name": name, "comp": UI_COMP_BY_NAME[name], "value": value})
        seen.add(name)

    for field in old:
        name = _TEN_O.get(field["name"])
        value = field.get("value")
        if not name or field.get("clear") or value in (None, ""):
            continue
        if bo_nguoi_nop and field["name"].startswith("CongDan_"):
            continue
        if field["name"] in _NOI_CAP:
            label = _igate._noi_cap(value)
            if not label:
                warnings.append(
                    f"Nơi cấp CCCD ghi \"{value}\" — ô \"Nơi cấp giấy tờ tùy thân\" của cổng chỉ có Bộ Công An / Cục "
                    "Cảnh sát QLHC về TTXH, cán bộ kiểm tra lại."
                )
                continue
            value = label
        elif field["name"] in _GIOI_TINH:
            value = _gioi_tinh(value)
        elif name == "data[ChuHS]":
            value = _igate._CHU_HS_CA_NHAN if _goc._fold(value) == "ca nhan" else _igate._loai_to_chuc(
                old_values.get("ChuHoSo_tenCoQuanToChucCHS") or ""
            )
        add(name, value)

    expect = list(_EXPECT_NGUOI_NOP)
    to_chuc = _goc._fold(old_values.get("ChuHoSo_maDoiTuongNopHS")) not in ("", "ca nhan")
    expect += _EXPECT_TO_CHUC if to_chuc else _EXPECT_CA_NHAN
    expect += _EXPECT_DIA_CHI_CHU
    for name in expect:
        if name not in seen:
            out.append({"name": name, "comp": "dom-expect", "value": ""})
            seen.add(name)
    return out, warnings
