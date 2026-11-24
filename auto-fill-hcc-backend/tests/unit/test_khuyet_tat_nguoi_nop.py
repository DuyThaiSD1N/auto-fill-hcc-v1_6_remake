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
    assert d["data[ownerFullname]"] == "NGUYỄN VĂN CON"
    assert d["data[ownerIdentityNumber]"] == "001220000001"
    assert d["data[ownerBirthday]"] == "01/02/2020"


def test_tai_khoan_nguoi_dai_dien_bo_tich_chu_ho_so_la_nguoi_khuyet_tat():
    out = mapper.enrich(_fields(_MUC_I, _MUC_II), _TK_DAI_DIEN)
    # Chỉ hai ô họ tên + CCCD người nộp được bỏ khoá (xem test_theo_tai_khoan_luon_bo_khoa_hai_o_ho_ten_cccd_nguoi_nop).
    assert {f["name"] for f in out if f.get("enableInput")} == {"data[fullname]", "data[identityNumber]"}
    d = _values(out)
    assert d["data[isOwnerDossierCheck]"] is False
    assert d["data[fullname]"] == "NGUYỄN VĂN CHA"
    assert d["data[ownerFullname]"] == "NGUYỄN VĂN CON"


def test_tai_khoan_la_nguoi_khuyet_tat_thi_tich():
    d = _values(mapper.enrich(_fields(_MUC_I), _TK_NKT))
    assert d["data[isOwnerDossierCheck]"] is True
    assert d["data[ownerFullname]"] == "NGUYỄN VĂN CON"


def test_to_khai_nguoi_nop_la_nguoi_dai_dien_bo_qua_tai_khoan():
    out = mapper.enrich(_fields(_MUC_I, _MUC_II), {**_TO_KHAI, **_TK_NKT})
    d = _values(out)
    assert out[0]["name"] == "data[isOwnerDossierCheck]" and out[0]["value"] is False
    assert d["data[fullname]"] == "NGUYỄN VĂN CHA"
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
    assert d["data[ownerFullname]"] == "NGUYỄN VĂN CON"


def test_to_khai_nguoi_dai_dien_khong_ngay_sinh_thi_xoa_trong():
    muc_ii = {k: v for k, v in _MUC_II.items() if k != "Ndd_NgaySinh"}
    out = mapper.enrich(_fields(_MUC_I, muc_ii), {**_TO_KHAI, **_TK_NKT})
    birthday = [f for f in out if f["name"] == "data[birthday]"]
    assert len(birthday) == 1
    assert birthday[0]["value"] == "" and birthday[0]["clear"] is True and birthday[0]["markEmpty"] is True
    assert _values(out)["data[fullname]"] == "NGUYỄN VĂN CHA"


def test_to_khai_muc_ii_trong_thi_nguoi_khuyet_tat_tu_nop():
    out = mapper.enrich(_fields(_MUC_I), _TO_KHAI)
    d = _values(out)
    assert out[0]["name"] == "data[isOwnerDossierCheck]" and out[0]["value"] is True
    assert d["data[fullname]"] == "NGUYỄN VĂN CON"
    assert d["data[identityNumber]"] == "001220000001"
    assert d["data[ownerFullname]"] == "NGUYỄN VĂN CON"


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
    assert d["data[NddHoTen]"] == "NGUYỄN VĂN CHA MẤT DẤU"


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


def test_ngay_sai_dinh_dang_hoac_sau_hom_nay_thi_bo_iso_thi_doi():
    """Ô ngày cổng tự diễn giải chuỗi khác dd/mm/yyyy thành ngày vô nghĩa → chỉ phát ngày có thật, không sau hôm nay."""
    muc_i = {**_MUC_I, "Nkt_NgaySinh": "2020-02-01", "ChuHoSo_HoTen": "Nguyễn Văn Con",
             "ChuHoSo_SoDinhDanh": "001220000001", "ChuHoSo_NgaySinh": "2020-02-01", "ChuHoSo_NgayCap": "18/19/2025"}
    d = _values(mapper.enrich(_fields(muc_i), {}))
    assert d["data[NktNgaySinh]"] == "01/02/2020" and d["data[ownerBirthday]"] == "01/02/2020"
    assert "data[ownerIdentityDate]" not in d
    for bad in ("1988", "25/2026", "01/01/2999", "31/02/2000"):
        d = _values(mapper.enrich(_fields({**_MUC_I, "Nkt_NgaySinh": bad}), {}))
        assert "data[NktNgaySinh]" not in d, bad


