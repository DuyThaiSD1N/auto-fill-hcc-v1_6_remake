import json

from app.pipelines.bau_to_truong_to_hoa_giai.attach import planner
from app.process.schemas import FileItem
from app.procedures.ke_khai_links import with_ke_khai_detect_urls
from app.procedures.registry import get_attach_pipeline, get_procedure

_MAU_01 = (
    "Mẫu số 01 BIÊN BẢN VỀ KẾT QUẢ BIỂU QUYẾT BẦU HÒA GIẢI VIÊN TẠI CUỘC HỌP ĐẠI DIỆN CÁC HỘ GIA ĐÌNH "
    "Tổ bầu hòa giải viên gồm các thành viên sau đây: Nguyễn Văn An - Tổ trưởng"
)
_MAU_04 = (
    "Mẫu số 04 BIÊN BẢN VỀ KẾT QUẢ BIỂU QUYẾT BẦU TỔ TRƯỞNG TỔ HÒA GIẢI "
    "Số lượng hòa giải viên của tổ hòa giải: 05 Thành viên. Kết quả biểu quyết bầu Tổ trưởng tổ hòa giải như sau: "
    "01 Trần Văn Bình 05 100%"
)
_MAU_06 = (
    "Mẫu số 06 DANH SÁCH Đề nghị công nhận hòa giải viên Kính gửi: Chủ tịch Ủy ban nhân dân phường Mẫu Sơn "
    "Căn cứ kết quả bầu hòa giải viên (có biên bản gửi kèm), đề nghị ... quyết định công nhận hòa giải viên"
)
_MAU_07 = (
    "Mẫu số 07 GIẤY ĐỀ NGHỊ Công nhận tổ trưởng tổ hòa giải Kính gửi: Chủ tịch Ủy ban nhân dân phường Mẫu Sơn "
    "Căn cứ kết quả bầu tổ trưởng tổ hòa giải (có biên bản gửi kèm)"
)
_MAU_10 = "Mẫu số 10 TỔNG HỢP DANH SÁCH Hòa giải viên cơ sở Họ và tên Ngày, tháng năm sinh Trình độ văn hóa"


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


