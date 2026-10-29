"""Map dữ kiện nguồn → ô Form.io bước 1 cho thủ tục 1.115667 (Lào Cai, cổng iGate mới).

Chọn người như pipeline cổng cũ (cap_GCN_nhan_chuyen_nhuong/process/mapper.py — dùng lại các hàm gom ứng viên của file
đó), nhưng phát sang bộ ô data[...] của form "FORM NGUOI NOP":
  Người nộp : theo tài khoản → ứng viên (CCCD → người ghi trong giấy tờ → bên được ủy quyền → chủ hồ sơ) KHỚP mốc tài
              khoản; nhiều người trùng tên mà không đối chiếu được số → không đoán. Theo tờ khai → bên được ủy quyền →
              chủ hồ sơ. Cổng KHOÁ Họ tên/CCCD/Ngày sinh theo tài khoản nên chỉ điền Giới tính, Ngày/Nơi cấp, Tỉnh →
              Phường/Xã → Địa chỉ, SĐT, Email; người theo tờ khai lệch tài khoản → để trống + cảnh báo.
  Chủ hồ sơ : bên NHẬN chuyển nhượng. Tổ chức → Doanh nghiệp/Tổ chức + tên + MST. Cá nhân → họ tên, số, ngày sinh,
              giới tính theo CCCD (bù bằng HĐ/Đơn); ngày/nơi cấp theo HĐ (bù bằng CCCD). Địa chỉ Đơn → HĐ → CCCD.
              SĐT/Email mục 1.d) của Đơn. ChuHS là driver → phát TRƯỚC.
Giấy tờ đất đai hay chỉ ghi "Sinh năm 1957" → ô ngày sinh để trống, không bịa. KHÔNG tích "Người nộp hồ sơ là chủ hồ
sơ". Ô (*) thiếu dữ liệu → dom-expect.
"""

from app.pipelines._shared.area_remap import province_label
from app.pipelines._shared.formatting import upper_person_name
from app.pipelines.cap_GCN_nhan_chuyen_nhuong.process import mapper as _goc
from app.pipelines.cap_gcn_nhan_chuyen_nhuong_igate_lao_cai.process.schema import UI_ALIASES, UI_COMP_BY_NAME
from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.process.mapper import _gioi_tinh, _noi_cap
from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process import mapper as _igate

_EXPECT_NGUOI_NOP = ("data[province]", "data[district]", "data[address]", "data[phoneNumber]")


