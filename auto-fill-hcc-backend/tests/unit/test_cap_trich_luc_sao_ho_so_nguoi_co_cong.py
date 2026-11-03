"""Cấp trích lục hoặc sao hồ sơ người có công với cách mạng (1.010828, Sở Nội vụ — cổng Bộ Nội vụ Form.io)."""

from app.pipelines.cap_trich_luc_sao_ho_so_nguoi_co_cong.attach import planner
from app.pipelines.cap_trich_luc_sao_ho_so_nguoi_co_cong.process import mapper
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS

KEY = "cap-trich-luc-sao-ho-so-nguoi-co-cong"
_TU_NOP = {"formContext": {"applicantFullname": "Trần Văn Mẫu", "applicantIdentityNumber": "001064000111"}}
_NOP_THAY = {"formContext": {"applicantFullname": "Lê Thị Khác", "applicantIdentityNumber": "001190000999"}}


def _values(**overrides):
    values = {
        "Don_TieuDe": "ĐƠN ĐỀ NGHỊ cấp trích lục hồ sơ người có công",
        "Don_HoTen": "Trần văn Mẫu",
        "Don_NgaySinh": "5/3/1964",
        "Don_GioiTinh": "Nam",
        "Don_SoDinhDanh": "001064000111",
        "Don_NgayCap": "3/9/2026",
        "Don_NoiCap": "Phường Mẫu Hòa",
        "Don_NoiThuongTru": {"tinh": "", "xa": "Phường Mẫu Hòa", "diaChi": "12 đường Mẫu"},
        "Don_DienThoai": "0912 000 111",
        "Person1_HoTen": "TRẦN VĂN MẪU",
        "Person1_SoDinhDanh": "001064000111",
        "Person1_NgaySinh": "05/03/1964",
        "Person1_GioiTinh": "Nam",
        "Person1_NgayCap": "05/09/2026",
        "Person1_NoiCap": "BỘ CÔNG AN",
        "Person1_NoiCuTru": {"tinh": "Khánh Hòa", "xa": "Nam Nha Trang", "diaChi": "12 Đường Mẫu"},
    }
    values.update(overrides)
    return values


def _run(values, options=None):
    fields, warnings = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)
    return {f["name"]: f["value"] for f in fields}, warnings


def test_registry_wires_key_from_ke_khai_links():
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.010828" and link["selectSo"] is True
    proc = registry.get_procedure(KEY)
    assert proc["label"] == link["label"]
    assert proc["hasAttachmentStep"] is True and proc["detect"]["textPriority"] is True
    assert registry.get_pipeline(KEY) is not None and registry.get_attach_pipeline(KEY) is not None
    assert planner.__name__.split(".")[2] == KEY.replace("-", "_")


def test_tu_nop_uu_tien_cccd_va_khong_dung_o_khoa():
    f, warnings = _run(_values(), _TU_NOP)
    for locked in ("data[fullname]", "data[birthday]", "data[identityNumber]", "data[chonDoiTuong]"):
        assert locked not in f
    assert f["data[isOwnerDossierCheck]"] is True
    assert f["data[gender]"] == "Nam"
    # Ngày cấp + nơi cấp theo thẻ, không theo Đơn viết tay.
    assert f["data[identityDate]"] == "05/09/2026"
    assert f["data[idIssuePlace]"] == "Bộ Công an"
    assert f["data[province]"] == "Tỉnh Khánh Hòa"
    assert f["data[district]"] == "Phường Nam Nha Trang"
    assert f["data[address]"] == "12 Đường Mẫu"
    assert f["data[phoneNumber]"] == "0912000111"
    assert any("Ngày cấp CCCD trên thẻ" in w for w in warnings)


