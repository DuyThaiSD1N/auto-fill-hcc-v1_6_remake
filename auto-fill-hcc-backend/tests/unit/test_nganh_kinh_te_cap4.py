"""Tri thức ngành kinh tế (QĐ 36/2025/QĐ-TTg) cho đăng ký kinh doanh: chỉ mã 4 số."""
import json
import re
from pathlib import Path

import app.pipelines.dang_ky_kinh_doanh as pkg

_FILE = Path(pkg.__file__).parent / "data" / "nganh_kinh_te_cap4.json"


def test_chi_co_ma_4_so_khong_trung_va_du_noi_dung():
    nganh = json.loads(_FILE.read_text(encoding="utf-8"))["nganh"]
    ma = [n["ma"] for n in nganh]
    assert len(ma) == 495 and len(set(ma)) == 495
    assert all(re.fullmatch(r"\d{4}", m) for m in ma)
    assert all(n["ten"].strip() and n["noiDung"].strip() for n in nganh)
    assert not any(re.search(r"(?<!\d)\d{5}(?!\d)", n["noiDung"]) for n in nganh), "không còn mã cấp 5"


def test_vai_nganh_ho_kinh_doanh_hay_gap():
    by_ma = {n["ma"]: n for n in json.loads(_FILE.read_text(encoding="utf-8"))["nganh"]}
    assert by_ma["4722"]["ten"] == "Bán lẻ thực phẩm"
    assert by_ma["5610"]["ten"] == "Nhà hàng và các dịch vụ ăn uống phục vụ lưu động"
    assert "Bán lẻ rau, quả" in by_ma["4722"]["noiDung"]
