"""Map dữ kiện nguồn → ô Form.io bước 1 cho thủ tục 1.115651 (Lào Cai, cổng iGate mới).

Cùng ma trận nguồn với pipeline cổng cũ (chuyen_doi_md_sd_dat_lao_cai/process/mapper.py) — dùng lại các hàm
chọn người/chuẩn hoá của file đó — nhưng phát sang bộ ô data[...] của form "FORM NGUOI NOP":
  Người nộp : Họ tên/CCCD/Ngày sinh cổng KHOÁ theo tài khoản → không bao giờ phát.
              Giới tính, ngày cấp, nơi cấp, Tỉnh → Phường/Xã → Địa chỉ → giấy tờ CỦA CHÍNH người nộp (CCCD khớp
              số/họ tên tài khoản; ngày/nơi cấp còn bù từ đơn/giấy ủy quyền ghi đúng số đó).
              SĐT/Email → chỉ khi người nộp CHÍNH LÀ chủ hồ sơ (số trên Đơn là của người sử dụng đất).
              Thiếu Tỉnh/Phường-Xã/Địa chỉ/SĐT (*) → dom-expect (tô đỏ cho cán bộ gõ tay).
  Chủ hồ sơ : người sử dụng đất đứng tên Đơn. ChuHS phát TRƯỚC (driver ẩn/hiện ô).
              Cá nhân → CCCD rồi Đơn; tổ chức → tên + MST (GCN ĐKDN > Đơn).
              Địa chỉ: tổ chức → GCN ĐKDN → Đơn; cá nhân → CCCD → Đơn; cuối cùng vị trí khu đất.
              Di động/Email → Đơn → GCN ĐKDN.

⚑ HAI CHẾ ĐỘ NGƯỜI NỘP (`options.submitterMode`) như cổng cũ, nhưng cổng mới khoá Họ tên/CCCD/Ngày sinh nên chế
độ THEO TỜ KHAI chỉ bù được các ô còn lại theo chủ hồ sơ cá nhân, và cảnh báo khi tài khoản là người khác.
"""

from app.pipelines._shared.area_remap import province_label
from app.pipelines._shared.formatting import upper_person_name
from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process.schema import UI_ALIASES, UI_COMP_BY_NAME
from app.pipelines.chuyen_doi_md_sd_dat_lao_cai.process import mapper as _goc

# Nhãn NGUYÊN VĂN của option trên cổng.
_GIOI_TINH = {"Nam": "Nam", "Nữ": "Nữ"}
_NOI_CAP = {
    "bo cong an": "Bộ Công An",
    "cuc canh sat quan ly hanh chinh ve trat tu xa hoi": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
}
_CHU_HS_CA_NHAN = "Cá nhân"
_CHU_HS_DOANH_NGHIEP = "Doanh nghiệp"
_CHU_HS_TO_CHUC = "Tổ chức"
# Tên tổ chức có các cụm này → "Doanh nghiệp"; còn lại (cơ quan nhà nước, hội, đơn vị sự nghiệp…) → "Tổ chức".
_DAU_HIEU_DOANH_NGHIEP = ("cong ty", "doanh nghiep", "hop tac xa", "ngan hang", "chi nhanh", "tap doan")

_EXPECT_NGUOI_NOP = ("data[province]", "data[district]", "data[address]", "data[phoneNumber]")


def _area(value) -> dict | None:
    """_goc._area đọc khoá diaChi; LLM có thể trả chiTietDuoiXa (mô tả schema) → nhận cả hai."""
    if isinstance(value, dict) and not value.get("diaChi") and value.get("chiTietDuoiXa"):
        value = {**value, "diaChi": value.get("chiTietDuoiXa")}
    return _goc._area(value)


def _noi_cap(value) -> str | None:
    """Ô nơi cấp chỉ có 2 option — nơi cấp khác (CMND công an tỉnh…) thì không chọn được."""
    text = _goc._issuer(value)
    return _NOI_CAP.get(_goc._fold(text)) if text else None


def _gioi_tinh(person: dict | None, xung_ho=None) -> str | None:
    return _GIOI_TINH.get(_goc._gender(person, xung_ho) or "")


def _loai_to_chuc(org_name: str) -> str:
    folded = _goc._fold(org_name)
    return _CHU_HS_DOANH_NGHIEP if any(k in folded for k in _DAU_HIEU_DOANH_NGHIEP) else _CHU_HS_TO_CHUC