def test_chu_ho_so_la_nguoi_lam_don():
    f, _ = _run(_values(), _TU_NOP)
    assert f["data[ownerFullname]"] == "TRẦN VĂN MẪU"
    assert f["data[ownerBirthday]"] == "05/03/1964"
    assert f["data[ownerGender]"] == "Nam"
    assert f["data[ownerIdentityNumber]"] == "001064000111"
    assert f["data[ownerIdentityDate]"] == "05/09/2026"
    assert f["data[ownerIdIssuePlace]"] == "Bộ Công an"
    assert f["data[ownerProvince]"] == "Tỉnh Khánh Hòa"
    assert f["data[ownerDistrict]"] == "Phường Nam Nha Trang"
    assert f["data[ownerAddress]"] == "12 Đường Mẫu"
    assert f["data[ownerPhoneNumber]"] == "0912000111"
    assert f["data[ownerNation]"] == "Việt Nam"


def test_nop_thay_khong_co_giay_to_nguoi_nop_de_trong_phan_i():
    f, warnings = _run(_values(), _NOP_THAY)
    assert f["data[isOwnerDossierCheck]"] is False
    for name in ("data[fullname]", "data[identityNumber]", "data[identityDate]", "data[idIssuePlace]",
                 "data[province]", "data[address]", "data[phoneNumber]"):
        assert name not in f
    assert f["data[gender]"] == "Nữ"  # Suy từ số định danh tài khoản, không lấy giới tính người làm đơn.
    assert f["data[ownerFullname]"] == "TRẦN VĂN MẪU"
    assert any("nộp thay" in w and "tự nhập ngày cấp, nơi cấp, địa chỉ" in w for w in warnings)


_CCCD_NGUOI_NOP = {
    "NguoiNop_HoTen": "LÊ THỊ KHÁC",
    "NguoiNop_SoDinhDanh": "001190000999",
    "NguoiNop_GioiTinh": "Nữ",
    "NguoiNop_NgayCap": "10/10/2021",
    "NguoiNop_NoiCap": "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
    "NguoiNop_NoiCuTru": {"tinh": "Thành phố Hà Nội", "xa": "Phường Mẫu Đình", "diaChi": "Số 5 ngõ Mẫu"},
}


def test_nop_thay_lay_phan_i_tu_cccd_nguoi_dang_nhap():
    f, warnings = _run(_values(**_CCCD_NGUOI_NOP), _NOP_THAY)
    assert f["data[isOwnerDossierCheck]"] is False
    assert "data[fullname]" not in f and "data[identityNumber]" not in f  # Ô khoá giữ theo tài khoản.
    assert f["data[gender]"] == "Nữ"
    assert f["data[identityDate]"] == "10/10/2021"
    assert f["data[idIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert f["data[province]"] == "Thành phố Hà Nội"
    assert f["data[address]"] == "Số 5 ngõ Mẫu"
    assert "data[phoneNumber]" not in f  # SĐT trên Đơn là của người làm đơn.
    # Chủ hồ sơ vẫn là người làm đơn.
    assert f["data[ownerFullname]"] == "TRẦN VĂN MẪU"
    assert f["data[ownerAddress]"] == "12 Đường Mẫu"
    assert any("Tự nhập SĐT người nộp" in w for w in warnings)


def test_nop_thay_cccd_nguoi_dang_nhap_lo_vao_person1():
    """LLM lỡ xếp CCCD người đăng nhập vào Person1_*: không dùng cho chủ hồ sơ, dùng cho Phần I."""
    values = _values(**{k.replace("NguoiNop_", "Person1_"): v for k, v in _CCCD_NGUOI_NOP.items()})
    f, warnings = _run(values, _NOP_THAY)
    assert f["data[ownerIdentityNumber]"] == "001064000111"
    assert f["data[ownerFullname]"] == "Trần văn Mẫu"
    assert f["data[identityDate]"] == "10/10/2021"
    assert not any("không phải của người làm đơn" in w for w in warnings)


def test_nguoi_nop_khong_khop_tai_khoan_thi_khong_dung():
    f, _ = _run(_values(**{**_CCCD_NGUOI_NOP, "NguoiNop_SoDinhDanh": "001190000777"}), _NOP_THAY)
    assert "data[identityDate]" not in f and "data[province]" not in f


_THEO_TO_KHAI = {**_NOP_THAY, "submitterMode": "owner_as_submitter"}


def test_bat_lay_nguoi_nop_theo_to_khai():
    raw, warnings = mapper.enrich([{"name": k, "value": v} for k, v in _values().items()], _THEO_TO_KHAI)
    by_name = {field["name"]: field for field in raw}
    f = {name: field["value"] for name, field in by_name.items()}
    assert f["data[isOwnerDossierCheck]"] is True
    assert f["data[fullname]"] == "TRẦN VĂN MẪU" and by_name["data[fullname]"]["enableInput"] is True
    assert f["data[identityNumber]"] == "001064000111" and by_name["data[identityNumber]"]["enableInput"] is True
    assert f["data[birthday]"] == "05/03/1964"
    assert f["data[gender]"] == "Nam"
    assert f["data[identityDate]"] == "05/09/2026"
    assert f["data[province]"] == "Tỉnh Khánh Hòa"
    assert f["data[phoneNumber]"] == "0912000111"
    assert any("Lấy người nộp theo tờ khai" in w for w in warnings)
    assert not any("nộp thay" in w for w in warnings)


def test_theo_to_khai_thieu_ngay_sinh_thi_xoa_ngay_sinh_tai_khoan():
    values = _values(Person1_NgaySinh="", Don_NgaySinh="")
    raw, _ = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], _THEO_TO_KHAI)
    birthday = next(field for field in raw if field["name"] == "data[birthday]")
    assert birthday["value"] == "" and birthday["clear"] is True and birthday["markEmpty"] is True


