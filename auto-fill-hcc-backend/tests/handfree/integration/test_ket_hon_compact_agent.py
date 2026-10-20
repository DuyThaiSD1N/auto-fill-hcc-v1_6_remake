"""Compact agent đăng ký kết hôn: OCR text -> BenNam/BenNu -> legacy UI fields."""

from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.ket_hon import process as agent
from app.pipelines.ket_hon.process import base_prompt as ket_hon_base_prompt
from app.pipelines.ket_hon.process.prompt import EXTRA_RULES
from app.pipelines.ket_hon.process.schema import FIELDS
from app.channels.handfree.procedure_registry import get_attach_pipeline, get_pipeline, get_procedure
from app.upload_session.classify import classify_text, route_to_slot
from app.upload_session.store import progress


def test_ket_hon_compact_prompt_instructs_gender_split():
    system_prompt = ket_hon_base_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "Nam -> nhóm BenNam_*" in system_prompt
    assert "Nữ -> nhóm BenNu_*" in system_prompt
    assert "Không phân biệt nam/nữ theo tên file" in system_prompt
    assert "BẮT BUỘC cố đọc BenNam_NoiCap/BenNu_NoiCap" in system_prompt
    assert "Bộ Công an" in system_prompt
    assert "HoTenBenNam" in system_prompt
    assert "Không trả field UI/default" in system_prompt


def test_registry_uses_ket_hon_compact_agent_mode():
    proc = get_procedure("ket-hon")
    docs = {item["key"]: item for item in proc["requiredDocs"]}

    assert get_pipeline("ket-hon") is agent.run
    assert get_attach_pipeline("ket-hon") is not None
    assert proc["flowProfile"] == "tu-phap"
    assert proc["ownerInfo"]["enabled"] is True
    assert proc["mode"] == "agent"
    assert proc["hasAttachmentStep"] is True
    assert proc["roles"] == []
    assert "tự phân biệt theo giới tính" in proc["uploadHint"]
    assert proc["hideRepeatableHint"] is True
    assert docs["cccd_nam"]["name"] == "Căn cước công dân bên nam"
    assert docs["cccd_nu"]["name"] == "Căn cước công dân bên nữ"
    assert docs["khac"]["name"] == "Giấy tờ chứng minh tình trạng hôn nhân hoặc giấy tờ khác"
    assert all(item["sides"] == 1 and item.get("repeatable") for item in docs.values())
    assert not docs["cccd_nam"].get("optional") and not docs["cccd_nu"].get("optional")
    assert docs["to_khai"]["optional"] and docs["khac"]["optional"]


def test_ket_hon_repeatable_docs_accept_many_files_without_face_limit():
    docs = get_procedure("ket-hon")["requiredDocs"]
    existing = [
        *({"doc_key": "cccd_nam"} for _ in range(3)),
        *({"doc_key": "cccd_nu"} for _ in range(4)),
        *({"doc_key": "to_khai"} for _ in range(5)),
        *({"doc_key": "khac"} for _ in range(6)),
    ]
    result = progress({
        "procedure_key": "ket-hon",
        "required_docs": docs,
        "files": existing,
        "complete": False,
    })
    counts = {item["key"]: item["receivedCount"] for item in result["docs"]}

    assert result["received"] == result["total"] == 2
    assert counts == {"cccd_nam": 3, "cccd_nu": 4, "to_khai": 5, "khac": 6}
    assert route_to_slot(
        classify_text("CĂN CƯỚC CÔNG DÂN Giới tính: Nam"), docs, existing, None
    )[0] == "cccd_nam"
    assert route_to_slot(
        classify_text("CĂN CƯỚC CÔNG DÂN Giới tính: Nữ"), docs, existing, None
    )[0] == "cccd_nu"
    assert route_to_slot(
        classify_text("TỜ KHAI ĐĂNG KÝ KẾT HÔN"), docs, existing, None
    )[0] == "to_khai"
    assert route_to_slot(
        classify_text("GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN"), docs, existing, None
    )[0] == "khac"
