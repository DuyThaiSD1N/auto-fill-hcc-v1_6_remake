"""Hưởng trợ cấp khi người có công từ trần — hai chế độ người nộp. Chủ hồ sơ = người khai. Dữ liệu giả."""

from app.pipelines.uu_dai_ncc_tu_tran.process import mapper

_KHAI = {
    "ToKhai_HoTen": "NGUYỄN VĂN A",
    "ToKhai_SoDinhDanh": "001070000001",
    "ToKhai_NgaySinh": "02/03/1970",
    "ToKhai_GioiTinh": "Nam",
    "TuTran_HoTen": "NGUYỄN VĂN B",
    "TuTran_NgaySinh": "01/01/1940",
}
_TK_KHAC = {"formContext": {"applicantFullname": "Cán Bộ Một Cửa", "applicantIdentityNumber": "001099000009"}}
_TO_KHAI = {"submitterMode": "owner_as_submitter", **_TK_KHAC}


def _run(options, extra=None):
    values = dict(_KHAI, **(extra or {}))
    out, _ = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)
    return out, {(f["name"], f.get("occurrence")): f for f in out}


def test_to_khai_nguoi_nop_la_nguoi_khai_bo_khoa_2_o():
    out, d = _run(_TO_KHAI)
    assert d[("data[isOwnerDossierCheck]", None)]["value"] is True
    assert d[("data[fullname]", 0)]["value"] == "NGUYỄN VĂN A" and d[("data[fullname]", 0)]["enableInput"] is True
    assert d[("data[identityNumber]", None)]["value"] == "001070000001"
    assert d[("data[identityNumber]", None)]["enableInput"] is True
    assert d[("data[birthday]", 0)]["value"] == "02/03/1970"
    # Người từ trần (occ1) không bị bỏ khoá.
    assert "enableInput" not in d[("data[fullname]", 1)]


def test_to_khai_thieu_ngay_sinh_du_thi_xoa_va_danh_dau():
    _, d = _run(_TO_KHAI, {"ToKhai_NgaySinh": "1970"})
    assert d[("data[birthday]", 0)]["clear"] is True and d[("data[birthday]", 0)]["markEmpty"] is True
    assert d[("data[birthday]", 0)]["value"] == ""


def test_tai_khoan_la_nguoi_khac_thi_bo_trong_phan_i():
    out, d = _run(_TK_KHAC)
    assert d[("data[isOwnerDossierCheck]", None)]["value"] is False
    assert ("data[fullname]", 0) not in d
    assert not any(f.get("enableInput") for f in out)
    assert d[("data[ownerFullname]", None)]["value"] == "NGUYỄN VĂN A"


def test_tai_khoan_trung_nguoi_khai_thi_tich_khong_bo_khoa():
    out, d = _run({"formContext": {"applicantFullname": "Nguyễn Văn A", "applicantIdentityNumber": "001070000001"}})
    assert d[("data[isOwnerDossierCheck]", None)]["value"] is True
    assert d[("data[fullname]", 0)]["value"] == "NGUYỄN VĂN A"
    assert not any(f.get("enableInput") for f in out)


# ---- Đính kèm: cài đặt "Có tách hồ sơ khi đính kèm" (PDF gộp → mỗi giấy một tệp) ----

_TRANG = (
    "Mẫu số 12 CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM BẢN KHAI Để giải quyết chế độ ưu đãi khi người có công từ trần",
    "Số tài khoản tại ngân hàng, xác nhận của UBND cấp xã, phường. Người khai ký, ghi rõ họ và tên Nguyễn Văn A",
    "ỦY BAN NHÂN DÂN PHƯỜNG AN BÌNH GIẤY XÁC NHẬN Xác nhận ông Nguyễn Văn B đã từ trần, đề nghị Sở Nội vụ",
    "UBND PHƯỜNG AN BÌNH TRÍCH LỤC KHAI TỬ (BẢN SAO) Họ, chữ đệm, tên: NGUYỄN VĂN B, ngày chết 01/01/2026",
    "CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM BIÊN BẢN ỦY QUYỀN Căn cứ Bộ Luật dân sự, bên ủy quyền, bên được ủy quyền",
    "CĂN CƯỚC CÔNG DÂN Citizen Identity Card số định danh 001070000001 họ và tên Nguyễn Văn A",
    "Đặc điểm nhân dạng, ngày cấp, CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
)
_TEXT_7 = "\n".join(f"───── Trang {n + 1}/7 ─────\n{t}" for n, t in enumerate(_TRANG))
_LOAI_7 = ["ban_khai", "ban_khai", "giay_xac_nhan", "trich_luc_khai_tu", "giay_uy_quyen", "cccd", "cccd"]


def _plan_split(page_types, text=_TEXT_7):
    from app.pipelines.uu_dai_ncc_tu_tran.attach import planner

    return planner.build_plan_items([{"name": "goc.pdf"}], [{"name": "goc.pdf", "text": text}], {}, {0: page_types})