def test_theo_to_khai_trung_tai_khoan_khong_canh_bao():
    _, warnings = _run(_values(), {**_TU_NOP, "submitterMode": "owner_as_submitter"})
    assert not any("Lấy người nộp theo tờ khai" in w for w in warnings)


def test_dia_chi_the_mat_so_nha_lay_chi_tiet_don():
    f, _ = _run(_values(
        Person1_NoiCuTru={"tinh": "Khánh Hòa", "xa": "Nam Nha Trang", "diaChi": "Đường Mẫu"},
        Don_NoiThuongTru={"tinh": "", "xa": "Phường Nam Nha Trang", "diaChi": "12 Đường Mẫu"},
    ), _TU_NOP)
    assert f["data[ownerProvince]"] == "Tỉnh Khánh Hòa"
    assert f["data[ownerAddress]"] == "12 Đường Mẫu"


def test_khong_co_cccd_lay_theo_don():
    values = {k: v for k, v in _values().items() if not k.startswith("Person1_")}
    values["Don_NoiThuongTru"] = {"tinh": "Khánh Hòa", "xa": "Phường Mẫu Hòa", "diaChi": "12 đường Mẫu"}
    f, _ = _run(values)
    assert f["data[ownerFullname]"] == "Trần văn Mẫu"
    assert f["data[ownerIdentityDate]"] == "03/09/2026"
    assert f["data[ownerIdIssuePlace]"] == "Phường Mẫu Hòa"
    assert f["data[ownerAddress]"] == "12 đường Mẫu"
    assert f["data[hoSoDinhKem][0][textField2]"] == "Bản chính"
    assert "data[hoSoDinhKem][1][textField1]" not in f


def test_cccd_nguoi_khac_khong_dung():
    f, warnings = _run(_values(Person1_HoTen="LÊ THỊ KHÁC", Person1_SoDinhDanh="001190000999"))
    assert f["data[ownerIdentityNumber]"] == "001064000111"
    assert f["data[ownerFullname]"] == "Trần văn Mẫu"
    assert any("không phải của người làm đơn" in w for w in warnings)


def test_bang_ho_so_kem_theo_va_canh_bao_don_di_chuyen():
    f, warnings = _run(_values())
    assert f["data[hoSoDinhKem][0][textField1]"] == "Đơn đề nghị cấp trích lục hồ sơ người có công"
    assert f["data[hoSoDinhKem][0][textField2]"] == "Bản chính"
    assert f["data[hoSoDinhKem][1][textField1]"] == "Căn cước công dân"
    assert f["data[hoSoDinhKem][1][textField2]"] == "Bản sao"
    assert not any("không phải đơn đề nghị cấp trích lục" in w for w in warnings)

    f, warnings = _run(_values(Don_TieuDe="ĐƠN ĐỀ NGHỊ Di chuyển hồ sơ trợ cấp một lần"))
    assert f["data[hoSoDinhKem][0][textField1]"] == "Đơn đề nghị di chuyển hồ sơ trợ cấp một lần"
    assert any("không phải đơn đề nghị cấp trích lục" in w for w in warnings)


