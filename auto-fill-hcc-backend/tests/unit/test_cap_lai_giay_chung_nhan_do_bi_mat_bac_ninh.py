"""Unit test "[Bắc Ninh] Cấp lại Giấy chứng nhận do bị mất" (1.115465).

Theo mapping DOM 10/11/2026: Đơn Mẫu 18 khớp CLASS eform-element-<Key>; số vào sổ / số phát hành GCN bị mất (Đơn
trình báo, Bản cam kết) ghép vào "II. Nội dung biến động"; khối doiTuongKhac* = chủ hồ sơ. Đính kèm: tệp có Đơn (kể cả
tệp chung cả bộ) → TP-H05.000026, GCN → TP-H05.000040, mảnh trích đo → TP-H05.000045, còn lại → File đính kèm khác.
Dữ liệu trong test là bịa.
"""

import asyncio

from app.pipelines.cap_lai_giay_chung_nhan_do_bi_mat_bac_ninh.attach import planner
from app.pipelines.cap_lai_giay_chung_nhan_do_bi_mat_bac_ninh.attach.prompt import SYSTEM_PROMPT
from app.pipelines.cap_lai_giay_chung_nhan_do_bi_mat_bac_ninh.process import fallback, mapper, runner, schema

_KEY = "cap-lai-giay-chung-nhan-do-bi-mat-bac-ninh"

_SAMPLE = {
    "Cccd_HoTen": "Nguyễn Văn An",
    "Cccd_SoDinhDanh": "0270.900.01234",
    "Cccd_NgayCap": "10/05/2022",
    "Cccd_NoiCap": "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
    "Don_KinhGui": "Chi nhánh văn phòng đăng ký đất đai liên phường xã Từ Sơn",
    "Don_DiaChi": "Thôn Đông - Xã Tân Hồng - Huyện Từ Sơn - Tỉnh Bắc Ninh",
    "Don_DienThoai": "0912.345.678",
    "Don_NoiDungBienDong": "- Cấp lại giấy chứng nhận do bị mất\n- Thay đổi địa chỉ thường trú ......",
    "Gcn_SoVaoSo": "CS01234/T05/Q02",
    "Gcn_SoPhatHanh": "CĐ 123456",
}


def _fields(values: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in values.items()]


def _ui(values: dict) -> dict:
    return {f["name"]: f for f in mapper.enrich(_fields(values))}


# ── Điền đơn ──

def test_than_don_khop_class_eform_va_nguoi_nhan_khop_name():
    ui = _ui(_SAMPLE)
    assert ui["KinhGui"]["value"] == "Chi nhánh văn phòng đăng ký đất đai liên phường xã Từ Sơn"
    assert ui["Ten2"]["value"] == "Nguyễn Văn An"
    assert ui["GiayToNhanThanphapNhan"]["value"] == (
        "CCCD số 027090001234, cấp 10/05/2022, Cục Cảnh sát quản lý hành chính về trật tự xã hội")
    assert ui["DiaChi"]["value"] == "Thôn Đông, Xã Tân Hồng, Huyện Từ Sơn, Tỉnh Bắc Ninh"
    assert ui["DienThoaiLienHeNeuCo"]["value"] == "0912345678"
    assert ui["IINoiDungBienDong3"]["comp"] == "bn-textarea"
    assert ui["nhanTaiNhahoTen"]["value"] == "Nguyễn Văn An"
    assert ui["nhanTaiNhasoCCCD"]["value"] == "027090001234"
    assert ui["nhanTaiNhadiaChi"]["value"] == ui["DiaChi"]["value"]
    # Mọi tên ô phát ra đều có trong bảng comp (FE khớp CLASS hoặc NAME).
    assert set(ui) <= set(schema.UI_COMP_BY_NAME)
    # Ô phần UBND xác nhận / nơi-ngày khai (cổng điền sẵn, class trùng) không phát.
    assert not {"NoiKhaiHoSo", "NgayKhaiHoSo", "HienTrangSuDungDatSuDungOnDinh"} & set(ui)


