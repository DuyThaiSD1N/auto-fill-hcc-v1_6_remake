"""Map dữ kiện nguồn → ô Form.io bước 1 cho thủ tục 1.115678 (Lào Cai, cổng iGate mới).

Chốt người nộp như pipeline cổng cũ (cho_thue_dat_thue_rung/process/mapper.py — dùng lại các hàm đối chiếu của file
đó): mốc là TÀI KHOẢN đang đăng nhập; trùng chủ hồ sơ → tự nộp (hai khối bổ khuyết cho nhau), khác → nộp thay (không
chép chéo). Khác cổng cũ ở chỗ cổng mới KHOÁ Họ tên/CCCD/Ngày sinh người nộp theo tài khoản (không ghi được ở chế độ
nào), nên:
  • Khối người nộp chỉ điền Giới tính, Ngày/Nơi cấp, Tỉnh → Phường/Xã → Địa chỉ, SĐT, Email — và CHỈ khi biết chắc
    các mục đó là của người đang đăng nhập (trùng chủ hồ sơ hoặc trùng bên được ủy quyền). Tài khoản là người thứ
    ba → để trống + cảnh báo, không gắn nhân thân người khác vào khối đã khoá tên tài khoản.
  • Khối chủ hồ sơ điền thẳng từ giấy tờ; KHÔNG tích "Người nộp hồ sơ là chủ hồ sơ" (tích là cổng chép đè).
Ô (*) không có dữ liệu → dom-expect (tô đỏ cho cán bộ gõ tay).
"""

from app.pipelines._shared.area_remap import province_label
from app.pipelines._shared.compact_agent.issuer import default_issuer
from app.pipelines._shared.formatting import upper_person_name
from app.pipelines.cho_thue_dat_thue_rung.process import mapper as _goc
from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.process.schema import UI_ALIASES, UI_COMP_BY_NAME
from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process import mapper as _igate

_GIOI_TINH = {"nam": "Nam", "nu": "Nữ"}
_EXPECT_NGUOI_NOP = ("data[province]", "data[district]", "data[address]", "data[phoneNumber]")


def _area(value) -> dict | None:
    """_goc._area đọc khoá diaChi/chiTiet; schema mô tả chiTietDuoiXa → nhận cả hai."""
    if isinstance(value, dict) and not value.get("diaChi") and value.get("chiTietDuoiXa"):
        value = {**value, "diaChi": value.get("chiTietDuoiXa")}
    return _goc._area(value)


def _gioi_tinh(value) -> str | None:
    return _GIOI_TINH.get(_goc._fold(_goc._plain(value) or ""))


