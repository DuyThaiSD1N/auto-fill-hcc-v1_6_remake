"""Map dữ kiện nguồn → ô Form.io bước 1 cho thủ tục 1.115677 (Lào Cai, cổng iGate mới).

Chọn người GIỮ NGUYÊN mapper cổng cũ (xac_nhan_tiep_tuc_dat_nong_nghiep/process/mapper.py): người nộp theo mốc tài khoản
(vợ/chồng cùng đứng tên mục 1 Đơn Mẫu số 39 được dùng địa chỉ/liên hệ mục 2, người ngoài hộ thì không) hoặc theo tờ
khai; chủ hồ sơ = người đứng tên ĐẦU TIÊN mục 1 Đơn (CCCD → Đơn → giấy tờ khác), tổ chức → tên + MST + trụ sở. Ở đây
chỉ ĐỔI TÊN ô CongDan_* / ChuHoSo_* sang data[...] của form "FORM NGUOI NOP":
  • Họ tên / Số CCCD / Ngày sinh / Dân tộc / Tên tổ chức + MST người nộp: cổng mới KHOÁ theo tài khoản hoặc không có
    ô → không phát; riêng Họ tên / CCCD / Ngày sinh ở chế độ theo tờ khai mà khác tài khoản → phát kèm enableInput
    (lệnh xoá của cổng cũ thành xoá + tô đỏ ô đó, _igate.o_khoa_tu_cong_cu).
  • Nơi cấp CCCD: ô mới chỉ có Bộ Công An / Cục CS QLHC về TTXH → nơi cấp khác thì để trống + cảnh báo.
  • Đối tượng chủ hồ sơ CN/DN → ChuHS "Cá nhân" / "Doanh nghiệp" hoặc "Tổ chức" theo tên tổ chức.
Chế độ THEO TỜ KHAI mà người theo tờ khai KHÁC tài khoản: bỏ khoá Họ tên/CCCD/Ngày sinh rồi ghi cả khối người nộp theo
tờ khai + cảnh báo. Ô (*) thiếu dữ liệu → dom-expect. KHÔNG tích "Người nộp hồ sơ
là chủ hồ sơ".
"""

from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process import mapper as _igate
from app.pipelines.xac_nhan_tiep_tuc_dat_nong_nghiep.process import mapper as _goc
from app.pipelines.xac_nhan_tiep_tuc_dat_nong_nghiep_igate_lao_cai.process.schema import UI_COMP_BY_NAME

# Ô cổng cũ → ô Form.io cổng mới. Ô không có trong bảng (Họ tên/CCCD/Ngày sinh người nộp, Dân tộc…) bị bỏ.
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

_EXPECT_NGUOI_NOP = ("data[province]", "data[district]", "data[address]", "data[phoneNumber]")
_EXPECT_CA_NHAN = ("data[ownerFullname]", "data[ownerIdentityNumber]", "data[ownerGender]")
_EXPECT_TO_CHUC = ("data[ownerOrganizationFullname]", "data[ownerTaxCode]")
_EXPECT_DIA_CHI_CHU = ("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", "data[ownerPhoneNumber]")


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    old, warnings = _goc.enrich(fields, options)
    old_values = {f["name"]: f.get("value") for f in old if not f.get("clear")}
    theo_to_khai = str((options or {}).get("submitterMode") or "") == "owner_as_submitter"

    # Theo tờ khai: cổng cũ ghi đè Họ tên/CCCD người nộp; cổng mới khoá theo tài khoản → khác tài khoản (hoặc không có
    # mốc) thì bỏ khoá ba ô Họ tên/CCCD/Ngày sinh rồi ghi đè (_igate.o_khoa_tu_cong_cu).
    mo_khoa = False
    if theo_to_khai and old_values.get("CongDan_tenCongDan"):
        ctx = (options or {}).get("formContext") or {}
        ctx_id = _goc._id_number(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
        ctx_name = _goc._person_name(ctx.get("applicantFullname"))
        nguoi = {"HoTen": old_values.get("CongDan_tenCongDan"), "SoDinhDanh": old_values.get("CongDan_soCmnd")}
        lech = _goc._canh_bao_lech_tai_khoan(nguoi, ctx_id, ctx_name) if (ctx_id or ctx_name) else None
        mo_khoa = bool(lech) or not (ctx_id or ctx_name)
        if mo_khoa:
            warnings = [w for w in warnings if w != lech]
            warnings.append(_igate.canh_bao_mo_khoa(_goc._person_name(nguoi["HoTen"]), ctx_name))

    out: list[dict] = []
    seen: set[str] = set()
    for field in old:
        name = _TEN_O.get(field["name"])
        value = field.get("value")
        if not name or field.get("clear") or value in (None, ""):
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
            value = (
                _igate._loai_to_chuc(old_values.get("ChuHoSo_tenCoQuanToChucCHS") or "")
                if value == _goc._DOI_TUONG_TO_CHUC else _igate._CHU_HS_CA_NHAN
            )
        if name in seen:
            continue
        out.append({"name": name, "comp": UI_COMP_BY_NAME[name], "value": value})
        seen.add(name)
    if mo_khoa:
        _igate.ghi_o_khoa(out, seen, _igate.o_khoa_tu_cong_cu(old))

    expect = list(_EXPECT_NGUOI_NOP)
    to_chuc = old_values.get("ChuHoSo_maDoiTuongNopHS") == _goc._DOI_TUONG_TO_CHUC
    expect += _EXPECT_TO_CHUC if to_chuc else _EXPECT_CA_NHAN
    expect += _EXPECT_DIA_CHI_CHU
    for name in expect:
        if name not in seen:
            out.append({"name": name, "comp": "dom-expect", "value": ""})
            seen.add(name)
    return out, warnings
