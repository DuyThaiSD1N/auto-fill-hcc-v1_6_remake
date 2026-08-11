"""Người yêu cầu khai tử phải GHI ĐÈ dữ liệu VNeID điền sẵn trên form.

Ca hồi quy chính: hồ sơ chỉ có 2 CCCD (người trẻ = người yêu cầu, người già = người chết),
KHÔNG có tờ khai, và tài khoản đăng nhập cổng là người thứ ba (nộp thay). Trước đây tài khoản
cổng là mỏ neo duy nhất nên thẻ người yêu cầu bị coi là "không đáng tin" → mapper rơi về chính
dữ liệu VNeID → extension điền lại đúng thứ đang có sẵn, nhìn như không điền gì.
"""

from app.pipelines.khai_tu.process import mapper, reason

_YOUNG_ID = "079199001111"
_OLD_ID = "079045002222"
_ACCOUNT_ID = "079188003333"

_ACCOUNT_CTX = {
    "formContext": {
        "applicantFullname": "Người Nộp Thay",
        "applicantIdentityNumber": _ACCOUNT_ID,
    }
}


def _two_card_fields() -> list[dict]:
    return [
        # Thẻ người yêu cầu (người trẻ) — agent trích xuất định tuyến vào Cccd_*.
        {"name": "Cccd_HoTen", "value": "Nguyễn Văn Trẻ"},
        {"name": "Cccd_SoDinhDanh", "value": _YOUNG_ID},
        {"name": "Cccd_NgayCap", "value": "10/05/2021"},
        {"name": "Cccd_NoiCap", "value": "Cục Cảnh sát QLHC về TTXH"},
        {"name": "Cccd_NoiCuTru", "value": {"tinh": "Lâm Đồng", "xa": "Xã Đoàn Kết", "diaChi": "SN 12"}},
        # Thẻ người chết (người già).
        {"name": "NguoiMat_HoTen", "value": "Nguyễn Văn Già"},
        {"name": "NguoiMat_SoDinhDanh", "value": _OLD_ID},
        {"name": "NguoiMat_NgayMat", "value": "01/08/2026"},
    ]


def _by_name(fields: list[dict]) -> dict[str, dict]:
    return {f["name"]: f for f in fields}


def test_two_identity_cards_override_vneid_account():
    out = _by_name(mapper.enrich(_two_card_fields(), _ACCOUNT_CTX))

    # Khối người yêu cầu lấy theo THẺ trong hồ sơ, không phải tài khoản đăng nhập.
    assert out["HoVaTenC"]["value"] == "Nguyễn Văn Trẻ"
    assert out["SoDinhDanhC"]["value"] == _YOUNG_ID
    assert out["SoGiayToDinhDanhC"]["value"] == _YOUNG_ID
    assert out["NoiCapDDC"]["value"] == "Cục Cảnh sát QLHC về TTXH"
    assert out["nycNoiCuTru_TrongNuoc"]["value"]["diaChi"] == "SN 12"
    # Dữ liệu thật từ giấy tờ → KHÔNG gắn cờ default (extension chỉ tô vàng ô mặc định).
    assert not any(out[name].get("default") for name in ("HoVaTenC", "SoDinhDanhC", "nycNoiCuTru_TrongNuoc"))
    # Thẻ người yêu cầu không được coi nhầm là thẻ người chết.
    assert out["HoTen"]["value"] == "Nguyễn Văn Già"
    assert out["SoDinhDanh"]["value"] == _OLD_ID


def test_declaration_still_outranks_identity_cards():
    # Có tờ khai ghi người yêu cầu KHÁC thẻ Cccd_* → thẻ không được dùng cho người yêu cầu.
    fields = _two_card_fields() + [
        {"name": "NguoiYeuCau_HoTen", "value": "Trần Thị Đứng Đơn"},
        {"name": "NguoiYeuCau_SoDinhDanh", "value": "079200004444"},
    ]
    out = _by_name(mapper.enrich(fields, _ACCOUNT_CTX))

    assert out["HoVaTenC"]["value"] == "Trần Thị Đứng Đơn"
    assert out["SoDinhDanhC"]["value"] == "079200004444"
    # Dữ kiện của thẻ người khác KHÔNG được ghép vào người yêu cầu của tờ khai.
    assert "NgayCapDDC" not in out
    assert "nycNoiCuTru_TrongNuoc" not in out


def test_single_untrusted_card_still_falls_back_to_account():
    # Chỉ 1 thẻ, không phân được vai từ hồ sơ → tài khoản cổng vẫn là mỏ neo, thẻ lệch thì bỏ.
    fields = [
        {"name": "Cccd_HoTen", "value": "Nguyễn Văn Già"},
        {"name": "Cccd_SoDinhDanh", "value": _OLD_ID},
    ]
    out = _by_name(mapper.enrich(fields, _ACCOUNT_CTX))

    assert out["HoVaTenC"]["value"] == "Người Nộp Thay"
    assert out["HoVaTenC"].get("default") is True


_ROLE_OUTPUT = f"""
<nguoi_yeu_cau>
Họ tên: Nguyễn Văn Trẻ
Số CCCD/CMND: {_YOUNG_ID}
Căn cứ phân vai: hai thẻ trong hồ sơ, suy đoán theo tuổi
</nguoi_yeu_cau>
<nguoi_mat>
Họ tên: Nguyễn Văn Già
Số CCCD/CMND: {_OLD_ID}
</nguoi_mat>
<giay_to_khong_thuoc_hai_vai>
Không có
</giay_to_khong_thuoc_hai_vai>
"""


def test_role_context_survives_when_two_cards_anchor_each_other():
    # Không tờ khai + tài khoản cổng là người thứ ba, nhưng hai vai có hai số định danh riêng
    # → kết quả phân vai tự đứng vững, không được vứt.
    context = reason._render_context(_ROLE_OUTPUT, _ACCOUNT_CTX, has_declaration=False)

    assert context
    assert reason.role_identity(context) == (_YOUNG_ID, "Nguyễn Văn Trẻ")
    assert "KHÁC người yêu cầu đã phân vai" in context


def test_role_context_dropped_when_it_has_no_anchor_of_its_own():
    raw = """
<nguoi_yeu_cau>
Họ tên: Nguyễn Văn Trẻ
Số CCCD/CMND: Không xác định
</nguoi_yeu_cau>
<nguoi_mat>
Họ tên: Nguyễn Văn Già
Số CCCD/CMND: Không xác định
</nguoi_mat>
<giay_to_khong_thuoc_hai_vai>
Không có
</giay_to_khong_thuoc_hai_vai>
"""
    assert reason._render_context(raw, _ACCOUNT_CTX, has_declaration=False) == ""


def test_requester_card_anchored_by_role_context_even_without_deceased_card():
    # Chỉ có thẻ người yêu cầu (thẻ người chết không đọc được số) nhưng tầng phân vai đã chốt
    # → vẫn tin thẻ đó, không rơi về tài khoản cổng.
    context = reason._render_context(_ROLE_OUTPUT, _ACCOUNT_CTX, has_declaration=False)
    fields = [
        {"name": "Cccd_HoTen", "value": "Nguyễn Văn Trẻ"},
        {"name": "Cccd_SoDinhDanh", "value": _YOUNG_ID},
        {"name": "NguoiMat_HoTen", "value": "Nguyễn Văn Già"},
    ]
    out = _by_name(mapper.enrich(fields, _ACCOUNT_CTX, reasoning_context=context))

    assert out["HoVaTenC"]["value"] == "Nguyễn Văn Trẻ"
    assert out["SoDinhDanhC"]["value"] == _YOUNG_ID
