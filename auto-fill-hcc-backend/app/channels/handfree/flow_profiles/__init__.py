"""Resolve reusable backend flow profiles into procedure capabilities."""

from copy import deepcopy

from .tu_phap import TU_PHAP_FLOW


FLOW_PROFILES: dict[str, dict] = {
    "tu-phap": TU_PHAP_FLOW,
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge dictionaries; procedure values always win."""
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _validate_resolved(procedure: dict) -> None:
    profile_key = str(procedure.get("flowProfile") or "")
    if not profile_key:
        return

    wizard = procedure.get("wizard") or {}
    steps = [wizard.get(name) for name in (
        "ownerStep", "declarationStep", "attachmentStep", "resultStep"
    )]
    if any(not isinstance(step, int) or step <= 0 for step in steps) or len(set(steps)) != 4:
        raise ValueError(
            f"Thủ tục {procedure.get('key')} có wizard không hợp lệ cho profile {profile_key}."
        )

    execution_subject = procedure.get("executionSubject") or {}
    execution_subject_keys: set[str] = set()
    if execution_subject.get("enabled"):
        options = execution_subject.get("options") or []
        option_keys = {
            str(option.get("key") or "")
            for option in options
            if isinstance(option, dict)
            and option.get("label")
            and option.get("portalValue") is not None
        }
        default = str(execution_subject.get("default") or "")
        if len(option_keys) != len(options) or default not in option_keys:
            raise ValueError(
                f"Thủ tục {procedure.get('key')} có executionSubject không hợp lệ."
            )
        execution_subject_keys = option_keys

    authorization_info = procedure.get("authorizationInfo") or {}
    if authorization_info.get("enabled"):
        active_subject = str(
            (authorization_info.get("activeWhen") or {}).get("executionSubject") or ""
        )
        auth_fields = authorization_info.get("fields") or {}
        if active_subject not in execution_subject_keys or not auth_fields:
            raise ValueError(
                f"Thủ tục {procedure.get('key')} có authorizationInfo không hợp lệ."
            )
        required = {"key", "label", "comp", "reportLabel", "sectionLabel"}
        for source_name, spec in auth_fields.items():
            if not isinstance(spec, dict) or not required.issubset(spec):
                raise ValueError(
                    f"Trường authorizationInfo {source_name} của "
                    f"{procedure.get('key')} thiếu contract."
                )

    owner_info = procedure.get("ownerInfo") or {}
    if not owner_info.get("enabled"):
        return
    fields = owner_info.get("fields") or {}
    if not fields:
        raise ValueError(f"Thủ tục {procedure.get('key')} bật ownerInfo nhưng không có fields.")
    required = {"key", "label", "comp", "reportLabel"}
    for source_name, spec in fields.items():
        if not isinstance(spec, dict) or not required.issubset(spec):
            raise ValueError(
                f"Trường ownerInfo {source_name} của {procedure.get('key')} thiếu contract."
            )


def resolve_flow_profile(procedure: dict) -> dict:
    """Materialize one raw registry entry without leaking behavior to the extension."""
    profile_key = str(procedure.get("flowProfile") or "").strip()
    if not profile_key:
        return deepcopy(procedure)
    profile = FLOW_PROFILES.get(profile_key)
    if profile is None:
        raise ValueError(
            f"Thủ tục {procedure.get('key')} khai báo flowProfile không tồn tại: {profile_key}"
        )
    resolved = _deep_merge(profile, procedure)
    _validate_resolved(resolved)
    return resolved


__all__ = ["FLOW_PROFILES", "resolve_flow_profile"]
