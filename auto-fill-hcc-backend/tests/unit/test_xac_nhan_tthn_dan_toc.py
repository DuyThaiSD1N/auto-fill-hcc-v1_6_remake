# req_1b8b17a7b4d9 — OCR đọc rõ "K'Ho" nhưng ô dân tộc trên cổng lại thành "Họ".
#
# Dropdown dân tộc của eForm không có option "K'Ho" (option chuẩn là "Cơ Ho"). Gửi nguyên văn thì
# extension không khớp chính xác được, quay sang khớp lỏng và dấu nháy bị coi là ranh giới từ nên
# option ngắn "Họ" lọt vào. Mapper phải chuẩn hóa TRƯỚC KHI phát ra, ở MỌI nhánh (bản thân, ủy
# quyền, fallback tờ khai) — trước đây chỉ nhánh ủy quyền gọi normalize_ethnic.
import pytest

from app.pipelines.xac_nhan_tthn.process.mapper import enrich


def _dan_toc(values: dict) -> str | None:
    fields = [{"name": k, "value": v} for k, v in values.items()]
    for field in enrich(fields):
        if field["name"] == "DanTocC1":
            return field["value"]
    return None


@pytest.mark.parametrize("raw", ["K'Ho", "K’Ho", "K Ho", "Kho", "Cơ Ho", "Ho", "Họ"])
def test_dan_toc_bien_the_ve_option_co_ho(raw):
    assert _dan_toc({
        "ToKhai_HoTen": "K'BRỄN HA TUẤN ANH",
        "ToKhai_SoDinhDanh": "068203001234",
        "ToKhai_DanToc": raw,
    }) == "Cơ Ho"


def test_dan_toc_tu_giay_khai_sinh_cung_duoc_chuan_hoa():
    # Thẻ căn cước mẫu mới không in dân tộc → nguồn duy nhất là giấy khai sinh.
    assert _dan_toc({
        "Cccd_HoTen": "K'BRỄN HA TUẤN ANH",
        "Cccd_SoDinhDanh": "068203001234",
        "Gks_HoTen": "K'BRỄN HA TUẤN ANH",
        "Gks_DanToc": "K'Ho",
    }) == "Cơ Ho"


def test_dan_toc_nhanh_uy_quyen_van_chuan_hoa():
    assert _dan_toc({
        "PoA_SubjectName": "K'BRỄN HA TUẤN ANH",
        "PoA_SubjectIdNumber": "068203001234",
        "PoA_SubjectDanToc": "K'Ho",
        "Cccd_HoTen": "NGUYỄN VĂN B",
        "Cccd_SoDinhDanh": "001203004567",
    }) == "Cơ Ho"


def test_ten_ngoai_danh_muc_giu_nguyen_van():
    # Nhóm địa phương không có trong dropdown: KHÔNG ép sang dân tộc khác, để cán bộ tự chọn.
    assert _dan_toc({
        "ToKhai_HoTen": "K'BRỄN HA TUẤN ANH",
        "ToKhai_SoDinhDanh": "068203001234",
        "ToKhai_DanToc": "Cill",
    }) == "Cill"
