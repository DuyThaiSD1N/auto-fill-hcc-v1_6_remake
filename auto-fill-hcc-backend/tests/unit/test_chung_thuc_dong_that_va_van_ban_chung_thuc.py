"""Chứng thực giao dịch tài sản + phân chia di sản: chọn hàng theo bảng THẬT trên trang và đưa văn bản
đem đi chứng thực vào hàng dự thảo khi hồ sơ không có dự thảo."""
import json
import sys
from types import SimpleNamespace

from app.pipelines.chung_thuc_giao_dich_tai_san.attach import planner as giao_dich
from app.pipelines.chung_thuc_phan_chia_di_san.attach.planner import (
    _ROW_1_COMPONENT as PCDS_ROW_1,
    _ROW_2_COMPONENT as PCDS_ROW_2,
    build_plan_items,
)
from app.process.schemas import FileItem

# Cổng xếp hàng dự thảo LÊN TRƯỚC hàng giấy chứng nhận, tên hàng giấy chứng nhận khác mẫu mặc định.
_GD_SWAPPED_ROWS = [
    {"index": 1, "componentName": "Dự thảo giao dịch"},
    {"index": 2, "componentName": "Bản sao giấy chứng nhận quyền sở hữu, quyền sử dụng hoặc bản sao giấy tờ thay thế"},
]
_PCDS_SWAPPED_ROWS = [
    {"index": 1, "componentName": "Dự thảo văn bản phân chia di sản"},
    {"index": 2, "componentName": "Bản sao giấy chứng nhận quyền sở hữu, quyền sử dụng hoặc bản sao giấy tờ thay thế"},
]


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