def test_noi_dung_bien_dong_giu_dong_va_ghep_so_gcn_bi_mat():
    value = _ui(_SAMPLE)["IINoiDungBienDong3"]["value"]
    assert value.split("\n") == [
        "- Cấp lại giấy chứng nhận do bị mất",
        "- Thay đổi địa chỉ thường trú",
        "Thông tin Giấy chứng nhận bị mất: Số vào sổ cấp Giấy chứng nhận: CS01234/T05/Q02; "
        "Số phát hành (số seri): CĐ 123456",
    ]


def test_don_da_ghi_so_gcn_thi_khong_ghi_lai():
    values = {**_SAMPLE, "Don_NoiDungBienDong": "Cấp lại GCN do bị mất, số vào sổ CS01234/T05/Q02, số phát hành CĐ123456"}
    assert _ui(values)["IINoiDungBienDong3"]["value"] == values["Don_NoiDungBienDong"]


def test_don_trong_muc_ii_van_co_so_gcn_thi_dung_cau_mac_dinh():
    values = {k: v for k, v in _SAMPLE.items() if k != "Don_NoiDungBienDong"}
    value = _ui(values)["IINoiDungBienDong3"]["value"]
    assert value.startswith("Cấp lại Giấy chứng nhận do bị mất\nThông tin Giấy chứng nhận bị mất:")
    # Không có cả mục II lẫn số GCN → không phát ô (không bịa).
    bare = {k: v for k, v in values.items() if not k.startswith("Gcn_")}
    assert "IINoiDungBienDong3" not in _ui(bare)


def test_o_cham_giu_cho_khong_phat():
    values = {**_SAMPLE, "Don_GiayTo2": "........", "Don_TranhChap": "…", "Don_MaSoThue": "....."}
    ui = _ui(values)
    assert not {"2", "MaSoThueNeuCo", "2TinhTrangTranhChapDatDai"} & set(ui)


# ── Fallback OCR ──

_OCR = """Mẫu số 18. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất
Kính gửi: Chi nhánh văn phòng đăng ký đất đai liên phường xã Từ Sơn
- Tên(2): Nguyễn Văn An
- Địa chỉ: Thôn Đông, Xã Tân Hồng, Tỉnh Bắc Ninh
II. Nội dung biến động(3): Cấp lại giấy chứng nhận do bị mất
III. Thông tin về đối tượng được miễn, giảm nghĩa vụ tài chính về đất đai (nếu có): ........
(2) Tình trạng tranh chấp đất đai: ..............
BẢN CAM KẾT
Năm 2020 tôi được cấp giấy chứng nhận Quyền sử dụng đất có số vào sổ
CS01234/T05/Q02 do Sở Tài nguyên - Môi trường cấp. Số phát hành CĐ 123456. Thửa 12, tờ bản đồ số 3."""


def test_fallback_bat_so_gcn_dia_chi_kinh_gui_khi_llm_bo_sot():
    out = fallback.apply_ocr_fallback({"Cccd_HoTen": "Nguyễn Văn An"}, [{"text": _OCR}])
    assert out["Gcn_SoVaoSo"] == "CS01234/T05/Q02"
    assert out["Gcn_SoPhatHanh"] == "CĐ 123456"
    assert out["Don_DiaChi"] == "Thôn Đông, Xã Tân Hồng, Tỉnh Bắc Ninh"
    assert out["Don_KinhGui"] == "Chi nhánh văn phòng đăng ký đất đai liên phường xã Từ Sơn"
    assert out["Don_NoiDungBienDong"] == "Cấp lại giấy chứng nhận do bị mất"
    # Dòng chỉ có chấm giữ chỗ = trống.
    assert "Don_TranhChap" not in out


def test_fallback_khong_de_gia_tri_llm_va_khong_bat_chu_thuong():
    out = fallback.apply_ocr_fallback({"Gcn_SoVaoSo": "CH00999"}, [{"text": _OCR}])
    assert out["Gcn_SoVaoSo"] == "CH00999"
    out = fallback.apply_ocr_fallback({}, [{"text": "ghi số vào sổ là 123 trang"}])
    assert "Gcn_SoVaoSo" not in out


# ── Khối ủy quyền (purpose="authorized_person") ──

