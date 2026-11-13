"""Xác định mức độ khuyết tật — chủ hồ sơ = người ở mục I; người nộp có hai chế độ.

Theo tài khoản (mặc định): người nộp khớp mỏ neo UI. Theo tờ khai (`submitterMode`): người nộp là
người đại diện hợp pháp (mục II); mục II trống thì người khuyết tật tự nộp. Dữ liệu giả.
"""

import asyncio

from app.pipelines.khuyet_tat.process import mapper, runner

_TO_KHAI = {"submitterMode": "owner_as_submitter"}
_TK_DAI_DIEN = {"formContext": {"applicantFullname": "NGUYỄN VĂN CHA", "applicantIdentityNumber": "001080000002"}}
_TK_NKT = {"formContext": {"applicantFullname": "NGUYỄN VĂN CON", "applicantIdentityNumber": "001220000001"}}

_MUC_I = {
    "Nkt_HoTen": "Nguyễn Văn Con",
    "Nkt_SoDinhDanh": "001220000001",
    "Nkt_NgaySinh": "01/02/2020",
    "Nkt_GioiTinh": "Nam",
    "Nkt_ThuongTru": {"quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "Hải Châu", "diaChi": "Tổ 1"},
}
_MUC_II = {
    "Ndd_HoTen": "Nguyễn Văn Cha",
    "Ndd_SoDinhDanh": "001080000002",
    "Ndd_NgaySinh": "03/04/1980",
    "Ndd_NgayCap": "05/06/2022",
    "Ndd_SoDienThoai": "0900000002",
    "Ndd_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "Hải Châu", "diaChi": "Tổ 2"},
}


def _fields(*groups):
    values = {}
    for group in groups:
        values.update(group)
    return [{"name": k, "comp": "x-input", "value": v} for k, v in values.items()]


def _values(out):
    return {f["name"]: f["value"] for f in out}


def test_chu_ho_so_du_phong_tu_muc_i_khong_lay_nguoi_dai_dien():
    d = _values(mapper.enrich(_fields(_MUC_I, _MUC_II), {}))
    assert d["data[ownerFullname]"] == "Nguyễn Văn Con"
    assert d["data[ownerIdentityNumber]"] == "001220000001"
    assert d["data[ownerBirthday]"] == "01/02/2020"


def test_tai_khoan_nguoi_dai_dien_bo_tich_chu_ho_so_la_nguoi_khuyet_tat():
    out = mapper.enrich(_fields(_MUC_I, _MUC_II), _TK_DAI_DIEN)
    assert not any(f.get("enableInput") for f in out)
    d = _values(out)
    assert d["data[isOwnerDossierCheck]"] is False
    assert d["data[fullname]"] == "NGUYỄN VĂN CHA"
    assert d["data[ownerFullname]"] == "Nguyễn Văn Con"


def test_tai_khoan_la_nguoi_khuyet_tat_thi_tich():
    d = _values(mapper.enrich(_fields(_MUC_I), _TK_NKT))
    assert d["data[isOwnerDossierCheck]"] is True
    assert d["data[ownerFullname]"] == "Nguyễn Văn Con"


def test_to_khai_nguoi_nop_la_nguoi_dai_dien_bo_qua_tai_khoan():
    out = mapper.enrich(_fields(_MUC_I, _MUC_II), {**_TO_KHAI, **_TK_NKT})
    d = _values(out)
    assert out[0]["name"] == "data[isOwnerDossierCheck]" and out[0]["value"] is False
    assert d["data[fullname]"] == "Nguyễn Văn Cha"
    assert d["data[identityNumber]"] == "001080000002"
    assert d["data[birthday]"] == "03/04/1980"
    assert d["data[identityDate]"] == "05/06/2022"
    assert d["data[district]"] == "Phường Hải Châu" and d["data[address]"] == "Tổ 2"
    assert d["data[phoneNumber]"] == "0900000002"
    locked = {f["name"]: f.get("enableInput") for f in out if f["name"] in ("data[fullname]", "data[identityNumber]")}
    assert locked == {"data[fullname]": True, "data[identityNumber]": True}
    # Mục II không ghi giới tính → suy từ số định danh người đại diện (chữ số thứ 4: chẵn → Nam); nơi cấp không có
    # nguồn → để trống, không bịa.
    assert d["data[gender]"] == "Nam" and "data[idIssuePlace]" not in d
    assert d["data[ownerFullname]"] == "Nguyễn Văn Con"


def test_to_khai_nguoi_dai_dien_khong_ngay_sinh_thi_xoa_trong():
    muc_ii = {k: v for k, v in _MUC_II.items() if k != "Ndd_NgaySinh"}
    out = mapper.enrich(_fields(_MUC_I, muc_ii), {**_TO_KHAI, **_TK_NKT})
    birthday = [f for f in out if f["name"] == "data[birthday]"]
    assert len(birthday) == 1
    assert birthday[0]["value"] == "" and birthday[0]["clear"] is True and birthday[0]["markEmpty"] is True
    assert _values(out)["data[fullname]"] == "Nguyễn Văn Cha"


def test_to_khai_muc_ii_trong_thi_nguoi_khuyet_tat_tu_nop():
    out = mapper.enrich(_fields(_MUC_I), _TO_KHAI)
    d = _values(out)
    assert out[0]["name"] == "data[isOwnerDossierCheck]" and out[0]["value"] is True
    assert d["data[fullname]"] == "Nguyễn Văn Con"
    assert d["data[identityNumber]"] == "001220000001"
    assert d["data[ownerFullname]"] == "Nguyễn Văn Con"


def test_to_khai_khong_dua_moc_tai_khoan_vao_prompt():
    ctx = asyncio.run(runner._owner_only_context([{"text": "CCCD 001080000002"}], {**_TO_KHAI, **_TK_DAI_DIEN}))
    assert 'result="missing_ui_anchor"' in ctx
    assert "001080000002" not in ctx and "NGUYỄN VĂN CHA" not in ctx


def test_ngay_sinh_chi_co_nam_khong_ghi_de_o_ngay_sinh():
    """LLM hay suy năm sinh từ số CCCD ("1980") — ô ngày cổng cần đủ ngày/tháng/năm, ghi năm trần làm sai ngày tài
    khoản đổ sẵn → bỏ (cả hai chế độ người nộp)."""
    nguoi_nop = {"NguoiNop_HoTen": "Nguyễn Văn Cha", "NguoiNop_SoDinhDanh": "001080000002", "NguoiNop_NgaySinh": "1980"}
    d = _values(mapper.enrich(_fields(_MUC_I, _MUC_II, nguoi_nop), _TK_DAI_DIEN))
    assert "data[birthday]" not in d
    d = _values(mapper.enrich(_fields(_MUC_I, {**_MUC_II, "Ndd_NgaySinh": "1980"}), _TO_KHAI))
    assert d.get("data[birthday]", "") == ""


def test_ho_ten_nguoi_dai_dien_theo_tai_khoan_khi_cung_so_dinh_danh():
    """Chữ viết tay mục II hay mất dấu khi OCR; người đại diện cùng số định danh với tài khoản đang nộp → họ tên tài
    khoản. Khác số thì giữ nguyên chữ trên đơn."""
    d = _values(mapper.enrich(_fields(_MUC_I, {**_MUC_II, "Ndd_HoTen": "Nguyễn Văn Cha Mất Dấu"}), _TK_DAI_DIEN))
    assert d["data[NddHoTen]"] == "NGUYỄN VĂN CHA"
    d = _values(mapper.enrich(_fields(_MUC_I, {**_MUC_II, "Ndd_HoTen": "Nguyễn Văn Cha Mất Dấu"}), _TK_NKT))
    assert d["data[NddHoTen]"] == "Nguyễn Văn Cha Mất Dấu"


def test_gioi_tinh_nguoi_nop_suy_tu_so_dinh_danh_khi_giay_khong_ghi():
    """Theo tài khoản: giấy không ghi giới tính người nộp → suy từ số định danh tài khoản (chữ số thứ 4 lẻ → Nữ)."""
    tk = {"formContext": {"applicantFullname": "NGUYỄN THỊ MẸ", "applicantIdentityNumber": "001190000003"}}
    d = _values(mapper.enrich(_fields(_MUC_I), tk))
    assert d["data[gender]"] == "Nữ"
    # Giấy ghi rõ giới tính đúng người → theo giấy.
    nguoi_nop = {"NguoiNop_HoTen": "Nguyễn Thị Mẹ", "NguoiNop_SoDinhDanh": "001190000003", "NguoiNop_GioiTinh": "Nam"}
    d = _values(mapper.enrich(_fields(_MUC_I, nguoi_nop), tk))
    assert d["data[gender]"] == "Nam"


def test_khanh_hoa_ghi_chu_co_dinh_theo_tai_khoan():
    """Tài khoản tỉnh Khánh Hòa: server bật cờ, mapper ghi ô Ghi chú bằng câu cố định. Tỉnh khác, thủ tục đổi/cấp lại
    dùng chung mapper, hay client tự gửi cờ đều không ghi."""
    kh = {"tinh": "Tỉnh Khánh Hoà", "xa": "Phường Giả"}
    opts = mapper.with_account_process_options(_TK_NKT, kh, "xac-dinh-muc-do-khuyet-tat")
    assert opts["khanhHoaGhiChu"] is True and opts["formContext"] == _TK_NKT["formContext"]
    d = _values(mapper.enrich(_fields(_MUC_I), opts))
    assert d["data[ghiChu]"] == "Xác định mức độ khuyết tật và cấp giấy xác nhận khuyết tật"

    gia = {**_TK_NKT, "khanhHoaGhiChu": True}
    for user, procedure in (
        ({"tinh": "Thành phố Đà Nẵng", "xa": "Phường Giả"}, "xac-dinh-muc-do-khuyet-tat"),
        (kh, "doi-cap-lai-giay-xac-nhan-khuyet-tat"),
        (None, "xac-dinh-muc-do-khuyet-tat"),
    ):
        opts = mapper.with_account_process_options(gia, user, procedure)
        assert "khanhHoaGhiChu" not in opts
        assert "data[ghiChu]" not in _values(mapper.enrich(_fields(_MUC_I), opts))