def test_quan_he_theo_danh_sach_cua_cong():
    """Danh sách cổng: Ông, Bà, Cha, Mẹ, Vợ, Chồng, Con, Anh, Chị, Em, Cháu ruột, Khác. Họ hàng khác → Khác."""
    cases = {"Bố đẻ": "Cha", "Bà ngoại": "Bà", "Bác": "Khác", "Cô": "Khác", "Cậu ruột": "Khác",
             "Con dâu": "Con", "Con gái": "Con", "Cháu nội": "Cháu ruột", "Chồng": "Chồng", "Vợ": "Vợ",
             "Me": "Mẹ", "chong": "Chồng"}
    for raw, want in cases.items():
        d = _values(mapper.enrich(_fields(_MUC_I, {**_MUC_II, "Ndd_QuanHe": raw}), {}))
        assert d["data[NddQuanheNkt]"] == want, raw
    d = _values(mapper.enrich(_fields(_MUC_I, {**_MUC_II, "Ndd_QuanHe": "ba"}), {}))
    assert "data[NddQuanheNkt]" not in d


def test_tai_khoan_khop_gan_thi_nhan_la_chu_tai_khoan_va_lay_ten_so_theo_tai_khoan():
    """Chữ viết tay OCR lệch ít so với tài khoản VNeID của chính người đó: trùng hẳn một mỏ neo, mỏ kia lệch ≤2 chữ →
    vẫn là chủ tài khoản, họ tên + số theo tài khoản. Lệch cả hai thì không nhận."""
    lech_ten = {**_MUC_I, "Nkt_HoTen": "Nguyễn Văn Com"}
    d = _values(mapper.enrich(_fields(lech_ten), _TK_NKT))
    assert d["data[isOwnerDossierCheck]"] is True
    assert d["data[ownerFullname]"] == d["data[NktHoTen]"] == "NGUYỄN VĂN CON"
    lech_so = {**_MUC_I, "Nkt_SoDinhDanh": "001220000081"}
    d = _values(mapper.enrich(_fields(lech_so), _TK_NKT))
    assert d["data[isOwnerDossierCheck]"] is True
    assert d["data[ownerIdentityNumber]"] == d["data[NktSoDinhdanh]"] == "001220000001"
    lech_ca_hai = {**_MUC_I, "Nkt_HoTen": "Nguyễn Văn Com", "Nkt_SoDinhDanh": "001220000081"}
    d = _values(mapper.enrich(_fields(lech_ca_hai), _TK_NKT))
    assert d["data[isOwnerDossierCheck]"] is False and d["data[NktSoDinhdanh]"] == "001220000081"
    # Người đại diện là chủ tài khoản, OCR lệch một số → số theo tài khoản; theo tờ khai cũng vậy.
    muc_ii = {**_MUC_II, "Ndd_SoDinhDanh": "001080000092"}
    d = _values(mapper.enrich(_fields(_MUC_I, muc_ii), _TK_DAI_DIEN))
    assert d["data[NddSoDinhdanh]"] == "001080000002"
    d = _values(mapper.enrich(_fields(_MUC_I, muc_ii), {**_TO_KHAI, **_TK_DAI_DIEN}))
    assert d["data[identityNumber]"] == "001080000002"


def test_ngay_sinh_nguoi_nop_lech_nam_voi_so_tai_khoan_thi_bo():
    """Năm sinh mã hoá trong số định danh tài khoản (chữ số 4–6): ngày lệch năm là ngày khác lạc vào → bỏ."""
    nguoi_nop = {"NguoiNop_HoTen": "Nguyễn Văn Cha", "NguoiNop_SoDinhDanh": "001080000002"}
    d = _values(mapper.enrich(_fields(_MUC_I, {**nguoi_nop, "NguoiNop_NgaySinh": "26/10/2025"}), _TK_DAI_DIEN))
    assert "data[birthday]" not in d
    d = _values(mapper.enrich(_fields(_MUC_I, {**nguoi_nop, "NguoiNop_NgaySinh": "03/04/1980"}), _TK_DAI_DIEN))
    assert d["data[birthday]"] == "03/04/1980"


