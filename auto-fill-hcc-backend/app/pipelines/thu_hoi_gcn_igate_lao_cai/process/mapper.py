"""Map dữ kiện nguồn → ô Form.io bước 1 cho thủ tục 1.115687 (Lào Cai, cổng iGate mới — cấp phường/xã).

Chọn người GIỮ NGUYÊN mapper cổng cũ (thu_hoi_gcn_cap_lan_dau_khong_dung_quy_dinh_cap_lai/process/mapper.py):
  • Người nộp theo mốc tài khoản: nhân thân + NƠI THƯỜNG TRÚ từ CCCD của chính người đăng nhập, rồi người được ghi kèm
    CCCD trong Đơn/Giấy ủy quyền (nộp thay → Bên B). Theo tờ khai: người nộp = chủ hồ sơ cá nhân.
  • Chủ hồ sơ = người ĐỨNG ĐƠN (Bên A khi nộp thay), KHÔNG phải người đang đứng tên trên GCN bị cấp sai; 4 loại đối
    tượng CN/DN/CQ/TC; địa chỉ Đơn → Giấy ủy quyền → CCCD; SĐT/Email trên Đơn.
Ở đây ĐỔI TÊN ô CongDan_* / ChuHoSo_* sang data[...]:
  • Họ tên / CCCD / Ngày sinh / Dân tộc / Tên cơ quan + MST người nộp: cổng mới KHOÁ theo tài khoản hoặc không có ô.
  • Nơi cấp: chỉ 2 option (Bộ Công An / Cục CS QLHC về TTXH) → nơi cấp khác để trống + cảnh báo.
  • Đối tượng CN → "Cá nhân", DN → "Doanh nghiệp", CQ/TC → "Tổ chức" (ChuHS mới chỉ có 3 lựa chọn).
  • Lệnh XOÁ ô nhân thân tài khoản của chế độ theo tờ khai (_shared/lao_cai_nguoi_nop) bỏ đi: cổng mới không đổ sẵn.
  • SĐT người nộp: cổng cũ để tự nhập; cổng mới (*) → SĐT trên Đơn chỉ khi người nộp chính là chủ hồ sơ cá nhân.
Theo tờ khai mà người theo tờ khai KHÁC tài khoản → bỏ trống khối người nộp + cảnh báo. Ô (*) thiếu → dom-expect. KHÔNG
tích "Người nộp hồ sơ là chủ hồ sơ".
"""

from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process import mapper as _igate
from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai.process.mapper import _dia_chi
from app.pipelines.thu_hoi_gcn_cap_lan_dau_khong_dung_quy_dinh_cap_lai.process import mapper as _goc
from app.pipelines.thu_hoi_gcn_igate_lao_cai.process.schema import UI_COMP_BY_NAME

_TEN_O = {
    "CongDan_gioiTinhCongDan": "data[gender]",
    "CongDan_ngayCapCmnd": "data[identityDate]",
    "CongDan_noiCapCmnd": "data[idIssuePlace]",
    "CongDan_maTinhThanh": "data[province]",
    "CongDan_maPhuongXa": "data[district]",
    "CongDan_diaChi": "data[address]",
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
_EXPECT_TO_CHUC = ("data[ownerOrganizationFullname]",)
_EXPECT_DIA_CHI_CHU = ("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", "data[ownerPhoneNumber]")


def _cung_nguoi(person: dict | None, so, ten) -> bool:
    so_nguoi = _goc._digits((person or {}).get("SoDinhDanh"))
    if so_nguoi and _goc._digits(so):
        return so_nguoi == _goc._digits(so)
    return bool(_goc._fold(ten)) and _goc._fold((person or {}).get("HoTen")) == _goc._fold(ten)


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    # _goc._area chỉ đọc khoá diaChi; schema mô tả chiTietDuoiXa → chép sang diaChi trước khi chạy mapper cũ.
    fields = [{**f, "value": _dia_chi(f.get("value"))} for f in fields]
    old, warnings = _goc.enrich(fields, options)
    old_values = {f["name"]: f.get("value") for f in old if not f.get("clear")}
    values = _goc._by_name(fields)
    ctx = (options or {}).get("formContext") or {}
    ctx_id = _goc._digits(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    ctx_name = ctx.get("applicantFullname")
    theo_to_khai = str((options or {}).get("submitterMode") or "") == "owner_as_submitter"

    # Theo tờ khai: cổng cũ ghi đè Họ tên/CCCD người nộp; cổng mới khoá theo tài khoản → lệch thì không điền khối này.
    bo_nguoi_nop = False
    to_khai_nguoi = {"HoTen": old_values.get("CongDan_tenCongDan"), "SoDinhDanh": old_values.get("CongDan_soCmnd")}
    if theo_to_khai and to_khai_nguoi["HoTen"] and (ctx_id or ctx_name) and not _cung_nguoi(
        to_khai_nguoi, ctx_id, ctx_name
    ):
        bo_nguoi_nop = True
        warnings = [w for w in warnings if "đang điền nhân thân theo TỜ KHAI" not in w]
        warnings.append(
            "Bật \"Lấy người nộp theo tờ khai\" nhưng tài khoản đang đăng nhập là " + (ctx_name or "người khác")
            + ", không phải " + to_khai_nguoi["HoTen"] + ". Cổng mới KHOÁ Họ tên/Số CCCD/Ngày sinh người nộp theo "
            "tài khoản nên không sửa được — đăng nhập đúng tài khoản người đi nộp. Trợ lý để trống phần còn lại của "
            "khối người nộp."
        )

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

    # SĐT/Email người nộp: chỉ khi người nộp CHÍNH LÀ chủ hồ sơ cá nhân đứng Đơn (số trên Đơn là của người đó).
    if not bo_nguoi_nop:
        if theo_to_khai and to_khai_nguoi["HoTen"]:
            nop_so, nop_ten = to_khai_nguoi["SoDinhDanh"], to_khai_nguoi["HoTen"]
        else:
            nop_so, nop_ten = ctx_id, ctx_name
        chu = {"HoTen": old_values.get("ChuHoSo_tenChuHoSo"), "SoDinhDanh": old_values.get("ChuHoSo_soCMNDChuHoSo")}
        if chu["HoTen"] and (nop_so or nop_ten) and _cung_nguoi(chu, nop_so, nop_ten):
            add("data[phoneNumber]", _goc._phone(values.get("Don_DienThoai")))
            add("data[email]", _goc._email(values.get("Don_Email")))

    expect = list(_EXPECT_NGUOI_NOP)
    to_chuc = old_values.get("ChuHoSo_maDoiTuongNopHS") not in (None, _goc._DOI_TUONG_CA_NHAN)
    expect += _EXPECT_TO_CHUC if to_chuc else _EXPECT_CA_NHAN
    expect += _EXPECT_DIA_CHI_CHU
    for name in expect:
        if name not in seen:
            out.append({"name": name, "comp": "dom-expect", "value": ""})
            seen.add(name)
    return out, warnings
