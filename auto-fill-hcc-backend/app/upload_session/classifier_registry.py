"""Tự khám phá cấu hình phân loại upload dành riêng cho channel Handfree.

Mỗi ``app/pipelines/<tên>/handfree/upload_classification.py`` khai ``PROCEDURE_KEYS``
và ``SPEC``. Nhờ vậy engine upload không cần thêm một nhánh ``if procedure_key`` mỗi
khi mở rộng thủ tục; lỗi cấu hình hoặc trùng key được phát hiện ngay lúc khởi động.
"""
from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path

from app.upload_session.llm_classifier import ClassificationSpec


FallbackToSlot = Callable[
    [str, list[dict], list[dict], str | None],
    tuple[str | None, str | None, str],
]


@dataclass(frozen=True)
class UploadClassifier:
    spec: ClassificationSpec
    fallback_to_slot: FallbackToSlot | None = None


def _discover() -> dict[str, UploadClassifier]:
    classifiers: dict[str, UploadClassifier] = {}
    pipelines_dir = Path(__file__).resolve().parents[1] / "pipelines"

    for config_path in sorted(pipelines_dir.glob("*/handfree/upload_classification.py")):
        # config_path.parent là thư mục handfree; procedure nằm ở cấp cha.
        package_name = config_path.parent.parent.name
        module_name = f"app.pipelines.{package_name}.handfree.upload_classification"
        module = import_module(module_name)

        procedure_keys = getattr(module, "PROCEDURE_KEYS", None)
        spec = getattr(module, "SPEC", None)
        fallback = getattr(module, "fallback_to_slot", None)

        if not procedure_keys:
            raise RuntimeError(f"{module_name} thiếu PROCEDURE_KEYS")
        if not isinstance(spec, ClassificationSpec):
            raise RuntimeError(f"{module_name} thiếu ClassificationSpec hợp lệ")
        if fallback is not None and not callable(fallback):
            raise RuntimeError(f"{module_name}.fallback_to_slot phải là hàm")

        classifier = UploadClassifier(spec=spec, fallback_to_slot=fallback)
        for raw_key in procedure_keys:
            procedure_key = str(raw_key or "").strip()
            if not procedure_key:
                raise RuntimeError(f"{module_name} chứa procedure key rỗng")
            if procedure_key in classifiers:
                raise RuntimeError(f"Trùng upload classifier cho {procedure_key}")
            classifiers[procedure_key] = classifier

    return classifiers


_CLASSIFIERS = _discover()


def get_upload_classifier(procedure_key: str) -> UploadClassifier | None:
    return _CLASSIFIERS.get(procedure_key)