async def _plan_giao_dich(monkeypatch, names, llm_docs, options=None):
    async def fake_ocr_per_file(files):
        return [{"name": f["name"], "text": "OCR"} for f in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": llm_docs})

    monkeypatch.setitem(sys.modules, "app.services.ocr", SimpleNamespace(ocr_per_file=fake_ocr_per_file))
    monkeypatch.setattr(giao_dich.client, "chat", fake_chat)
    res = await giao_dich.plan([_file(name) for name in names], options or {})
    return {item["fileIndex"]: item for item in res["attachments"]}


async def test_giao_dich_chon_hang_theo_bang_that_khi_cong_dao_thu_tu(monkeypatch):
    items = await _plan_giao_dich(
        monkeypatch,
        ["so-do.pdf", "giao-dich.pdf"],
        [
            {"index": 0, "type": "asset_ownership_proof", "title": "Giấy chứng nhận quyền sử dụng đất"},
            {"index": 1, "type": "transaction_draft", "title": "Giao dịch chuyển nhượng quyền sử dụng đất", "certificationTarget": True},
        ],
        {"attachmentContext": {"components": _GD_SWAPPED_ROWS}},
    )
    assert (items[0]["target"], items[0]["componentIndex"]) == ("existing", 2)
    assert items[0]["componentName"] == _GD_SWAPPED_ROWS[1]["componentName"]
    assert (items[1]["target"], items[1]["componentIndex"]) == ("existing", 1)
    assert items[1]["componentName"] == "Dự thảo giao dịch"


async def test_giao_dich_khong_co_bang_that_giu_hang_mac_dinh(monkeypatch):
    items = await _plan_giao_dich(
        monkeypatch,
        ["so-do.pdf", "giao-dich.pdf"],
        [
            {"index": 0, "type": "asset_ownership_proof", "title": "Giấy chứng nhận quyền sử dụng đất"},
            {"index": 1, "type": "transaction_draft", "title": "Hợp đồng chuyển nhượng"},
        ],
    )
    assert items[0]["componentIndex"] == 1
    assert items[0]["componentName"] == giao_dich._ROW_1_COMPONENT
    assert items[1]["componentIndex"] == 2
    assert items[1]["componentName"] == "Dự thảo giao dịch"


async def test_giao_dich_van_ban_chung_thuc_thay_cho_du_thao(monkeypatch):
    items = await _plan_giao_dich(
        monkeypatch,
        ["cccd.pdf", "uy-quyen.pdf"],
        [
            {"index": 0, "type": "identity_document", "title": "Căn cước công dân", "certificationTarget": False},
            {"index": 1, "type": "authorization", "title": "Giấy ủy quyền", "certificationTarget": True},
        ],
        {"attachmentContext": {"components": _GD_SWAPPED_ROWS}},
    )
    assert (items[1]["target"], items[1]["componentIndex"]) == ("existing", 1)
    assert items[1]["componentName"] == "Dự thảo giao dịch"
    assert items[1]["documentName"] == "Giấy ủy quyền", "giữ tên loại giấy, không gắn nhãn dự thảo"
    assert items[0]["target"] == "new"


async def test_giao_dich_da_co_du_thao_thi_khong_thay_cho(monkeypatch):
    items = await _plan_giao_dich(
        monkeypatch,
        ["hop-dong.pdf", "uy-quyen.pdf"],
        [
            {"index": 0, "type": "transaction_draft", "title": "Hợp đồng chuyển nhượng", "certificationTarget": True},
            {"index": 1, "type": "authorization", "title": "Văn bản ủy quyền", "certificationTarget": True},
        ],
    )
    assert items[0]["componentIndex"] == 2
    assert items[1]["target"] == "new"


async def test_giao_dich_llm_khong_tra_truong_moi_giu_hanh_vi_cu(monkeypatch):
    items = await _plan_giao_dich(
        monkeypatch,
        ["uy-quyen.pdf"],
        [{"index": 0, "type": "authorization", "title": "Văn bản ủy quyền"}],
    )
    assert items[0]["target"] == "new"


_PCDS_FILES = [{"name": "uy-quyen.pdf"}]


def test_phan_chia_giay_uy_quyen_co_loi_chung_vao_hang_du_thao_that():
    llm = {0: {"type": "authorization", "title": "Giấy ủy quyền", "certificationTarget": True}}
    components = [
        {"index": 1, "componentName": PCDS_ROW_1 + " trong trường hợp văn bản phân chia di sản liên quan đến tài sản đó"},
        {"index": 2, "componentName": "Dự thảo văn bản phân chia di sản"},
    ]
    for split in (False, True):
        attachments, _, classified = build_plan_items(_PCDS_FILES, [], llm, split=split, components=components)
        assert len(attachments) == 1
        item = attachments[0]
        assert (item["target"], item["componentIndex"]) == ("existing", 2)
        assert item["componentName"] == "Dự thảo văn bản phân chia di sản"
        assert item["documentName"] == "Giấy ủy quyền"
        assert classified[0]["componentIndex"] == 2


def test_phan_chia_uy_quyen_nop_ho_so_di_cung_van_ban_phan_chia_van_o_hang_giay_to_kem():
    files = [{"name": "uy-quyen.pdf"}, {"name": "van-ban.pdf"}]
    llm = {
        0: {"type": "authorization", "title": "Văn bản ủy quyền", "certificationTarget": False},
        1: {"type": "division_draft", "title": "Văn bản thỏa thuận phân chia di sản", "certificationTarget": True},
    }
    attachments, _, _ = build_plan_items(files, [], llm, split=False)
    by_file = {item["fileIndex"]: item for item in attachments}
    assert (by_file[0]["componentIndex"], by_file[0]["componentName"]) == (1, PCDS_ROW_1)
    assert (by_file[1]["componentIndex"], by_file[1]["componentName"]) == (2, PCDS_ROW_2)


def test_phan_chia_llm_khong_tra_truong_moi_giu_hanh_vi_cu():
    llm = {0: {"type": "authorization", "title": "Văn bản ủy quyền"}}
    attachments, _, _ = build_plan_items(_PCDS_FILES, [], llm, split=False)
    assert attachments[0]["componentIndex"] == 1
    assert attachments[0]["componentName"] == PCDS_ROW_1


def test_phan_chia_chon_hang_theo_bang_that_khi_cong_dao_thu_tu():
    files = [{"name": "so-do.pdf"}, {"name": "van-ban.pdf"}]
    llm = {
        0: {"type": "asset_ownership_proof", "title": "Giấy chứng nhận quyền sử dụng đất"},
        1: {"type": "division_draft", "title": "Văn bản thỏa thuận phân chia di sản", "certificationTarget": True},
    }
    for split in (False, True):
        attachments, _, _ = build_plan_items(files, [], llm, split=split, components=_PCDS_SWAPPED_ROWS)
        by_file = {item["fileIndex"]: item for item in attachments}
        assert (by_file[0]["componentIndex"], by_file[0]["componentName"]) == (2, _PCDS_SWAPPED_ROWS[1]["componentName"])
        assert (by_file[1]["componentIndex"], by_file[1]["componentName"]) == (1, "Dự thảo văn bản phân chia di sản")


def test_prompt_hai_thu_tuc_yeu_cau_certification_target():
    from app.pipelines.chung_thuc_giao_dich_tai_san.attach.prompt import SYSTEM_PROMPT as gd_prompt
    from app.pipelines.chung_thuc_phan_chia_di_san.attach.prompt import SYSTEM_PROMPT as pcds_prompt

    for text in (gd_prompt, pcds_prompt):
        assert "<certification_target_rules>" in text
        assert "LỜI CHỨNG THỰC" in text
        assert '"certificationTarget":true' in text
