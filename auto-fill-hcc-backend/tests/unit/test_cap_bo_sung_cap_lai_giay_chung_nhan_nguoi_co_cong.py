"""Cấp bổ sung hoặc cấp lại giấy chứng nhận người có công / thân nhân liệt sĩ (1.010814, Mẫu số 25)."""

from app.pipelines.cap_bo_sung_cap_lai_giay_chung_nhan_nguoi_co_cong.attach import planner
from app.pipelines.cap_bo_sung_cap_lai_giay_chung_nhan_nguoi_co_cong.process import mapper
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS

KEY = "cap-bo-sung-cap-lai-giay-chung-nhan-nguoi-co-cong"
_TU_NOP = {"formContext": {"applicantFullname": "Trần Văn Mẫu", "applicantIdentityNumber": "001203000111",
                           "applicantBirthday": "03/12/2003"}}
_NOP_THAY = {"formContext": {"applicantFullname": "Lê Thị Khác", "applicantIdentityNumber": "001190000999"}}


def _values(**overrides):
    values = {
        "Don_HoTen": "TRẦN VĂN MẪU",
        "Don_NgaySinh": "15/03/2003",
        "Don_GioiTinh": "Nam",
        "Don_SoDinhDanh": "001203000111",
        "Don_NgayCap": "01/07/2026",
        "Don_NoiCap": "Bộ Công an",
        "Don_QueQuan": {"tinh": "Tỉnh Hưng Yên", "xa": "Xã Đông Quan", "diaChi": ""},
        "Don_NoiThuongTru": {"tinh": "Tỉnh Hưng Yên", "xa": "Xã Đông Quan", "diaChi": "Thôn Mẫu 1"},
        "Don_DienThoai": "0912 000 111",
        "Don_DienNguoiCoCong": "Thân nhân liệt sĩ (con của liệt sĩ Trần Văn Gốc)",
        "Don_SoQuyetDinh": "100/QĐ-LĐTBXH",
        "Don_NgayQuyetDinh": "12/5/2011",
        "Don_CoQuanQuyetDinh": "Giám đốc Sở Lao động - Thương binh và Xã hội tỉnh Mẫu",
        "Don_LoaiGiayChungNhan": "Giấy chứng nhận thân nhân liệt sĩ",
        "Don_LoaiDeNghi": "Cấp lại",
        "Don_LyDo": "Giấy chứng nhận bị hư hỏng do ngập nước.",
        "Person1_HoTen": "TRẦN VĂN MẪU",
        "Person1_SoDinhDanh": "001203000111",
        "Person1_NgaySinh": "15/03/2003",
        "Person1_GioiTinh": "Nam",
        "Person1_NgayCap": "01/07/2026",
        "Person1_NoiCap": "Bộ Công an",
    }
    values.update(overrides)
    return values


def _run(values, options=None):
    fields, warnings = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)
    by_key = {(f["name"], f.get("occurrence")): f["value"] for f in fields}
    return by_key, warnings


def test_registry_wires_key_from_ke_khai_links():
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.010814"
    proc = registry.get_procedure(KEY)
    assert proc["label"] == link["label"]
    assert proc["hasAttachmentStep"] is True and proc["detect"]["textPriority"] is True
    assert registry.get_pipeline(KEY) is not None and registry.get_attach_pipeline(KEY) is not None
    assert planner.__name__.split(".")[2] == KEY.replace("-", "_")


def test_tu_nop_dien_phan_i_khong_dung_o_khoa():
    f, warnings = _run(_values(), _TU_NOP)
    # Ô khoá theo tài khoản không phát ở Phần I.
    for locked in ("data[fullname]", "data[birthday]", "data[identityNumber]"):
        assert (locked, 0) not in f and (locked, None) not in f
    assert f[("data[gender]", 0)] == "Nam"
    assert f[("data[identityDate]", 0)] == "01/07/2026"
    assert f[("data[province]", 0)] == "Tỉnh Hưng Yên"
    assert f[("data[district]", None)] == "Xã Đông Quan"
    assert f[("data[address]", 0)] == "Thôn Mẫu 1"
    assert f[("data[phoneNumber]", 0)] == "0912000111"
    assert f[("data[isOwnerDossierCheck]", None)] is True
    assert any("Ngày sinh tài khoản" in w for w in warnings)
    # Phần II.
    assert f[("data[ownerFullname]", None)] == "TRẦN VĂN MẪU"
    assert f[("data[ownerBirthday]", None)] == "15/03/2003"
    assert f[("data[ownerNation]", None)] == "Việt Nam"


