"""Pipeline "Thực hiện trợ cấp xã hội và nhận chăm sóc, nuôi dưỡng, hỗ trợ kinh phí nhận chăm sóc, nuôi
dưỡng hằng tháng" (1.116909, NĐ 335/2026/NĐ-CP): người nộp/chủ hồ sơ và đính kèm 2 dòng tờ khai."""

from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.thuc_hien_tro_cap_xa_hoi_nhan_cham_soc_nuoi_duong_hang_thang.attach import planner as ap
from app.pipelines.thuc_hien_tro_cap_xa_hoi_nhan_cham_soc_nuoi_duong_hang_thang.process import mapper
from app.pipelines.thuc_hien_tro_cap_xa_hoi_nhan_cham_soc_nuoi_duong_hang_thang.process import runner as process_runner
from app.pipelines.thuc_hien_tro_cap_xa_hoi_nhan_cham_soc_nuoi_duong_hang_thang.process.prompt import EXTRA_RULES
from app.pipelines.thuc_hien_tro_cap_xa_hoi_nhan_cham_soc_nuoi_duong_hang_thang.process.schema import FIELDS

_KEY = "thuc-hien-tro-cap-xa-hoi-nhan-cham-soc-nuoi-duong-hang-thang"


def _mapped(fields, options=None):
    result, warnings = mapper.enrich(
        [{"name": name, "value": value} for name, value in fields.items()],
        options,
    )
    return {field["name"]: field["value"] for field in result}, warnings


def _child():
    # Trẻ khuyết tật: tờ khai mục I.1 không ghi số điện thoại.
    return {
        "DoiTuong_HoTen": "LÊ MINH ANH",
        "DoiTuong_NgaySinh": "03/02/2019",
        "DoiTuong_GioiTinh": "Nữ",
        "DoiTuong_SoDinhDanh": "001319012345",
        "DoiTuong_NgayCap": "20/07/2026",
        "DoiTuong_NoiCap": "BỘ CÔNG AN",
        "DoiTuong_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Hà Nội", "xa": "Phường Hoàn Kiếm", "diaChi": "Tổ 3"},
    }


def _guardian():
    return {
        **_child(),
        "NguoiNop_HoTen": "LÊ VĂN BÌNH",
        "NguoiNop_NgaySinh": "11/09/1990",
        "NguoiNop_GioiTinh": "Nam",
        "NguoiNop_SoDinhDanh": "001090054321",
        "NguoiNop_NgayCap": "02/03/2022",
        "NguoiNop_NoiCap": "Cục Cảnh sát QLHC về TTXH",
        "NguoiNop_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "", "xa": "Phường Hoàn Kiếm", "diaChi": "Tổ 3"},
        "NguoiNop_DienThoai": "0912 345 678",
        "NguoiNop_QuanHe": "bố đẻ",
    }


_DECLARATION_MODE = {"submitterMode": "owner_as_submitter"}


