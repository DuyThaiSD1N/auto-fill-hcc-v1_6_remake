"""Tests cho thủ tục "Xác nhận thông tin hộ tịch" (mã 2.002516).

Hồ sơ mẫu (dữ liệu bịa): con đẻ nộp thay, xác nhận thông tin hộ tịch cho bố.
Phần 1 người nộp = người con (tờ khai + CCCD), Phần 2 chủ hồ sơ = người bố (tờ khai / giấy khai sinh + CMND).
"""

from app.pipelines.xac_nhan_thong_tin_ho_tich import process as agent
from app.pipelines.xac_nhan_thong_tin_ho_tich.attach import plan as attach_plan
from app.pipelines.xac_nhan_thong_tin_ho_tich.attach.planner import build_plan_items
from app.pipelines.xac_nhan_thong_tin_ho_tich.process import mapper
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

KEY = "xac-nhan-thong-tin-ho-tich"


def _field(name, value):
    return {"name": name, "comp": "x-input", "value": value}


def _values(mapped: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in mapped}


def _ho_so_nop_thay() -> list[dict]:
    return [
        _field("TkNyc_HoTen", "Lê Thị Mai"),
        _field("TkNyc_SoGiayToTuyThan", "001190012345"),
        _field("TkNyc_NgayCapGiayToTuyThan", "15/3/2021"),
        _field("TkNyc_NoiCapGiayToTuyThan", "Cục CS QLHC về TTXH"),
        _field("TkNyc_NoiCuTru", {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Phường Đoàn Kết",
                                  "diaChi": "Tổ dân phố 5"}),
        _field("Nyc_HoTen", "LÊ THỊ MAI"),
        _field("Nyc_SoDinhDanh", "001190012345"),
        _field("Nyc_NgaySinh", "05/06/1990"),
        _field("Nyc_GioiTinh", "Nữ"),
        _field("Dt_HoTen", "Lê Văn Hùng"),
        _field("Dt_NgaySinh", "10/08/1962"),
        _field("Dt_GioiTinh", "Nam"),
        _field("Dt_DanToc", "Kinh"),
        _field("Dt_QuocTich", "Việt Nam"),
        _field("Dt_SoGiayToTuyThan", "031046789"),
        _field("Dt_NgayCapGiayToTuyThan", "12/03/2020"),
        _field("Dt_NoiCapGiayToTuyThan", "Công an tỉnh Lai Châu"),
        _field("ChuThe_NoiCuTru", {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Phường Đoàn Kết",
                                   "diaChi": "Tổ dân phố 5"}),
        _field("ToKhai_NoiDung", "Ông Lê Văn Hùng có mẹ đẻ là Trần Thị Nụ, bố đẻ là Lê Văn Xuân"),
        _field("ToKhai_LyDo", "Làm thủ tục thừa kế"),
        _field("ToKhai_QuanHe", "con đẻ"),
    ]


def test_dang_ky_registry_va_link():
    proc = get_procedure(KEY)
    assert proc and proc["mode"] == "agent" and proc["hasAttachmentStep"] is True
    assert proc["detect"]["urlIncludes"] == ["maThuTuc=2.002516"]
    assert get_pipeline(KEY) is agent.run
    assert get_attach_pipeline(KEY) is attach_plan
    link = next(item for item in KE_KHAI_LINKS if item.get("key") == KEY)
    assert link["code"] == "2.002516"


def test_nop_thay_dien_phan_1_nguoi_yeu_cau_phan_2_nguoi_duoc_xac_nhan():
    out, warnings = mapper.enrich(_ho_so_nop_thay(), {})
    d = _values(out)

    assert d["data[fullname]"] == "Lê Thị Mai"
    assert d["data[birthday]"] == "05/06/1990"
    assert d["data[gender]"] == "Nữ"
    assert d["data[identityNumber]"] == "001190012345"
    assert d["data[identityDate]"] == "15/03/2021"
    assert d["data[idIssuePlace]"]
    assert d["data[province]"] == "Tỉnh Lai Châu"
    assert d["data[district]"]
    assert d["data[address]"] == "Tổ dân phố 5"

    assert d["data[isOwnerDossierCheck]"] is False
    assert d["data[ownerFullname]"] == "Lê Văn Hùng"
    assert d["data[ownerBirthday]"] == "10/08/1962"
    assert d["data[ownerGender]"] == "Nam"
    assert d["data[ownerDanToc]"] == "Kinh"
    assert d["data[ownerNation]"] == "Việt Nam"
    assert d["data[ownerIdentityNumber]"] == "031046789"
    assert d["data[ownerIdentityDate]"] == "12/03/2020"
    assert d["data[ownerIdIssuePlace]"] == "Công an tỉnh Lai Châu"
    assert d["data[ownerProvince]"] == "Tỉnh Lai Châu"
    assert d["data[ownerAddress]"] == "Tổ dân phố 5"

    # SĐT/email không có trong giấy tờ → không bịa.
    assert "data[phoneNumber]" not in d and "data[ownerPhoneNumber]" not in d
    assert not any(name.startswith("ToKhai_") for name in d)
    assert any("điện thoại" in w for w in warnings)


