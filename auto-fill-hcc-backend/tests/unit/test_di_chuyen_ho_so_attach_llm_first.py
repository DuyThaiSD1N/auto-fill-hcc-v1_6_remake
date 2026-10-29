"""Đính kèm di chuyển hồ sơ người hưởng trợ cấp ưu đãi: LLM quyết định loại giấy, luật dò chữ chỉ dự phòng khi LLM không
trả lời cho tệp đó — không bao giờ đè LLM."""
from app.pipelines.di_chuyen_ho_so_nguoi_huong_tro_cap.attach.planner import build_plan_items


def _plan(texts, llm_types):
    files = [{"name": f"f{i}.pdf"} for i in range(len(texts))]
    ocr = [{"name": f"f{i}.pdf", "text": t} for i, t in enumerate(texts)]
    return build_plan_items(files, ocr, llm_types)


def test_llm_thang_luat_do_chu():
    # Luật dò chữ thấy "mẫu số 27" → đơn; LLM đọc cả tệp nói là CCCD → theo LLM.
    items, _, classified = _plan(["CĂN CƯỚC CÔNG DÂN ... ghi chú mẫu số 27"], {0: "cccd"})
    assert [(i["slotKey"], i["slotIndex"]) for i in items] == [("cccd", 0)]
    assert classified[0]["source"] == "llm"


def test_mat_sau_cccd_luat_bo_sot_thi_llm_van_dinh():
    items, _, _ = _plan(["Đặc điểm nhận dạng / Personal identification ... IDVNM"], {0: "cccd"})
    assert [i["slotKey"] for i in items] == ["cccd"]


def test_llm_noi_giay_nguon_khac_thi_bo_qua():
    items, warnings, classified = _plan(["PHIẾU BÁO DI CHUYỂN HỒ SƠ"], {0: "phieu_bao_di_chuyen"})
    assert items == [] and classified[0].get("skipped") and not warnings


def test_llm_khong_tra_loi_thi_moi_dung_luat_du_phong():
    items, _, classified = _plan(["ĐƠN ĐỀ NGHỊ di chuyển hồ sơ Mẫu số 27"], {})
    assert [(i["slotKey"], i["slotIndex"]) for i in items] == [("don_mau_27", 1)]
    assert classified[0]["source"] == "rule"


_GOP = (
    "───── Trang 1/3 ─────\nỦY BAN NHÂN DÂN PHƯỜNG AN BÌNH\nV/v di chuyển chế độ trợ cấp\nKính gửi: Sở Nội vụ\n"
    "───── Trang 2/3 ─────\nMẫu số 27\nCỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐƠN ĐỀ NGHỊ\nDi chuyển hồ sơ liệt sĩ\n"
    "CCCD số 001000000000\n"
    "───── Trang 3/3 ─────\nTỔ QUỐC GHI CÔNG\n"
)


def test_tep_gop_llm_noi_other_thi_do_tieu_de_tung_trang():
    items, warnings, classified = _plan([_GOP], {0: "other"})
    assert [(i["slotKey"], i["slotIndex"]) for i in items] == [("don_mau_27", 1)]
    assert classified[0]["source"] == "pages" and not warnings


def test_tep_mot_trang_llm_noi_giay_khac_khong_bi_do_trang():
    items, _, classified = _plan(["PHIẾU BÁO DI CHUYỂN HỒ SƠ ... theo Đơn đề nghị Mẫu số 27"], {0: "phieu_bao_di_chuyen"})
    assert items == [] and classified[0].get("skipped")


def test_tep_gop_co_cccd_khong_co_don():
    text = "───── Trang 1/2 ─────\nCÔNG VĂN\n───── Trang 2/2 ─────\nCĂN CƯỚC CÔNG DÂN\nCitizen Identity Card\n"
    items, _, _ = _plan([text], {0: "phieu_bao_di_chuyen"})
    assert [i["slotKey"] for i in items] == ["cccd"]


def _llm_tra(monkeypatch, raw):
    from app.pipelines.di_chuyen_ho_so_nguoi_huong_tro_cap.attach import planner

    async def _chat(*_a, **_k):
        return raw

    monkeypatch.setattr(planner.client, "chat", _chat)
    return planner


def test_llm_tra_moi_trang_mot_phan_tu_cho_mot_tep_thi_gop_lai(monkeypatch):
    planner = _llm_tra(
        monkeypatch,
        '{"documents":[{"index":0,"docType":"other"},{"index":1,"docType":"don_mau_27"},'
        '{"index":2,"docType":"to_quoc_ghi_cong"}]}',
    )
    import asyncio

    assert asyncio.run(planner._classify_with_llm([{"index": 0, "text": _GOP}])) == {0: "don_mau_27"}