def test_nguoi_giam_ho_la_nguoi_nop_tre_la_chu_ho_so():
    ui, warnings = _mapped(_guardian(), _DECLARATION_MODE)

    assert not warnings
    assert ui["data[chonDoiTuong]"] == "Cá nhân"
    assert ui["data[fullname]"] == "LÊ VĂN BÌNH"
    assert ui["data[identityNumber]"] == "001090054321"
    assert ui["data[birthday]"] == "11/09/1990"
    assert ui["data[idIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    # Tỉnh của người giám hộ suy từ cùng phường của đối tượng.
    assert ui["data[province]"] == "Thành phố Hà Nội"
    assert ui["data[address]"] == "Tổ 3"
    assert ui["data[phoneNumber]"] == "0912345678"
    assert ui["data[isOwnerDossierCheck]"] is False
    assert ui["data[ownerFullname]"] == "LÊ MINH ANH"
    assert ui["data[ownerIdentityNumber]"] == "001319012345"
    assert ui["data[ownerIdIssuePlace]"] == "Bộ Công an"
    assert ui["data[ownerNation]"] == "Việt Nam"
    assert ui["data[ghiChu]"] == "Người nộp là người giám hộ (Bố đẻ) của chủ hồ sơ"


def test_doi_tuong_khong_co_sdt_thi_dung_sdt_nguoi_giam_ho():
    ui, _ = _mapped(_guardian(), _DECLARATION_MODE)
    assert ui["data[ownerPhoneNumber]"] == "0912345678"


def test_doi_tuong_co_sdt_rieng_thi_giu_sdt_doi_tuong():
    ui, _ = _mapped({**_guardian(), "DoiTuong_DienThoai": "0987654321"}, _DECLARATION_MODE)
    assert ui["data[ownerPhoneNumber]"] == "0987654321"
    assert ui["data[phoneNumber]"] == "0912345678"


def test_tai_khoan_khop_nguoi_giam_ho_lay_ten_va_so_theo_tai_khoan():
    ui, warnings = _mapped(_guardian(), {
        "formContext": {"applicantFullname": "Lê Văn Bình", "applicantIdentityNumber": "001090054321"}
    })

    assert not warnings
    assert ui["data[fullname]"] == "Lê Văn Bình"
    assert ui["data[identityDate]"] == "02/03/2022"
    assert ui["data[ownerFullname]"] == "LÊ MINH ANH"
    assert "data[ghiChu]" in ui


def test_tai_khoan_khong_co_trong_ho_so_chi_dien_ten_va_so():
    ui, warnings = _mapped(_guardian(), {
        "formContext": {"applicantFullname": "Phạm Thu Hà", "applicantIdentityNumber": "001185099999"}
    })

    assert ui["data[fullname]"] == "Phạm Thu Hà"
    assert ui["data[identityNumber]"] == "001185099999"
    for leaked in ("data[birthday]", "data[identityDate]", "data[address]", "data[ghiChu]"):
        assert leaked not in ui
    assert warnings and "001185099999" in warnings[0]


def test_khong_co_nguoi_khai_thay_thi_doi_tuong_tu_nop():
    ui, warnings = _mapped({**_child(), "DoiTuong_DienThoai": "0987654321"}, _DECLARATION_MODE)

    assert not warnings
    assert ui["data[fullname]"] == "LÊ MINH ANH"
    assert ui["data[ownerFullname]"] == "LÊ MINH ANH"
    assert "data[ghiChu]" not in ui


def test_so_dinh_danh_nguoi_khai_sai_do_dai_thi_bo():
    ui, _ = _mapped({**_guardian(), "NguoiNop_SoDinhDanh": "0010900543210"}, _DECLARATION_MODE)
    assert ui["data[fullname]"] == "LÊ VĂN BÌNH"
    assert "data[identityNumber]" not in ui


def test_noi_cap_theo_ngay_cap_khi_to_khai_ghi_chung_bo_cong_an():
    # Tờ khai ghi "Bộ Công An" cho CCCD gắn chip cấp 2022 → Cục Cảnh sát; thẻ cấp sau 01/07/2024 → Bộ Công an.
    ui, _ = _mapped({
        **_guardian(),
        "NguoiNop_NoiCap": "Bộ Công An",
        "DoiTuong_NoiCap": "Cục cảnh sát quản lý hành chính về trật tự xã hội",
    }, _DECLARATION_MODE)
    assert ui["data[idIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert ui["data[ownerIdIssuePlace]"] == "Bộ Công an"


def test_noi_cap_khong_doi_voi_cmnd_9_so_hoac_thieu_ngay_cap():
    ui, _ = _mapped({
        **_guardian(),
        "NguoiNop_SoDinhDanh": "012345678",
        "NguoiNop_NgayCap": "05/05/2015",
        "NguoiNop_NoiCap": "Công an tỉnh Nam Định",
        "DoiTuong_NgayCap": "",
    }, _DECLARATION_MODE)
    assert ui["data[idIssuePlace]"] == "Công an tỉnh Nam Định"
    assert ui["data[ownerIdIssuePlace]"] == "Bộ Công an"


def test_khong_co_email_thi_xoa_o_email():
    result, _ = mapper.enrich([{"name": k, "value": v} for k, v in _guardian().items()], _DECLARATION_MODE)
    email = next(f for f in result if f["name"] == "data[email]")
    assert email["value"] == "" and email["clear"] is True


def test_prompt_noi_ro_nguoi_giam_ho_muc_i2():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)
    assert "Nghị định 335/2026/NĐ-CP" in system_prompt
    assert "Thông tin người giám hộ" in system_prompt
    assert "đúng 9 hoặc 12 chữ số" in system_prompt


async def test_runner_mo_khoa_o_ho_ten_va_cccd_khi_theo_to_khai(monkeypatch):
    async def fake_run(files_by_role, **kwargs):
        return {"fields": [{"name": k, "value": v} for k, v in _guardian().items()], "errors": []}

    monkeypatch.setattr(process_runner.runner, "run", fake_run)
    res = await process_runner.run({}, _DECLARATION_MODE)

    unlocked = {f["name"] for f in res["fields"] if f.get("enableInput")}
    assert unlocked == {"data[fullname]", "data[identityNumber]"}


# ── Đính kèm: bảng 2 dòng (Mẫu 01, Mẫu 02); giấy tờ không có dòng riêng đính chung dòng tờ khai chính. ──

_TK01_TEXT = (
    "TỜ KHAI ĐỀ NGHỊ TRỢ CẤP XÃ HỘI, TRỢ CẤP HƯU TRÍ XÃ HỘI Thông tin người giám hộ "
    "Giấy xác nhận khuyết tật số 0123 Ngày cấp"
)
_TK02_TEXT = "TỜ KHAI NHẬN CHĂM SÓC, NUÔI DƯỠNG, ĐỀ NGHỊ HỖ TRỢ KINH PHÍ NHẬN CHĂM SÓC, NUÔI DƯỠNG"
_CCCD_TEXT = "CĂN CƯỚC CÔNG DÂN Số định danh cá nhân"
_GXN_TEXT = "GIẤY XÁC NHẬN KHUYẾT TẬT Dạng khuyết tật Mức độ khuyết tật: Nặng"


def _files(*names):
    return [{"name": n, "type": "application/pdf", "dataUrl": ""} for n in names]


def test_mau_01_cccd_va_khuyet_tat_dinh_chung_dong_mau_01_to_khai_dung_dau():
    files = _files("gxn.pdf", "cccd_tre.pdf", "to_khai.pdf", "cccd_bo.pdf")
    ocr = [
        {"name": "gxn.pdf", "text": _GXN_TEXT},
        {"name": "cccd_tre.pdf", "text": _CCCD_TEXT},
        {"name": "to_khai.pdf", "text": _TK01_TEXT},
        {"name": "cccd_bo.pdf", "text": _CCCD_TEXT},
    ]
    items, warnings, _ = ap.build_plan_items(files, ocr, {})

    assert not warnings
    assert [i["fileName"] for i in items] == ["to_khai.pdf", "cccd_tre.pdf", "cccd_bo.pdf", "gxn.pdf"]
    assert {i["componentName"] for i in items} == {"Tờ khai đề nghị trợ cấp xã hội"}
    assert [i["documentName"] for i in items] == [
        "Tờ khai đề nghị trợ cấp xã hội (Mẫu số 01)", "Căn cước", "Căn cước 2", "Giấy xác nhận khuyết tật",
    ]
    assert all(i["target"] == "attp-row" and i["loaiBan"] == "Scan tệp tin" for i in items)


def test_to_khai_nhac_giay_xac_nhan_khuyet_tat_van_la_to_khai():
    assert ap._rule_doc_type(_TK01_TEXT) == "to_khai_mau_01"
    assert ap._rule_doc_type(_TK02_TEXT) == "to_khai_mau_02"
    assert ap._rule_doc_type(_GXN_TEXT) == "khuyet_tat"


def test_mau_02_vao_dong_rieng():
    files = _files("tk01.pdf", "tk02.pdf")
    ocr = [{"name": "tk01.pdf", "text": _TK01_TEXT}, {"name": "tk02.pdf", "text": _TK02_TEXT}]
    items, _, _ = ap.build_plan_items(files, ocr, {})

    rows = {i["fileName"]: i["componentName"] for i in items}
    assert rows == {"tk01.pdf": "Tờ khai đề nghị trợ cấp xã hội", "tk02.pdf": "Tờ khai nhận chăm sóc, nuôi dưỡng"}


def test_chi_co_mau_02_thi_giay_to_chung_vao_dong_mau_02():
    files = _files("cccd.pdf", "tk02.pdf")
    ocr = [{"name": "cccd.pdf", "text": _CCCD_TEXT}, {"name": "tk02.pdf", "text": _TK02_TEXT}]
    items, _, _ = ap.build_plan_items(files, ocr, {})

    assert [i["fileName"] for i in items] == ["tk02.pdf", "cccd.pdf"]
    assert {i["componentName"] for i in items} == {"Tờ khai nhận chăm sóc, nuôi dưỡng"}


def test_llm_uu_tien_hon_rule_va_tep_la_giu_ten_goc():
    files = _files("scan_1.pdf", "scan_2.pdf")
    ocr = [{"name": "scan_1.pdf", "text": "noi dung mo"}, {"name": "scan_2.pdf", "text": "khong ro"}]
    items, warnings, classified = ap.build_plan_items(files, ocr, {0: "to_khai_mau_01", 1: "other"})

    assert items[0]["documentName"] == "Tờ khai đề nghị trợ cấp xã hội (Mẫu số 01)"
    assert items[1]["documentName"] == "scan_2.pdf"
    assert items[1]["componentName"] == "Tờ khai đề nghị trợ cấp xã hội"
    assert classified[0]["source"] == "llm"
    assert warnings and "scan_2.pdf" in warnings[0]


def test_normalize_doc_type_tu_llm():
    assert ap._normalize_doc_type("to_khai_mau_02") == "to_khai_mau_02"
    assert ap._normalize_doc_type("to_khai_mau_01") == "to_khai_mau_01"
    assert ap._normalize_doc_type("khai_sinh") == "khai_sinh"
    assert ap._normalize_doc_type("cu_tru") == "cu_tru"
    assert ap._normalize_doc_type("can_cuoc") == "can_cuoc"
    assert ap._normalize_doc_type("xyz") == "other"


async def test_plan_goi_ocr_va_llm(monkeypatch):
    from app.process.schemas import FileItem
    from app.services import ocr as ocr_service

    async def fake_ocr(_files):
        return [{"name": "a.pdf", "text": _CCCD_TEXT}, {"name": "b.pdf", "text": _TK01_TEXT}]

    async def fake_classify(_docs):
        return {0: "can_cuoc", 1: "to_khai_mau_01"}

    monkeypatch.setattr(ocr_service, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(ap, "_classify_with_llm", fake_classify)

    files = [FileItem(name=n, type="application/pdf", dataUrl="data:application/pdf;base64,QUJD", role="attachment")
             for n in ("a.pdf", "b.pdf")]
    result = await ap.plan(files, {}, None)

    assert [a["fileName"] for a in result["attachments"]] == ["b.pdf", "a.pdf"]
    assert not result["errors"]


def test_registry_va_nhan_dien_khong_trung_thu_tuc_cu():
    from app.procedures import registry

    assert registry._PIPELINE[_KEY] is process_runner.run
    assert registry._ATTACH_PIPELINE[_KEY] is ap.plan
    phrase = registry._BY_KEY[_KEY]["detect"]["textIncludes"][0].lower()
    old = registry._BY_KEY["tro-cap-xa-hoi-hang-thang"]
    assert phrase not in old["label"].lower()
    assert not all(p.lower() in registry._BY_KEY[_KEY]["label"].lower() for p in old["detect"]["textIncludes"])
