from app.attachments.schemas import AttachmentPlanItem
from app.pipelines.xac_nhan_dieu_kien_dien_tich_nha_o_dang_ky_thuong_tru.attach import planner
from app.pipelines.xac_nhan_dieu_kien_dien_tich_nha_o_dang_ky_thuong_tru.process import mapper
from app.pipelines.xac_nhan_dieu_kien_dien_tich_nha_o_dang_ky_thuong_tru.process.schema import (
    FIELDS,
    TEN_THU_TUC,
    UI_COMP_BY_NAME,
)
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

_KEY = "xac-nhan-dieu-kien-dien-tich-nha-o-dang-ky-thuong-tru"
_TO_KHAI_NAME = "Tờ khai xác nhận tình trạng chỗ ở hợp pháp"


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


def _fields(**values) -> list[dict]:
    return [{"name": name, "value": value} for name, value in values.items()]


# --------------------------------------------------------------------------------------
# REGISTRY / KÊ KHAI
# --------------------------------------------------------------------------------------
def test_registry_and_ke_khai_link_share_key():
    procedure = get_procedure(_KEY)
    assert procedure and procedure["hasAttachmentStep"] is True
    assert get_pipeline(_KEY) is not None
    assert get_attach_pipeline(_KEY) is not None

    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    assert link["code"] == "1.013314"
    # Chọn phường/xã như bình thường: không phải thủ tục cấp tỉnh/Sở.
    assert not link.get("selectSo") and not link.get("provinceOnlyAgency")

    detect = with_ke_khai_detect_urls([procedure])[0]["detect"]
    assert link["url"] in detect["urlIncludes"]
    assert "matthc=1.013314" in detect["urlIncludes"]


def test_schema_does_not_emit_admin_fields():
    assert "data[ProcedureDossierQuantity]" not in UI_COMP_BY_NAME
    assert "data[hinhThucNop]" not in UI_COMP_BY_NAME
    assert "data[district2]" not in UI_COMP_BY_NAME
    assert len({field["name"] for field in FIELDS}) == len(FIELDS)


# --------------------------------------------------------------------------------------
# ĐIỀN FORM
# --------------------------------------------------------------------------------------
def test_owner_panel_and_residence_address_from_to_khai():
    fields, warnings = mapper.enrich(_fields(
        ChuHoSo_HoTen="LÊ VĂN AN",
        ChuHoSo_NgaySinh="5/3/1980",
        ChuHoSo_GioiTinh="Nam",
        ChuHoSo_SoDinhDanh="001 080 012 345",
        ChuHoSo_NgayCap="12/8/2024",
        ChuHoSo_NoiCap="Bộ Công an",
        ChuHoSo_NoiCuTru={"tinh": "Quảng Ngãi", "xa": "Phường Cẩm Thành", "diaChi": "12 Đường Số 3, Tổ dân phố 4"},
        NguoiNop_HoTen="LÊ VĂN AN",
        ChoO_DiaChi={"tinh": "Quảng Ngãi", "xa": "Phường Cẩm Thành", "diaChi": "12 Đường Số 3, Tổ dân phố 4"},
        ThuaDat_So="27",
        ThuaDat_ToBanDo="Tờ bản đồ số 11",
        ToKhai_TinhTrangChoO="Sử dụng ổn định, không tranh chấp",
        ToKhai_SoNguoiThueMuon="3 người",
    ))
    values = _values(fields)

    assert warnings == []
    assert values["data[ownerFullname]"] == "LÊ VĂN AN"
    assert values["data[fullname]"] == "LÊ VĂN AN"
    assert values["data[birthday]"] == "05/03/1980"
    assert values["data[identityNumber]"] == "001080012345"
    assert values["data[identityDate]"] == "12/08/2024"
    assert values["data[province]"] == "Tỉnh Quảng Ngãi"
    assert values["data[district]"] == "Phường Cẩm Thành"
    assert values["data[address]"] == "12 Đường Số 3, Tổ dân phố 4"
    assert values["data[chonDoiTuong]"] == "Cá nhân"
    # Không ủy quyền -> không điền "Số điện thoại ủy quyền".
    assert "data[phoneNumber1]" not in values
    assert values["data[diaChiThuaDat]"] == (
        "12 Đường Số 3, Tổ dân phố 4, Phường Cẩm Thành, Tỉnh Quảng Ngãi (Thửa đất số 27, Tờ bản đồ số 11)"
    )
    assert values["data[province2]"] == "Tỉnh Quảng Ngãi"
    assert values["data[village2]"] == "Phường Cẩm Thành"
    assert values["data[nation2]"] == "Việt Nam"
    assert values["data[noidungyeucaugiaiquyet]"] == (
        f"{TEN_THU_TUC}. Tình trạng chỗ ở để đăng ký thường trú, tạm trú: Sử dụng ổn định, không tranh chấp; "
        "Tổng số người thuê, mượn, ở nhờ: 3 người"
    )
    # Mọi ô phát ra đều có trên form.
    assert all(item["name"] in UI_COMP_BY_NAME for item in fields)


