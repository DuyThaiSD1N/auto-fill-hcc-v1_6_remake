"""Tên chủ thể trong documentName (= tên tệp trên cổng) phải đúng chữ in trên giấy: LLM hay đổi dấu tên cho quen
mắt (thẻ in "HUẾ" → "Huệ")."""

from app.pipelines.chung_thuc_ban_sao.attach.planner import _ocr_spelled_subject
from app.pipelines.chung_thuc_ban_sao.attach.prompt import SYSTEM_PROMPT

OCR = "Họ, chữ đệm và tên khai sinh / Full name:\nLÊ THỊ HUẾ\nNgày sinh / Date of birth: 01/01/2000"


def test_ho_ten_sai_dau_chep_lai_dung_dau_ocr():
    assert _ocr_spelled_subject("Lê Thị Huệ", "CCCD Lê Thị Huệ", OCR) == ("Lê Thị Huế", "CCCD Lê Thị Huế")


def test_ten_goi_rut_gon_trong_document_name_cung_duoc_sua():
    assert _ocr_spelled_subject("Lê Thị Huệ", "Bằng tốt nghiệp THPT Huệ", OCR)[1] == "Bằng tốt nghiệp THPT Huế"


def test_ten_dung_hoac_khong_co_dong_trung_thi_giu_nguyen():
    assert _ocr_spelled_subject("Lê Thị Huế", "CCCD Lê Thị Huế", OCR) == ("Lê Thị Huế", "CCCD Lê Thị Huế")
    assert _ocr_spelled_subject("Trần Văn Nam", "CCCD Trần Văn Nam", OCR) == ("Trần Văn Nam", "CCCD Trần Văn Nam")
    assert _ocr_spelled_subject("", "Giấy khai sinh", OCR) == ("", "Giấy khai sinh")


def test_dong_ho_ten_sau_dau_hai_cham():
    text = "Họ và tên: NGUYỄN VĂN TUẾ"
    assert _ocr_spelled_subject("Nguyễn Văn Tuệ", "CCCD Nguyễn Văn Tuệ", text)[1] == "CCCD Nguyễn Văn Tuế"


def test_prompt_dan_chep_nguyen_van_dau_ho_ten():
    assert "chép NGUYÊN VĂN từng chữ và dấu như OCR_TEXT" in SYSTEM_PROMPT


def test_chu_ocr_gop_mot_dong_moi_trang():
    text = "CĂN CƯỚC Họ, chữ đệm và tên khai sinh / Full name: LÊ THỊ HUẾ Ngày, tháng, năm sinh / Date of birth"
    assert _ocr_spelled_subject("Lê Thị Huệ", "CCCD Lê Thị Huệ", text) == ("Lê Thị Huế", "CCCD Lê Thị Huế")
