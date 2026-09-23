"""Cấp bản sao trích lục hộ tịch — đặt tên giấy tờ (trace req_aa693b7a217c).

Lỗi gốc: Trích lục BỔ SUNG và Trích lục CẢI CHÍNH hộ tịch bị LLM xếp vào civil_status_marriage, rồi
planner đè nhãn cố định → hai dòng "Giấy đăng ký kết hôn" / "Giấy đăng ký kết hôn 2". Luật mới:
  · giấy khớp rõ loại → tên chuẩn theo TIÊU ĐỀ (Giấy khai sinh ≠ Trích lục khai sinh);
  · giấy đơn lẻ "lạ" → other + đúng tiêu đề in trên giấy;
  · rule keyword chỉ đỡ khi LLM không trả kết quả, không bao giờ đè LLM.
"""

import json

from app.pipelines.trich_luc.attach.civil_status_names import civil_status_name
from app.pipelines.trich_luc.attach.dinh_kem_khong_tach import planner
from app.pipelines.trich_luc.attach.dinh_kem_khong_tach.prompt import SYSTEM_PROMPT
from app.process.schemas import FileItem

_GKS = (
    "───── Trang 1/2 ─────\nỦY BAN NHÂN DÂN HẢI CHÂU\nGIẤY KHAI SINH\n(BẢN CHÍNH)\n"
    "Họ và tên: DƯƠNG TRỌNG NGHĨA\n"
    "───── Trang 2/2 ─────\nPHẦN GHI CHÚ NHỮNG THÔNG TIN THAY ĐỔI SAU NÀY\n"
    "Cải chính Tên của cha … Trích lục số: 380/TLCCHT"
)
_BO_SUNG = (
    "UBND PHƯỜNG HẢI CHÂU\nSố: 380/2026/TLBSHT\nTRÍCH LỤC\nBỔ SUNG HỘ TỊCH\n"
    "Giấy tờ tùy thân: Thẻ căn cước công dân số 048207007503\n"
    "Trong Sổ đăng ký khai sinh và Giấy khai sinh Số 217 ngày 21/09/2007"
)
_CAI_CHINH = (
    "UBND PHƯỜNG HẢI CHÂU\nSố: 381/2026/TLCCHT\nTRÍCH LỤC\nCẢI CHÍNH HỘ TỊCH\n"
    "Giấy tờ tùy thân: Thẻ căn cước công dân số 048207007503\n"
    "Trong Sổ đăng ký khai sinh và Giấy khai sinh Số 217 ngày 21/09/2007"
)


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