def test_tach_moi_giay_mot_tep_cung_vao_o_ban_khai():
    items, warnings, classified = _plan_split(_LOAI_7)
    assert [(i["documentName"], i["sourceSegments"][0]["pageIndexes"]) for i in items] == [
        ("Bản khai giải quyết chế độ ưu đãi khi người có công từ trần (Mẫu số 12)", [0, 1]),
        ("Giấy xác nhận của UBND cấp xã", [2]),
        ("Trích lục khai tử/giấy báo tử", [3]),
        ("Giấy ủy quyền", [4]),
        ("Căn cước công dân", [5, 6]),
    ]
    assert {(i["slotKey"], i["slotIndex"], i["target"], i["fileIndex"]) for i in items} == {
        ("ban_khai", 0, "fixed-slot", 0)}
    assert not warnings
    assert classified[0]["source"] == "llm-pages"
    assert classified[0]["tachGiayTo"][0] == {"docType": "ban_khai", "pages": [1, 2]}


def test_tach_ban_khai_luon_dung_dau_bo_trang_trang():
    trang = ("CĂN CƯỚC CÔNG DÂN Citizen Identity Card số định danh 001070000001 họ và tên Nguyễn Văn A", "(1)",
             _TRANG[0], _TRANG[1])
    text = "\n".join(f"───── Trang {n + 1}/4 ─────\n{t}" for n, t in enumerate(trang))
    items, _, _ = _plan_split(["cccd", "cccd", "ban_khai", "ban_khai"], text)
    assert [(i["detectedType"], i["sourceSegments"][0]["pageIndexes"]) for i in items] == [
        ("Bản khai Mẫu số 12", [2, 3]), ("Căn cước công dân", [0]),
    ]


def test_tach_ca_tep_mot_giay_khong_trang_trang_thi_khong_cat():
    text = "\n".join(f"───── Trang {n + 1}/2 ─────\n{_TRANG[n]}" for n in range(2))
    items, _, _ = _plan_split(["ban_khai", "ban_khai"], text)
    assert len(items) == 1 and "sourceSegments" not in items[0]


def test_tach_trang_chua_ro_loai_van_dinh_va_canh_bao():
    items, warnings, _ = _plan_split(["ban_khai", "ban_khai", "other", "other", "other", "cccd", "cccd"])
    assert [i["documentName"] for i in items][1] == "Giấy tờ kèm theo"
    assert len(warnings) == 1


def test_bien_ban_uy_quyen_khong_phai_bien_ban_hop():
    from app.pipelines.uu_dai_ncc_tu_tran.attach import planner

    assert planner._normalize_doc_type("Biên bản ủy quyền") == "giay_uy_quyen"
    assert planner._normalize_doc_type("Biên bản họp gia đình") == "bien_ban_hop"
    assert planner._normalize_doc_type("giay_xac_nhan") == "giay_xac_nhan"


def _plan_e2e(monkeypatch, options):
    import asyncio

    from app.pipelines.uu_dai_ncc_tu_tran.attach import planner
    from app.process.schemas import FileItem
    from app.services import ocr

    async def _ocr(files, **_k):
        return [{"name": f["name"], "text": _TEXT_7} for f in files]

    calls = []

    async def _chat(messages, **_k):
        calls.append(messages[0]["content"])
        return '{"tep":[{"fileIndex":0,"trang":%s}]}' % str(_LOAI_7).replace("'", '"')

    monkeypatch.setattr(ocr, "ocr_per_file", _ocr)
    monkeypatch.setattr(planner.client, "chat", _chat)
    monkeypatch.setattr(planner, "splittable_pages", lambda _f, text: planner.split_pages(text))
    files = [FileItem(name="goc.pdf", type="application/pdf", role="", dataUrl="data:application/pdf;base64,AA==")]
    return asyncio.run(planner.plan(files, options)), calls


def test_bat_cai_dat_thi_xep_trang_ca_tep_khop_luat_ban_khai(monkeypatch):
    result, calls = _plan_e2e(monkeypatch, {"splitDocuments": True, "supportsSourceSegments": True})
    assert len(calls) == 1 and "TỪNG TRANG" in calls[0]
    assert len(result["attachments"]) == 5 and result["extracted"]["splitDocuments"] is True


def test_tat_cai_dat_thi_dinh_nguyen_tep_khong_goi_llm(monkeypatch):
    result, calls = _plan_e2e(monkeypatch, {"splitDocuments": False})
    assert calls == []
    assert len(result["attachments"]) == 1 and "sourceSegments" not in result["attachments"][0]
    assert result["extracted"]["splitDocuments"] is False


def test_registry_cong_bo_ho_tro_tach():
    from app.channels.handfree.procedure_registry import get_procedure as hf_get
    from app.procedures.registry import get_procedure

    assert get_procedure("uu-dai-ncc-tu-tran")["supportsSplitDocuments"] is True
    assert hf_get("uu-dai-ncc-tu-tran")["supportsSplitDocuments"] is True
