"""Khai tử: số/ngày cấp/nơi cấp của người yêu cầu ưu tiên lấy từ ẢNH THẺ CCCD.

Ba ô này in sẵn trên thẻ nên đáng tin hơn chữ viết tay trên tờ khai. Mỏ neo phân vai lại
đọc từ tờ khai, nên lệch vài chữ số là chuyện thường và KHÔNG được vì thế mà xóa cả cụm
thẻ — xóa thì mapper rơi ngược về số sai của tờ khai.
"""

from app.pipelines.khai_tu.process import mapper, reason
from app.pipelines.khai_tu.process.schema import COMPACT_COMP_BY_NAME


def _context(requester_name: str, requester_id: str, rejected: str = "Không có") -> str:
    return (
        "<phan_vai_da_xac_dinh>\n"
        "<nguoi_yeu_cau>\n"
        f"Họ tên: {requester_name}\n"
        f"Số CCCD/CMND: {requester_id}\n"
        "</nguoi_yeu_cau>\n"
        "<nguoi_mat>\n"
        "Họ tên: Nguyễn Thị Học\n"
        "Số CCCD/CMND: Không xác định\n"
        "</nguoi_mat>\n"
        "<giay_to_khong_thuoc_hai_vai>\n"
        f"{rejected}\n"
        "</giay_to_khong_thuoc_hai_vai>\n"
        "</phan_vai_da_xac_dinh>"
    )


def _fields(values: dict) -> list[dict]:
    return [
        {"name": name, "comp": COMPACT_COMP_BY_NAME.get(name, "input"), "value": value}
        for name, value in values.items()
    ]


def _ui(values: dict, context: str) -> dict:
    kept = reason.sanitize_identity_fields(_fields(values), context)
    return {field["name"]: field["value"] for field in mapper.enrich(kept, {}, reasoning_context=context)}


def _cccd_names(values: dict, context: str) -> list[str]:
    kept = reason.sanitize_identity_fields(_fields(values), context)
    return [field["name"] for field in kept if field["name"].startswith("Cccd_")]


_DECLARATION = {
    "NguoiYeuCau_HoTen": "Đặng Tấn",
    # Tờ khai viết tay bị OCR thừa một chữ số so với thẻ.
    "NguoiYeuCau_SoDinhDanh": "051803700308",
    "NguoiYeuCau_NgayCap": "12/12/2020",
    "NguoiYeuCau_NoiCap": "Quan Trưởng CCSQLHC về Trật Tự Xã Hội",
}
_CARD = {
    "Cccd_HoTen": "ĐẶNG TẦN",
    "Cccd_SoDinhDanh": "051037003080",
    "Cccd_NgaySinh": "11/02/1937",
    "Cccd_NgayCap": "10/05/2021",
    "Cccd_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
}
_DECEASED = {"NguoiMat_HoTen": "Nguyễn Thị Học", "NguoiMat_NgaySinh": "1890"}


