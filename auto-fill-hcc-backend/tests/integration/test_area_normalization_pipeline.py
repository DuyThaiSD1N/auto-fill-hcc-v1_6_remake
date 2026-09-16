"""Khoá LỚP CHUẨN HOÁ ĐỊA CHỈ DÙNG CHUNG cho mọi thủ tục.

Bối cảnh: toàn bộ máy móc remap phường/xã nằm ở app/pipelines/_shared/area_remap.py, nhưng nó chỉ
có tác dụng khi được GỌI ở hai chốt dùng chung:

  1. compact_agent.runner.validate()  — ngay sau khi LLM trả field, TRƯỚC mọi mapper của thủ tục;
  2. process.service.execute_process() — chốt cuối trước khi trả về extension.

Gỡ một trong hai chốt đó thì không test thủ tục nào đỏ ngay (mỗi mapper tự gọi remap_area một kiểu,
47 pipeline có ô địa chỉ KHÔNG gọi lần nào), nên sai sót đi thẳng ra cổng: ô Phường/Xã nhận một tên
không còn trong danh mục, extension dò lỏng trong dropdown rồi chọn nhầm option khác mà vẫn tô xanh.
Chuyện này ĐÃ xảy ra một lần (lớp chuẩn hoá bị gỡ nguyên trong một commit "update code"), nên file
này chốt chính cái việc "hai chốt đó có được gọi không", không chỉ chốt hành vi của area_remap.
"""

import json
from pathlib import Path

import pytest

from app.pipelines._shared import area_remap
from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines._shared.compact_agent import runner as compact_runner
from app.process import service as process_service


# ---------------------------------------------------------------------------
# Chốt 1: compact_agent.runner.validate()
# ---------------------------------------------------------------------------

def _validate_area(value, ocr_text=""):
    fields = compact_runner.validate(
        {"NoiCuTru": value},
        allowed={"NoiCuTru"},
        comp_by_name={"NoiCuTru": "x-select-area"},
        ocr_text=ocr_text,
    )
    assert len(fields) == 1
    return fields[0]["value"]


def test_validate_remaps_old_ward_to_current_catalog_name():
    """Xã cũ sau sáp nhập phải ra tên MỚI ngay ở bước chung, không chờ mapper từng thủ tục."""
    out = _validate_area(
        {"quocGia": "Việt Nam", "tinh": "Bình Thuận", "xa": "Hàm Kiệm", "diaChi": "Tổ 3"},
        ocr_text="Hàm Kiệm, Bình Thuận",
    )

    assert out["tinh"] == "Lâm Đồng"
    assert out["xa"] == "Xã Hàm Kiệm"
    assert out["diaChi"] == "Tổ 3"


def test_validate_consumes_district_hint_and_never_leaks_it():
    """Gợi ý "huyen" gỡ được trùng tên phường đánh số, rồi phải BỊ BỎ khỏi giá trị field.

    Biểu mẫu không có ô cấp huyện: để khoá này lọt xuống extension là thêm một khoá lạ không ai đọc.
    """
    out = _validate_area(
        {"quocGia": "Việt Nam", "tinh": "Lâm Đồng", "xa": "Phường 1",
         "diaChi": "36/12 Nguyễn Văn Trỗi", "huyen": "Bảo Lộc"},
        ocr_text="36/12 Nguyễn Văn Trỗi, P1, Bảo Lộc, Lâm Đồng",
    )

    assert "huyen" not in out and "quanHuyen" not in out
    assert out["xa"] == "Phường 1 Bảo Lộc"


def test_validate_district_hint_is_stripped_even_without_province():
    """Luật chống bịa bắt LLM để trống "tinh" khi giấy không ghi — khoá gợi ý vẫn phải bị tiêu thụ."""
    out = _validate_area(
        {"quocGia": "Việt Nam", "tinh": "", "xa": "Phường Nghĩa Lộ", "diaChi": "Tổ 3",
         "huyen": "Nghĩa Lộ"},
        ocr_text="Tổ 3, Phường Nghĩa Lộ",
    )

    assert "huyen" not in out
    assert out["xa"] == "Phường Nghĩa Lộ"


def test_validate_drops_province_that_no_document_mentions():
    """Tỉnh LLM tự "điền nốt" (giấy không có chữ đó, lại không khớp xã) phải bị bỏ trống."""
    out = _validate_area(
        {"quocGia": "Việt Nam", "tinh": "Thành phố Hà Nội", "xa": "Phường Nghĩa Lộ",
         "diaChi": "Tổ 3"},
        ocr_text="Tổ 3, Phường Nghĩa Lộ",
    )

    assert out["tinh"] == ""


def test_validate_keeps_province_of_a_recoverable_old_address():
    """Địa chỉ CŨ HỢP LỆ không được coi là bịa chỉ vì OCR không đọc ra tên tỉnh.

    "Hàm Kiệm, Bình Thuận" remap ra "Xã Hàm Kiệm, Lâm Đồng" — xoá tỉnh ở đây là remap mất điểm tựa
    và hỏng cả một địa chỉ vốn cứu được.
    """
    out = _validate_area(
        {"quocGia": "Việt Nam", "tinh": "Bình Thuận", "xa": "Hàm Kiệm", "diaChi": "Tổ 3"},
        ocr_text="(chữ viết tay, OCR không đọc được tên tỉnh)",
    )

    assert out["tinh"] == "Lâm Đồng"
    assert out["xa"] == "Xã Hàm Kiệm"