def test_llm_tra_lech_index_khi_nhieu_tep_thi_bo_de_dung_luat(monkeypatch):
    planner = _llm_tra(
        monkeypatch,
        '{"documents":[{"index":0,"docType":"other"},{"index":1,"docType":"cccd"},{"index":2,"docType":"other"}]}',
    )
    import asyncio

    docs = [{"index": 0, "text": "a"}, {"index": 1, "text": "b"}]
    assert asyncio.run(planner._classify_with_llm(docs)) == {}


# ---- Chế độ tách (cài đặt "Có tách hồ sơ khi đính kèm") ----

_TRANG = (
    "UỶ BAN NHÂN DÂN PHƯỜNG AN BÌNH, công văn về việc di chuyển chế độ trợ cấp, kính gửi Sở Nội vụ",
    "Mẫu số 27 CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM ĐƠN ĐỀ NGHỊ Di chuyển hồ sơ liệt sĩ, họ và tên Trần Văn A",
    "Tôi xin cam đoan những nội dung trên là đúng sự thật. Người làm đơn ký và ghi rõ họ tên Trần Văn A",
    "(1)",
    "CĂN CƯỚC CÔNG DÂN Citizen Identity Card số định danh 001000000000 họ và tên Trần Văn A",
)
_TEXT_5 = "\n".join(f"───── Trang {n + 1}/5 ─────\n{t}" for n, t in enumerate(_TRANG))


def _plan_split(page_types):
    files = [{"name": "goc.pdf"}]
    ocr = [{"name": "goc.pdf", "text": _TEXT_5}]
    return build_plan_items(files, ocr, {}, {0: page_types})


def test_tach_moi_o_chi_nhan_dung_trang_cua_no_bo_trang_trang():
    items, warnings, classified = _plan_split(
        ["phieu_bao_di_chuyen", "don_mau_27", "don_mau_27", "don_mau_27", "cccd"])
    assert [(i["slotKey"], i["sourceSegments"]) for i in items] == [
        ("don_mau_27", [{"fileIndex": 0, "pageIndexes": [1, 2]}]),
        ("cccd", [{"fileIndex": 0, "pageIndexes": [4]}]),
    ]
    assert all(i["fileIndex"] == 0 and i["target"] == "fixed-slot" for i in items)
    assert not warnings
    assert classified[0]["tachGiayTo"] == [
        {"docType": "phieu_bao_di_chuyen", "pages": [1]},
        {"docType": "don_mau_27", "pages": [2, 3]},
        {"docType": "cccd", "pages": [5]},
    ]


def test_tach_cccd_va_ct07_cung_vao_o_cccd_thanh_hai_muc():
    items, _, _ = _plan_split(["xac_nhan_cu_tru", "don_mau_27", "don_mau_27", "don_mau_27", "cccd"])
    assert [(i["slotKey"], i["slotIndex"], i["sourceSegments"][0]["pageIndexes"]) for i in items] == [
        ("don_mau_27", 1, [1, 2]), ("cccd", 0, [4]), ("cccd", 0, [0]),
    ]


def test_tach_ca_tep_mot_loai_thi_chi_bo_trang_trang():
    items, _, _ = _plan_split(["don_mau_27"] * 5)
    assert [i["sourceSegments"][0]["pageIndexes"] for i in items] == [[0, 1, 2, 4]]


def test_tach_ca_tep_mot_loai_khong_trang_trang_thi_khong_cat():
    text = "\n".join(f"───── Trang {n + 1}/2 ─────\n{_TRANG[n + 1]}" for n in range(2))
    items, _, _ = build_plan_items([{"name": "don.pdf"}], [{"name": "don.pdf", "text": text}], {},
                                   {0: ["don_mau_27", "don_mau_27"]})
    assert len(items) == 1 and "sourceSegments" not in items[0]


def test_tach_chi_co_giay_nguon_khac_thi_bo_qua_khong_canh_bao():
    items, warnings, classified = _plan_split(["phieu_bao_di_chuyen", "ban_khai", "ban_khai", "ban_khai", "to_quoc_ghi_cong"])
    assert items == [] and not warnings and classified[0].get("skipped")


def test_tach_chi_khi_bat_cai_dat_va_extension_cat_duoc_trang():
    from app.pipelines.di_chuyen_ho_so_nguoi_huong_tro_cap.attach.planner import split_requested

    assert split_requested({"splitDocuments": True})
    assert not split_requested({"splitDocuments": True, "supportsSourceSegments": False})
    assert not split_requested({"splitDocuments": "true"}) and not split_requested(None)


def test_llm_xep_trang_lech_so_trang_thi_tep_do_dinh_nguyen(monkeypatch):
    planner = _llm_tra(monkeypatch, '{"tep":[{"fileIndex":0,"trang":["don_mau_27","cccd"]}]}')
    import asyncio

    pages = {0: list(_TRANG), 1: ["a", "b"]}
    assert asyncio.run(planner._classify_pages(pages)) == {}