def _patch(monkeypatch, ocr_texts, llm_documents=None):
    calls = []

    async def fake_ocr_per_file(files):
        return [{"name": f["name"], "text": ocr_texts.get(f["name"], "")} for f in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        calls.append(messages)
        return json.dumps({"documents": llm_documents or []})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    return calls


async def test_hai_tep_gop_mau_xep_dung_hai_dong(monkeypatch):
    calls = _patch(monkeypatch, {
        "bien-ban.pdf": _MAU_01 + "\n" + _MAU_04,
        "danh-sach.pdf": _MAU_06 + "\n" + _MAU_07 + "\n" + _MAU_10,
    })

    res = await planner.plan([_file("bien-ban.pdf"), _file("danh-sach.pdf")], {}, None)
    items = res["attachments"]

    assert len(items) == 2
    assert items[0]["componentIndex"] == 1
    assert items[0]["target"] == "existing"
    assert items[0]["needsAddComponent"] is False
    assert items[0]["sourceFileIndexes"] == [0]
    assert items[0]["componentName"].startswith("Biên bản kiểm phiếu hoặc biên bản về kết quả biểu quyết")
    assert items[1]["componentIndex"] == 2
    assert items[1]["sourceFileIndexes"] == [1]
    assert items[1]["componentName"] == "Văn bản đề nghị công nhận tổ trưởng tổ hòa giải."
    assert res["errors"] == []
    # Hồ sơ đúng mẫu thì rule nhận hết, không gọi LLM.
    assert calls == []


async def test_tach_tung_mau_gop_theo_dong_va_mau_chinh_dung_dau(monkeypatch):
    _patch(monkeypatch, {
        "mau01.pdf": _MAU_01,
        "mau06.pdf": _MAU_06,
        "mau04.pdf": _MAU_04,
        "mau10.pdf": _MAU_10,
        "mau07.pdf": _MAU_07,
    })

    res = await planner.plan(
        [_file("mau01.pdf"), _file("mau06.pdf"), _file("mau04.pdf"), _file("mau10.pdf"), _file("mau07.pdf")],
        {},
        None,
    )
    items = res["attachments"]

    assert [item["componentIndex"] for item in items] == [1, 2]
    assert items[0]["sourceFileIndexes"] == [2, 0]
    assert items[0]["fileIndex"] == 2
    assert items[1]["sourceFileIndexes"] == [4, 1, 3]
    assert items[1]["fileIndex"] == 4


async def test_giay_de_nghi_nhac_bien_ban_gui_kem_khong_bi_nhan_la_bien_ban(monkeypatch):
    _patch(monkeypatch, {"de-nghi.pdf": _MAU_07})

    res = await planner.plan([_file("de-nghi.pdf")], {}, None)

    assert [item["componentIndex"] for item in res["attachments"]] == [2]
    assert any("dòng 1 để trống" in err for err in res["errors"])


async def test_mot_tep_gop_ca_hai_nhom_dinh_ca_hai_dong(monkeypatch):
    _patch(monkeypatch, {"tat-ca.pdf": _MAU_01 + _MAU_04 + _MAU_06 + _MAU_07 + _MAU_10})

    res = await planner.plan([_file("tat-ca.pdf")], {}, None)
    items = res["attachments"]

    assert [item["componentIndex"] for item in items] == [1, 2]
    assert items[0]["sourceFileIndexes"] == [0]
    assert items[1]["sourceFileIndexes"] == [0]
    assert items[0]["documentName"] != items[1]["documentName"]


async def test_tep_gop_khong_dinh_dong_1_khi_da_co_bien_ban_rieng(monkeypatch):
    _patch(monkeypatch, {
        "bien-ban.pdf": _MAU_04,
        "tat-ca.pdf": _MAU_01 + _MAU_07,
    })

    res = await planner.plan([_file("bien-ban.pdf"), _file("tat-ca.pdf")], {}, None)
    items = res["attachments"]

    assert items[0]["sourceFileIndexes"] == [0]
    assert items[1]["sourceFileIndexes"] == [1]


async def test_tai_lieu_la_bi_bo_qua_va_llm_fallback(monkeypatch):
    calls = _patch(
        monkeypatch,
        {
            "cccd.pdf": "CĂN CƯỚC CÔNG DÂN Số định danh cá nhân: 001200000000",
            "mo.pdf": "tổ hòa giải ... chữ mờ",
            "bien-ban.pdf": _MAU_04,
        },
        llm_documents=[
            {"index": 0, "type": "other", "title": "CCCD"},
            {"index": 1, "type": "proposal", "title": "Giấy đề nghị"},
        ],
    )

    res = await planner.plan([_file("cccd.pdf"), _file("mo.pdf"), _file("bien-ban.pdf")], {}, None)
    items = res["attachments"]

    assert len(calls) == 1
    assert res["extracted"]["llmDocuments"] == ["cccd.pdf", "mo.pdf"]
    assert [(item["componentIndex"], item["sourceFileIndexes"]) for item in items] == [(1, [2]), (2, [1])]
    assert any("cccd.pdf" in err and "bỏ qua" in err for err in res["errors"])
    assert not any(item["needsAddComponent"] for item in items)


def test_registry_attach_mode_va_detect():
    proc = get_procedure("bau-to-truong-to-hoa-giai")
    assert proc["mode"] == "attach"
    assert get_attach_pipeline("bau-to-truong-to-hoa-giai") is planner.plan

    public = with_ke_khai_detect_urls([proc])[0]
    url_includes = [u.lower() for u in public["detect"]["urlIncludes"]]
    assert "matthc=2.000950" in url_includes
    assert any("019d2bfd-95cf-74f7-8f8e-81c925ae839a" in u for u in url_includes)