# ---------------------------------------------------------------------------
# Chốt 2: process.service.execute_process()
# ---------------------------------------------------------------------------

def _prepared(result):
    async def pipeline(_files, _options):
        return result

    return process_service.PreparedProcess(
        procedure="bat-ky", proc={}, pipeline=pipeline, files_by_role={},
        pipeline_options={}, total_bytes=0, ocr_provider="test",
    )


async def test_execute_process_blanks_unselectable_ward_and_flags_default():
    """Tên xã không có trong danh mục phải bị xoá + đánh dấu default để extension tô viền vàng."""
    result = await process_service.execute_process(_prepared({
        "fields": [{
            "name": "NoiCuTru", "comp": "x-select-area",
            "value": {"quocGia": "Việt Nam", "tinh": "Lâm Đồng",
                      "xa": "Xã Không Có Thật", "diaChi": "Tổ 1"},
        }],
    }))

    field = result["fields"][0]
    assert field["value"]["xa"] == ""
    assert field["value"]["tinh"] == "Lâm Đồng", "tỉnh hợp lệ thì giữ, chỉ bỏ ô xã"
    assert field["default"] is True


async def test_execute_process_leaves_valid_ward_untouched():
    result = await process_service.execute_process(_prepared({
        "fields": [{
            "name": "NoiCuTru", "comp": "x-select-area",
            "value": {"quocGia": "Việt Nam", "tinh": "Lâm Đồng",
                      "xa": "Phường Xuân Hương - Đà Lạt", "diaChi": "Tổ 1"},
        }],
    }))

    field = result["fields"][0]
    assert field["value"]["xa"] == "Phường Xuân Hương - Đà Lạt"
    assert "default" not in field


# ---------------------------------------------------------------------------
# Prompt: gợi ý cấp huyện là điều kiện sống của bảng tra 3 khoá
# ---------------------------------------------------------------------------

def test_compact_prompt_still_asks_for_district_hint():
    """Bỏ khoá "huyen" khỏi prompt là bảng _REMAP_BY_DISTRICT thành code chết.

    Đó là đường DUY NHẤT chọn đúng một tên phường trùng ở nhiều huyện của cùng một tỉnh cũ
    ("Phường 1" có ở cả Đà Lạt lẫn Bảo Lộc), nên phải chốt lại ở đây.
    """
    system_prompt = compact_prompt.build_system_prompt(
        [{"name": "NoiCuTru", "desc": "nơi cư trú"}]
    )

    assert '"huyen"' in system_prompt
    assert "KHÔNG BỊA" in system_prompt
    assert area_remap._REMAP_BY_DISTRICT, "bảng 3 khoá rỗng thì gợi ý huyện cũng vô nghĩa"


# ---------------------------------------------------------------------------
# Dữ liệu remap: đích đến phải CÓ THẬT trong danh mục hành chính hiện hành
# ---------------------------------------------------------------------------

def _remap_entries():
    data_dir = Path(area_remap.__file__).parent / "data"
    for path in sorted(data_dir.glob("remap_*.json")):
        with open(path, encoding="utf-8-sig") as f:
            for entry in json.load(f):
                yield path.name, entry


def test_every_remap_destination_exists_in_current_catalog():
    """Đích đến của mọi dòng remap phải chọn được trên cổng.

    Bảng remap là hơn 10.000 dòng gõ tay: đích lệch danh mục một chút (sai dấu "Sì Lờ"/"Sì Lở",
    dấu nháy ’ thay vì ', còn sót ghi chú "(huyện X)", thiếu tiền tố "Đặc khu") thì KHÔNG có gì
    báo lỗi — backend trả về một tên trông như thật và ô Phường/Xã trên cổng im lặng chọn sai.
    Đợt quét đầu tiên bắt được 60 dòng như vậy ở 7 tỉnh.
    """
    if not area_remap._CURRENT_PROVINCES:
        pytest.skip("chưa nạp được danh mục hành chính hiện hành")

    dead = []
    for file_name, entry in _remap_entries():
        tinh_moi = entry.get("tinh_moi") or entry.get("tinh_cu") or ""
        xa_moi = entry.get("xa_moi") or ""
        if not tinh_moi or not xa_moi:
            continue
        if not area_remap.is_current_area(tinh_moi, xa_moi):
            dead.append(f"{file_name}: {entry.get('tinh_cu')}/{entry.get('xa_cu')}"
                        f" -> {tinh_moi}/{xa_moi}")

    assert not dead, "đích remap không có trong danh mục hiện hành:\n" + "\n".join(dead[:40])


def test_apostrophe_variants_match_the_same_ward():
    """Tên Tây Nguyên gõ bằng ’ (U+2019) hay ' (ASCII) phải ra CÙNG một xã trong danh mục."""
    assert area_remap.is_current_area("Đắk Lắk", "Xã Ea M’Droh")
    assert area_remap.is_current_area("Đắk Lắk", "Xã Ea M'Droh")

    out = area_remap.remap_area(
        {"quocGia": "Việt Nam", "tinh": "Đắk Lắk", "xa": "Quảng Hiệp", "diaChi": "Thôn 1"}
    )
    # Giá trị trả về lấy ĐÚNG chính tả của danh mục (dấu nháy ASCII), không phải chính tả trong
    # file remap — cổng khớp option theo đúng chuỗi nhãn.
    assert out["xa"] == "Xã Ea M'Droh"