def _cung_nguoi(left_id, left_name, right_id, right_name) -> bool:
    left_id, right_id = _goc._digits(left_id), _goc._digits(right_id)
    if left_id and right_id:
        return left_id == right_id
    return bool(_goc._fold(left_name)) and _goc._fold(left_name) == _goc._fold(right_name)


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    return enrich_with_warnings(fields, options)[0]


def enrich_with_warnings(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _goc._by_name(fields)
    ctx = (options or {}).get("formContext") or {}
    theo_to_khai = str((options or {}).get("submitterMode") or "") == "owner_as_submitter"
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
        # Ô (*) extension chịu trách nhiệm nhưng hồ sơ không có dữ liệu → FE tô đỏ nếu ô đang trống.
        for name in names:
            if name not in seen:
                out.append({"name": name, "comp": "dom-expect", "value": ""})
                seen.add(name)

    cards = _goc._people(values, "DanhSachCccd")
    named = _goc._people(values, "NguoiTrongGiayTo")

    # ----- Chủ hồ sơ: xác định loại trước (người nộp cần biết có trùng chủ hồ sơ không). -----
    org_name = _goc._plain(values.get("ChuHoSo_TenToChuc"))
    org_tax = _goc._tax_code(values.get("ChuHoSo_MaSoThue"))
    is_org = _goc._fold(values.get("ChuHoSo_LoaiDoiTuong")) == "to chuc" and bool(org_name)

    owner_id = _goc._id_number(values.get("ChuHoSo_SoDinhDanh"))
    owner_card = None if is_org else _goc._find_person(cards, owner_id, values.get("ChuHoSo_HoTen"))
    owner_named = None if is_org else _goc._find_person(named, owner_id, values.get("ChuHoSo_HoTen"))
    person_name = _goc._plain((owner_card or {}).get("HoTen")) or _goc._plain(values.get("ChuHoSo_HoTen"))
    person_id = _goc._id_number((owner_card or {}).get("SoDinhDanh")) or owner_id
    is_person = not is_org and bool(person_name and person_id)

    # ----- Khối người nộp. -----
    applicant_id = ctx.get("applicantIdentityNumber") or ctx.get("identityNumber")
    applicant_name = ctx.get("applicantFullname")
    if theo_to_khai:
        nguoi_nop = None if is_org else _goc._merge_person(_goc._owner_person(values), cards, named)
        nop_la_chu = nguoi_nop is not None
        if nguoi_nop and (_goc._digits(applicant_id) or _goc._fold(applicant_name)) and not _cung_nguoi(
            applicant_id, applicant_name, _goc._get(nguoi_nop, "SoDinhDanh"), _goc._get(nguoi_nop, "HoTen")
        ):
            warnings.append(
                "Bật \"Lấy người nộp theo tờ khai\" nhưng tài khoản đang đăng nhập là "
                + (_goc._plain(applicant_name) or "người khác")
                + ", không phải " + (_goc._plain(_goc._get(nguoi_nop, "HoTen")) or "chủ hồ sơ")
                + ". Cổng mới KHOÁ Họ tên/Số CCCD/Ngày sinh người nộp theo tài khoản nên không sửa được — đăng "
                "nhập đúng tài khoản người đi nộp. Các ô còn lại của khối người nộp đang điền theo chủ hồ sơ."
            )
        elif not nguoi_nop:
            warnings.append(
                "Bật cài đặt \"Lấy người nộp theo tờ khai\" nhưng "
                + ("chủ hồ sơ là tổ chức (trợ lý không xác định được người đại diện/bên được uỷ quyền đi nộp)"
                   if is_org else "không đọc được họ tên/số định danh của chủ hồ sơ")
                + ", nên trợ lý để trống khối \"Thông tin người nộp hồ sơ\" — cán bộ nhập tay."
            )
    else:
        nop_la_chu = is_person and _cung_nguoi(applicant_id, applicant_name, person_id, person_name)
        if nop_la_chu:
            nguoi_nop = _goc._merge_person(_goc._owner_person(values), cards, named)
        else:
            base = _goc._find_person(cards, applicant_id, applicant_name) or _goc._match_by_id(named, applicant_id)
            nguoi_nop = _goc._merge_person(base, cards, named)

    if nguoi_nop:
        add("data[gender]", _gioi_tinh(nguoi_nop, values.get("ChuHoSo_XungHo") if nop_la_chu else None))
        add("data[identityDate]", _goc._full_date(_goc._get(nguoi_nop, "NgayCap")))
        noi_cap = _goc._get(nguoi_nop, "NoiCap")
        add("data[idIssuePlace]", _noi_cap(noi_cap))
        if noi_cap and "data[idIssuePlace]" not in seen:
            warnings.append(
                f"Nơi cấp CCCD của người nộp ghi \"{_goc._plain(noi_cap)}\" — ô \"Nơi cấp giấy tờ tùy thân\" của cổng "
                "chỉ có Bộ Công An / Cục Cảnh sát QLHC về TTXH, cán bộ kiểm tra lại."
            )
        cu_tru = _area(_goc._get(nguoi_nop, "NoiCuTru"))
        if not cu_tru and nop_la_chu:
            cu_tru = _area(values.get("ChuHoSo_DiaChiDon"))
        if cu_tru:
            # Tỉnh TRƯỚC Phường/Xã: đổi tỉnh là cổng reset Phường/Xã.
            add("data[province]", province_label(cu_tru.get("tinh")))
            add("data[district]", _goc._plain(cu_tru.get("xa")))
            add("data[address]", _goc._plain(cu_tru.get("diaChi")))
    if nop_la_chu:
        add("data[phoneNumber]", _goc._phone(values.get("Don_DienThoai")))
        add("data[email]", _goc._email(values.get("Don_Email")))
    expect(*_EXPECT_NGUOI_NOP)

    # ----- Khối chủ hồ sơ. -----
    if is_org:
        add("data[ChuHS]", _loai_to_chuc(org_name))
        add("data[ownerOrganizationFullname]", org_name.upper())
        add("data[ownerTaxCode]", org_tax)
        expect("data[ownerTaxCode]")
    elif is_person:
        add("data[ChuHS]", _CHU_HS_CA_NHAN)
        add("data[ownerFullname]", upper_person_name(person_name))
        add("data[ownerIdentityNumber]", person_id)
        add("data[ownerIdentityDate]",
            _goc._full_date((owner_card or {}).get("NgayCap"))
            or _goc._full_date(values.get("ChuHoSo_NgayCap"))
            or _goc._full_date((owner_named or {}).get("NgayCap")))
        add("data[ownerIdentityAgency22]",
            _noi_cap((owner_card or {}).get("NoiCap"))
            or _noi_cap(values.get("ChuHoSo_NoiCap"))
            or _noi_cap((owner_named or {}).get("NoiCap")))
        add("data[ownerBirthday]",
            _goc._full_date((owner_card or {}).get("NgaySinh"))
            or _goc._full_date(values.get("ChuHoSo_NgaySinh"))
            or _goc._full_date((owner_named or {}).get("NgaySinh")))
        add("data[ownerGender]",
            _gioi_tinh(owner_card) or _gioi_tinh(owner_named, values.get("ChuHoSo_XungHo")))
        expect("data[ownerGender]")
    else:
        warnings.append(
            "Không xác định được chủ hồ sơ (người sử dụng đất đứng tên Đơn) — khối \"Thông tin chủ hồ sơ\" "
            "để trống, cán bộ nhập tay."
        )

    if is_org or is_person:
        if is_org:
            residence = _area(values.get("ChuHoSo_DiaChiDkdn")) or _area(values.get("ChuHoSo_DiaChiDon"))
        else:
            residence = _area((owner_card or {}).get("NoiCuTru")) or _area(values.get("ChuHoSo_DiaChiDon"))
        residence = residence or _area(values.get("ThuaDat_DiaChi"))
        if residence:
            add("data[ownerProvince]", province_label(residence.get("tinh")))
            add("data[ownerDistrict]", _goc._plain(residence.get("xa")))
            add("data[ownerAddress]", _goc._plain(residence.get("diaChi")))
        add("data[ownerPhoneNumber]",
            _goc._phone(values.get("Don_DienThoai"))
            or (_goc._phone(values.get("Dkdn_DienThoai")) if is_org else None))
        add("data[ownerEmail]",
            _goc._email(values.get("Don_Email")) or (_goc._email(values.get("Dkdn_Email")) if is_org else None))
        expect("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", "data[ownerPhoneNumber]")

    return out, warnings