def test_old_cmnd_number_is_not_used_as_identity_number():
    fields, _ = mapper.enrich(_fields(ChuHoSo_HoTen="TRẦN THỊ BÌNH", ChuHoSo_SoDinhDanh="230123456"))
    values = _values(fields)
    assert "data[identityNumber]" not in values
    # Không có mục III -> nội dung yêu cầu giữ đúng tên thủ tục.
    assert values["data[noidungyeucaugiaiquyet]"] == TEN_THU_TUC


def test_authorized_applicant_only_fills_applicant_slots():
    fields, _ = mapper.enrich(_fields(
        ChuHoSo_HoTen="LÊ VĂN AN",
        ChuHoSo_SoDinhDanh="001080012345",
        NguoiNop_HoTen="PHẠM VĂN CƯỜNG",
        NguoiNop_SoDinhDanh="001090054321",
        NguoiNop_DienThoai="0912 345 678",
    ))
    values = _values(fields)
    assert values["data[ownerFullname]"] == "LÊ VĂN AN"
    assert values["data[fullname]"] == "PHẠM VĂN CƯỜNG"
    assert values["data[identityNumber]"] == "001080012345"
    assert values["data[phoneNumber1]"] == "0912345678"


def test_old_admin_units_on_gcn_are_remapped_and_ward_only_infers_province():
    """GCN cấp trước sắp xếp ghi 'tỉnh Kon Tum / phường Nguyễn Trãi' -> quy đổi sang đơn vị hiện hành; Tờ khai chỉ
    có 'Kính gửi: UBND Phường Đăk Bla' (không ghi tỉnh) -> suy tỉnh từ danh mục xã."""
    fields, _ = mapper.enrich(_fields(
        ChuHoSo_HoTen="LÊ VĂN AN",
        ChuHoSo_NoiCuTru={"tinh": "tỉnh Kon Tum", "xa": "phường Nguyễn Trãi", "diaChi": "Tổ 9"},
        ChoO_DiaChi={"xa": "Phường Đăk Bla", "diaChi": "45 Đường Số 7"},
    ))
    values = _values(fields)
    assert values["data[province]"] == "Tỉnh Quảng Ngãi"
    assert values["data[district]"] == "Phường Đăk Bla"
    assert values["data[province2]"] == "Tỉnh Quảng Ngãi"
    assert values["data[village2]"] == "Phường Đăk Bla"
    assert values["data[diaChiThuaDat]"] == "45 Đường Số 7, Phường Đăk Bla, Tỉnh Quảng Ngãi"


def test_residence_block_not_borrowed_from_owner_address():
    fields, _ = mapper.enrich(_fields(
        ChuHoSo_HoTen="LÊ VĂN AN",
        ChuHoSo_NoiCuTru={"tinh": "Quảng Ngãi", "xa": "Phường Cẩm Thành", "diaChi": "12 Đường Số 3"},
    ))
    values = _values(fields)
    assert not {"data[diaChiThuaDat]", "data[province2]", "data[village2]"} & set(values)


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM
# --------------------------------------------------------------------------------------
def _seg(file_index: int, page_from: int, page_to: int, doc_type: str) -> dict:
    return {"fileIndex": file_index, "pageFrom": page_from, "pageTo": page_to, "type": doc_type, "documentName": ""}


