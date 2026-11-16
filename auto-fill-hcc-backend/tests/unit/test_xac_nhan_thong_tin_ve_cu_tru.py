"""Xác nhận thông tin về cư trú (1.010041, Cổng DVC Bộ Công an): mapper ô form, Trường hợp trên / khác địa bàn,
hình thức nhận kết quả, nhận diện trang dùng chung với đăng ký thường trú, luồng trợ lý. Thủ tục không đính kèm."""
import asyncio

from app.channels.handfree.chat import flow
from app.pipelines.xac_nhan_thong_tin_ve_cu_tru.process import mapper
from app.pipelines.xac_nhan_thong_tin_ve_cu_tru.process import runner as process_runner
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls

KEY = "xac-nhan-thong-tin-ve-cu-tru"
# Khai hộ: người đề nghị là con, bố (chủ hộ) được ủy quyền nộp thay.
PERSON = {
    "CoQuan_Tinh": "Tỉnh Lai Châu", "CoQuan_Xa": "Phường Đoàn Kết",
    "NguoiDeNghi_HoTen": "Le Minh Khoa", "NguoiDeNghi_NgaySinh": "3/5/2005", "NguoiDeNghi_GioiTinh": "Nam",
    "NguoiDeNghi_SoDinhDanh": "0122 0500 0123", "NguoiDeNghi_SoDienThoai": "0987 000 222",
    "NguoiDeNghi_Email": "Khoa.Le@example.com",
    "NoiThuongTru_Tinh": "Tỉnh Lai Châu", "NoiThuongTru_Xa": "Phường Đoàn Kết",
    "ChuHo_HoTen": "Le Van Hai", "ChuHo_QuanHe": "Con", "ChuHo_SoDinhDanh": "012070000456",
    "NoiDungDeNghi": "Đề nghị xác nhận thông tin về cư trú: nơi thường trú hiện tại. Mục đích: bổ sung hồ sơ học bổng.",
    # LLM chép nhầm chủ hộ vào bảng cùng thay đổi → bỏ theo số định danh.
    "ThanhVien": [{"hoTen": "Le Van Hai", "soDinhDanh": "012070000456", "quanHeVoiChuHo": "Chủ hộ"}],
    "HinhThucNhanKetQua": "Bản giấy, nhận trực tiếp",
}


def _enrich(values: dict, options=None) -> list[dict]:
    return mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)


def _by(values: dict, options=None) -> dict:
    return {f["name"]: f for f in _enrich(values, options)}


def test_thu_tu_va_gia_tri_o_form():
    out = _enrich(PERSON)
    by = {f["name"]: f for f in out}
    names = [f["name"] for f in out]
    assert names[:2] == ["cboORG", "cboBPROC_CASE_CODE"]
    assert names.index("cboFORMAT_DATE") < names.index("txtBIRTH_DATE") < names.index("txtFULLNAME")
    assert names[-2:] == ["cboTYPE_GET_RESULT", "txtNUMBER_OF_RESULT"]
    assert by["cboORG"]["value"] == {"province": "Tỉnh Lai Châu", "ward": "Phường Đoàn Kết",
                                     "cityId": "cboRECEIVE_ADDR_CITY_ID", "wardId": "cboRECEIVE_ADDR_VILLAGE_ID",
                                     "readySelect": "cboBPROC_CASE_CODE"}
    assert by["cboORG"]["onlyIfEmpty"] is True and "default" not in by["cboORG"]
    # Thường trú cùng phường với cơ quan tiếp nhận → trên địa bàn quản lý.
    assert by["cboBPROC_CASE_CODE"]["value"] == "Cấp cho NK thường trú trên địa bàn quản lý"
    assert "default" not in by["cboBPROC_CASE_CODE"]
    assert by["txtFULLNAME"]["value"] == "LE MINH KHOA" and by["txtID_CARD_NUMBER"]["value"] == "012205000123"
    assert by["txtBIRTH_DATE"]["value"] == "03/05/2005" and by["cboFORMAT_DATE"]["value"] == "Ngày tháng năm"
    assert by["cboGENDER_ID"]["value"] == "Nam"
    assert by["txtPHONE_NUMBER"]["value"] == "0987000222" and by["txtEMAIL"]["value"] == "khoa.le@example.com"
    assert by["txtHH_HEAD_FULLNAME"]["value"] == "LE VAN HAI"
    assert by["cboRELATIONSHIP_WITH_HHHEAD_ID"]["value"] == "Con"
    assert by["txtID_CARD_NUMBER_HHEAD"]["value"] == "012070000456"
    assert by["txtCHANGED_CONTENT_NOTE"]["value"].startswith("Đề nghị xác nhận thông tin về cư trú")
    # Bảng cùng thay đổi chỉ có chủ hộ chép nhầm → bỏ, không gửi bảng rỗng.
    assert "tblNguoi_CUNGTD" not in by
    # Ô của đăng ký thường trú mà thủ tục này ẩn / không điền.
    assert not {"radIsHouseHold", "txtSUGGEST_DETAIL_ADDR", "radIsChangePerson", "chkRULE"} & set(by)
    # Nhận bản giấy trực tiếp; giấy không ghi số lượng phiếu → 1, tô vàng.
    assert by["cboTYPE_GET_RESULT"]["value"] == "Nhận trực tiếp"
    assert by["txtNUMBER_OF_RESULT"]["value"] == "1" and by["txtNUMBER_OF_RESULT"]["default"] is True


def test_thuong_tru_khac_phuong_thi_khac_dia_ban():
    values = dict(PERSON, NoiThuongTru_Xa="Phường Tân Phong")
    assert _by(values)["cboBPROC_CASE_CODE"]["value"] == "Cấp cho NK thường trú khác địa bàn quản lý"
    values = dict(PERSON, NoiThuongTru_Tinh="Tỉnh Điện Biên", NoiThuongTru_Xa="Phường Mường Thanh")
    assert _by(values)["cboBPROC_CASE_CODE"]["value"] == "Cấp cho NK thường trú khác địa bàn quản lý"