def test_theo_tai_khoan_luon_bo_khoa_hai_o_ho_ten_cccd_nguoi_nop():
    """Cổng khoá ô họ tên + CCCD Phần I theo tài khoản VNeID: luôn kèm enableInput; không có giá trị thì chỉ bỏ khoá + tô
    đỏ (dom-expect), không ghi đè."""
    out = mapper.enrich(_fields(_MUC_I, _MUC_II), _TK_DAI_DIEN)
    by = {f["name"]: f for f in out}
    assert by["data[fullname]"]["enableInput"] is True and by["data[fullname]"]["value"] == "NGUYỄN VĂN CHA"
    assert by["data[identityNumber]"]["enableInput"] is True
    by = {f["name"]: f for f in mapper.enrich(_fields(_MUC_I, _MUC_II), {})}
    for name in ("data[fullname]", "data[identityNumber]"):
        assert by[name] == {"name": name, "comp": "dom-expect", "value": "", "enableInput": True}


def test_to_khai_ngay_sinh_ngay_cap_nguoi_dai_dien_phai_cua_chinh_nguoi_do_tren_giay():
    """Mục II không ghi ngày sinh / ngày cấp: model từng ghép "01/01/<năm suy từ số CCCD>" và lấy ngày cấp thẻ người khuyết
    tật trên giấy ra viện cho người đại diện → bỏ (ngày sinh xoá ô cổng đổ sẵn), giữ cho chủ hồ sơ."""
    ocr = ("II. Thông tin người đại diện hợp pháp\n- Họ và tên: Nguyễn Văn Cha\n"
           "- Số CMND hoặc căn cước công dân: 001080000002\n"
           "Số CCCD/CMND: 001220000001 Ngày cấp: 05/06/2022\n")
    muc_ii = {**_MUC_II, "Ndd_NgaySinh": "01/01/1980", "Ndd_NgayCap": "05/06/2022", "Ndd_NoiCap": "Cục Cảnh sát"}
    out = {f["name"]: f for f in mapper.enrich(_fields(_MUC_I, muc_ii), {**_TO_KHAI, "_ocr_text": ocr})}
    assert out["data[birthday]"]["value"] == "" and out["data[birthday]"]["clear"] is True
    assert "data[identityDate]" not in out and "data[idIssuePlace]" not in out
    # Ngày có trên giấy, cùng dòng với số của chính người đại diện → giữ.
    ocr_ok = ocr + "Họ tên: Nguyễn Văn Cha, sinh ngày 03/04/1980, CCCD 001080000002 cấp ngày 07/08/2021\n"
    muc_ii = {**muc_ii, "Ndd_NgaySinh": "03/04/1980", "Ndd_NgayCap": "07/08/2021"}
    out = {f["name"]: f["value"] for f in mapper.enrich(_fields(_MUC_I, muc_ii), {**_TO_KHAI, "_ocr_text": ocr_ok})}
    assert out["data[birthday]"] == "03/04/1980" and out["data[identityDate]"] == "07/08/2021"
    assert out["data[idIssuePlace]"] == "Cục Cảnh sát"


def test_ho_ten_nguoi_trong_ho_so_in_hoa_nguoi_nop_theo_tai_khoan_giu_nguyen():
    tk = {"formContext": {"applicantFullname": "Nguyễn Văn Cha", "applicantIdentityNumber": "001080000002"}}
    d = _values(mapper.enrich(_fields(_MUC_I, _MUC_II), tk))
    assert d["data[ownerFullname]"] == d["data[NktHoTen]"] == "NGUYỄN VĂN CON"
    assert d["data[NddHoTen]"] == "NGUYỄN VĂN CHA"
    assert d["data[fullname]"] == "Nguyễn Văn Cha"  # tên VNeID cổng đổ sẵn
    assert _values(mapper.enrich(_fields(_MUC_I, _MUC_II), _TO_KHAI))["data[fullname]"] == "NGUYỄN VĂN CHA"


def test_moc_lai_ten_nguoi_khac_so_nguoi_dai_dien_thi_khong_doi_ten():
    """Điền lại trên form đã điền: ô họ tên khoá được cổng đổ lại tên tài khoản (người khuyết tật), ô số còn số người đại
    diện lượt trước ghi → mốc lai hai người, không đổi tên người đại diện / người nộp theo mốc."""
    moc_lai = {"formContext": {"applicantFullname": "NGUYỄN VĂN CON", "applicantIdentityNumber": "001080000002"}}
    for options in (moc_lai, {**moc_lai, **_TO_KHAI}):
        d = _values(mapper.enrich(_fields(_MUC_I, _MUC_II), options))
        assert d["data[NddHoTen]"] == "NGUYỄN VĂN CHA"
    d = _values(mapper.enrich(_fields(_MUC_I, _MUC_II), {**moc_lai, **_TO_KHAI}))
    assert d["data[fullname]"] == "NGUYỄN VĂN CHA"
