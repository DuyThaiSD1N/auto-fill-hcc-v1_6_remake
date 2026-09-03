"""Hotfix theo tài khoản: chèn 1 file ẢO vào STT1 cho thủ tục Chứng thực bản sao.

Chỉ áp dụng cho tài khoản extension có **tỉnh Đà Nẵng + xã/phường Hải Châu**. Với các
tài khoản đó, cán bộ muốn ô cố định STT1 ("Bản chính giấy tờ… và bản sao cần chứng thực")
KHÔNG chứa giấy tờ thật, mà chỉ nhận một bản COPY (đổi tên) của một file thật; toàn bộ giấy
tờ thật được đẩy xuống các dòng "Thêm thành phần hồ sơ".

Module này CHỈ:
  1. Nhận diện account (fold(tinh) chứa "da nang" và fold(xa) chứa "hai chau").
  2. Đẩy item đang ở STT1 (target=existing, componentIndex=1) xuống dòng thêm (target=new).
  3. Gắn directive ``stt1VirtualCopy`` để extension tự vật chất hoá file ảo theo từng mode
     (merge: 1 ảo ở STT1; split: mỗi tab 1 ảo copy chính file của tab).

Backend KHÔNG tạo byte file ảo — extension dùng lại fileIndex + đổi tên nên không tốn payload.
Mọi thủ tục/tài khoản khác: hàm trả nguyên `result`, hành vi giữ y hệt hiện tại.
"""
from typing import Any

from app.pipelines._shared import fold
from app.pipelines.chung_thuc_ban_sao.attach.planner import (
    DEFAULT_COPY_CERTIFICATION_COMPONENT,
)

# Chỉ bật hotfix cho đúng thủ tục này; router truyền procedure key vào để chặn nhầm thủ tục khác.
PROCEDURE_KEY = "chung-thuc-ban-sao"


def is_da_nang_hai_chau(user: dict | None) -> bool:
    """True khi tài khoản thuộc phường Hải Châu, Đà Nẵng.

    Khớp LỎNG bằng substring trên chuỗi đã fold dấu để chịu được mọi biến thể lưu trong DB
    ("Thành phố Đà Nẵng"/"Đà Nẵng", "Phường Hải Châu"/"Hải Châu"…).
    """
    if not user:
        return False
    tinh = fold(user.get("tinh") or "")
    xa = fold(user.get("xa") or "")
    return "da nang" in tinh and "hai chau" in xa


def _reroute_stt1_to_new(item: dict) -> dict:
    """Chuyển item đang ở ô cố định STT1 thành một dòng "Thêm thành phần hồ sơ" (target=new).

    Tên thành phần dùng chính tên tài liệu để tạo dòng có nhãn rõ ràng, không giữ lại mô tả
    dài của ô STT1 (nếu giữ, extension sẽ khớp nhầm trở lại STT1).
    """
    new_name = (item.get("documentName") or item.get("detectedType") or "").strip()
    if not new_name or fold(new_name) in fold(DEFAULT_COPY_CERTIFICATION_COMPONENT):
        new_name = "Tài liệu chứng thực"
    return {
        **item,
        "componentName": new_name,
        "target": "new",
        "componentIndex": None,
        "needsAddComponent": True,
    }


def apply_stt1_virtual_copy(result: dict, user: dict | None, procedure: str) -> dict:
    """Sửa `result` tại chỗ cho account Hải Châu; trả nguyên `result` cho mọi trường hợp khác."""
    if procedure != PROCEDURE_KEY or not is_da_nang_hai_chau(user):
        return result

    attachments = result.get("attachments")
    if not isinstance(attachments, list) or not attachments:
        return result

    # Đẩy giấy tờ thật đang ở STT1 xuống dòng thêm → STT1 để trống cho file ảo (do FE chèn).
    rerouted: list[dict] = []
    for item in attachments:
        if item.get("target") == "existing" and item.get("componentIndex") == 1:
            rerouted.append(_reroute_stt1_to_new(item))
        else:
            rerouted.append(item)
    result["attachments"] = rerouted

    # Directive để extension biết cần chèn file ảo vào STT1 (merge 1 file; split mỗi tab 1 file).
    result["stt1VirtualCopy"] = {
        "componentName": DEFAULT_COPY_CERTIFICATION_COMPONENT,
        "componentIndex": 1,
    }
    return result