def test_nop_thay_dien_eform_ho_tich_muc_i_muc_ii_va_noi_dung():
    out, _ = mapper.enrich(_ho_so_nop_thay(), {})
    d = _values(out)
    eform = [f["name"] for f in out if f["comp"].startswith("x-")]

    # Radio quan hệ đi TRƯỚC khối nhân thân (đổi option làm cổng dựng lại Mục I/II).
    assert eform[:2] == ["doiTuongYeuCau", "nycQuanHe"]
    assert d["doiTuongYeuCau"] == "Cá nhân" and d["nycQuanHe"] == "Khác"
    names = [f["name"] for f in out]
    assert names.index("nycQuanHeKhac") == names.index("nycQuanHe") + 1
    assert d["nycQuanHeKhac"] == "Con đẻ"

    assert d["HoVaTenC"] == "LÊ THỊ MAI"
    assert d["SoDinhDanhC"] == "001190012345"
    assert d["SoGiayToTuyThanC"] == "001190012345"
    assert d["LoaiGiayToDinhDanhC"] == "Căn cước công dân"  # Cục Cảnh sát cấp → CCCD cũ
    assert d["NgayCapDDC"] == "15/03/2021"
    assert d["nycNoiCuTru"] == "Trong nước"
    # Tên ô thật trên cổng sai chính tả "TruongNuoc"; tên đúng đi kèm làm alias.
    area_field = next(f for f in out if f["name"] == "nycNoiCuTru_TruongNuoc")
    assert area_field["value"]["tinh"] == "Lai Châu"
    assert area_field["aliases"] == ["nycNoiCuTru_TrongNuoc"]

    assert d["hoTenNguoiDuocXN"] == "LÊ VĂN HÙNG"
    assert d["ngaySinhNguoiDuocXN"] == "10/08/1962"
    assert d["duocXNGioiTinh"] == "Nam"
    assert d["danTocNguoiDuocXN"] == "Kinh"
    assert d["quocTichNguoiDuocXN"] == "Việt Nam"
    # CMND 9 số: không phải số định danh cá nhân.
    assert "duocXNDDCN" not in d
    assert d["duocXNLoaiGiayToTuyThan"] == "Chứng minh nhân dân"
    assert d["duocXNSoGiayToTuyThan"] == "031046789"
    assert d["duocXNNgayCapGiayToTuyThan"] == "12/03/2020"
    assert d["duocXNNoiCapGiayToTuyThan"] == "Công an tỉnh Lai Châu"
    assert d["duocXNNoiCuTru_TrongNuoc"]["diaChi"] == "Tổ dân phố 5"

    assert d["noiDungXacNhan"].startswith("Ông Lê Văn Hùng")
    assert d["lyDoXacNhan"] == "Làm thủ tục thừa kế"


def test_tu_xac_nhan_cho_minh_thi_tich_nguoi_nop_la_chu_ho_so():
    fields = [
        _field("TkNyc_HoTen", "Lê Văn Hùng"),
        _field("TkNyc_SoGiayToTuyThan", "031046789"),
        _field("Dt_HoTen", "LÊ VĂN HÙNG"),
        _field("Dt_NgaySinh", "10/08/1962"),
        _field("Dt_GioiTinh", "Nam"),
        _field("Dt_SoGiayToTuyThan", "031046789"),
    ]
    d = _values(mapper.enrich(fields, {})[0])
    assert d["data[isOwnerDossierCheck]"] is True
    assert d["data[fullname]"] == "Lê Văn Hùng"
    assert d["data[birthday]"] == "10/08/1962"
    assert "data[ownerFullname]" not in d
    assert d["nycQuanHe"] == "Bản thân"
    assert d["HoVaTenC"] == d["hoTenNguoiDuocXN"] == "LÊ VĂN HÙNG"


def test_attach_gks_va_cccd_vao_dong_2_uy_quyen_dong_3_bo_qua_to_khai_ban_giay():
    files = [
        {"name": "cccd.jpg", "type": "image/jpeg"},
        {"name": "gks.pdf", "type": "application/pdf"},
        {"name": "uq.pdf", "type": "application/pdf"},
        {"name": "tokhai.pdf", "type": "application/pdf"},
    ]
    texts = {
        0: "CĂN CƯỚC CÔNG DÂN 001190012345 Lê Thị Mai",
        1: "GIẤY KHAI SINH Họ và tên: Lê Văn Hùng",
        2: "GIẤY ỦY QUYỀN",
        3: "TỜ KHAI ĐỀ NGHỊ XÁC NHẬN THÔNG TIN HỘ TỊCH ... giấy khai sinh, căn cước công dân",
    }
    items, classified, warnings = build_plan_items(files, texts, {})
    by_file = {item["fileIndex"]: item for item in items}

    assert [c["type"] for c in classified] == ["identity", "civil_status", "authorization", "paper_declaration"]
    # Ánh xạ dòng 2: Giấy khai sinh + CCCD/CMND cùng một dòng.
    assert by_file[0]["target"] == "existing" and by_file[0]["componentIndex"] == 2
    assert by_file[1]["target"] == "existing" and by_file[1]["componentIndex"] == 2
    assert by_file[2]["target"] == "existing" and by_file[2]["componentIndex"] == 3
    # Tờ khai bản giấy = dòng 1 (Tờ khai.pdf cổng tự sinh) → không đính lại, không thêm thành phần mới.
    assert 3 not in by_file
    assert classified[3]["target"] == "skip"
    assert all(item.get("componentIndex") != 1 for item in items)
    assert not any(item["needsAddComponent"] for item in items)
    assert not warnings