def test_nhan_than_nguoi_yeu_cau_lay_tu_the_khi_to_khai_lech_so():
    context = _context("Đặng Tấn", "051803700308")
    ui = _ui({**_DECLARATION, **_CARD, **_DECEASED}, context)
    # Họ tên cũng theo thẻ, giữ nguyên văn cách viết in trên thẻ.
    assert ui["HoVaTenC"] == "ĐẶNG TẦN"
    assert ui["SoDinhDanhC"] == "051037003080"
    assert ui["SoGiayToDinhDanhC"] == "051037003080"
    assert ui["NgayCapDDC"] == "10/05/2021"
    assert ui["NoiCapDDC"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    # Thẻ chỉ chi phối cụm giấy tờ tùy thân, không kéo theo vai người mất.
    assert ui["HoTen"] == "Nguyễn Thị Học"


def test_the_van_duoc_giu_khi_to_khai_roi_chu_dem():
    context = _context("Đặng Văn Tấn", "051803700308")
    values = {**_DECLARATION, **_CARD, **_DECEASED}
    assert "Cccd_SoDinhDanh" in _cccd_names(values, context)


def test_the_cua_nguoi_khac_van_bi_loai():
    """Thẻ của người thứ ba: cả HỌ TÊN lẫn số đều khác người yêu cầu → vẫn loại."""
    context = _context("Đặng Tấn", "051803700308", rejected="- Phạm Văn C — 044444444444 — không liên quan")
    values = {
        **_DECLARATION,
        **_DECEASED,
        "Cccd_HoTen": "PHẠM VĂN C",
        "Cccd_SoDinhDanh": "044444444444",
        "Cccd_NgayCap": "10/05/2021",
    }
    assert _cccd_names(values, context) == []
    # Không còn thẻ khớp thì cụm giấy tờ quay về số đọc từ tờ khai.
    assert _ui(values, context)["SoDinhDanhC"] == "051803700308"


def test_the_lech_ca_so_lan_ten_van_bi_loai():
    context = _context("Đặng Tấn", "051803700308")
    values = {**_DECLARATION, **_DECEASED, "Cccd_HoTen": "NGUYỄN VĂN D", "Cccd_SoDinhDanh": "044444444444"}
    assert _cccd_names(values, context) == []


def test_noi_cu_tru_van_uu_tien_to_khai():
    """Địa chỉ in trên thẻ là nơi thường trú lúc cấp, hay lạc hậu sau sáp nhập đơn vị hành chính."""
    context = _context("Đặng Tấn", "051803700308")
    values = {
        **_DECLARATION,
        **_CARD,
        **_DECEASED,
        "NguoiYeuCau_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Quảng Ngãi", "xa": "Nghĩa Lộ", "diaChi": "Tổ 10"},
        "Cccd_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Quảng Ngãi", "xa": "Quảng Phú", "diaChi": ""},
    }
    assert _ui(values, context)["nycNoiCuTru_TrongNuoc"]["diaChi"] == "Tổ 10"


def test_ho_ten_quay_ve_to_khai_khi_khong_co_the():
    context = _context("Đặng Tấn", "051803700308")
    ui = _ui({**_DECLARATION, **_DECEASED}, context)
    assert ui["HoVaTenC"] == "Đặng Tấn"
    assert ui["SoDinhDanhC"] == "051803700308"


def test_the_bi_agent_loai_nham_vi_lech_dau_ten_van_duoc_giu():
    """Ca thật hồ sơ Đặng Tấn: agent phân vai loại thẻ vì "Đặng Tần" != "Đặng Tấn" (lệch dấu).

    Lệch dấu tên + lệch chữ số là lỗi OCR tờ khai viết tay, không phải bằng chứng đổi người;
    xoá cả cụm thẻ sẽ đẩy biểu mẫu về đúng con số sai của tờ khai.
    """
    context = _context(
        "Đặng Tấn",
        "051803700308",
        rejected="- Đặng Tần — Số CCCD/CMND: 051037003080 — Lý do loại: không khớp người yêu cầu",
    )
    values = {**_DECLARATION, **_CARD, **_DECEASED}
    assert "Cccd_SoDinhDanh" in _cccd_names(values, context)
    ui = _ui(values, context)
    assert ui["SoDinhDanhC"] == "051037003080"
    assert ui["HoVaTenC"] == "ĐẶNG TẦN"


def test_the_trung_so_nguoi_chet_van_bi_loai_du_trung_ten():
    """Trùng số đã chốt của người chết là xung đột vai thật, không phải lỗi OCR."""
    context = _context("Đặng Tấn", "051803700308").replace(
        "Họ tên: Nguyễn Thị Học\nSố CCCD/CMND: Không xác định",
        "Họ tên: Đặng Tấn\nSố CCCD/CMND: 051037003080",
    )
    values = {**_DECLARATION, **_CARD, **_DECEASED}
    assert _cccd_names(values, context) == []