def _noi_cap(raw, ngay_cap: str | None, so: str | None) -> str | None:
    """Option "Nơi cấp giấy tờ tùy thân" (chỉ Bộ Công An / Cục CS QLHC về TTXH). Giấy tờ không ghi nơi cấp mà có
    số định danh thì suy theo ngày cấp như cổng cũ; không có số thì không bịa."""
    plain = _goc._plain(raw)
    if plain:
        return _igate._noi_cap(plain)
    return _igate._noi_cap(default_issuer(ngay_cap)) if so else None


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
    ctx_id, ctx_name = _goc._account_anchor(options)
    co_moc = bool(ctx_id or ctx_name)
    theo_to_khai = str((options or {}).get("submitterMode") or "") == "owner_as_submitter"
    same_person = (_goc._cung_nguoi_theo_to_khai(values) if theo_to_khai
                   else _goc._same_person(values, ctx_id, ctx_name))

    def pick(nop_key: str, chs_key: str) -> tuple[object, object]:
        nop_raw, chs_raw = values.get(nop_key), values.get(chs_key)
        if not same_person:
            return nop_raw, chs_raw
        # Cùng một người: ưu tiên khối chủ hồ sơ — tài khoản trùng CHỦ HỒ SƠ mà giấy tờ vẫn có bên được ủy quyền
        # (ủy quyền rồi tự đi nộp) thì NguoiNop_* là người KHÁC, không được đứng trước.
        merged = chs_raw or nop_raw
        return merged, merged

    nop_ten, chs_ten = pick("NguoiNop_HoTen", "ChuHoSo_HoTen")
    nop_ngay_sinh, chs_ngay_sinh = pick("NguoiNop_NgaySinh", "ChuHoSo_NgaySinh")
    nop_gioi_tinh, chs_gioi_tinh = pick("NguoiNop_GioiTinh", "ChuHoSo_GioiTinh")
    nop_so_raw, chs_so_raw = pick("NguoiNop_SoDinhDanh", "ChuHoSo_SoDinhDanh")
    nop_ngay_cap_raw, chs_ngay_cap_raw = pick("NguoiNop_NgayCap", "ChuHoSo_NgayCap")
    nop_noi_cap_raw, chs_noi_cap_raw = pick("NguoiNop_NoiCap", "ChuHoSo_NoiCap")
    nop_dien_thoai, chs_dien_thoai = pick("NguoiNop_DienThoai", "ChuHoSo_DienThoai")
    nop_email, chs_email = pick("NguoiNop_Email", "ChuHoSo_Email")

    nop_so = _goc._digits(nop_so_raw)
    nop_ten_fold = _goc._fold(_goc._plain(nop_ten) or "")

    # ----- Khối NGƯỜI NỘP: chỉ khi biết chắc người trong giấy tờ CHÍNH LÀ tài khoản đang đăng nhập. -----
    co_nguoi_nop = bool(nop_so or nop_ten_fold)
    khop_tai_khoan = _goc._match(ctx_id, ctx_name, nop_so, nop_ten_fold) if co_moc else None
    dien_nguoi_nop = co_nguoi_nop and khop_tai_khoan is not False
    if theo_to_khai and co_nguoi_nop and khop_tai_khoan is False:
        warnings.append(
            "Bật \"Lấy người nộp theo tờ khai\" nhưng tài khoản đang đăng nhập không phải "
            + (_goc._plain(nop_ten) or "người nộp trong hồ sơ")
            + ". Cổng mới KHOÁ Họ tên/Số CCCD/Ngày sinh người nộp theo tài khoản nên không sửa được — đăng nhập "
            "đúng tài khoản người đi nộp. Trợ lý để trống phần còn lại của khối người nộp."
        )
    elif not theo_to_khai and co_nguoi_nop and khop_tai_khoan is False:
        warnings.append(
            "⚠ Tài khoản đang đăng nhập không phải chủ hồ sơ cũng không phải người được ủy quyền ghi trong hồ sơ"
            + (f" ({_goc._plain(nop_ten)})" if _goc._plain(nop_ten) else "")
            + ". Cổng ghi người nộp theo tài khoản nên trợ lý để trống Giới tính/Ngày cấp/Nơi cấp/Địa chỉ/SĐT của "
            "khối người nộp — đăng nhập đúng tài khoản người đi nộp, hoặc cán bộ nhập tay."
        )
    elif not co_nguoi_nop:
        warnings.append(
            "Không xác định được người nộp hồ sơ từ giấy tờ — khối \"Thông tin người nộp hồ sơ\" để trống, cán bộ "
            "nhập tay."
        )

    nop_area = None
    if dien_nguoi_nop:
        nop_ngay_cap = _goc._date(nop_ngay_cap_raw)
        add("data[gender]", _gioi_tinh(nop_gioi_tinh))
        add("data[identityDate]", nop_ngay_cap)
        add("data[idIssuePlace]", _noi_cap(nop_noi_cap_raw, nop_ngay_cap, nop_so))
        if _goc._plain(nop_noi_cap_raw) and "data[idIssuePlace]" not in seen:
            warnings.append(
                f"Nơi cấp CCCD của người nộp ghi \"{_goc._plain(nop_noi_cap_raw)}\" — ô \"Nơi cấp giấy tờ tùy thân\" "
                "của cổng chỉ có Bộ Công An / Cục Cảnh sát QLHC về TTXH, cán bộ kiểm tra lại."
            )
        # Cùng một người → địa chỉ chủ hồ sơ trước (như pick): NguoiNop_* có thể là bên được ủy quyền khác người.
        if same_person:
            nop_area = _area(values.get("ChuHoSo_NoiCuTru")) or _area(values.get("NguoiNop_NoiCuTru"))
        else:
            nop_area = _area(values.get("NguoiNop_NoiCuTru"))
        if nop_area:
            # Tỉnh TRƯỚC Phường/Xã: đổi tỉnh là cổng reset Phường/Xã.
            add("data[province]", province_label(_goc._strip_admin_prefix(nop_area.get("tinh"))))
            add("data[district]", _goc._plain(nop_area.get("xa")))
            add("data[address]", _goc._plain(nop_area.get("diaChi")))
        add("data[phoneNumber]", _goc._phone(nop_dien_thoai))
        add("data[email]", _goc._plain(nop_email))
        if not same_person and not _goc._phone(nop_dien_thoai):
            warnings.append(
                "Không đọc được số điện thoại của người được ủy quyền — ô \"Số điện thoại\" (*) của khối người nộp "
                "cán bộ hỏi trực tiếp người nộp, KHÔNG lấy số của chủ hồ sơ."
            )
    if not co_moc and not theo_to_khai:
        warnings.append(
            "Chưa đọc được tài khoản định danh đang đăng nhập trên cổng, nên vai người nộp chỉ là suy đoán từ giấy "
            "tờ. Cán bộ kiểm tra lại khối \"Thông tin người nộp hồ sơ\" trước khi nộp."
        )
    expect(*_EXPECT_NGUOI_NOP)

    # ----- Khối CHỦ HỒ SƠ: ChuHS là driver → phát trước. -----
    ten_to_chuc = _goc._plain(values.get("ChuHoSo_TenToChuc"))
    if is_org and ten_to_chuc:
        add("data[ChuHS]", _igate._loai_to_chuc(ten_to_chuc))
        add("data[ownerOrganizationFullname]", ten_to_chuc.upper())
        add("data[ownerTaxCode]", _goc._tax_code(values.get("ChuHoSo_MaSoThue")))
        expect("data[ownerTaxCode]")
    else:
        if is_org:
            warnings.append("Hồ sơ của tổ chức nhưng không đọc được tên tổ chức — khối chủ hồ sơ cán bộ nhập tay.")
        add("data[ChuHS]", _igate._CHU_HS_CA_NHAN)
        chs_so = _goc._digits(chs_so_raw)
        chs_ngay_cap = _goc._date(chs_ngay_cap_raw)
        add("data[ownerFullname]", upper_person_name(_goc._plain(chs_ten)))
        add("data[ownerIdentityNumber]", chs_so)
        add("data[ownerIdentityDate]", chs_ngay_cap)
        add("data[ownerIdentityAgency22]", _noi_cap(chs_noi_cap_raw, chs_ngay_cap, chs_so))
        add("data[ownerBirthday]", _goc._date(chs_ngay_sinh))
        add("data[ownerGender]", _gioi_tinh(chs_gioi_tinh))
        expect("data[ownerFullname]", "data[ownerIdentityNumber]", "data[ownerGender]")

    chs_area = _area(values.get("ChuHoSo_NoiCuTru"))
    if not chs_area and same_person:
        chs_area = nop_area
    if chs_area:
        add("data[ownerProvince]", province_label(_goc._strip_admin_prefix(chs_area.get("tinh"))))
        add("data[ownerDistrict]", _goc._plain(chs_area.get("xa")))
        add("data[ownerAddress]", _goc._plain(chs_area.get("diaChi")))
    else:
        warnings.append("Không đọc được địa chỉ chủ hồ sơ — cán bộ nhập tay Tỉnh/Phường-Xã/Địa chỉ ở khối chủ hồ sơ.")
    add("data[ownerPhoneNumber]", _goc._phone(chs_dien_thoai))
    add("data[ownerEmail]", _goc._plain(chs_email))
    expect("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", "data[ownerPhoneNumber]")

    return out, warnings
