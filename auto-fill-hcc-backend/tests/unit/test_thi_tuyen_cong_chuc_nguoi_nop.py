"""Thi tuyển công chức — hai chế độ người nộp (Phần I) như các thủ tục hưu trí/bảo trợ xã hội.

Ba ô Phần I (họ tên, ngày sinh, CCCD) cổng khoá và đổ từ VNeID: theo tài khoản KHÔNG ghi; theo tờ khai ghi
kèm `enableInput` để extension bỏ disabled. Dữ liệu giả.
"""

import asyncio

import pytest

from app.pipelines.thi_tuyen_cong_chuc.process import mapper as mapper_a
from app.pipelines.thi_tuyen_cong_chuc.process import runner as runner_a

_KHOA = ("data[fullname]", "data[birthday]", "data[identityNumber]")
_TK_DU_TUYEN = {"applicantFullname": "NGUYỄN VĂN GIẢ", "applicantIdentityNumber": "001099000001"}
_TK_KHAC = {"applicantFullname": "TRẦN THỊ KHÁC", "applicantIdentityNumber": "001099000002"}


def _facts(extra=None):
    values = {
        "Phieu_HoTen": "Nguyễn Văn Giả",
        "Phieu_SoDinhDanh": "001099000001",
        "Phieu_NgaySinh": "01/02/1999",
        "Phieu_GioiTinh": "Nam",
        "Phieu_NgayCap": "03/04/2021",
        "Phieu_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        "Phieu_DienThoai": "0900000001",
        "Phieu_NoiThuongTru": {"quocGia": "Việt Nam", "tinh": "Tỉnh Lai Châu", "xa": "Xã Giả", "diaChi": "Bản Giả"},
    }
    values.update(extra or {})
    return [{"name": k, "comp": "x-input", "value": v} for k, v in values.items()]


def _part_one(out):
    return {f["name"]: f for f in out if f.get("occurrence") == 0}


def _by_name(out):
    return {f["name"]: f["value"] for f in out if f.get("occurrence") in (None, 0)}


@pytest.fixture(params=[mapper_a], ids=["thi_tuyen"])
def mapper(request):
    return request.param


def test_tai_khoan_khop_nguoi_du_tuyen_tich_va_khong_ghi_o_khoa(mapper):
    out, warnings = mapper.enrich(_facts(), {"formContext": _TK_DU_TUYEN})
    one = _part_one(out)
    assert _by_name(out)["data[isOwnerDossierCheck]"] is True
    assert not set(_KHOA) & set(one)
    assert one["data[gender]"]["value"] == "Nam" and one["data[phoneNumber]"]["value"] == "0900000001"
    assert not any("người đang nộp" in w or "TỜ KHAI" in w for w in warnings)


def test_khong_co_moc_thi_khong_dien_phan_mot(mapper):
    for options in (None, {}, {"formContext": {}}):
        out, warnings = mapper.enrich(_facts(), options)
        assert not _part_one(out)
        values = _by_name(out)
        assert values["data[isOwnerDossierCheck]"] is False
        assert values["data[ownerFullname]"] == "Nguyễn Văn Giả"
        assert any("F5 trang cổng" in w for w in warnings)


def test_tai_khoan_khop_nguoi_nop_khac_bo_tich_phan_mot_la_nguoi_do(mapper):
    facts = _facts({
        "NguoiNop_HoTen": "Trần Thị Khác", "NguoiNop_SoDinhDanh": "001099000002",
        "NguoiNop_GioiTinh": "Nữ", "NguoiNop_DienThoai": "0900000002",
    })
    out, _ = mapper.enrich(facts, {"formContext": _TK_KHAC})
    one = _part_one(out)
    assert _by_name(out)["data[isOwnerDossierCheck]"] is False
    assert one["data[gender]"]["value"] == "Nữ" and one["data[phoneNumber]"]["value"] == "0900000002"
    assert not set(_KHOA) & set(one)
    assert _by_name(out)["data[ownerFullname]"] == "Nguyễn Văn Giả"


