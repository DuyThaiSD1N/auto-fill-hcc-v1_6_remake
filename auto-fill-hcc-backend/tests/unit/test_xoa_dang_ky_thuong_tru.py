"""Xóa đăng ký thường trú (1.003197, Cổng DVC Bộ Công an): mapper ô form trên bộ id trang thường trú, Trường hợp theo
lý do + cả hộ / nhân khẩu, Nội dung đề nghị chỉ khi tờ khai ghi đúng nội dung xóa, cơ quan (CT01 chỉ ghi xã thì tỉnh
theo tài khoản), link trang thủ tục Bộ Công an + nhận diện trang kê khai dùng chung với đăng ký thường trú, luồng trợ
lý, đính kèm (tách / không tách) vào bảng giấy tờ cùng trang."""
import asyncio
import json

from app.channels.handfree.chat import flow
from app.pipelines.xoa_dang_ky_thuong_tru.attach import planner as attach
from app.pipelines.xoa_dang_ky_thuong_tru.attach.dinh_kem_khong_tach import planner as khong_tach
from app.pipelines.xoa_dang_ky_thuong_tru.attach.dinh_kem_khong_tach.planner import ROWS
from app.pipelines.xoa_dang_ky_thuong_tru.process import mapper
from app.pipelines.xoa_dang_ky_thuong_tru.process import runner as process_runner
from app.pipelines.xoa_dang_ky_thuong_tru.process.schema import CASES
from app.process.schemas import FileItem
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls
from app.services import ocr
from app.services.llm import client as llm_client