def test_llm_bo_tien_to_xa_van_cung_dia_ban():
    values = dict(PERSON, NoiThuongTru_Tinh="", NoiThuongTru_Xa="Đoàn Kết")
    case = _by(values)["cboBPROC_CASE_CODE"]
    assert case["value"] == "Cấp cho NK thường trú trên địa bàn quản lý" and "default" not in case


def test_khong_biet_noi_thuong_tru_thi_tren_dia_ban_to_vang():
    values = {k: v for k, v in PERSON.items() if not k.startswith("NoiThuongTru_")}
    case = _by(values)["cboBPROC_CASE_CODE"]
    assert case["value"] == "Cấp cho NK thường trú trên địa bàn quản lý" and case["default"] is True


def test_giay_khong_ghi_co_quan_thi_lay_xa_tai_khoan_to_vang():
    values = {k: v for k, v in PERSON.items() if not k.startswith("CoQuan_")}
    options = mapper.with_account_process_options({}, {"tinh": "Tỉnh Mẫu", "xa": "Phường Mẫu"}, KEY)
    agency = _by(values, options)["cboORG"]
    assert agency["value"]["ward"] == "Phường Mẫu" and agency["default"] is True
    # Thủ tục khác không nhận cờ của thủ tục này.
    assert "_accountAgency" not in mapper.with_account_process_options({}, {"tinh": "T", "xa": "X"}, "khac")


def test_hinh_thuc_nhan_ket_qua():
    # Không giấy nào ghi → giữ mặc định của cổng, không gửi ô nào.
    by = _by({k: v for k, v in PERSON.items() if k != "HinhThucNhanKetQua"})
    assert not {"cboTYPE_GET_RESULT", "txtNUMBER_OF_RESULT"} & set(by)
    by = _by(dict(PERSON, HinhThucNhanKetQua="Nhận kết quả trên Cổng dịch vụ công"))
    assert by["cboTYPE_GET_RESULT"]["value"] == "Nhận qua cổng thông tin" and "txtNUMBER_OF_RESULT" not in by
    by = _by(dict(PERSON, HinhThucNhanKetQua="Gửi qua bưu chính", SoLuongPhieu="02 bản"))
    assert by["cboTYPE_GET_RESULT"]["value"] == "Qua đường bưu chính"
    assert by["txtNUMBER_OF_RESULT"]["value"] == "2" and "default" not in by["txtNUMBER_OF_RESULT"]


def test_runner_dung_mapper(monkeypatch):
    async def fake_run(files_by_role, **kwargs):
        assert kwargs["comp_by_name"]["ThanhVien"] == "x-array"
        assert "NoiThuongTru_Xa" in kwargs["allowed"]
        return {"fields": [{"name": k, "value": v} for k, v in PERSON.items()]}

    monkeypatch.setattr(process_runner.runner, "run", fake_run)
    res = asyncio.run(process_runner.run({}, {}))
    assert {f["name"] for f in res["fields"]} >= {"cboORG", "cboBPROC_CASE_CODE", "txtFULLNAME"}


def _detect(url: str) -> str:
    """Bước khớp URL của popup.js: rule urlIncludes đầu tiên (đúng urlScope) thắng, so trên URL đã lower-case."""
    url = url.lower()
    for proc in with_ke_khai_detect_urls(registry.PROCEDURES):
        detect = proc.get("detect") or {}
        scope = detect.get("urlScope") or []
        if scope and not any(s and s.lower() in url for s in scope):
            continue
        if any(u and u.lower() in url for u in detect.get("urlIncludes") or []):
            return proc["key"]
    return ""


def test_link_registry_va_nhan_dien_trang_chung_voi_thuong_tru():
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.010041" and "TT=THUONGTRU_09" in link["url"]
    proc = registry.get_procedure(KEY)
    assert registry.get_pipeline(KEY) is not None
    # Không đính kèm.
    assert proc["hasAttachmentStep"] is False and registry.get_attach_pipeline(KEY) is None
    # Cùng trang dang-ky-thuong-tru.html: _09 → thủ tục này, _08 điều chỉnh, _01 vẫn là đăng ký thường trú.
    assert _detect(link["url"]) == KEY
    for other in ("dieu-chinh-thong-tin-ve-cu-tru", "dang-ky-thuong-tru"):
        assert _detect(next(item for item in KE_KHAI_LINKS if item["key"] == other)["url"]) == other


def test_entry_tro_ly_cung_key_toan_quoc():
    from app.channels.handfree import procedure_registry as handfree

    hf = handfree.get_procedure(KEY)
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert hf["keKhaiUrl"] == link["url"] and hf["detect"] == registry.get_procedure(KEY)["detect"]
    assert hf["requiresCapability"] == "supportsBcaThuongTru" and hf["submitCommitCheckbox"] == "chkRULE"
    assert hf["hasAttachmentStep"] is False and "provinceOnly" not in hf
    assert handfree._HOAN_THIEN_THEO_TINH[KEY] == handfree._TAT_CA
    conv = {"state": "greet", "procedure_key": None, "client_capabilities": {"supportsBcaThuongTru": True},
            "location": {"province": "Tỉnh Lai Châu", "province_slug": "lai_chau", "ward": "Phường Đoàn Kết"}}
    flow._to_confirm_procedure(conv, KEY)
    from app.channels.handfree.chat.intents import Intent

    r = flow._handle_guide_login(conv, Intent("event", "page_status", {"bcaAgencyBlock": True}))
    assert "nơi thường trú" in r.display_md
