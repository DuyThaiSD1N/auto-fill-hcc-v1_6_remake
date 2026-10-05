"""Đăng ký hoạt động khuyến mại mang tính may rủi trên địa bàn 01 tỉnh (Bộ Công Thương, 2.000004)."""

import re
from pathlib import Path

from app.pipelines.dang_ky_khuyen_mai_may_rui.attach import planner
from app.pipelines.dang_ky_khuyen_mai_may_rui.process import mapper
from app.pipelines.dang_ky_khuyen_mai_may_rui.process.schema import UI_COMP_BY_NAME
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

KEY = "dang-ky-khuyen-mai-may-rui-mot-tinh"
_ACCOUNT = {"formContext": {"applicantFullname": "Nguyễn Văn A", "applicantIdentityNumber": "001099000001"}}


def _don():
    return {
        "ThuongNhan_Ten": "Hộ kinh doanh Trần Thị B",
        "ThuongNhan_MaSoThue": "0100000001",
        "ThuongNhan_DiaChi": {
            "tinh": "Tỉnh Lào Cai", "xa": "Xã Thác Bà", "diaChi": "Thôn Mẫu",
            "fullText": "Thôn Mẫu, Xã Thác Bà, Tỉnh Lào Cai",
        },
        "ThuongNhan_DienThoai": "84900000001",
        "ThuongNhan_NguoiLienHe": "Nguyễn Văn A",
        "ThuongNhan_DienThoaiLienHe": "0900.000.002",
        "ThuongNhan_DaiDien": "TRẦN THỊ B",
        "Don_So": "01/KM",
        "Don_NgayLap": "09/12/2025",
        "Don_DiaDanh": "Lào Cai",
        "Don_KinhGui": "Sở Công Thương tỉnh Lào Cai",
        "CTKM_Ten": "Mua hàng trúng quà",
        "CTKM_TuNgay": "15/12/2025",
        "CTKM_DenNgay": "16/02/2026",
        "CTKM_HangHoaKhuyenMai": "Tủ lạnh, máy giặt",
        "CTKM_HangHoaDungKhuyenMai": "Xe máy điện: 2 chiếc",
        "CTKM_DiaBan": "tỉnh Lào Cai",
        "CTKM_HinhThuc": "Bốc thăm trúng thưởng",
        "CTKM_KhachHang": "Tất cả khách hàng",
        "CTKM_TongGiaTri": "72.000.000 VNĐ",
    }


def _cccd(**over):
    return {
        "NguoiNop_HoTen": "NGUYỄN VĂN A",
        "NguoiNop_SoDinhDanh": "001099000001",
        "NguoiNop_NgaySinh": "01/02/1990",
        "NguoiNop_NgayCap": "03/04/2022",
        "NguoiNop_NoiCuTru": {"tinh": "Tỉnh Hưng Yên", "xa": "Xã Đông Quan", "diaChi": "Thôn 1"},
        **over,
    }


def _run(values, options=None):
    fields, warnings = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)
    by_key = {(f["name"], f.get("occurrence")): f for f in fields}
    return by_key, warnings


def _snapshot(name_part: str) -> str:
    root = Path(__file__).resolve().parents[3] / "thongtin"
    folder = next(p for p in root.iterdir() if p.name.startswith("196"))
    page = next(p for p in folder.iterdir() if p.suffix == ".html" and name_part in p.name)
    return page.read_text(encoding="utf-8", errors="ignore")


def test_registry_detect_theo_ma_ten_va_host():
    proc = get_procedure(KEY)
    assert proc["detect"]["urlScope"] == ["dichvucong-tthc.moit.gov.vn"]
    assert proc["detect"]["textIncludes"][0] == "2.000004"
    assert proc["hasAttachmentStep"] is True
    assert get_pipeline(KEY) is not None and get_attach_pipeline(KEY) is not None


def test_ui_key_co_that_tren_snapshot():
    html = _snapshot("fill")
    for name in UI_COMP_BY_NAME:
        assert f'name="{name}"' in html, name
    for key in ("fullname", "phoneNumber", "province", "district", "address", "taxCode", "email"):
        assert len(re.findall(rf'name="data\[{key}\]"', html)) == 2, key


def test_key_trung_gan_occurrence_khi_cccd_khop_tai_khoan():
    fields, _ = _run({**_don(), **_cccd()}, _ACCOUNT)
    assert fields[("data[fullname]", 0)]["value"] == "NGUYỄN VĂN A"
    assert fields[("data[fullname]", 1)]["value"] == "Hộ kinh doanh Trần Thị B"
    assert fields[("data[province]", 0)]["value"] == "Hưng Yên"
    assert fields[("data[province]", 1)]["value"] == "Lào Cai"
    assert fields[("data[district]", 0)]["value"] == "Đông Quan"
    assert fields[("data[district]", 1)]["value"] == "Thác Bà"
    assert fields[("data[address]", 1)]["value"] == "Thôn Mẫu"
    assert fields[("data[taxCode]", 1)]["value"] == "0100000001"
    assert ("data[taxCode]", 0) not in fields
    # Tài khoản trùng người liên hệ trên Đơn → SĐT tài khoản = SĐT người liên hệ.
    assert fields[("data[phoneNumber]", 0)]["value"] == "0900000002"
    assert fields[("data[phoneNumber]", 1)]["value"] == "0900000001", "84… đổi về 0…"