KEY = "xoa-dang-ky-thuong-tru"
# Người đề nghị là chủ hộ, cả hộ (vợ + con) xóa thường trú vì đã bán nhà. Dữ liệu giả.
PERSON = {
    "CoQuan_Tinh": "Tỉnh Lai Châu", "CoQuan_Xa": "Phường Đoàn Kết",
    "TruongHop": "",
    "NguoiDeNghi_HoTen": "Lo Van Binh", "NguoiDeNghi_NgaySinh": "5/3/1980", "NguoiDeNghi_GioiTinh": "Nam",
    "NguoiDeNghi_SoDinhDanh": "0120 8000 0111", "NguoiDeNghi_SoDienThoai": "………", "NguoiDeNghi_Email": "",
    "ChuHo_HoTen": "Lo Van Binh", "ChuHo_QuanHe": "chủ hộ", "ChuHo_SoDinhDanh": "012080000111",
    "NoiDungDeNghi": "Đề nghị xóa đăng ký thường trú cho cả hộ do đã chuyển nhượng nhà",
    "ThanhVien": [
        {"hoTen": "Lo Van Binh", "soDinhDanh": "012080000111", "quanHeVoiChuHo": "Chủ hộ"},
        {"hoTen": "Vu Thi Hoa", "ngaySinh": "02/01/1985", "gioiTinh": "Nữ", "soDinhDanh": "012185000222",
         "quanHeVoiChuHo": "vợ"},
        {"hoTen": "Lo Minh An", "ngaySinh": "2012", "gioiTinh": "", "soDinhDanh": "012212000333",
         "quanHeVoiChuHo": "con đẻ"},
    ],
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
    assert names.index("cboFORMAT_DATE") < names.index("txtBIRTH_DATE")
    # Nội dung đề nghị SAU Trường hợp (chọn Trường hợp là cổng tự sinh câu, ghi đè lại theo tờ khai).
    assert names.index("cboBPROC_CASE_CODE") < names.index("txtCHANGED_CONTENT_NOTE")
    # Cặp id + ô cơ quan của trang thường trú; Tỉnh/Xã trống sẵn → onlyIfEmpty như tách hộ.
    assert by["cboORG"]["value"] == {"province": "Tỉnh Lai Châu", "ward": "Phường Đoàn Kết",
                                     "cityId": "cboRECEIVE_ADDR_CITY_ID", "wardId": "cboRECEIVE_ADDR_VILLAGE_ID",
                                     "readySelect": "cboBPROC_CASE_CODE"}
    assert by["cboORG"]["onlyIfEmpty"] is True and "default" not in by["cboORG"]
    assert by["cboBPROC_CASE_CODE"]["value"] == "Cả hộ do không còn chỗ ở hợp pháp"
    assert by["txtFULLNAME"]["value"] == "LO VAN BINH" and by["txtID_CARD_NUMBER"]["value"] == "012080000111"
    assert by["txtBIRTH_DATE"]["value"] == "05/03/1980" and by["cboFORMAT_DATE"]["value"] == "Ngày tháng năm"
    assert by["cboGENDER_ID"]["value"] == "Nam"
    assert by["txtHH_HEAD_FULLNAME"]["value"] == "LO VAN BINH"
    assert by["cboRELATIONSHIP_WITH_HHHEAD_ID"]["value"] == "Chủ hộ"
    assert by["txtID_CARD_NUMBER_HHEAD"]["value"] == "012080000111"
    assert by["txtCHANGED_CONTENT_NOTE"]["value"] == PERSON["NoiDungDeNghi"]
    # Ô trống / chấm chấm không điền; khối ẩn với Xóa ĐKTT (nơi đề nghị, CT02, VNeID) và radio khai hộ không điền.
    assert not {"txtPHONE_NUMBER", "txtEMAIL", "txtSUGGEST_DETAIL_ADDR", "radIsHouseHold", "radIsChangePerson",
                "chkDOSSIER_CT02", "txtFULLNAME0", "chkRULE"} & set(by)


def test_bang_thanh_vien_bo_chu_ho_va_viet_hoa_quan_he():
    table = _by(PERSON)["tblNguoi_CUNGTD"]["value"]
    assert table["addSelector"] == "#tblNguoi_CUNGTD a.add_CUNGTD"
    # Dòng "Chủ hộ" chép nhầm vào bảng → bỏ trước khi đánh chỉ số; ô ngày sinh của bảng là ô chữ (không định dạng).
    assert table["rows"] == [
        [{"id": "txtFULLNAME_CUNGTD0", "comp": "dom-input", "value": "VU THI HOA"},
         {"id": "txtDOB_CUNGTD0", "comp": "dom-input", "value": "02/01/1985"},
         {"id": "cboGENDER_CUNGTD0", "comp": "dom-select", "value": "Nữ"},
         {"id": "txtIDENTIFIER_NOCARD_NUMBER_CUNGTD0", "comp": "dom-input", "value": "012185000222"},
         {"id": "cboRELATIONSHIP_CHUHO_CUNGTD0", "comp": "dom-select", "value": "Vợ"}],
        [{"id": "txtFULLNAME_CUNGTD1", "comp": "dom-input", "value": "LO MINH AN"},
         {"id": "txtDOB_CUNGTD1", "comp": "dom-input", "value": "2012"},
         {"id": "cboGENDER_CUNGTD1", "comp": "dom-select", "value": "Nam"},
         {"id": "txtIDENTIFIER_NOCARD_NUMBER_CUNGTD1", "comp": "dom-input", "value": "012212000333"},
         {"id": "cboRELATIONSHIP_CHUHO_CUNGTD1", "comp": "dom-select", "value": "Con đẻ"}],
    ]


def test_truong_hop_theo_ly_do_va_ca_ho_nhan_khau():
    member = dict(PERSON, ChuHo_HoTen="Lo Van Tien", ChuHo_QuanHe="con", ChuHo_SoDinhDanh="012050000999",
                  ThanhVien=[])
    cases = {
        "Xóa đăng ký thường trú do đã bán nhà": "Nhân khẩu do không còn chỗ ở hợp pháp",
        "Đề nghị xóa thường trú vì vắng mặt liên tục trên 12 tháng": "Nhân khẩu do vắng mặt trên 12 tháng",
        "Xóa đăng ký thường trú do ra nước ngoài định cư": "Nhân khẩu do định cư nước ngoài",
        "Xóa đăng ký thường trú cả hộ do định cư ở nước ngoài": "Cả hộ do định cư nước ngoài",
    }
    for reason, want in cases.items():
        assert _by(dict(member, NoiDungDeNghi=reason))["cboBPROC_CASE_CODE"]["value"] == want, reason
    # Người đề nghị là chủ hộ → luôn nhãn "Cả hộ" (nhóm nhân khẩu của cổng không có quan hệ "Chủ hộ").
    assert _by(dict(PERSON, TruongHop="Nhân khẩu do vắng mặt trên 12 tháng"))["cboBPROC_CASE_CODE"]["value"] == \
        "Cả hộ do vắng mặt trên 12 tháng"
    # LLM rút gọn nhãn → vẫn ra đúng nhãn.
    assert _by(dict(member, TruongHop="vắng mặt 12 tháng", NoiDungDeNghi=""))["cboBPROC_CASE_CODE"]["value"] == \
        "Nhân khẩu do vắng mặt trên 12 tháng"
    # Mục 10 chép nhầm nội dung thủ tục khác (không có lý do xóa) → không gửi Trường hợp, KHÔNG ghi đè câu cổng tự sinh.
    wrong = _by(dict(PERSON, NoiDungDeNghi="Cấp cho nhân khẩu thường trú trên địa bàn quản lý"))
    assert "cboBPROC_CASE_CODE" not in wrong and "txtCHANGED_CONTENT_NOTE" not in wrong
    assert set(CASES) == {mapper._case({"TruongHop": c}, False) for c in CASES} | {
        mapper._case({"TruongHop": c}, True) for c in CASES}


def test_ct01_chi_ghi_xa_thi_tinh_theo_tai_khoan_to_vang():
    options = mapper.with_account_process_options({}, {"tinh": "Tỉnh Lai Châu", "xa": "Phường Tân Phong"}, KEY)
    agency = _by(dict(PERSON, CoQuan_Tinh=""), options)["cboORG"]
    assert agency["value"]["province"] == "Tỉnh Lai Châu" and agency["value"]["ward"] == "Phường Đoàn Kết"
    assert agency["default"] is True
    agency = _by({k: v for k, v in PERSON.items() if not k.startswith("CoQuan_")}, options)["cboORG"]
    assert agency["value"]["ward"] == "Phường Tân Phong" and agency["default"] is True
    assert "cboORG" not in _by({k: v for k, v in PERSON.items() if not k.startswith("CoQuan_")})
    assert "_accountAgency" not in mapper.with_account_process_options({}, {"tinh": "T", "xa": "X"}, "khac")


def test_o_lien_he_chu_tai_khoan_giu_gia_tri_cong():
    by = _by(dict(PERSON, NguoiDeNghi_SoDienThoai="0912345678", NguoiDeNghi_Email="a,b@gmail.com"))
    assert by["txtPHONE_NUMBER"]["keepPortalValue"] is True and by["txtEMAIL"]["value"] == "a.b@gmail.com"


def test_runner_dung_mapper(monkeypatch):
    async def fake_run(files_by_role, **kwargs):
        assert kwargs["comp_by_name"]["ThanhVien"] == "x-array" and "TruongHop" in kwargs["allowed"]
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


def test_link_trang_thu_tuc_bo_cong_an_va_nhan_dien_trang_ke_khai():
    from app.channels.handfree import procedure_registry as handfree

    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    # Link user đưa: trang thủ tục Cổng DVC Bộ Công an → extension bấm "Nộp hồ sơ" (chặng "bca", khớp mã trên trang).
    assert link["code"] == "1.003197" and link["url"].endswith("/bocongan/bothutuc/tthc?matt=26348")
    assert link["needsAgencySelect"] is False and link["directSubmit"] is True and link["bcaSubmit"] is True
    proc = registry.get_procedure(KEY)
    assert registry.get_pipeline(KEY) is not None
    assert proc["hasAttachmentStep"] is True and proc["supportsSplitDocuments"] is True
    assert registry.get_attach_pipeline(KEY) is attach.plan
    # Trang kê khai THUONGTRU_02 → thủ tục này; THUONGTRU_01 vẫn là đăng ký thường trú, _05 vẫn là tách hộ.
    page = handfree.get_procedure(KEY)["keKhaiUrl"]
    assert _detect(page) == KEY
    for other in ("dang-ky-thuong-tru", "tach-ho"):
        assert _detect(next(item for item in KE_KHAI_LINKS if item["key"] == other)["url"]) == other


def test_entry_tro_ly_cung_key_toan_quoc_hoi_truong_hop_dinh_kem_cung_trang():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.procedure_registry import case_pipeline_options

    hf = handfree.get_procedure(KEY)
    assert hf["detect"] == registry.get_procedure(KEY)["detect"]
    # Trợ lý mở thẳng trang kê khai (luồng bcaPortal) như các thủ tục cư trú khác.
    assert "dang-ky-thuong-tru.html" in hf["keKhaiUrl"] and "TT=THUONGTRU_02" in hf["keKhaiUrl"]
    assert hf["bcaPortal"] is True and hf["requiresCapability"] == "supportsBcaThuongTru"
    assert hf["submitCommitCheckbox"] == "chkRULE"
    assert hf["hasAttachmentStep"] is True and hf["samePageAttach"] is True and hf["askBeforeAttach"] is True
    assert hf["supportsSplitDocuments"] is True and hf["docsAdjustRefill"] is True and "provinceOnly" not in hf
    assert flow.refill_at_done(hf)
    assert handfree._HOAN_THIEN_THEO_TINH[KEY] == handfree._TAT_CA
    # Nút Trường hợp = đúng nhãn mapper dùng; công dân chọn thì thắng nhãn LLM.
    assert hf["bcaCase"]["options"] == list(CASES)
    options = case_pipeline_options(hf, {"bca_case": CASES[5]})
    assert options == {"bcaCase": CASES[5]}
    assert _by(PERSON, options)["cboBPROC_CASE_CODE"]["value"] == CASES[5]


# ── Đính kèm (ảnh user 24/11/2026: dòng Tờ khai + dòng chứng minh không còn chỗ ở hợp pháp / định cư nước ngoài theo
# Trường hợp, nút "+" thêm dòng) ──
_PAGES = ["TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ", "HỢP ĐỒNG CHUYỂN NHƯỢNG QUYỀN SỬ DỤNG ĐẤT", "Các bên ký tên",
          "GIẤY KHAI SINH", "CĂN CƯỚC CÔNG DÂN"]
_OCR = "\n".join(f"───── Trang {i + 1}/{len(_PAGES)} ─────\n{t}\nTrang {i + 1} / {len(_PAGES)}"
                 for i, t in enumerate(_PAGES))
_DOCS = [
    {"fileIndex": 0, "pages": [1], "docType": "to_khai", "documentName": "Tờ khai thay đổi thông tin cư trú"},
    {"fileIndex": 0, "pages": [2, 3], "docType": "cho_o", "documentName": "Hợp đồng chuyển nhượng quyền sử dụng đất"},
    {"fileIndex": 0, "pages": [4], "docType": "nhan_than", "documentName": "Giấy khai sinh"},
    {"fileIndex": 0, "pages": [5], "docType": "cccd", "documentName": "Thẻ căn cước", "matThe": "ca_hai",
     "chuThe": "LO VAN BINH"},
]


def _files(*names):
    return [FileItem(name=n, type="application/pdf", dataUrl="data:,", role="") for n in names]


def _patch(monkeypatch, documents, fail_split=False):
    async def fake_ocr(files):
        return [{"text": _OCR} for _ in files]

    async def fake_chat(messages, max_tokens=None, **_):
        if fail_split and "TỪNG TRANG" in messages[0]["content"]:
            raise RuntimeError("llm hỏng")
        return json.dumps({"documents": documents})

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(llm_client, "chat", fake_chat)


def test_tach_file_dung_dong_va_khong_sot_trang(monkeypatch):
    _patch(monkeypatch, _DOCS)
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {"splitDocuments": True}))
    items = res["attachments"]
    got = [(i["rowKey"] or i["componentName"], i["newRow"], i["sourceSegments"][0]["pageIndexes"]) for i in items]
    assert got == [
        (ROWS["to_khai"]["rowKey"], False, [0]),
        (ROWS["cho_o"]["rowKey"], False, [1, 2]),
        # Giấy có loại rõ mà bảng không có dòng → dòng "+" mang tên giấy.
        ("Giấy khai sinh", True, [3]),
        # Thẻ căn cước mang tên chủ thẻ (cán bộ phân biệt thẻ của từng người).
        ("CCCD Lo Van Binh", True, [4]),
    ]
    assert sorted(p for i in items for s in i["sourceSegments"] for p in s["pageIndexes"]) == list(range(5))
    assert all(i["target"] == "bca-row" and i["bcaPlainTable"] is True for i in items)
    assert items[0]["groupLabel"] == "Xóa đăng ký thường trú"
    assert items[0]["rowFields"] == {"count": "01"} and not res["errors"]