def test_merged_pdf_all_pages_go_to_to_khai_row_gcn_cover_first():
    """PDF gộp 3 trang: trang 1 Tờ khai + trang 2 (I-V) + trang 3 (bìa + VI) -> chung dòng 1 (mục I), không tạo
    dòng qua modal; trong GCN trang bìa đứng trước."""
    raw_files = [{"name": "ho-so.pdf", "type": "application/pdf"}]
    file_meta = {0: {"pageCount": 3, "pageBoundariesAvailable": True}}
    pages_by_file = {0: {
        1: "TỜ KHAI Xác nhận tình trạng chỗ ở hợp pháp ... II. THÔNG TIN VỀ CHỖ Ở HỢP PHÁP",
        2: "CHỨNG NHẬN I- Tên người sử dụng đất ... II- Thửa đất được quyền sử dụng",
        3: "VI- Những thay đổi sau khi cấp giấy chứng nhận ... CẦN CHÚ Ý ... GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT",
    }}
    segments = [_seg(0, 1, 1, "to_khai"), _seg(0, 2, 3, "giay_chung_nhan")]

    attachments, classified, warnings = planner.build_plan_items(raw_files, segments, file_meta, pages_by_file)

    assert warnings == []
    assert len(attachments) == 1
    item = attachments[0]
    assert item["target"] == "attp-row"
    assert item["needsAddComponent"] is False
    assert item["componentName"] == _TO_KHAI_NAME
    assert item["componentIndex"] == 0
    assert item["loaiBan"] == "Bản chính"
    assert item["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0]}, {"fileIndex": 0, "pageIndexes": [2, 1]}]
    assert all(c["componentIndex"] == 0 for c in classified)
    AttachmentPlanItem(**item)


def test_every_file_including_cccd_and_unknown_goes_to_to_khai_row():
    raw_files = [{"name": "cccd.jpg", "type": "image/jpeg"}, {"name": "la.pdf", "type": "application/pdf"},
                 {"name": "uy-quyen.pdf", "type": "application/pdf"}, {"name": "to-khai.pdf", "type": "application/pdf"}]
    file_meta = {i: {"pageCount": 1, "pageBoundariesAvailable": True} for i in range(4)}
    pages_by_file = {0: {1: "CĂN CƯỚC CÔNG DÂN"}, 1: {1: "trang trắng"}, 2: {1: "GIẤY ỦY QUYỀN"}, 3: {1: "TỜ KHAI"}}
    segments = [_seg(0, 1, 1, "cccd"), _seg(1, 1, 1, "other"), _seg(2, 1, 1, "authorization"),
                _seg(3, 1, 1, "to_khai")]

    attachments, classified, warnings = planner.build_plan_items(raw_files, segments, file_meta, pages_by_file)

    assert len(attachments) == 1
    assert attachments[0]["fileIndex"] == 3
    assert attachments[0]["sourceSegments"] == [
        {"fileIndex": 3, "pageIndexes": None},
        {"fileIndex": 2, "pageIndexes": None},
        {"fileIndex": 0, "pageIndexes": None},
        {"fileIndex": 1, "pageIndexes": None},
    ]
    assert all(c.get("target") != "skip" for c in classified)
    assert any("Giấy chứng nhận" in warning for warning in warnings)
    assert any("la.pdf" in warning for warning in warnings)


def test_llm_type_aliases_normalize():
    assert planner._normalize_type("GCN QSDĐ") == "giay_chung_nhan"
    assert planner._normalize_type("Tờ khai mẫu 02") == "to_khai"
    assert planner._normalize_type("hợp đồng thuê nhà") == "giay_to_cho_o"
    assert planner._normalize_type("giấy ủy quyền") == "authorization"
    assert planner._normalize_type("căn cước") == "cccd"
