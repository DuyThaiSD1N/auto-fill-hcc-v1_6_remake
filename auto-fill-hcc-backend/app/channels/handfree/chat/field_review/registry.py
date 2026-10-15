"""Tự khám phá cấu hình bổ sung ô theo thủ tục.

Mỗi ``app/pipelines/<tên>/handfree/field_review.py`` khai ``PROCEDURE_KEYS``, ``REQUIRED`` (tên ô bắt buộc trên
tờ khai) và tuỳ chọn ``NO_SECTION`` (ô không thuộc phần nào — hỏi không kèm tên phần). Thủ tục không có file
này thì không bật vòng bổ sung. Lỗi cấu hình hoặc trùng key được phát hiện ngay lúc khởi động.
"""
from importlib import import_module
from pathlib import Path


def _names(module_name: str, value, attr: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not all(isinstance(v, str) and v.strip() for v in value):
        raise RuntimeError(f"{module_name}.{attr} phải là danh sách tên ô")
    return tuple(value)


def _discover() -> dict[str, dict]:
    configs: dict[str, dict] = {}
    pipelines_dir = Path(__file__).resolve().parents[4] / "pipelines"
    for config_path in sorted(pipelines_dir.glob("*/handfree/field_review.py")):
        module_name = f"app.pipelines.{config_path.parent.parent.name}.handfree.field_review"
        module = import_module(module_name)
        procedure_keys = getattr(module, "PROCEDURE_KEYS", None)
        if not procedure_keys:
            raise RuntimeError(f"{module_name} thiếu PROCEDURE_KEYS")
        config = {
            "required": _names(module_name, getattr(module, "REQUIRED", None), "REQUIRED"),
            "noSection": _names(module_name, getattr(module, "NO_SECTION", ()), "NO_SECTION"),
        }
        for raw_key in procedure_keys:
            procedure_key = str(raw_key or "").strip()
            if not procedure_key:
                raise RuntimeError(f"{module_name} chứa procedure key rỗng")
            if procedure_key in configs:
                raise RuntimeError(f"Trùng cấu hình bổ sung ô cho {procedure_key}")
            configs[procedure_key] = config
    return configs


_CONFIGS = _discover()


def get(procedure_key: str) -> dict | None:
    return _CONFIGS.get(str(procedure_key or ""))