def test_khoi_uy_quyen_la_chu_ho_so():
    out, warnings = mapper.enrich_authorized(_fields({
        "ChuHoSo_HoTen": "Nguyễn Văn An",
        "ChuHoSo_GioiTinh": "Nam",
        "ChuHoSo_SoDinhDanh": "027090001234",
        "ChuHoSo_NgaySinh": "01/02/1990",
        "ChuHoSo_NoiCap": "Cục CS QLHC về TTXH",
        "ChuHoSo_DienThoai": "0912 345 678",
        "ChuHoSo_ThuongTru": {"tinh": "Bắc Ninh", "xa": "Phường Tân Hồng", "chiTietDuoiXa": "Thôn Đông"},
    }))
    assert warnings == []
    by = {f["name"]: f for f in out}
    assert by["doiTuongKhachoTen"]["value"] == "Nguyễn Văn An"
    assert by["doiTuongKhacgioiTinhId"] == {"name": "doiTuongKhacgioiTinhId", "comp": "bn-select", "value": "Nam"}
    assert by["doiTuongKhacsoDienThoai"]["value"] == "0912345678"
    assert by["doiTuongKhacnoiCap"]["value"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    names = [f["name"] for f in out]
    assert names.index("doiTuongKhactinhThanhId") < names.index("doiTuongKhacphuongXaId")
    assert by["doiTuongKhacdiaChiChiTiet"]["value"] == "Thôn Đông, Phường Tân Hồng, Bắc Ninh"


def test_khoi_uy_quyen_thieu_cccd_thi_khong_dien():
    out, warnings = mapper.enrich_authorized(_fields({"ChuHoSo_HoTen": "Nguyễn Văn An"}))
    assert out == [] and warnings


def test_runner_tach_luot_theo_purpose(monkeypatch):
    calls = []

    async def fake_run(files_by_role, **kwargs):
        calls.append(kwargs["fields"])
        if kwargs["fields"] is schema.FIELDS_UYQUYEN:
            return {"fields": [{"name": "ChuHoSo_HoTen", "value": "Nguyễn Văn An"},
                               {"name": "ChuHoSo_SoDinhDanh", "value": "027090001234"}]}
        return {"fields": [{"name": "Cccd_HoTen", "value": "Nguyễn Văn An"}]}

    monkeypatch.setattr(runner.runner, "run", fake_run)
    res = asyncio.run(runner.run({}, {"purpose": "authorized_person"}))
    assert calls[-1] is schema.FIELDS_UYQUYEN
    assert {f["name"] for f in res["fields"]} == {"doiTuongKhachoTen", "doiTuongKhacsoDinhDanh"}
    res = asyncio.run(runner.run({}, {}))
    assert calls[-1] is schema.FIELDS
    assert {f["name"] for f in res["fields"]} == {"Ten2", "nhanTaiNhahoTen"}


# ── Đính kèm ──

def test_dinh_kem_theo_ma_tp_h05_cua_form_cap_lai():
    route = {t: planner._build_item({"name": "x.pdf"}, 0, t, "Tài liệu") for t in planner._ROUTE}
    assert route["application"]["componentName"] == "TP-H05.000026"
    assert route["application"]["slotKey"] == "banChinh"
    assert route["land_certificate"]["componentName"] == "TP-H05.000040"
    assert route["cadastral_survey"]["componentName"] == "TP-H05.000045"
    for doc_type in ("identity", "authorization", "other"):
        assert route[doc_type]["target"] == "supplementary" and route[doc_type]["componentName"] == ""
    assert planner._build_item({"name": "x.pdf"}, 0, "khong_ro", "X")["target"] == "supplementary"


# Cài đặt "Có tách hồ sơ khi đính kèm" — bộ mẫu theo đúng cấu trúc tệp scan chung user gửi 10/11/2026 (chữ bịa):
# Đơn Mẫu 18 (1-2) / XN tình trạng hôn nhân (3) + mặt sau trắng (4) / Bản cam kết (5) + trắng (6) / Đơn trình báo
# (7) + trắng (8) / CCCD hai mặt chung một trang (9) + trắng (10). Chạy thật trên tệp đó cũng chia đúng 5 giấy này.
_TRANG_TACH = [
    "Mẫu số 18. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất ĐƠN ĐĂNG KÝ BIẾN ĐỘNG " + "x" * 80,
    "Cam đoan nội dung kê khai trên đơn là đúng sự thật II- XÁC NHẬN CỦA ỦY BAN NHÂN DÂN CẤP XÃ " + "x" * 80,
    "UBND PHƯỜNG TÂN HỒNG GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN Họ tên: NGUYỄN VĂN AN " + "x" * 80,
    "|",
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM BẢN CAM KẾT Tên tôi là: Nguyễn Văn An " + "x" * 80,
    "|",
    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM ĐƠN TRÌNH BÁO Về việc mất giấy chứng nhận " + "x" * 80,
    "|",
    "CĂN CƯỚC CÔNG DÂN Số / No.: 027090001234 Họ và tên / Full name: NGUYỄN VĂN AN " + "x" * 80,
    "|",
]
_BO_TACH = "\n".join(f"───── Trang {i}/10 ─────\n{body}" for i, body in enumerate(_TRANG_TACH, start=1))


def _bo_ho_so():
    import base64

    import fitz

    from app.process.schemas import FileItem

    with fitz.open() as doc:
        for _ in _TRANG_TACH:
            doc.new_page()
        data = "data:application/pdf;base64," + base64.b64encode(doc.tobytes()).decode()
    return [FileItem(name="ho-so-chung.pdf", type="application/pdf", dataUrl=data, role="")]


def _patch_tach(monkeypatch, calls: list[str], trang_dau=(1, 3, 5, 7, 9)):
    import json

    from app.pipelines.cap_lai_giay_chung_nhan_do_bi_mat_bac_ninh.attach import prompt
    from app.services import ocr

    def fake_ocr(files, *_a, **_k):
        async def _run():
            preset = ocr._preset_texts.get() or {}
            return [{"name": f["name"], "text": preset.get(f["dataUrl"], _BO_TACH)} for f in files]
        return _run()

    async def fake_chat(messages, *_a, **_k):
        calls.append(messages[0]["content"])
        if messages[0]["content"] == prompt.SPLIT_SYSTEM_PROMPT:
            return json.dumps({"tep": [{"fileIndex": 0, "trangDau": list(trang_dau)}]})
        n = len(json.loads(messages[1]["content"].split("\n", 1)[1].split("\n\n")[0]))
        if n == 1:  # không tách: cả tệp mở đầu bằng Đơn
            return json.dumps({"documents": [{"index": 0, "type": "application", "documentName": "Đơn đăng ký biến "
                                              "động Mẫu số 18"}]})
        return json.dumps({"documents": [
            {"index": 0, "type": "application", "documentName": "Đơn đăng ký biến động Mẫu số 18"},
            {"index": 1, "type": "other", "documentName": "Giấy xác nhận tình trạng hôn nhân"},
            {"index": 2, "type": "other", "documentName": "Bản cam kết"},
            {"index": 3, "type": "other", "documentName": "Đơn trình báo mất giấy chứng nhận"},
            {"index": 4, "type": "identity", "documentName": "Căn cước công dân"},
        ]})

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner.client, "chat", fake_chat)