def test_phan_iii_mau_khai():
    f, _ = _run(_values(), _TU_NOP)
    assert f[("data[fullname]", 1)] == "TRẦN VĂN MẪU"
    assert f[("data[birthday]", 1)] == "15/03/2003"
    assert f[("data[identityNumber]", 1)] == "001203000111"
    assert f[("data[loaiDeNghi]", None)] == "Cấp lại"
    assert f[("data[loaiGiayChungNhan]", None)] == "Giấy chứng nhận thân nhân liệt sĩ"
    assert f[("data[province1]", None)] == "Tỉnh Hưng Yên"
    assert f[("data[village1]", None)] == "Xã Đông Quan"
    assert f[("data[address1]", None)] == "Xã Đông Quan, Tỉnh Hưng Yên", "quê quán chỉ tới xã → nhập lại xã, tỉnh"
    assert f[("data[province]", 1)] == "Tỉnh Hưng Yên"
    assert f[("data[village]", None)] == "Xã Đông Quan"
    assert f[("data[address]", 1)] == "Thôn Mẫu 1"
    assert f[("data[dienNguoiCoCong]", None)].startswith("Thân nhân liệt sĩ")
    assert f[("data[sqdTroCap]", None)] == "100/QĐ-LĐTBXH"
    assert f[("data[nqdTroCap]", None)] == "12/05/2011"
    assert f[("data[noiCap]", None)].startswith("Giám đốc Sở")
    assert f[("data[lyDo]", None)].startswith("Giấy chứng nhận bị hư hỏng")
    assert f[("data[hoSoDinhKem][0][textField2]", None)] == "Bản chính"
    assert f[("data[hoSoDinhKem][1][textField1]", None)] == "Căn cước công dân"


def test_nop_thay_khong_dien_phan_i():
    f, warnings = _run(_values(), _NOP_THAY)
    assert ("data[gender]", 0) not in f and ("data[province]", 0) not in f
    assert f[("data[isOwnerDossierCheck]", None)] is False
    assert f[("data[ownerFullname]", None)] == "TRẦN VĂN MẪU"
    assert any("không khớp người nộp" in w for w in warnings)


def test_gcn_cu_cua_nguoi_khac_khong_lay_so_lieu():
    values = _values(Don_SoQuyetDinh=None, Don_NgayQuyetDinh=None, Don_CoQuanQuyetDinh=None,
                     GCN_HoTen="Trần Văn Gốc", GCN_SoQuyetDinh="13", GCN_LoaiGiayChungNhan="GIẤY CHỨNG NHẬN")
    f, warnings = _run(values, _TU_NOP)
    assert ("data[sqdTroCap]", None) not in f
    assert any("khác người làm đơn" in w for w in warnings)


def test_loai_de_nghi_suy_tu_ly_do():
    f, _ = _run(_values(Don_LoaiDeNghi=None, Don_LyDo="Bổ sung số CCCD thay số giấy khai sinh"), _TU_NOP)
    assert f[("data[loaiDeNghi]", None)] == "Cấp bổ sung"


def test_plan_don_vao_dong_1_con_lai_them_giay_to():
    files = [{"name": n} for n in ("don.pdf", "gcn.pdf", "cccd.jpg", "la.pdf")]
    ocr = [
        {"name": "don.pdf", "text": "Mẫu số 25 ĐƠN ĐỀ NGHỊ Cấp bổ sung hoặc cấp lại giấy chứng nhận thân nhân "
                                    "liệt sĩ Tôi là Thân nhân liệt sĩ Lý do Người làm đơn"},
        {"name": "gcn.pdf", "text": "GIẤY CHỨNG NHẬN THÂN NHÂN LIỆT SĨ Được cấp theo Quyết định số 13"},
        {"name": "cccd.jpg", "text": "CĂN CƯỚC Số định danh cá nhân 001203000111"},
        {"name": "la.pdf", "text": "Biên bản họp gia đình"},
    ]
    items, warnings, _ = planner.build_plan_items(files, ocr, {})
    assert items[0]["target"] == "fixed-slot" and items[0]["slotIndex"] == 0
    assert [i["documentName"] for i in items[1:]] == ["Giấy chứng nhận đã cấp", "Căn cước công dân", "Giấy tờ kèm theo"]
    assert all(i["target"] == "new" for i in items[1:])
    assert any("la.pdf" in w for w in warnings)


def test_plan_thieu_don_canh_bao():
    items, warnings, _ = planner.build_plan_items([{"name": "a.jpg"}], [{"name": "a.jpg", "text": "CĂN CƯỚC CÔNG DÂN"}], {})
    assert items[0]["documentName"] == "Căn cước công dân"
    assert any("Mẫu số 25" in w for w in warnings)
