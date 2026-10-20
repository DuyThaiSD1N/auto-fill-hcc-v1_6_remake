"""Đăng ký lại khai tử: dòng CCCD đặt tên theo người ("CCCD <Họ tên>"), không đánh số 2, 3…"""
from app.pipelines.khai_tu_dang_ky_lai.attach.planner import build_plan_items

_TRUOC_A = "CĂN CƯỚC CÔNG DÂN\nSố / No.: 001095000123\nHọ và tên / Full name:\nNGUYỄN VĂN AN\nGiới tính: Nam"
_SAU_A = "Đặc điểm nhận dạng\nCỤC TRƯỞNG CỤC CẢNH SÁT\nIDVNM0950001230001095000123<<1"
_TRUOC_B = "CĂN CƯỚC CÔNG DÂN\nSố / No.: 001197000456\nHọ và tên / Full name:\nTRẦN THỊ BÌNH\nGiới tính: Nữ"


def _files(n):
    return [{"name": f"f{i}.jpg", "type": "image/jpeg"} for i in range(n)]


def _ocr(*texts):
    return [{"name": f"f{i}.jpg", "text": t} for i, t in enumerate(texts)]


def _names(attachments):
    return [a["documentName"] for a in attachments]


def test_hai_nguoi_dat_ten_theo_ho_ten_llm():
    llm = {0: {"type": "identity", "subjectName": "Nguyễn Văn An"},
           1: {"type": "identity", "subjectName": "Trần Thị Bình"}}
    att, _ = build_plan_items(_files(2), _ocr(_TRUOC_A, _TRUOC_B), llm)
    assert _names(att) == ["CCCD Nguyễn Văn An", "CCCD Trần Thị Bình"]
    assert all(a["componentName"] == a["documentName"] and a["target"] == "new" for a in att)


def test_gop_hai_mat_mat_sau_tai_truoc_van_lay_ten_mat_truoc():
    llm = {0: {"type": "identity", "subjectName": ""}, 1: {"type": "identity", "subjectName": "Nguyễn Văn An"}}
    att, classified = build_plan_items(_files(2), _ocr(_SAU_A, _TRUOC_A), llm)
    assert len(att) == 1 and sorted(att[0]["sourceFileIndexes"]) == [0, 1]
    assert att[0]["documentName"] == "CCCD Nguyễn Văn An"
    assert {c["documentName"] for c in classified} == {"CCCD Nguyễn Văn An"}


def test_llm_khong_tra_ten_thi_doc_dong_ho_ten_trong_ocr():
    att, _ = build_plan_items(_files(1), _ocr(_TRUOC_B), {0: {"type": "identity"}})
    assert _names(att) == ["CCCD TRẦN THỊ BÌNH"]


def test_khong_doc_duoc_ten_giu_nhan_chung():
    att, _ = build_plan_items(_files(1), _ocr("Đặc điểm nhận dạng\nCỤC TRƯỞNG CỤC CẢNH SÁT"),
                              {0: {"type": "identity", "subjectName": ""}})
    assert _names(att) == ["Căn cước công dân"]


def test_giay_khac_khong_doi_ten():
    llm = {0: {"type": "death_proof", "documentName": "Trích lục khai tử", "subjectName": "Nguyễn Văn An"},
           1: {"type": "identity", "subjectName": "Nguyễn Văn An"}}
    att, _ = build_plan_items(_files(2), _ocr("TRÍCH LỤC KHAI TỬ", _TRUOC_A), llm)
    assert _names(att) == ["Giấy tờ chứng minh sự kiện chết", "CCCD Nguyễn Văn An"]
