"""Tests cho thủ tục "Xác nhận thông tin hộ tịch" (mã 2.002516).

Hồ sơ mẫu: bà Nguyễn Thị Ngọc Lan (con đẻ) nộp thay, xác nhận thông tin hộ tịch cho bố là ông Nguyễn Bật Vấn.
Phần 1 người nộp = Lan (tờ khai + CCCD), Phần 2 chủ hồ sơ = Vấn (tờ khai / giấy khai sinh + CMND).
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
        _field("TkNyc_HoTen", "Nguyễn Thị Ngọc Lan"),
        _field("TkNyc_SoGiayToTuyThan", "012190009891"),
        _field("TkNyc_NgayCapGiayToTuyThan", "22/4/2021"),
        _field("TkNyc_NoiCapGiayToTuyThan", "Cục CS QLHC về TTXH"),
        _field("TkNyc_NoiCuTru", {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Phường Đoàn Kết",
                                  "diaChi": "Tổ dân phố Quyết Tiến 7"}),
        _field("Nyc_HoTen", "NGUYỄN THỊ NGỌC LAN"),
        _field("Nyc_SoDinhDanh", "012190009891"),
        _field("Nyc_NgaySinh", "05/06/1990"),
        _field("Nyc_GioiTinh", "Nữ"),
        _field("Dt_HoTen", "Nguyễn Bật Vấn"),
        _field("Dt_NgaySinh", "22/02/1965"),
        _field("Dt_GioiTinh", "Nam"),
        _field("Dt_DanToc", "Kinh"),
        _field("Dt_QuocTich", "Việt Nam"),
        _field("Dt_SoGiayToTuyThan", "045046381"),
        _field("Dt_NgayCapGiayToTuyThan", "12/03/2020"),
        _field("Dt_NoiCapGiayToTuyThan", "Công an tỉnh Lai Châu"),
        _field("ChuThe_NoiCuTru", {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Phường Đoàn Kết",
                                   "diaChi": "Tổ dân phố Quyết Tiến 7"}),
        _field("ToKhai_NoiDung", "Ông Nguyễn Bật Vấn có mẹ đẻ là Nguyễn Thị Nỳ, bố đẻ là Nguyễn Bật Xưa"),
        _field("ToKhai_QuanHe", "con đẻ"),
    ]


def test_dang_ky_registry_va_link():
    proc = get_procedure(KEY)
    assert proc and proc["mode"] == "agent" and proc["hasAttachmentStep"] is True
    assert get_pipeline(KEY) is agent.run
    assert get_attach_pipeline(KEY) is attach_plan
    link = next(item for item in KE_KHAI_LINKS if item.get("key") == KEY)
    assert link["code"] == "2.002516"


def test_nop_thay_dien_phan_1_nguoi_yeu_cau_phan_2_nguoi_duoc_xac_nhan():
    out, warnings = mapper.enrich(_ho_so_nop_thay(), {})
    d = _values(out)

    assert d["data[fullname]"] == "Nguyễn Thị Ngọc Lan"
    assert d["data[birthday]"] == "05/06/1990"
    assert d["data[gender]"] == "Nữ"
    assert d["data[identityNumber]"] == "012190009891"
    assert d["data[identityDate]"] == "22/04/2021"
    assert d["data[idIssuePlace]"]
    assert d["data[province]"] == "Tỉnh Lai Châu"
    assert d["data[district]"]
    assert d["data[address]"] == "Tổ dân phố Quyết Tiến 7"

    assert d["data[isOwnerDossierCheck]"] is False
    assert d["data[ownerFullname]"] == "Nguyễn Bật Vấn"
    assert d["data[ownerBirthday]"] == "22/02/1965"
    assert d["data[ownerGender]"] == "Nam"
    assert d["data[ownerDanToc]"] == "Kinh"
    assert d["data[ownerNation]"] == "Việt Nam"
    assert d["data[ownerIdentityNumber]"] == "045046381"
    assert d["data[ownerIdentityDate]"] == "12/03/2020"
    assert d["data[ownerIdIssuePlace]"] == "Công an tỉnh Lai Châu"
    assert d["data[ownerProvince]"] == "Tỉnh Lai Châu"
    assert d["data[ownerAddress]"] == "Tổ dân phố Quyết Tiến 7"

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

    assert d["HoVaTenC"] == "NGUYỄN THỊ NGỌC LAN"
    assert d["SoDinhDanhC"] == "012190009891"
    assert d["SoGiayToTuyThanC"] == "012190009891"
    assert d["LoaiGiayToDinhDanhC"] == "Thẻ căn cước công dân"
    assert d["NgayCapDDC"] == "22/04/2021"
    assert d["nycNoiCuTru"] == "Trong nước"
    # Tên ô thật trên cổng sai chính tả "TruongNuoc"; tên đúng đi kèm làm alias.
    area_field = next(f for f in out if f["name"] == "nycNoiCuTru_TruongNuoc")
    assert area_field["value"]["tinh"] == "Lai Châu"
    assert area_field["aliases"] == ["nycNoiCuTru_TrongNuoc"]

    assert d["hoTenNguoiDuocXN"] == "NGUYỄN BẬT VẤN"
    assert d["ngaySinhNguoiDuocXN"] == "22/02/1965"
    assert d["duocXNGioiTinh"] == "Nam"
    assert d["danTocNguoiDuocXN"] == "Kinh"
    assert d["quocTichNguoiDuocXN"] == "Việt Nam"
    # CMND 9 số: không phải số định danh cá nhân.
    assert "duocXNDDCN" not in d
    assert d["duocXNLoaiGiayToTuyThan"] == "Chứng minh nhân dân"
    assert d["duocXNSoGiayToTuyThan"] == "045046381"
    assert d["duocXNNgayCapGiayToTuyThan"] == "12/03/2020"
    assert d["duocXNNoiCapGiayToTuyThan"] == "Công an tỉnh Lai Châu"
    assert d["duocXNNoiCuTru_TrongNuoc"]["diaChi"] == "Tổ dân phố Quyết Tiến 7"

    assert d["noiDungXacNhan"].startswith("Ông Nguyễn Bật Vấn")


def test_tu_xac_nhan_cho_minh_thi_tich_nguoi_nop_la_chu_ho_so():
    fields = [
        _field("TkNyc_HoTen", "Nguyễn Bật Vấn"),
        _field("TkNyc_SoGiayToTuyThan", "045046381"),
        _field("Dt_HoTen", "NGUYỄN BẬT VẤN"),
        _field("Dt_NgaySinh", "22/02/1965"),
        _field("Dt_GioiTinh", "Nam"),
        _field("Dt_SoGiayToTuyThan", "045046381"),
    ]
    d = _values(mapper.enrich(fields, {})[0])
    assert d["data[isOwnerDossierCheck]"] is True
    assert d["data[fullname]"] == "Nguyễn Bật Vấn"
    assert d["data[birthday]"] == "22/02/1965"
    assert "data[ownerFullname]" not in d
    assert d["nycQuanHe"] == "Bản thân"
    assert d["HoVaTenC"] == d["hoTenNguoiDuocXN"] == "NGUYỄN BẬT VẤN"


def test_attach_giay_khai_sinh_vao_dong_2_cccd_them_moi_uy_quyen_dong_3():
    files = [
        {"name": "cccd.jpg", "type": "image/jpeg"},
        {"name": "gks.pdf", "type": "application/pdf"},
        {"name": "uq.pdf", "type": "application/pdf"},
        {"name": "tokhai.pdf", "type": "application/pdf"},
    ]
    texts = {
        0: "CĂN CƯỚC CÔNG DÂN 012190009891 Nguyễn Thị Ngọc Lan",
        1: "GIẤY KHAI SINH Họ và tên: Nguyễn Bật Vấn",
        2: "GIẤY ỦY QUYỀN",
        3: "TỜ KHAI ĐỀ NGHỊ XÁC NHẬN THÔNG TIN HỘ TỊCH ... giấy khai sinh, căn cước công dân",
    }
    items, classified, warnings = build_plan_items(files, texts, {})
    by_file = {item["fileIndex"]: item for item in items}

    assert [c["type"] for c in classified] == ["identity", "civil_status", "authorization", "paper_declaration"]
    assert by_file[1]["target"] == "existing" and by_file[1]["componentIndex"] == 2
    assert by_file[2]["target"] == "existing" and by_file[2]["componentIndex"] == 3
    assert by_file[0]["target"] == "new" and by_file[0]["needsAddComponent"] is True
    assert by_file[3]["target"] == "new"
    # Không đính gì vào dòng 1 (tờ khai điện tử cổng tự sinh).
    assert all(item.get("componentIndex") != 1 for item in items)
    assert not warnings


def test_attach_khong_co_giay_khai_sinh_thi_cccd_vao_dong_2_va_canh_bao():
    files = [{"name": "cccd.jpg", "type": "image/jpeg"}]
    items, _, warnings = build_plan_items(files, {0: "CĂN CƯỚC CÔNG DÂN 012190009891"}, {})
    assert items[0]["target"] == "existing" and items[0]["componentIndex"] == 2
    assert any("Giấy khai sinh" in w for w in warnings)


def test_ten_theo_giay_khai_sinh_khi_chu_viet_tay_lech_dau_va_bo_ngay_cap_cmnd_vo_ly():
    fields = [
        _field("TkNyc_HoTen", "Nguyễn Thị Ngọc Lan"),
        _field("TkNyc_SoGiayToTuyThan", "012190000989"),
        _field("Dt_HoTen", "Nguyễn Bất Văn"),
        _field("Dt_SoGiayToTuyThan", "045046380"),
        _field("Dt_NgayCapGiayToTuyThan", "19/02/2026"),
        _field("Gks_HoTen", "NGUYỄN BẬT VẤN"),
        _field("Gks_HoTenMe", "NGUYỄN THỊ NỶ"),
        _field("Gks_HoTenCha", "NGUYỄN BẬT XƯA"),
        _field("ToKhai_NoiDung", "Ông Nguyễn bất Vân có mẹ đẻ là Nguyễn Thị Mỹ, bố đẻ là Nguyễn Bật Sủa"),
    ]
    out, warnings = mapper.enrich(fields, {})
    d = _values(out)
    assert d["data[ownerFullname]"] == "Nguyễn Bật Vấn"
    assert d["hoTenNguoiDuocXN"] == "NGUYỄN BẬT VẤN"
    assert d["noiDungXacNhan"] == "Ông Nguyễn Bật Vấn có mẹ đẻ là Nguyễn Thị Nỷ, bố đẻ là Nguyễn Bật Xưa"
    assert "data[ownerIdentityDate]" not in d and "duocXNNgayCapGiayToTuyThan" not in d
    assert any("2021" in w for w in warnings)
    assert any("đã sửa 'Nguyễn Thị Mỹ'" in w for w in warnings)
    # Không có CCCD người yêu cầu → nhắc ngày sinh/giới tính.
    assert any("ngày sinh, giới tính" in w for w in warnings)


def test_ten_khac_han_giay_khai_sinh_thi_giu_to_khai():
    fields = [_field("Dt_HoTen", "Trần Văn Bình"), _field("Gks_HoTen", "NGUYỄN BẬT VẤN")]
    d = _values(mapper.enrich(fields, {})[0])
    assert d["data[ownerFullname]"] == "Trần Văn Bình"


def test_khong_sua_ten_nguoi_khac_lech_nhieu_ky_tu():
    assert mapper._fix_names_in_text("bố đẻ là Nguyễn Văn Sơn", ["NGUYỄN BẬT XƯA"]) == "bố đẻ là Nguyễn Văn Sơn"