def test_cccd_lech_mot_trong_hai_moc_thi_khong_dien_khoi_tai_khoan():
    for override in ({"NguoiNop_SoDinhDanh": "001099000009"}, {"NguoiNop_HoTen": "LÊ VĂN C"}):
        fields, warnings = _run({**_don(), **_cccd(**override)}, _ACCOUNT)
        assert ("data[fullname]", 0) not in fields and ("data[identityNumber]", None) not in fields
        assert any("không khớp tài khoản" in w for w in warnings)
        assert fields[("data[fullname]", 1)]["value"] == "Hộ kinh doanh Trần Thị B"


def test_khong_co_moc_tai_khoan_thi_khong_dien_khoi_tai_khoan():
    fields, warnings = _run({**_don(), **_cccd()})
    assert not any(occ == 0 for (_, occ) in fields)
    assert ("data[identityNumber]", None) not in fields
    assert any("Chưa đọc được tài khoản" in w for w in warnings)


def test_tai_khoan_la_chu_ho_co_so_can_cuoc_tren_don():
    values = {**_don(), "ThuongNhan_NguoiLienHe": "Người Khác", "ThuongNhan_SoCanCuoc": "001099000001"}
    fields, _ = _run(values, _ACCOUNT)
    assert fields[("data[phoneNumber]", 0)]["value"] == "0900000001"
    assert fields[("data[ownerIdentityNumber]", None)]["value"] == "001099000001"


def test_chu_ho_so_la_thuong_nhan_va_xoa_cccd_cong_do_san():
    fields, _ = _run(_don(), _ACCOUNT)
    assert fields[("data[isOwnerDossier]", None)]["value"] is False
    assert fields[("data[ownerFullname]", None)]["value"] == "Hộ kinh doanh Trần Thị B"
    assert fields[("data[ownerIdentityNumber]", None)]["value"] == ""
    assert fields[("data[ownertaxCode]", None)]["value"] == "0100000001"
    assert fields[("data[ownerAddress]", None)]["value"] == "Thôn Mẫu, Xã Thác Bà, Tỉnh Lào Cai"


def test_to_khai_dau_don_chuong_trinh_va_noi_dung_yeu_cau():
    fields, warnings = _run(_don())
    assert fields[("data[soDon]", None)]["value"] == "01/KM"
    assert fields[("data[tinhThanhPhoNopDon]", None)]["value"] == "Lào Cai"
    assert fields[("data[ngayNopDon]", None)]["value"] == "09/12/2025"
    assert fields[("data[fullname1]", None)]["value"] == "Nguyễn Văn A"
    assert fields[("data[daiDienPhapLuat]", None)]["value"] == "TRẦN THỊ B"
    assert fields[("data[ngayvb1]", None)]["value"] == "15/12/2025"
    assert any("16/02/2026" in w for w in warnings), "ô thời gian chỉ 1 ngày → cảnh báo ngày kết thúc"
    request = fields[("data[noidungyeucaugiaiquyet]", None)]
    assert request["value"] == (
        "Văn bản số 01/KM ngày 09/12/2025 của Hộ kinh doanh Trần Thị B về việc đăng ký thực hiện khuyến mại "
        "chương trình \"Mua hàng trúng quà\""
    )
    assert "default" not in request
    assert ("data[slhh]", None) not in fields, "Đơn để trống số lượng → không điền"


def test_planner_3_dong_giay_to_ngoai_danh_muc_vao_dong_dang_ky():
    files = [{"name": n} for n in ("dk.pdf", "tl.pdf", "phieu.jpg", "cq.pdf", "anh.pdf", "cccd.jpg")]
    llm = {0: "dang_ky", 1: "the_le", 2: "bang_chung", 3: "chat_luong", 4: "other", 5: "cccd"}
    items, warnings, _ = planner.build_plan_items(files, llm)
    assert [i["fileIndex"] for i in items] == list(range(6))
    assert all(i["target"] == "attp-row" for i in items)
    names = {i["fileName"]: i["documentName"] for i in items}
    assert names["cq.pdf"] == planner._LABELS["chat_luong"] and names["cccd.jpg"] == "Căn cước công dân"
    assert names["anh.pdf"] == "anh.pdf", "giấy chưa biết loại giữ tên gốc"
    comp = {i["fileName"]: i["componentName"] for i in items}
    dang_ky = planner._ROWS["dang_ky"]["componentName"]
    assert comp["dk.pdf"] == comp["cq.pdf"] == comp["anh.pdf"] == comp["cccd.jpg"] == dang_ky
    assert comp["tl.pdf"] == planner._ROWS["the_le"]["componentName"]
    assert comp["phieu.jpg"] == planner._ROWS["bang_chung"]["componentName"]
    assert warnings == []


def test_planner_llm_chet_moi_tep_ve_dong_dang_ky():
    items, _, _ = planner.build_plan_items([{"name": "a.pdf"}, {"name": "b.pdf"}], {})
    assert {i["componentName"] for i in items} == {planner._ROWS["dang_ky"]["componentName"]}


def test_component_name_khop_dung_mot_dong_tren_snapshot():
    # Tên tệp trên macOS ở dạng NFD → chọn trang đính kèm theo nội dung (có radio rdo_File), không theo tên.
    root = Path(__file__).resolve().parents[3] / "thongtin"
    folder = next(p for p in root.iterdir() if p.name.startswith("196"))
    pages = [p.read_text(encoding="utf-8", errors="ignore") for p in folder.iterdir() if p.suffix == ".html"]
    html = next(h for h in pages if "rdo_File" in h)
    text = mapper._fold(re.sub(r"<[^>]+>", " ", html))
    for row in planner._ROWS.values():
        assert text.count(mapper._fold(row["componentName"])) == 1, row["componentName"]