def test_gioi_tinh_suy_tu_so_dinh_danh():
    f, _ = _run(_values(Person1_GioiTinh="", Don_GioiTinh=""))
    assert f["data[ownerGender]"] == "Nam"


_DON_TEXT = (
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM ĐƠN ĐỀ NGHỊ Di chuyển hồ sơ trợ cấp một lần Kính gửi: Sở Nội vụ tỉnh Mẫu "
    "Họ và tên: Trần Văn Mẫu CCCD/CMND số: 001064000111 Người làm đơn"
)
_CCCD_TEXT = "CĂN CƯỚC IDENTITY CARD Số định danh cá nhân 001064000111 IDVNM0640001110001064000111<<6"


def test_attach_don_va_cccd_dinh_chung_dong_1():
    files = [{"name": "cccd.pdf"}, {"name": "don.pdf"}]
    ocr = [{"name": "cccd.pdf", "text": _CCCD_TEXT}, {"name": "don.pdf", "text": _DON_TEXT}]
    items, warnings, classified = planner.build_plan_items(files, ocr)
    assert [i["fileName"] for i in items] == ["don.pdf", "cccd.pdf"]  # Đơn trước.
    assert all(i["target"] == "fixed-slot" and i["slotIndex"] == 0 for i in items)
    assert items[1]["documentName"] == "Căn cước công dân"
    assert {c["docType"] for c in classified} == {"don_de_nghi", "identity_document"}
    assert any("di chuyển hồ sơ" in w for w in warnings)


def test_attach_tep_la_van_dinh_dong_1_va_canh_bao_thieu_don():
    files = [{"name": "anh.jpg"}]
    items, warnings, _ = planner.build_plan_items(files, [{"name": "anh.jpg", "text": "Ảnh chụp không rõ"}])
    assert items[0]["slotIndex"] == 0 and items[0]["documentName"] == "Giấy tờ kèm theo"
    assert any("Không nhận ra loại giấy tờ" in w for w in warnings)
    assert any("Chưa có Đơn đề nghị" in w for w in warnings)


def test_attach_don_trich_luc_khong_canh_bao():
    text = "ĐƠN ĐỀ NGHỊ cấp trích lục hồ sơ người có công Người làm đơn"
    items, warnings, _ = planner.build_plan_items([{"name": "don.pdf"}], [{"name": "don.pdf", "text": text}])
    assert items[0]["detectedType"] == "Đơn đề nghị cấp trích lục hoặc sao hồ sơ người có công"
    assert warnings == []


def _context(options, texts):
    import asyncio

    from app.pipelines.cap_trich_luc_sao_ho_so_nguoi_co_cong.process import runner

    return asyncio.run(runner._submitter_context([{"text": t} for t in texts], options))


def test_runner_neo_cccd_nguoi_dang_nhap():
    cccd_nop = "CĂN CƯỚC CÔNG DÂN Số: 001190000999 Họ và tên: LÊ THỊ KHÁC"
    ctx = _context(_NOP_THAY, [_DON_TEXT, _CCCD_TEXT, cccd_nop])
    assert 'result="co_giay_to"' in ctx and "tài liệu #3" in ctx


def test_runner_bo_moc_khi_theo_to_khai_hoac_thieu_moc():
    cccd_nop = "CĂN CƯỚC CÔNG DÂN Số: 001190000999 Họ và tên: LÊ THỊ KHÁC"
    assert 'result="owner_as_submitter"' in _context(_THEO_TO_KHAI, [cccd_nop])
    assert 'result="missing_ui_anchor"' in _context({}, [cccd_nop])
    assert 'result="khong_co_giay_to"' in _context(_NOP_THAY, [_DON_TEXT])
