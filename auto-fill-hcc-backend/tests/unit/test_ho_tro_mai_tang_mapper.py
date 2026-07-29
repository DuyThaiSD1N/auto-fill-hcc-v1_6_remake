"""Unit test mapper hỗ trợ mai táng (gọi thẳng enrich, không qua OCR/LLM).

Tách khỏi test integration để không dính config drift của respx/settings.
"""

from app.pipelines.ho_tro_mai_tang.process import mapper


def _flds(d: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in d.items()]


def _run(vals: dict, ctx: dict | None = None):
    fields, warnings = mapper.enrich(_flds(vals), ctx or {})
    return {f["name"]: f["value"] for f in fields}, warnings


_UI_MAI = {"formContext": {"applicantFullname": "Bùi Thị Thanh Mai",
                           "applicantIdentityNumber": "025199000635"}}


def test_tokhai_same_person_survives_wrong_handwritten_number():
    """Số CMND trên tờ khai viết tay bị OCR sai vẫn phải nhận ra TRÙNG người nộp (khớp tên)
    → tích 'người nộp là chủ hồ sơ', không điền owner trùng, số/ngày lấy từ CCCD."""
    d, w = _run({
        "Person1_HoTen": "BÙI THỊ THANH MAI",
        "Person1_SoDinhDanh": "025199000635",
        "Person1_NgayCap": "20/09/2024",
        "Person1_NoiCap": "Bộ Công an",
        "Person1_NoiCuTru": {"tinh": "Phú Thọ", "xa": "Lâm Thao", "diaChi": "Khu Phương Lai"},
        # Tờ khai viết tay: số thừa space + sai chữ số, năm cấp sai (1924)
        "ToKhai_ChuHoTen": "Bùi Thị Thanh Mai",
        "ToKhai_ChuHoSoGiayTo": "025 199900635",
        "ToKhai_ChuHoNgayCap": "20/09/1924",
        "ToKhai_ChuHoNoiCuTru": {"tinh": "Phú Thọ", "xa": "Lâm Thao", "diaChi": "khu phương lại"},
    }, _UI_MAI)

    assert d["data[isOwnerDossierCheck]"] is True
    assert d["data[fullname]"] == "BÙI THỊ THANH MAI"
    assert d["data[identityNumber]"] == "025199000635"     # số đúng từ CCCD
    assert d["data[identityDate]"] == "20/09/2024"          # ngày cấp đúng từ CCCD
    assert "data[ownerFullname]" not in d                    # không điền owner trùng
    assert not w


def test_tokhai_owner_from_form_when_no_cccd():
    """Chủ hồ sơ khác người nộp và không có CCCD → owner lấy từ tờ khai, gender để trống."""
    d, w = _run({
        "Person1_HoTen": "TRẦN THỊ THANH THẢO",
        "Person1_SoDinhDanh": "036192014693",
        "Person1_NoiCuTru": {"tinh": "Ninh Bình", "xa": "Gia Thắng", "diaChi": "Xóm 2"},
        "ToKhai_ChuHoTen": "Bùi Mạnh Cường",
        "ToKhai_ChuHoNamSinh": "20/08/1990",
        "ToKhai_ChuHoSoGiayTo": "001906118210",
        "ToKhai_ChuHoNgayCap": "01/10/2025",
        "ToKhai_ChuHoNoiCap": "Bộ Công an",
        "ToKhai_ChuHoNoiCuTru": {"tinh": "Lai Châu", "xa": "Tân Phong", "diaChi": "Tổ 9"},
    }, {"formContext": {"applicantFullname": "TRẦN THỊ THANH THẢO",
                        "applicantIdentityNumber": "036192014693"}})

    assert d["data[isOwnerDossierCheck]"] is False
    assert d["data[fullname]"] == "TRẦN THỊ THANH THẢO"
    assert d["data[province]"] == "Ninh Bình"               # requester giữ địa chỉ CCCD
    assert d["data[ownerFullname]"] == "Bùi Mạnh Cường"
    assert d["data[ownerIdentityNumber]"] == "001906118210"
    assert d["data[ownerBirthday]"] == "20/08/1990"
    assert d["data[ownerProvince]"] == "Lai Châu"           # owner địa chỉ từ tờ khai
    assert d["data[ownerDistrict]"] == "Tân Phong"
    assert d["data[ownerAddress]"] == "Tổ 9"
    assert "data[ownerGender]" not in d                      # tờ khai không ghi giới tính
    assert not w


def test_tokhai_owner_prefers_cccd_identity_but_tokhai_address():
    """Có CCCD chủ hồ sơ: định danh ưu tiên CCCD, địa chỉ ưu tiên tờ khai (2 cấp)."""
    d, w = _run({
        "Person1_HoTen": "TRẦN THỊ THANH THẢO",
        "Person1_SoDinhDanh": "036192014693",
        "Person2_HoTen": "BÙI MẠNH CƯỜNG",
        "Person2_SoDinhDanh": "001906118210",
        "Person2_GioiTinh": "Nam",
        "Person2_NgayCap": "01/10/2025",
        "Person2_NoiCap": "Bộ Công an",
        "Person2_NoiCuTru": {"tinh": "Điện Biên", "xa": "Mường Lay", "diaChi": "Bản 1"},
        "ToKhai_ChuHoTen": "Bùi Mạnh Cường",
        "ToKhai_ChuHoSoGiayTo": "001906118210",
        "ToKhai_ChuHoNoiCuTru": {"tinh": "Lai Châu", "xa": "Tân Phong", "diaChi": "Tổ 9"},
    }, {"formContext": {"applicantFullname": "TRẦN THỊ THANH THẢO",
                        "applicantIdentityNumber": "036192014693"}})

    assert d["data[isOwnerDossierCheck]"] is False
    assert d["data[ownerGender]"] == "Nam"                  # định danh từ CCCD
    assert d["data[ownerIdentityDate]"] == "01/10/2025"
    assert d["data[ownerProvince]"] == "Lai Châu"           # địa chỉ từ tờ khai, KHÔNG lấy Điện Biên
    assert d["data[ownerAddress]"] == "Tổ 9"
    assert not w


def test_no_tokhai_falls_back_to_cccd_only_logic():
    """Không có tờ khai → giữ logic cũ (1 CCCD = người nộp kiêm chủ hồ sơ)."""
    d, w = _run({
        "Person1_HoTen": "NGUYỄN VĂN A",
        "Person1_SoDinhDanh": "111111111111",
        "Person1_NoiCuTru": {"tinh": "Hà Nội", "xa": "Cầu Giấy", "diaChi": "Số 1"},
    }, {})

    assert d["data[isOwnerDossierCheck]"] is True
    assert d["data[fullname]"] == "NGUYỄN VĂN A"
    assert "data[ownerFullname]" not in d
    assert not w
