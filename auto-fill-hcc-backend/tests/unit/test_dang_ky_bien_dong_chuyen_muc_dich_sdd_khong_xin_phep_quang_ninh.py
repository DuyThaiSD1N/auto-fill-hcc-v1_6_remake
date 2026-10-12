"""Unit test "[Quảng Ninh] [Đặc thù] Đăng ký biến động chuyển mục đích sử dụng đất không phải xin phép cơ quan
nhà nước có thẩm quyền - Miền núi, hải đảo" (1.115846).

- Đăng ký attach-only, key trùng ke_khai_links, có planner riêng.
- Bộ hồ sơ mẫu (GCN, đơn Mẫu 18, tờ khai thuế SDĐ nông nghiệp, tờ khai lệ phí trước bạ; tên file ngẫu nhiên)
  đính nguyên file: GCN → hàng 3; Đơn + 2 tờ khai đính kèm chung hàng 4, Đơn trước. Hàng 1, 2 để trống.
- PDF gộp nhiều trang chỉ OCR 2 trang đầu; tệp đính vẫn là bản gốc.
"""

import base64
import json
from pathlib import Path

import fitz

from app.pipelines.dang_ky_bien_dong_chuyen_muc_dich_sdd_khong_xin_phep_quang_ninh.attach import planner
from app.process.schemas import FileItem
from app.procedures.registry import get_attach_pipeline, get_procedure

_KEY = "dang-ky-bien-dong-chuyen-muc-dich-sdd-khong-xin-phep-quang-ninh"
_LINKS = Path(__file__).resolve().parents[2] / "app" / "procedures" / "data" / "ke_khai_links.json"

_GCN = (
    "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT QUYỀN SỞ HỮU NHÀ Ở VÀ TÀI SẢN KHÁC GẮN LIỀN VỚI ĐẤT "
    "I. Người sử dụng đất: Ông: Trần Văn Bình Bà: Lê Thị Hoa DA 123456 "
    "II. Thửa đất a) Thửa đất số: 118 , tờ bản đồ số: 27 d) Mục đích sử dụng: Đất trồng cây hàng năm khác "
    "BẢNG KÊ TỌA ĐỘ"
)
_DON_18 = (
    "Mẫu số 18. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất\n"
    "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT\n"
    "I. Người sử dụng đất, chủ sở hữu tài sản gắn liền với đất:\n"
    "- Tên(2): Ông TRẦN VĂN BÌNH, sinh năm 1970; Bà LÊ THỊ HOA, sinh năm 1972\n"
    "- Giấy tờ nhân thân/pháp nhân(3):\n"
    "II. Nội dung biến động(5): Chuyển mục đích sử dụng đất từ đất trồng cây hàng năm khác sang\n"
    "đất trồng cây lâu năm tại Giấy chứng nhận QSDĐ số seri DA 123456, số vào sổ CH 00999.\n"
    "III.Thông tin về đối tượng được miễn, giảm nghĩa vụ tài chính\n"
    "IV. Giấy tờ liên quan: (1) Bản gốc Giấy chứng nhận đã cấp;"
)
_THUE_NN = (
    "Mẫu số: 02/SDDNN TỜ KHAI THUẾ SỬ DỤNG ĐẤT NÔNG NGHIỆP [17] Sổ địa chính: [18] Thửa đất số: 118 "
    "[19] Tờ bản đồ số: 27 Cộng cây lâu năm"
)
_LPTB = (
    "Mẫu số: 01/LPTB TỜ KHAI LỆ PHÍ TRƯỚC BẠ (Áp dụng đối với nhà, đất) 1.1. Thửa đất số (Số hiệu thửa đất): "
    "118; Tờ bản đồ số: 27 1.4. Mục đích sử dụng đất: Đất trồng cây lâu năm"
)


def _sample() -> tuple[list[dict], list[dict]]:
    texts = {
        "Lp3-dQ.pdf": _LPTB,
        "Xk8_mN.pdf": _GCN,
        "Rt2vBw.pdf": _THUE_NN,
        "Gh5-yZ.pdf": _DON_18,
    }
    files = [{"name": name, "type": "application/pdf"} for name in texts]
    ocr = [{"name": name, "text": text} for name, text in texts.items()]
    return files, ocr


def test_registry_attach_only_and_own_planner():
    proc = get_procedure(_KEY)
    assert proc is not None
    assert proc["mode"] == "attach"
    assert proc["detect"]["urlScope"] == ["dichvucong.quangninh.gov.vn"]
    assert "Miền núi, hải đảo" in proc["detect"]["textIncludes"]
    assert get_attach_pipeline(_KEY) is planner.plan