def _area(value) -> dict | None:
    """_goc._area chỉ đọc khoá diaChi; schema mô tả chiTietDuoiXa → nhận cả hai."""
    if isinstance(value, dict) and not value.get("diaChi") and value.get("chiTietDuoiXa"):
        value = {**value, "diaChi": value.get("chiTietDuoiXa")}
    return _goc._area(value)


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

    def add_area(names: tuple[str, str, str], area: dict) -> None:
        # Tỉnh TRƯỚC Phường/Xã: đổi tỉnh là cổng reset Phường/Xã.
        add(names[0], province_label(area.get("tinh")))
        add(names[1], _goc._plain(area.get("xa")))
        add(names[2], _goc._plain(area.get("diaChi")))

    cards = _goc._cards(values)
    org_name = _goc._plain(values.get("ChuHoSo_TenToChuc"))
    is_org = _goc._fold(values.get("ChuHoSo_LoaiDoiTuong")) == "to chuc" and bool(org_name)

    ctx = (options or {}).get("formContext") or {}
    anchor_id = _goc._digits(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    anchor_name = _goc._fold(ctx.get("applicantFullname") or ctx.get("fullname"))
    has_anchor = bool(anchor_id or anchor_name)
    theo_to_khai = str((options or {}).get("submitterMode") or "") == "owner_as_submitter"

    proxy = _goc._proxy_person(values)
    owner_person = None if is_org else _goc._owner_person(values)
    candidates = _goc._merge_candidates(
        cards,
        _goc._people(values, "NguoiTrongGiayTo"),
        [proxy] if proxy else [],
        [owner_person] if owner_person else [],
    )

    # ----- Khối NGƯỜI NỘP -----
    nguoi_nop = None
    if theo_to_khai:
        base = proxy or owner_person
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
                "Bật \"Lấy người nộp theo tờ khai\" nhưng hồ sơ không ghi người được ủy quyền / bên nhận chuyển nhượng "
                "— khối \"Thông tin người nộp hồ sơ\" để trống, cán bộ nhập tay."
            )
    elif not has_anchor:
        warnings.append(
            "Không đọc được tài khoản định danh đang đăng nhập trên cổng — trợ lý bỏ trống nhân thân khối \"Thông tin "
            "người nộp hồ sơ\" để khỏi điền nhầm người. Đăng nhập rồi quét lại."
        )
    else:
        matched = [p for p in candidates if _goc._match_anchor(p, anchor_id, anchor_name)]
        if len(matched) == 1:
            nguoi_nop = matched[0]
        elif matched:
            warnings.append(
                "Hồ sơ có nhiều người trùng họ tên với tài khoản đăng nhập mà không đối chiếu được số căn cước, trợ lý "
                "bỏ trống khối \"Thông tin người nộp hồ sơ\" để khỏi điền nhầm người — cán bộ nhập tay."
            )
        else:
            warnings.append(
                "Hồ sơ không có giấy tờ nào ghi nhân thân của CHÍNH người đang đăng nhập"
                + (f" ({_goc._plain(ctx.get('applicantFullname'))})" if ctx.get("applicantFullname") else "")
                + " nên Giới tính/Ngày cấp/Nơi cấp/Địa chỉ/SĐT của khối người nộp để trống — cán bộ nhập tay."
            )

    if nguoi_nop:
        nop_so = _goc._id_number(_goc._get(nguoi_nop, "SoDinhDanh"))
        nop_ngay_cap = _goc._full_date(_goc._get(nguoi_nop, "NgayCap"))
        noi_cap_raw = _goc._get(nguoi_nop, "NoiCap")
        add("data[gender]", _gioi_tinh(_goc._gender(nguoi_nop, None)))
        add("data[identityDate]", nop_ngay_cap)
        add("data[idIssuePlace]", _noi_cap(noi_cap_raw, nop_ngay_cap, nop_so))
        if _goc._plain(noi_cap_raw) and "data[idIssuePlace]" not in seen:
            warnings.append(
                f"Nơi cấp CCCD của người nộp ghi \"{_goc._plain(noi_cap_raw)}\" — ô \"Nơi cấp giấy tờ tùy thân\" của "
                "cổng chỉ có Bộ Công An / Cục Cảnh sát QLHC về TTXH, cán bộ kiểm tra lại."
            )
        nop_area = _area(_goc._get(nguoi_nop, "NoiCuTru"))
        if nop_area:
            add_area(("data[province]", "data[district]", "data[address]"), nop_area)
        add("data[phoneNumber]", _goc._phone(_goc._get(nguoi_nop, "DienThoai")))
        # Email mục 1.d) của Đơn là của chủ hồ sơ — chỉ dùng khi chính chủ hồ sơ đi nộp.
        if owner_person and _goc._match_anchor(
            owner_person, _goc._digits(_goc._get(nguoi_nop, "SoDinhDanh")), _goc._fold(_goc._get(nguoi_nop, "HoTen"))
        ):
            add("data[email]", _goc._email(values.get("Don_Email")))
    expect(*_EXPECT_NGUOI_NOP)

    # ----- Khối CHỦ HỒ SƠ = bên nhận chuyển nhượng. ChuHS là driver → phát trước. -----
    owner_id = _goc._id_number(values.get("ChuHoSo_SoDinhDanh"))
    owner_card = (
        _goc._card_by_id(cards, owner_id) if owner_id else _goc._card_by_name(cards, values.get("ChuHoSo_HoTen"))
    )
    chu = None
    if is_org:
        add("data[ChuHS]", _igate._loai_to_chuc(org_name))
        add("data[ownerOrganizationFullname]", org_name.upper())
        tax = _goc._digits(values.get("ChuHoSo_MaSoThue"))
        add("data[ownerTaxCode]", tax if len(tax) in (10, 13) else None)
        expect("data[ownerOrganizationFullname]", "data[ownerTaxCode]")
    else:
        add("data[ChuHS]", _igate._CHU_HS_CA_NHAN)
        # Khối ChuHoSo_* + Đơn thường thiếu ngày/nơi cấp; bù từ CCCD/giấy tờ khác của CHÍNH người đó.
        chu = next(iter(_goc._merge_candidates([owner_person], candidates)), None) if owner_person else None
        card = owner_card or {}
        chu_so = _goc._id_number(card.get("SoDinhDanh")) or owner_id or _goc._id_number(_goc._get(chu, "SoDinhDanh"))
        chu_ngay_cap = (
            _goc._full_date(values.get("ChuHoSo_NgayCap"))
            or _goc._full_date(card.get("NgayCap"))
            or _goc._full_date(_goc._get(chu, "NgayCap"))
        )
        noi_cap_raw = values.get("ChuHoSo_NoiCap") or card.get("NoiCap") or _goc._get(chu, "NoiCap")
        add("data[ownerFullname]", upper_person_name(
            _goc._plain(card.get("HoTen")) or _goc._plain(values.get("ChuHoSo_HoTen"))
        ))
        add("data[ownerIdentityNumber]", chu_so)
        add("data[ownerIdentityDate]", chu_ngay_cap)
        add("data[ownerIdentityAgency22]", _noi_cap(noi_cap_raw, chu_ngay_cap, chu_so))
        add("data[ownerBirthday]", (
            _goc._full_date(card.get("NgaySinh"))
            or _goc._full_date(values.get("ChuHoSo_NgaySinh"))
            or _goc._full_date(_goc._get(chu, "NgaySinh"))
        ))
        add("data[ownerGender]", _gioi_tinh(_goc._gender(owner_card or chu, values.get("ChuHoSo_XungHo"))))
        expect("data[ownerFullname]", "data[ownerIdentityNumber]", "data[ownerGender]")

    residence = (
        _area(values.get("ChuHoSo_DiaChiDon"))
        or _area(values.get("ChuHoSo_DiaChiHopDong"))
        or _area((owner_card or {}).get("NoiCuTru"))
        or (_area(_goc._get(chu, "NoiCuTru")) if chu else None)
    )
    if residence:
        add_area(("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]"), residence)
        if _goc._plain(residence.get("tinh")) and not _goc._plain(residence.get("xa")):
            warnings.append(
                "Địa chỉ chủ hồ sơ ghi theo đơn vị hành chính CŨ (trước sáp nhập) nên không khớp danh mục hiện hành — "
                "cán bộ chọn tay ô Phường/Xã của khối chủ hồ sơ."
            )
    else:
        warnings.append("Không đọc được địa chỉ chủ hồ sơ — cán bộ nhập tay Tỉnh/Phường-Xã/Địa chỉ ở khối chủ hồ sơ.")
    add("data[ownerPhoneNumber]", _goc._phone(values.get("Don_DienThoai")) or _goc._phone(_goc._get(chu, "DienThoai")))
    add("data[ownerEmail]", _goc._email(values.get("Don_Email")))
    expect("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", "data[ownerPhoneNumber]")

    return out, warnings
