"""Biểu mẫu trích lục hiện hành trên Cổng DVC quốc gia mới: cổng gỡ Giới tính / Dân tộc / khối nơi cư trú của người
được cấp, thêm "Họ, tên Cha" / "Họ, tên Mẹ" ở phần giấy tờ hộ tịch."""

import pytest

from app.pipelines.trich_luc_dvc_moi.handfree import field_review
from app.pipelines.trich_luc_dvc_moi.process import mapper, schema
from app.traces.key_fields import KEY_FIELDS_BY_PROCEDURE

ACCOUNT = {"applicantFullname": "NGUYEN VAN A", "applicantIdentityNumber": "001090000001"}
CONTEXT = (
    "<phan_vai_da_xac_dinh>\n"
    "<nguoi_duoc_cap>\nHọ tên: TRAN THI B\nSố định danh: 001190000002\nTrạng thái: còn sống\n</nguoi_duoc_cap>\n"
    "<giay_to_ho_tich>\nLoại ghi trên tờ khai: không có\nLoại trích lục cần cấp: khai sinh\n</giay_to_ho_tich>\n"
    "<quan_he>\nQuan hệ ghi trên tờ khai: không có\nĐối chiếu với người nộp: không xác định\n"
    "Kết luận: Mẹ đẻ\nQuan hệ khác: \nCăn cứ: x\n</quan_he>\n"
    "</phan_vai_da_xac_dinh>"
)
VALUES = {
    "NguoiDuocCap_HoTen": "Tran Thi B", "NguoiDuocCap_SoDinhDanh": "001190000002",
    "NguoiDuocCap_NgaySinh": "01/02/1990", "NguoiDuocCap_GioiTinh": "Nữ", "NguoiDuocCap_DanToc": "Kinh",
    "NguoiDuocCap_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Lâm Đồng", "xa": "Phường Xuân Hương", "diaChi": "Số 1"},
    "GiayTo_LoaiSuKien": "birth", "GiayTo_CoQuanDangKy": "Ủy ban nhân dân phường X",
    "GiayTo_HoTenCha": "Tran Van C", "GiayTo_HoTenMe": "Le Thi D",
    "GiayTo_So": "12/1990", "GiayTo_NgayDangKy": "05/02/1990",
}


@pytest.fixture(autouse=True)
def _che_do_thuong(monkeypatch):
    from app.pipelines.trich_luc_dvc_moi import che_do_demo
    monkeypatch.setattr(che_do_demo, "BAT", False)


def _enrich(values: dict, ocr_text: str = ""):
    fields = [{"name": k, "value": v} for k, v in values.items()]
    return mapper.enrich(fields, {"_reasoning_context": CONTEXT, "_ocr_text": ocr_text, "formContext": ACCOUNT})


def test_o_cong_da_go_khong_tra_ve_nhung_van_giu_loai_cu_tru():
    out, warnings = _enrich(VALUES)
    names = [f["name"] for f in out]
    assert not set(names) & schema.UI_REMOVED_BY_PORTAL
    assert {f["name"]: f for f in out}["citizenNDK_LoaiCuTru"]["value"] == "Thường trú"
    assert not warnings


def test_dia_chi_khong_chon_duoc_xa_khong_bao_cho_can_bo_o_khong_con_tren_form():
    values = {**VALUES, "NguoiDuocCap_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Lâm Đồng", "xa": "Bản Không Có"}}
    _, warnings = _enrich(values)
    assert not any("nơi cư trú" in w or "Tỉnh/Thành phố" in w for w in warnings)


def test_ho_ten_cha_me_dien_in_hoa_sau_co_quan_dang_ky():
    out, _ = _enrich(VALUES)
    names = [f["name"] for f in out]
    by = {f["name"]: f for f in out}
    assert by["citizenHotenCha"]["value"] == "TRAN VAN C" and by["citizenHotenMe"]["value"] == "LE THI D"
    assert names.index("citizenHoSo_CoQuanDangKy") < names.index("citizenHotenCha") < names.index("citizenHotenMe")
    assert not by["citizenHotenCha"].get("default") and not by["citizenHotenCha"].get("onlyIfEmpty")


def test_giay_khong_ghi_cha_me_thi_khong_tra_o():
    values = {k: v for k, v in VALUES.items() if k not in ("GiayTo_HoTenCha", "GiayTo_HoTenMe")}
    names = [f["name"] for f in _enrich(values)[0]]
    assert "citizenHotenCha" not in names and "citizenHotenMe" not in names


def test_truong_cha_me_co_trong_schema_va_nhan_mong():
    assert {"GiayTo_HoTenCha", "GiayTo_HoTenMe"} <= schema.ALLOWED
    assert schema.UI_COMP_BY_NAME["citizenHotenCha"] == schema.UI_COMP_BY_NAME["citizenHotenMe"] == "sjs-text"
    assert field_review.HMONG_LABELS["citizenHotenCha"][0] == "npe txiv"
    assert field_review.HMONG_LABELS["citizenHotenMe"][0] == "npe niam"


def test_truong_chinh_cua_trace_khong_tinh_o_cong_da_go():
    assert not set(KEY_FIELDS_BY_PROCEDURE["trich-luc-ks"]) & schema.UI_REMOVED_BY_PORTAL