def test_tat_tach_thi_dinh_nguyen_tep_vao_moi_dong_kem_ghi_chu(monkeypatch):
    _patch(monkeypatch, _DOCS)
    for options in ({}, {"splitDocuments": "true"}, None):
        res = asyncio.run(attach.plan(_files("hoso.pdf"), options))
        items = res["attachments"]
        assert all("sourceSegments" not in i and i["fileIndex"] == 0 for i in items)
        assert [(i["rowKey"], i["newRow"]) for i in items] == [
            (ROWS["to_khai"]["rowKey"], False), (ROWS["cho_o"]["rowKey"], False), ("", True)]
        assert items[1]["rowFields"]["note"] == (
            "Đính kèm chung tệp hoso.pdf (5 trang): Hợp đồng chuyển nhượng quyền sử dụng đất tại trang 2–3/5")
        assert items[2]["componentName"] == "Giấy khai sinh, Thẻ căn cước"
        assert items[2]["rowFields"]["note"].endswith("tại trang 4–5/5")


def test_ho_so_chi_co_to_khai_khong_gan_vao_dong_chung_minh():
    # Ảnh user: hồ sơ chỉ có CT01 → chỉ dòng 1 có tệp, dòng chứng minh để trống.
    items, warnings, _ = khong_tach.build_plan_items(
        ["ct01.pdf"], {0: 1}, [{"fileIndex": 0, "pages": [1], "docType": "to_khai"}])
    assert [i["rowKey"] for i in items] == [ROWS["to_khai"]["rowKey"]] and not warnings


