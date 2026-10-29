"""Map dữ kiện nguồn → ô Form.io bước 1 cho thủ tục 1.115679 (Lào Cai, cổng iGate mới — bản nộp ở phường/xã).

Chọn người GIỮ NGUYÊN mapper cổng cũ (chuyen_md_sd_dat_phuong_xa_lao_cai/process/mapper.py): người nộp theo mốc tài
khoản (CCCD → người ghi kèm số CCCD trong Đơn/Giấy uỷ quyền, kể cả BÊN ĐƯỢC UỶ QUYỀN) hoặc theo tờ khai (bên được uỷ
quyền, không có thì chủ hồ sơ cá nhân); chủ hồ sơ = người sử dụng đất ở mục 1 Đơn, tổ chức chọn loại theo tên; địa chỉ
CCCD → Đơn → Giấy uỷ quyền → GCN → vị trí thửa đất. Ở đây ĐỔI TÊN ô CongDan_* / ChuHoSo_* sang data[...]:
  • Họ tên / CCCD / Ngày sinh / Dân tộc / Tên cơ quan + MST người nộp: cổng mới KHOÁ theo tài khoản hoặc không có ô.
  • Nơi cấp: chỉ 2 option (Bộ Công An / Cục CS QLHC về TTXH) → nơi cấp khác để trống + cảnh báo.
  • Đối tượng CN → "Cá nhân", DN → "Doanh nghiệp", CQ/TC → "Tổ chức" (ChuHS mới chỉ có 3 lựa chọn).
  • Lệnh XOÁ ô nhân thân tài khoản của chế độ theo tờ khai (_shared/lao_cai_nguoi_nop) bỏ đi: cổng mới không đổ sẵn.
Theo tờ khai mà người theo tờ khai KHÁC tài khoản → bỏ trống khối người nộp + cảnh báo. Ô (*) thiếu → dom-expect. KHÔNG
tích "Người nộp hồ sơ là chủ hồ sơ".
"""

from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process import mapper as _igate
from app.pipelines.chuyen_md_sd_dat_phuong_xa_igate_lao_cai.process.schema import UI_COMP_BY_NAME
from app.pipelines.chuyen_md_sd_dat_phuong_xa_lao_cai.process import mapper as _goc

_TEN_O = {
    "CongDan_gioiTinhCongDan": "data[gender]",
    "CongDan_ngayCapCmnd": "data[identityDate]",
    "CongDan_noiCapCmnd": "data[idIssuePlace]",
    "CongDan_maTinhThanh": "data[province]",
    "CongDan_maPhuongXa": "data[district]",
    "CongDan_diaChi": "data[address]",
    "CongDan_diDong": "data[phoneNumber]",
    "CongDan_email": "data[email]",
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
}
_NOI_CAP = {"CongDan_noiCapCmnd", "ChuHoSo_noiCapCMNDCHS"}
_CHU_HS = {
    _goc._DOI_TUONG_CA_NHAN: _igate._CHU_HS_CA_NHAN,
    _goc._DOI_TUONG_DOANH_NGHIEP: _igate._CHU_HS_DOANH_NGHIEP,
    _goc._DOI_TUONG_CO_QUAN: _igate._CHU_HS_TO_CHUC,
    _goc._DOI_TUONG_TO_CHUC_KHAC: _igate._CHU_HS_TO_CHUC,
}

_EXPECT_NGUOI_NOP = ("data[province]", "data[district]", "data[address]", "data[phoneNumber]")
_EXPECT_CA_NHAN = ("data[ownerFullname]", "data[ownerIdentityNumber]", "data[ownerGender]")
_EXPECT_TO_CHUC = ("data[ownerOrganizationFullname]", "data[ownerTaxCode]")
_EXPECT_DIA_CHI_CHU = ("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", "data[ownerPhoneNumber]")


def _dia_chi(value):
    """_goc._area chỉ đọc khoá diaChi; schema mô tả chiTietDuoiXa → chép sang diaChi ở mọi object địa chỉ."""
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


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    fields = [{**f, "value": _dia_chi(f.get("value"))} for f in fields]
    old, warnings = _goc.enrich(fields, options)
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
        warnings = [w for w in warnings if "đang điền theo TỜ KHAI" not in w and "điền theo TỜ KHAI nhưng" not in w]
        warnings.append(
            "Bật \"Lấy người nộp theo tờ khai\" nhưng tài khoản đang đăng nhập là " + (ctx_name or "người khác")
            + ", không phải " + to_khai_ten + ". Cổng mới KHOÁ Họ tên/Số CCCD/Ngày sinh người nộp theo tài khoản "
            "nên không sửa được — đăng nhập đúng tài khoản người đi nộp. Trợ lý để trống phần còn lại của khối "
            "người nộp."
        )
    warnings = [w.replace("sáu ô có dấu (*) ở khối này", "các ô có dấu (*) ở khối này") for w in warnings]

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
        elif name == "data[ChuHS]":
            value = _CHU_HS.get(value, _igate._CHU_HS_TO_CHUC)
        add(name, value)

    # Giới tính người nộp mặc định "Nam" trên cổng mới: người nộp chính là chủ hồ sơ mà hồ sơ chỉ có xưng hô Ông/Bà ở
    # Đơn (mapper cũ chỉ suy cho chủ hồ sơ) → dùng lại giới tính chủ hồ sơ.
    nop_so, nop_ten = (to_khai_so, to_khai_ten) if theo_to_khai and to_khai_ten else (ctx_id, ctx_name)
    if not bo_nguoi_nop and "data[gender]" not in seen and _cung_nguoi(
        nop_so, nop_ten, old_values.get("ChuHoSo_soCMNDChuHoSo"), old_values.get("ChuHoSo_tenChuHoSo")
    ):
        add("data[gender]", old_values.get("ChuHoSo_gioiTinhChuHoSo"))

    expect = list(_EXPECT_NGUOI_NOP)
    to_chuc = old_values.get("ChuHoSo_maDoiTuongNopHS") not in (None, _goc._DOI_TUONG_CA_NHAN)
    expect += _EXPECT_TO_CHUC if to_chuc else _EXPECT_CA_NHAN
    expect += _EXPECT_DIA_CHI_CHU
    for name in expect:
        if name not in seen:
            out.append({"name": name, "comp": "dom-expect", "value": ""})
            seen.add(name)
    return out, warnings
