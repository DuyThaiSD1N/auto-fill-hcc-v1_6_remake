"""Đăng ký khai sinh kết hợp đăng ký nhận cha, mẹ, con — chế độ TÁCH giấy tờ: một tệp quét gộp cả hồ sơ được chia trang
bằng một lượt LLM, mỗi giấy xếp dòng đúng luật chế độ không tách (STT3 giấy chứng sinh, STT4 xác nhận quan hệ, còn lại
thêm dòng mới, gộp hai mặt CCCD cùng người), trỏ về tệp gốc bằng sourceSegments."""
import json

from app.pipelines.khai_sinh_ket_hop_nhan_cmc.attach import planner as dispatcher
from app.pipelines.khai_sinh_ket_hop_nhan_cmc.attach.dinh_kem_tach import planner as split
from app.process.schemas import FileItem

_DECL_KS = "TỜ KHAI ĐĂNG KÝ KHAI SINH\nkèm theo Giấy chứng sinh số 001"
_DECL_CMC = "TỜ KHAI ĐĂNG KÝ NHẬN CHA, MẸ, CON\nTôi cam đoan việc nhận cha con nói trên là đúng sự thật"
_NOTE = "Chú thích: ghi theo hướng dẫn"
_JUDGMENT = "TÒA ÁN NHÂN DÂN ... BẢN ÁN về việc ly hôn"
_ADN = "Trung Tâm Xét Nghiệm Huyết Thống\nKẾT QUẢ XÉT NGHIỆM ADN\nKết luận: có quan hệ huyết thống bố - con"
_JUNK = "Vâng, đây là một văn bản không có giá trị."
_BIRTH = "BỆNH VIỆN ĐA KHOA\nGIẤY CHỨNG SINH"
_FRONT = "CĂN CƯỚC CÔNG DÂN\nSố / No.: 001090000001\nHọ và tên: NGUYỄN VĂN A"
_BACK = "Đặc điểm nhận dạng\nIDVNM0900000011001090000001<<<<\nNGUYEN<<VAN<A"


def _file(name: str, mime: str = "application/pdf") -> FileItem:
    return FileItem(name=name, type=mime, dataUrl=f"data:{mime};base64,AAA", role="doc")


def _paged(*pages: str) -> str:
    return "\n".join(f"───── Trang {i}/{len(pages)} ─────\n{text}" for i, text in enumerate(pages, 1))


def _patch(monkeypatch, texts: dict[str, str], documents):
    async def fake_ocr(files):
        return [{"name": f["name"], "text": texts.get(f["name"], "")} for f in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        if isinstance(documents, Exception):
            raise documents
        return json.dumps({"documents": documents})

    monkeypatch.setattr(split.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(split.client, "chat", fake_chat)


async def test_tep_quet_gop_ca_ho_so_tach_dung_dong(monkeypatch):
    pages = [_DECL_KS, _NOTE, _DECL_CMC, _NOTE, _JUDGMENT, "trang 2 bản án", _ADN, "bảng locus", _JUNK,
             _BIRTH, _FRONT, _BACK]
    _patch(monkeypatch, {"hoso.pdf": _paged(*pages)}, [
        {"fileIndex": 0, "pages": [1, 2], "docType": "birth_declaration", "documentName": "Tờ khai đăng ký khai sinh"},
        {"fileIndex": 0, "pages": [3, 4], "docType": "recognition_declaration", "documentName": "Tờ khai nhận cha mẹ con"},
        {"fileIndex": 0, "pages": [5, 6], "docType": "marital_status_evidence", "documentName": "Bản án ly hôn"},
        {"fileIndex": 0, "pages": [7, 8], "docType": "relationship_proof", "documentName": "Kết quả xét nghiệm ADN"},
        {"fileIndex": 0, "pages": [9], "docType": "blank_page", "documentName": ""},
        {"fileIndex": 0, "pages": [10], "docType": "birth_proof", "documentName": "Giấy chứng sinh"},
        {"fileIndex": 0, "pages": [11], "docType": "identity", "documentName": "Căn cước công dân"},
        {"fileIndex": 0, "pages": [12], "docType": "identity", "documentName": "Căn cước công dân"},
    ])

    result = await dispatcher.plan([_file("hoso.pdf")], {"splitDocuments": True}, {})
    items = result["attachments"]
    by_name = {i["documentName"]: i for i in items}

    assert by_name["Giấy chứng sinh"]["componentIndex"] == 3
    assert by_name["Giấy chứng sinh"]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [9]}]
    assert by_name["Kết quả xét nghiệm ADN"]["componentIndex"] == 4
    assert by_name["Kết quả xét nghiệm ADN"]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [6, 7]}]
    assert by_name["Bản án ly hôn"]["target"] == "new"
    assert by_name["Tờ khai đăng ký khai sinh bản giấy"]["target"] == "new", "tờ khai nhắc giấy chứng sinh vẫn là tờ khai"
    cccd = [i for i in items if i.get("sourceSegments") and len(i["sourceSegments"]) == 2]
    assert cccd and cccd[0]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [10]},
                                                  {"fileIndex": 0, "pageIndexes": [11]}], "gộp hai mặt CCCD cùng người"
    covered = sorted(p for i in items for s in i["sourceSegments"] for p in s["pageIndexes"])
    assert covered == [p for p in range(12) if p != 8], "không sót trang nào, chỉ bỏ trang trắng"
    assert all(i["fileName"] == "hoso.pdf" for i in items)
    assert result["extracted"]["attachmentMode"] == "split_documents"


