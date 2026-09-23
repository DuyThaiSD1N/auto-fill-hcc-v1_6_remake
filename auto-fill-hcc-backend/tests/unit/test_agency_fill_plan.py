"""Kế hoạch điền hộ khối "Chọn cơ quan thực hiện" — dùng CHUNG hai kênh.

Handfree phát qua action fill_agency_plan; Auto Fill (no handfree) nạp qua /api/v1/procedures
rồi hiện nút "Chọn cơ quan thực hiện". Hai registry khai riêng nhưng phải trỏ về cùng một
nguồn: chép thành hai bản là sớm muộn sửa một bên, bên kia lặng lẽ giữ giá trị cũ — mà sai ở
đây thì hồ sơ nộp lên SAI CƠ QUAN, không ai phát hiện tới lúc bị trả lại.
"""
import pytest

from app.channels.handfree.procedure_registry import PROCEDURES as HANDFREE
from app.procedures import agency_plans
from app.procedures.registry import PROCEDURES as CORE

_KEY = "khai-sinh-dang-ky"
# Engine fill-angular của CẢ HAI bản extension hiểu đúng bấy nhiêu comp (đã đối chiếu source).
_COMPS = {"select", "diachi", "checkbox", "radio-bylabel", "raw", "date", "ngaysinh", "text"}


def _entry(procedures):
    return next(p for p in procedures if p["key"] == _KEY)


def test_hai_kenh_dung_cung_mot_ke_hoach():
    assert _entry(CORE)["agencyFillPlan"] == _entry(HANDFREE)["agencyFillPlan"]
    assert _entry(CORE)["agencyFillPlan"] == agency_plans.LIEN_THONG_KHAI_SINH


def test_extension_no_handfree_nhan_duoc_ke_hoach():
    """public_list() trả thẳng PROCEDURES — thiếu khoá này là nút không bao giờ hiện."""
    from app.procedures.registry import public_list

    assert _entry(public_list())["agencyFillPlan"]


@pytest.mark.parametrize("step", agency_plans.LIEN_THONG_KHAI_SINH)
def test_moi_buoc_dung_hop_dong_fields(step):
    assert set(step) == {"name", "comp", "value"}, step
    assert step["comp"] in _COMPS, f"engine không hiểu comp '{step['comp']}'"


def test_dien_dung_sau_o_can_cham_tay():
    """Khoá danh sách ô. Thêm ô readonly (Cơ quan thực hiện, tên cơ quan BHXH…) là ghi đè lên
    giá trị cổng vừa tự suy; thêm khối thường trú là đè lên phần "Cùng địa bàn" tự mirror."""
    assert [s["name"] for s in agency_plans.LIEN_THONG_KHAI_SINH] == [
        "IsNuocNgoai", "CqdkksDiaChi", "DkksTruongHop",
        "CqdkttIsDkks", "DkttTruongHop", "IsCapTheCanCuoc",
    ]


def test_tick_cap_the_can_cuoc():
    """Yêu cầu nghiệp vụ: mặc định tích "Cấp thẻ căn cước" cho trẻ."""
    step = next(s for s in agency_plans.LIEN_THONG_KHAI_SINH if s["name"] == "IsCapTheCanCuoc")
    assert step["comp"] == "checkbox" and step["value"] is True


def test_cho_trong_dia_ban_dung_dung_ten_placeholder():
    """Hai kênh đều tự thay {province}/{ward}; đổi tên chỗ trống ở đây mà quên sửa bên kia là
    ô Tỉnh nhận nguyên chuỗi "{province}"."""
    diachi = next(s for s in agency_plans.LIEN_THONG_KHAI_SINH if s["comp"] == "diachi")
    assert diachi["value"] == {"tinh": "{province}", "xa": "{ward}"}


def test_khong_con_cho_trong_nao_khac():
    """Chỗ trống lạ sẽ không được thay và đi thẳng vào ô trên cổng."""
    import json
    import re

    found = set(re.findall(r"\{(\w+)\}", json.dumps(agency_plans.LIEN_THONG_KHAI_SINH,
                                                    ensure_ascii=False)))
    assert found <= {"province", "ward"}, f"chỗ trống chưa ai thay: {found - {'province', 'ward'}}"
