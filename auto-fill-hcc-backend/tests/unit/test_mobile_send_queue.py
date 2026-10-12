"""Trang điện thoại Auto Fill gửi MỖI TỆP MỘT LƯỢT (tối đa 2 cùng lúc), có mã chống trùng.

Gửi cả khay trong một lượt: máy tính chờ tệp cuối mới thấy tệp đầu, đứt mạng gửi lại cả cục.
Chạy THẬT script của trang bằng node với DOM/XHR giả (tests/unit/js/mobile_send_queue_harness.js).
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from app.upload_session.mobile_page import render_mobile_page

HARNESS = Path(__file__).parent / "js" / "mobile_send_queue_harness.js"
pytestmark = pytest.mark.skipif(not shutil.which("node"), reason="cần node để chạy script trang điện thoại")


def _run(tmp_path, scenario: str) -> dict:
    html = render_mobile_page("HS-QUEUE01")
    js = tmp_path / "page.js"
    js.write_text(html[html.index("<script>") + 8:html.rindex("</script>")], encoding="utf-8")
    out = subprocess.run(["node", str(HARNESS), str(js), scenario], capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_moi_tep_mot_luot_toi_da_hai_luong(tmp_path):
    res = _run(tmp_path, "ok")
    assert [r["name"] for r in res["requests"]] == ["a.pdf", "b.pdf", "c.pdf"]
    assert res["maxActive"] == 2
    assert len({r["key"] for r in res["requests"]}) == 3, "mỗi tệp một mã chống trùng"
    assert all(r["token"] == "TK" and r["url"] == "/api/v1/upload-sessions/HS-QUEUE01/files" for r in res["requests"])
    assert res["stat"].startswith("✅ Đã gửi")
    assert res["sendBtn"] == "📤 Chưa có tài liệu để gửi", "gửi xong tệp nào rời khay tệp đó"


def test_loi_mang_gui_lai_dung_tep_do_voi_cung_ma(tmp_path):
    res = _run(tmp_path, "retry")
    b = [r for r in res["requests"] if r["name"] == "b.pdf"]
    assert len(b) == 2 and b[0]["key"] == b[1]["key"], "gửi lại giữ nguyên mã để máy chủ bỏ bản trùng"
    assert len([r for r in res["requests"] if r["name"] == "a.pdf"]) == 1
    assert res["stat"].startswith("✅ Đã gửi")


def test_tep_bi_tu_choi_nam_lai_khay_tep_khac_van_gui(tmp_path):
    res = _run(tmp_path, "reject")
    # Lượt Gửi lại chỉ còn đúng tệp bị từ chối, giữ mã cũ.
    assert [r["name"] for r in res["requests"]] == ["b.pdf"]
    assert res["stat"].startswith("✅ Đã gửi")


def test_mang_dung_hinh_huy_va_gui_lai(tmp_path):
    res = _run(tmp_path, "stall")
    b = [r for r in res["requests"] if r["name"] == "b.pdf"]
    assert len(b) == 2 and b[0]["key"] == b[1]["key"]
    assert res["stat"].startswith("✅ Đã gửi")