async def test_llm_chia_giay_loi_thi_quay_ve_che_do_khong_tach(monkeypatch):
    _patch(monkeypatch, {"hoso.pdf": _paged(_ADN, _BIRTH)}, RuntimeError("sập"))

    async def fake_classify(documents):
        return {d["index"]: {"type": "relationship_proof", "documentName": ""} for d in documents}

    monkeypatch.setattr(dispatcher.ocr, "ocr_per_file", split.ocr.ocr_per_file)
    monkeypatch.setattr(dispatcher, "_classify_with_llm", fake_classify)
    result = await dispatcher.plan([_file("hoso.pdf")], {"splitDocuments": True}, {})

    assert [i["componentIndex"] for i in result["attachments"]] == [4]
    assert "sourceSegments" not in result["attachments"][0]
    assert any("tách" in e for e in result["errors"])


async def test_khong_bat_tach_thi_giu_che_do_cu(monkeypatch):
    called = []

    async def fake_split(*_a, **_k):
        called.append(1)

    monkeypatch.setattr(split, "plan", fake_split)

    async def fake_without(files, options, session):
        return {"attachments": [], "mode": "without"}

    monkeypatch.setattr(dispatcher, "plan_without_split", fake_without)
    assert (await dispatcher.plan([_file("a.pdf")], {"splitDocuments": False}, {}))["mode"] == "without"
    assert (await dispatcher.plan([_file("a.pdf")], {}, {}))["mode"] == "without"
    assert not called


def test_registry_ca_hai_extension_bat_tach():
    from app.channels.handfree.procedure_registry import get_procedure as handfree_proc
    from app.procedures.registry import get_procedure as core_proc

    key = "khai-sinh-ket-hop-nhan-cha-me-con"
    assert handfree_proc(key)["supportsSplitDocuments"] is True
    assert core_proc(key)["supportsSplitDocuments"] is True


async def test_phieu_adn_bi_cat_nhieu_doan_va_trang_chu_thich_bi_goi_la_trang_trang(monkeypatch):
    """LLM cắt phiếu ADN thành nhiều đoạn (trang trắng chen giữa) → gộp lại một giấy cho dòng 4; trang chú thích dài của
    tờ khai bị gọi nhầm là trang trắng → không bỏ, gộp vào tờ khai; trang rác ngắn thì bỏ."""
    long_note = _NOTE + " " + "hướng dẫn ghi " * 40
    _patch(monkeypatch, {"hoso.pdf": _paged(_DECL_KS, long_note, _ADN, "mã vạch mẫu", _JUNK, "biểu đồ điện di")}, [
        {"fileIndex": 0, "pages": [1], "docType": "birth_declaration", "documentName": "Tờ khai đăng ký khai sinh"},
        {"fileIndex": 0, "pages": [2], "docType": "blank_page", "documentName": ""},
        {"fileIndex": 0, "pages": [3], "docType": "relationship_proof", "documentName": "Kết quả xét nghiệm ADN"},
        {"fileIndex": 0, "pages": [4], "docType": "relationship_proof", "documentName": "Kết quả xét nghiệm ADN"},
        {"fileIndex": 0, "pages": [5], "docType": "blank_page", "documentName": ""},
        {"fileIndex": 0, "pages": [6], "docType": "relationship_proof", "documentName": "Kết quả xét nghiệm ADN"},
    ])

    items = (await dispatcher.plan([_file("hoso.pdf")], {"splitDocuments": True}, {}))["attachments"]

    assert [(i["componentIndex"], i["sourceSegments"]) for i in items] == [
        (None, [{"fileIndex": 0, "pageIndexes": [0, 1]}]),
        (4, [{"fileIndex": 0, "pageIndexes": [2, 3, 5]}]),
    ]