def test_key_matches_ke_khai_links():
    links = json.loads(_LINKS.read_text(encoding="utf-8"))["links"]
    entry = next(item for item in links if item.get("code") == "1.115846")
    assert entry["key"] == _KEY
    assert entry["provincePortalFlow"]["host"] == "dichvucong.quangninh.gov.vn"


def test_rule_fallback_routes_sample_dossier():
    files, ocr = _sample()

    attachments, warnings, classified = planner.build_plan_items(files, ocr)

    # Hàng 3 trước, hàng 4: Đơn trước rồi mới tới các tờ khai đính kèm chung.
    assert [(item["fileName"], item["componentIndex"]) for item in attachments] == [
        ("Xk8_mN.pdf", 3),
        ("Gh5-yZ.pdf", 4),
        ("Rt2vBw.pdf", 4),
        ("Lp3-dQ.pdf", 4),
    ]
    assert [item["detectedType"] for item in attachments] == [
        "gcn_da_cap",
        "don_mau_18",
        "to_khai_02_sddnn",
        "to_khai_01_lptb",
    ]
    assert all(item["target"] == "existing" for item in attachments)
    assert {item["source"] for item in classified} == {"rule"}
    assert not any("Chưa có" in warning for warning in warnings)
    shared = next(w for w in warnings if w.startswith("Hàng 4 đính kèm chung"))
    assert "2 tờ khai" in shared and "Rt2vBw.pdf" in shared and "Lp3-dQ.pdf" in shared


def test_suggest_note_from_don_and_gcn():
    files, ocr = _sample()

    _, warnings, _ = planner.build_plan_items(files, ocr)

    note = next(w for w in warnings if w.startswith("Ghi chú"))
    assert (
        "Chuyển mục đích sử dụng đất từ đất trồng cây hàng năm khác sang đất trồng cây lâu năm – thửa 118, "
        "tờ BĐ 27 – GCN seri DA 123456 – Ông Trần Văn Bình, Bà Lê Thị Hoa."
    ) in note


def test_llm_type_wins_and_missing_required_warns():
    files = [
        {"name": "trich-do.jpg", "type": "image/jpeg"},
        {"name": "uy-quyen.pdf", "type": "application/pdf"},
        {"name": "khac.pdf", "type": "application/pdf"},
    ]
    ocr = [
        {"name": "trich-do.jpg", "text": "Bản vẽ"},
        {"name": "uy-quyen.pdf", "text": "HỢP ĐỒNG ỦY QUYỀN về việc nộp hồ sơ đăng ký biến động"},
        {"name": "khac.pdf", "text": "Biên lai thu tiền"},
    ]

    attachments, warnings, _ = planner.build_plan_items(files, ocr, {0: "manh_trich_do", 1: "other"})

    by_name = {item["fileName"]: item for item in attachments}
    assert by_name["trich-do.jpg"]["componentIndex"] == 1
    # LLM trả other → rule nhận ra hợp đồng ủy quyền → hàng 2 có sẵn trên cổng, không thêm dòng.
    assert by_name["uy-quyen.pdf"]["componentIndex"] == 2
    assert by_name["uy-quyen.pdf"]["needsAddComponent"] is False
    assert by_name["khac.pdf"]["target"] == "new"
    assert by_name["khac.pdf"]["componentName"] == "khac"
    assert attachments[-1]["fileName"] == "khac.pdf"
    assert any("hàng 3" in w for w in warnings)
    assert any("hàng 4" in w for w in warnings)
    assert not any(w.startswith("Ghi chú") for w in warnings)


def _pdf_data_url(pages: int) -> str:
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    raw = doc.tobytes()
    doc.close()
    return "data:application/pdf;base64," + base64.b64encode(raw).decode("ascii")


async def test_plan_ocr_only_first_pages_but_attaches_original(monkeypatch):
    seen_pages: dict[str, int] = {}

    async def fake_ocr_per_file(files):
        for item in files:
            raw = base64.b64decode(item["dataUrl"].split(",", 1)[1])
            with fitz.open(stream=raw, filetype="pdf") as doc:
                seen_pages[item["name"]] = doc.page_count
        return [{"name": item["name"], "text": _DON_18} for item in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{"index": 0, "docType": "don_mau_18"}]})

    from app.services import ocr

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    data_url = _pdf_data_url(5)

    result = await planner.plan([FileItem(name="don.pdf", type="application/pdf", dataUrl=data_url, role="doc")])

    assert seen_pages == {"don.pdf": 2}
    assert result["attachments"][0]["componentIndex"] == 4
    assert result["attachments"][0]["fileIndex"] == 0