async def _plan(monkeypatch, texts, reply_for):
    names = [f"scan-{i}.pdf" for i in range(len(texts))]
    calls = []

    async def fake_ocr(files):
        return [{"name": n, "text": t} for n, t in zip(names, texts)]

    async def fake_chat(messages, max_tokens, enable_thinking):
        user = messages[1]["content"]
        calls.append(user)
        reply = reply_for(user)
        if isinstance(reply, Exception):
            raise reply
        return json.dumps({"documents": [reply]})

    monkeypatch.setattr(planner.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    result = await planner.plan_trich_luc_attachments_without_split([_file(n) for n in names], {}, {})
    return result, calls


async def test_trace_hai_trich_luc_giu_dung_tieu_de(monkeypatch):
    def reply_for(user):
        if "CẢI CHÍNH HỘ TỊCH" in user:
            return {"fileIndex": 0, "type": "other", "documentName": "Trích lục cải chính hộ tịch"}
        if "BỔ SUNG HỘ TỊCH" in user:
            return {"fileIndex": 0, "type": "other", "documentName": "Trích lục bổ sung hộ tịch"}
        return {"fileIndex": 0, "type": "civil_status_birth", "documentName": "Giấy khai sinh"}

    result, calls = await _plan(monkeypatch, [_GKS, _BO_SUNG, _CAI_CHINH], reply_for)
    names = [a["documentName"] for a in result["attachments"]]

    assert names == ["Giấy khai sinh", "Trích lục bổ sung hộ tịch", "Trích lục cải chính hộ tịch"]
    assert all(a["target"] == "new" for a in result["attachments"])
    assert len(calls) == 3, "mỗi file một lượt gọi — file này không kéo file kia sai theo"
    assert all(c["source"] == "llm" for c in result["extracted"]["classified"])


async def test_llm_tra_fileindex_sai_van_gan_dung_file(monkeypatch):
    """Gọi riêng từng file nên KHÔNG tra theo fileIndex LLM tự ghi."""
    def reply_for(user):
        doc_type = "civil_status_death" if "KHAI TỬ" in user else "civil_status_birth"
        return {"fileIndex": 99, "type": doc_type, "documentName": ""}

    result, _ = await _plan(monkeypatch, ["GIẤY KHAI SINH", "TRÍCH LỤC KHAI TỬ"], reply_for)

    assert [a["documentName"] for a in result["attachments"]] == ["Giấy khai sinh", "Trích lục khai tử"]


async def test_llm_loi_trich_luc_khong_bi_goi_la_giay_khai_sinh(monkeypatch):
    """Bản cũ đoán tên bằng chữ trong giấy: gặp "…Giấy khai sinh số…" là đặt tên Giấy khai sinh."""
    result, _ = await _plan(monkeypatch, [_CAI_CHINH], lambda _u: RuntimeError("provider down"))

    item = result["attachments"][0]
    assert item["documentName"] != "Giấy khai sinh"
    assert item["documentName"] == "Tài liệu trích lục hộ tịch"
    assert result["extracted"]["classified"][0]["source"] == "rule"


def test_ban_chinh_va_trich_luc_la_hai_ten_khac_nhau():
    assert civil_status_name("civil_status_birth", "Giấy khai sinh") == "Giấy khai sinh"
    assert civil_status_name("civil_status_birth", "Trích lục khai sinh") == "Trích lục khai sinh"
    assert civil_status_name("civil_status_birth", "Trích lục khai sinh (bản sao).") == "Trích lục khai sinh"
    assert civil_status_name("civil_status_marriage", "Trích lục kết hôn") == "Trích lục kết hôn"
    assert civil_status_name("civil_status_death", "Giấy chứng tử") == "Giấy chứng tử"
    # Contract cũ của eForm: giấy chứng nhận kết hôn vẫn mang nhãn "Giấy đăng ký kết hôn".
    assert civil_status_name("civil_status_marriage", "Giấy chứng nhận kết hôn") == "Giấy đăng ký kết hôn"
    # Tiêu đề lạ/không có → nhãn mặc định của loại, KHÔNG khớp chuỗi con.
    assert civil_status_name("civil_status_birth", "Giấy khai sinh Dương Trọng Nghĩa") == "Giấy khai sinh"
    assert civil_status_name("civil_status_birth", "") == "Giấy khai sinh"


async def test_trich_luc_khai_sinh_mang_dung_ten(monkeypatch):
    def reply_for(_user):
        return {"fileIndex": 0, "type": "civil_status_birth", "documentName": "Trích lục khai sinh"}

    result, _ = await _plan(monkeypatch, ["TRÍCH LỤC KHAI SINH (BẢN SAO)"], reply_for)

    assert result["attachments"][0]["documentName"] == "Trích lục khai sinh"


def test_prompt_co_luat_giay_la_va_bay_tham_chieu():
    assert "ĐÚNG TIÊU ĐỀ in trên giấy" in SYSTEM_PROMPT
    assert "Trích lục cải chính hộ tịch" in SYSTEM_PROMPT
    assert "THAM CHIẾU tới sổ gốc" in SYSTEM_PROMPT
    assert '"Trích lục khai sinh"' in SYSTEM_PROMPT
