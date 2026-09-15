import json
import sys
from types import SimpleNamespace

from app.pipelines.chung_thuc_giao_dich_tai_san.attach import planner
from app.pipelines.chung_thuc_giao_dich_tai_san.attach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.process.schemas import FileItem
from app.procedures.registry import get_pipeline, get_procedure


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


def _patch_ocr(monkeypatch, fake_ocr_per_file):
    fake_ocr = SimpleNamespace(ocr_per_file=fake_ocr_per_file)
    monkeypatch.setitem(sys.modules, "app.services.ocr", fake_ocr)


async def test_chung_thuc_giao_dich_tai_san_attachment_plan_routes_fixed_rows(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "dang-ky-xe.pdf", "text": "GIẤY CHỨNG NHẬN ĐĂNG KÝ XE MÔ TÔ"},
            {
                "name": "hop-dong.pdf",
                "text": "HỢP ĐỒNG CHUYỂN NHƯỢNG QUYỀN SỞ HỮU XE MÔ TÔ",
            },
            {"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN\nSố định danh cá nhân: 040203015844"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "asset_ownership_proof", "title": "Đăng ký xe"},
                {
                    "index": 1,
                    "type": "transaction_draft",
                    "title": "Hợp đồng chuyển nhượng quyền sở hữu xe mô tô",
                },
                {"index": 2, "type": "identity_document", "title": "Căn cước công dân"},
            ]
        })

    _patch_ocr(monkeypatch, fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan_chung_thuc_giao_dich_tai_san_attachments(
        [_file("dang-ky-xe.pdf"), _file("hop-dong.pdf"), _file("cccd.pdf")],
        {},
    )
    items = res["attachments"]

    assert items[0]["target"] == "existing"
    assert items[0]["componentIndex"] == 1
    assert "giấy chứng nhận quyền sở hữu, quyền sử dụng" in items[0]["componentName"]
    assert items[0]["documentName"] == "Đăng ký xe"
    assert items[1]["target"] == "existing"
    assert items[1]["componentIndex"] == 2
    assert items[1]["componentName"] == "Dự thảo giao dịch"
    assert items[1]["documentName"] == "Hợp đồng chuyển nhượng quyền sở hữu xe mô tô"
    assert items[2]["target"] == "new"
    assert items[2]["componentName"] == "Căn cước công dân"
    assert items[2]["needsAddComponent"] is True


async def test_chung_thuc_giao_dich_tai_san_repeated_fixed_type_becomes_new_component(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "dang-ky-xe-1.pdf", "text": "GIẤY CHỨNG NHẬN ĐĂNG KÝ XE"},
            {"name": "dang-ky-xe-2.pdf", "text": "GIẤY CHỨNG NHẬN ĐĂNG KÝ XE"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "type": "asset_ownership_proof", "title": "Đăng ký xe"},
                {"index": 1, "type": "asset_ownership_proof", "title": "Đăng ký xe"},
            ]
        })

    _patch_ocr(monkeypatch, fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan_chung_thuc_giao_dich_tai_san_attachments(
        [_file("dang-ky-xe-1.pdf"), _file("dang-ky-xe-2.pdf")],
        {},
    )
    items = res["attachments"]

    assert items[0]["target"] == "existing"
    assert items[0]["componentIndex"] == 1
    assert items[1]["target"] == "new"
    assert items[1]["componentName"] == "Đăng ký xe 2"
    assert items[1]["documentName"] == "Đăng ký xe 2"


def test_chung_thuc_giao_dich_tai_san_procedure_is_attach_only():
    proc = get_procedure("chung-thuc-giao-dich-tai-san")

    assert proc is not None
    assert proc["mode"] == "attach"
    assert proc["roles"] == []
    assert "Dự thảo giao dịch" in proc["uploadHint"]
    assert get_pipeline("chung-thuc-giao-dich-tai-san") is None


def test_chung_thuc_giao_dich_tai_san_normalizes_asset_title():
    assert planner._label_for_type(  # noqa: SLF001
        "asset_ownership_proof",
        "Giấy chứng nhận đăng ký xe mô tô, xe gắn máy",
    ) == "Đăng ký xe"


def test_chung_thuc_giao_dich_tai_san_prompt_uses_ocr_text_only():
    assert "asset_ownership_proof" in SYSTEM_PROMPT
    assert "transaction_draft" in SYSTEM_PROMPT
    assert "Không dùng tên file" in SYSTEM_PROMPT

    prompt = build_user_prompt([
        {
            "index": 0,
            "fileName": "Hợp đồng chuyển nhượng quyền sở hữu xe mô tô.pdf",
            "text": "HỢP ĐỒNG CHUYỂN NHƯỢNG QUYỀN SỞ HỮU XE MÔ TÔ",
        }
    ])

    assert "ocrText" in prompt
    assert "HỢP ĐỒNG CHUYỂN NHƯỢNG" in prompt
    assert "Hợp đồng chuyển nhượng quyền sở hữu xe mô tô.pdf" not in prompt
    assert "fileName" not in prompt
