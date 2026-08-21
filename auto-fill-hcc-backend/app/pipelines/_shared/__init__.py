"""Tiện ích dùng chung cho các pipeline thủ tục."""
from app.pipelines._shared.naming import (
    GENERIC_DOCUMENT_TYPE,
    fold,
    normalize_document_name,
    sanitize_wallet_document_label,
)

__all__ = [
    "GENERIC_DOCUMENT_TYPE",
    "fold",
    "normalize_document_name",
    "sanitize_wallet_document_label",
]
