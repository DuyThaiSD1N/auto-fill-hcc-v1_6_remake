"""Map dữ kiện nguồn → ô Form.io bước 1 cho thủ tục 1.115650 (Lào Cai, cổng iGate mới).

Chọn người nộp như pipeline cổng cũ (giao_thue_dat_lao_cai/process/mapper.py — dùng lại các hàm gom ứng viên của file
đó): theo tài khoản → người trong hồ sơ KHỚP mốc tài khoản (CCCD → người ghi trong giấy tờ → bên được ủy quyền → khối
phẳng); theo tờ khai → bên được ủy quyền → khối NguoiNop_* → chủ hồ sơ cá nhân.

Cổng mới KHOÁ Họ tên/CCCD/Ngày sinh người nộp theo tài khoản (không ghi được ở chế độ nào), nên khối người nộp chỉ điền
Giới tính, Ngày/Nơi cấp, Tỉnh → Phường/Xã → Địa chỉ, SĐT, Email của ĐÚNG người đang đăng nhập; người theo tờ khai lệch tài
khoản → để trống + cảnh báo. Khối chủ hồ sơ điền thẳng từ giấy tờ (thường là TỔ CHỨC xin giao/thuê đất làm dự án);
KHÔNG tích "Người nộp hồ sơ là chủ hồ sơ". Ô (*) thiếu dữ liệu → dom-expect.
"""

from app.pipelines._shared.area_remap import province_label
from app.pipelines._shared.formatting import upper_person_name
from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.process.mapper import _gioi_tinh, _noi_cap
from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process import mapper as _igate
from app.pipelines.giao_thue_dat_igate_lao_cai.process.schema import UI_ALIASES, UI_COMP_BY_NAME
from app.pipelines.giao_thue_dat_lao_cai.process import mapper as _goc

_EXPECT_NGUOI_NOP = ("data[province]", "data[district]", "data[address]", "data[phoneNumber]")


def _area(value) -> dict | None:
    """_goc._area đọc khoá diaChi/chiTiet; schema mô tả chiTietDuoiXa → nhận cả hai."""
    if isinstance(value, dict) and not value.get("diaChi") and value.get("chiTietDuoiXa"):
        value = {**value, "diaChi": value.get("chiTietDuoiXa")}
    return _goc._area(value)


