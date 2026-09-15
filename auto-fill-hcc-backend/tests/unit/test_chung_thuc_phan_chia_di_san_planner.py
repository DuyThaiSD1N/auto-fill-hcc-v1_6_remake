"""Đính kèm chứng thực phân chia di sản: 2 chế độ gộp / không gộp (options.splitDocuments)."""

from app.pipelines.chung_thuc_phan_chia_di_san.attach.planner import (
    _ROW_1_COMPONENT,
    _ROW_2_COMPONENT,
    build_plan_items,
)

_FILES = [
    {"name": "cccd.pdf"},
    {"name": "so-do.pdf"},
    {"name": "van-ban-phan-chia.pdf"},
    {"name": "uy-quyen.pdf"},
]
# LLM-first: type do LLM trả. Giấy ủy quyền = authorization (dù nội dung nhắc số GCN QSDĐ).
_LLM = {
    0: {"type": "identity_document", "title": "Căn cước công dân"},
    1: {"type": "asset_ownership_proof", "title": "Giấy chứng nhận quyền sử dụng đất"},
    2: {"type": "division_draft", "title": "Văn bản thỏa thuận phân chia di sản thừa kế"},
    3: {"type": "authorization", "title": "Văn bản ủy quyền"},
}


def _by_file(attachments):
    return {item["fileIndex"]: item for item in attachments}


def test_merge_mode_lumps_all_non_draft_into_row1():
    """GỘP (mặc định): CCCD + sổ đỏ + ủy quyền gộp 1 PDF dòng 1; dự thảo dòng 2."""
    attachments, warnings, classified = build_plan_items(_FILES, [], _LLM, split=False)

    assert len(attachments) == 2
    row1 = next(a for a in attachments if a["componentIndex"] == 1)
    row2 = next(a for a in attachments if a["componentIndex"] == 2)

    assert row1["componentName"] == _ROW_1_COMPONENT
    assert row1["target"] == "existing"
    assert sorted(row1["sourceFileIndexes"]) == [0, 1, 3]   # ủy quyền vẫn nằm dòng 1 (như cũ)
    assert row2["componentName"] == _ROW_2_COMPONENT
    assert row2["fileIndex"] == 2 and row2["sourceFileIndexes"] == [2]
    assert not warnings
    assert not any(a["needsAddComponent"] for a in attachments)


def test_merge_mode_is_default_when_option_missing():
    """Thiếu split (extension cũ) → GỘP như cũ ⇒ tương thích ngược."""
    attachments, _, _ = build_plan_items(_FILES, [], _LLM)
    assert len(attachments) == 2
    assert {a["componentIndex"] for a in attachments} == {1, 2}


def test_split_mode_one_row_per_document():
    """KHÔNG GỘP: dự thảo → dòng 2; giấy đầu tiên → dòng 1; các giấy sau → thành phần mới."""
    attachments, warnings, classified = build_plan_items(_FILES, [], _LLM, split=True)

    assert len(attachments) == 4
    by_file = _by_file(attachments)

    # CCCD = giấy bổ trợ đầu tiên → dòng 1 cố định.
    assert by_file[0]["target"] == "existing"
    assert by_file[0]["componentIndex"] == 1
    assert by_file[0]["componentName"] == _ROW_1_COMPONENT

    # Dự thảo LUÔN ở dòng 2 cố định (không bị tính là "giấy đầu tiên").
    assert by_file[2]["target"] == "existing"
    assert by_file[2]["componentIndex"] == 2
    assert by_file[2]["componentName"] == _ROW_2_COMPONENT

    # Sổ đỏ + ủy quyền → thêm thành phần hồ sơ mới, mỗi cái 1 dòng, nhãn đúng loại.
    assert by_file[1]["target"] == "new" and by_file[1]["needsAddComponent"] is True
    assert "Giấy chứng nhận quyền sử dụng đất" in by_file[1]["componentName"]
    assert by_file[3]["target"] == "new" and by_file[3]["needsAddComponent"] is True
    assert by_file[3]["componentName"] == "Văn bản ủy quyền"

    assert all(a["sourceFileIndexes"] == [a["fileIndex"]] for a in attachments)
    assert not warnings


def test_split_mode_draft_first_does_not_steal_row1():
    """Dự thảo tải lên trước vẫn về dòng 2; giấy bổ trợ đầu tiên mới chiếm dòng 1."""
    files = [{"name": "van-ban.pdf"}, {"name": "cccd.pdf"}, {"name": "so-do.pdf"}]
    llm = {
        0: {"type": "division_draft", "title": "Văn bản phân chia di sản"},
        1: {"type": "identity_document", "title": "Căn cước công dân"},
        2: {"type": "asset_ownership_proof", "title": "Giấy chứng nhận quyền sử dụng đất"},
    }
    attachments, _, _ = build_plan_items(files, [], llm, split=True)
    by_file = _by_file(attachments)

    assert by_file[0]["componentIndex"] == 2                      # dự thảo → dòng 2
    assert by_file[1]["componentIndex"] == 1                      # CCCD (bổ trợ đầu) → dòng 1
    assert by_file[2]["target"] == "new"                         # sổ đỏ → thành phần mới


def test_split_mode_default_type_becomes_new_component():
    """LLM-first: file không rõ loại (other) vẫn được đính — vào thành phần mới, không bị bỏ."""
    files = [{"name": "a.pdf"}, {"name": "b.pdf"}]
    llm = {0: {"type": "asset_ownership_proof", "title": "Sổ đỏ"}, 1: {}}
    attachments, _, classified = build_plan_items(files, [], llm, split=True)
    by_file = _by_file(attachments)

    assert by_file[0]["componentIndex"] == 1
    assert by_file[1]["target"] == "new"
    assert classified[1]["type"] == "other"