_CCCD_NGUOI_KHAC = {
    "Person1_HoTen": "TRẦN THỊ KHÁC", "Person1_SoDinhDanh": "001099000002", "Person1_NgaySinh": "05/06/2003",
    "Person1_GioiTinh": "Nữ", "Person1_NgayCap": "07/08/2022",
    "Person1_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Nghệ An", "xa": "Xã Khác", "diaChi": "Xóm Khác"},
}


def test_cccd_nguoi_nop_ho_nam_o_person1_van_nhan_la_nguoi_nop(mapper):
    out, warnings = mapper.enrich(_facts(_CCCD_NGUOI_KHAC), {"formContext": _TK_KHAC})
    one = _part_one(out)
    assert _by_name(out)["data[isOwnerDossierCheck]"] is False
    assert one["data[gender]"]["value"] == "Nữ"
    assert one["data[identityDate]"]["value"] == "07/08/2022"
    assert one["data[address]"]["value"] == "Xóm Khác"
    assert not set(_KHOA) & set(one)
    assert not any("người đang nộp" in w for w in warnings)


def test_cccd_nguoi_khac_khong_bo_sung_cho_nguoi_du_tuyen(mapper):
    facts = [f for f in _facts(_CCCD_NGUOI_KHAC) if f["name"] not in ("Phieu_NgayCap", "Phieu_NoiThuongTru")]
    out, _ = mapper.enrich(facts, {"formContext": _TK_DU_TUYEN})
    values = _by_name(out)
    assert "data[ownerIdentityDate]" not in values
    assert "data[ownerAddress]" not in values


def test_nguoi_nop_khac_khong_khop_tai_khoan_thi_khong_lay(mapper):
    facts = _facts({"NguoiNop_HoTen": "Lê Văn Lạ", "NguoiNop_SoDinhDanh": "001099000003", "NguoiNop_GioiTinh": "Nam"})
    out, warnings = mapper.enrich(facts, {"formContext": _TK_KHAC})
    assert not _part_one(out)
    assert any("Không xác định được người đang nộp" in w for w in warnings)


def test_to_khai_ghi_du_ca_o_khoa_kem_enable_input(mapper):
    out, warnings = mapper.enrich(_facts(), {"formContext": _TK_KHAC, "submitterMode": "owner_as_submitter"})
    one = _part_one(out)
    assert _by_name(out)["data[isOwnerDossierCheck]"] is True
    assert one["data[fullname]"]["value"] == "Nguyễn Văn Giả"
    assert one["data[identityNumber]"]["value"] == "001099000001"
    assert one["data[birthday]"]["value"] == "01/02/1999"
    assert all(one[name].get("enableInput") is True for name in _KHOA)
    assert any("TỜ KHAI" in w for w in warnings)


@pytest.mark.parametrize("runner", [runner_a], ids=["thi_tuyen"])
def test_runner_ngu_canh_nguoi_nop(runner):
    phieu = {"text": "PHIẾU ĐĂNG KÝ DỰ TUYỂN ... Họ và tên: Nguyễn Văn Giả ... CCCD 001099000001"}
    cccd_khac = {"text": "CĂN CƯỚC CÔNG DÂN Số 001099000002 Họ và tên TRẦN THỊ KHÁC"}
    ctx = asyncio.run(runner._requester_context([phieu, cccd_khac], {"formContext": _TK_DU_TUYEN}))
    assert 'result="owner_match"' in ctx
    ctx = asyncio.run(runner._requester_context([phieu, cccd_khac], {"formContext": _TK_KHAC}))
    assert 'result="document_match"' in ctx and "001099000002" in ctx and "001099000001" not in ctx
    ctx = asyncio.run(runner._requester_context([phieu], {}))
    assert 'result="missing_ui_anchor"' in ctx
    ctx = asyncio.run(runner._owner_only_context([phieu], {"formContext": _TK_KHAC}))
    assert 'result="missing_ui_anchor"' in ctx and "001099000002" not in ctx