def test_giay_dinh_cu_vao_dong_dinh_cu_giay_chua_ro_vao_dong_to_khai():
    items, warnings, _ = khong_tach.build_plan_items(
        ["dinhcu.pdf", "bia.pdf"], {0: 1, 1: 1},
        [{"fileIndex": 0, "pages": [1], "docType": "dinh_cu", "documentName": "Thẻ thường trú nước ngoài"},
         {"fileIndex": 1, "pages": [1], "docType": "other"}])
    assert [i["rowKey"] for i in items] == [ROWS["dinh_cu"]["rowKey"], ROWS["to_khai"]["rowKey"]]
    assert "bia.pdf" in warnings[0]


def test_dong_tren_cong_khop_ten_dong_trong_anh():
    # Chữ dòng trên cổng (ảnh 24/11/2026), so như extension: bỏ dấu, bỏ dấu câu, chứa rowKey.
    from app.pipelines._shared import fold

    for label, row in (("Tờ khai thay đổi thông tin cư trú", "to_khai"),
                       ("Giấy tờ chứng minh về việc không còn chỗ ở hợp pháp", "cho_o"),
                       ("Giấy tờ chứng minh định cư nước ngoài", "dinh_cu")):
        assert ROWS[row]["rowKey"] in fold(label), label


def test_ke_hoach_qua_duoc_response_model(monkeypatch):
    from app.attachments.schemas import AttachmentPlanResp

    _patch(monkeypatch, _DOCS)
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {}))
    out = AttachmentPlanResp.model_validate(res).model_dump(mode="json")["attachments"]
    assert out[0]["rowKey"] == ROWS["to_khai"]["rowKey"] and out[0]["bcaPlainTable"] is True
    assert out[2]["newRow"] is True


def test_tach_loi_quay_ve_khong_tach(monkeypatch):
    _patch(monkeypatch, _DOCS, fail_split=True)
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {"splitDocuments": True}))
    assert res["attachments"] and all("sourceSegments" not in i for i in res["attachments"])
    assert any("(tách)" in e for e in res["errors"])


def test_llm_loi_khong_tach_van_dinh_du_tep_vao_dong_to_khai(monkeypatch):
    async def fake_ocr(files):
        return [{"text": _OCR} for _ in files]

    async def broken(*_a, **_k):
        raise RuntimeError("llm hỏng")

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(llm_client, "chat", broken)
    res = asyncio.run(attach.plan(_files("a.pdf", "b.pdf"), {}))
    assert [i["rowKey"] for i in res["attachments"]] == [ROWS["to_khai"]["rowKey"]] * 2
    assert any("kiểm tra lại" in e for e in res["errors"])