def _province(area: dict) -> str | None:
    return province_label(_goc._strip_admin_prefix(area.get("tinh")))


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _goc._by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()
    warnings: list[str] = []

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if name in UI_ALIASES:
            field["aliases"] = UI_ALIASES[name]
        out.append(field)
        seen.add(name)

    def expect(*names: str) -> None:
        for name in names:
            if name not in seen:
                out.append({"name": name, "comp": "dom-expect", "value": ""})
                seen.add(name)

    is_org = _goc._is_org(values)
    ten_to_chuc = _goc._plain(values.get("ChuHoSo_TenToChuc"))
    ma_so_thue = _goc._tax_code(values.get("ChuHoSo_MaSoThue"))

    ctx = (options or {}).get("formContext") or {}
    anchor_id = _goc._digits(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    anchor_name = _goc._fold(ctx.get("applicantFullname") or ctx.get("fullname"))
    has_anchor = bool(anchor_id or anchor_name)
    theo_to_khai = str((options or {}).get("submitterMode") or "") == "owner_as_submitter"

    proxy = _goc._proxy_person(values)
    nop_block = _goc._person_block(values, "NguoiNop")
    chs_block = _goc._person_block(values, "ChuHoSo")
    candidates = _goc._merge_candidates(
        _goc._people(values, "DanhSachCccd"),
        _goc._people(values, "NguoiTrongGiayTo"),
        [proxy] if proxy else [],
        [nop_block] if nop_block else [],
        [chs_block] if not is_org and chs_block else [],
    )

    # ----- Khối NGƯỜI NỘP -----
    if theo_to_khai:
        base = proxy or nop_block or (None if is_org else chs_block)
        nguoi_nop = next(iter(_goc._merge_candidates([base], candidates)), None) if base else None
        if nguoi_nop and has_anchor and not _goc._match_anchor(nguoi_nop, anchor_id, anchor_name):
            warnings.append(
                "Bật \"Lấy người nộp theo tờ khai\" nhưng tài khoản đang đăng nhập là "
                + (_goc._plain(ctx.get("applicantFullname")) or "người khác")
                + ", không phải " + (_goc._plain(_goc._get(nguoi_nop, "HoTen")) or "người nộp trong hồ sơ")
                + ". Cổng mới KHOÁ Họ tên/Số CCCD/Ngày sinh người nộp theo tài khoản nên không sửa được — đăng nhập "
                "đúng tài khoản người đi nộp. Trợ lý để trống phần còn lại của khối người nộp."
            )
            nguoi_nop = None
        elif not nguoi_nop:
            warnings.append(
                "Bật \"Lấy người nộp theo tờ khai\" nhưng hồ sơ không ghi người được ủy quyền / người nộp — khối "
                "\"Thông tin người nộp hồ sơ\" để trống, cán bộ nhập tay."
            )
    else:
        nguoi_nop = next(
            (p for p in candidates if _goc._match_anchor(p, anchor_id, anchor_name)), None
        ) if has_anchor else None
        if not has_anchor:
            warnings.append(
                "Không đọc được tài khoản định danh đang đăng nhập trên cổng — trợ lý bỏ trống nhân thân khối "
                "\"Thông tin người nộp hồ sơ\" để khỏi điền nhầm người. Đăng nhập rồi quét lại."
            )
        elif not nguoi_nop:
            warnings.append(
                "Hồ sơ không có giấy tờ nào ghi nhân thân của CHÍNH người đang đăng nhập"
                + (f" ({_goc._plain(ctx.get('applicantFullname'))})" if ctx.get("applicantFullname") else "")
                + " nên Giới tính/Ngày cấp/Nơi cấp/Địa chỉ/SĐT của khối người nộp để trống — cán bộ nhập tay."
            )

    nop_area = None
    if nguoi_nop:
        nop_so = _goc._digits(_goc._get(nguoi_nop, "SoDinhDanh"))
        nop_ngay_cap = _goc._date(_goc._get(nguoi_nop, "NgayCap"))
        noi_cap_raw = _goc._get(nguoi_nop, "NoiCap")
        add("data[gender]", _gioi_tinh(_goc._get(nguoi_nop, "GioiTinh")))
        add("data[identityDate]", nop_ngay_cap)
        add("data[idIssuePlace]", _noi_cap(noi_cap_raw, nop_ngay_cap, nop_so))
        if _goc._plain(noi_cap_raw) and "data[idIssuePlace]" not in seen:
            warnings.append(
                f"Nơi cấp CCCD của người nộp ghi \"{_goc._plain(noi_cap_raw)}\" — ô \"Nơi cấp giấy tờ tùy thân\" của "
                "cổng chỉ có Bộ Công An / Cục Cảnh sát QLHC về TTXH, cán bộ kiểm tra lại."
            )
        nop_area = _area(_goc._get(nguoi_nop, "NoiCuTru"))
        if nop_area:
            # Tỉnh TRƯỚC Phường/Xã: đổi tỉnh là cổng reset Phường/Xã.
            add("data[province]", _province(nop_area))
            add("data[district]", _goc._plain(nop_area.get("xa")))
            add("data[address]", _goc._plain(nop_area.get("diaChi")))
        add("data[phoneNumber]", _goc._phone(_goc._get(nguoi_nop, "DienThoai")))
        add("data[email]", _goc._plain(_goc._get(nguoi_nop, "Email")))
    expect(*_EXPECT_NGUOI_NOP)

    # ----- Khối CHỦ HỒ SƠ: ChuHS là driver → phát trước. -----
    chu = None
    if is_org:
        add("data[ChuHS]", _igate._loai_to_chuc(ten_to_chuc) if ten_to_chuc else "Doanh nghiệp")
        add("data[ownerOrganizationFullname]", ten_to_chuc.upper() if ten_to_chuc else None)
        add("data[ownerTaxCode]", ma_so_thue)
        if not ten_to_chuc:
            warnings.append("Hồ sơ của tổ chức nhưng không đọc được tên tổ chức — cán bộ nhập tay ở khối chủ hồ sơ.")
        expect("data[ownerOrganizationFullname]", "data[ownerTaxCode]")
    else:
        add("data[ChuHS]", _igate._CHU_HS_CA_NHAN)
        # Khối phẳng ChuHoSo_* thường chỉ có tên + số; bù nhân thân từ CCCD/giấy tờ khác của CHÍNH người đó.
        chu = next(iter(_goc._merge_candidates([chs_block], candidates)), None) if chs_block else None
        chu_so = _goc._digits(_goc._get(chu, "SoDinhDanh"))
        chu_ngay_cap = _goc._date(_goc._get(chu, "NgayCap"))
        add("data[ownerFullname]", upper_person_name(_goc._plain(_goc._get(chu, "HoTen"))))
        add("data[ownerIdentityNumber]", chu_so)
        add("data[ownerIdentityDate]", chu_ngay_cap)
        add("data[ownerIdentityAgency22]", _noi_cap(_goc._get(chu, "NoiCap"), chu_ngay_cap, chu_so))
        add("data[ownerBirthday]", _goc._date(_goc._get(chu, "NgaySinh")))
        add("data[ownerGender]", _gioi_tinh(_goc._get(chu, "GioiTinh")))
        expect("data[ownerFullname]", "data[ownerIdentityNumber]", "data[ownerGender]")

    # Địa chỉ chủ hồ sơ: trụ sở (tổ chức) / nơi cư trú (cá nhân). Chỉ mượn địa chỉ người nộp khi chính chủ hồ sơ
    # cá nhân đi nộp — với tổ chức, nơi ở của người đi nộp KHÔNG phải trụ sở.
    chs_area = _area(values.get("ChuHoSo_NoiCuTru")) or (_area(_goc._get(chu, "NoiCuTru")) if chu else None)
    if not chs_area and chu and nguoi_nop and _goc._match_anchor(
        chu, _goc._digits(_goc._get(nguoi_nop, "SoDinhDanh")) or "", _goc._fold(_goc._get(nguoi_nop, "HoTen"))
    ):
        chs_area = nop_area
    if chs_area:
        add("data[ownerProvince]", _province(chs_area))
        add("data[ownerDistrict]", _goc._plain(chs_area.get("xa")))
        add("data[ownerAddress]", _goc._plain(chs_area.get("diaChi")))
    else:
        warnings.append("Không đọc được địa chỉ chủ hồ sơ — cán bộ nhập tay Tỉnh/Phường-Xã/Địa chỉ ở khối chủ hồ sơ.")
    add("data[ownerPhoneNumber]", _goc._phone(values.get("ChuHoSo_DienThoai") or _goc._get(chu, "DienThoai")))
    add("data[ownerEmail]", _goc._plain(values.get("ChuHoSo_Email") or _goc._get(chu, "Email")))
    expect("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", "data[ownerPhoneNumber]")

    return out, warnings