def test_tach_giay_to_tep_chung_moi_giay_vao_dung_o(monkeypatch):
    from app.pipelines.cap_lai_giay_chung_nhan_do_bi_mat_bac_ninh import attach

    calls: list[str] = []
    _patch_tach(monkeypatch, calls)
    res = asyncio.run(attach.plan(_bo_ho_so(), {"splitDocuments": True}))

    rows = [(a["documentName"], a["target"], a["componentName"], a["sourceSegments"][0]["pageIndexes"])
            for a in res["attachments"]]
    assert rows == [
        ("Đơn đăng ký biến động Mẫu số 18", "existing", "TP-H05.000026", [0, 1]),
        ("Giấy xác nhận tình trạng hôn nhân", "supplementary", "", [2, 3]),
        ("Bản cam kết", "supplementary", "", [4, 5]),
        ("Đơn trình báo mất giấy chứng nhận", "supplementary", "", [6, 7]),
        ("Căn cước công dân", "supplementary", "", [8, 9]),
    ]
    # Dòng GCN TP-H05.000040 để trống: GCN đã mất, Đơn trình báo / Bản cam kết không vào đó.
    assert all(a["componentName"] != "TP-H05.000040" for a in res["attachments"])
    assert res["extracted"]["attachmentMode"] == "split_documents"
    assert [t["pages"] for t in res["extracted"]["tachGiayTo"]] == [[1, 2], [3, 4], [5, 6], [7, 8], [9, 10]]


