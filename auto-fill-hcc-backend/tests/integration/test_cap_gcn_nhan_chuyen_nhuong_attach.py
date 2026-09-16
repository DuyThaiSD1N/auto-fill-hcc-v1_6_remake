"""Kế hoạch đính kèm [Lào Cai] 1.115667 — hồ sơ mẫu 5 PDF trong file ánh xạ thành phần hồ sơ."""

from app.pipelines.cap_GCN_nhan_chuyen_nhuong.attach import catalog
from app.pipelines.cap_GCN_nhan_chuyen_nhuong.attach.planner import build_plan_items
from app.procedures.registry import get_attach_pipeline, get_procedure

KEY = "dang-ky-cap-gcn-nhan-chuyen-nhuong-du-an-bat-dong-san-lao-cai"

_FILES = [
    {"name": "gcn.pdf", "_index": 0},
    {"name": "hop_dong.pdf", "_index": 1},
    {"name": "don.pdf", "_index": 2},
    {"name": "kiem_tra_hien_trang.pdf", "_index": 3},
    {"name": "nghiem_thu.pdf", "_index": 4},
]
_OCR = [
    {"name": "gcn.pdf", "text": "GIẤY CHỨNG NHẬN ... 4. Sơ đồ thửa đất, tài sản gắn liền với đất ..."},
    {"name": "hop_dong.pdf", "text": "HỢP ĐỒNG CHUYỂN NHƯỢNG QUYỀN SỬ DỤNG ĐẤT ..."},
    {"name": "don.pdf", "text": "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI ..."},
    {"name": "kiem_tra_hien_trang.pdf", "text": "BIÊN BẢN KIỂM TRA HIỆN TRẠNG CĂN ..."},
    {"name": "nghiem_thu.pdf", "text": "BIÊN BẢN NGHIỆM THU HOÀN THÀNH CÔNG TRÌNH ..."},
]
_LLM = {
    0: {"label": "gcn_chu_dau_tu", "documentName": "Giấy chứng nhận AA 04812256"},
    1: {"label": "hop_dong", "documentName": "Hợp đồng chuyển nhượng lô 16 LK4"},
    2: {"label": "don_dang_ky", "documentName": ""},
    3: {"label": "ban_giao", "documentName": "Biên bản kiểm tra hiện trạng căn"},
    4: {"label": "nghiem_thu", "documentName": "Biên bản nghiệm thu hoàn thành công trình"},
}


def _slots(attachments: list[dict]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for item in attachments:
        out.setdefault(item["slotName"].split(".")[0], []).append(item["fileName"])
    return out


def test_registry_enables_attachment_step():
    assert get_procedure(KEY)["hasAttachmentStep"] is True
    assert get_attach_pipeline(KEY) is not None


def test_sample_dossier_goes_to_branch_b_rows():
    attachments, warnings, _, branch = build_plan_items(_FILES, _OCR, _LLM, "b")

    assert branch == "b" and not warnings
    assert _slots(attachments) == {
        "b-6": ["gcn.pdf"],
        "b-2": ["hop_dong.pdf"],
        "b-1": ["don.pdf"],
        "b-3": ["kiem_tra_hien_trang.pdf"],
        "b-4": ["nghiem_thu.pdf"],
        "b-8": ["gcn.pdf"],  # sơ đồ ở trang 2 GCN → đính lại chính file đó
    }
    for item in attachments:
        assert item["target"] == "fixed-slot" and item["tickRow"] is True
        assert item["sectionHeader"] == catalog.SECTION_HEADERS["b"]
        assert item["slotKeywords"]


def test_unknown_branch_defaults_to_b_and_branch_a_uses_its_own_rows():
    attachments, _, _, branch = build_plan_items(_FILES, _OCR, _LLM, "")
    assert branch == "b"

    attachments, _, _, branch = build_plan_items(_FILES, _OCR, _LLM, "a")
    assert branch == "a"
    slots = _slots(attachments)
    assert slots["a-1"] == ["don.pdf"] and slots["a-4"] == ["hop_dong.pdf"] and slots["a-2"] == ["nghiem_thu.pdf"]
    assert all(item["sectionHeader"] == catalog.SECTION_HEADERS["a"] for item in attachments)


def test_separate_site_plan_is_not_duplicated_from_certificate():
    files = _FILES + [{"name": "so_do.pdf", "_index": 5}]
    llm = {**_LLM, 5: {"label": "so_do", "documentName": "Sơ đồ nhà"}}
    attachments, _, _, _ = build_plan_items(files, _OCR, llm, "b")
    assert _slots(attachments)["b-8"] == ["so_do.pdf"]


def test_identity_and_unknown_documents_are_skipped_with_warning():
    files = [{"name": "cccd.jpg", "_index": 0}, {"name": "la.pdf", "_index": 1}]
    attachments, warnings, classified, _ = build_plan_items(files, [], {0: {"label": "cccd"}}, "b")
    assert attachments == []
    assert len(warnings) == 2
    assert {c["target"] for c in classified} == {"skip"}


def test_row_keywords_pick_exactly_one_row_per_branch():
    # Tên dòng theo bảng Thành phần hồ sơ trên cổng (đã fold): mỗi từ khóa chỉ khớp đúng 1 dòng trong nhánh.
    rows_b = [
        "b-1. don dang ky bien dong dat dai, tai san gan lien voi dat theo mau so 24 ban hanh kem theo quyet dinh "
        "so 47/2026/qd ubnd (ban chinh)",
        "b-2. hop dong chuyen nhuong quyen su dung dat, quyen so huu nha o, cong trinh xay dung, hang muc cong "
        "trinh xay dung theo quy dinh cua phap luat (ban chinh)",
        "b-3. bien ban ban giao nha, dat, cong trinh xay dung, hang muc cong trinh xay dung (ban chinh)",
        "b-4. van ban ve viec nha o, cong trinh xay dung da duoc nghiem thu dua vao khai thac, su dung theo quy "
        "dinh cua phap luat ve xay dung doi voi truong hop co nhan chuyen nhuong nha o, cong trinh xay dung",
        "b-5. van ban ve viec du dieu kien duoc chuyen nhuong cho ca nhan tu xay dung nha o doi voi truong hop "
        "chuyen nhuong quyen su dung dat da co ha tang ky thuat",
        "b-6. giay chung nhan da cap cho chu dau tu du an (neu co) (ban chinh)",
        "b-7. chung tu chung minh viec hoan thanh nghia vu tai chinh doi voi truong hop van phong dang ky dat dai",
        "b-8. so do tai san gan lien voi dat (ban chinh)",
    ]
    for label, *_ in catalog.CATALOG:
        keywords = catalog.slot("b", label)["slotKeywords"]
        hits = [row for row in rows_b if any(kw in row for kw in keywords)]
        assert len(hits) == 1, (label, hits)