def test_attach_giay_tuy_than_nguoi_thu_hai_thanh_dong_moi():
    files = [{"name": f"f{i}.jpg", "type": "image/jpeg"} for i in range(3)]
    texts = {
        0: "CĂN CƯỚC CÔNG DÂN 001190012345 Lê Thị Mai",
        1: "CHỨNG MINH NHÂN DÂN 031046789 Lê Văn Hùng",
        2: "GIẤY KHAI SINH Họ và tên: Lê Văn Hùng",
    }
    items, _, _ = build_plan_items(files, texts, {})
    by_file = {item["fileIndex"]: item for item in items}
    assert by_file[0]["componentIndex"] == 2 and by_file[2]["componentIndex"] == 2
    # Dòng có sẵn chỉ nhận giấy tùy thân của MỘT chủ thể (quy tắc dùng chung identity_merge).
    assert by_file[1]["target"] == "new" and by_file[1]["needsAddComponent"] is True
    assert len({item["documentName"] for item in items}) == len(items)


def test_attach_giay_khong_ro_loai_them_thanh_phan_moi():
    files = [{"name": "x.pdf", "type": "application/pdf"}]
    items, _, warnings = build_plan_items(files, {0: "Biên lai thu tiền điện"}, {})
    assert items[0]["target"] == "new" and items[0]["needsAddComponent"] is True
    assert any("Giấy khai sinh" in w for w in warnings)


def test_attach_khong_co_giay_khai_sinh_thi_cccd_vao_dong_2_va_canh_bao():
    files = [{"name": "cccd.jpg", "type": "image/jpeg"}]
    items, _, warnings = build_plan_items(files, {0: "CĂN CƯỚC CÔNG DÂN 001190012345"}, {})
    assert items[0]["target"] == "existing" and items[0]["componentIndex"] == 2
    assert any("Giấy khai sinh" in w for w in warnings)


def test_ten_theo_giay_khai_sinh_khi_chu_viet_tay_lech_dau_va_bo_ngay_cap_cmnd_vo_ly():
    fields = [
        _field("TkNyc_HoTen", "Lê Thị Mai"),
        _field("TkNyc_SoGiayToTuyThan", "001190012345"),
        _field("Dt_HoTen", "Lê văn Hưng"),
        _field("Dt_SoGiayToTuyThan", "031046789"),
        _field("Dt_NgayCapGiayToTuyThan", "19/02/2026"),
        _field("Gks_HoTen", "LÊ VĂN HÙNG"),
        _field("Gks_HoTenMe", "TRẦN THỊ NỤ"),
        _field("Gks_HoTenCha", "LÊ VĂN XUÂN"),
        _field("ToKhai_NoiDung", "Ông Lê văn Hưng có mẹ đẻ là Trần Thị Mụ, bố đẻ là Lê Văn Suân"),
    ]
    out, warnings = mapper.enrich(fields, {})
    d = _values(out)
    assert d["data[ownerFullname]"] == "Lê Văn Hùng"
    assert d["hoTenNguoiDuocXN"] == "LÊ VĂN HÙNG"
    assert d["noiDungXacNhan"] == "Ông Lê Văn Hùng có mẹ đẻ là Trần Thị Nụ, bố đẻ là Lê Văn Xuân"
    assert "data[ownerIdentityDate]" not in d and "duocXNNgayCapGiayToTuyThan" not in d
    assert any("2021" in w for w in warnings)
    assert any("đã sửa 'Trần Thị Mụ'" in w for w in warnings)
    # Không có CCCD người yêu cầu → nhắc ngày sinh/giới tính.
    assert any("ngày sinh, giới tính" in w for w in warnings)


def test_ten_khac_han_giay_khai_sinh_thi_giu_to_khai():
    fields = [_field("Dt_HoTen", "Trần Văn Bình"), _field("Gks_HoTen", "LÊ VĂN HÙNG")]
    d = _values(mapper.enrich(fields, {})[0])
    assert d["data[ownerFullname]"] == "Trần Văn Bình"


def test_khong_sua_ten_nguoi_khac_lech_nhieu_ky_tu():
    assert mapper._fix_names_in_text("bố đẻ là Lê Minh Sơn", ["LÊ VĂN XUÂN"]) == "bố đẻ là Lê Minh Sơn"
