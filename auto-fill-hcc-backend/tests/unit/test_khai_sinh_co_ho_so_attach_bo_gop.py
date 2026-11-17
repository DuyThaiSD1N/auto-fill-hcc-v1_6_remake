"""Đăng ký khai sinh cho người đã có hồ sơ: file gộp nhiều giấy tờ không bị đặt tên như một tấm CCCD."""
import asyncio
import json

from app.pipelines.khai_sinh_co_ho_so import attach
from app.pipelines.khai_sinh_co_ho_so.attach import planner, prompt
from app.process.schemas import FileItem
from app.services import ocr

_BUNDLE = "\n".join(
    f"───── Trang {i}/8 ─────\n{body}" for i, body in enumerate(
        ["CĂN CƯỚC Họ, chữ đệm và tên khai sinh / Full name: PHẠM THỊ AN Ngày, tháng, năm sinh: 01/01/1960 " + "x" * 600,
         "CHỨNG NHẬN KẾT HÔN", "CĂN CƯỚC CÔNG DÂN VÕ VĂN B", "CĂN CƯỚC CÔNG DÂN PHẠM C",
         "CĂN CƯỚC CÔNG DÂN NGUYỄN THỊ D", "CHỨNG NHẬN KẾT HÔN", "CĂN CƯỚC", "MRZ"], start=1))


def test_rut_gon_giu_dau_moi_trang():
    short = prompt._truncate_text(_BUNDLE, limit=1600)
    assert all(f"Trang {i}/8" in short for i in range(1, 9))
    assert "NGUYỄN THỊ D" in short


def test_bo_gop_khong_gan_ten_nguoi(monkeypatch):
    async def fake_ocr(files, *_a, **_k):
        return [{"name": f["name"], "text": _BUNDLE} for f in files]

    async def fake_chat(*_a, **_k):
        return json.dumps({"documents": [{"index": 0, "type": "personal_document", "title": "Hồ sơ giấy tờ cá nhân"}]})

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    res = asyncio.run(attach.plan([FileItem(name="ho-so.pdf", type="application/pdf", dataUrl="data:,", role="")], {}))
    assert res["attachments"][0]["documentName"] == "Hồ sơ giấy tờ cá nhân"


# ---- Cài đặt "Tách giấy tờ": tệp gộp chia theo trang, mỗi giấy vào đúng dòng ----

_TRANG_TACH = [
    "BẢN CAM ĐOAN về việc chưa được đăng ký khai sinh. Tôi cam đoan người con chưa được đăng ký khai sinh " + "x" * 80,
    "CĂN CƯỚC CÔNG DÂN Họ và tên / Full name: TRẦN VĂN CON Ngày sinh: 15/10/2000 " + "x" * 80,
    "GIẤY ỦY QUYỀN thực hiện việc đăng ký khai sinh, bên ủy quyền LÊ VĂN NỘP " + "x" * 80,
]
_BO_TACH = "\n".join(f"───── Trang {i}/3 ─────\n{body}" for i, body in enumerate(_TRANG_TACH, start=1))


def _pdf_ba_trang() -> str:
    import base64

    import fitz

    with fitz.open() as doc:
        for _ in _TRANG_TACH:
            doc.new_page()
        return "data:application/pdf;base64," + base64.b64encode(doc.tobytes()).decode()


def _fake_ocr_theo_preset(files, *_a, **_k):
    async def _run():
        preset = ocr._preset_texts.get() or {}
        return [{"name": f["name"], "text": preset.get(f["dataUrl"], _BO_TACH)} for f in files]
    return _run()


def _fake_chat_tach(calls):
    async def fake_chat(messages, *_a, **_k):
        calls.append(messages[0]["content"])
        if messages[0]["content"] == prompt.SPLIT_SYSTEM_PROMPT:
            return json.dumps({"tep": [{"fileIndex": 0, "trangDau": [1, 2, 3]}]})
        return json.dumps({"documents": [
            {"index": 0, "type": "commitment", "title": "Bản cam đoan"},
            {"index": 1, "type": "personal_document", "title": "Căn cước công dân"},
            {"index": 2, "type": "authorization", "title": "Văn bản ủy quyền"},
        ]})
    return fake_chat


