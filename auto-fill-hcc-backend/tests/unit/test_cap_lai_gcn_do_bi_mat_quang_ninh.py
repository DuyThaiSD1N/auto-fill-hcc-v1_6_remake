"""Unit test "[Quảng Ninh] [Đặc thù] Cấp lại Giấy chứng nhận do bị mất - Miền núi, hải đảo" (1.115849).

- Đăng ký attach-only, key trùng ke_khai_links, có planner riêng.
- Bộ hồ sơ mẫu (bộ phiếu đo đạc, bộ giấy tờ thừa kế, 3 tờ khai, đơn Mẫu 18; tên file ngẫu nhiên) đính
  nguyên file vào đúng hàng 2/6/3/4/5/8, hàng 1 (GCN đã mất) và hàng 7 để trống.
- PDF gộp nhiều trang chỉ OCR 2 trang đầu (OCR đủ trang quá timeout extension); tệp đính vẫn là bản gốc.
"""

import base64
import json
from pathlib import Path

import fitz

from app.pipelines.cap_lai_gcn_do_bi_mat_quang_ninh.attach import planner
from app.process.schemas import FileItem
from app.procedures.registry import get_attach_pipeline, get_procedure

_KEY = "cap-lai-gcn-do-bi-mat-quang-ninh"
_LINKS = Path(__file__).resolve().parents[2] / "app" / "procedures" / "data" / "ke_khai_links.json"

_PHIEU_DO_DAC = (
    "PHIẾU ĐO ĐẠC CHỈNH LÝ THỬA ĐẤT 1. Thửa đất số: 75 ; Tờ bản đồ số: 9 ; Diện tích: 210.0 m2 "
    "5. Giấy tờ pháp lý: GCNQSD đất số seri K 456789, số vào sổ 88 cấp ngày 02/3/2003 "
    "8. Sơ đồ thửa đất "
    "PHIẾU XÁC NHẬN KẾT QUẢ ĐO ĐẠC HIỆN TRẠNG THỬA ĐẤT "
    "BẢN MÔ TẢ RANH GIỚI, MỐC GIỚI THỬA ĐẤT "
    "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT NHỮNG THAY ĐỔI SAU KHI CẤP GIẤY CHỨNG NHẬN "
    "ĐƠN XIN ĐĂNG KÝ QUYỀN SỬ DỤNG ĐẤT "
    "HỢP ĐỒNG ỦY QUYỀN Bên A là những người được hưởng thừa kế"
)
_BO_THUA_KE = (
    "BẢN CAM KẾT Tôi cam kết không đề nghị chứng nhận nhà ở trên đất "
    "VĂN BẢN PHÂN CHIA DI SẢN lời chứng của công chứng viên "
    "Biên bản kết thúc niêm yết UBND đặc khu "
    "TRÍCH LỤC KHAI TỬ TRÍCH LỤC KẾT HÔN GIẤY KHAI SINH "
    "VĂN BẢN TỪ CHỐI NHẬN DI SẢN "
    "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT NHỮNG THAY ĐỔI SAU KHI CẤP GIẤY CHỨNG NHẬN"
)
_LPTB = (
    "Mẫu số: 01/LPTB TỜ KHAI LỆ PHÍ TRƯỚC BẠ (Áp dụng đối với nhà, đất) 6. Giấy tờ có liên quan, gồm: "
    "- Phiếu đo đạc chỉnh lý thửa đất - Văn bản phân chia di sản"
)
_SDDPNN = (
    "Mẫu số:01/TK-SDDPNN TỜ KHAI THUẾ SỬ DỤNG ĐẤT PHI NÔNG NGHIỆP [20.1] Số giấy chứng nhận: K 456789"
)
_TNCN = "Mẫu số: 03/BĐS-TNCN TỜ KHAI THUẾ THU NHẬP CÁ NHÂN nhận thừa kế bất động sản"
_DON_18 = (
    "Mẫu số 18. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất "
    "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT II. Nội dung biến động: "
    "- Cấp lại giấy chứng nhận do bị mất giấy chứng nhận số seri K 456789 "
    "- Nhận thừa kế quyền sử dụng đất tại thửa đất số 75, tờ bản đồ số 9 "
    "IV. Giấy tờ liên quan: (2) Văn bản phân chia di sản (3) Phiếu đo đạc chỉnh lý thửa đất"
)