def test_khong_bat_tach_thi_ca_tep_chung_vao_dong_don(monkeypatch):
    from app.pipelines.cap_lai_giay_chung_nhan_do_bi_mat_bac_ninh import attach
    from app.pipelines.cap_lai_giay_chung_nhan_do_bi_mat_bac_ninh.attach import prompt

    calls: list[str] = []
    _patch_tach(monkeypatch, calls)
    for options in ({}, {"splitDocuments": False}, {"splitDocuments": "true"},
                    {"splitDocuments": True, "supportsSourceSegments": False}):
        calls.clear()
        res = asyncio.run(attach.plan(_bo_ho_so(), options))
        assert prompt.SPLIT_SYSTEM_PROMPT not in calls
        assert [(a["componentName"], "sourceSegments" in a) for a in res["attachments"]] == [("TP-H05.000026", False)]


def test_registry_bat_tach_giay_to_ca_auto_fill_va_tro_ly():
    from app.channels.handfree.procedure_registry import get_procedure as get_tl
    from app.procedures.registry import get_procedure

    assert get_procedure(_KEY)["supportsSplitDocuments"] is True
    assert get_tl(_KEY)["supportsSplitDocuments"] is True


def test_prompt_phan_loai_tep_chung_vao_don_va_trinh_bao_khong_phai_gcn():
    assert "KỂ CẢ khi phía sau cùng tệp còn giấy khác" in SYSTEM_PROMPT
    assert "Đơn trình báo mất giấy chứng nhận, Bản cam kết" in SYSTEM_PROMPT


# ── Registry lõi + trợ lý ──

def test_registry_loi_va_link_ke_khai_cung_key():
    from app.procedures.ke_khai_links import KE_KHAI_LINKS
    from app.procedures.registry import PROCEDURES, get_attach_pipeline, get_pipeline, get_procedure

    proc = get_procedure(_KEY)
    assert proc["label"] == "[Tỉnh Bắc Ninh] Cấp lại Giấy chứng nhận do bị mất"
    assert proc["detect"] == {"urlScope": ["dichvucong.bacninh.gov.vn"],
                              "urlIncludes": ["maThuTucHanhChinh=1.115465"]}
    assert get_pipeline(_KEY) is not None and get_attach_pipeline(_KEY) is not None
    trung = [p["key"] for p in PROCEDURES
             if "maThuTucHanhChinh=1.115465" in ((p.get("detect") or {}).get("urlIncludes") or [])]
    assert trung == [_KEY]
    link = next(link for link in KE_KHAI_LINKS if link["key"] == _KEY)
    assert link["code"] == "1.115465" and link["label"].startswith("Bắc Ninh - ")


def test_tro_ly_co_the_bac_ninh_hoi_co_quan_va_khoi_uy_quyen():
    from app.channels.handfree.chat.field_review import registry
    from app.channels.handfree.procedure_registry import _HOAN_THIEN_THEO_TINH, get_procedure, procedure_code

    tl = get_procedure(_KEY)
    assert procedure_code(tl) == "1.115465"
    assert tl["provinceOnly"] == ["bacninh"]
    assert tl["agencyProvinceOnly"] is True and not tl.get("agencySoFirst")
    assert tl["samePageAttach"] is True and tl["bacNinhTabFlow"]
    # Cổng chọn sẵn chi nhánh không theo nơi có đất → trợ lý hỏi cơ quan tiếp nhận.
    assert tl["bacNinhAgencyAsk"] is True
    assert tl["bacNinhAuthorizedPerson"]["subjectOption"] == "Cá nhân khác là Công dân Việt Nam"
    assert tl["bacNinhAuthorizedAsk"] is True
    assert registry.get(_KEY) is not None
    assert _KEY in _HOAN_THIEN_THEO_TINH