def test_tach_giay_to_moi_giay_vao_dung_dong(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(ocr, "ocr_per_file", _fake_ocr_theo_preset)
    monkeypatch.setattr(planner.client, "chat", _fake_chat_tach(calls))
    files = [FileItem(name="bo-ho-so.pdf", type="application/pdf", dataUrl=_pdf_ba_trang(), role="")]
    res = asyncio.run(attach.plan(files, {"splitDocuments": True, "supportsSourceSegments": True}))

    rows = [(a["componentIndex"], a["fileIndex"], a["sourceSegments"]) for a in res["attachments"]]
    assert rows == [
        (2, 0, [{"fileIndex": 0, "pageIndexes": [0]}]),
        (3, 0, [{"fileIndex": 0, "pageIndexes": [1]}]),
        (5, 0, [{"fileIndex": 0, "pageIndexes": [2]}]),
    ]
    assert res["extracted"]["attachmentMode"] == "split_documents"
    assert [c["pageFrom"] for c in res["extracted"]["classified"]] == [1, 2, 3]
    assert {c["fileName"] for c in res["extracted"]["classified"]} == {"bo-ho-so.pdf"}


def test_khong_bat_tach_thi_giu_nguyen_tep(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(ocr, "ocr_per_file", _fake_ocr_theo_preset)
    monkeypatch.setattr(planner.client, "chat", _fake_chat_tach(calls))
    files = [FileItem(name="bo-ho-so.pdf", type="application/pdf", dataUrl=_pdf_ba_trang(), role="")]
    # Extension cũ không cắt được trang → không tách dù bật cài đặt.
    for options in ({}, {"splitDocuments": "true"}, {"splitDocuments": True, "supportsSourceSegments": False}):
        calls.clear()
        res = asyncio.run(attach.plan(files, options))
        assert prompt.SPLIT_SYSTEM_PROMPT not in calls
        assert all("sourceSegments" not in a for a in res["attachments"])


def test_tach_giay_to_loi_llm_dinh_nguyen_tep(monkeypatch):
    async def fake_chat(messages, *_a, **_k):
        if messages[0]["content"] == prompt.SPLIT_SYSTEM_PROMPT:
            return "không phải JSON"
        return json.dumps({"documents": [{"index": 0, "type": "personal_document", "title": "Hồ sơ giấy tờ cá nhân"}]})

    monkeypatch.setattr(ocr, "ocr_per_file", _fake_ocr_theo_preset)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [FileItem(name="bo-ho-so.pdf", type="application/pdf", dataUrl=_pdf_ba_trang(), role="")]
    res = asyncio.run(attach.plan(files, {"splitDocuments": True, "supportsSourceSegments": True}))
    assert len(res["attachments"]) == 1 and "sourceSegments" not in res["attachments"][0]
    assert res["attachments"][0]["componentIndex"] == 3


def _plan_ten_trung(monkeypatch, docs, options):
    """Ba trang, LLM đặt tên theo ``docs``; trả documentName/componentName của kế hoạch và classified."""
    async def fake_chat(messages, *_a, **_k):
        if messages[0]["content"] == prompt.SPLIT_SYSTEM_PROMPT:
            return json.dumps({"tep": [{"fileIndex": 0, "trangDau": [1, 2, 3]}]})
        return json.dumps({"documents": docs})

    monkeypatch.setattr(ocr, "ocr_per_file", _fake_ocr_theo_preset)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [FileItem(name="bo-ho-so.pdf", type="application/pdf", dataUrl=_pdf_ba_trang(), role="")]
    return asyncio.run(attach.plan(files, options))


def test_tach_giay_to_ten_trung_danh_so_tu_1(monkeypatch):
    docs = [
        {"index": 0, "type": "commitment", "title": "Bản cam đoan"},
        {"index": 1, "type": "personal_document", "title": "Giấy chứng nhận kết hôn"},
        {"index": 2, "type": "personal_document", "title": "Giấy chứng nhận kết hôn"},
    ]
    res = _plan_ten_trung(monkeypatch, docs, {"splitDocuments": True, "supportsSourceSegments": True})
    names = [a["documentName"] for a in res["attachments"]]
    assert names == ["Bản cam đoan", "Giấy chứng nhận kết hôn 1", "Giấy chứng nhận kết hôn 2"]
    assert [a["detectedType"] for a in res["attachments"]] == names
    assert [c["documentName"] for c in res["extracted"]["classified"]] == names
    assert all("_ten_goc" not in a for a in res["attachments"])

    # Thành phần mới (tờ khai giấy): tên dòng mới cũng phải đánh số theo, không thì cổng coi là "đã có".
    docs = [
        {"index": 0, "type": "paper_declaration", "title": ""},
        {"index": 1, "type": "paper_declaration", "title": ""},
        {"index": 2, "type": "commitment", "title": "Bản cam đoan"},
    ]
    res = _plan_ten_trung(monkeypatch, docs, {"splitDocuments": True, "supportsSourceSegments": True})
    moi = [(a["documentName"], a["componentName"]) for a in res["attachments"] if a["target"] == "new"]
    assert moi == [("Tờ khai đăng ký 1", "Tờ khai đăng ký 1"), ("Tờ khai đăng ký 2", "Tờ khai đăng ký 2")]


def test_khong_tach_ten_trung_giu_cach_dat_cu(monkeypatch):
    async def fake_chat(*_a, **_k):
        return json.dumps({"documents": [
            {"index": 0, "type": "personal_document", "title": "Giấy chứng nhận kết hôn"},
            {"index": 1, "type": "personal_document", "title": "Giấy chứng nhận kết hôn"},
        ]})

    async def fake_ocr(files, *_a, **_k):
        return [{"name": f["name"], "text": "GIẤY CHỨNG NHẬN KẾT HÔN"} for f in files]

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [FileItem(name=f"kh{i}.pdf", type="application/pdf", dataUrl=f"data:,{i}", role="") for i in (1, 2)]
    res = asyncio.run(attach.plan(files, {}))
    assert [a["documentName"] for a in res["attachments"]] == ["Giấy chứng nhận kết hôn", "Giấy chứng nhận kết hôn 2"]


def test_registry_bat_tach_giay_to():
    from app.channels.handfree.procedure_registry import get_procedure as hf_get
    from app.procedures.registry import get_procedure

    assert get_procedure("khai-sinh-da-co-ho-so")["supportsSplitDocuments"] is True
    assert hf_get("khai-sinh-da-co-ho-so")["supportsSplitDocuments"] is True


# ---- Bước điền (process/mapper): người nộp hộ kèm CCCD của tài khoản, loại khai sinh, xoá ô cha/mẹ trống ----

from app.pipelines.khai_sinh_co_ho_so.process import mapper  # noqa: E402
from app.pipelines.khai_sinh_co_ho_so.process import reason as co_ho_so_reason  # noqa: E402

_ACCOUNT = {"formContext": {"applicantFullname": "LÊ VĂN NỘP", "applicantIdentityNumber": "001204000003"}}
_HO_SO = {
    "Subject_FullName": "TRẦN VĂN CON", "Subject_BirthDate": "15/10/2026", "Subject_Gender": "Nam",
    "Father_FullName": "TRẦN VĂN CHA", "Father_IdNumber": "024091000002", "Father_IdIssueDate": "20/12/2024",
    "Father_BirthDateOrYear": "29/11/1991", "Father_Ethnicity": "Kinh",
    "Mother_FullName": "HOÀNG THỊ MẸ", "Mother_BirthDateOrYear": "21/09/2000", "Mother_Ethnicity": "Kinh",
}
_THE_TAI_KHOAN = {
    "AccountCard_IdNumber": "001204000003", "AccountCard_FullName": "LÊ VĂN NỘP",
    "AccountCard_IdIssueDate": "10/04/2021",
    "AccountCard_ResidenceDomestic": {"quocGia": "Việt Nam", "tinh": "Lào Cai", "xa": "Phường Yên Bái",
                                      "diaChi": "Tổ 1"},
}


def _enrich(values, options=None):
    fields = [{"name": k, "comp": "x-input", "value": v} for k, v in values.items()]
    return {f["name"]: f for f in mapper.enrich(fields, options)}


def test_loai_khai_sinh_la_x_select_va_theo_cha_me():
    out = _enrich(_HO_SO)
    assert out["nksLoaiKhaiSinh"]["comp"] == "x-select"
    assert out["nksLoaiKhaiSinh"]["value"] == "Đã xác định được cả cha lẫn mẹ"
    khong_cha = {k: v for k, v in _HO_SO.items() if not k.startswith("Father_")}
    assert _enrich(khong_cha)["nksLoaiKhaiSinh"]["value"] == "Chưa xác định được cha"


def test_cccd_tai_khoan_dien_noi_cu_tru_muc_i_giu_nhan_than_vneid():
    out = _enrich({**_HO_SO, **_THE_TAI_KHOAN}, _ACCOUNT)
    assert out["QuanHe"]["value"] == "Khac" and not out["QuanHe"].get("default")
    assert out["nycLoaiCuTru"]["value"] == "Thường trú"
    assert out["nycNoiCuTru"]["value"] == "1"
    assert out["nycNoiCuTru_TrongNuoc"]["value"]["diaChi"] == "Tổ 1"
    # Họ tên/số/ngày cấp/nơi cấp: cổng đã đổ từ VNeID của chính người này → không ghi đè bằng OCR.
    assert not {"HoVaTenC", "SoDinhDanhC", "NgayCapDDC", "NoiCapDDC"} & set(out)


def test_cccd_khong_trung_so_tai_khoan_khong_dien_muc_i():
    lech = {**_THE_TAI_KHOAN, "AccountCard_IdNumber": "001204999999"}
    out = _enrich({**_HO_SO, **lech}, _ACCOUNT)
    assert out["QuanHe"]["value"] == "Khac" and out["QuanHe"].get("default")
    assert "nycNoiCuTru_TrongNuoc" not in out
    assert "nycNoiCuTru_TrongNuoc" not in _enrich({**_HO_SO, **_THE_TAI_KHOAN})


def test_cccd_tai_khoan_trung_cha_tich_cha():
    the_cha = {**_THE_TAI_KHOAN, "AccountCard_IdNumber": "024091000002"}
    account = {"formContext": {"applicantFullname": "TRẦN VĂN CHA", "applicantIdentityNumber": "024091000002"}}
    assert _enrich({**_HO_SO, **the_cha}, account)["QuanHe"]["value"] == "ChaDe"


def test_cha_me_thieu_truong_thi_xoa_trang():
    out = _enrich(_HO_SO)
    for name in ("SoDinhDanhMe", "SoGiayToDinhDanhMe", "NgayCapDDMe", "NoiCapDDMe"):
        assert out[name]["clear"] is True and out[name]["value"] == ""
    assert out["HoTenMeKS"]["value"] == "HOÀNG THỊ MẸ" and not out["HoTenMeKS"].get("clear")
    # Cha có thẻ: ô nào có dữ liệu thì điền, nơi cấp suy mặc định theo ngày cấp → không bị xoá.
    assert out["SoDinhDanhCha"]["value"] == "024091000002"
    assert not out["NoiCapDDCha"].get("clear")
    assert not any(f.get("clear") for n, f in out.items() if n.endswith("Cha") or n.endswith("ChaKS"))


def test_context_ghim_so_dinh_danh_tai_khoan():
    raw = "<con>\nHọ tên: TRẦN VĂN CON\nNgày sinh: 15/10/2026\nGiới tính: Nam\n</con>"
    docs = [{"name": "ks.pdf", "text": "GIẤY KHAI SINH\nHọ, chữ đệm, tên: TRẦN VĂN CON"}]
    context = co_ho_so_reason._render_context(raw, _ACCOUNT, docs)
    assert "<tai_khoan_dang_nhap>" in context and "001204000003" in context
    assert "<tai_khoan_dang_nhap>" not in co_ho_so_reason._render_context(raw, {}, docs)


# Hồ sơ CHỈ có tờ khai (không CCCD nào), cha ghi "Nơi cư trú: (chết)": agent trích xuất bỏ sót cả vai
# cha thì vẫn phải dựng lại cha theo tờ khai, nơi cư trú "Đã chết", không rơi về "Chưa xác định được cha".
_TO_KHAI_CHA_CHET = "\n".join([
    "TỜ KHAI ĐĂNG KÝ KHAI SINH",
    "Họ, chữ đệm, tên người yêu cầu: TRẦN VĂN NAM",
    "Quan hệ với người được khai sinh: Bản thân",
    "Đề nghị cơ quan đăng ký khai sinh cho người dưới đây:",
    "Họ, chữ đệm, tên: TRẦN VĂN NAM",
    "Ngày, tháng, năm sinh: 02/03/1970",
    "Họ, chữ đệm, tên người mẹ: LÊ THỊ HOA",
    "Năm sinh: (5) 1940 Dân tộc: (2) Quốc tịch: (2)",
    "Nơi cư trú: (2) (Chết)",
    "Họ, chữ đệm, tên người cha: TRẦN VĂN BA",
    "Năm sinh: (5) Dân tộc: (2) Quốc tịch: (2)",
    "Nơi cư trú: (2) (chết)",
    "Giấy tờ tùy thân: (3)",
    "Tôi cam đoan nội dung đề nghị đăng ký khai sinh trên đây là đúng sự thật",
])


def test_chi_co_to_khai_cha_da_chet_bi_bo_sot_van_dung_lai_cha():
    raw = (
        "<con>\nHọ tên: TRẦN VĂN NAM\nNgày sinh: 02/03/1970\nGiới tính: Nam\nTrạng thái: còn sống\n</con>\n"
        "<me>\nHọ tên: LÊ THỊ HOA\nNgày sinh: 1940\nGiới tính: Nữ\nTrạng thái: đã chết\n</me>\n"
        "<cha>\nHọ tên: TRẦN VĂN BA\nGiới tính: Nam\nTrạng thái: không xác định\n</cha>"
    )
    context = co_ho_so_reason._render_context(raw, {}, [{"name": "tk.pdf", "text": _TO_KHAI_CHA_CHET}])
    cha = co_ho_so_reason._section(context, "cha")
    assert "Trạng thái: đã chết" in cha and "Đối chiếu CCCD:" in cha

    # Agent trích xuất trả mẹ nhưng bỏ sót toàn bộ Father_*.
    extracted = [
        {"name": "Subject_FullName", "comp": "x-input", "value": "TRẦN VĂN NAM"},
        {"name": "Mother_FullName", "comp": "x-input", "value": "LÊ THỊ HOA"},
        {"name": "Mother_BirthDateOrYear", "comp": "x-input", "value": "1940"},
    ]
    fields = co_ho_so_reason.sanitize_extracted_fields(extracted, context)
    father = {f["name"]: f for f in fields if f["name"].startswith("Father_")}
    assert father["Father_FullName"]["value"] == "TRẦN VĂN BA" and father["Father_FullName"].get("default")

    ui = {f["name"]: f["value"] for f in mapper.enrich(fields, {"_reasoning_context": context})}
    assert ui["HoTenChaKS"] == "TRẦN VĂN BA"
    assert ui["ChaNoiCuTru"] == "Khác" and ui["ChaNoiCuTru_NuocNgoai"] == "Đã chết"
    assert ui["nksLoaiKhaiSinh"] == "Đã xác định được cả cha lẫn mẹ"


# Thẻ cha + thẻ mẹ scan chung MỘT trang; tờ khai ghi số mẹ ở "Giấy tờ tùy thân: (3) <số>" và viết sai năm
# sinh mẹ (1965, thẻ 1945 → chỉ cách con 10 năm). Trước đây Python chỉ đọc thẻ đầu trang, không đọc số
# trên dòng "Giấy tờ tùy thân" → khối mẹ giữ năm tờ khai, bị xoá vì sai thế hệ, form ra "Chưa xác định được mẹ".
def _mat_truoc(so, ten, ngay_sinh, gioi_tinh):
    return "\n".join([
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
        "Độc lập - Tự do - Hạnh phúc",
        "CĂN CƯỚC CÔNG DÂN",
        "Citizen Identity Card",
        f"Số / No.: {so}",
        "Họ và tên / Full name:",
        ten,
        f"Ngày sinh / Date of birth: {ngay_sinh}",
        f"Giới tính / Sex: {gioi_tinh} Quốc tịch / Nationality: Việt Nam",
        "Có giá trị đến:",
        "Không thời hạn",
    ])


_HO_SO_HAI_THE_MOT_TRANG = "\n".join([
    "───── Trang 1/2 ─────",
    _mat_truoc("001045000001", "PHẠM VĂN AN", "10/10/1945", "Nam"),
    "",
    _mat_truoc("001145000002", "ĐỖ THỊ BÌNH", "03/03/1945", "Nữ"),
    "",
    "───── Trang 2/2 ─────",
    "Đặc điểm nhận dạng / Personal identification:",
    "Ngày, tháng, năm / Date, month, year: 01/01/2021",
    "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
])

_TO_KHAI_ME_SAI_NAM = "\n".join([
    "TỜ KHAI ĐĂNG KÝ KHAI SINH",
    "Họ, chữ đệm, tên người yêu cầu: PHẠM VĂN CƯỜNG",
    "Quan hệ với người được khai sinh:",
    "Đề nghị cơ quan đăng ký khai sinh cho người dưới đây:",
    "Họ, chữ đệm, tên: PHẠM VĂN CƯỜNG",
    "Ngày, tháng, năm sinh: 05/05/1975",
    "Giới tính: Nam Dân tộc: Kinh Quốc tịch: Việt Nam",
    "Họ, chữ đệm, tên người mẹ: Đỗ Thị Bình",
    "Ngày, tháng, năm sinh: (5) 03/03/1965 Dân tộc: (2) Kinh Quốc tịch: (2) Việt Nam",
    "Nơi cư trú: (2) Thôn 1 xã Hòa Bình",
    "Giấy tờ tùy thân: (3) 001145000002",
    "Họ, chữ đệm, tên người cha: Phạm Văn An",
    "Ngày, tháng, năm sinh: (5) 10/10/1945 Dân tộc: (2) Kinh Quốc tịch: (2) Việt Nam",
    "Nơi cư trú: (2) Đã chết",
    "Giấy tờ tùy thân: (3)",
    "Tôi cam đoan nội dung đề nghị đăng ký khai sinh trên đây là đúng sự thật",
])


def test_the_me_chung_trang_the_cha_va_to_khai_sai_nam_van_dien_me():
    docs = [
        {"name": "ho-so.pdf", "text": _HO_SO_HAI_THE_MOT_TRANG},
        {"name": "tk.pdf", "text": _TO_KHAI_ME_SAI_NAM},
    ]
    cards = [
        person["id"]
        for unit in co_ho_so_reason._identity_units(docs)
        if co_ho_so_reason._is_card_unit(unit) and (person := co_ho_so_reason._person_from_document(unit))
    ]
    assert cards == ["001045000001", "001145000002"]

    raw = (
        "<con>\nHọ tên: PHẠM VĂN CƯỜNG\nNgày sinh: 05/05/1975\nGiới tính: Nam\nTrạng thái: còn sống\n</con>\n"
        "<me>\nHọ tên: ĐỖ THỊ BÌNH\nSố CCCD/CMND: 001145000002\nNgày sinh: 03/03/1945\nGiới tính: Nữ\n</me>\n"
        "<cha>\nHọ tên: PHẠM VĂN AN\nNgày sinh: 10/10/1945\nGiới tính: Nam\nTrạng thái: đã chết\n</cha>"
    )
    context = co_ho_so_reason._render_context(raw, {}, docs)
    me = co_ho_so_reason._section(context, "me")
    assert "Số CCCD/CMND: 001145000002" in me and "Ngày sinh: 03/03/1945" in me
    assert "Đối chiếu CCCD trùng số" in me

    extracted = [
        {"name": "Subject_FullName", "comp": "x-input", "value": "PHẠM VĂN CƯỜNG"},
        {"name": "Mother_FullName", "comp": "x-input", "value": "Đỗ Thị Bình"},
        {"name": "Mother_IdNumber", "comp": "x-input", "value": "001145000002"},
        {"name": "Mother_BirthDateOrYear", "comp": "x-input", "value": "03/03/1965"},
        {"name": "Father_FullName", "comp": "x-input", "value": "PHẠM VĂN AN"},
    ]
    fields = co_ho_so_reason.sanitize_extracted_fields(extracted, context)
    ui = {f["name"]: f["value"] for f in mapper.enrich(fields, {"_reasoning_context": context})}
    assert ui["HoTenMeKS"] == "ĐỖ THỊ BÌNH" and ui["SoDinhDanhMe"] == "001145000002"
    assert ui["NamSinhMeKS"] == "03/03/1945"
    assert ui["nksLoaiKhaiSinh"] == "Đã xác định được cả cha lẫn mẹ"


# Tờ khai để trống dân tộc cha/mẹ ("Dân tộc: (2) Quốc tịch: (2)"), LLM chép "Kinh" của con sang: không gửi gì
# cho DanTocMeKS/DanTocChaKS — kể cả lệnh clear, vì mở dropdown dân tộc là cổng tự chọn "Kinh" đầu danh sách.
def test_dan_toc_cha_me_de_trong_tren_to_khai_thi_khong_cham_o():
    raw = (
        "<con>\nHọ tên: TRẦN VĂN NAM\nNgày sinh: 02/03/1970\nGiới tính: Nam\nDân tộc: Kinh\n</con>\n"
        "<me>\nHọ tên: LÊ THỊ HOA\nNgày sinh: 1940\nGiới tính: Nữ\nDân tộc: Kinh\nTrạng thái: đã chết\n</me>\n"
        "<cha>\nHọ tên: TRẦN VĂN BA\nGiới tính: Nam\nDân tộc: Kinh\nTrạng thái: đã chết\n</cha>"
    )
    context = co_ho_so_reason._render_context(raw, {}, [{"name": "tk.pdf", "text": _TO_KHAI_CHA_CHET}])
    assert "Dân tộc: Kinh" not in co_ho_so_reason._section(context, "me")
    assert "Dân tộc: Kinh" not in co_ho_so_reason._section(context, "cha")

    extracted = [
        {"name": "Subject_FullName", "comp": "x-input", "value": "TRẦN VĂN NAM"},
        {"name": "Mother_FullName", "comp": "x-input", "value": "LÊ THỊ HOA"},
        {"name": "Mother_Ethnicity", "comp": "x-input", "value": "Kinh"},
        {"name": "Father_FullName", "comp": "x-input", "value": "TRẦN VĂN BA"},
        {"name": "Father_Ethnicity", "comp": "x-input", "value": "Kinh"},
    ]
    fields = co_ho_so_reason.sanitize_extracted_fields(extracted, context)
    names = {f["name"] for f in mapper.enrich(fields, {"_reasoning_context": context})}
    assert "HoTenMeKS" in names and "HoTenChaKS" in names
    assert "DanTocMeKS" not in names and "DanTocChaKS" not in names