def _sample() -> tuple[list[dict], list[dict]]:
    texts = {
        "aB3-xYz.pdf": _PHIEU_DO_DAC,
        "Qw9kLm2.pdf": _BO_THUA_KE,
        "Zr7tUv.pdf": _LPTB,
        "Hn4pWq.pdf": _SDDPNN,
        "Ty6-Ab.pdf": _TNCN,
        "P_kd8S.pdf": _DON_18,
    }
    files = [{"name": name, "type": "application/pdf"} for name in texts]
    ocr = [{"name": name, "text": text} for name, text in texts.items()]
    return files, ocr


def test_registry_attach_only_and_own_planner():
    proc = get_procedure(_KEY)
    assert proc is not None
    assert proc["mode"] == "attach"
    assert proc["detect"]["urlScope"] == ["dichvucong.quangninh.gov.vn"]
    assert "Cấp lại Giấy chứng nhận do bị mất" in proc["detect"]["textIncludes"]
    assert get_attach_pipeline(_KEY) is planner.plan


def test_key_matches_ke_khai_links():
    links = json.loads(_LINKS.read_text(encoding="utf-8"))["links"]
    entry = next(item for item in links if item.get("code") == "1.115849")
    assert entry["key"] == _KEY


def test_rule_fallback_routes_sample_dossier():
    files, ocr = _sample()

    attachments, warnings, classified = planner.build_plan_items(files, ocr)

    rows = {item["fileName"]: item.get("componentIndex") for item in attachments}
    assert rows == {
        "aB3-xYz.pdf": 2,
        "Qw9kLm2.pdf": 6,
        "Zr7tUv.pdf": 3,
        "Hn4pWq.pdf": 4,
        "Ty6-Ab.pdf": 5,
        "P_kd8S.pdf": 8,
    }
    assert all(item["target"] == "existing" for item in attachments)
    assert {item["source"] for item in classified} == {"rule"}
    # Hàng 1 (GCN đã mất) và hàng 7 (mất Trang bổ sung) để trống.
    assert 1 not in rows.values() and 7 not in rows.values()
    assert not any("Chưa có" in warning for warning in warnings)


def test_warnings_flag_sddpnn_form_and_suggest_note():
    files, ocr = _sample()

    _, warnings, _ = planner.build_plan_items(files, ocr)

    assert any("Hn4pWq.pdf" in w and "01/TK-SDDPNN" in w for w in warnings)
    note = next(w for w in warnings if w.startswith("Ghi chú"))
    assert "Cấp lại GCN do bị mất đối với thửa đất số 75, tờ bản đồ số 9" in note
    assert "số seri K 456789" in note
    assert "nhận thừa kế" in note


def test_llm_type_wins_and_missing_required_warns():
    files = [
        {"name": "gcn.jpg", "type": "image/jpeg"},
        {"name": "uy-quyen.pdf", "type": "application/pdf"},
        {"name": "khac.pdf", "type": "application/pdf"},
    ]
    ocr = [
        {"name": "gcn.jpg", "text": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT"},
        {"name": "uy-quyen.pdf", "text": "HỢP ĐỒNG ỦY QUYỀN về việc nhận di sản thừa kế"},
        {"name": "khac.pdf", "text": "Biên lai thu tiền"},
    ]

    attachments, warnings, _ = planner.build_plan_items(files, ocr, {0: "gcn_da_cap", 1: "other"})

    by_name = {item["fileName"]: item for item in attachments}
    assert by_name["gcn.jpg"]["componentIndex"] == 1
    # LLM trả other → rule nhận ra hợp đồng ủy quyền đứng riêng → thêm thành phần hồ sơ mới.
    assert by_name["uy-quyen.pdf"]["detectedType"] == "van_ban_dai_dien"
    assert by_name["uy-quyen.pdf"]["needsAddComponent"] is True
    assert by_name["khac.pdf"]["target"] == "new"
    assert by_name["khac.pdf"]["componentName"] == "khac"
    assert any("hàng 6" in w for w in warnings)
    assert any("hàng 8" in w for w in warnings)


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
        return [{"name": item["name"], "text": _BO_THUA_KE} for item in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{"index": 0, "docType": "giay_to_cap_lai_bi_mat"}]})

    from app.services import ocr

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    data_url = _pdf_data_url(5)

    result = await planner.plan([FileItem(name="bo-thua-ke.pdf", type="application/pdf", dataUrl=data_url, role="doc")])

    assert seen_pages == {"bo-thua-ke.pdf": 2}
    assert result["attachments"][0]["componentIndex"] == 6
    assert result["attachments"][0]["fileIndex"] == 0
