"""Ngày trên MỌI thủ tục phải ra khỏi backend đúng một dạng dd/mm/yyyy.

Widget ngày của cổng tách sẵn ba ô day/month/year và chỉ hiểu dd/mm/yyyy. Agent thì trả đủ kiểu
tùy giấy tờ ("5/3/2024", "16-12-2024", "22.11.2024", "2024-12-16"), và phần lớn pipeline hộ tịch
KHÔNG chuẩn hóa gì trước khi trả về. Extension gặp dạng lạ là bỏ qua ô đó, mà ô ngày trượt lượt
điền đầu thì không được thử lại — ra đúng triệu chứng "lúc điền được, lúc không".
"""

import asyncio

from app.pipelines._shared.formatting import normalize_ui_date, normalize_ui_dates
from app.process.service import PreparedProcess, execute_process


def test_moi_bien_the_ngay_ve_dd_mm_yyyy():
    assert normalize_ui_date("16/12/2024") == "16/12/2024"
    assert normalize_ui_date("5/3/2024") == "05/03/2024"
    assert normalize_ui_date("16-12-2024") == "16/12/2024"
    assert normalize_ui_date("22.11.2024") == "22/11/2024"
    assert normalize_ui_date("2024-12-16") == "16/12/2024", "ISO phải đảo lại"


def test_gia_tri_khong_phai_ngay_thi_giu_nguyen():
    """Ô "Năm sinh" cha/mẹ chỉ có năm; không được cố nhét thành ngày đầy đủ."""
    assert normalize_ui_date("1968") == "1968"
    assert normalize_ui_date("") == ""
    assert normalize_ui_date(None) is None
    assert normalize_ui_date("Không rõ") == "Không rõ"


def test_chi_dung_vao_dung_o_ngay():
    fields = [
        {"name": "NgayCapDDC", "comp": "x-date", "value": "5/3/2024"},
        {"name": "NamSinhChaKS", "comp": "x-date-text", "value": "1941"},
        {"name": "SoDinhDanhC", "comp": "x-input", "value": "024068006368"},
        {"name": "ngayCapGiayTo-name-date-input", "comp": "raw", "value": "2024-12-16"},
        {"name": "nycNoiCuTru_TrongNuoc", "comp": "x-select-area",
         "value": {"quocGia": "Việt Nam", "tinh": "Bắc Ninh"}},
    ]
    result = {field["name"]: field["value"] for field in normalize_ui_dates(fields)}

    assert result["NgayCapDDC"] == "05/03/2024"
    assert result["NamSinhChaKS"] == "1941"
    assert result["SoDinhDanhC"] == "024068006368", "x-input không phải ô ngày"
    assert result["ngayCapGiayTo-name-date-input"] == "2024-12-16", "raw giữ đúng dạng cổng chờ"
    assert result["nycNoiCuTru_TrongNuoc"]["tinh"] == "Bắc Ninh"


def test_chot_chan_nam_o_cho_nghen_chung_cua_moi_thu_tuc():
    """Mỗi pipeline chuẩn hóa một kiểu (nhiều cái không làm gì) → siết một lần ở execute_process."""

    async def fake_pipeline(files_by_role, options):
        return {"fields": [
            {"name": "NgayCapDD_BenNam", "comp": "x-date", "value": "22.11.2024"},
            {"name": "NgaySinhBenNam", "comp": "x-date", "value": "1991-07-14"},
        ]}

    prepared = PreparedProcess(
        procedure="ket-hon-nuoc-ngoai",
        proc={},
        pipeline=fake_pipeline,
        files_by_role={},
        pipeline_options={},
        total_bytes=0,
        ocr_provider="test",
    )
    result = asyncio.run(execute_process(prepared))
    values = {field["name"]: field["value"] for field in result["fields"]}

    assert values["NgayCapDD_BenNam"] == "22/11/2024"
    assert values["NgaySinhBenNam"] == "14/07/1991"
